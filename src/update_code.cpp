#include "config.h"
#include <ArduinoJson.h>
#include <Update.h>
#include "mqtt_tasks.h"

void updateCode(char* topic, byte* payload, unsigned int length) {
    if (strcmp(topic, CONTROL_TOPIC) == 0) {
        JsonDocument doc;
        deserializeJson(doc, payload, length);
        const char* type = doc["type"];

        if (strcmp(type, "start") == 0) {
            if (ota_in_progress) {
                publishLog("Error: OTA already in progress.");
                return;
            }
            total_size = doc["size"];
            if (total_size == 0) {
                publishLog("Error: Invalid firmware size (0).");
                return;
            }
            // Begin the OTA process. This erases the target partition.
            if (Update.begin(total_size)) {
                ota_in_progress = true;
                bytes_received = 0;
                publishLog("OTA started. Waiting for firmware...");
                Serial.printf("OTA Update Started. Total size: %d\n", total_size);
            } else {
                publishLog("Error: Not enough space for OTA. Check partition scheme.");
                Update.printError(Serial);
            }
        } else if (strcmp(type, "end") == 0) {
            if (!ota_in_progress) return;
            // Finalize the update. The 'true' argument makes it bootable.
            if (Update.end(true)) {
                publishLog("Update successful! Rebooting...");
                Serial.println("OTA Done! Rebooting...");
                delay(1000);
                ESP.restart();
            } else {
                publishLog("Error during Update.end(). HASH/verification failed.");
                Update.printError(Serial);
                ota_in_progress = false;
            }
        } else if (strcmp(type, "abort") == 0) {
            if (!ota_in_progress) return;
            Update.abort();
            ota_in_progress = false;
            publishLog("OTA aborted by server.");
        }
        return;
    }

    // Handle firmware data chunks
    if (strcmp(topic, FIRMWARE_TOPIC) == 0) {
        if (!ota_in_progress) return;
        if (length > 0) {
            // Write the received chunk to the flash partition
            Update.write(payload, length);
            bytes_received += length;
            Serial.printf("Received chunk. Total: %d / %d\n", bytes_received, total_size);
        }
    }
}