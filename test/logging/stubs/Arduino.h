#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdarg>
#include <cstdio>
#include <algorithm>
#define RTC_NOINIT_ATTR
inline unsigned long millis() { return 0; }
class Print {
public:
 virtual void flush() {}
 virtual size_t write(uint8_t) { return 1; }
 virtual size_t write(const uint8_t*,size_t n) { return n; }
};
