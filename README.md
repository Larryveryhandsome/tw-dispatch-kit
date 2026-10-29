# tw-dispatch-kit｜到府清潔接單派工系統

給到府清潔、家事服務、民宿清潔團隊用的營運系統：**線上估價 → 正式報價單 → 客人線上簽收 → 派工 → 夥伴手機打卡拍照 → 月底對帳與薪資結算**，一套 Python 程式全部包辦，不用再靠 LINE 群組跟 Excel 硬撐。

這份是從實際營運中的清潔團隊系統整理出來的**示範版**：品牌、客戶、夥伴、地址、電話全部換成虛構資料，LINE、金流、推播預設全部關閉。

- 🧾 **線上估價／報價**：客人在手機填坪數、狀況、時段，系統依規則初估；主管確認後送出正式報價單，客人線上勾選條款、手寫簽名就成立工單。
- 🗓️ **排班派工**：依地區、夥伴可排時間、分級邀請夥伴接單；請假、改期會提示受影響的工單。
- 📱 **夥伴手機頁**：不用裝 App，用連結看自己的班表、地址、打卡、拍完工照片。
- 💰 **帳務**：工單完成自動入帳，月結客戶帳單、夥伴薪資結算、收款紀錄。
- 👥 **角色權限**：管理員、客服排班、帳務、清潔夥伴各看各的；夥伴看不到客戶清單與其他夥伴的資料。
- 🔌 **選用串接**：LINE 官方帳號（多品牌）、LINE Pay、Google 日曆、Anthropic（拍收據讀金額）。開源版**不附任何金鑰**，要用請照 [docs/金鑰申請.md](docs/金鑰申請.md) 自己申請。

> ⚠️ 原則上本專案只是工具範本，不構成法律意見。實際營運請自行確認《個人資料保護法》、《勞動基準法》（夥伴是承攬或僱傭）、消費者保護與電子簽章等規定；報價單與合約條款請交專業人士審閱。

---

## 5 分鐘看示範（全部假資料、不連網）

