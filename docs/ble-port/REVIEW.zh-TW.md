# v3.27 review

使用者 v3.26 diag.log 兩次記錄 free=23,192 / largest=3,956 bytes，Section::loadPage 的 4 KiB 地板拒絕後連續重試沒有任何回收，最後穿透到 clearCache/reset。隨後完整重建路徑 releaseRetainedCache 釋放 43,160 bytes，堆積恢復到 free=66,404 / largest=42,996。新修正把回收移到實際顯示頁的載入入口，並將低記憶體失敗與讀檔／格式失敗分流。

loadPageForRender 在低水位時回收 retained mini cache；不卸字型、不清 advance 表、不更動排版度量。健康水位保留預熱；實際 loadPage 回報低記憶體時若還能釋放快取，只再讀一次捕捉的 pageNo，不重讀可能已被按鍵更動的 currentPage。Section 自己的 4 KiB 地板未降低。回收會透過既有機制使 warm identity 失效，後續預熱正常重建。

handlePageLoadLowMemory 最多 requestUpdate 三次，之後使用既有記憶體不足字串提示，等待操作；重試計數維持在上限，直到實際成功載入才清除，避免無法載入時被判成正常已顯示頁；所有低記憶體出口在一般清快取分支之前 return，保留 Section、currentPage、SD 快取與既有持久化進度。載入成功前不進入更新 offset、儲存閱讀進度的路徑。真實 I/O／格式失敗仍走原本有限重建，並未把讀不到的檔案無限重試。沒有新增整頁 BMP／SD swap，也不改 BLE 門檻或睡眠政策。

測試使用正式載入 helper、低記憶體 handler 及 render 裡的完整載入失敗分流，加桌面檔案／字型／堆積 adapter。仍無法取代真實 SD 字型、注音、圖片頁及連續跨章的實機驗證。低水位釋放預熱點陣可能增加某些頁面的 SD 字型讀取；本版優先避免載入失敗與錯誤刪除索引，不宣稱速度或省電提升。

# v3.26 review

Storage.ready 只代表掛載初始化狀態，不能證明卡還插著；休眠入口另讀 CID，失敗就直接走不使用檔案的時鐘畫面。兩條休眠路徑（淺睡與真關機）都呼叫 SleepActivity::onEnter，因此共用同一分流。enterDeepSleep 的淺睡資格另要求當下卡片可讀；沒有卡直接深睡，避免淺睡計時到時 rebootIfCardChanged 的保護性重啟最後停在缺卡開機畫面。睡後才換卡的既有重啟保護仍保留。自訂桌布列舉與重試耗盡後也用時鐘代替品牌預設圖。

時鐘使用 HalClock::formatTime 與 UI_12_FONT_ID（內建 UI 字型），沿用可信時間檢查、時區與格式。畫前重設 BW、清空 framebuffer，以 HALF_REFRESH 顯示一次。沒有額外計時喚醒或 Wi-Fi 校時。正常開機後的休眠會將時區／格式三位元組版本資料備份到 NVS，同值不重寫；未掛載卡時只讀備份，不嘗試讀 settings.json。無備份或資料不合法時維持預設。開機缺卡提示及安全換卡重啟保護保留，沒有把缺卡當成可以閱讀。

# v3.25 review

以使用者此次 v3.24 crash report 的原 ELF 解碼，operator new → vector<string> realloc append → ParsedTextVertical.cpp:881（colWords.push_back）；當時已停止 BLE。新章 spine=3 在重啟後用同一份書成功建出 321 頁，支持工作集／碎片化壓力，不支持直接判定書籍損壞或待機降頻為根因。

修正在 full-build 起點釋放可重建的 retained font cache，沒有卸載字型或修改度量；ActivityManager 已在呼叫 render 前等待 BLE start/stop，若仍持有 radio 就重試，不會進入索引。沿用 frame buffer loan。

直排完整函式保留原分欄、尾欄、token 消耗、visible offset 與注音來源對應。縮小批次，按實際逐字筆數 reserve。此編譯單元單獨使用 -fexceptions；編譯期 __EXCEPTIONS 檢查確保恢復邊界不會被靜默省掉，其他單元維持 -fno-exceptions。bad_alloc 在函式邊界內處理，暫存先解構，再 latch OOM 並清理輸入，避免既有無進展迴圈。無效 TextBlock 也 latch；不會靜默提交缺欄章節。既有 parser hasOom/latchBuildAborted 與 Section suspendBuild/finalizeBuild 失敗流程接手，保留可用舊 partial，未更動進度儲存或配對。

本次測試使用實際直排完整函式及 VerticalColumns/VerticalText，字型度量、TextBlock 和注音引擎為桌面 adapter；這不是實機字型與注音引擎的完整測試。仍需實機跨章、長章、注音與 BLE 恢復驗證。catch 僅針對直排範圍配置失敗，不能宣稱攔截整個韌體所有 OOM。

# v3.24 review

依 diag.log 的 page=254/cache=262/partial=1 及 BLE 記憶體拒絕紀錄，移除為連線而 suspend 章節建置的循環。使用現有完整章節寫入路徑，其 FrameBufferLoan 與 OOM 處理保留；完整快取不重建，普通閱讀仍漸進。prepareForBle 在已選遙控器的 shown-page 鎖定範圍內，舊 partial 回存 currentPage 至 nextPageNumber 再請求 render，沒有更動配對、進度及頁事件。
CPU 降頻僅穩定 connected，起停／搜尋／連線作業不符合；HAL 以 minimumFrequency 把 BLE 頻率下限保留在 80 MHz，Wi-Fi 與 NormalSpeed lock 照舊阻止省電。主迴圈操作恢復全速；不更動 BLE 連線參數或底層睡眠。節電幅度待實機測量。

