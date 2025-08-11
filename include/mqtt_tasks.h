#ifndef MQTT_TASKS_H
#define MQTT_TASKS_H

#include "config.h"

void reconnect_mqtt();
void publishLog(const char* message);
void mqtt_callback(char* topic, byte* payload, unsigned int length);
void setup_mqtt();

#endif
