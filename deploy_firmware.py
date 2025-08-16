# deploy_firmware.py

import os
import paho.mqtt.client as mqtt
import ssl
import json
import time
import threading

# --- MQTT Configuration ---
MQTT_BROKER_IP = os.getenv("MQTT_BROKER_IP")
MQTT_PORT = 8883
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

# --- Topics and Files ---
FIRMWARE_FILE = os.getenv("FIRMWARE_FILE")
DEVICE_ID = os.getenv("DEVICE_ID")
OTA_CONTROL_TOPIC = os.getenv("OTA_CONTROL_TOPIC")
FIRMWARE_TOPIC = os.getenv("FIRMWARE_TOPIC")
LOG_TOPIC = f"{DEVICE_ID}/ota/log" # The log topic for this device

CHUNK_SIZE = 8192

# Use a threading.Event to signal when the OTA is complete or failed
ota_finished_event = threading.Event()
ota_status = "in_progress"

# --- MQTT Client Setup ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(LOG_TOPIC) 
    else:
        print(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    global ota_status
    print(f"[{msg.topic}] {msg.payload.decode()}")
    log_message = msg.payload.decode()
    
    if msg.topic == LOG_TOPIC:
        if "OTA Success" in log_message:
            ota_status = "success"
            ota_finished_event.set() # Signal completion
        elif "failed" in log_message.lower() or "error" in log_message.lower():
            ota_status = "failed"
            ota_finished_event.set() # Signal failure

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS)

# --- Firmware Deployment Logic ---
def deploy_firmware():
    global ota_status
    try:
        if not os.path.exists(FIRMWARE_FILE):
            print(f"ERROR: Firmware file '{FIRMWARE_FILE}' not found.")
            ota_status = "file_not_found"
            ota_finished_event.set()
            return

        with open(FIRMWARE_FILE, 'rb') as f:
            firmware_data = f.read()
        
        total_size = len(firmware_data)
        
        print(f"Starting OTA for {DEVICE_ID}. Size: {total_size} bytes.")

        start_payload = json.dumps({"type": "start", "size": total_size})
        mqtt_client.publish(OTA_CONTROL_TOPIC, start_payload, qos=1)
        time.sleep(1)

        offset = 0
        while offset < total_size and not ota_finished_event.is_set():
            chunk = firmware_data[offset:offset + CHUNK_SIZE]
            mqtt_client.publish(FIRMWARE_TOPIC, chunk, qos=1)
            offset += len(chunk)
            time.sleep(0.02)

        if ota_status == "in_progress":
            end_payload = json.dumps({"type": "end"})
            mqtt_client.publish(OTA_CONTROL_TOPIC, end_payload, qos=1)
            print("Published END message.")

    except Exception as e:
        print(f"An error occurred during OTA: {e}")
        ota_status = "failed"
        ota_finished_event.set()

# Main execution
if __name__ == '__main__':
    try:
        # Connection loop with retries
        connected = False
        retry_count = 0
        max_retries = 5
        while not connected and retry_count < max_retries:
            print(f"Attempting MQTT connection (retry {retry_count + 1}/{max_retries})...")
            try:
                mqtt_client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)
                connected = True
            except Exception as e:
                print(f"Connection failed: {e}. Retrying in 10 seconds.")
                time.sleep(10)
                retry_count += 1

        if not connected:
            print("Failed to connect to MQTT broker after multiple retries. Exiting.")
            exit(1)

        mqtt_client.loop_start() 
        deploy_firmware()
        
        print("Waiting for OTA process to complete...")
        if not ota_finished_event.wait(timeout=600):
            print("Timeout: OTA process did not complete in time.")
            ota_status = "timeout"
            
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
        if ota_status == "success":
            print("\nOTA Deployment Successful! 🎉")
            exit(0)
        else:
            print(f"\nOTA Deployment Failed with status: {ota_status} ❌")
            exit(1)
            
    except Exception as e:
        print(f"Script failed: {e}")
        exit(1)