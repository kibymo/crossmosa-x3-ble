#pragma once
#include "Arduino.h"
class HardwareSerial : public Print {
public:
 void begin(unsigned long) {}
 operator bool() const { return false; }
 void print(const char*) {}
};
inline HardwareSerial Serial;
