# 全台藝文展覽表

整理台灣博物館、美術館、文創園區「目前有哪些展覽」的靜態網站。每一筆資料都附官網來源與查證日期；官網沒寫的就標「待確認」，不憑印象填寫。

- 目前收錄：基隆市、臺北市、臺中市共 7 個場館、36 筆展覽（查證日期 2026-11-16）
- 技術：純 HTML、CSS、原生 JavaScript，不使用外部套件；用 Python 腳本由 JSON 資料產生網頁
- **規則文件：[AGENTS.md](AGENTS.md)**（AI 與人都請先讀）

## 使用方式

```bash
python3 build.py        # 由 data/venues/*.json 產生 index.html 與 venues/*.html
python3 check_site.py   # 檢查資料與網頁是否符合規則
python3 -m http.server 8000   # 本機預覽
```

## 新增內容

照 [AGENTS.md](AGENTS.md) 的「工作流程」：新增或修改 `data/venues/<slug>.json`，執行建置與檢查即可。

## 免責聲明

資料整理自各場館官網，僅供參考；展期、開放時間與票價請以官網公告為準。本站不是任何場館的官方網站。
