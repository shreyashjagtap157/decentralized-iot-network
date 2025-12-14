#include "HAL.h"

// GPIO Control
void HAL::pinModeSetup(uint8_t pin, uint8_t mode) {
    pinMode(pin, mode);
}

void HAL::digitalWritePin(uint8_t pin, uint8_t value) {
    digitalWrite(pin, value);
}

int HAL::digitalReadPin(uint8_t pin) {
    return digitalRead(pin);
}

// ADC/DAC Operations
int HAL::analogReadPin(uint8_t pin) {
    return analogRead(pin);
}

void HAL::analogWritePin(uint8_t pin, int value) {
    analogWrite(pin, value);
}

// UART Communication
void HAL::uartBegin(long baudRate) {
    Serial.begin(baudRate);
}

void HAL::uartWrite(const char* data) {
    Serial.print(data);
}

String HAL::uartRead() {
    if (Serial.available()) {
        return Serial.readString();
    }
    return "";
}

// I2C Communication
void HAL::i2cBegin() {
    Wire.begin();
}

void HAL::i2cWrite(uint8_t address, uint8_t data) {
    Wire.beginTransmission(address);
    Wire.write(data);
    Wire.endTransmission();
}

uint8_t HAL::i2cRead(uint8_t address) {
    Wire.requestFrom(address, (uint8_t)1);
    if (Wire.available()) {
        return Wire.read();
    }
    return 0;
}

// SPI Communication
void HAL::spiBegin() {
    SPI.begin();
}

void HAL::spiTransfer(uint8_t data) {
    SPI.transfer(data);
}

// PWM Control
void HAL::pwmSetup(uint8_t pin, uint16_t frequency, uint8_t resolution) {
    ledcSetup(pin, frequency, resolution);
    ledcAttachPin(pin, pin);
}

void HAL::pwmWrite(uint8_t pin, uint32_t value) {
    ledcWrite(pin, value);
}