#include "Logging.h"
#include "esp_system.h"
#include <cassert>
#include <cstdlib>
esp_reset_reason_t testResetReason = ESP_RST_POWERON;
void addToLogRingBuffer(const char*);
int main(int argc, char** argv) {
 assert(argc == 2);
 clearLastLogs();
 addToLogRingBuffer("before-crash\n");
 testResetReason = static_cast<esp_reset_reason_t>(std::atoi(argv[1]));
 for (int i=0; i<32; ++i) addToLogRingBuffer("new-boot\n");
 assert(getLastLogs() == "before-crash\n");
 resumeLogRingBuffer();
 addToLogRingBuffer("after-report\n");
 assert(getLastLogs() == "before-crash\nafter-report\n");
 clearLastLogs();
 assert(getLastLogs().empty());
 addToLogRingBuffer("normal-runtime\n");
 assert(getLastLogs() == "normal-runtime\n");
}
