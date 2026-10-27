# tw-dispatch-kit 公開前檢查（RELEASE_CHECK）

- 檢查日：2026-10-27
- 目前可見度：**PRIVATE**（等主 session／店長驗收後才決定是否公開）
- 來源：已去品牌的線上示範版，白名單複製；原示範站與正式營運系統都沒有改動
- 測試環境：Windows 11、Python 3.14.2 與 3.10.22；GitHub Actions（Ubuntu／Windows × Python 3.10／3.12）

## 結論先講

**建議可以公開，但要店長確認三件事**（見最後「要店長決定」）。八道閘門沒有阻斷項目；第 3 道「真實串接沒實測」與第 5 道「夥伴流程以外的效能、瀏覽器相容沒做」是已知限制。

| # | 閘門 | 結果 | 一句話 |
|---|---|---|---|
| 1 | 需求與設計 | ✅ | 角色權限、外部服務關閉時的退路、示範與自架兩種模式都寫在 README／SECURITY.md |
| 2 | 程式本身 | ✅ | 38 項測試全過；pyflakes 無未定義名稱；相依套件 0 個已知漏洞 |
| 3 | 串接 | ⚠️ | LINE／LINE Pay／Google／Anthropic 只驗證「沒金鑰不連線、示範版連不出去」，真實帳號沒實測 |
| 4 | 完成使用者任務 | ✅ | 估價 → 報價 → 簽收成立工單、必填空白、過去日期、竄改條款、重複送出都用 HTTP 實測 |
| 5 | 安全／效能／環境 | ⚠️ | 越權（夥伴打管理 API、客服看／改夥伴銀行帳戶）、冒用電話重新應徵、CSRF、Origin、停止端點都測過；效能壓測與手機實機瀏覽器沒有做 |
| 6 | 資料 | ✅ | 備份檔實際還原並啟動 server，筆數一致；重建示範資料不刪舊檔 |
| 7 | 交付版本 | ✅ | 全新 git 歷史（不含來源系統任何歷史）；乾淨環境照 README 安裝可跑 |
| 8 | 出事能恢復 | ✅ | 每日自動備份保留 30 份、還原已演練；錯誤記錄在 log；示範資料一行指令重建 |

## 去識別化

| 項目 | 結果 |
|---|---|
| 白名單複製 | 只放 `app/*.py`、`app/web/*`、`schema*.sql`、`demo_server.py`、`seed_demo.py`、`demo_intro.html`；沒有 `data/`、`backups/`、`*.db`、`*.bk*`、`__pycache__`、log、`online.flag` |
| 指定字樣 grep | 品牌名、公司名、負責人與合夥人姓名、我們的網域、固定 IP、內網 IP、私鑰：**0**。真實 LINE userId：**0**（唯一命中是全 0 的佔位值）。09 手機號碼：只剩示範用 `0900-000-xxx` |
| 環境變數改名 | 原本帶品牌縮寫的環境變數全部改成 `DISPATCH_*` |
| 業務線代號 | 帶有真實品牌意涵的內部代號改成中性的 `helper`（居家小幫手）、`bnb`（民宿清潔線）、公司代號 `democo` |
| 程式註解 | 約 1,300 行帶日期的註解：移除「日期＋客服／負責人／店長／稽核」前綴、內部回報單號；內部對話原話改寫成中性技術說明；客戶名、案場名、夥伴暱稱、內部帳號名改成「某客戶」「小明」這類假名或刪除 |
| 寫死的本機路徑 | 本機 AI 閘道、海巡資料庫路徑改成環境變數，預設空值＝功能關閉 |
| 寫死的對外網址 | 真實的加好友短網址、舊網站來源、伺服器 IP 都移除；對外網址改用 `DISPATCH_BASE_URL` |
| 金鑰 | 一律從 `DISPATCH_SECRET_*` 環境變數讀，預設空值；程式裡 0 個金鑰（`tests/test_config.py` 自動檢查） |
| 圖示 | 品牌圖示、文字標誌都是「示範」字樣的通用圖，沒有真實 LOGO |
| `deep_audit.py` | 見下表，命中逐筆判讀後全部是誤判或刻意保留 |

### deep_audit 命中判讀

