#include "MQTTClient.h"

MQTTClient::MQTTClient(Client& networkClient, const char* server, uint16_t port) : client(networkClient) {
    client.setServer(server, port);
}

void MQTTClient::connect(const char* clientId, const char* username, const char* password) {
    while (!client.connected()) {
        if (client.connect(clientId, username, password)) {
            Serial.println("MQTT connected");
        } else {
            Serial.print("MQTT connection failed, rc=");
            Serial.println(client.state());
            delay(5000);
        }
    }
}

void MQTTClient::publish(const char* topic, const char* payload) {
    client.publish(topic, payload);
}

void MQTTClient::subscribe(const char* topic) {
    client.subscribe(topic);
}

void MQTTClient::loop() {
    client.loop();
}