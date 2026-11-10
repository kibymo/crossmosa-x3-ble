#include "I18n.h"
#include <cassert>
#include <cstring>
#include <iostream>
int main() {
  assert(getLanguageCount() == 2);
  auto& i = I18n::getInstance();
  assert(I18n::languageFromCode("TC") == Language::TC);
  i.setLanguage(Language::TC);
  assert(std::strcmp(i.get(StrId::STR_SETTINGS_TITLE), "設定") == 0);
  assert(std::strcmp(i.get(StrId::STR_BLE_REMOTE), "藍牙翻頁遙控器") == 0);
  for (unsigned n=0; n<static_cast<unsigned>(StrId::_COUNT); ++n) {
    assert(std::strcmp(i.get(static_cast<StrId>(n)), "???") != 0);
  }
  assert(std::strcmp(i.get(StrId::STR_GO_TO_BOOK_PERCENT), "全書進度") == 0);
  assert(std::strcmp(i.get(StrId::STR_GO_TO_CHAPTER_PERCENT), "本章進度") == 0);
  assert(std::strcmp(i.get(StrId::STR_CHAPTER_PROGRESS_PERCENTAGE), "本章進度百分比") == 0);
  i.setLanguage(Language::EN);
  assert(std::strcmp(i.get(StrId::STR_SETTINGS_TITLE), "Settings") == 0);
  assert(std::strcmp(i.get(StrId::STR_GO_TO_BOOK_PERCENT), "Book progress") == 0);
  assert(std::strcmp(i.get(StrId::STR_GO_TO_CHAPTER_PERCENT), "Chapter progress") == 0);
  assert(std::strcmp(i.get(StrId::STR_CHAPTER_PROGRESS_PERCENTAGE), "Chapter Progress Percentage") == 0);
  std::cout << "Chinese and English language switching and all generated keys passed\n";
}