# v3.23 review

原 SMALL_FONT_ID 註冊 notosans_8_regular，不包含「本章：」三字。依使用者後續要求移除狀態列前綴，保留原小字型及配對的測寬／繪製呼叫。沒有變更設定頁的「本章進度百分比」名稱或百分比計算。沒有新增字型。

# v3.22 review

新增設定透過既有 SettingsList 泛用 JSON 讀寫；缺少新 key 時預設隱藏。StatusBarSpec 的文字列可見性納入新開關，因此單獨顯示本章百分比也會保留狀態列空間。共用 BaseTheme 處理所有主題，加入字串寬度後沿用標題裁切與時鐘配置。計算只用傳入的章節頁數，不配置新快取或觸發索引；EPUB partial 與 building 均明示估計。TXT 無章節時不顯示。

# v3.21 review

diag.log 的 v3.20 區段三次顯示百分比畫面後緊接章節索引／閱讀；與按下選範圍、放開立即提交百分比的程式流程吻合。修正在範圍選單端消耗完整開啟按鍵，ActivityManager 於迴圈末切換，下圈先更新輸入後才執行選擇器。沒有變更共用輸入或 BLE 邏輯。仍須實機確認。

# v3.20 本章進度審查

在現有 GO_TO_PERCENT 選單內用 OptionPopup 選範圍，不增加主選單列數。新增動作列舉附加於尾端，既有動作值不變。原有全書百分比流程保留。
百分比滑桿重用原元件，依範圍改顯示標題；中英文字串加入現有 I18n 資料，沒有新增字型。
章內跳轉保留 currentSpineIndex，清除舊頁碼、offset、anchor 及設定重定位後走 pendingPercentJump。既有 renderer 在部分章節上先完整建立分頁，再套用百分比；完整快取可直接載入。
0% 為第一頁；100% 夾到最後一頁，不換章。章節仍依 EPUB spine 分段定義，並非保證每一 TOC 子節都獨立。

# v3.19 修正審查

## 部分快取邊界

v3.18 記錄顯示 page=143、cached=144、partial=1，接收 next 後 spine 由 1 變 2。prepareForBle() 暫停排版並釋放 parser，isBuilding() 因而為 false；pageTurn() 漏了 isPartial()，誤把快取水位當章末。
修正為在 building 或 partial 時前進同章，由 render() 既有補排流程完成。真章末、前後翻頁與建置中邊界均納入主機測試。若補排後才發現已是實際章末，既有 render() 會夾回最後實頁，再按下一頁才換章。

## BLE 恢復

restartIntoBook() 原本只記錄手動重啟提示，與 runtime 的「silent restart」訊息不一致。現已接回既有重啟續讀，先鎖定繪圖並確認進度及狀態儲存成功。runtime 的 RTC memo 防止 BLE 尚未重新啟動前連續自動重啟；BLE 成功啟動後才重新允許後續恢復。
這是碎片化恢復措施，未證明動態 RAM 保留的根因已消除，也不對總 RAM 不足強制放行。沒有修改 radio 門檻或刪除中文字型功能。

## v3.18 介面整合檢查

- 以 CrossMux a6fd569 作參考，將設定分為主選單、搜尋、已配對、按鍵設定四頁。
- 主選單開關與即時連線狀態分開呈現；狀態及操作提示分兩行，長文字按螢幕寬截斷。
- 返回先取消學習，再返回主選單，最後離開設定；離開搜尋頁停止搜尋。
- 配對使用獨立裝置名稱及位址，不再從翻譯過的顯示文字裁切名稱。
- 僅使用者選取「解除配對」列時才解除；空清單不可操作。
- 學習、重設按鍵仍檢查已連線，配對表、預設映射及 BLE 啟動保護未變更。
- 圖示僅在連線且狀態列文字區可見時畫出，納入左側群組寬度，避免與標題重疊。
- 圖示直接畫入既有 framebuffer；沒有新 framebuffer、計時器或背景刷新任務。
- 介面並未導入 CrossMux 的跳章／長按映射，不代表 v3.17 跳章及斷線已修復。

實機仍需確認各頁操作、字形、配對保留、狀態列位置及不同方向的顯示。

# v3.17-zh 自我檢查

- 以使用者實測可用的 v3.16 為基礎，只恢復 TC 翻譯與內建 CJK UI 字型。
- CROSSMOSA_LOW_RAM_UI 保留三種 SD UI 備援不載入的行為；閱讀字型照常載入，BLE 快取上限保留。
- 阿拉伯文／希伯來文雙向排序及阿拉伯文連字維持停用。BLE 記憶體保護、靜態任務、配對與單向遙控翻頁不變。
- 內建 10px regular、14px regular、14px bold 字型涵蓋 zh-hant.yaml 的 420 個 CJK 用字。罕見檔名字仍可能不在內建字庫。
- 實際 I18n.cpp / I18nStrings.cpp 主機測試確認 TC/EN 切換、設定與 BLE 翻譯，以及所有生成 key 可查詢。
- 144 項 BLE 主機測試、379 HID 檢查、5 種 panic reset 與停用 bidi 文字回退檢查通過。
- 傾斜翻頁判定未修改。
- X3 的中文介面、設定與閱讀切換、最大連續 RAM 仍需實測；靜態 RAM 與 Flash 比較另見 validation/ram-comparison.log。
