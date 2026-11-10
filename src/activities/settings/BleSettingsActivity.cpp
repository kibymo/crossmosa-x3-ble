#include "BleSettingsActivity.h"
#include <I18n.h>
#include "CrossPointSettings.h"
#include "I18nKeys.h"
#include "fontIds.h"
#include <cstdio>
#include "util/DiagLog.h"
#include <WiFi.h>
#include <FontCacheManager.h>

namespace {
const char* label(const char* en, const char* zh) {
  return I18n::getInstance().getLanguage() == Language::EN ? en : zh;
}
}  // namespace

bool BleSettingsActivity::startWithDiagnostics() {
  DiagLog::mem("ble-start-before");
  size_t released = 0;
  {
    RenderLock lock(*this);
    if (auto* cache = renderer.getFontCacheManager()) released = cache->releaseForPairing();
  }
  DiagLog::line("BLE pairing cache release bytes=%u", static_cast<unsigned>(released));
  DiagLog::mem("ble-cache-released");
  DiagLog::line("BLE start request wifiMode=%d", static_cast<int>(WiFi.getMode()));
  const bool ok = bleturner::switchOn();
  const auto st = bleturner::status();
  DiagLog::line("BLE start result ok=%d compiled=%d running=%d starting=%d stopping=%d",
                ok, st.compiledIn, st.running, st.starting, st.stopping);
  DiagLog::mem("ble-start-after");
  return ok;
}

