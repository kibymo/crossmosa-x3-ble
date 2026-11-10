#pragma once
#include "activities/Activity.h"
#include <BlePageTurner.h>
#include <vector>

// The CrossPoint radio and button tables, presented through CrossMosa's Activity API.
class BleSettingsActivity final : public Activity {
  struct Row { std::string text, addr; int action; std::string peerName; };
  enum class View { Menu, Scan, Paired, Mapping };
  View view = View::Menu;
  std::vector<Row> rows;
  size_t selected = 0;
  unsigned long refreshedAt = 0, learnSince = 0;
  bleturner::Action learning = bleturner::Action::None;
  std::string learnPeer;
  uint32_t learnedCode = 0, pressedAt = 0;
  std::string note, renderedNote;
  bool previousDiagForced = false;
  bool lastConnected = false;
  bool startWithDiagnostics();
  void refresh();
  void activate();
  void learnKey();
  void keepLearned(bool hold);
 public:
  BleSettingsActivity(GfxRenderer& r, MappedInputManager& i) : Activity("BleSettings", r, i) {}
  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;
  bool preventAutoSleep() override { return true; }
  bool supportsLightSleep() const override { return false; }
};
