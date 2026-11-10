#pragma once

#include <I18n.h>

#include "MappedInputManager.h"
#include "activities/Activity.h"
#include "util/ButtonNavigator.h"

class EpubReaderPercentSelectionActivity final : public Activity {
 public:
  // Slider-style percent selector for jumping within a book.
  explicit EpubReaderPercentSelectionActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                              const int initialPercent, const StrId title = StrId::STR_GO_TO_PERCENT)
      : Activity("EpubReaderPercentSelection", renderer, mappedInput), percent(initialPercent), title(title) {}

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  // Current percent value (0-100) shown on the slider.
  int percent = 0;
  const StrId title;

  // True while a touch that landed on the slider bar is being dragged.
  bool draggingBar = false;

  ButtonNavigator buttonNavigator;

  // Change the current percent by a delta and clamp within bounds.
  void adjustPercent(int delta);
};
