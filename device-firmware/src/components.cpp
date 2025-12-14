#include "components.h"
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include <Preferences.h>

// Configuration - should be loaded from environment or config file
namespace Config {
    const char* MQTT_BROKER = "mqtt.iot-network.example.com";
    const int MQTT_PORT = 8883;
    const char* WIFI_AP_SSID = "ESP32-IoT-Relay";
    const char* WIFI_AP_PASSWORD = "secure_password_123";
    const char* DEVICE_ID = "ESP32_001";
    const unsigned long METRICS_INTERVAL_MS = 5000;
    const int MAX_CACHED_ENTRIES = 100;
}

// Global counters for bandwidth tracking
struct BandwidthCounters {
    uint32_t bytesTransmitted;
    uint32_t bytesReceived;
    uint32_t packetsProcessed;
    uint32_t droppedPackets;
    unsigned long lastResetTime;
} bandwidthCounters = {0, 0, 0, 0, 0};

// Connection quality metrics
struct QualityMetrics {
    int rssi;
    float packetLossRate;
    int avgLatency;
    int connectionScore;
} qualityMetrics = {0, 0.0, 0, 100};

// Preferences for persistent storage
Preferences preferences;

// NetworkRelay Implementation
void NetworkRelay::setupAP() {
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP(Config::WIFI_AP_SSID, Config::WIFI_AP_PASSWORD);
    
    IPAddress IP = WiFi.softAPIP();
    Serial.print("Access Point Started. IP: ");
    Serial.println(IP);
    
    // Initialize bandwidth counters
    bandwidthCounters.lastResetTime = millis();
}

void NetworkRelay::processPacket(const uint8_t* data, size_t length) {
    if (data == nullptr || length == 0) {
        bandwidthCounters.droppedPackets++;
        return;
    }
    
    // Update bandwidth counters
    updateBandwidthCounters(length);
    bandwidthCounters.packetsProcessed++;
    
    // Forward packet if needed
    forwardToOptimalNode();
}

void NetworkRelay::updateBandwidthCounters(size_t length) {
    // Determine if this is TX or RX based on context
    // For now, assume this is received data
    bandwidthCounters.bytesReceived += length;
    bandwidthCounters.bytesTransmitted += length; // Assuming relay forwards
    
    // Reset counters periodically (every hour)
    if (millis() - bandwidthCounters.lastResetTime > 3600000) {
        // Save to preferences before reset
        preferences.begin("bandwidth", false);
        preferences.putULong("totalTx", preferences.getULong("totalTx", 0) + bandwidthCounters.bytesTransmitted);
        preferences.putULong("totalRx", preferences.getULong("totalRx", 0) + bandwidthCounters.bytesReceived);
        preferences.end();
        
        bandwidthCounters.bytesTransmitted = 0;
        bandwidthCounters.bytesReceived = 0;
        bandwidthCounters.lastResetTime = millis();
    }
}

void NetworkRelay::forwardToOptimalNode() {
    // Simple node selection based on signal strength
    int numStations = WiFi.softAPgetStationNum();
    
    if (numStations == 0) {
        return; // No connected clients
    }
    
    // In a mesh network, we would select the best node
    // For now, just log the forwarding action
    Serial.printf("Forwarding packet to %d connected stations\n", numStations);
}

void NetworkRelay::assessConnectionQuality() {
    // Assess RSSI
    qualityMetrics.rssi = WiFi.RSSI();
    
    // Calculate packet loss rate
    if (bandwidthCounters.packetsProcessed > 0) {
        qualityMetrics.packetLossRate = (float)bandwidthCounters.droppedPackets / 
            (bandwidthCounters.packetsProcessed + bandwidthCounters.droppedPackets) * 100.0;
    }
    
    // Calculate connection score (0-100)
    int rssiScore = map(constrain(qualityMetrics.rssi, -100, -30), -100, -30, 0, 50);
    int lossScore = max(0, 50 - (int)(qualityMetrics.packetLossRate * 5));
    qualityMetrics.connectionScore = rssiScore + lossScore;
    
    Serial.printf("Connection Quality: RSSI=%d, Loss=%.1f%%, Score=%d\n",
        qualityMetrics.rssi, qualityMetrics.packetLossRate, qualityMetrics.connectionScore);
}

