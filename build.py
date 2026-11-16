#!/usr/bin/env python3
"""把 data/venues/*.json 產生成 index.html 與 venues/<slug>.html。
用法：python3 build.py            （使用今天日期）
      python3 build.py --today 2026-11-16   （指定「今天」，測試用）
規則與資料格式見 AGENTS.md。"""
import argparse, glob, hashlib, html, json, os
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
STATUS_LABEL = {"ongoing": "展出中", "upcoming": "即將開展", "ended": "已結束", "unknown": "展期待確認"}
STATUS_ORDER = {"ongoing": 0, "upcoming": 1, "unknown": 2, "ended": 3}


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def load_venues():
    venues = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "venues", "*.json"))):
        with open(path, encoding="utf-8") as f:
            venues.append(json.load(f))
    return venues


def status_of(start, end, today):
    """今天以 ISO 字串比較。回傳 ongoing / upcoming / ended / unknown。"""
    if not start and not end:
        return "unknown"
    if start and today < start:
        return "upcoming"
    if end and today > end:
        return "ended"
    return "ongoing"


def date_text(start, end):
    if start and end:
        return f"{start} ～ {end}"
    if start:
        return f"{start} 起（官網未標示結束日）"
    if end:
        return f"開始日待確認 ～ {end}"
    return "展期待確認"


def venue_class(slug):
    """依 slug 穩定地分配海報底色（v0～v6），新增場館不用指定顏色。"""
    return "v" + str(int(hashlib.md5(slug.encode("utf-8")).hexdigest(), 16) % 7)


def dot(d):
    return d.replace("-", ".") if d else None


def date_html(start, end):
    if start and end:
        return f'<div class="date">{dot(start)} —<br>{dot(end)}</div>'
    if start:
        return f'<div class="date">{dot(start)} 起<br><span class="info">官網未標示結束日</span></div>'
    if end:
        return f'<div class="date">開始日待確認 —<br>{dot(end)}</div>'
    return '<div class="date none">展期待確認</div>'


def exhibition_card(ex, venue, today, show_venue):
    st = status_of(ex.get("start"), ex.get("end"), today)
    vc = venue_class(venue["slug"])
    p = [f'<article class="exh {vc}" data-status="{st}" data-start="{esc(ex.get("start"))}" '
         f'data-end="{esc(ex.get("end"))}" data-city="{esc(venue["city"])}" '
         f'data-search="{esc((ex["title"] + " " + venue["name"] + " " + venue["city"]).lower())}">']
    p.append(f'<div class="top"><span>{esc(ex["kind"])}</span><span class="st {st}" data-role="status">{STATUS_LABEL[st]}</span></div>')
    p.append(f'<h3>{esc(ex["title"])}</h3>')
    p.append(date_html(ex.get("start"), ex.get("end")))
    where = []
    if show_venue:
        where.append(f'<a href="venues/{esc(venue["slug"])}.html">{esc(venue["name"])}</a>（{esc(venue["city"])}）')
    where.append(esc(ex["location"]) if ex.get("location") else "地點官網未寫明，待確認")
    p.append('<p class="info">' + "<br>".join(where) + "</p>")
    if ex.get("note"):
        p.append(f'<p class="note">{esc(ex["note"])}</p>')
    p.append(f'<p class="src"><a href="{esc(ex["source_url"])}" target="_blank" rel="noopener">官網來源（{esc(ex["date_source"])}）</a>'
             f'｜查證 {esc(venue["verified_on"])}</p>')
    p.append("</article>")
    return "\n".join(p)


PAGE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="bar"><div class="bar-in">
  <a class="brand" href="{home}"><span class="zh">全台藝文展覽表</span><span class="en">Taiwan Exhibition Guide</span></a>
  <nav><a href="{home}#exhibitions">展覽</a><a href="{home}#venues">場館</a><a href="{home}#about">資料說明</a></nav>
</div></header>
{body}
<footer class="site"><div class="wrap">
  <p>資料整理自各場館官網，僅供參考；展期、開放時間與票價請以官網公告為準。本站不是任何場館的官方網站。</p>
  <p>網站建置日期：{built}｜新增或修改內容的規則請見 <a href="{agents}">AGENTS.md</a></p>
