"""GolfVotes static site generator (HackerTube-style layout). Standard library only.

Usage: python3 build/build.py  -> writes _site/
Inputs: data/site.json, data/problems.json, data/videos.json, data/links.json (optional)
"""
import html, json, os, re, shutil
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
D = lambda f: json.load(open(os.path.join(ROOT, "data", f)))
SITE, PROBLEMS, VDATA = D("site.json"), D("problems.json"), D("videos.json")
LINKS = D("links.json") if os.path.exists(os.path.join(ROOT, "data", "links.json")) else {}
VIDEOS = VDATA["videos"]
BASE = SITE["base_path"].rstrip("/")
URL = SITE["base_url"].rstrip("/")
MIN = SITE.get("min_recs_per_problem", 2)
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)
PNAME = {p["key"]: p for p in PROBLEMS}
SITEMAP = []


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "unknown"


def fmt_dur(s):
    if not s:
        return ""
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_n(n):
    return f"{n / 1e6:.1f}M".replace(".0M", "M") if n >= 1e6 else (f"{n / 1e3:.0f}K" if n >= 1e3 else str(n))


# ---------- data shaping ----------
for v in VIDEOS:
    v["cs"] = slugify(v.get("channel"))
    tc = v.get("topic_counts") or {}
    v["top"] = max(tc, key=tc.get) if tc else None
    v["page"] = v["recs"] >= MIN          # gets its own watch page
WATCH = {v["vid"]: v for v in VIDEOS if v["page"]}

by_problem = {}
for p in PROBLEMS:
    k, rows = p["key"], []
    for v in VIDEOS:
        n = (v.get("topic_counts") or {}).get(k, 0)
        if n >= MIN:
            ok = (v.get("t_success") or {}).get(k, 0)
            rows.append((n + 0.75 * ok + 0.02 * min(v["recs"], 50), n, ok, v))
    rows.sort(key=lambda r: -r[0])
    by_problem[k] = rows[: SITE.get("max_videos_per_problem", 60)]
    p["total_recs"], p["video_count"] = sum(r[1] for r in rows), len(rows)

channels = defaultdict(lambda: {"recs": 0, "success": 0, "videos": [], "topics": Counter(), "url": None, "name": None})
for v in VIDEOS:
    c = channels[v["cs"]]
    c["name"], c["url"] = v.get("channel"), v.get("channel_url")
    c["recs"] += v["recs"]; c["success"] += v.get("success", 0); c["videos"].append(v)
    for t, n in (v.get("topic_counts") or {}).items():
        c["topics"][t] += n
COACHES = sorted([(s, c) for s, c in channels.items() if c["recs"] >= SITE.get("min_recs_per_coach", 10)], key=lambda x: -x[1]["recs"])
COACH_SET = {s for s, _ in COACHES}
coach_wins = defaultdict(list)
for p in PROBLEMS:
    if by_problem[p["key"]]:
        coach_wins[by_problem[p["key"]][0][3]["cs"]].append(p)
TOTAL_RECS = sum(v["recs"] for v in VIDEOS)
GROUPS = ["Ball flight", "Contact", "Swing faults", "Swing sequence", "Setup", "Clubs", "Short game", "Training", "On the course"]

