"""Compile the actual reader/host functions against minimal host fakes."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

def function(path, signature):
    text = (ROOT / path).read_text()
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

page_turn = function('src/activities/reader/EpubReaderActivity.cpp',
                     'void EpubReaderActivity::pageTurn(bool isForwardTurn)')
restart = function('src/main.cpp', 'void restartIntoBook()')
fakes = r'''
#include <memory>
#include <limits>
#include <cassert>
#include <cstdio>
#define LOG_ERR(...) ((void)0)
bool locked=false, lockAvailable=true, deepSleepInProgress=false;
struct RenderLock {
 enum class Mode { Try };
 bool owned;
 explicit RenderLock(Mode):owned(lockAvailable){if(owned) locked=true;}
 template<class T> explicit RenderLock(T&):owned(true){assert(!locked);locked=true;}
 ~RenderLock(){if(owned) locked=false;}
 bool ownsLock() const{return owned;}
};
struct Section {
 int currentPage=143,pageCount=144; bool building=false,partial=true;
 bool isBuilding(){return building;} bool isPartial(){return partial;}
};
unsigned long millis(){return 1;}
struct EpubReaderActivity {
 std::unique_ptr<Section> section=std::make_unique<Section>();
 int nextPageNumber=0,currentSpineIndex=1,pendingPageJump=0;
 unsigned long lastPageTurnTime=0; bool nextBuildTurnSinceTick_=false;
 void requestUpdate(){} void pageTurn(bool);
};
struct Manager {
 bool reader=true; unsigned failures=0,flushes=0;
 bool currentIsReaderActivity(){return reader;}
 unsigned flushProgress(){assert(locked);++flushes;return failures;}
} activityManager;
struct State {unsigned saves=0;bool ok=true;bool saveDurable(){assert(locked);++saves;return ok;}} APP_STATE;
struct DiagLog {static void line(const char*){}};
unsigned reboots=0;
void silentRestartToReader(){assert(locked);assert(APP_STATE.saves);++reboots;}
'''
checks = r'''
int main(){
 EpubReaderActivity p;p.pageTurn(true);
 assert(p.currentSpineIndex==1 && p.section && p.section->currentPage==144);
 EpubReaderActivity done;done.section->partial=false;done.pageTurn(true);
 assert(done.currentSpineIndex==2 && !done.section);
 EpubReaderActivity active;active.section->building=true;active.pageTurn(true);
 assert(active.currentSpineIndex==1 && active.section->currentPage==144);
 EpubReaderActivity mid;mid.section->currentPage=142;mid.pageTurn(true);
 assert(mid.currentSpineIndex==1 && mid.section->currentPage==143);
 EpubReaderActivity back;back.pageTurn(false);
 assert(back.currentSpineIndex==1 && back.section->currentPage==142);
 EpubReaderActivity previous;previous.section->currentPage=0;previous.pageTurn(false);
 assert(previous.currentSpineIndex==0 && !previous.section);
 lockAvailable=false;restartIntoBook();assert(reboots==0 && activityManager.flushes==0);
 lockAvailable=true;deepSleepInProgress=true;restartIntoBook();assert(reboots==0);
 deepSleepInProgress=false;activityManager.reader=false;restartIntoBook();assert(reboots==0);
 activityManager.reader=true;activityManager.failures=1;restartIntoBook();
 assert(reboots==0 && APP_STATE.saves==0);
 activityManager.failures=0;APP_STATE.ok=false;restartIntoBook();assert(reboots==0);
 APP_STATE.ok=true;restartIntoBook();assert(reboots==1 && APP_STATE.saves==2);
 puts("PASS: 6 navigation cases and 6 recovery cases (actual production functions)");
}
'''
with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / 'test.cpp'
    binary = Path(directory) / 'test'
    source.write_text(fakes + page_turn + '\n' + restart + checks)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