void NetworkRelay::handleConnectionDrop() {
    Serial.println("Connection dropped! Attempting recovery...");
    
    // Try to reconnect to WiFi
    if (!WiFi.isConnected()) {
        WiFi.reconnect();
        
        int attempts = 0;
        while (!WiFi.isConnected() && attempts < 10) {
            delay(500);
            Serial.print(".");
            attempts++;
        }
        
        if (WiFi.isConnected()) {
            Serial.println("\nReconnected successfully!");
        } else {
            Serial.println("\nReconnection failed. Will retry later.");
        }
    }
}

// MQTTClient Implementation
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);
MQTTClient* mqttInstance = nullptr;

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    if (mqttInstance) {
        char message[length + 1];
        memcpy(message, payload, length);
        message[length] = '\0';
        mqttInstance->handleMessage(topic, message);
    }
}

void MQTTClient::connect() {
    mqttInstance = this;
    
    // Configure TLS (use proper certificates in production)
    wifiClient.setInsecure(); // Only for development!
    
    mqttClient.setServer(Config::MQTT_BROKER, Config::MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(512);
    
    reconnect();
}

void MQTTClient::reconnect() {
    int retryCount = 0;
    const int maxRetries = 5;
    int backoffDelay = 1000;
    
    while (!mqttClient.connected() && retryCount < maxRetries) {
        Serial.print("Attempting MQTT connection...");
        
        String clientId = String(Config::DEVICE_ID) + "-" + String(random(0xffff), HEX);
        
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("connected");
            
            // Subscribe to command topics
            subscribe("devices/commands/+");
            subscribe(String("devices/" + String(Config::DEVICE_ID) + "/commands").c_str());
            
            // Publish online status
            StaticJsonDocument<100> statusDoc;
            statusDoc["deviceId"] = Config::DEVICE_ID;
            statusDoc["status"] = "online";
            statusDoc["timestamp"] = millis();
            
            char statusBuffer[100];
            serializeJson(statusDoc, statusBuffer);
            publish("devices/status", statusBuffer);
            
        } else {
            Serial.printf("failed, rc=%d. Retry in %dms\n", mqttClient.state(), backoffDelay);
            delay(backoffDelay);
            backoffDelay = min(backoffDelay * 2, 30000); // Exponential backoff, max 30s
            retryCount++;
        }
    }
}

void MQTTClient::publish(const char* topic, const char* payload) {
    if (mqttClient.connected()) {
        if (!mqttClient.publish(topic, payload)) {
            Serial.printf("Failed to publish to %s\n", topic);
        }
    } else {
        Serial.println("MQTT not connected, queuing message...");
        // In production, queue to SPIFFS and retry later
    }
}

void MQTTClient::subscribe(const char* topic) {
    if (mqttClient.connected()) {
        if (mqttClient.subscribe(topic)) {
            Serial.printf("Subscribed to: %s\n", topic);
        } else {
            Serial.printf("Failed to subscribe to: %s\n", topic);
        }
    }
}

void MQTTClient::handleMessage(const char* topic, const char* payload) {
    Serial.printf("Message received [%s]: %s\n", topic, payload);
    
    // Parse JSON command
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
        Serial.printf("JSON parse error: %s\n", error.c_str());
        return;
    }
    
    // Handle different command types
    const char* command = doc["command"];
    if (command) {
        if (strcmp(command, "restart") == 0) {
            Serial.println("Restart command received. Restarting...");
            ESP.restart();
        } else if (strcmp(command, "status") == 0) {
            // Send full status report
            Serial.println("Status request received");
        } else if (strcmp(command, "config") == 0) {
            // Update configuration
            Serial.println("Config update received");
        }
    }
}

void MQTTClient::loop() {
    if (!mqttClient.connected()) {
        reconnect();
    }
    mqttClient.loop();
}

// MetricsCollector Implementation
static unsigned long lastMetricsReport = 0;
static StaticJsonDocument<512> cachedMetrics[10];
static int cachedMetricsCount = 0;

