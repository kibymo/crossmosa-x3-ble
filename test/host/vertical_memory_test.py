"""Run the complete production vertical-layout function with deterministic font metrics.
Compare bounded batches with the previous batching, and inject allocation failure
at every allocation in the actual function. Hardware font/ruby engines are adapters.
"""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'lib/Epub/Epub/ParsedTextVertical.cpp').read_text()
source=re.sub(r'^#include[^\n]*\n','',source,flags=re.M)
preamble=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <functional>
#include <memory>
#include <new>
#include <string>
#include <vector>
#include "lib/Utf8/Utf8.h"
#include "lib/Epub/Epub/VerticalText.h"
#include "lib/Epub/Epub/VerticalColumns.h"
static long failAt=-1, calls=0, live=0;
static bool failArena=false;static int testEm=20;static size_t largest=100000;
void* operator new(std::size_t n) {
 if(failAt>=0 && calls++==failAt) throw std::bad_alloc();
 if(void* p=std::malloc(n?n:1)){++live;return p;}throw std::bad_alloc();
}
void operator delete(void* p) noexcept {if(p){--live;std::free(p);}}
void operator delete(void* p,std::size_t) noexcept {::operator delete(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {::operator delete(p);}
void operator delete[](void* p,std::size_t) noexcept {::operator delete(p);}
#define LOG_ERR(...) ((void)0)
#define MALLOC_CAP_DEFAULT 0
size_t heap_caps_get_free_size(int){return 200000;}
size_t heap_caps_get_largest_free_block(int){return largest;}
namespace EpdFontFamily {using Style=uint8_t;constexpr Style REGULAR=0,RUBY_CONTINUE=64;}
enum class CssTextAlign {Left,Right,Center};
struct BlockStyle {bool isRtl=false,textIndentDefined=false;int textIndent=0;CssTextAlign alignment=CssTextAlign::Right;};
namespace zhuyin {struct SwapBatch{};struct Stats {uint32_t listOom=0;};Stats swapStats(){return {};}}
uint32_t utf8NextCodepoint(const unsigned char** p){const char* q=(const char*)*p;const char* end=q+std::strlen(q);auto c=vtext::nextCodepoint(q,end);*p=(const unsigned char*)q;return c;}
void utf8AppendCodepoint(uint32_t c,std::string& s){if(c<128)s+=char(c);else if(c<2048){s+=char(192|(c>>6));s+=char(128|(c&63));}else{s+=char(224|(c>>12));s+=char(128|((c>>6)&63));s+=char(128|(c&63));}}
struct GfxRenderer {
 template<class... T>void ensureSdCardFontReady(T&&...)const{}
 int probeEmFP(int)const{return 16*testEm;}
 int getFontAscenderSize(int)const{return 18;}
 int getTextAdvanceX(int,const char* s,EpdFontFamily::Style=0)const{return int(std::strlen(s))*10;}
 int getSpaceAdvance(int,uint32_t,uint32_t,EpdFontFamily::Style)const{return 5;}
 bool getGlyphInkBox(int,uint32_t cp,EpdFontFamily::Style,int* w,int* h,int* l,int* t)const{*w=cp<128?9:18;*h=18;*l=0;*t=18;return true;}
};
namespace vtext {int32_t probeEmFP(const GfxRenderer& r,int f){return r.probeEmFP(f);}}
struct TextBlock {
 std::vector<std::string> text;std::vector<int16_t> pos;std::vector<uint16_t> cross;std::vector<uint8_t> styles;bool ok;
 TextBlock(const std::vector<std::string>& t,const std::vector<int16_t>& p,const std::vector<uint8_t>& s,const std::vector<uint8_t>&,const std::vector<uint16_t>& c,const BlockStyle&,const std::vector<std::string>&,const zhuyin::SwapBatch&):text(t),pos(p),cross(c),styles(s),ok(!failArena){}
 bool valid()const{return ok;}
};
struct ParsedText {
 bool oom_=false;std::deque<std::string> words,rubyTexts;
 std::vector<uint8_t> wordStyles;std::vector<bool> wordContinues,wordNoSpaceBefore,wordIsFocusSuffix;
 std::vector<uint32_t> offsets;BlockStyle blockStyle;bool isNaturalAlign=true,verticalIndentApplied=false;
 inline static int vertWordRotLogged=0,vertRotLogged=0,vertTcyLogged=0,vertHungLogged=0,vertIndGateLogged=0,vertHangLogged=0,vertGeoLogged=0,vertGeoKey=0;
 struct Prof {uint64_t layUs=0,layCdUs=0,layCalls=0,advUs=0;};static Prof buildProf;inline static bool buildProfInCd=false;
 static int64_t profNowUs(){return 0;}template<class...T>static void vertDiag(T...){}
 void updateNaturalAlign(){}void zhuyinAbandon(){}void zhuyinStop(bool){}
 bool zhuyinActive()const{return zy;}bool zhuyinPrepareBatch(bool){return false;}bool zy=false;
 template<class...T>size_t zhuyinCoveredColumns(T...){return 0;}
 template<class...T>zhuyin::SwapBatch zhuyinLineSwaps(T&&...){return {};}
 void zhuyinNoteBuilt(const zhuyin::SwapBatch&,uint32_t){}
 uint32_t visibleOffsetAt(size_t i)const{return i<offsets.size()?offsets[i]:0;}
 void eraseVisibleOffsetPrefix(size_t n){offsets.erase(offsets.begin(),offsets.begin()+std::min(n,offsets.size()));}
 void add(std::string s){offsets.push_back(offsets.empty()?0:offsets.back()+1);words.push_back(std::move(s));rubyTexts.emplace_back();wordStyles.push_back(0);wordContinues.push_back(false);wordNoSpaceBefore.push_back(true);wordIsFocusSuffix.push_back(false);}
 void layoutAndExtractColumns(const GfxRenderer&,int,uint16_t,const std::function<void(std::shared_ptr<TextBlock>,uint32_t,int)>&,bool);
};
ParsedText::Prof ParsedText::buildProf;
'''
section_source=(root/'lib/Epub/Epub/Section.cpp').read_text()
suspend=section_source[section_source.index('void Section::suspendBuild() {'):section_source.index('\nvoid Section::abandonBuild()',section_source.index('void Section::suspendBuild() {'))]
section_adapter=r'''
#define LOG_INF(...) ((void)0)
constexpr int SECTION_FILE_PARTIAL_VERSION=1;
struct MockParser {bool aborted=false;bool hasBuildAborted(){return aborted;}size_t parseBytesConsumed(){return 123;}void abortParse(){}};
struct MockCss{void clear(){}};
struct MockFile {bool open=true;explicit operator bool()const{return open;}void close(){open=false;}};
struct MockStorage {bool exists(const char*){return false;}void remove(const char*){}} Storage;
struct Section {
 struct Build {std::unique_ptr<MockParser> parser=std::make_unique<MockParser>();MockCss* cssParser=nullptr;bool reusedHtml=true;std::string tmpHtmlPath="tmp";uint32_t totalBytes=999;};
 std::unique_ptr<Build> build_=std::make_unique<Build>();bool buildComplete_=false,partial_=true;
 uint32_t builtPageCount_=200,partialPageCount_=100,partialBytesConsumed_=50,partialTotalBytes_=500,pageCount=100;int spineIndex=3,commits=0;
 inline static int lastPoisonAvoidedSpine=-1;MockFile file;
 std::string binTmpPath(){return "bin.tmp";}
 bool commitBuildFile(int,uint32_t,uint32_t){++commits;return true;}
 void suspendBuild();
};
'''
main=r'''
static uint64_t hash=1469598103934665603ull;static size_t cols=0,emitted=0;
void digest(std::shared_ptr<TextBlock> b,uint32_t off,int tokens){
 auto feed=[](uint64_t n){hash=(hash^n)*1099511628211ull;};feed(off);feed(tokens);feed(b->text.size());
 for(size_t i=0;i<b->text.size();++i){for(unsigned char c:b->text[i])feed(c);feed(b->pos[i]);feed(b->cross[i]);feed(b->styles[i]);++emitted;}++cols;
}
void fill(ParsedText& p,int n,int mode){for(int i=0;i<n;++i){
 if(mode==1 && i%7==0)p.add("第10章");
 else if(mode==2 && i%13==0)p.add("FBI");
 else if(mode==3 && i%11==0)p.add("。！？");
 else p.add(i%2?"文":"字");
}}
int main(int argc,char**){
 GfxRenderer r;
 {Section s;s.build_->parser->aborted=true;s.suspendBuild();assert(s.commits==0 && s.pageCount==100 && s.partial_ && !s.build_ && !s.buildComplete_);}
 {Section s;s.partial_=false;s.build_->parser->aborted=true;s.suspendBuild();assert(s.commits==0 && s.pageCount==0 && !s.partial_ && !s.build_);}
 {Section s;s.suspendBuild();assert(s.commits==1 && s.pageCount==200 && s.partial_ && !s.buildComplete_);}
 if(argc>1){long injections=0;
  for(bool zy:{false,true}){
   long count=0;{ParsedText p;fill(p,420,1);p.zy=zy;calls=0;failAt=100000000;
    p.layoutAndExtractColumns(r,0,320,[](auto,uint32_t,int){},true);failAt=-1;count=calls;assert(!p.oom_);}
   for(long k=0;k<count;++k){const long before=live;{
    ParsedText p;fill(p,420,1);p.zy=zy;calls=0;failAt=k;
    p.layoutAndExtractColumns(r,0,320,[](auto,uint32_t,int){},true);
    failAt=-1;assert(calls>k);++injections;
    if(p.oom_)assert(p.words.empty() && p.wordStyles.empty() && p.offsets.empty());
   }assert(live==before);}
  }
  {ParsedText p;fill(p,100,0);failArena=true;p.layoutAndExtractColumns(r,0,320,[](auto,uint32_t,int){assert(false);},true);failArena=false;assert(p.oom_ && p.words.empty());}
  {ParsedText p;fill(p,100,0);largest=4095;p.layoutAndExtractColumns(r,0,320,[](auto,uint32_t,int){assert(false);},true);largest=100000;assert(p.oom_ && p.words.empty());}
  std::printf("PASS %ld injected allocation failures, arena rejection and 4 KiB floor; scratch released, OOM latched and inputs cleared\n",injections);return 0;
 }
 for(int em:{10,20,28,46})for(int mode=0;mode<4;++mode)for(int n:{1,15,16,17,191,192,193,799,800,801,3500})for(bool soft:{false,true}){
  testEm=em;ParsedText p;fill(p,n,mode);p.zy=(mode%2);p.layoutAndExtractColumns(r,0,320,digest,!soft);
  if(soft){for(int i=0;i<230;++i)p.add("字");p.layoutAndExtractColumns(r,0,320,digest,true);}
  assert(!p.oom_ && p.words.empty());
 }
 std::printf("%llu %zu %zu\n",(unsigned long long)hash,cols,emitted);
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)
 # Same production code, change only the batch sizes to the previous release.
 baseline=subprocess.check_output(['git','show','HEAD:lib/Epub/Epub/ParsedTextVertical.cpp'],cwd=root,text=True)
 baseline=re.sub(r'^#include[^\n]*\n','',baseline,flags=re.M)
 results=[]
 for name,body in [('bounded',source),('previous_batch',baseline)]:
  (p/f'{name}.cpp').write_text(preamble+body+section_adapter+suspend+main)
  subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-I',str(root),str(p/f'{name}.cpp'),'-o',str(p/name)],check=True)
  results.append(subprocess.check_output([str(p/name)],text=True).strip())
 assert results[0]==results[1],results
 print('PASS complete production vertical layout, 352 batch-boundary and soft-flush scenarios: same text, coordinates, styles, offsets and token accounting as previous batch sizes:',results[0])
 subprocess.run([str(p/'bounded'),'faults'],check=True)
# Verify the sticky OOM follows both parser error paths and avoids full-cache commit.
parser=(root/'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text()
assert parser.count('currentTextBlock->hasOom()')>=3
section=(root/'lib/Epub/Epub/Section.cpp').read_text()
assert 'if (!build_->parser->finishParse())' in section
assert 'if (build_->parser->hasBuildAborted())' in section
print('PASS production Section::suspendBuild: aborted tmp never committed, existing partial preserved, fresh failure leaves no cache; successful suspension still persists complete pages. Parser OOM guards present.')
