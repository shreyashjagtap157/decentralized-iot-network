#ifndef LOGGER_H
#define LOGGER_H

#include <Arduino.h>

class Logger {
public:
    static void logInfo(const String& message);
    static void logWarning(const String& message);
    static void logError(const String& message);
};

#endif