void MetricsCollector::collectStats() {
    if (millis() - lastMetricsReport < Config::METRICS_INTERVAL_MS) {
        return; // Not time yet
    }
    
    StaticJsonDocument<300> doc;
    doc["deviceId"] = Config::DEVICE_ID;
    doc["timestamp"] = millis();
    doc["bytesTransmitted"] = bandwidthCounters.bytesTransmitted;
    doc["bytesReceived"] = bandwidthCounters.bytesReceived;
    doc["connectionQuality"] = assessConnectionQuality();
    doc["userSessions"] = WiFi.softAPgetStationNum();
    doc["freeHeap"] = ESP.getFreeHeap();
    doc["uptime"] = millis() / 1000;
    
    char buffer[300];
    serializeJson(doc, buffer);
    
    sendToBackend(buffer);
    lastMetricsReport = millis();
}

int MetricsCollector::assessConnectionQuality() {
    int rssi = WiFi.RSSI();
    
    // Convert RSSI to quality score (0-100)
    // RSSI typically ranges from -100 (weak) to -30 (excellent)
    int quality;
    if (rssi <= -100) {
        quality = 0;
    } else if (rssi >= -50) {
        quality = 100;
    } else {
        quality = 2 * (rssi + 100);
    }
    
    return quality;
}

void MetricsCollector::sendToBackend(const char* data) {
    // Try to send via MQTT
    if (mqttClient.connected()) {
        String topic = String("devices/") + Config::DEVICE_ID + "/usage";
        mqttClient.publish(topic.c_str(), data);
        Serial.println("Metrics sent to backend");
    } else {
        // Cache locally for later
        cacheLocally();
        Serial.println("Backend unreachable, metrics cached locally");
    }
}

void MetricsCollector::aggregateData() {
    // Aggregate hourly data for efficient reporting
    preferences.begin("metrics", false);
    
    uint32_t hourlyTx = preferences.getULong("hourlyTx", 0);
    uint32_t hourlyRx = preferences.getULong("hourlyRx", 0);
    
    hourlyTx += bandwidthCounters.bytesTransmitted;
    hourlyRx += bandwidthCounters.bytesReceived;
    
    preferences.putULong("hourlyTx", hourlyTx);
    preferences.putULong("hourlyRx", hourlyRx);
    preferences.end();
    
    Serial.printf("Aggregated data - TX: %lu, RX: %lu\n", hourlyTx, hourlyRx);
}

void MetricsCollector::cacheLocally() {
    if (!SPIFFS.begin(true)) {
        Serial.println("SPIFFS mount failed");
        return;
    }
    
    // Append to cache file
    File file = SPIFFS.open("/metrics_cache.json", FILE_APPEND);
    if (!file) {
        Serial.println("Failed to open cache file");
        return;
    }
    
    StaticJsonDocument<200> doc;
    doc["deviceId"] = Config::DEVICE_ID;
    doc["timestamp"] = millis();
    doc["bytesTx"] = bandwidthCounters.bytesTransmitted;
    doc["bytesRx"] = bandwidthCounters.bytesReceived;
    doc["quality"] = qualityMetrics.connectionScore;
    
    String line;
    serializeJson(doc, line);
    file.println(line);
    file.close();
    
    Serial.println("Metrics cached to SPIFFS");
}

void MetricsCollector::optimizeBattery() {
    // Implement power-saving measures for battery operation
    
    // Check if we're in low activity mode
    int connectedClients = WiFi.softAPgetStationNum();
    
    if (connectedClients == 0) {
        // No clients connected, reduce power consumption
        
        // Reduce WiFi TX power
        WiFi.setTxPower(WIFI_POWER_8_5dBm);
        
        // Increase sleep time between operations
        Serial.println("Low activity mode: Power optimization enabled");
        
        // Enter light sleep for a short period
        delay(100);
        esp_sleep_enable_timer_wakeup(100000); // 100ms
        esp_light_sleep_start();
    } else {
        // Clients connected, full power mode
        WiFi.setTxPower(WIFI_POWER_19_5dBm);
    }
}

