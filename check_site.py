#!/usr/bin/env python3
"""檢查網站是否符合 AGENTS.md 的規則。AI 每次修改資料或頁面後都要執行：python3 check_site.py
全部通過會回傳 0；有錯誤會列出來並回傳 1。"""
import glob, json, os, re, sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
errors, warnings = [], []
KINDS = {"特展", "常設展"}
DATE_SOURCES = {"詳情頁", "列表頁", "首頁"}
CATEGORIES = {"博物館", "美術館", "文創園區", "其他"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEY = re.compile(r"(gsk_[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
VENUE_REQ = ["slug", "name", "city", "category", "address", "website", "exhibition_page", "verified_on", "exhibitions"]
EX_REQ = ["id", "title", "kind", "source_url", "date_source"]


def err(msg): errors.append(msg)


def check_date(v, where, allow_none=True):
    if v is None:
        if not allow_none: err(f"{where}：不可為空")
        return
    if not ISO.match(v): err(f"{where}：日期格式必須是 YYYY-MM-DD，目前是 {v!r}"); return
    try: date.fromisoformat(v)
    except ValueError: err(f"{where}：不是有效日期 {v!r}")


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "data", "venues", "*.json")))
    if not files: err("data/venues/ 裡沒有任何場館資料")
    slugs, ex_ids = set(), set()
    for path in files:
        name = os.path.basename(path)
        try: v = json.load(open(path, encoding="utf-8"))
        except Exception as e: err(f"{name}：不是有效的 JSON（{e}）"); continue
        for k in VENUE_REQ:
            if k not in v: err(f"{name}：缺少必填欄位 {k}")
        if "slug" not in v: continue
        if not SLUG.match(v["slug"]): err(f"{name}：slug 只能是小寫英數與連字號")
        if v["slug"] + ".json" != name: err(f"{name}：檔名必須等於 slug（{v['slug']}.json）")
        if v["slug"] in slugs: err(f"{name}：slug 重複")
        slugs.add(v["slug"])
        if v.get("category") not in CATEGORIES: err(f"{name}：category 必須是 {sorted(CATEGORIES)} 其中之一")
        for k in ("website", "exhibition_page"):
            if not str(v.get(k, "")).startswith("https://"): err(f"{name}：{k} 必須是 https 網址")
        check_date(v.get("verified_on"), f"{name} verified_on", allow_none=False)
        if v.get("verified_on") and ISO.match(v["verified_on"]) and v["verified_on"] > date.today().isoformat():
            err(f"{name}：verified_on 不可以是未來的日期")
        if not v.get("hours") and not (v.get("notes") or ""): warnings.append(f"{name}：沒有開放時間，建議在 notes 說明原因")
        if not v.get("exhibitions") and not v.get("notes"):
            err(f"{name}：exhibitions 是空的時候，notes 必須說明原因（例如官網沒列出）")
        for i, ex in enumerate(v.get("exhibitions", [])):
            w = f"{name} 第 {i+1} 筆展覽"
            for k in EX_REQ:
                if not ex.get(k): err(f"{w}：缺少必填欄位 {k}")
            if ex.get("kind") and ex["kind"] not in KINDS: err(f"{w}：kind 必須是 {sorted(KINDS)}")
            if ex.get("date_source") and ex["date_source"] not in DATE_SOURCES: err(f"{w}：date_source 必須是 {sorted(DATE_SOURCES)}")
            if ex.get("id"):
                if not ex["id"].startswith(v["slug"] + "-"): err(f"{w}：id 必須以「{v['slug']}-」開頭")
                if ex["id"] in ex_ids: err(f"{w}：id 重複 {ex['id']}")
                ex_ids.add(ex["id"])
            check_date(ex.get("start"), w + " start"); check_date(ex.get("end"), w + " end")
            if ex.get("start") and ex.get("end") and ISO.match(ex["start"]) and ISO.match(ex["end"]) and ex["start"] > ex["end"]:
                err(f"{w}：start 不可晚於 end")
            if not str(ex.get("source_url", "")).startswith("https://"): err(f"{w}：source_url 必須是 https 網址")
            if ex.get("date_source") == "列表頁" and not v.get("notes"):
                warnings.append(f"{w}：日期只來自列表頁，建議在場館 notes 註明尚未核對詳情頁")
            for k in ex:
                if k not in {"id", "title", "kind", "start", "end", "location", "source_url", "date_source", "note"}:
                    err(f"{w}：不允許的欄位 {k}（本站不收介紹文字，只收官網有的事實欄位）")
        text = open(path, encoding="utf-8").read()
        if KEY.search(text): err(f"{name}：疑似含有 API 金鑰，請移除")
        if EMAIL.search(text): err(f"{name}：不要放 Email 或個人聯絡方式")
    # 檢查產生出的網頁
    idx = os.path.join(ROOT, "index.html")
    if not os.path.exists(idx): err("找不到 index.html，請先執行 python3 build.py")
    else:
        html = open(idx, encoding="utf-8").read()
        for s in slugs:
            if f'venues/{s}.html' not in html: err(f"index.html 沒有連到場館 {s}，請重新執行 python3 build.py")
            if not os.path.exists(os.path.join(ROOT, "venues", s + ".html")): err(f"缺少 venues/{s}.html，請重新執行 python3 build.py")
        for needle in ('lang="zh-Hant"', 'name="viewport"', "style.css", "AGENTS.md"):
            if needle not in html: err(f"index.html 缺少 {needle}")
    for page in glob.glob(os.path.join(ROOT, "venues", "*.html")):
        if os.path.basename(page)[:-5] not in slugs: err(f"{os.path.relpath(page, ROOT)}：沒有對應的資料檔，請刪除或補上 JSON")
    # 不可使用外部依賴
    for page in [idx] + glob.glob(os.path.join(ROOT, "venues", "*.html")):
        if os.path.exists(page):
            t = open(page, encoding="utf-8").read()
            if re.search(r'<(script|link)[^>]+(src|href)="https?://', t): err(f"{os.path.relpath(page, ROOT)}：不可以引用外部 CDN 或外部字型")
    for w in warnings: print("提醒：", w)
    if errors:
        print(f"\n發現 {len(errors)} 個問題：")
        for e in errors: print(" ✗", e)
        return 1
    print(f"全部通過：{len(files)} 個場館、{len(ex_ids)} 筆展覽，格式與規則都符合 AGENTS.md。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
