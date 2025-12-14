#ifndef COMPONENTS_H
#define COMPONENTS_H

#include <Arduino.h>

/**
 * NetworkRelay - Manages WiFi AP mode and packet forwarding
 * for the IoT mesh network relay functionality.
 */
class NetworkRelay {
public:
    void setupAP();
    void processIncomingConnections();
    void processPacket(const uint8_t* data, size_t length);
    void updateBandwidthCounters(size_t length);
    void forwardToOptimalNode();
    void assessConnectionQuality();
    void handleConnectionDrop();
};

/**
 * MQTTClient - Handles MQTT communication with the backend
 * servers for command reception and data transmission.
 */
class MQTTClient {
public:
    void connect();
    void reconnect();
    void publish(const char* topic, const char* payload);
    void subscribe(const char* topic);
    void handleMessage(const char* topic, const char* payload);
    void loop();
};

/**
 * MetricsCollector - Collects and reports device metrics
 * including bandwidth usage, connection quality, and system stats.
 */
class MetricsCollector {
public:
    void collectStats();
    int assessConnectionQuality();
    void sendToBackend(const char* data);
    void aggregateData();
    void cacheLocally();
    void optimizeBattery();
};

#endif
