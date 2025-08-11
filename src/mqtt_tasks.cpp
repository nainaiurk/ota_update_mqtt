#include "config.h"
#include "mqtt_tasks.h"
#include "update_code.h"

void setup_mqtt(){
    wifiClientSecure.setCACert(hivemq_ca_cert);
    mqttClient.setServer(mqtt_server, mqtt_port);
    mqttClient.setCallback(mqtt_callback);
    mqttClient.setBufferSize(CHUNK_SIZE + 200);
}

void reconnect_mqtt() {
    while (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection to HiveMQ Cloud...");
        String client_id = "esp32-ota-client-";
        client_id += String(random(0xffff), HEX);

        if (mqttClient.connect(client_id.c_str(), mqtt_username, mqtt_password)) {
            Serial.println("connected");
            // Subscribe to topics with QoS 1 for reliable delivery
            mqttClient.subscribe(CONTROL_TOPIC, 1);
            mqttClient.subscribe(FIRMWARE_TOPIC, 1);
            
            char buffer[100];
            sprintf(buffer, "ESP32 Ready. Firmware v%.2f", FIRMWARE_VERSION);
            publishLog(buffer);
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

void publishLog(const char* message) {
    if (mqttClient.connected()) {
        mqttClient.publish(LOG_TOPIC, message);
    }
}

// Callback function for handling incoming MQTT messages
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    updateCode(topic, payload, length);
}