#ifndef CONFIG_H
#define CONFIG_H

#include <WiFiClientSecure.h> // Used for TLS/SSL connections, even when insecure
#include <PubSubClient.h>

#define FIRMWARE_VERSION 3.0
#define CHUNK_SIZE 32768  // Must match the chunk size in your Flask server

// --- WiFi Credentials ---
// Replace with your network credentials
extern const char* ssid;
extern const char* password;

// --- HiveMQ Cloud Credentials ---
// These should match the credentials in your Flask application

extern const char* mqtt_server;
extern const int mqtt_port;
extern const char* mqtt_username;
extern const char* mqtt_password;

// --- Root CA Certificate for HiveMQ Cloud (Let's Encrypt - ISRG Root X1) ---
// This is required to validate the server's identity during the TLS handshake.
extern const char* hivemq_ca_cert;

// --- MQTT Topics ---
extern const char* FIRMWARE_TOPIC;
extern const char* CONTROL_TOPIC;
extern const char* LOG_TOPIC;

// --- Global Objects ---
extern WiFiClientSecure wifiClientSecure;
extern PubSubClient mqttClient;

// --- State Variables for OTA Process ---
extern bool ota_in_progress;
extern int total_size;
extern int bytes_received;

#endif