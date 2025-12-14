#include "Logger.h"

void Logger::logInfo(const String& message) {
    Serial.print("[INFO]: ");
    Serial.println(message);
}

void Logger::logWarning(const String& message) {
    Serial.print("[WARNING]: ");
    Serial.println(message);
}

void Logger::logError(const String& message) {
    Serial.print("[ERROR]: ");
    Serial.println(message);
}