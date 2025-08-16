from flask import Flask, render_template_string, request, redirect, url_for, flash
import paho.mqtt.client as mqtt
import ssl
import time
import os

# --- Configuration ---
# IMPORTANT: Update these with your HiveMQ Cloud credentials
MQTT_BROKER = "efe52791799c4cea8a355ed0a19beaec.s1.eu.hivemq.cloud"  # e.g., "xxxxxxxx.s2.eu.hivemq.cloud"
MQTT_PORT = 8883  # Standard port for secure MQTT (TLS)
MQTT_USERNAME = "ota_test"
MQTT_PASSWORD = "Ota_test123"
MQTT_CLIENT_ID = "flask-ota-server-02"

# MQTT Topics (must match the ESP32 firmware)
FIRMWARE_TOPIC = "esp32/ota/firmware"
CONTROL_TOPIC = "esp32/ota/control"
LOG_TOPIC = "esp32/ota/log" 

# Firmware chunk size
CHUNK_SIZE = 8192   # 8 KB

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.urandom(24) 

# --- MQTT Client Setup ---
def get_mqtt_client():
    """Configures and returns a Paho MQTT client for HiveMQ Cloud."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MQTT_CLIENT_ID)
    
    # Set username and password for authentication
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # Enable TLS for secure connection
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start() # Start a background thread
    return client

# --- Web Page Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flask MQTT OTA Uploader for HiveMQ</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #111827; color: #e5e7eb; }
        .card { background-color: #1f2937; border: 1px solid #374151; }
        .btn { background-color: #3b82f6; }
        .btn:hover { background-color: #2563eb; }
        .file-input-label { border-color: #4b5563; }
        .file-input-label:hover { background-color: #374151; }
        .flashes { list-style: none; padding: 0; }
        .flashes li { padding: 1rem; margin-bottom: 1rem; border-radius: 0.5rem; }
        .flashes .success { background-color: #10b981; color: white; }
        .flashes .error { background-color: #ef4444; color: white; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen">
    <div class="max-w-xl w-full p-4">
        <div class="card rounded-xl shadow-lg p-8">
            <h1 class="text-3xl font-bold text-center mb-2 text-white">ESP32 OTA Uploader</h1>
            <p class="text-center text-gray-400 mb-6">Targeting HiveMQ Cloud</p>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                <ul class="flashes mb-4">
                {% for category, message in messages %}
                  <li class="{{ category }}">{{ message }}</li>
                {% endfor %}
                </ul>
              {% endif %}
            {% endwith %}

            <form action="/upload" method="post" enctype="multipart/form-data">
                <div class="mb-4">
                    <label for="firmware" class="block text-sm font-medium text-gray-300 mb-2">Select Firmware File (.bin)</label>
                    <label for="firmware" class="file-input-label flex items-center justify-center w-full h-32 px-4 transition bg-transparent border-2 border-dashed rounded-md appearance-none cursor-pointer">
                        <span class="flex items-center space-x-2">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <span id="file-name" class="font-medium text-gray-400">
                                Drop file here or <span class="text-blue-400">browse</span>
                            </span>
                        </span>
                        <input type="file" name="firmware" id="firmware" class="hidden" accept=".bin" required onchange="document.getElementById('file-name').textContent = this.files[0].name;">
                    </label>
                </div>
                <button type="submit" class="btn w-full text-white font-bold py-2 px-4 rounded-lg transition-colors">
                    Upload Firmware
                </button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    """Renders the main upload page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the file upload and MQTT publishing logic."""
    if 'firmware' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('index'))
    
    file = request.files['firmware']

    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.bin'):
        try:
            firmware_data = file.read()
            total_size = len(firmware_data)
            
            print(f"Starting OTA update for {file.filename}. Total size: {total_size} bytes.")

            # Connect to MQTT Broker
            client = get_mqtt_client()
            
            # 1. Publish START signal
            start_payload = f'{{"type":"start", "size":{total_size}}}'
            client.publish(CONTROL_TOPIC, start_payload, qos=1)
            print(f"Published START to {CONTROL_TOPIC}")
            time.sleep(1) 

            # 2. Publish firmware in chunks
            offset = 0
            while offset < total_size:
                chunk = firmware_data[offset:offset + CHUNK_SIZE]
                client.publish(FIRMWARE_TOPIC, chunk, qos=1)
                offset += len(chunk)
                print(f"  Published chunk. Progress: {offset}/{total_size} bytes")
                time.sleep(0.02)

            # 3. Publish END signal
            end_payload = '{"type":"end"}'
            client.publish(CONTROL_TOPIC, end_payload, qos=1)
            print(f"Published END to {CONTROL_TOPIC}")

            # Disconnect MQTT client
            client.loop_stop()
            client.disconnect()

            flash(f"Successfully uploaded {file.filename} ({total_size} bytes). ESP32 should be rebooting.", 'success')

        except Exception as e:
            print(f"An error occurred: {e}")
            flash(f"An error occurred: {e}", 'error')
            # In case of error, try to send an abort signal
            try:
                client = get_mqtt_client()
                client.publish(CONTROL_TOPIC, '{"type":"abort"}', qos=1)
                client.disconnect()
            except:
                pass

    else:
        flash('Invalid file type. Please upload a .bin file.', 'error')

    return redirect(url_for('index'))

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)