# ---------- icons ----------
I = {
    "menu": '<path d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"/>',
    "search": '<path d="M20.87 20.17l-5.59-5.59A6.95 6.95 0 0 0 17 10a7 7 0 1 0-7 7c1.75 0 3.35-.64 4.58-1.71l5.59 5.59.7-.71zM10 16a6 6 0 1 1 0-12 6 6 0 0 1 0 12z"/>',
    "help": '<path d="M11 18h2v-2h-2v2zm1-16C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2c0 2-3 1.75-3 5h2c0-2.25 3-2.5 3-5 0-2.21-1.79-4-4-4z"/>',
    "moon": '<path d="M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.39 5.39 0 0 1-4.4 2.26 5.4 5.4 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1z"/>',
    "home": '<path d="M4 21V10.08l8-6.96 8 6.96V21h-6v-6h-4v6H4z"/>',
    "cat": '<path d="M4 4h7v7H4zm2 2v3h3V6zm7-2h7v7h-7zm2 2v3h3V6zM4 13h7v7H4zm2 2v3h3v-3zm7-2h7v7h-7zm2 2v3h3v-3z"/>',
    "coach": '<path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>',
    "like": '<path d="M18.77 11h-4.23l1.52-4.94C16.38 5.03 15.54 4 14.38 4c-.58 0-1.14.24-1.52.65L7 11H3v10h14.43c1.06 0 1.98-.67 2.19-1.61l1.34-6c.27-1.24-.78-2.39-2.19-2.39zM7 20H4v-8h3v8z"/>',
    "hist": '<path d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>',
    "later": '<path d="M14.97 16.95 10 13.87V7h2v5.76l4.03 2.49-1.06 1.7zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>',
    "stats": '<path d="M5 9h3v11H5zm5.5-5h3v16h-3zM16 13h3v7h-3z"/>',
    "ext": '<path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42L17.59 5H14V3zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/>',
    "check": '<path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>',
}
svg = lambda k: f'<svg viewBox="0 0 24 24" aria-hidden="true">{I[k]}</svg>'