| 命中 | 位置 | 判讀 |
|---|---|---|
| 字典「宜蘭」約 110 筆 | 地區清單、示範地址（`示範路`）、官網範例文案、地圖預設中心 | 誤判：地名。開源版預設服務區在宜蘭，README「已知限制」說明要改 `regions.py` |
| 字典「泰山」「池上」 | `web/regions.js` 全台鄉鎮清單 | 誤判：地名（新北市泰山區、臺東縣池上鄉） |
| 字典「velo」 | LINE 官方文件用語「Developers」 | 誤判 |
| 字典「留白」 | `qprint.html`、`style.css` 的版面「留白」 | 誤判：排版用語 |
| 字典「留白」＋本人姓名 | README、NOTICE、`demo_intro.html`、`web/demo-banner.js` | **刻意保留**：作者署名與「需要客製化？加 LINE @812ibtir（留白事務所，林其衞）」廣告 |
| 手機號碼 `0900-000-xxx` | `seed_demo.py`、`door.py`、`linepay.py`、`mall.html`、測試 | 誤判：示範用假號碼 |
| LINE userId／32 碼 hex | `line_bot.py` 的 `OWNER_UID = 'U000…0'` | 誤判：全 0 佔位值 |
| 文件／資料庫檔 | 本機的 `data/`、`backups/` | 執行示範產生的檔案，已被 `.gitignore` 排除，不在 repo 裡 |

## 測試證據

| 項目 | 指令 | 結果 |
|---|---|---|
| 全部測試 | `python -m unittest discover -s tests -v`（Python 3.14.2，Windows） | 38 項全過（連跑 3 次） |
| 同上 | Python 3.10.22 新 venv，只裝 `requirements.txt` | 38 項全過 |
| 3.10 語法相容 | 逐檔 `ast.parse` | 原本 `seo.py` 有 3.12 才能用的 f-string 寫法，已改寫 |
| 靜態檢查 | `pyflakes app tests` | 0 個未定義名稱；其餘 50 則是來源本來就有的「import 沒用到／被迴圈變數蓋掉」提示 |
| 相依套件漏洞 | `pip-audit -r requirements.txt` | No known vulnerabilities found |
| CI | `.github/workflows/test.yml` | 推送後結果見下方「推送後驗證」 |

### 高風險需求（實際用 HTTP 打）

| 需求 | 風險 | 測試 | 預期 | 結果 |
|---|---|---|---|---|
| 夥伴只看得到自己的工單 | 越權讀取 | worker 讀 `/api/state`，逐筆比對 `assignments.worker_id` | 全部是自己；沒有 `customers`、`workers` | ✅ `test_worker_sees_only_own_jobs` |
| 夥伴不能用管理功能 | 提權 | worker 打 `/api/quotes`、`billing`、`ledger`、`chats`、`brands`、`payhist`；POST `quote/confirm` | 全部 403 | ✅ |
| 跨站請求 | CSRF | 管理員 POST 不帶 CSRF token；外站 Origin 打估價 API | 拒絕 | ✅ |
| 停止示範 server | 外網任何人可停站 | `/__demo_stop` 帶公開 Host、`Cf-Connecting-Ip`、`X-Forwarded-For`、外站 Host | 403、server 還活著 | ✅（本版新修，見下方「來源版發現的問題」） |
| 示範版不連外 | 誤發 LINE、誤扣款 | 載入 `demo_server` 後連 `api.line.me`、`1.1.1.1:443` | 都被擋 | ✅ |
| 報價簽收 | 竄改、重複 | 條款摘要錯誤、沒簽名、連按兩次 | 400、400、第二次回 `already` 且工單只多 1 張 | ✅ |
| 個資告知 | 未同意就收個資 | 估價表單 `consent=false` | 400 | ✅ |
| 金鑰 | 寫死、外流 | 掃描私鑰、sk-、AIza、gh*_、真 LINE userId、真手機號碼、本機路徑；環境變數優先、空白當沒設 | 0 命中 | ✅ `test_config.py` |
| 夥伴銀行帳戶只給 money 權限 | 個資／金流資料外洩、被竄改 | staff 讀 `/api/state`；staff POST `/api/save/workers` 帶 `bank_*`、`payout_cycle` | 四個欄位與時薪都是 null；存檔後 DB 銀行欄位不變、回應也不帶出；一般欄位（備註）照常可改；管理員看得到 | ✅ `BankFieldsTest` |
| 冒用夥伴身分重新應徵 | 知道電話就能冒用 | 陌生 LINE 帳號＋既有夥伴的電話送應徵（`reapply_mode=screen`、夥伴曾被婉拒） | 不 screen、`worker_files` 不改、不綁 LINE；核准綁定後才 screen＋掛檔；按「不是本人」擱置資料作廢 | ✅ `test_reapply_security.py`（舊程式跑這兩個測試會失敗，已確認） |
| 自架模式 | 弱密碼 | `create_admin.py` 用全數字、5 碼密碼 | 拒絕；正確密碼可登入、錯誤密碼 403 | ✅ `test_selfhost.py` |

