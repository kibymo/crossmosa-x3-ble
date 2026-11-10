from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
def extract(s,token):
 a=s.index(token);b=s.index('{',a)+1;d=1
 while d:
  d+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
reader=(root/'src/activities/reader/EpubReaderActivity.cpp').read_text()
prepare=extract(reader,'void EpubReaderActivity::prepareForBle()')
assert 'suspendBuild()' not in prepare
policy=reader[reader.index('const bool bleChapter ='):reader.index('if (bleChapter) DiagLog')]
power=extract((root/'lib/hal/HalPowerManager.cpp').read_text(),'void HalPowerManager::setPowerSaving(')
main=(root/'src/main.cpp').read_text()
a=main.index('    const bool stableBle =');b=main.index(';',a)+1
stable=main[a:b]
code=r'''
#include <algorithm>
#include <cassert>
#include <memory>
#define LOG_DBG(...) ((void)0)
constexpr int WIFI_MODE_NULL=0;
int frequency=160;
int getCpuFrequencyMhz(){return frequency;}bool setCpuFrequencyMhz(int f){frequency=f;return true;}
struct Wifi {int mode=0;int getMode(){return mode;}} WiFi;
struct HalPowerManager {
 enum LockMode {None,NormalSpeed};LockMode currentLockMode=None;
 int normalFreq=160;bool isLowPower=false;static constexpr int LOW_POWER_FREQ=10;
 void setPowerSaving(bool enabled,int minimumFrequency=0);
};
@POWER@
struct Section {int currentPage=254;bool partial=true,building=false;bool isPartial(){return partial;}bool isBuilding(){return building;}};
struct EpubReaderActivity {
 std::unique_ptr<Section> section=std::make_unique<Section>();int nextPageNumber=-1;bool update=false;
 void stopNextChapterPrebuild(const char*){}void requestUpdate(){update=true;}void prepareForBle();
};
PREPARE
bool full(bool enabled,bool chosen,bool pendingPercentJump){
 struct {struct {bool enabled;const char* peerAddr;} ble;} SETTINGS{{enabled,chosen?"peer":""}};
 POLICY
 return needsFullBuild;
}
struct Status {bool connected,starting,stopping,scanning,connecting;};
bool stableConnection(Status blePower){@STABLE@ return stableBle;}
int main(){
 assert(stableConnection({true,false,false,false,false}));
 assert(!stableConnection({false,false,false,false,false}));
 assert(!stableConnection({true,true,false,false,false}));
 assert(!stableConnection({true,false,true,false,false}));
 assert(!stableConnection({true,false,false,true,false}));
 assert(!stableConnection({true,false,false,false,true}));
 assert(full(true,true,false));assert(full(true,true,true));assert(!full(false,true,false));assert(!full(true,false,false));assert(full(false,false,true));
 EpubReaderActivity r;r.prepareForBle();assert(!r.section&&r.update&&r.nextPageNumber==254);
 EpubReaderActivity complete;complete.section->partial=false;complete.prepareForBle();assert(complete.section&&!complete.update);
 EpubReaderActivity active;active.section->building=true;active.prepareForBle();assert(active.section&&active.section->building&&!active.update);
 HalPowerManager p;p.setPowerSaving(true,80);assert(frequency==80);p.setPowerSaving(false);assert(frequency==160);
 p.setPowerSaving(true);assert(frequency==10);p.setPowerSaving(true,80);assert(frequency==80);
 WiFi.mode=1;p.setPowerSaving(true,80);assert(frequency==160);WiFi.mode=0;
 p.currentLockMode=HalPowerManager::NormalSpeed;p.setPowerSaving(true,80);assert(frequency==160);
 p.currentLockMode=HalPowerManager::None;p.setPowerSaving(true,80);assert(frequency==80);
 p.normalFreq=0;p.setPowerSaving(false);assert(frequency==80);
}
'''.replace('@POWER@',power).replace('PREPARE',prepare).replace('POLICY',policy).replace('@STABLE@',stable)
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'t.cpp').write_text(code);subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'t.cpp'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
print('PASS: production chapter policy, partial re-entry position, complete/active builders, BLE frequency floor, restore, legacy idle, Wi-Fi and render lock guards')