# ---------- layout ----------
def page(path, title, desc, body, nav="", og=None, ld=None, canonical=True, cls=""):
    full = URL + path
    side = "".join(f'<a href="{BASE}{h}"{" class=on" if nav == n else ""}>{svg(ic)}<span>{lbl}</span></a>' for n, h, ic, lbl in [
        ("home", "/", "home", "Home"), ("cat", "/categories/", "cat", "Problems"), ("coaches", "/coaches/", "coach", "Coaches"),
        ("liked", "/liked/", "like", "Liked"), ("history", "/history/", "hist", "History"), ("later", "/later/", "later", "Watch later"),
        ("stats", "/report/", "stats", "Stats")])
    nl = SITE.get("newsletter_url")
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
{f'<link rel="canonical" href="{e(full)}">' if canonical else ''}
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(full)}"><meta property="og:image" content="{e(og or URL + '/static/og/default.png')}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{BASE}/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}/static/style.css?v={e(VDATA['generated'])}2">
<script>try{{var t=localStorage.getItem("gv_theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{f'<script type="application/ld+json">{json.dumps(ld)}</script>' if ld else ''}
</head><body class="{cls}" data-base="{BASE}">
<header class="top">
  <div class="left"><button class="icon" id="menu" aria-label="Menu">{svg('menu')}</button>
  <a class="brand" href="{BASE}/" aria-label="{e(SITE['name'])} home">Golf<b>Votes</b></a></div>
  <form class="search" action="{BASE}/search/" role="search"><input name="q" id="q" type="search" placeholder="Search a problem, coach or video" autocomplete="off" aria-label="Search"><button aria-label="Search">{svg('search')}</button></form>
  <div class="right"><a class="icon" href="{BASE}/about/" aria-label="About" title="About">{svg('help')}</a><button class="icon" id="theme" aria-label="Toggle theme">{svg('moon')}</button></div>
</header>
<nav class="side" id="side">{side}
  <div class="sidefoot">{f'<a class="sub" href="{e(nl)}">Get the monthly top fixes</a>' if nl else ''}
  <a href="{BASE}/about/">About</a> · <a href="{BASE}/privacy/">Privacy</a> · <a href="{BASE}/imprint/">Imprint</a><br>Not affiliated with Reddit or YouTube.</div>
</nav>
<div class="scrim" id="scrim"></div>
<main class="main">{body}</main>
<script src="{BASE}/static/app.js?v={e(VDATA['generated'])}2" defer></script>
</body></html>"""
    dest = os.path.join(OUT, path.strip("/"), "index.html") if not path.endswith(".html") else os.path.join(OUT, path.strip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(doc)
    if canonical:
        SITEMAP.append(full)


def thumb(vid, q="mqdefault"):
    return f"https://i.ytimg.com/vi/{vid}/{q}.jpg"


def card(v, n=None, ok=None, rank=None):
    n = v["recs"] if n is None else n
    ok = v.get("success", 0) if ok is None else ok
    href = f"{BASE}/watch/{v['vid']}/" if v["page"] else f"https://www.youtube.com/watch?v={v['vid']}"
    dur = fmt_dur(v.get("duration_s"))
    yrs = v.get("years") or []
    sub = f"{fmt_n(v['views'])} views" if v.get("views") else (f"recommended {yrs[0]}–{yrs[1]}" if yrs and yrs[0] != yrs[1] else (f"recommended {yrs[0]}" if yrs else ""))
    ch = f'<a href="{BASE}/coach/{v["cs"]}/">{e(v["channel"])}</a>' if v["cs"] in COACH_SET else e(v["channel"])
    return f"""<article class="vc">
<a class="th" href="{href}"><img loading="lazy" src="{thumb(v['vid'])}" alt="">{f'<span class="rk">#{rank}</span>' if rank else ''}{f'<span class="du">{dur}</span>' if dur else ''}</a>
<div class="vm"><h3><a href="{href}">{e(v['title'])}</a></h3>
<p class="ch">{ch}</p>
<p class="st"><b>{n}</b> golfer{'s' if n != 1 else ''} recommend{'s' if n == 1 else ''}{f' · <span class="ok">✓ {ok} fixed it</span>' if ok else ''}{f' · {sub}' if sub else ''}</p></div>
</article>"""


def chips(active=None):
    tops = sorted([p for p in PROBLEMS if p["video_count"]], key=lambda p: -p["total_recs"])[:14]
    c = f'<a class="chip{" on" if not active else ""}" href="{BASE}/">All</a>'
    c += "".join(f'<a class="chip{" on" if active == p["key"] else ""}" href="{BASE}/fix/{p["slug"]}/">{e(p["name"])}</a>' for p in tops)
    return f'<div class="chips">{c}<a class="chip" href="{BASE}/categories/">All problems →</a></div>'


# ---------- pages ----------
def build_home():
    top = sorted(WATCH.values(), key=lambda v: -(v["recs"] + 0.75 * v.get("success", 0)))[:60]
    body = f"""{chips()}
<section class="intro"><h1>The golf fixes golfers <em>actually</em> recommend.</h1>
<p>{TOTAL_RECS:,} times, golfers answered another golfer's swing question with a YouTube lesson. We counted them. Pick your problem or browse the most recommended lessons.</p></section>
<div class="grid">{''.join(card(v) for v in top)}</div>"""
    page("/", f"{SITE['name']}: {SITE['tagline']}", SITE["description"], body, nav="home",
         ld={"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": URL + "/",
             "potentialAction": {"@type": "SearchAction", "target": URL + "/search/?q={q}", "query-input": "required name=q"}})


def build_problem(p):
    rows = by_problem[p["key"]]
    if not rows:
        return
    ok_total = sum(r[2] for r in rows)
    aids = LINKS.get("problem_aids", {}).get(p["key"], [])
    aid_html = ('<div class="aids"><b>Training aids golfers mention</b> <span class="ad">Ad</span> ' + " · ".join(
        f'<a href="{BASE}/go/{e(a["slug"])}/" rel="sponsored noopener">{e(a["name"])}</a>' for a in aids) + "</div>") if aids else ""
    body = f"""{chips(p['key'])}
<section class="intro"><p class="kick">{e(p['group'])}</p><h1>{e(p['q'])}</h1>
<p>{e(p['intro'])}</p>
<p class="meta"><b>{p['video_count']}</b> lessons ranked by <b>{p['total_recs']:,}</b> independent recommendations{f' · <b>{ok_total}</b> golfers said it fixed it' if ok_total else ''}. <a href="{BASE}/about/">How we count</a></p>{aid_html}</section>
<div class="grid">{''.join(card(v, n, ok, i + 1) for i, (s, n, ok, v) in enumerate(rows))}</div>"""
    page(f"/fix/{p['slug']}/", f"{p['q']} {p['video_count']} lessons golfers recommend | {SITE['name']}",
         f"{p['intro']} Ranked by {p['total_recs']:,} independent recommendations from golfers.", body, nav="cat",
         og=f"{URL}/static/og/{p['slug']}.png",
         ld={"@context": "https://schema.org", "@type": "ItemList", "name": p["q"], "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": f"{URL}/watch/{r[3]['vid']}/", "name": r[3]["title"]} for i, r in enumerate(rows[:10])]})


def build_categories():
    boxes = ""
    for g in GROUPS:
        ps = sorted([p for p in PROBLEMS if p["group"] == g and p["video_count"]], key=lambda p: -p["total_recs"])
        if not ps:
            continue
        boxes += f'<div class="box"><h2>{e(g)}<span>{sum(p["total_recs"] for p in ps):,}</span></h2>' + "".join(
            f'<a href="{BASE}/fix/{p["slug"]}/">{e(p["name"])}<span>{p["total_recs"]:,}</span></a>' for p in ps) + "</div>"
    page("/categories/", f"Golf problems | {SITE['name']}", "Every golf problem with the lessons golfers recommend for it.",
         f'<h1 class="ptitle">Problems</h1><div class="boxes">{boxes}</div>', nav="cat")


def build_watch(v):
    tc = sorted((v.get("topic_counts") or {}).items(), key=lambda x: -x[1])
    tags = "".join(f'<a class="tag" href="{BASE}/fix/{PNAME[t]["slug"]}/">{e(PNAME[t]["name"])} · {n}</a>' for t, n in tc if t in PNAME)
    notes = []
    for t, _ in tc:
        for x in (v.get("t_notes") or {}).get(t, []):
            x = x.strip().rstrip(".")
            if len(x) >= 8 and not re.search(r"[\"'“”‘’]", x) and x.lower() not in {y.lower() for y in notes}:
                notes.append(x[0].upper() + x[1:])
    notes = notes[:6]
    rel_src = by_problem.get(v["top"], []) if v["top"] else []
    rel = [r[3] for r in rel_src if r[3]["vid"] != v["vid"]][:12]
    if len(rel) < 12:
        rel += [x for x in sorted(channels[v["cs"]]["videos"], key=lambda x: -x["recs"]) if x["vid"] != v["vid"] and x["page"] and x not in rel][: 12 - len(rel)]
    upnext = "".join(f'<a class="un" href="{BASE}/watch/{x["vid"]}/"><span class="th"><img loading="lazy" src="{thumb(x["vid"])}" alt=""></span>'
                     f'<span><b>{e(x["title"])}</b><i>{e(x["channel"])}</i><i>{x["recs"]} golfers recommend</i></span></a>' for x in rel)
    yrs = v.get("years") or []
    ch = f'<a href="{BASE}/coach/{v["cs"]}/">{e(v["channel"])}</a>' if v["cs"] in COACH_SET else e(v["channel"])
    body = f"""<div class="watch"><div class="wl">
<button class="player" data-vid="{e(v['vid'])}" aria-label="Play"><img src="{thumb(v['vid'], 'hqdefault')}" alt=""><span class="pb"></span></button>
<h1 class="vt">{e(v['title'])}</h1>
<p class="vch">{ch}</p>
<p class="vst"><b>{v['recs']}</b> golfers recommended it{f' · <span class="ok">✓ {v["success"]} said it fixed their problem</span>' if v.get('success') else ''}{f' · {yrs[0]}–{yrs[1]}' if yrs and yrs[0] != yrs[1] else ''}</p>
<div class="acts" data-vid="{e(v['vid'])}" data-t="{e(v['title'])}" data-c="{e(v['channel'])}">
<button class="pill" data-act="liked">{svg('like')}<span>Like</span></button>
<button class="pill" data-act="later">{svg('later')}<span>Watch later</span></button>
<a class="pill" href="https://www.youtube.com/watch?v={e(v['vid'])}" target="_blank" rel="noopener nofollow">{svg('ext')}<span>YouTube</span></a></div>
<div class="desc">{f'<p><b>Why golfers recommend it</b></p><ul>' + ''.join(f'<li>{e(x)}</li>' for x in notes) + '</ul>' if notes else ''}
<p class="dim">Summaries are written by AI from what golfers said about the video.</p>
<div class="tags">{tags}</div></div>
</div><aside class="wr"><h2>Up next</h2>{upnext}</aside></div>"""
    page(f"/watch/{v['vid']}/", f"{v['title']} | {SITE['name']}",
         f"{v['recs']} golfers recommended this {v['channel']} lesson" + (f" for {PNAME[v['top']]['name'].lower()}" if v["top"] in PNAME else "") + ".",
         body, cls="wpage",
         ld={"@context": "https://schema.org", "@type": "VideoObject", "name": v["title"], "thumbnailUrl": thumb(v["vid"], "hqdefault"),
             "uploadDate": v.get("published") or f"{(v.get('years') or [2020])[0]}-01-01", "description": f"{v['recs']} golfers recommended this lesson.",
             "embedUrl": f"https://www.youtube-nocookie.com/embed/{v['vid']}"})


def build_coaches():
    rows = "".join(f'<a class="crow" href="{BASE}/coach/{s}/"><span class="n">{i}</span><b>{e(c["name"])}</b>'
                   f'<span>{c["recs"]:,} recommendations · {len(c["videos"])} videos</span>'
                   f'<i>{e(", ".join(PNAME[t]["name"] for t, _ in c["topics"].most_common(3) if t in PNAME))}</i></a>' for i, (s, c) in enumerate(COACHES, 1))
    page("/coaches/", f"Most recommended golf coaches on YouTube | {SITE['name']}",
         "The YouTube golf instructors golfers recommend most, ranked by independent recommendations.",
         f'<h1 class="ptitle">Most recommended coaches</h1><p class="lead">Ranked by how often golfers recommended their lessons to other golfers.</p><div class="clist">{rows}</div>', nav="coaches")


def badge_svg(a, b):
    w1 = 10 + 7 * len(a); w = w1 + 12 + 7 * len(b)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="28" role="img" aria-label="{e(a)}: {e(b)}"><rect width="{w}" height="28" rx="6" fill="#0b3d2c"/>'
            f'<rect x="{w1}" width="{w - w1}" height="28" rx="6" fill="#e8f5ee"/><rect x="{w1}" width="8" height="28" fill="#e8f5ee"/>'
            f'<g font-family="system-ui,Segoe UI,Roboto,sans-serif" font-size="12" font-weight="600"><text x="8" y="18" fill="#fff">{e(a)}</text>'
            f'<text x="{w1 + 6}" y="18" fill="#0b3d2c">{e(b)}</text></g></svg>')


def build_coach(s, c):
    vids = sorted([v for v in c["videos"]], key=lambda v: -v["recs"])[:48]
    tops = " ".join(f'<a class="tag" href="{BASE}/fix/{PNAME[t]["slug"]}/">{e(PNAME[t]["name"])} · {n}</a>' for t, n in c["topics"].most_common(8) if t in PNAME)
    badges = ""
    os.makedirs(os.path.join(OUT, "badge"), exist_ok=True)
    for p in coach_wins.get(s, [])[:3]:
        fn = f"{s}--{p['slug']}.svg"
        open(os.path.join(OUT, "badge", fn), "w").write(badge_svg(SITE["name"], f"#1 recommended for {p['name'].lower()}"))
        code = f'<a href="{URL}/fix/{p["slug"]}/"><img src="{URL}/badge/{fn}" alt="#1 recommended for {e(p["name"].lower())} on {e(SITE["name"])}"></a>'
        badges += f'<div class="badge"><img src="{BASE}/badge/{fn}" alt=""><textarea readonly rows="2">{e(code)}</textarea></div>'
    body = f"""<section class="chead"><div class="av">{e((c['name'] or '?')[0])}</div><div>
<h1>{e(c['name'])}</h1><p class="dim"><b>{c['recs']:,}</b> recommendations · <b>{len(c['videos'])}</b> videos{f' · <span class="ok">✓ {c["success"]} said it fixed their problem</span>' if c['success'] else ''}</p>
<div class="tags">{tops}</div>{f'<p><a href="{e(c["url"])}" target="_blank" rel="noopener nofollow">YouTube channel ↗</a></p>' if c.get('url') else ''}</div></section>
{f'<section class="badges"><b>Ranked #1 on {e(SITE["name"])}</b> · embed code for your site{badges}</section>' if badges else ''}
<div class="grid">{''.join(card(v) for v in vids)}</div>"""
    page(f"/coach/{s}/", f"{c['name']}: most recommended lessons | {SITE['name']}",
         f"The {c['name']} lessons golfers recommend most, ranked by {c['recs']:,} independent recommendations.", body, nav="coaches")


def build_report():
    st = SITE["stats"]
    ps = sorted([p for p in PROBLEMS if p["total_recs"]], key=lambda p: -p["total_recs"])
    mx = ps[0]["total_recs"]
    bars = "".join(f'<div class="bar"><a href="{BASE}/fix/{p["slug"]}/">{e(p["name"])}</a><span class="b" style="--w:{100 * p["total_recs"] / mx:.1f}%"></span><span>{p["total_recs"]:,}</span></div>' for p in ps)
    cmx = COACHES[0][1]["recs"]
    cb = "".join(f'<div class="bar"><a href="{BASE}/coach/{s}/">{e(c["name"])}</a><span class="b" style="--w:{100 * c["recs"] / cmx:.1f}%"></span><span>{c["recs"]:,}</span></div>' for s, c in COACHES[:15])
    body = f"""<div class="prose"><h1 class="ptitle">What golfers recommend to each other</h1>
<div class="kpis"><div><b>{st['comments_scanned']}</b>comments read</div><div><b>{st['yt_comments']}</b>with a YouTube link</div><div><b>{TOTAL_RECS:,}</b>lesson recommendations</div><div><b>{len(WATCH):,}</b>lessons ranked</div></div>
<h2>Problems golfers ask about most</h2><div class="bars">{bars}</div><h2>Most recommended coaches</h2><div class="bars">{cb}</div>
<p class="dim">Free to cite with a link to {e(SITE['name'])}. Method: <a href="{BASE}/about/">About</a>.</p></div>"""
    page("/report/", f"What golfers recommend to each other: the data | {SITE['name']}",
         f"Which golf problems golfers ask about most and which YouTube coaches they recommend, from {st['comments_scanned']} comments.", body, nav="stats", og=f"{URL}/static/og/report.png")


def build_text():
    st = SITE["stats"]
    about = f"""<div class="prose"><h1 class="ptitle">{e(SITE['name'])}</h1><p class="lead">The YouTube golf lessons golfers keep telling each other to watch.</p>
<div class="kpis"><div><b>{len(WATCH):,}</b>lessons</div><div><b>{st['comments_scanned']}</b>comments read</div><div><b>{len([p for p in PROBLEMS if p['video_count']])}</b>problems</div><div><b>{st['period']}</b>years</div></div>
<h2>Why</h2><p>YouTube's recommendations are tuned for watch time, not for fixing your slice. Meanwhile golfers in online communities answer each other's swing questions every day with a link to the one lesson that finally helped them. Those answers are scattered across years of threads. {e(SITE['name'])} collects and counts them.</p>
<h2>How it was built</h2><ol>
<li><b>Read the threads.</b> {st['comments_scanned']} public comments from golf-instruction communities ({st['period']}) were scanned for YouTube links: {st['yt_comments']} comments.</li>
<li><b>Read each comment with an AI model.</b> Is it a real lesson recommendation, not a meme, highlight or gear review? Which problem is it about? Does the golfer say it fixed it?</li>
<li><b>Count independent golfers.</b> Each golfer counts once per video. A lesson needs at least {MIN} different golfers recommending it for a problem.</li>
<li><b>Rank per problem</b> by those recommendations, with extra weight when golfers report it actually fixed their problem.</li></ol>
<h2>Promises</h2><p>Nobody can pay to rank higher. Sponsored content or affiliate links, if they ever appear, are labeled and kept out of the rankings. We don't republish anyone's comments or usernames.</p>
<h2>Your data</h2><p>Liked, history and watch later are stored only in your browser.</p></div>"""
    page("/about/", f"About | {SITE['name']}", "How GolfVotes ranks golf lessons by independent recommendations.", about)
    page("/privacy/", f"Privacy | {SITE['name']}", "Privacy.", f"""<div class="prose"><h1 class="ptitle">Privacy</h1>
<p>No cookies, no analytics, no tracking. Liked videos, history, watch later and your theme are stored only in your browser (localStorage).</p>
<p><b>YouTube:</b> Video thumbnails are loaded from YouTube's image servers (i.ytimg.com), which receive your IP address. Videos play only after you click; then your browser connects to youtube-nocookie.com under Google's privacy policy.</p>
<p><b>Hosting:</b> {e(SITE.get('hosting_note', ''))}</p><p>{e(SITE.get('privacy_contact', ''))}</p></div>""")
    page("/imprint/", f"Imprint | {SITE['name']}", "Imprint.", f'<div class="prose"><h1 class="ptitle">Imprint</h1>{SITE.get("imprint_html", "")}</div>')
    for slug, nav, title, empty in [("liked", "liked", "Liked", "Videos you like show up here."), ("history", "history", "History", "Videos you open show up here."),
                                    ("later", "later", "Watch later", "Save videos to watch later."), ("search", "", "Search", "")]:
        page(f"/{slug}/", f"{title} | {SITE['name']}", title, f'<h1 class="ptitle" id="ltitle">{title}</h1><div class="grid" id="list" data-list="{slug}"></div><p class="dim" id="empty">{empty}</p>',
             nav=nav, canonical=False)


def build_index():
    """Compact client-side index for search, liked, history, later."""
    idx = [[v["vid"], v["title"], v["channel"], v["cs"] if v["cs"] in COACH_SET else "", v["recs"], v.get("success", 0),
            PNAME[v["top"]]["name"] if v["top"] in PNAME else ""] for v in sorted(WATCH.values(), key=lambda x: -x["recs"])]
    probs = [[p["slug"], p["name"], p["q"], p["total_recs"]] for p in PROBLEMS if p["video_count"]]
    coaches = [[s, c["name"], c["recs"]] for s, c in COACHES]
    json.dump({"v": idx, "p": probs, "c": coaches}, open(os.path.join(OUT, "static", "index.json"), "w"), separators=(",", ":"), ensure_ascii=False)


def build_misc():
    for slug, target in (LINKS.get("go") or {}).items():
        d = os.path.join(OUT, "go", slug); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={e(target)}"><a href="{e(target)}" rel="sponsored">Continue</a>')
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /go/\nSitemap: {URL}/sitemap.xml\n")
    page("/404.html", f"Not found | {SITE['name']}", "Not found.", f'<h1 class="ptitle">Not found</h1><p><a href="{BASE}/">Find your golf fix</a></p>', canonical=False)
    open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                                                     "".join(f"<url><loc>{e(u)}</loc></url>" for u in SITEMAP) + "</urlset>")
    if SITE.get("cname"):
        open(os.path.join(OUT, "CNAME"), "w").write(SITE["cname"] + "\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(OUT, "static"))
    build_home(); build_categories()
    for p in PROBLEMS:
        build_problem(p)
    for v in WATCH.values():
        build_watch(v)
    build_coaches()
    for s, c in COACHES:
        build_coach(s, c)
    build_report(); build_text(); build_index(); build_misc()
    print(f"built {len(SITEMAP)} indexed pages, {len(WATCH)} watch pages, {len(COACHES)} coaches -> {OUT}")