### 第 6 道 資料

| 項目 | 做法 | 結果 |
|---|---|---|
| 備份還原 | 把 server 自動產生的 `backups/operations-*.db` 複製到新資料夾當 `operations.db`，啟動示範 server、用管理員讀 `/api/state` | ✅ `integrity_check = ok`；客戶 15、夥伴 6、工單 65、派工 71、帳單 9，與原資料庫一致 |
| 重建示範資料 | 連跑兩次 `seed_demo.py` | ✅ 舊資料庫改名 `_舊示範資料_*.db` 保留，不刪除（`test_reseed_keeps_old_db`） |
| 既有資料庫再啟動 | `core.initialize()` 每次啟動都跑（`CREATE TABLE IF NOT EXISTS`＋欄位補齊） | ✅ 還原的舊資料庫可直接啟動 |

## 來源版發現的問題（已在開源版修正，**示範站本身沒改**）

1. 🔴 **示範站 `/__demo_stop` 經 Cloudflare Tunnel 可被外網觸發**：原本只檢查來源 IP 是 127.0.0.1，但 Tunnel 轉進來的請求來源也是 127.0.0.1。開源版改成「來源本機＋Host 是本機埠＋沒有任何代理標頭」才接受，並加測試。**線上示範站仍是舊寫法，建議負責示範站的 session 同步修正。**
2. 🟠 非 Windows 主機會在讀寫金鑰時直接出錯（DPAPI 限 Windows）：開源版改成環境變數優先，系統內部金鑰在非 Windows 以 `plain:` 前綴存放，並寫進已知限制。
3. 🔴 **重新應徵可冒用既有夥伴身分**（自動安全審查在 `worker_portal.py` 抓到）：電話對到既有夥伴時，就算 LINE 還沒確認是本人，系統已呼叫 `interviews.screen()` 並把這次上傳的檔案掛到該夥伴名下。開源版改成：只有送出的 LINE 已綁定該夥伴才直接篩選；否則把資料暫存在 `reapply_pending:<綁定申請 id>`，等 `decide_bind` 核准才 screen＋掛檔，拒絕則作廢。**線上示範站與正式系統仍是舊寫法，建議負責的 session 同步修正。**
4. 🔴 **客服（staff）看得到、改得到夥伴銀行帳戶**（自動安全審查在 `server.py` 抓到）：沒有 money 權限時 `state_for` 只清掉時薪，`bank_name`／`bank_account`／`bank_holder`／`payout_cycle` 照樣送出，`/api/save` 也沒擋。開源版改成三處都擋：`state_for` 設成 null、`/api/save` 移除這四個欄位、存檔回應也清掉。**線上示範站與正式系統仍是舊寫法，建議同步修正。**
5. 🟡 `seo.py` 用了 Python 3.12 才支援的 f-string 寫法，3.10 無法啟動：已改寫。

## 已知限制（README 已寫）

1. 真實 LINE、LINE Pay、Google、Anthropic 串接沒有在開源版實測；第一次接真帳號請用測試頻道與 sandbox。
2. 介面文字與預設值偏向原團隊（三條業務線、派單管理群、宜蘭地區），要換品牌與地區需改設定。
3. 金鑰加密只支援 Windows DPAPI；非 Windows 請用環境變數。
4. 沒做效能壓測、沒在 iOS／Android 實機瀏覽器逐頁檢查（來源版本來就在營運中使用，但開源版沒重做）。
5. **POST 先回應、再提交交易**：同一個瀏覽器在回應後極短時間內的下一個請求，偶爾會讀到還沒提交的狀態（例如剛登入就 401，重新整理即可）。來源程式本來的寫法，開源版沒有改動核心交易流程。
6. 程式約 2.7 萬行 Python、註解為中文；註解去識別化是「規則＋逐類人工檢查」，不是逐行人工審閱。

## 要店長決定

1. **公開與否**：目前 PRIVATE。
2. **地名**：開源版保留「宜蘭」作為預設服務區與示範地址（約 110 處），會讓人看得出原團隊在宜蘭。要不要改成中性的「○○縣」？
3. **來源系統的三個漏洞**（`/__demo_stop` 外網可停站、重新應徵可冒用夥伴身分、客服看得到改得到夥伴銀行帳戶）：開源版已修；線上示範站與正式系統要不要請負責的 session 同步修。

