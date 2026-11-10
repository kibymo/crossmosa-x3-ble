from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
s=(root/'lib/EpdFont/builtinFonts/notosans_8_regular.h').read_text()
s=s.split('notosans_8_regularIntervals[] = {',1)[1].split('};',1)[0]
intervals=[tuple(int(x,16) for x in row[:2]) for row in re.findall(r'\{\s*0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+)\s*\}',s)]
for ch in '0123456789%~ /.-':
 assert any(lo<=ord(ch)<=hi for lo,hi in intervals),ch
for ch in '本章：':
 assert not any(lo<=ord(ch)<=hi for lo,hi in intervals),ch
source=(root/'src/components/themes/BaseTheme.cpp').read_text().split('void BaseTheme::drawStatusBar',1)[1]
assert 'tr(STR_CHAPTER_PREFIX)' not in source
assert 'getTextWidth(SMALL_FONT_ID, progressStr)' in source
assert 'drawText(SMALL_FONT_ID, rightClusterX - progressTextWidth, textY, progressStr)' in source
print('PASS: original small font lacks chapter prefix; every numeric status character supported; prefix absent and measurement/drawing use matching font')
