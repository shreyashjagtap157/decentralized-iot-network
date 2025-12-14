#include <Arduino.h>
#include "components.h"

NetworkRelay relay;
MQTTClient mqtt;
MetricsCollector collector;

void setup() {
  Serial.begin(115200);
  relay.setupAP();
  mqtt.connect();
  // Other setup tasks
}

void loop() {
  // Main loop logic
  mqtt.loop();
  collector.collectStats();
  delay(5000); // Report every 5 seconds
}