## 推送後驗證

| 項目 | 做法 | 結果 |
|---|---|---|
| 乾淨 clone | `gh repo clone` 到 `%TEMP%d	dk`（初始 commit `65f5509`），Python 3.10.22 新 venv，`pip install -r requirements.txt` | ✅ 安裝成功；34 項測試全過（有無 UTF-8 模式都過） |
| 照 README 跑示範 | `python app/seed_demo.py`；`DEMO_PORT=5490 python app/demo_server.py` | ✅ `/`、`/intro`、`/home`、`/book`、`/mall`、`/privacy`、`/join`、夥伴頁全部 200；四個角色 `/enter` 後 `/api/state` 200；瀏覽器開老闆畫面、夥伴手機畫面、線上估價，console 無錯誤、底部客製化廣告正常；測完用 `/__demo_stop` 停掉，5490 已釋放 |
| clone 的 deep_audit | `deep_audit.py`（檔案＋全歷史＋作者信箱） | ✅ 命中全部判讀為誤判或刻意保留（同上表）；只在歷史裡的命中 0、非 noreply 作者 0 |
| CI（`65f5509`） | GitHub Actions | ⚠️ Ubuntu 3.10／3.12 綠；Windows 3.10／3.12 的 `test_selfhost` 失敗：登入回應後馬上打 `/api/me` 拿到 401。原因是 server「先回應、再提交交易」，CI 機器太快時下一個請求比 commit 早到（來源程式本來就這樣，不是開源版改壞的）。第二個 commit 讓測試稍等重試並列入已知限制 |
| 第二個 commit `5009efc` | 修重新應徵冒用漏洞＋新增 2 個測試＋上面的測試修正 | ✅ 本機 Windows Python 3.14／3.10 共 36 項全過 |
| CI（`5009efc`） | GitHub Actions run 40462689708 | ✅ **四個組合全綠**：Ubuntu 3.10、Ubuntu 3.12、Windows 3.10、Windows 3.12 |
| 乾淨 clone（`5009efc`） | 重新 `gh repo clone`、Python 3.10.22 新 venv、`pip install -r requirements.txt` | ✅ 36 項測試全過 |
| clone 的 deep_audit（`5009efc`） | 同上 | ✅ 🔴136／🟠12／🟡12 全部是上表的誤判或刻意保留；歷史命中 0、非 noreply 作者 0 |

| 第三個 commit `2e1be65` | 修客服看／改夥伴銀行帳戶＋`BankFieldsTest` | ✅ 本機 Windows Python 3.14（連跑 3 次）／3.10 共 38 項全過 |
| CI（`2e1be65`） | GitHub Actions run 40465323494 | ✅ **四個組合全綠**：Ubuntu 3.10、Ubuntu 3.12、Windows 3.10、Windows 3.12 |
| 乾淨 clone（`2e1be65`） | 重新 `gh repo clone`、Python 3.10.22 新 venv、`pip install -r requirements.txt`、照 README 跑示範（埠 5490） | ✅ 38 項測試全過；7 個主要頁面＋4 個角色 `/api/state` 全部 200；測完 `/__demo_stop`，5490 已釋放 |
| clone 的 deep_audit（`2e1be65`） | 同上 | ✅ 命中同上表，全部誤判或刻意保留；歷史命中 0、非 noreply 作者 0 |

> 第 7 道說明：git 歷史是全新的（不含來源系統任何歷史）；目前有 5 個 commit（初始 commit、兩個公開前安全修正、兩次本檔補驗證結果），全部經過去識別化掃描，兩個都經過去識別化掃描。


## 2026-10-27 公開前補強（主 session）
- 主 session 用正式資料（唯讀）比對：程式裡還留有 1 個真實客戶暱稱、1 個真實客戶家名稱、3 個真實客戶／任務編號（決策處理與註解裡），已全部換成中性占位值；比對 348 個真實客戶／夥伴／案場名稱與 4,654 個真實資料編號，剩下命中都是誤判（LINE 字樣、作者署名、常見稱呼）。
- 這個 repo 曾在修正前短暫公開不到 1 分鐘（0 star、0 fork），已立即改回私人；修正後把歷史重建成全新單一 commit 再公開，舊歷史打包備份在作者本機。
- 修正後 38 項測試全過。
