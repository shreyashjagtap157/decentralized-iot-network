#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <Arduino.h>
#include <PubSubClient.h>

class MQTTClient {
public:
    MQTTClient(Client& networkClient, const char* server, uint16_t port);
    void connect(const char* clientId, const char* username = nullptr, const char* password = nullptr);
    void publish(const char* topic, const char* payload);
    void subscribe(const char* topic);
    void loop();

private:
    PubSubClient client;
};

#endif