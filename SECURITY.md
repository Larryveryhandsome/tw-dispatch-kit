# 資安政策

## 回報漏洞

發現資安問題時，**請不要開公開的 Issue**。請用 GitHub 的「Report a vulnerability」（Security → Advisories）私下回報，內容包含影響範圍、重現步驟、可能的影響。原則上我們會在 7 天內回覆。

## 設計上的安全措施

- 只聽 `127.0.0.1`；檢查 `Host` 標頭（擋 DNS rebinding），對外必須經過 HTTPS 反向代理並把網域設進 `DISPATCH_PUBLIC_HOSTS`。
- POST 一律檢查 `Origin` 與 CSRF token；只收 JSON，限制大小。
- 角色權限：管理員／客服排班／帳務／清潔夥伴；夥伴的 API 只回自己的工單，打管理 API 一律 403。
- 密碼 PBKDF2-SHA256（31 萬次）加鹽；登入節流（同一來源 15 分鐘 20 次、同一帳號連錯 6 次鎖 15 分鐘）；初始密碼 72 小時沒換就失效。
- 對外表單要勾個資告知（後端檢查並留存版本、時間、IP）；有個資查詢與刪除流程。
- 報價簽收檢查條款摘要（條款改過就要重新閱讀）、簽名格式與大小；重複送出不重複建單。
- 金鑰只從環境變數 `DISPATCH_SECRET_*` 讀，或在 Windows 用 DPAPI 加密存資料庫；`data/`、`backups/`、`.env`、`*.db` 都在 `.gitignore`。
- 示範版：所有對外連線在 socket 層擋掉；`/__demo_stop` 只接受本機直連（有代理標頭或非本機 Host 一律 403）。

## 使用者自己要注意

- 不要把 `data/`、`backups/`、`.env` 上傳到 git 或公開的雲端資料夾。
- 示範版的 `/enter` 是免登入入口，**只適合放假資料**；正式資料請用 `server.py`。
- 金鑰外流時，立刻到發放處撤銷或重新產生（位置見 `docs/金鑰申請.md`）。
