#ifndef ENCRYPTION_H
#define ENCRYPTION_H

#include <Arduino.h>
#include <Crypto.h>

class Encryption {
public:
    static String encryptAES(const String& data, const String& key);
    static String decryptAES(const String& data, const String& key);
};

#endif