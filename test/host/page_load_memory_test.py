"""Compile the production page-loading and failure paths with recorded heap states."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/activities/reader/EpubReaderActivity.cpp').read_text()
def function(signature):
 a=source.index(signature);b=source.index('{',a)+1;depth=1
 while depth:
  depth+=(source[b]=='{')-(source[b]=='}');b+=1
 return source[a:b]
start=source.index('    const int pageNo = section->currentPage;',source.index('void EpubReaderActivity::render('))
end=source.index('    pageLoadRetryCount = 0;  // Reset the retry counter once a page loads cleanly',start)
end=source.index('\n',end)
path=source[start:end]
code=r'''
#include <cassert>
#include <cstdint>
#include <memory>
#include <vector>
#include <utility>
#define LOG_ERR(...) ((void)0)
constexpr int STR_BUILD_LOW_MEMORY=1,STR_PAGE_LOAD_ERROR=2,UI_12_FONT_ID=12;
namespace EpdFontFamily {enum{BOLD};}
const char* tr(int id){return id==1?"memory low":"page error";}
unsigned now=0;unsigned millis(){return ++now;}
size_t freeHeap=23192,maxHeap=3956;int releases=0,clears=0,aborts=0,destroys=0;
bool warm=true;std::vector<int> loads;
struct {size_t getFreeHeap(){return freeHeap;}size_t getMaxAllocHeap(){return maxHeap;}}ESP;
struct DiagLog {template<class...T>static void line(T...) {}};
struct Page{};
struct Section {
 int currentPage=6,pageCount=66;bool low=false;int mode=0,calls=0;
 ~Section(){++destroys;}
 bool lastLoadWasLowMemory(){return low;}
 std::unique_ptr<Page> loadPage(int page){
  ++calls;loads.push_back(page);low=false;
  if(mode==2)return nullptr; // Genuine corrupt/unreadable cache.
  if(mode==1||maxHeap<4096){low=true;return nullptr;}
  if(mode==3&&calls==1){low=true;currentPage=9;return nullptr;}
  return std::make_unique<Page>();
 }
 void abandonBuild(){++aborts;}void clearCache(){++clears;}
};
struct FontCacheManager {
 size_t retained=43160;
 size_t releaseRetainedCache(){++releases;warm=false;const auto n=retained;retained=0;if(n){freeHeap=66404;maxHeap=42996;}return n;}
};
struct Renderer {
 FontCacheManager fcm;bool hasFcm=true;int cleared=0,displayed=0,errors=0;
 FontCacheManager* getFontCacheManager(){return hasFcm?&fcm:nullptr;}
 void clearScreen(){++cleared;}void displayBuffer(){++displayed;}
 void drawCenteredText(int,int,const char*,bool,int){++errors;}
};
struct {int popups=0;void drawPopup(Renderer&,const char* text){assert(std::string(text)=="memory low");++popups;}}GUI;
struct EpubReaderActivity {
 std::unique_ptr<Section> section=std::make_unique<Section>();Renderer renderer;
 uint8_t pageLoadRetryCount=0;static constexpr int MAX_PAGE_LOAD_RETRIES=3;
 int requests=0,savedPage=5,savedOffset=1000;
 void requestUpdate(){++requests;}void showPendingSyncSaveError(){}
 std::unique_ptr<Page> loadPageForRender(int pageNo);bool handlePageLoadLowMemory();void run();
};
void reset(size_t f=23192,size_t m=3956){freeHeap=f;maxHeap=m;releases=clears=aborts=destroys=0;warm=true;loads.clear();GUI.popups=0;}
'''
code=code.replace('#include <vector>','#include <vector>\n#include <string>')
code+=function('std::unique_ptr<Page> EpubReaderActivity::loadPageForRender(')
code+=function('bool EpubReaderActivity::handlePageLoadLowMemory()')
code+='void EpubReaderActivity::run(){'+path+'\n}\n'
code+=r'''
int main(){
 // Recorded failure: 3,956-byte largest block. Reclaim before the first load.
 reset();{EpubReaderActivity r;r.run();assert(loads==std::vector<int>{6}&&releases==1&&!warm);assert(r.section&&r.section->currentPage==6&&r.savedPage==5&&r.savedOffset==1000);assert(clears==0&&aborts==0&&r.requests==0&&GUI.popups==0);}
 // Healthy prewarm remains usable, avoiding extra SD reads.
 reset(90000,61428);{EpubReaderActivity r;r.run();assert(releases==0&&warm&&loads.size()==1);}
 // Total heap pressure also reclaims when the largest block alone looks adequate.
 reset(23000,20000);{EpubReaderActivity r;r.run();assert(releases==1&&r.section&&clears==0);}
 // Unanticipated allocation failure: release then retry the captured page,
 // even when navigation changes currentPage during IO.
 reset(90000,61428);{EpubReaderActivity r;r.section->mode=3;r.run();assert(loads==std::vector<int>({6,6})&&releases==1&&r.section->currentPage==9&&clears==0);}
 // Persistent OOM: exactly three scheduled retries then a memory prompt.
 reset();{EpubReaderActivity r;r.section->mode=1;auto* original=r.section.get();for(int i=0;i<4;++i)r.run();assert(r.requests==3&&GUI.popups==1&&r.pageLoadRetryCount==3);assert(r.section.get()==original&&clears==0&&aborts==0&&destroys==0&&r.section->currentPage==6&&r.savedPage==5&&r.savedOffset==1000);r.run();assert(r.requests==3&&GUI.popups==2&&r.pageLoadRetryCount==3&&clears==0);r.section->mode=0;r.run();assert(r.section.get()==original&&clears==0&&r.pageLoadRetryCount==0);}
 // With no reclaimable data or no manager, OOM still cannot delete a cache.
 reset();{EpubReaderActivity r;r.renderer.fcm.retained=0;r.run();assert(r.requests==1&&loads.size()==1&&clears==0&&r.section);}
 reset();{EpubReaderActivity r;r.renderer.hasFcm=false;for(int i=0;i<4;++i)r.run();assert(releases==0&&r.requests==3&&GUI.popups==1&&r.section&&clears==0);}
 // Actual corrupt/unreadable data retains its original bounded rebuild path.
 reset(90000,61428);{EpubReaderActivity r;r.section->mode=2;r.run();assert(!r.section&&clears==1&&aborts==1&&r.requests==1&&GUI.popups==0&&releases==0);}
 reset(90000,61428);{EpubReaderActivity r;r.pageLoadRetryCount=3;r.section->mode=2;r.run();assert(!r.section&&r.renderer.errors==1&&r.requests==0&&clears==1);}
 // A successful load resets an earlier retry count.
 reset(90000,61428);{EpubReaderActivity r;r.pageLoadRetryCount=2;r.run();assert(r.pageLoadRetryCount==0&&r.section);}
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-variable',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS 10 production page-load scenarios: recorded 3956-byte heap, healthy prewarm, total pressure, same-page recovery, persistent OOM bounded retries and retained Section/cache/progress, no manager, no releasable cache, genuine corruption and successful retry reset')
