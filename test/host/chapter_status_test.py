"""Compile production progress text formatting and test independent toggles."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'src/components/themes/BaseTheme.cpp').read_text()
a=s.index('    char progressStr[128];',s.index('void BaseTheme::drawStatusBar'))
b=s.index('    int progressTextWidth',a)
body=s[a:b]
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#define STR_CHAPTER_PREFIX 1
const char* tr(int){return "";}
struct Spec {bool showBookProgressPercent,showChapterPageCount,showChapterProgressPercent;};
std::string format(Spec sb,int currentPage,int pageCount,bool pageCountEstimated=false,bool hidePageCount=false) {
 float bookProgress=25;int progressDecimals=0;
 BODY
 return progressStr;
}
int main(){
 assert(format({false,false,true},50,100)=="50%");
 assert(format({true,false,true},50,100)=="25%  50%");
 assert(format({true,true,true},50,100)=="50/100  25%  50%");
 assert(format({false,true,true},50,100)=="50/100  50%");
 assert(format({true,false,false},50,100)=="25%");
 assert(format({false,false,false},50,100)=="");
 assert(format({false,false,true},1,1)=="100%");
 assert(format({false,false,true},0,100)=="0%");
 assert(format({false,false,true},500,100)=="100%");
 assert(format({false,false,true},-1,100)=="0%");
 assert(format({false,false,true},1,0)=="");
 assert(format({false,false,true},50,100,true)=="~50%");
 assert(format({false,false,true},50,100,false,true)=="");
 assert(format({true,true,true},50,100,true,true)=="25%");
}
'''.replace('BODY',body)
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'t.cpp').write_text(code);subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'t.cpp'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
settings=(root/'src/SettingsList.h').read_text()
assert '"statusBarChapterProgressPercentage"' in settings
h=(root/'src/CrossPointSettings.h').read_text()
assert 'uint8_t statusBarChapterProgressPercentage = 0;' in h
assert 'showBookProgressPercent || showChapterProgressPercent || showsTitle()' in h
reader=(root/'src/activities/reader/EpubReaderActivity.cpp').read_text()
assert 'section->isBuilding() || section->isPartial());' in reader
assert 'const float pageCount = section->estimatedTotalPages();' in reader
print('PASS: 14 production text cases, independent toggles, estimated marker, boundaries and TXT suppression; persistence registration and layout visibility guards')
