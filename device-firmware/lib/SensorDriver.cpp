#include "SensorDriver.h"

SensorDriver::SensorDriver(uint8_t pin) : sensorPin(pin) {
    pinMode(sensorPin, INPUT);
}

float SensorDriver::readTemperature() {
    // Simulated temperature reading
    int rawValue = analogRead(sensorPin);
    return (rawValue / 1024.0) * 100.0; // Example conversion
}

float SensorDriver::readHumidity() {
    // Simulated humidity reading
    int rawValue = analogRead(sensorPin);
    return (rawValue / 1024.0) * 100.0; // Example conversion
}