**需要：** Python 3.10 以上（[python.org 下載](https://www.python.org/downloads/)，Windows 安裝時勾選「Add python.exe to PATH」）。

```bash
git clone https://github.com/Larryveryhandsome/tw-dispatch-kit.git
cd tw-dispatch-kit
pip install -r requirements.txt
```

建立示範資料（15 位客戶、6 位夥伴、約 65 張工單，全部虛構）：

```bash
python app/seed_demo.py
```

啟動示範 server：

```bash
python app/demo_server.py
```

打開 http://127.0.0.1:5480 ，先看到說明頁，按「直接試玩」就進系統，**不用登入**。也可以直接用這些網址切換身分：

| 網址 | 看到什麼 |
|---|---|
| http://127.0.0.1:5480/enter?as=admin | 老闆／管理員畫面 |
| http://127.0.0.1:5480/enter?as=staff | 客服排班 |
| http://127.0.0.1:5480/enter?as=finance | 帳務 |
| http://127.0.0.1:5480/enter?as=worker | 清潔夥伴的手機畫面 |
| http://127.0.0.1:5480/book | 客人的線上估價表單 |
| http://127.0.0.1:5480/home | 官網範例 |

停止示範：

```bash
python app/demo_server.py --stop
```

想換埠：`DEMO_PORT=5490 python app/demo_server.py`（Windows PowerShell：`$env:DEMO_PORT=5490; python app/demo_server.py`）。

### 示範版的安全設計

- **對外連線全部擋掉**：`demo_server.py` 啟動時把 socket 換成只允許連回本機示範埠，LINE、LINE Pay、Google、推播、AI 一律連不出去（`tests/test_demo_server.py` 有測）。
- **推播、本機 AI 強制關閉**：`DISPATCH_NO_PUSH=1`、`DISPATCH_AIB_LOCAL=0`。
- **只聽 127.0.0.1**；`/__demo_stop` 只接受本機直連，經過反向代理或 Cloudflare Tunnel 進來的停止請求一律 403。
- 重跑 `seed_demo.py` 會把舊的示範資料庫改名保留在 `data/`，不會刪除。

---

## 自己架起來用（進階）

示範版之外，也可以用自己的資料跑正式模式：

```bash
python app/create_admin.py boss "老闆"      # 建第一個管理員，密碼在終端機輸入（至少 10 碼、不能只有數字）
python app/server.py                         # 預設 http://127.0.0.1:4781，用剛剛的帳密登入
```

- 資料庫在 `DISPATCH_DATA`（預設 `app/data/operations.db`），每天自動備份到旁邊的 `backups/`，保留 30 份。
- 只聽 `127.0.0.1`。要給夥伴和客人從外網用，請用 HTTPS 的反向代理或 Cloudflare Tunnel，並把網域設進 `DISPATCH_PUBLIC_HOSTS`。
- 還沒設好金鑰前，建議先設 `DISPATCH_NO_PUSH=1`，確認流程都對了再拿掉。

### 環境變數

| 變數 | 預設 | 說明 |
|---|---|---|
| `DEMO_PORT` | `5480` | 示範 server 的埠 |
| `DISPATCH_DATA` | `app/data`（示範版是 `data/`） | 資料庫與上傳檔案的位置 |
| `DISPATCH_PORT` | `4781` | 正式模式的埠 |
| `DISPATCH_PUBLIC_HOSTS` | `ops.example.com` | 對外網址（逗號分隔），經 HTTPS 代理進來的 Host |
| `DISPATCH_SITE_HOSTS` | `www.example.com` | 官網網址，只開公開頁 |
| `DISPATCH_BASE_URL` | `https://ops.example.com` | LINE 卡片、報價單連結用的對外網址 |
| `DISPATCH_NO_PUSH` | 空 | 設 `1`＝不送 LINE、不推播、不連外部服務 |
| `DISPATCH_SECRET_*` | 空 | 各種金鑰，名稱見 [docs/金鑰申請.md](docs/金鑰申請.md) |
| `DISPATCH_LOCAL_LLM_GATEWAY` | 空 | 選用：本機 LLM 閘道資料夾（要提供 `local_llm.chat()`）；空值＝不用 |
| `DISPATCH_OUTREACH_DB` | 空 | 選用：社群海巡系統的資料庫路徑；空值＝「海巡留言待審」功能關閉 |

金鑰的讀法：先看環境變數 `DISPATCH_SECRET_<名稱>`；沒有的話才讀資料庫裡在 Windows 上用 DPAPI 加密的值（從管理畫面輸入的金鑰）。非 Windows 主機請一律用環境變數。

---

## 測試

```bash
python -m unittest discover -s tests -v
```

測試不連網、不需要金鑰，會在暫存資料夾建示範資料、用隨機埠啟動示範 server 再停掉，涵蓋：建示範資料、server 啟動、主要頁面、免登入 `/enter`、`/__demo_stop` 只接受本機直連、對外連線被擋、估價／報價／簽收流程（含竄改條款、重複送出）、夥伴權限（只看到自己的工單、打不到管理 API）、用陌生 LINE 冒用既有夥伴電話重新應徵、自架模式建管理員與登入、金鑰只從環境變數讀。

GitHub Actions 會在 Ubuntu 與 Windows、Python 3.10 與 3.12 上自動跑。

## 專案結構

```
app/
  demo_server.py   示範啟動器（擋對外連線、免登入入口）
  seed_demo.py     建虛構示範資料
  create_admin.py  自架：建第一個管理員
  server.py        HTTP server 與 API
  core.py          資料庫連線、共用工具；schema*.sql 為資料表定義
  booking.py       估價單、報價、簽收；pricing.py 計價規則
  dispatch.py      派工；tiers.py 分級邀請；leave.py 請假補人
  board.py         今日面板、完工、結算；ledger.py 記帳
  line_bot.py      LINE 官方帳號（多品牌）；linepay.py LINE Pay
  web/             前端（純 HTML／CSS／JS，不用打包）
tests/             測試
docs/金鑰申請.md     串接 LINE／LINE Pay／Google／Anthropic 的申請與設定
```

## ⚠️ 已知限制

- **真實串接沒有在開源版實測**：LINE、LINE Pay、Google 日曆、Anthropic 的程式碼來自實際營運版本，但開源版只驗證了「沒設金鑰時不會連線」。第一次接真帳號時，請先用測試頻道與 LINE Pay sandbox。
- **介面文字偏向特定團隊的流程**：例如三個業務線（示範清潔、居家小幫手、民宿清潔線）、派單管理群、宜蘭地區的地名與預設服務區。要改成你們的品牌與地區，需要改 `app/brands.py`、`app/regions.py`、`app/pricing.py` 等設定（或找我們客製化）。
- **金鑰加密只支援 Windows DPAPI**：非 Windows 主機從管理畫面輸入的外部金鑰無法解密，請改用環境變數；系統自己產生的內部金鑰（照片網址簽章、日曆訂閱）在非 Windows 會以明文存在資料庫。
- **程式碼很大、註解是中文**：約 2.7 萬行 Python ＋ 5 千行 JavaScript，沒有拆成套件；歡迎 PR。
- 後端是「先回應、再提交交易」：回應後立刻送出的下一個請求，偶爾會讀到舊狀態（例如剛登入馬上 401，重新整理即可）。
- 只聽 127.0.0.1，對外一定要經過 HTTPS 代理；多台機器、多租戶（SaaS）不在這個版本的範圍。

## 授權

[Apache-2.0](LICENSE)。轉散布請保留 [NOTICE](NOTICE) 的作者署名，以及工具畫面上的客製化聯絡資訊。資安問題請看 [SECURITY.md](SECURITY.md)。

---

## 🛠️ 需要客製化？

這個系統是開源的，可以免費使用。如果你想要：

- 換成你們的品牌、服務項目、價目表、服務地區
- 串接你們的 LINE 官方帳號、LINE Pay、Google 日曆、記帳流程
- 幫你架站（HTTPS、備份、排程）、教學，或長期維護

歡迎加 LINE 跟我們聊。我們會依需求的範圍與複雜度報價，原則上以實際報價單為準。

<a href="https://line.me/ti/p/xzHT2IywOM"><img src="https://scdn.line-apps.com/n/line_add_friends/btn/zh-Hant.png" alt="加入好友" height="36"></a>

- 💬 LINE：[林其衞](https://line.me/ti/p/xzHT2IywOM)（請註明「接單派工系統 客製化」）
- 🏢 留白事務所：網頁設計、AI 自動化、房仲遠端助理
- 👤 作者：林其衞／[留白事務所](https://github.com/Larryveryhandsome)
