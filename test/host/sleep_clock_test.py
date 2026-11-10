"""Exercise production sleep dispatch and RTC rendering without an SD card."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[2]
source = (root / 'src/activities/boot_sleep/SleepActivity.cpp').read_text()
def function(signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]
code = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <cstring>
#include <vector>
namespace EpdFontFamily {enum {BOLD};}
namespace HalDisplay {enum {HALF_REFRESH};}
constexpr int UI_12_FONT_ID=12,STR_ENTERING_SLEEP=1;
const char* tr(int){return "sleep";}
struct GfxRenderer {
 enum Orientation {Portrait,Landscape}; enum {BW};
 Orientation orientation=Landscape; int clears=0,displays=0,mode=-1;
 std::string text; int font=0,y=0;
 void setOrientation(Orientation o){orientation=o;}
 void setRenderMode(int m){mode=m;}
 int getScreenHeight()const{return 792;}
 void clearScreen(){++clears;text.clear();}
 void drawCenteredText(int f,int v,const char* t){font=f;y=v;text=t;}
 void displayBuffer(int){++displays;}
};
struct Activity {void onEnter(){}};
struct CrossPointSettings {enum SLEEP_SCREEN_MODE {BLANK,CUSTOM,COVER,COVER_CUSTOM,LIGHT};
 int sleepScreen=CUSTOM,orientation=0;uint8_t clockUtcOffsetQ=80,clockFormat=0;
} SETTINGS;
struct {bool lastSleepFromReader=false;} APP_STATE;
struct {void drawPopup(GfxRenderer&,const char*){}} GUI;
namespace NvsStore {
 std::vector<uint8_t> saved;int writes=0;
 bool getBlob(const char*,void* out,size_t* size){if(saved.size()!=*size)return false;memcpy(out,saved.data(),*size);return true;}
 bool putBlob(const char*,const void* in,size_t size){auto p=static_cast<const uint8_t*>(in);saved.assign(p,p+size);++writes;return true;}
}
void sleepClockPreferences();
namespace ReaderUtils {void applyOrientation(GfxRenderer&,int){}}
struct {
 bool mounted=true,present=true;int reads=0;
 bool ready(){return mounted;}
 bool readCardId(uint8_t*){++reads;return present;}
} Storage;
struct {
 bool valid=true;uint8_t offset=0;bool twelve=false;
 bool formatTime(char* out,size_t n,uint8_t q,bool h){offset=q;twelve=h;if(!valid)return false;snprintf(out,n,"%s",h?"8:45 PM":"20:45");return true;}
} halClock;
struct SleepActivity:Activity {
 GfxRenderer& renderer;mutable int route=0;static bool skipEnteringPopup;
 explicit SleepActivity(GfxRenderer& r):renderer(r){}
 void onEnter();void renderClockSleepScreen()const;
 void renderBlankSleepScreen()const{route=1;}
 void renderCustomSleepScreen()const{route=2;}
 void renderCoverSleepScreen()const{route=3;}
 void renderDefaultSleepScreen()const{route=4;}
};
bool SleepActivity::skipEnteringPopup=false;
'''
code += function('void sleepClockPreferences()')
code += function('void SleepActivity::onEnter()')
code += function('void SleepActivity::renderClockSleepScreen()')
code += r'''
int main(){
 Storage.mounted=true;SETTINGS.clockUtcOffsetQ=80;SETTINGS.clockFormat=1;
 sleepClockPreferences();assert(NvsStore::writes==1);
 sleepClockPreferences();assert(NvsStore::writes==1);
 Storage.mounted=false;SETTINGS.clockUtcOffsetQ=48;SETTINGS.clockFormat=0;
 sleepClockPreferences();assert(SETTINGS.clockUtcOffsetQ==80&&SETTINGS.clockFormat==1&&NvsStore::writes==1);
 NvsStore::saved={1,255,0};SETTINGS.clockUtcOffsetQ=48;sleepClockPreferences();assert(SETTINGS.clockUtcOffsetQ==48);
 NvsStore::saved.clear();SETTINGS.clockUtcOffsetQ=80;SETTINGS.clockFormat=0;

 for(int mode=0;mode<=4;++mode)for(bool mounted:{false,true})for(bool reader:{false,true}){
  SETTINGS.sleepScreen=mode;Storage.mounted=mounted;Storage.present=false;Storage.reads=0;APP_STATE.lastSleepFromReader=reader;
  GfxRenderer r;SleepActivity s(r);s.onEnter();
  assert(s.route==0&&r.text=="20:45"&&r.displays==1&&r.clears==1&&r.mode==GfxRenderer::BW);
  assert(Storage.reads==(mounted?1:0));assert(halClock.offset==80&&!halClock.twelve);
 }
 Storage.mounted=Storage.present=true;APP_STATE.lastSleepFromReader=false;
 for(int mode=0;mode<=4;++mode){SETTINGS.sleepScreen=mode;GfxRenderer r;SleepActivity s(r);s.onEnter();
  const int expected[]={1,2,3,2,4};assert(s.route==expected[mode]&&r.displays==0);}
 SETTINGS.sleepScreen=CrossPointSettings::COVER_CUSTOM;APP_STATE.lastSleepFromReader=true;
 {GfxRenderer r;SleepActivity s(r);s.onEnter();assert(s.route==3);}
 {SETTINGS.clockFormat=1;GfxRenderer r;SleepActivity s(r);s.renderClockSleepScreen();assert(r.text=="8:45 PM"&&halClock.twelve);}
 {halClock.valid=false;GfxRenderer r;SleepActivity s(r);s.renderClockSleepScreen();assert(r.text=="--:--"&&r.displays==1);}
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp)
    (p/'test.cpp').write_text(code)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
custom = function('void SleepActivity::renderCustomSleepScreen()')
assert custom.rstrip().endswith('renderClockSleepScreen();\n}')
print('PASS production sleep dispatch: unmounted/removed SD, all modes, reader/home orientation, valid SD routing; persistent clock preferences and unchanged-write suppression; RTC 24/12h, timezone, invalid clock placeholder; custom image exhaustion falls back to clock')

main_source = (root / 'src/main.cpp').read_text()
start = main_source.index('  const bool willTryLightSleep =')
policy = main_source[start:main_source.index(';', start)+1]
policy_code = '#include <cassert>\nint main(){for(bool sleepCardAvailable:{false,true}){struct{bool supportsLightSleep(){return true;}}activityManager;struct{int getMode(){return 0;}}WiFi;bool fromTimeout=false,batteryOkForLightSleep=true;const int WIFI_MODE_NULL=0;auto lightSleepEnabled=[](){return true;};' + policy + 'assert(willTryLightSleep==sleepCardAvailable);}}'
policy_code = '#include <initializer_list>\n' + policy_code
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp)
    (p/'policy.cpp').write_text(policy_code)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(p/'policy.cpp'),'-o',str(p/'policy')],check=True)
    subprocess.run([str(p/'policy')],check=True)
print('PASS production light-sleep policy: absent card uses deep sleep; present card keeps existing eligibility')