void BleSettingsActivity::onEnter() {
  Activity::onEnter();
  previousDiagForced = DiagLog::setForced(true, "ble-settings");
  if (SETTINGS.ble.enabled) startWithDiagnostics();
  refresh();
}
void BleSettingsActivity::onExit() {
  learning = bleturner::Action::None;
  DiagLog::setForced(previousDiagForced, "ble-settings-exit");
  Activity::onExit();
}
void BleSettingsActivity::refresh() {
  RenderLock lock(*this);
  std::vector<Row> next;
  const auto st = bleturner::status();
  if (st.connected != lastConnected) {
    lastConnected = st.connected;
    note = st.connected ? label("Remote connected", "遙控器已連線") : label("Remote disconnected", "遙控器已斷線");
  }
  const char* state = !SETTINGS.ble.enabled ? label("Bluetooth: OFF", "藍牙：關閉")
      : st.connected ? label("Bluetooth: connected", "藍牙：已連線")
      : st.stopping ? label("Bluetooth: stopping", "藍牙：停止中")
      : st.starting ? label("Bluetooth: starting", "藍牙：啟動中")
      : st.readerDeferred ? label("Bluetooth: memory unavailable", "藍牙：記憶體不足")
      : st.connecting ? label("Bluetooth: connecting", "藍牙：連線中")
      : st.scanning ? label("Bluetooth: scanning", "藍牙：搜尋中")
      : st.running ? label("Bluetooth: waiting for remote", "藍牙：等待遙控器")
      : label("Bluetooth: stopped", "藍牙：已停止");
  if (view == View::Menu) {
    next.push_back({SETTINGS.ble.enabled ? label("Bluetooth: ON (toggle)", "藍牙開關：開啟") : label("Bluetooth: OFF (toggle)", "藍牙開關：關閉"), "", 0});
    next.push_back({label("Scan for remotes", "搜尋遙控器"), "", 7});
    next.push_back({label("Paired remotes", "已配對遙控器"), "", 8});
    next.push_back({label("Button mappings", "按鍵設定"), "", 9});
  } else if (view == View::Scan) {
    next.push_back({st.scanning ? label("Scanning...", "搜尋中…") : label("Scan / rescan (15s)", "搜尋／重新搜尋（15 秒）"), "", 1});
    for (uint8_t i = 0; i < bleturner::foundCount(); ++i) {
      const auto p = bleturner::found(i);
      next.push_back({std::string(label("Pair: ", "配對：")) + p.name, p.addr, 5, p.name});
    }
  } else if (view == View::Paired) {
    for (uint8_t i = 0; i < bleturner::bondCount(); ++i) {
      const auto p = bleturner::bond(i);
      next.push_back({std::string(label("Forget: ", "解除配對：")) + p.name, p.addr, 6});
    }
    if (next.empty()) next.push_back({label("No paired remotes", "尚無已配對遙控器"), "", -1});
  } else {
    next.push_back({label("Learn next-page button", "設定下一頁按鍵"), "", 2});
    next.push_back({label("Learn previous-page button", "設定上一頁按鍵"), "", 3});
    next.push_back({label("Reset page button mappings", "還原翻頁按鍵設定"), "", 4});
  }
  // Every panel keeps the live radio state visible, independently of transient notes.
  const std::string panelNote = std::string(state) + (note.empty() ? "" : " | " + note);
  bool changed = next.size() != rows.size() || panelNote != renderedNote;
  renderedNote = panelNote;
  for (size_t i = 0; !changed && i < next.size(); ++i)
    changed = next[i].text != rows[i].text || next[i].addr != rows[i].addr;
  rows = std::move(next);
  if (selected >= rows.size()) selected = 0;
  if (changed) requestUpdate();
}
void BleSettingsActivity::activate() {
  if (selected >= rows.size()) return;
  const Row row = rows[selected];
  switch (row.action) {
    case 7: case 8: case 9:
      {
        RenderLock lock(*this);
        view = row.action == 7 ? View::Scan : row.action == 8 ? View::Paired : View::Mapping;
        selected = 0; note.clear();
      }
      refresh(); requestUpdate(); return;
    case 0:
      SETTINGS.ble.enabled = !SETTINGS.ble.enabled;
      if (SETTINGS.ble.enabled) {
        note = startWithDiagnostics() ? label("Bluetooth ready", "藍牙已就緒") : label("Bluetooth start failed", "藍牙啟動失敗");
      } else {
        bleturner::switchOff(); note = label("Bluetooth off", "藍牙已關閉");
      }
      SETTINGS.saveToFile(); break;
    case 1:
      if (!SETTINGS.ble.enabled) note = label("Enable Bluetooth first", "請先開啟藍牙");
      else if (!startWithDiagnostics()) note = label("Bluetooth start failed", "藍牙啟動失敗");
      else {
        bleturner::scan(15000); note = label("Press the remote to advertise", "請按遙控器以供搜尋");
      }
      break;
    case 2: case 3: {
      if (!bleturner::status().connected) { note = label("Connect a remote first", "請先連線遙控器"); break; }
      learning = row.action == 2 ? bleturner::Action::NextPage : bleturner::Action::PrevPage;
      learnPeer = bleturner::linked().addr;
      learnSince = millis(); learnedCode = 0;
      bleturner::Event discard;
      while (bleturner::pollEvent(discard)) {}
      DiagLog::line("BLE-LEARN start action=%d connected=%d", static_cast<int>(learning), bleturner::status().connected);
      note = label("Press/release remote button (15s)", "請按下並放開遙控器按鍵（15 秒）");
      break;
    }
    case 4: {
      const auto p = bleturner::linked();
      if (!bleturner::status().connected) { note = label("Connect a remote first", "請先連線遙控器"); break; }
      bleturner::forgetRemote(SETTINGS.ble.remotes, SETTINGS.ble.remoteCount, p.addr);
      SETTINGS.ble.prevKeyUsage = SETTINGS.ble.nextKeyUsage = 0;
      SETTINGS.saveToFile(); note = label("Default button mappings restored", "已還原預設按鍵"); break;
    }
    case 5:
      note = bleturner::pair(row.addr.c_str(), row.peerName.c_str()) ? label("Pairing...", "配對中…") : label("Pairing failed", "配對失敗");
      break;
    case 6:
      if (bleturner::forget(row.addr.c_str())) {
        SETTINGS.saveToFile(); note = label("Remote forgotten", "已解除配對");
      } else note = label("Could not forget remote", "無法解除配對");
      break;
  }
  refresh(); requestUpdate();
}
void BleSettingsActivity::keepLearned(bool hold) {
  const auto p = bleturner::linked();
  if (!bleturner::status().connected || learnPeer != p.addr) {
    learning = bleturner::Action::None; note = label("Remote disconnected", "遙控器已斷線"); return;
  }
  auto* t = bleturner::editableTable(SETTINGS.ble.remotes, SETTINGS.ble.remoteCount, p.addr, p.name);
  const bool ok = t && bleturner::learn(*t, learning, learnedCode, hold);
  if (ok) SETTINGS.saveToFile();
  learning = bleturner::Action::None;
  learnedCode = 0;
  note = ok ? label("Button mapping saved", "已儲存按鍵設定") : label("Could not save mapping", "無法儲存按鍵設定");
  DiagLog::line("BLE-LEARN result saved=%d hold=%d", ok, hold);
}
void BleSettingsActivity::learnKey() {
  if (learning == bleturner::Action::None) return;
  const auto p = bleturner::linked();
  if (!bleturner::status().connected || learnPeer != p.addr) {
    learning = bleturner::Action::None; note = label("Learning cancelled", "已取消按鍵設定"); requestUpdate(); return;
  }
  const auto action = learning;
  bleturner::Event ev;
  while (learning == action && bleturner::pollEvent(ev)) {
    if (ev.pressed) {
      learnedCode = ev.code; pressedAt = ev.atMs; learnSince = millis();
    } else if (learnedCode && learnedCode == ev.code) {
      if (ev.wasRest) learnedCode = 0;
      else keepLearned(ev.atMs - pressedAt >= bleturner::kHoldMs);
    }
  }
  if (learning == action && millis() - learnSince >= bleturner::kWaitMs) {
    if (learnedCode) keepLearned(false);
    else { learning = bleturner::Action::None; note = label("No button received", "未收到按鍵"); DiagLog::line("BLE-LEARN timeout no-button"); }
  }
  if (learning != action) { refresh(); requestUpdate(); }
}
void BleSettingsActivity::loop() {
  using B = MappedInputManager::Button;
  if (mappedInput.wasPressed(B::Back)) {
    if (learning != bleturner::Action::None) {
      learning = bleturner::Action::None; note = label("Learning cancelled", "已取消按鍵設定"); requestUpdate();
    } else if (view != View::Menu) {
      if (view == View::Scan) bleturner::scan(0);
      {
        RenderLock lock(*this);
        view = View::Menu; selected = 0; note.clear();
      }
      refresh(); requestUpdate();
    } else finish();
    return;
  }
  if (mappedInput.wasPressed(B::Up) || mappedInput.wasPressed(B::Left)) {
    RenderLock lock(*this); if (!rows.empty()) selected = selected ? selected - 1 : rows.size() - 1; requestUpdate();
  }
  if (mappedInput.wasPressed(B::Down) || mappedInput.wasPressed(B::Right)) {
    RenderLock lock(*this); if (!rows.empty()) selected = (selected + 1) % rows.size(); requestUpdate();
  }
  if (mappedInput.wasPressed(B::Confirm) && learning == bleturner::Action::None) activate();
  if (bleturner::service()) { SETTINGS.saveToFile(); note = label("Remote connected", "遙控器已連線"); requestUpdate(); }
  learnKey();
  if (millis() - refreshedAt >= 500) { refreshedAt = millis(); refresh(); }
}
void BleSettingsActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const char* title = view == View::Scan ? label("Scan for remotes", "搜尋遙控器")
      : view == View::Paired ? label("Paired remotes", "已配對遙控器")
      : view == View::Mapping ? label("Button mappings", "按鍵設定") : tr(STR_BLE_REMOTE);
  renderer.drawText(UI_10_FONT_ID, 12, 12, title);
  const auto split = renderedNote.find(" | ");
  const auto statusText = renderedNote.substr(0, split);
  renderer.drawText(UI_10_FONT_ID, 12, 38, renderer.truncatedText(UI_10_FONT_ID, statusText.c_str(), renderer.getScreenWidth() - 24).c_str());
  if (split != std::string::npos) {
    const auto feedback = renderedNote.substr(split + 3);
    renderer.drawText(UI_10_FONT_ID, 12, 64, renderer.truncatedText(UI_10_FONT_ID, feedback.c_str(), renderer.getScreenWidth() - 24).c_str());
  }
  const int height = renderer.getLineHeight(UI_10_FONT_ID) + 8;
  const int count = (renderer.getScreenHeight() - 140) / height;
  const size_t start = count > 0 ? (selected / count) * count : 0;
  for (int j = 0; j < count && start + j < rows.size(); ++j) {
    const std::string text = (start + j == selected ? "> " : "  ") + rows[start + j].text;
    if (start + j == selected) renderer.drawRect(6, 98 + j * height, renderer.getScreenWidth() - 12, height, 1, true);
    renderer.drawText(UI_10_FONT_ID, 12, 100 + j * height, renderer.truncatedText(UI_10_FONT_ID, text.c_str(), renderer.getScreenWidth() - 24).c_str());
  }
  renderer.drawText(UI_10_FONT_ID, 12, renderer.getScreenHeight() - 25, label("Back: return   OK: select", "返回：上一層　確認：選擇"));
  renderer.displayBuffer();
}