</div></footer>
{script}
</body>
</html>
"""

STATUS_JS = """<script>
(function () {
  var d = new Date(), today = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  var LABEL = { ongoing: '展出中', upcoming: '即將開展', ended: '已結束', unknown: '展期待確認' };
  function statusOf(s, e) {
    if (!s && !e) return 'unknown';
    if (s && today < s) return 'upcoming';
    if (e && today > e) return 'ended';
    return 'ongoing';
  }
  var cards = Array.prototype.slice.call(document.querySelectorAll('.exh'));
  cards.forEach(function (c) {
    var st = statusOf(c.dataset.start, c.dataset.end);
    c.dataset.status = st;
    var b = c.querySelector('[data-role="status"]');
    if (b) { b.className = 'st ' + st; b.textContent = LABEL[st]; }
  });
"""
FILTER_JS = """  var q = document.getElementById('q'), city = document.getElementById('city'), status = document.getElementById('status'), count = document.getElementById('count');
  if (!q) return;
  function apply() {
    var kw = q.value.trim().toLowerCase(), n = 0;
    cards.forEach(function (c) {
      var ok = (!kw || c.dataset.search.indexOf(kw) !== -1) &&
               (!city.value || c.dataset.city === city.value) &&
               (!status.value || c.dataset.status === status.value);
      c.hidden = !ok; if (ok) n++;
    });
    count.textContent = '符合條件的展覽：' + n + ' 筆';
  }
  [q, city, status].forEach(function (el) { el.addEventListener('input', apply); });
  apply();
"""
END_JS = "})();\n</script>"


def build_index(venues, today):
    cities = sorted({v["city"] for v in venues})
    all_ex = [(v, ex) for v in venues for ex in v["exhibitions"]]
    def key(t):
        st = status_of(t[1].get("start"), t[1].get("end"), today)
        return (STATUS_ORDER[st], t[1].get("end") or "9999-12-31", t[1]["title"])
    all_ex.sort(key=key)
    ongoing = [(v, e) for v, e in all_ex if status_of(e.get("start"), e.get("end"), today) == "ongoing"]
    closing = sorted([t for t in ongoing if t[1].get("end")], key=lambda t: t[1]["end"])
    body = []
    if closing:
        v, e = closing[0]
        side = "".join(f'<li><span class="d">{dot(x[1]["end"])} 結束</span><a href="venues/{esc(x[0]["slug"])}.html">{esc(x[1]["title"])}</a></li>' for x in closing[1:6])
        body.append(f'<section class="hero"><div class="hero-in"><div class="hero-main"><span class="en">Closing soon ／ 即將結束</span>'
                    f'<h1>{esc(e["title"])}</h1><p class="hero-date">{dot(e.get("start")) or ""} — {dot(e["end"])}</p>'
                    f'<p class="hero-meta"><a href="venues/{esc(v["slug"])}.html">{esc(v["name"])}</a>｜{esc(e.get("location") or "地點待確認")}</p></div>'
                    f'<aside class="hero-side"><h2>即將結束</h2><ol>{side}</ol></aside></div></section>')
    else:
        body.append('<section class="hero"><div class="hero-empty"><span class="en">Taiwan Exhibition Guide</span><h1>目前沒有有結束日的展出中展覽</h1></div></section>')
    body.append('<div class="wrap">')
    body.append(f'<section class="block" id="exhibitions"><h2>展覽 <span class="en">Exhibitions</span></h2>'
                f'<p class="lead">收錄 {len(cities)} 個縣市、{len(venues)} 個場館、{len(all_ex)} 筆展覽（依 {esc(today)} 計算，展出中 {len(ongoing)} 筆）。</p>')
    opts = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cities)
    body.append(f'<div class="filters"><label class="grow"><span class="en">Search</span><input id="q" type="search" placeholder="展名、場館或縣市" aria-label="搜尋"></label>'
                f'<label><span class="en">City</span><select id="city" aria-label="縣市"><option value="">全部縣市</option>{opts}</select></label>'
                f'<label><span class="en">Status</span><select id="status" aria-label="狀態"><option value="">全部狀態</option><option value="ongoing">展出中</option>'
                f'<option value="upcoming">即將開展</option><option value="unknown">展期待確認</option><option value="ended">已結束</option></select></label></div>')
    body.append('<p class="count" id="count"></p><div class="wall">')
    body.extend(exhibition_card(ex, v, today, True) for v, ex in all_ex)
    body.append("</div></section>")
    body.append('<section class="block" id="venues"><h2>場館 <span class="en">Venues</span></h2><div class="vlist">')
    for v in venues:
        body.append(f'<div class="vrow"><a href="venues/{esc(v["slug"])}.html">{esc(v["name"])}</a>'
                    f'<span class="m">{esc(v["city"])}{esc(v.get("district") or "")}｜{esc(v["category"])}</span>'
                    f'<span class="m">收錄展覽 {len(v["exhibitions"])} 筆</span><span class="m">查證 {esc(v["verified_on"])}</span></div>')
    body.append("</div></section></div>")
    body.append('<section class="about" id="about"><div class="wrap"><h2>資料說明</h2>'
                '<p>每一筆展覽都附官網來源與查證日期。官網沒有寫的資料（展期、地點、開放時間），本站一律標示「待確認」，不憑印象填寫。</p>'
                '<p>官網的行事曆列表和展覽詳情頁日期有時不一致，本站以展覽詳情頁為準，並在該筆資料註明。</p>'
                '<p>只收錄藝術、設計、歷史、科學、文化類的特展與常設展；快閃店、市集、賽事等不收錄。</p></div></section>')
    return PAGE.format(title="全台藝文展覽表", desc="博物館、美術館、文創園區的展覽整理，附官網來源與查證日期",
                       css="style.css", home="index.html", agents="AGENTS.md", built=esc(today),
                       body="\n".join(body), script=STATUS_JS + FILTER_JS + END_JS)


def build_venue(v, today):
    rows = [("縣市", f'{v["city"]}{v.get("district") or ""}'), ("類型", v["category"]), ("地址", v["address"]),
            ("開放時間", v.get("hours") or "官網未寫明，待確認"), ("休館日", v.get("closed") or "官網未寫明，待確認")]
    dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(val)}</dd>" for k, val in rows)
    dl += (f'<dt>官網</dt><dd><a href="{esc(v["website"])}" target="_blank" rel="noopener">{esc(v["website"])}</a></dd>'
           f'<dt>展覽頁</dt><dd><a href="{esc(v["exhibition_page"])}" target="_blank" rel="noopener">官網展覽頁</a></dd>'
           f'<dt>查證日期</dt><dd>{esc(v["verified_on"])}</dd>')
    body = ['<div class="wrap"><div class="vhead"><a class="back" href="../index.html">← 回展覽總表</a>'
            f'<h1>{esc(v["name"])}</h1><span class="en">{esc(v["category"])}</span></div>',
            f'<dl class="info2">{dl}</dl>']
    if v.get("notes"):
        body.append(f'<div class="vnote">{esc(v["notes"])}</div>')
    body.append(f'<h2 style="font-family:var(--serif);margin:28px 0 14px">展覽（{len(v["exhibitions"])} 筆）</h2>')
    if not v["exhibitions"]:
        body.append('<p class="empty">目前沒有收錄任何展覽，請見上方說明，並直接到官網確認。</p>')
    else:
        exs = sorted(v["exhibitions"], key=lambda e: (STATUS_ORDER[status_of(e.get("start"), e.get("end"), today)], e.get("end") or "9999-12-31"))
        body.append('<div class="wall">' + "\n".join(exhibition_card(e, v, today, False) for e in exs) + "</div>")
    body.append("</div>")
    return PAGE.format(title=f'{v["name"]}｜全台藝文展覽表', desc=f'{v["name"]}的展覽整理，附官網來源與查證日期',
                       css="../style.css", home="../index.html", agents="../AGENTS.md", built=esc(today),
                       body="\n".join(body), script=STATUS_JS + END_JS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()
    venues = load_venues()
    os.makedirs(os.path.join(ROOT, "venues"), exist_ok=True)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(venues, args.today))
    for v in venues:
        with open(os.path.join(ROOT, "venues", v["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(build_venue(v, args.today))
    print(f"已產生 index.html 與 {len(venues)} 個場館頁（今天 = {args.today}）")


if __name__ == "__main__":
    main()
