// RadioPort over the SDK's BleKeyboardHost, with the radio start on a FreeRTOS task. The only
// file of the module that includes the SDK or the chip's headers.
#if defined(FREEINK_CAP_BLE_HID_HOST) && FREEINK_CAP_BLE_HID_HOST

#include <BleKeyboardHost.h>
#include <esp_attr.h>
#include <esp_timer.h>

#include <atomic>
#include <cstdio>

extern "C" void crossmosaBleDiagnostic(const char*) __attribute__((weak));

#include "RadioPort.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace bleturner::port {
namespace {

// Looked up once: every call below is then a plain member call.
freeink::BleKeyboardHost& radioHost = freeink::BleKeyboardHost::getInstance();
freeink::BleKeyboardHost& hid() { return radioHost; }

// Outlives ESP.restart: the one heap restart already spent since the radio last came up.
RTC_NOINIT_ATTR Memo memo;
std::atomic<uint32_t> completedAt{0};
std::atomic<uint32_t> completedStackLeft{0};
std::atomic<bool> completedPending{false};

#ifdef BLE_PAGE_TURNER_STACK_PROBE
std::atomic<uint32_t> startStackMinimum{0};
#endif

// Keep the starter outside the heap: a temporary 3 KB task can split the only
// contiguous reader block during NimBLE init. A persistent worker also avoids
// reusing task storage before the idle task has completed deletion.
StackType_t startStack[4096 / sizeof(StackType_t)];
StaticTask_t startTaskStorage;
TaskHandle_t startWorker = nullptr;

void startTaskEntry(void*) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    detail::startTask();
#ifdef BLE_PAGE_TURNER_STACK_PROBE
    startStackMinimum.store(uxTaskGetStackHighWaterMark(nullptr), std::memory_order_release);
#endif
    completedStackLeft.store(uxTaskGetStackHighWaterMark(nullptr));
    completedAt.store(static_cast<uint32_t>(esp_timer_get_time() / 1000ULL));
    completedPending.store(true, std::memory_order_release);
  }
}

Peer peerOf(const char* addr, const char* name) { return Peer{addr, name}; }

}  // namespace

bool compiledIn() { return true; }
bool begin() { return hid().begin("FreeInk"); }

bool end(const uint32_t timeoutMs) { return hid().end(timeoutMs); }
bool running() { return hid().isRunning(); }
bool stopping() { return hid().isStopping(); }
bool connected() { return hid().isConnected(); }
bool connecting() { return hid().isConnecting(); }
// The SDK reports no advertisement count: a connection attempt in flight is the only activity.
ConnectionActivity connectionActivity() { return {hid().isConnecting(), 0}; }
bool scanning() { return hid().isScanning(); }
void poll() {
  hid().poll();
  if (completedPending.load(std::memory_order_acquire) &&
      static_cast<uint32_t>(esp_timer_get_time() / 1000ULL) - completedAt.load() >= 100 &&
      completedPending.exchange(false)) {
    // Sample the persistent starter's minimum stack margin from the main loop.
    if (crossmosaBleDiagnostic) {
      char line[96];
      snprintf(line, sizeof(line), "async-main-poll-after-100ms stack-min-free=%lu",
               static_cast<unsigned long>(completedStackLeft.load()));
      crossmosaBleDiagnostic(line);
    }
  }
}

bool popRaw(RawEdge& out) {
  freeink::RawButtonEvent ev;
  if (!hid().popRawButton(ev)) return false;
  out.reportId = ev.reportId;
  out.byteIndex = ev.byteIndex;
  out.value = ev.value;
  out.pressed = ev.pressed;
  out.keycode = ev.keycode;
  out.mods = ev.mods;
  out.wasRest = ev.wasRest;
  out.atMs = ev.atMs;
  return true;
}

bool popKey(KeyPress& out) {
  freeink::KeyEvent ev;
  if (!hid().popKey(ev)) return false;
  out.keycode = ev.keycode;
  out.mods = ev.mods;
  out.pressed = ev.pressed;
  return true;
}

// The SDK reconnects one selected remote, so the pick policy cannot ask for "the first bonded
// remote to come up": the chosen remote is armed, and nothing when none is chosen.
bool armBondedReconnect(uint8_t, const char* priorityAddr) {
  return priorityAddr != nullptr && priorityAddr[0] != '\0' && hid().armSelectedPeerReconnect(priorityAddr);
}
Peer linked() { return peerOf(hid().connectedAddr(), hid().connectedName()); }

void scan(const uint32_t durationMs) {
  if (durationMs == 0) {
    hid().stopScan();
  } else {
    hid().startScan(durationMs);
  }
}

bool connect(const char* addr) { return hid().connect(addr); }
void disconnect() { hid().disconnect(); }
void forget(const char* addr) { hid().forget(addr); }
bool takeConnectFailure(char* out, const size_t outLen) { return hid().takeConnectFailure(out, outLen); }
uint8_t bondCount() { return hid().pairedCount(); }
Peer bond(const uint8_t index) { return peerOf(hid().paired(index).addr, hid().paired(index).name); }
uint8_t foundCount() { return hid().deviceCount(); }
Peer found(const uint8_t index) { return peerOf(hid().device(index).addr, hid().device(index).name); }

bool spawnStart() {
  if (!startWorker) {
    // ESP-IDF uses bytes for stack depth, including xTaskCreateStatic.
    startWorker = xTaskCreateStatic(startTaskEntry, "ble-start", sizeof(startStack), nullptr, 2,
                                   startStack, &startTaskStorage);
  }
  if (!startWorker) return false;
  xTaskNotifyGive(startWorker);
  return true;
}
uint32_t nowMs() { return static_cast<uint32_t>(esp_timer_get_time() / 1000ULL); }
void sleepMs(const uint32_t ms) { vTaskDelay(pdMS_TO_TICKS(ms)); }
Memo& restartMemo() { return memo; }

#ifdef BLE_PAGE_TURNER_PROBE
void inject(const uint8_t* frame, const size_t len) { hid().onReportIngest(frame, len); }
unsigned rawOverflows() { return hid().rawOverflows(); }
#endif
#ifdef BLE_PAGE_TURNER_STACK_PROBE
uint32_t startStackLeft() { return startStackMinimum.load(std::memory_order_acquire); }
#endif

}  // namespace bleturner::port

#endif
