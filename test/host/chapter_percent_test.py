"""Exercise production chapter jump setup and percent landing with host fakes."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'src/activities/reader/EpubReaderActivity.cpp').read_text()
def extract(signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]
jump = extract('void EpubReaderActivity::jumpToChapterPercent(int percent)')
book_jump = extract('void EpubReaderActivity::jumpToPercent(int percent)')
landing = extract('if (pendingPercentJump && section->pageCount > 0)')
# Percent targets must pass through the full chapter build, including partial caches.
assert 'const bool cacheComplete = cacheLoaded && !section->isPartial();' in source
assert 'const bool needsFullBuild = pendingPercentJump || bleChapter;' in source
assert 'section->createSectionFile(renderSpec, popupFn)' in source
prefix = r'''
#include <algorithm>
#include <cassert>
#include <memory>
#include <optional>
#include <string>
#include <cstdio>
int clampPercent(int p){return std::clamp(p,0,100);}
struct RenderLock {template<class T> explicit RenderLock(T&){} };
struct Section {int currentPage=143,pageCount=144;};
struct Book {
 size_t getBookSize(){return 600;} int getSpineItemsCount(){return 3;}
 size_t getCumulativeSpineItemSize(int n){return n==0?100:n==1?300:600;}
};
struct EpubReaderActivity {
 std::unique_ptr<Book> epub=std::make_unique<Book>(); std::unique_ptr<Section> section=std::make_unique<Section>();
 int currentSpineIndex=7,nextPageNumber=143,cachedChapterTotalPageCount=144;
 std::optional<int> pendingPageJump=99,pendingOffsetJump=123,cachedVisibleTextOffset=456;
 std::string pendingAnchor="stale";
 bool pendingPercentJump=false;float pendingSpineProgress=0;
 void jumpToChapterPercent(int);void jumpToPercent(int);
 void land(){LANDING}
};
'''.replace('LANDING', landing)
main = r'''
int main(){
 for(int p: {-100,0,25,50,99,100,200}){
   EpubReaderActivity r;r.jumpToChapterPercent(p);
   assert(r.currentSpineIndex==7 && !r.section && r.pendingPercentJump);
   assert(!r.pendingPageJump && !r.pendingOffsetJump && !r.cachedVisibleTextOffset);
   assert(r.pendingAnchor.empty() && r.cachedChapterTotalPageCount==0 && r.nextPageNumber==0);
   assert(r.pendingSpineProgress==static_cast<float>(clampPercent(p))/100.0f);
   // Renderer supplies a completed 292-page chapter, rather than its 144-page cache watermark.
   r.section=std::make_unique<Section>();r.section->pageCount=292;r.land();
   int expected=std::min(291,static_cast<int>(static_cast<float>(clampPercent(p))/100.0f*292));
   assert(r.section->currentPage==expected && !r.pendingPercentJump && r.currentSpineIndex==7);
 }
 EpubReaderActivity single;single.jumpToChapterPercent(100);
 single.section=std::make_unique<Section>();single.section->pageCount=1;single.land();
 assert(single.section->currentPage==0);
 EpubReaderActivity noBook;noBook.epub.reset();noBook.jumpToChapterPercent(50);
 assert(noBook.section && !noBook.pendingPercentJump);
 EpubReaderActivity noSection;noSection.section.reset();noSection.jumpToChapterPercent(50);
 assert(!noSection.pendingPercentJump);
 EpubReaderActivity whole;whole.jumpToPercent(25);
 assert(whole.currentSpineIndex==1 && whole.pendingSpineProgress==0.25f && whole.pendingPercentJump);
 EpubReaderActivity start;start.jumpToPercent(0);
 assert(start.currentSpineIndex==0 && start.pendingSpineProgress==0);
 EpubReaderActivity end;end.jumpToPercent(100);
 assert(end.currentSpineIndex==2 && end.pendingSpineProgress>0.99f && end.pendingSpineProgress<1);
 puts("PASS: 10 chapter and 3 full-book navigation cases; partial cache requires full build; actual production setup and landing");
}
'''
with tempfile.TemporaryDirectory() as directory:
    cpp = Path(directory) / 'chapter.cpp'
    binary = Path(directory) / 'chapter'
    cpp.write_text(prefix + jump + book_jump + main)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
