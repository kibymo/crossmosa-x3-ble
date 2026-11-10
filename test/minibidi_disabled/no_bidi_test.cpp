#include "BidiUtils.h"
#include <cassert>
#include <string>
#include <vector>
int main() {
  const char* text[] = {"English 123", "繁體中文，直排。", "e\xcc\x81", "مرحبا", "שלום", ""};
  for (const auto* s : text) {
    std::string out = "unchanged";
    assert(!BidiUtils::startsWithRtl(s));
    assert(BidiUtils::detectParagraphLevel(s, 1) == 0);
    assert(!BidiUtils::applyBidiVisual(s, out, 1));
    assert(out == "unchanged");  // false tells callers to draw the original input
  }
  assert(!BidiUtils::startsWithRtl(nullptr));
  assert(!BidiUtils::isTransparentMark(0x064B));
  std::vector<uint16_t> order{2, 1, 0};
  assert(!BidiUtils::computeVisualWordOrder({"中文", "abc", "123"}, true, order));
  assert(order.empty());
}
