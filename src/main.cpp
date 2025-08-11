#include <WiFi.h>
#include "config.h"
#include "mqtt_tasks.h"
#include "update_code.h"

void setup_wifi() {
    delay(10);
    Serial.print("Connecting to ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

void setup() {
    Serial.begin(115200);
    setup_wifi();
    setup_mqtt();
}

void loop() {
    if (!mqttClient.connected()) {
        reconnect_mqtt();
    }
    mqttClient.loop();
    static unsigned long delay = 0;
    if (millis() - delay > 500) {
        Serial.printf("Firmware Version: %.2f\n", FIRMWARE_VERSION);
        delay = millis();
    }

}
