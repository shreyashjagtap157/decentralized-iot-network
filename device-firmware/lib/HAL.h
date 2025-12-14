#ifndef HAL_H
#define HAL_H

#include <Arduino.h>

class HAL {
public:
    // GPIO Control
    static void pinModeSetup(uint8_t pin, uint8_t mode);
    static void digitalWritePin(uint8_t pin, uint8_t value);
    static int digitalReadPin(uint8_t pin);

    // ADC/DAC Operations
    static int analogReadPin(uint8_t pin);
    static void analogWritePin(uint8_t pin, int value);

    // UART Communication
    static void uartBegin(long baudRate);
    static void uartWrite(const char* data);
    static String uartRead();

    // I2C Communication
    static void i2cBegin();
    static void i2cWrite(uint8_t address, uint8_t data);
    static uint8_t i2cRead(uint8_t address);

    // SPI Communication
    static void spiBegin();
    static void spiTransfer(uint8_t data);

    // PWM Control
    static void pwmSetup(uint8_t pin, uint16_t frequency, uint8_t resolution);
    static void pwmWrite(uint8_t pin, uint32_t value);
};

#endif