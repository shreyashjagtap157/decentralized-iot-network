#ifndef SENSOR_DRIVER_H
#define SENSOR_DRIVER_H

#include <Arduino.h>

class SensorDriver {
public:
    SensorDriver(uint8_t pin);
    float readTemperature();
    float readHumidity();

private:
    uint8_t sensorPin;
};

#endif