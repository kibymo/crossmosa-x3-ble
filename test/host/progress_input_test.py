from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'src/activities/reader/EpubReaderMenuActivity.cpp').read_text()
def block(token):
 a=s.index(token);b=s.index('{',a)+1;d=1
 while d:
  d+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
gate=block('if (popupClosing)')
callback=block('optionPopup.show(StrId::STR_GO_TO_PERCENT').split('[this](int idx) {',1)[1].rsplit('}',1)[0]
selector=(root/'src/activities/reader/EpubReaderPercentSelectionActivity.cpp').read_text()
start=selector.index('  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm))');end=selector.index('\n  }',start)+4
confirm=selector[start:end]
code='''
#include <cassert>
#include <initializer_list>
struct MappedInputManager {enum class Button {Back,Confirm};bool held=false,release=false,back=false;bool isPressed(Button b){return b==Button::Confirm&&held;}bool wasReleased(Button b){return b==Button::Confirm?release:back;}};
struct MenuResult {int action;int orientation;};
struct Menu {
 enum class MenuAction {GO_TO_PERCENT=3,GO_TO_CHAPTER_PERCENT=10};
 MappedInputManager mappedInput;bool popupClosing=false,finished=false;int pendingProgressAction=-1,pendingOrientation=0,result=-1;
 void finish(){finished=true;}void setResult(MenuResult r){result=r.action;}
 void choose(int idx){CALLBACK popupClosing=true;}
 void loop(){GATE}
};
struct PercentResult {int percent;};
struct Selector {
 MappedInputManager mappedInput;bool finished=false;int percent=50;
 void finish(){finished=true;}void setResult(PercentResult r){assert(r.percent==50);}
 void loop(){CONFIRM}
};
int main(){
 for(int scope:{0,1}) {Menu m;m.mappedInput.held=true;m.choose(scope);m.loop();assert(!m.finished);m.loop();assert(!m.finished);m.mappedInput.held=false;m.mappedInput.release=true;m.loop();assert(m.finished&&m.result==(scope?10:3));assert(m.pendingProgressAction==-1);
 // Manager installs selector after menu loop; next input update clears release.
 Selector s;s.loop();assert(!s.finished);s.mappedInput.held=true;s.loop();assert(!s.finished);
 s.mappedInput.held=false;s.mappedInput.release=true;s.loop();assert(s.finished);
 }
 Menu touch;touch.choose(1);touch.loop();assert(touch.finished&&touch.result==10);
 Menu cancel;cancel.popupClosing=true;cancel.mappedInput.back=true;cancel.loop();assert(!cancel.finished&&cancel.pendingProgressAction==-1);
}
'''.replace('CALLBACK',callback).replace('GATE',gate).replace('CONFIRM',confirm)
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'t.cpp').write_text(code);subprocess.run(['g++','-std=c++20','-Wall','-Wextra','-Werror',str(p/'t.cpp'),'-o',str(p/'t')],check=True);subprocess.run([str(p/'t')],check=True)
print('Production popup transition: held entry, release, both scopes, atomic input and cancellation passed')
