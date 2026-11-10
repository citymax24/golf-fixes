"""GolfVotes static site generator (HackerTube-style layout). Standard library only.

Usage: python3 build/build.py  -> writes _site/
Inputs: data/site.json, data/problems.json, data/videos.json, data/links.json (optional)
"""
import hashlib, html, json, os, re, shutil, sys, urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
D = lambda f: json.load(open(os.path.join(ROOT, "data", f)))
SITE, PROBLEMS, VDATA = D("site.json"), D("problems.json"), D("videos.json")
LINKS = D("links.json") if os.path.exists(os.path.join(ROOT, "data", "links.json")) else {}
VIDEOS = VDATA["videos"]
_opt = lambda f, d: D(f) if os.path.exists(os.path.join(ROOT, "data", f)) else d
COMMENTS = _opt("comments.json", {})
META = {m["vid"]: m for m in _opt("video_meta.json", [])}
PLANS = _opt("plans.json", [])
SEO = _opt("seo.json", {})
CARDS = _opt("cards.json", {})
RECENCY = _opt("recency.json", {})
REDDIT = _opt("reddit.json", {})
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
lastrec = lambda vid: (MON[int(RECENCY[vid][5:7]) - 1] + " " + RECENCY[vid][:4]) if RECENCY.get(vid) else ""
TYPES = {"drill": "Drill", "explainer": "Explainer", "lesson": "Live lesson", "pro_swing": "Pro swing", "quick_tip": "Quick tip",
         "practice_plan": "Practice plan", "fitness": "Fitness", "other": "Other"}
LEVELS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced", "all": "All levels"}
BASE = SITE["base_path"].rstrip("/")
URL = SITE["base_url"].rstrip("/")
MIN = SITE.get("min_recs_per_problem", 2)
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)
PNAME = {p["key"]: p for p in PROBLEMS}
SITEMAP = []
_h = lambda f: hashlib.md5(open(os.path.join(ROOT, "static", f), "rb").read()).hexdigest()[:8]
ASSET_V = {"css": _h("style.css"), "js": _h("app.js")}


def trunc(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0].rstrip(" ,.;:–-|") + "…"


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]+")


def nice(t):
    t = t or ""
    t = _EMOJI.sub("", t)
    t = re.sub(r"(?<=\w)'(?=\w)", "\u2019", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        small = {"a", "an", "the", "and", "or", "to", "for", "of", "in", "on", "with", "your", "at", "by"}
        w = t.lower().split(" ")
        t = " ".join(x if (i and x in small) else x[:1].upper() + x[1:] for i, x in enumerate(w))
    return t


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
# Coach URLs must not change when a channel is renamed (embedded badges point at them): remember slugs by channel URL and name.
SLUGS_FN = os.path.join(ROOT, "data", "coach_slugs.json")
SLUGS = json.load(open(SLUGS_FN)) if os.path.exists(SLUGS_FN) else {"url": {}, "name": {}}
for v in VIDEOS:
    u, nm = v.get("channel_url") or "", v.get("channel") or ""
    v["cs"] = SLUGS["url"].get(u) or SLUGS["name"].get(nm) or slugify(nm)
    if u:
        SLUGS["url"].setdefault(u, v["cs"])
    if nm:
        SLUGS["name"].setdefault(nm, v["cs"])
    tc = v.get("topic_counts") or {}
    v["top"] = max(tc, key=tc.get) if tc else None
    v["page"] = v["recs"] >= MIN          # gets its own watch page
    m = META.get(v["vid"], {})
    v["type"], v["level"], v["summary"] = m.get("type"), m.get("level"), m.get("summary")
WATCH = {v["vid"]: v for v in VIDEOS if v["page"]}
TITLE_COUNT = Counter(v["title"].lower() for v in WATCH.values())
USED = Counter()

by_problem = {}
for p in PROBLEMS:
    k, rows = p["key"], []
    for v in VIDEOS:
        n = (v.get("topic_counts") or {}).get(k, 0)
        if n >= MIN:
            ok = (v.get("t_success") or {}).get(k, 0)
            rows.append((n + 0.001 * ok + 0.00001 * min(v["recs"], 50), n, ok, v))
    rows.sort(key=lambda r: -r[0])
    by_problem[k] = rows[: SITE.get("max_videos_per_problem", 60)]
    p["total_recs"], p["video_count"] = sum(r[1] for r in rows), len(rows)

channels = defaultdict(lambda: {"recs": 0, "success": 0, "videos": [], "topics": Counter(), "url": None, "name": None})
for v in WATCH.values():
    c = channels[v["cs"]]
    c["name"], c["url"] = v.get("channel"), v.get("channel_url")
    c["recs"] += v["recs"]; c["success"] += v.get("success", 0); c["videos"].append(v)
    for t, n in (v.get("topic_counts") or {}).items():
        c["topics"][t] += n
COACHES = sorted([(s, c) for s, c in channels.items() if c["recs"] >= SITE.get("min_recs_per_coach", 10)], key=lambda x: -x[1]["recs"])
COACH_SET = {s for s, _ in COACHES}
AWARD_MIN = 10  # a '#1 most recommended' award needs at least this many recommendations and a clear lead over #2
coach_wins = defaultdict(list)
for p in PROBLEMS:
    r = by_problem[p["key"]]
    if r and r[0][1] >= AWARD_MIN and (len(r) == 1 or r[0][1] > r[1][1]):
        coach_wins[r[0][3]["cs"]].append(p)
TOTAL_RECS = sum(v["recs"] for v in VIDEOS)
GROUPS = ["Ball flight", "Contact", "Swing faults", "Swing sequence", "Setup", "Clubs", "Short game", "Training", "On the course"]

WORDMARK = open(os.path.join(ROOT, "static", "logo-word.svg")).read().strip().replace(' xmlns="http://www.w3.org/2000/svg"', "")

# ---------- icons ----------
I = {
    "menu": '<path d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"/>',
    "search": '<path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>',
    "help": '<path d="M11 18h2v-2h-2v2zm1-16C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2c0 2-3 1.75-3 5h2c0-2.25 3-2.5 3-5 0-2.21-1.79-4-4-4z"/>',
    "moon": '<path d="M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.39 5.39 0 0 1-4.4 2.26 5.4 5.4 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1z"/>',
    "home": '<path d="M4 21V10.08l8-6.96 8 6.96V21h-6v-6h-4v6H4z"/>',
    "cat": '<path d="M4 4h7v7H4zm2 2v3h3V6zm7-2h7v7h-7zm2 2v3h3V6zM4 13h7v7H4zm2 2v3h3v-3zm7-2h7v7h-7zm2 2v3h3v-3z"/>',
    "coach": '<path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>',
    "like": '<path transform="translate(1.2 1.2) scale(.9)" d="M9 21h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.58 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2zM9 9l4.34-4.34L12 10h9v2l-3 7H9V9zM1 9h4v12H1z"/>',
    "hist": '<path d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>',
    "later": '<path d="M14.97 16.95 10 13.87V7h2v5.76l4.03 2.49-1.06 1.7zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>',
    "stats": '<path d="M5 9h3v11H5zm5.5-5h3v16h-3zM16 13h3v7h-3z"/>',
    "ext": '<path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42L17.59 5H14V3zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/>',
    "dislike": '<path transform="translate(1.2 1.2) scale(.9)" d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm0 12l-4.34 4.34L12 14H3v-2l3-7h9v10zm4-12h4v12h-4z"/>',
    "play": '<path d="M8 5v14l11-7z"/>',
    "list": '<path d="M3 6h12v2H3zm0 4h12v2H3zm0 4h8v2H3zm12 0v6l5-3z"/>',
    "gear": '<path d="M19.14 12.94c.04-.31.06-.62.06-.94s-.02-.63-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96a7.02 7.02 0 0 0-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84a.48.48 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 0 0-.59.22L2.74 8.87a.48.48 0 0 0 .12.61l2.03 1.58c-.05.31-.09.63-.09.94s.02.63.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.48.48 0 0 0-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 15.6 12 3.6 3.6 0 0 1 12 15.6z"/>',
    "browse": '<path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/>',
    "data": '<path d="M12 3C7.58 3 4 4.79 4 7v10c0 2.21 3.59 4 8 4s8-1.79 8-4V7c0-2.21-3.58-4-8-4zm6 14c0 .5-2.13 2-6 2s-6-1.5-6-2v-2.23c1.61.78 3.72 1.23 6 1.23s4.39-.45 6-1.23V17zm0-4.55c-1.3.95-3.58 1.55-6 1.55s-4.7-.6-6-1.55V9.64c1.47.83 3.61 1.36 6 1.36s4.53-.53 6-1.36v2.81zM12 9C8.13 9 6 7.5 6 7s2.13-2 6-2 6 1.5 6 2-2.13 2-6 2z"/>',
    "check": '<path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>',
}
svg = lambda k: f'<svg viewBox="0 0 24 24" aria-hidden="true">{I[k]}</svg>'
CK = '<svg class="ck" viewBox="-6 -6 63.5 70.45" aria-hidden="true"><path d="M0 31.56L18.5 58.45L51.5 0"/></svg>'  # the check of the wordmark, drawn (a font glyph differs per device)


# ---------- layout ----------
def page(path, title, desc, body, nav="", og=None, ld=None, canonical=True, cls=""):
    full = URL + path
    title = title if len(title) <= 70 else trunc(title.rsplit(" | ", 1)[0], 57) + " | " + SITE["name"]
    desc = trunc(desc, 158)
    side = "".join(f'<a href="{BASE}{h}"{" class=on" if nav == n else ""}>{svg(ic)}<span>{lbl}</span></a>' for n, h, ic, lbl in [
        ("home", "/", "home", "Home"), ("cat", "/categories/", "cat", "Problems"), ("plans", "/plans/", "list", "Fix plans"),
        ("coaches", "/coaches/", "coach", "Coaches"), ("browse", "/browse/", "browse", "Browse"),
        ("liked", "/liked/", "like", "Liked"), ("later", "/later/", "later", "Watch later"), ("history", "/history/", "hist", "History"), ("about", "/about/", "help", "How we rank")])
    nl = SITE.get("newsletter_url")
    tnav = "".join(f'<a href="{BASE}{h}"' + (f' class="on" aria-current="{"page" if path == h else "true"}"' if nav == n else "") + f'>{lbl}</a>'
                   for n, h, lbl in [("cat", "/categories/", "Problems"), ("plans", "/plans/", "Fix plans"), ("coaches", "/coaches/", "Coaches"), ("browse", "/browse/", "Browse")])
    tnav += f'<a href="{BASE}/later/" id="tsaved" hidden>Saved</a><a href="{BASE}/about/"' + (' class="on" aria-current="page"' if nav == "about" else "") + '>How we rank</a>'
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
{f'<link rel="canonical" href="{e(full)}">' if canonical else ''}
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(full)}"><meta property="og:image" content="{e(og or URL + '/static/og3/default.png')}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{BASE}/static/favicon.svg?v=d" type="image/svg+xml"><link rel="apple-touch-icon" href="{BASE}/static/apple-touch-icon.png?v=d"><meta name="apple-mobile-web-app-title" content="GolfVotes"><meta name="application-name" content="GolfVotes">
{f'<meta name="google-site-verification" content="{e(SITE["google_verification"])}">' if SITE.get("google_verification") else ''}
<link rel="stylesheet" href="{BASE}/static/style.css?v={ASSET_V['css']}">
<script>try{{var t=localStorage.getItem("gv_theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{f'<script type="application/ld+json">{json.dumps(ld)}</script>' if ld else ''}
</head><body class="{cls}" data-base="{BASE}">
<a class="skip" href="#main">Skip to content</a>
<header class="top" id="top">
  <div class="left"><button class="icon" id="menu" aria-label="Menu" aria-expanded="false" aria-controls="side">{svg('menu')}</button>
  <a class="brand" href="{BASE}/" aria-label="{e(SITE['name'])} home">{WORDMARK}</a></div>
  <form class="search" id="searchform" action="{BASE}/search/" role="search"><span class="si" aria-hidden="true">{svg('search')}</span><input name="q" id="q" type="search" placeholder="Search a problem or lesson" autocomplete="off" aria-label="Search a problem or lesson" role="combobox" aria-expanded="false" aria-controls="sugg" aria-autocomplete="list"><kbd class="kh" aria-hidden="true">/</kbd><ul class="sugg" id="sugg" role="listbox" hidden></ul></form>
  <div class="right"><nav class="tnav" aria-label="Main">{tnav}</nav><button class="icon" id="stoggle" aria-label="Search" aria-expanded="false" aria-controls="searchform">{svg('search')}</button></div>
</header>
<nav class="side" id="side">{side}
</nav>
<div class="scrim" id="scrim"></div>
<main class="main" id="main" tabindex="-1">{body}
  <footer class="foot"><p class="fmsg"><span>Something wrong, missing or ranked badly? <a href="mailto:max@fassia.io?subject=GolfVotes%20feedback">Tell us</a></span> <span>Coaches: <a href="{BASE}/badges/">get your badges</a></span></p><p class="fthm"><button class="tbtn" id="theme" aria-pressed="false">Dark mode</button></p>{f'<a class="sub" href="{e(nl)}">Get the monthly top fixes</a>' if nl else ''}
  <nav class="fnav" aria-label="Footer"><a href="{BASE}/report/">Stats</a><a href="{BASE}/guides/best-golf-youtube-channels/">Best channels</a><a href="{BASE}/guides/best-golf-drills/">Best drills</a><a href="{BASE}/data/">Data</a><a href="{BASE}/settings/">Settings</a><a href="{BASE}/about/">About</a><a href="{BASE}/privacy/">Privacy</a><a href="{BASE}/imprint/">Imprint</a></nav>
  <p class="fnote">Not affiliated with Reddit or YouTube.</p></footer>
</main>
<script src="{BASE}/static/app.js?v={ASSET_V['js']}" defer></script>
<script data-goatcounter="https://golfvotes.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body></html>"""
    dest = os.path.join(OUT, path.strip("/"), "index.html") if not path.endswith(".html") else os.path.join(OUT, path.strip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(doc)
    if canonical:
        SITEMAP.append(full)


def thumb(vid, q="mq2"):
    """Preview images are self-hosted (static/thumbs, see build/fetch_thumbs.py) so visitors never contact Google
    just to see them. Other variants (og:image, JSON-LD) stay external: only crawlers fetch those."""
    if q in ("mq2", "hq2"):
        return f"{BASE}/static/thumbs/{q}/{vid}.webp"
    return f"https://i.ytimg.com/vi/{vid}/{q}.jpg"


MULTI = 0.6
_MW = json.load(open(os.path.join(os.path.dirname(__file__), "mini_wreath.json")))


def _digits(label, cap_h, cx=32.0, cy=34.6):
    """Rank number as outlines (no web font needed), scaled to ink height cap_h and centred optically:
    a '1' is placed between its ink centre and its stem centre, so the flag doesn't pull it off-axis."""
    sys.path.insert(0, os.path.dirname(__file__)); import badge_art
    d = badge_art.text_path(label, "InterDisplay-Black.otf", 100, 0, 0, -6 if len(label) > 1 else 0, anchor="start")
    n = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]
    pts = list(zip(n[0::2], n[1::2]))
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    mid = (x0 + x1) / 2
    if label.startswith("1"):
        w1 = (x1 - x0) if len(label) == 1 else (x1 - x0) * 0.45  # first glyph only for "10"
        foot = [p[0] for p in pts if p[1] > y1 - 0.04 * (y1 - y0) and p[0] <= x0 + w1]
        if foot and len(label) == 1:
            stem = (min(foot) + max(foot)) / 2
            mid = mid + 0.8 * (stem - mid)
        elif foot:  # "10": let the flag of the 1 hang out; centre between the stem's left edge and the right edge
            mid = mid + MULTI * ((min(foot) + x1) / 2 - mid)
    k = cap_h / (y1 - y0)
    return f'<path class="mst" transform="translate({cx - mid * k:.2f} {cy - (y0 + y1) / 2 * k:.2f}) scale({k:.4f})" d="{d}"/>'


def mini_seal(label="1", px=20):
    """Small GolfVotes seal: graded laurel with the rank number in deep green. Golden-ratio proportions:
    number height = height between the stems / phi (20.8 in the 64 grid); at 24 px and below it optically
    grows to wreath height / phi (24) so it stays legible. Colours come from CSS (.ms*)."""
    cap = (24.0 if px <= 24 else 20.8) * (0.86 if len(label) > 1 else 1)
    return (f'<svg class="ms" viewBox="0 0 64 64" width="{px}" height="{px}" aria-hidden="true">'
            f'<path class="mss" d="{_MW["stems"]}" fill="none" stroke-width="{3.0 if px < 28 else 2.2}" stroke-linecap="round"/><path class="msl" d="{_MW["leaves"]}"/>'
            f'{_digits(label, cap)}</svg>')


def award_text(a):
    return f'Top 10 most recommended channel {a["y"]}' if a["k"] == "top10" else f'#1 most recommended for {PNAME[a["k"]]["name"]} {a["y"]}'


def coach_mark(s, count=False):
    """Mini seal next to a coach name when the channel holds GolfVotes awards (details in the tooltip)."""
    a = [x for x in AWARDS.get(s, []) if x["k"] != "live"]
    if not a:
        return ""
    t = "GolfVotes awards: " + "; ".join(award_text(x) for x in a[:4]) + (f"; and {len(a) - 4} more" if len(a) > 4 else "")
    lab = "1" if any(x["k"] != "top10" for x in a) else "10"
    extra = f'<b>{len(a)} award{"s" if len(a) > 1 else ""}</b>' if count else ""
    return f'<span class="lau" title="{e(t)}" role="img" aria-label="{e(t)}">{mini_seal(lab, 20)}{extra}</span>'


PKEY = {p["name"]: p["key"] for p in PROBLEMS}
HQ2 = {f.rsplit(".", 1)[0] for f in os.listdir(os.path.join(ROOT, "static", "thumbs", "hq2"))}
HQ_SRCSET = ' srcset="{a} 320w, {b} 480w" sizes="(max-width:600px) 100vw, (max-width:1000px) 50vw, 33vw"'
RK4_SRCSET = ' srcset="{a} 320w, {b} 480w" sizes="(max-width:900px) 120px, 400px"'


def card(v, n=None, ok=None, rank=None, pname=None, extra="", hq=False):
    n = v["recs"] if n is None else n
    ok = v.get("success", 0) if ok is None else ok
    win = bool(rank == 1 and pname and any(x["k"] == PKEY.get(pname) for x in AWARDS.get(v["cs"], [])))  # gold only for a real award
    href = f"{BASE}/watch/{v['vid']}/" if v["page"] else f"https://www.youtube.com/watch?v={v['vid']}"
    dur = fmt_dur(v.get("duration_s"))
    yrs = v.get("years") or []
    sub = f"{fmt_n(v['views'])} views" if v.get("views") else (f"recommended {yrs[0]}–{yrs[1]}" if yrs and yrs[0] != yrs[1] else (f"recommended {yrs[0]}" if yrs else ""))
    ch = f'<a href="{BASE}/coach/{v["cs"]}/">{e(v["channel"])}</a>' if v["cs"] in COACH_SET else e(v["channel"])
    return f"""<article class="vc" data-vid="{e(v['vid'])}">
<div class="thw" data-vid="{e(v['vid'])}"><a class="th" href="{href}"><img loading="lazy" src="{thumb(v['vid'], 'hq2' if pname and rank and rank <= 3 and v['vid'] in HQ2 else 'mq2')}"{HQ_SRCSET.format(a=thumb(v['vid']), b=thumb(v['vid'], 'hq2')) if hq and v['vid'] in HQ2 else ''}{RK4_SRCSET.format(a=thumb(v['vid']), b=thumb(v['vid'], 'hq2')) if pname and rank == 4 and v['vid'] in HQ2 else ''} alt="">{f'<span class="rk{" g1" if win else ""}"{" title=" + chr(34) + "Most recommended lesson for this problem, GolfVotes award" + chr(34) if win else ""}>#{rank}</span>' if rank else ''}{f'<span class="du">{dur}</span>' if dur else ''}</a><button class="lb" aria-label="Watch later" title="Watch later">{svg('later')}</button></div>
<div class="vm"><h3><a href="{href}">{e(nice(v['title']))}</a></h3>
<p class="ch">{ch}{f' · {TYPES[v["type"]]}' if v.get("type") in TYPES and v["type"] != "other" else ''}</p>
<p class="st"><span><b>{n}</b> recommend{"s" if n == 1 else ""}</span>{f'<span class="ok">{CK}{ok} fixed it</span>' if ok else ''}{f'<span class="nw">{sub}</span>' if sub and not pname else ''}</p>{extra}</div>
</article>"""


def chips(active=None):
    order = ["slice", "shank", "early_extension", "over_the_top", "hook", "fat_thin", "driver_distance", "iron_contact", "chipping",
             "putting", "casting_lag", "bunker", "wedges_pitching", "rotation_hips", "takeaway_backswing", "setup_posture", "grip"]
    tops = sorted([q for q in PROBLEMS if q["video_count"] >= 5], key=lambda q: (q["key"] not in ("slice", "shank"), -q["video_count"]))[:14]
    c = f'<a class="chip{" on" if not active else ""}" href="{BASE}/">All</a>'
    c += "".join(f'<a class="chip{" on" if active == p["key"] else ""}" href="{BASE}/fix/{p["slug"]}/">{e(p["name"])}</a>' for p in tops)
    return f'<div class="chips">{c}<a class="chip" href="{BASE}/categories/">All problems →</a></div>'


# ---------- pages ----------
MISSES = [  # key, end x, end y (in a 320x360 course), label right-handed, label left-handed, flight path, verdict
    ("slice", 262, 96, "Curves right", "Curves left", "M160 326C120 250 150 130 262 96", "That’s a slice."),
    ("hook", 58, 96, "Curves left", "Curves right", "M160 326C200 250 170 130 58 96", "That’s a hook."),
    ("over_the_top", 92, 44, "Pulled left", "Pulled right", "M160 326L92 44", "That’s a pull. Usually over the top."),
    ("shank", 252, 236, "Shoots right", "Shoots left", "M160 326L252 236", "That’s a shank."),
    ("driver_distance", 160, 150, "Straight, but short", "Straight, but short", "M160 326L160 150", "You’re leaving distance out there."),
    ("fat_thin", 160, 262, "Fat or thin", "Fat or thin", "M160 326L160 262", "Fat or thin contact."),
]


def finder():
    """Ball-flight finder: tap where the ball ends up, get the miss by name and what golfers recommend for it.
    Dots are real links to the problem page, so it works without JavaScript too."""
    ms = [m for m in MISSES if m[0] in PNAME and by_problem.get(m[0])]
    if len(ms) < 4:
        return ""
    dots = "".join(f'<a class="bfd" role="button" aria-pressed="false" href="{BASE}/fix/{PNAME[k]["slug"]}/" data-k="{k}" style="--x:{x / 3.2:.1f}%;--y:{y / 3.6:.1f}%">'
                   f'<span class="r">{e(lr)}</span><span class="l">{e(ll)}</span></a>' for k, x, y, lr, ll, d, h in ms)
    lines = "".join(f'<path class="bfl" data-k="{k}" d="{d}" pathLength="1"/>' for k, x, y, lr, ll, d, h in ms)
    panels = ""
    for k, x, y, lr, ll, d, h in ms:
        p = PNAME[k]; sc, n, ok, v = by_problem[k][0]
        href = f"{BASE}/watch/{v['vid']}/" if v["page"] else f"{BASE}/fix/{p['slug']}/"
        panels += (f'<div class="bfp" id="bf-{k}" hidden><h2>{e(h)}</h2><p>{e(p["intro"])}</p>'
                   f'<div class="bfv"><button class="bfplay" type="button" data-vid="{e(v["vid"])}" data-t="{e(nice(v["title"]))}" data-c="{e(v.get("channel") or "")}" aria-label="Play: {e(nice(v["title"]))}">'
                   f'<img loading="lazy" src="{thumb(v["vid"], "hq2" if v["page"] else "mq2")}" alt=""><span class="pb"></span></button></div>'
                   f'<a class="bftt" href="{href}"><i>Most recommended</i><b>{e(trunc(nice(v["title"]), 70))}</b>'
                   f'<em>{n} recommend{"s" if n == 1 else ""}{f" · ✓ {ok} fixed it" if ok else ""}</em></a>'
                   f'<p class="bfy">Not playing? <a href="https://www.youtube.com/watch?v={e(v["vid"])}" target="_blank" rel="noopener">Open it on YouTube ↗</a></p>'
                   f'<a class="pill start bfa" href="{BASE}/fix/{p["slug"]}/">See all {p["video_count"]} lessons →</a>'
                   f'<p class="bfs">{p["total_recs"]:,} recommendations from golfers for this miss.</p></div>')
    return f"""<div class="bf" id="bf"><div><p class="bfq"><b>What’s your miss?</b><span>Tap it to watch the #1 lesson.</span></p><div class="bfc"><svg viewBox="0 0 320 360" aria-hidden="true">
<defs><pattern id="bfst" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(-32)"><rect class="bfsp" width="10" height="20"/></pattern><pattern id="bfst2" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(32)"><rect class="bfsp" width="10" height="20"/></pattern><filter id="bfno" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 .25  0 0 0 0 .1  0 0 0 .55 -.18"/></filter></defs><path class="bfwd" d="M0 0H34C40 60 22 120 30 180C36 240 24 300 36 360H0Z"/><path class="bfwd" d="M320 0H288C280 70 300 130 292 190C286 250 298 310 286 360H320Z"/><path class="bfpath" d="M276 366C262 322 284 286 272 244C262 208 282 176 276 140C272 112 252 96 246 70C242 54 244 38 238 24"/><path class="bfcut" d="M126 372C118 340 104 318 110 288C116 262 138 250 134 224C130 198 100 186 98 156C96 128 116 116 126 100C132 90 136 84 142 80C150 76 172 76 180 80C190 86 206 94 212 112C220 134 206 150 206 172C206 196 222 208 222 236C222 262 200 276 200 302C200 330 206 350 198 372Z"/><path class="bfw" d="M126 372C118 340 104 318 110 288C116 262 138 250 134 224C130 198 100 186 98 156C96 128 116 116 126 100C132 90 136 84 142 80C150 76 172 76 180 80C190 86 206 94 212 112C220 134 206 150 206 172C206 196 222 208 222 236C222 262 200 276 200 302C200 330 206 350 198 372Z"/><path class="bfws" d="M126 372C118 340 104 318 110 288C116 262 138 250 134 224C130 198 100 186 98 156C96 128 116 116 126 100C132 90 136 84 142 80C150 76 172 76 180 80C190 86 206 94 212 112C220 134 206 150 206 172C206 196 222 208 222 236C222 262 200 276 200 302C200 330 206 350 198 372Z"/><path class="bfws2" d="M126 372C118 340 104 318 110 288C116 262 138 250 134 224C130 198 100 186 98 156C96 128 116 116 126 100C132 90 136 84 142 80C150 76 172 76 180 80C190 86 206 94 212 112C220 134 206 150 206 172C206 196 222 208 222 236C222 262 200 276 200 302C200 330 206 350 198 372Z"/><path class="bfpl" d="M38 276c8-9 26-11 36-4 9 6 12 18 4 25-9 8-27 9-37 2-8-6-9-16-3-23z"/><path class="bfpw" d="M41 278c7-7 22-8 30-3 7 5 9 14 3 20-8 6-23 7-31 1-6-5-7-12-2-18z"/><rect class="bftb" x="145" y="315" width="30" height="24" rx="4" transform="rotate(-5 160 327)"/><path class="bfgo" d="M150 18c12-4 30-2 38 8 7 9 6 22-1 31-7 9-16 16-29 17-13 1-27-4-32-15-5-11-1-23 6-31 5-6 11-8 18-10z"/><path class="bfgc" d="M150 18c12-4 30-2 38 8 7 9 6 22-1 31-7 9-16 16-29 17-13 1-27-4-32-15-5-11-1-23 6-31 5-6 11-8 18-10z"/><path class="bfg2" d="M150 18c12-4 30-2 38 8 7 9 6 22-1 31-7 9-16 16-29 17-13 1-27-4-32-15-5-11-1-23 6-31 5-6 11-8 18-10z"/><circle class="bflip" cx="59.8" cy="188.8" r="13"/><circle class="bflip" cx="72.8" cy="199.8" r="12"/><circle class="bflip" cx="63.8" cy="213.8" r="12"/><circle class="bflip" cx="76.8" cy="225.8" r="13"/><circle class="bflip" cx="62.8" cy="235.8" r="9"/><circle class="bfhi" cx="63.3" cy="184.5" r="13"/><circle class="bfhi" cx="76.3" cy="195.5" r="12"/><circle class="bfhi" cx="67.3" cy="209.5" r="12"/><circle class="bfhi" cx="80.3" cy="221.5" r="13"/><circle class="bfhi" cx="66.3" cy="231.5" r="9"/><circle class="bfs" cx="62.0" cy="186.0" r="13"/><circle class="bfs" cx="75.0" cy="197.0" r="12"/><circle class="bfs" cx="66.0" cy="211.0" r="12"/><circle class="bfs" cx="79.0" cy="223.0" r="13"/><circle class="bfs" cx="65.0" cy="233.0" r="9"/><circle class="bflip" cx="243.8" cy="158.8" r="12"/><circle class="bflip" cx="256.8" cy="166.8" r="11"/><circle class="bflip" cx="242.8" cy="173.8" r="10"/><circle class="bfhi" cx="247.3" cy="154.5" r="12"/><circle class="bfhi" cx="260.3" cy="162.5" r="11"/><circle class="bfhi" cx="246.3" cy="169.5" r="10"/><circle class="bfs" cx="246.0" cy="156.0" r="12"/><circle class="bfs" cx="259.0" cy="164.0" r="11"/><circle class="bfs" cx="245.0" cy="171.0" r="10"/><circle class="bflip" cx="238.8" cy="299.8" r="10"/><circle class="bflip" cx="251.8" cy="303.8" r="9"/><circle class="bfhi" cx="242.3" cy="295.5" r="10"/><circle class="bfhi" cx="255.3" cy="299.5" r="9"/><circle class="bfs" cx="241.0" cy="297.0" r="10"/><circle class="bfs" cx="254.0" cy="301.0" r="9"/><circle class="bflip" cx="205.8" cy="72.8" r="10"/><circle class="bflip" cx="216.8" cy="82.8" r="9"/><circle class="bflip" cx="203.8" cy="87.8" r="7"/><circle class="bfhi" cx="209.3" cy="68.5" r="10"/><circle class="bfhi" cx="220.3" cy="78.5" r="9"/><circle class="bfhi" cx="207.3" cy="83.5" r="7"/><circle class="bfs" cx="208.0" cy="70.0" r="10"/><circle class="bfs" cx="219.0" cy="80.0" r="9"/><circle class="bfs" cx="206.0" cy="85.0" r="7"/><circle class="bflip" cx="107.8" cy="90.8" r="9"/><circle class="bflip" cx="118.8" cy="97.8" r="7"/><circle class="bfhi" cx="111.3" cy="86.5" r="9"/><circle class="bfhi" cx="122.3" cy="93.5" r="7"/><circle class="bfs" cx="110.0" cy="88.0" r="9"/><circle class="bfs" cx="121.0" cy="95.0" r="7"/><circle class="bfsh" cx="18.1" cy="8.2" r="7.1"/><circle class="bftr" cx="22.0" cy="4" r="7"/><circle class="bftr2" cx="19.3" cy="1.8" r="4.3"/><circle class="bftr3" cx="24.5" cy="1.2" r="3.2"/><circle class="bfsh" cx="276.5" cy="8.2" r="7.1"/><circle class="bftr" cx="280.4" cy="4" r="7"/><circle class="bftr2" cx="277.7" cy="1.8" r="4.3"/><circle class="bftr3" cx="282.9" cy="1.2" r="3.2"/><circle class="bfsh" cx="10.2" cy="24.2" r="12.2"/><circle class="bftr" cx="16.8" cy="17" r="12"/><circle class="bftr2" cx="12.2" cy="13.2" r="7.4"/><circle class="bftr3" cx="21.1" cy="12.2" r="5.5"/><circle class="bfsh" cx="303.2" cy="24.2" r="12.2"/><circle class="bftr" cx="309.8" cy="17" r="12"/><circle class="bftr2" cx="305.2" cy="13.2" r="7.4"/><circle class="bftr3" cx="314.1" cy="12.2" r="5.5"/><circle class="bfsh" cx="19.6" cy="37.6" r="11.2"/><circle class="bftr" cx="25.6" cy="31" r="11"/><circle class="bftr2" cx="21.4" cy="27.5" r="6.8"/><circle class="bftr3" cx="29.6" cy="26.6" r="5.1"/><circle class="bfsh" cx="294.9" cy="37.6" r="11.2"/><circle class="bftr" cx="301.0" cy="31" r="11"/><circle class="bftr2" cx="296.8" cy="27.5" r="6.8"/><circle class="bftr3" cx="305.0" cy="26.6" r="5.1"/><circle class="bfsh" cx="18.7" cy="52.0" r="10.2"/><circle class="bftr" cx="24.2" cy="46" r="10"/><circle class="bftr2" cx="20.4" cy="42.8" r="6.2"/><circle class="bftr3" cx="27.8" cy="42.0" r="4.6"/><circle class="bfsh" cx="272.7" cy="52.0" r="10.2"/><circle class="bftr" cx="278.2" cy="46" r="10"/><circle class="bftr2" cx="274.4" cy="42.8" r="6.2"/><circle class="bftr3" cx="281.8" cy="42.0" r="4.6"/><circle class="bfsh" cx="14.1" cy="67.4" r="9.2"/><circle class="bftr" cx="19.0" cy="62" r="9"/><circle class="bftr2" cx="15.6" cy="59.1" r="5.6"/><circle class="bftr3" cx="22.2" cy="58.4" r="4.1"/><circle class="bfsh" cx="302.7" cy="67.4" r="9.2"/><circle class="bftr" cx="307.6" cy="62" r="9"/><circle class="bftr2" cx="304.2" cy="59.1" r="5.6"/><circle class="bftr3" cx="310.8" cy="58.4" r="4.1"/><circle class="bfsh" cx="23.4" cy="83.8" r="8.2"/><circle class="bftr" cx="27.8" cy="79" r="8"/><circle class="bftr2" cx="24.8" cy="76.4" r="5.0"/><circle class="bftr3" cx="30.7" cy="75.8" r="3.7"/><circle class="bfsh" cx="294.4" cy="83.8" r="8.2"/><circle class="bftr" cx="298.8" cy="79" r="8"/><circle class="bftr2" cx="295.8" cy="76.4" r="5.0"/><circle class="bftr3" cx="301.7" cy="75.8" r="3.7"/><circle class="bfsh" cx="22.5" cy="101.2" r="7.1"/><circle class="bftr" cx="26.4" cy="97" r="7"/><circle class="bftr2" cx="23.7" cy="94.8" r="4.3"/><circle class="bftr3" cx="28.9" cy="94.2" r="3.2"/><circle class="bfsh" cx="272.1" cy="101.2" r="7.1"/><circle class="bftr" cx="276.0" cy="97" r="7"/><circle class="bftr2" cx="273.3" cy="94.8" r="4.3"/><circle class="bftr3" cx="278.5" cy="94.2" r="3.2"/><circle class="bfsh" cx="14.6" cy="117.2" r="12.2"/><circle class="bftr" cx="21.2" cy="110" r="12"/><circle class="bftr2" cx="16.6" cy="106.2" r="7.4"/><circle class="bftr3" cx="25.5" cy="105.2" r="5.5"/><circle class="bfsh" cx="298.8" cy="117.2" r="12.2"/><circle class="bftr" cx="305.4" cy="110" r="12"/><circle class="bftr2" cx="300.8" cy="106.2" r="7.4"/><circle class="bftr3" cx="309.7" cy="105.2" r="5.5"/><circle class="bfsh" cx="23.9" cy="130.6" r="11.2"/><circle class="bftr" cx="30.0" cy="124" r="11"/><circle class="bftr2" cx="25.8" cy="120.5" r="6.8"/><circle class="bftr3" cx="34.0" cy="119.6" r="5.1"/><circle class="bfsh" cx="290.6" cy="130.6" r="11.2"/><circle class="bftr" cx="296.6" cy="124" r="11"/><circle class="bftr2" cx="292.4" cy="120.5" r="6.8"/><circle class="bftr3" cx="300.6" cy="119.6" r="5.1"/><circle class="bfsh" cx="23.1" cy="145.0" r="10.2"/><circle class="bftr" cx="28.6" cy="139" r="10"/><circle class="bftr2" cx="24.8" cy="135.8" r="6.2"/><circle class="bftr3" cx="32.2" cy="135.0" r="4.6"/><circle class="bfsh" cx="292.5" cy="145.0" r="10.2"/><circle class="bftr" cx="298.0" cy="139" r="10"/><circle class="bftr2" cx="294.2" cy="135.8" r="6.2"/><circle class="bftr3" cx="301.6" cy="135.0" r="4.6"/><circle class="bfsh" cx="18.4" cy="160.4" r="9.2"/><circle class="bftr" cx="23.4" cy="155" r="9"/><circle class="bftr2" cx="20.0" cy="152.1" r="5.6"/><circle class="bftr3" cx="26.6" cy="151.4" r="4.1"/><circle class="bfsh" cx="298.2" cy="160.4" r="9.2"/><circle class="bftr" cx="303.2" cy="155" r="9"/><circle class="bftr2" cx="299.8" cy="152.1" r="5.6"/><circle class="bftr3" cx="306.4" cy="151.4" r="4.1"/><circle class="bfsh" cx="290.0" cy="176.8" r="8.2"/><circle class="bftr" cx="294.4" cy="172" r="8"/><circle class="bftr2" cx="291.4" cy="169.4" r="5.0"/><circle class="bftr3" cx="297.3" cy="168.8" r="3.7"/><circle class="bfsh" cx="3.6" cy="176.8" r="8.2"/><circle class="bftr" cx="8.0" cy="172" r="8"/><circle class="bftr2" cx="5.0" cy="169.4" r="5.0"/><circle class="bftr3" cx="10.9" cy="168.8" r="3.7"/><circle class="bfsh" cx="26.9" cy="194.2" r="7.1"/><circle class="bftr" cx="30.8" cy="190" r="7"/><circle class="bftr2" cx="28.1" cy="187.8" r="4.3"/><circle class="bftr3" cx="33.3" cy="187.2" r="3.2"/><circle class="bfsh" cx="291.9" cy="194.2" r="7.1"/><circle class="bftr" cx="295.8" cy="190" r="7"/><circle class="bftr2" cx="293.1" cy="187.8" r="4.3"/><circle class="bftr3" cx="298.3" cy="187.2" r="3.2"/><circle class="bfsh" cx="19.0" cy="210.2" r="12.2"/><circle class="bftr" cx="25.6" cy="203" r="12"/><circle class="bftr2" cx="21.0" cy="199.2" r="7.4"/><circle class="bftr3" cx="29.9" cy="198.2" r="5.5"/><circle class="bfsh" cx="294.4" cy="210.2" r="12.2"/><circle class="bftr" cx="301.0" cy="203" r="12"/><circle class="bftr2" cx="296.4" cy="199.2" r="7.4"/><circle class="bftr3" cx="305.3" cy="198.2" r="5.5"/><circle class="bfsh" cx="286.1" cy="223.6" r="11.2"/><circle class="bftr" cx="292.2" cy="217" r="11"/><circle class="bftr2" cx="288.0" cy="213.5" r="6.8"/><circle class="bftr3" cx="296.2" cy="212.6" r="5.1"/><circle class="bfsh" cx="4.1" cy="223.6" r="11.2"/><circle class="bftr" cx="10.2" cy="217" r="11"/><circle class="bftr2" cx="6.0" cy="213.5" r="6.8"/><circle class="bftr3" cx="14.2" cy="212.6" r="5.1"/><circle class="bfsh" cx="27.5" cy="238.0" r="10.2"/><circle class="bftr" cx="33.0" cy="232" r="10"/><circle class="bftr2" cx="29.2" cy="228.8" r="6.2"/><circle class="bftr3" cx="36.6" cy="228.0" r="4.6"/><circle class="bfsh" cx="288.1" cy="238.0" r="10.2"/><circle class="bftr" cx="293.6" cy="232" r="10"/><circle class="bftr2" cx="289.8" cy="228.8" r="6.2"/><circle class="bftr3" cx="297.2" cy="228.0" r="4.6"/><circle class="bfsh" cx="22.9" cy="253.4" r="9.2"/><circle class="bftr" cx="27.8" cy="248" r="9"/><circle class="bftr2" cx="24.4" cy="245.1" r="5.6"/><circle class="bftr3" cx="31.0" cy="244.4" r="4.1"/><circle class="bfsh" cx="293.9" cy="253.4" r="9.2"/><circle class="bftr" cx="298.8" cy="248" r="9"/><circle class="bftr2" cx="295.4" cy="245.1" r="5.6"/><circle class="bftr3" cx="302.0" cy="244.4" r="4.1"/><circle class="bfsh" cx="285.6" cy="269.8" r="8.2"/><circle class="bftr" cx="290.0" cy="265" r="8"/><circle class="bftr2" cx="287.0" cy="262.4" r="5.0"/><circle class="bftr3" cx="292.9" cy="261.8" r="3.7"/><circle class="bfsh" cx="8.0" cy="269.8" r="8.2"/><circle class="bftr" cx="12.4" cy="265" r="8"/><circle class="bftr2" cx="9.4" cy="262.4" r="5.0"/><circle class="bftr3" cx="15.3" cy="261.8" r="3.7"/><circle class="bfsh" cx="287.5" cy="287.2" r="7.1"/><circle class="bftr" cx="291.4" cy="283" r="7"/><circle class="bftr2" cx="288.7" cy="280.8" r="4.3"/><circle class="bftr3" cx="293.9" cy="280.2" r="3.2"/><circle class="bfsh" cx="290.0" cy="303.2" r="12.2"/><circle class="bftr" cx="296.6" cy="296" r="12"/><circle class="bftr2" cx="292.0" cy="292.2" r="7.4"/><circle class="bftr3" cx="300.9" cy="291.2" r="5.5"/><circle class="bfsh" cx="305.9" cy="316.6" r="11.2"/><circle class="bftr" cx="312.0" cy="310" r="11"/><circle class="bftr2" cx="307.8" cy="306.5" r="6.8"/><circle class="bftr3" cx="316.0" cy="305.6" r="5.1"/><circle class="bfsh" cx="8.5" cy="316.6" r="11.2"/><circle class="bftr" cx="14.6" cy="310" r="11"/><circle class="bftr2" cx="10.4" cy="306.5" r="6.8"/><circle class="bftr3" cx="18.6" cy="305.6" r="5.1"/><circle class="bfsh" cx="283.7" cy="331.0" r="10.2"/><circle class="bftr" cx="289.2" cy="325" r="10"/><circle class="bftr2" cx="285.4" cy="321.8" r="6.2"/><circle class="bftr3" cx="292.8" cy="321.0" r="4.6"/><circle class="bfsh" cx="31.9" cy="331.0" r="10.2"/><circle class="bftr" cx="37.4" cy="325" r="10"/><circle class="bftr2" cx="33.6" cy="321.8" r="6.2"/><circle class="bftr3" cx="41.0" cy="321.0" r="4.6"/><circle class="bfsh" cx="289.4" cy="346.4" r="9.2"/><circle class="bftr" cx="294.4" cy="341" r="9"/><circle class="bftr2" cx="291.0" cy="338.1" r="5.6"/><circle class="bftr3" cx="297.6" cy="337.4" r="4.1"/><circle class="bfsh" cx="3.0" cy="346.4" r="9.2"/><circle class="bftr" cx="8.0" cy="341" r="9"/><circle class="bftr2" cx="4.6" cy="338.1" r="5.6"/><circle class="bftr3" cx="11.2" cy="337.4" r="4.1"/><circle class="bfsh" cx="12.4" cy="362.8" r="8.2"/><circle class="bftr" cx="16.8" cy="358" r="8"/><circle class="bftr2" cx="13.8" cy="355.4" r="5.0"/><circle class="bftr3" cx="19.7" cy="354.8" r="3.7"/><circle class="bfsh" cx="305.4" cy="362.8" r="8.2"/><circle class="bftr" cx="309.8" cy="358" r="8"/><circle class="bftr2" cx="306.8" cy="355.4" r="5.0"/><circle class="bftr3" cx="312.7" cy="354.8" r="3.7"/><rect class="bfn" width="320" height="360" filter="url(#bfno)"/><ellipse class="bfcup" cx="160" cy="46.5" rx="5" ry="2"/><path class="bffs" d="M160 46L176 52"/><path class="bffh" d="M160 46V16"/><path class="bffp" d="M160 46V16"/><path class="bfff" d="M160.8 17c6-3 9 3 17-1v11c-8 4-11-2-17 1z"/>
<text class="bftx" x="160" y="12" text-anchor="middle">TARGET</text>{lines}<circle class="bfball" cx="160" cy="326" r="6"/><text class="bftx" x="160" y="352" text-anchor="middle">YOU</text></svg>{dots}</div>
<label class="bfh"><input type="checkbox" id="bflh"> I play left-handed</label></div>
<div class="bfr" aria-live="polite"><div class="bfp bf0" id="bf-0"><h2>Six misses. One tap.</h2><p>Pick the spot on the course where your shots usually end up. We name the miss and play the lesson golfers recommend most for it.</p></div>{panels}</div></div>"""


def build_home():
    top = sorted(WATCH.values(), key=lambda v: -(v["recs"] + 0.75 * v.get("success", 0)))[:60]
    def best(k):
        for sc, n, ok, v in by_problem.get(k, []):
            if v.get("top") == k and n >= 3:
                return sc, n, ok, v
        return None
    pick = [PNAME[k] for k in ["slice", "shank", "hook", "early_extension", "over_the_top", "driver_distance", "iron_contact", "chipping",
                               "putting", "casting_lag", "fat_thin", "bunker"] if k in PNAME and best(k)][:7]

    def tile(p):
        sc, n, ok, v = best(p["key"])
        proof = f'✓ {ok} say{"s" if ok == 1 else ""} it fixed it' if ok else f'{n} golfers recommend it'
        return (f'<a class="ptile" href="{BASE}/fix/{p["slug"]}/"><span class="pth"><img loading="lazy" src="{thumb(v["vid"])}" alt="">'
                f'</span><span class="pnm2">{e(p["name"])}</span><span class="ptop">Top pick: {e(trunc(nice(v["title"]), 44))}</span>'
                f'<span class="pok{" fx" if ok else ""}">{proof}</span></a>')
    tiles = "".join(tile(p) for p in pick)
    body = f"""<section class="welcome" id="welcome">
<h1 class="hq">Golf lessons, ranked by golfers.<span>{TOTAL_RECS:,} Reddit recommendations for YouTube lessons.</span></h1>
{finder()}
<p class="lede">We read {SITE["stats"]["comments_scanned"]} comments on r/GolfSwing and r/golftips and <a href="{BASE}/about/">counted</a> which YouTube lessons golfers recommend for each problem.</p>
<h2 class="pick">Or pick it by name</h2>
<div class="ptiles">{tiles}<a class="ptile more" href="{BASE}/categories/"><b>All {len([p for p in PROBLEMS if p["video_count"]])} problems →</b><span>{e(", ".join(q["name"] for q in sorted([q for q in PROBLEMS if q["video_count"] and q not in pick], key=lambda q: -q["video_count"])[:4]))} and more</span></a></div>
</section>
{chips()}
{('<h2 class="row">Watch these in order</h2><div class="pgrid row1">' + PLAN_CARDS_TOP + f'</div><p class="more"><a href="{BASE}/plans/">All {len(PLANS)} fix plans →</a></p><h2 class="row">Most recommended</h2>') if PLAN_CARDS else ''}
<div class="grid" id="feed">{''.join(card(v, hq=True) for v in top[:24])}</div>
<p class="more"><a href="{BASE}/browse/">Browse all {len(WATCH):,} lessons →</a></p>"""
    page("/", f"{SITE['name']}: {SITE['tagline']}", SITE["description"], body, nav="home",
         ld={"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": URL + "/",
             "potentialAction": {"@type": "SearchAction", "target": URL + "/search/?q={q}", "query-input": "required name=q"}})


def fixes_list(p):
    r = REDDIT.get(p["key"]) or {}
    vmap = {v["vid"]: v for v in VIDEOS}
    ins = [i for i in r.get("insights", []) if i.get("vid") in vmap][:3]
    if not ins:
        return ""
    return ('<details class="fixes"><summary>What golfers say fixed it</summary><ol>'
            + "".join(f'<li>{e(i["text"])} <a href="{BASE}/watch/{i["vid"]}/">Watch</a></li>' for i in ins) + "</ol></details>")


def sounds_like(p):
    r = REDDIT.get(p["key"]) or {}
    sl = [BAD.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), t) for t in r.get("sounds_like", [])][:4]
    if not sl:
        return ""
    return ('<section class="slbox"><h2>Sounds like you?</h2><p class="dim">How golfers described it when they asked for help:</p><ul class="sl">'
            + "".join(f"<li>“{e(t)}”</li>" for t in sl) + "</ul></section>")


def reddit_block(p):
    r = REDDIT.get(p["key"]) or {}
    vmap = {v["vid"]: v for v in VIDEOS}
    sl = [BAD.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), t) for t in r.get("sounds_like", [])][:4]
    ins = [i for i in r.get("insights", []) if i.get("vid") in vmap][:3]
    if not sl and not ins:
        return ""
    left = ('<div class="rb"><h2>Sounds like you?</h2><p class="dim">How golfers described it when they asked for help:</p><ul class="sl">'
            + "".join(f"<li>“{e(t)}”</li>" for t in sl) + "</ul></div>") if sl else ""
    right = ('<div class="rb"><h2>What golfers say fixed it</h2><ol class="ins">'
             + "".join(f'<li>{e(i["text"])} <a href="{BASE}/watch/{i["vid"]}/">Watch</a></li>' for i in ins) + "</ol></div>") if ins else ""
    return f'<section class="rblock">{left}{right}</section>'


def ask_cta(p):
    t = urllib.parse.quote(f"Help with my {p['name'].lower()}")
    return (f'<section class="ask"><h2>None of these fixed it?</h2><p>Post a swing video on r/GolfSwing. Golfers there answer fast. '
            f'Film down-the-line and face-on, and say what the ball does.</p>'
            f'<a class="pill inl" href="https://www.reddit.com/r/GolfSwing/submit?title={t}" target="_blank" rel="noopener nofollow">{svg("ext")}<span>Ask r/GolfSwing</span></a></section>')


def plan_cta(p):
    pl = next((x for x in PLANS if x.get("key") == p["key"] and x.get("slug")), None)
    if not pl:
        return ""
    mins = pl.get("mins")
    return (f'<a class="plancta" href="{BASE}/plan/{pl["slug"]}/"><b>Fix it step by step: {len(pl["items"])} videos'
            f'{f" ({mins} min)" if mins else ""}</b><span>Watch them in order, cause first, drill last →</span></a>')


def more_lessons(p, rows):
    """Every other lesson whose main topic is this problem, as plain links (keeps all watch pages reachable for crawlers)."""
    shown = {r[3]["vid"] for r in rows}
    rest = sorted([v for v in WATCH.values() if v.get("top") == p["key"] and v["vid"] not in shown], key=lambda v: -v["recs"])
    if not rest:
        return ""
    li = "".join(f'<li><a href="{BASE}/watch/{v["vid"]}/">{e(trunc(nice(v["title"]), 80))}</a> <span>{e(v.get("channel") or "")} · {v["recs"]}</span></li>' for v in rest)
    return f'<details class="morel"><summary>More lessons for {e(p["name"].lower())} ({len(rest)})</summary><ul>{li}</ul></details>'


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
<p class="meta"><b>{p['total_recs']:,}</b> golfers pointed to these <b>{p['video_count']}</b> lessons{f' · <b>{ok_total}</b> say they fixed it' if ok_total else ''}. Ranked by recommendations. <a href="{BASE}/about/">How we rank</a></p>{plan_cta(p)}{fixes_list(p)}{aid_html}</section>
<div class="grid ranked{' long' if len(rows) > 10 else ''}" id="ranked">{''.join(card(v, n, ok, i + 1, p['name'], top_quote(v) if i == 0 else "") for i, (s, n, ok, v) in enumerate(rows))}</div>
{f'<p class="more"><button class="pill inl" id="showall" aria-controls="ranked">Show all {len(rows)} lessons</button></p>' if len(rows) > 10 else ''}
{more_lessons(p, rows)}
{sounds_like(p)}
{ask_cta(p)}
{f'<article class="prose seo">{SEO["problems"][p["key"]]}<p class="dim">Written with AI from the lessons and recommendations above. Not a substitute for a coach.</p></article>' if SEO.get("problems", {}).get(p["key"]) else ''}"""
    page(f"/fix/{p['slug']}/", f"{p['q']} {p['video_count']} lessons golfers recommend | {SITE['name']}",
         f"{p['intro']} Ranked by {p['total_recs']:,} independent recommendations from golfers.", body, nav="cat",
         og=f"{URL}/static/og3/{p['slug']}.png",
         ld={"@context": "https://schema.org", "@type": "ItemList", "name": p["q"], "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": f"{URL}/watch/{r[3]['vid']}/", "name": r[3]["title"]} for i, r in enumerate(rows[:10])]})


def other_lessons():
    """Lessons with no clear main problem, so they are still linked from somewhere."""
    rest = sorted([v for v in WATCH.values() if not by_problem.get(v.get("top") or "")], key=lambda v: -v["recs"])
    if not rest:
        return ""
    li = "".join(f'<li><a href="{BASE}/watch/{v["vid"]}/">{e(trunc(nice(v["title"]), 80))}</a> <span>{e(v.get("channel") or "")} · {v["recs"]}</span></li>' for v in rest)
    return f'<details class="morel"><summary>Other recommended lessons ({len(rest)})</summary><ul>{li}</ul></details>'


def build_categories():
    boxes = ""
    for g in GROUPS:
        ps = sorted([p for p in PROBLEMS if p["group"] == g and p["video_count"]], key=lambda p: -p["total_recs"])
        if not ps:
            continue
        boxes += f'<div class="box"><h2>{e(g)}<span>{sum(p["video_count"] for p in ps):,} lessons</span></h2>' + "".join(
            f'<a href="{BASE}/fix/{p["slug"]}/">{e(p["name"])}<span>{p["video_count"]} lessons</span></a>' for p in ps) + "</div>"
    page("/categories/", f"Golf problems | {SITE['name']}", "Every golf problem with the lessons golfers recommend for it.",
         f'<h1 class="ptitle">Problems</h1><div class="boxes">{boxes}</div>{other_lessons()}', nav="cat")


def build_watch(v):
    tc = sorted((v.get("topic_counts") or {}).items(), key=lambda x: -x[1])
    tag_items = [(f'<a class="tag" href="{BASE}/fix/{PNAME[t]["slug"]}/">' if by_problem.get(t) else '<span class="tag">') + f'{n} mention {e(PNAME[t]["name"].lower())}' + ('</a>' if by_problem.get(t) else '</span>') for t, n in tc if t in PNAME]
    tags = "".join(tag_items[:4]) + (f'<details class="tmore"><summary>+{len(tag_items) - 4} more</summary>{"".join(tag_items[4:])}</details>' if len(tag_items) > 4 else "")
    notes = []
    for t, _ in tc:
        for x in (v.get("t_notes") or {}).get(t, []):
            x = x.strip().rstrip(".")
            if len(x) >= 8 and not re.search(r"[\"'“”‘’]", x) and x.lower() not in {y.lower() for y in notes}:
                notes.append(x[0].upper() + x[1:])
    notes = notes[:6]
    rel_src = by_problem.get(v["top"], []) if v["top"] else []
    rel = [r[3] for r in rel_src if r[3]["vid"] != v["vid"]][:12]
    vmap_all = {x["vid"]: x for x in VIDEOS}
    for pl in PLANS:
        ids = [i["vid"] for i in pl["items"]]
        if v["vid"] in ids:
            nxt = [vmap_all[i] for i in ids[ids.index(v["vid"]) + 1:] if i in vmap_all and vmap_all[i].get("page")]
            rel = nxt + [x for x in rel if x["vid"] not in {n["vid"] for n in nxt}]
            rel = rel[:12]
            break
    if len(rel) < 12:
        rel += [x for x in sorted(channels[v["cs"]]["videos"], key=lambda x: -x["recs"]) if x["vid"] != v["vid"] and x["page"] and x not in rel][: 12 - len(rel)]
    upnext = "".join(f'<a class="un" href="{BASE}/watch/{x["vid"]}/"><span class="th"><img loading="lazy" src="{thumb(x["vid"])}" alt=""></span>'
                     f'<span><b>{e(nice(x["title"]))}</b><i>{e(x["channel"])}</i><i>{x["recs"]} golfers recommend</i></span></a>' for x in rel)
    yrs = v.get("years") or []
    won = 'class="rctx win"' in rank_ctx(v)  # the winning lesson shows its seal in the rank line, not twice
    ch = f'<a href="{BASE}/coach/{v["cs"]}/">{e(v["channel"])}</a>{"" if won else coach_mark(v["cs"])}' if v["cs"] in COACH_SET else e(v["channel"])
    body = f"""<div class="watch"><div class="wl">
{''.join(plan_bar(pl, v) for pl in PLANS if pl.get("slug") and v["vid"] in [i["vid"] for i in pl["items"]])}
<button class="player" data-vid="{e(v['vid'])}" aria-label="Play"><img src="{thumb(v['vid'], 'hq2')}" alt=""><span class="pb"></span></button>
<h1 class="vt">{e(nice(v['title']))}</h1>
<p class="vch">{ch}</p>
{f'<p class="vaw">{rank_ctx(v).removesuffix(" · ")}</p>' if rank_ctx(v) else ''}<p class="vst"><span><b>{v['recs']}</b> golfers recommend</span>{f'<span class="ok">{CK}{v["success"]} fixed it</span>' if v.get('success') else ''}{f'<span class="nw">last recommended {lastrec(v["vid"])}</span>' if lastrec(v["vid"]) else ''}</p>
{top_quote(v)}
<div class="acts" data-vid="{e(v['vid'])}" data-t="{e(v['title'])}" data-c="{e(v['channel'])}">
<button class="pill" data-act="liked">{svg('like')}<span>Like</span></button>
<button class="pill" data-act="later">{svg('later')}<span>Watch later</span></button>
<a class="pill" href="https://www.youtube.com/watch?v={e(v['vid'])}" target="_blank" rel="noopener nofollow">{svg('ext')}<span>YouTube</span></a></div>
<div class="desc">{f'<p class="dim">{TYPES.get(v["type"], "")}{" · " + LEVELS[v["level"]] if v.get("level") in LEVELS else ""}</p>' if v.get("type") else ''}
{f'<p>{e(v["summary"])}</p>' if v.get("summary") and not (CARDS.get(v["vid"]) or {}).get("takeaways") else ''}
{''.join(plan_box(pl, v) for pl in PLANS if pl.get("slug") and v["vid"] in [i["vid"] for i in pl["items"]])}
{card_desc(v, notes)}
<p class="dim">AI summary of what golfers said.</p>
<div class="tags">{tags}</div></div>
<section class="vote" data-vid="{e(v['vid'])}" data-t="{e(trunc(v['title'], 60))}"><h2>Did this video fix it for you?</h2>
<p class="vbtns"><button class="pill inl" data-vote="yes">{svg('like')}<span>Yes, it helped</span></button><button class="pill inl" data-vote="no">{svg('dislike')}<span>Not for me</span></button></p>
<p class="vthanks dim" hidden>Thanks! Your vote helps other golfers. <a href="mailto:max@fassia.io?subject=GolfVotes%20feedback%3A%20{urllib.parse.quote(v['vid'])}">Tell us more</a></p></section>
{comments_html(v)}</div><aside class="wr"><h2>Up next</h2>{upnext}</aside></div>"""
    base = v["title"] if TITLE_COUNT[v["title"].lower()] == 1 else f"{v['title']} – {v['channel']}"
    rec = f"Recommended by {v['recs']} golfers" + (f" for {PNAME[v['top']]['name'].lower()}" if v["top"] in PNAME else "") + (f", {v['success']} said it fixed it" if v.get("success") else "") + "."
    tt = trunc(base, 53)
    USED[tt] += 1
    if USED[tt] > 1:
        tt = f"{tt} ({USED[tt]})"
    page(f"/watch/{v['vid']}/", f"{tt} | {SITE['name']}",
         (f"{v['summary']} {rec}" if v.get("summary") and len(v["summary"]) + len(rec) < 158 else (v.get("summary") or f"{v['channel']} lesson. {rec}")) if v.get("summary") else f"{v['channel']} lesson. {rec}",
         body, cls="wpage", og=thumb(v["vid"], "hqdefault"),
         ld={"@context": "https://schema.org", "@type": "VideoObject", "name": v["title"], "thumbnailUrl": thumb(v["vid"], "hqdefault"),
             "uploadDate": (v.get("published") or f"{(v.get('years') or [2020])[0]}-01-01") + "T00:00:00+00:00",
             "description": f"{v['recs']} golfers recommended this lesson.", "embedUrl": f"https://www.youtube-nocookie.com/embed/{v['vid']}",
             **({"duration": f"PT{v['duration_s'] // 60}M{v['duration_s'] % 60}S"} if v.get("duration_s") else {})})


def card_desc(v, notes):
    c = CARDS.get(v["vid"]) or {}
    out = ""
    if c.get("why"):
        out += f'<p><b>Why golfers recommend it:</b> {e(c["why"])}</p>'
    if c.get("takeaways"):
        out += '<p class="tkh"><b>What golfers took away</b></p><ul class="tk">' + "".join(f"<li>{e(t)}</li>" for t in c["takeaways"]) + "</ul>"
    elif not c and notes:
        out += '<p><b>Why golfers recommend it</b></p><ul>' + "".join(f"<li>{e(x)}</li>" for x in notes) + "</ul>"
    return out


BAD = re.compile(r"\b(f+u+c+k+\w*|shit\w*|bullshit|cunt\w*|bitch\w*|asshole\w*|dick\w*|wtf)\b", re.I)


def clean_title(t):
    t = BAD.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), t or "")
    return trunc(t, 70)


STANCE = {"useful": ("Useful", 0), "critical": ("Critical", 1), "cites": ("Cites it", 2), "praise": ("Praise", 3), "joke": ("Joke", 4)}


def comments_html(v):
    cs = COMMENTS.get(v["vid"]) or []
    if not cs:
        return ""
    card = (CARDS.get(v["vid"]) or {}).get("comments", {})
    for c in cs:
        cid = c["u"].rstrip("/").rsplit("/", 1)[-1]
        st = (card.get(cid) or {}).get("stance")
        c["st"], c["q"] = st, (card.get(cid) or {}).get("quote", "")
    if card:
        cs = sorted(cs, key=lambda c: (STANCE.get(c["st"], ("", 5))[1], 0 if c["l"] == "Says it fixed it" else 1))
    def one(c):
        body = e(c["b"]).replace("▶ this video", '<span class="vl">[this video]</span>')
        if c.get("q") and len(c["q"]) > 12 and e(c["q"]) in body:
            body = body.replace(e(c["q"]), f'<mark>{e(c["q"])}</mark>', 1)
        st = STANCE.get(c.get("st"), (None, 0))[0]
        tag = f'<span class="lab st-{c["st"]}">{st}</span>' if st and c.get("st") in ("critical",) else ""
        return (f"""<div class="cm{' cm-praise' if c.get('st') in ('praise', 'joke') else ''}"><p class="cmh"><b>r/{e(c['sub'])}</b> · {c['y']}{f' · <span class="up">▲ {c["s"]}</span>' if c.get("s", 0) >= 5 else ''}{f' · in “{e(clean_title(c["pt"]))}”' if c.get('pt') else ''}</p>
<p>{body}</p><p class="cmf">{tag}<span class="lab{' fix' if c['l'] == 'Says it fixed it' else ''}">{e(c['l'])}</span> <a href="{e(c['u'])}" target="_blank" rel="noopener nofollow">View on Reddit</a></p></div>""")
    main = [c for c in cs if c.get("st") not in ("praise", "joke")]
    rest = [c for c in cs if c.get("st") in ("praise", "joke")]
    nu = sum(1 for c in cs if c.get("st") == "useful"); ncrit = sum(1 for c in cs if c.get("st") == "critical")
    nfix = sum(1 for c in cs if c["l"] == "Says it fixed it")
    summary = f'<p class="dim">{nfix} say it fixed it{f" · {ncrit} say it didn&#39;t help" if ncrit else ""}</p>' if card else ""
    rows = "".join(one(c) for c in main) + (f'<details class="morecm"><summary>{len(rest)} more comments with just praise</summary>{"".join(one(c) for c in rest)}</details>' if rest else "")
    more = v["recs"] - len(cs)
    return f'<section class="cms"><h2>{len(cs)} comments from Reddit</h2>{summary}{rows}{f"<p class=dim>…and {more} more golfers who recommended it.</p>" if more > 0 else ""}<p class="dim small">Excerpts of public comments, without usernames, linked to the original. Want yours removed? See <a href="{BASE}/about/#removal">About</a>.</p></section>'


def _old_comments_html(v):
    cs = COMMENTS.get(v["vid"]) or []
    if not cs:
        return ""
    rows = "".join(f"""<div class="cm"><p class="cmh"><b>r/{e(c['sub'])}</b> · {c['y']}{f' · in “{e(c["pt"])}”' if c.get('pt') else ''}</p>
<p>{e(c['b'])}</p><p class="cmf"><span class="lab{' fix' if c['l'] == 'Says it fixed it' else ''}">{e(c['l'])}</span> <a href="{e(c['u'])}" target="_blank" rel="noopener nofollow">View on Reddit</a></p></div>""" for c in cs)
    more = v["recs"] - len(cs)
    return f'<section class="cms"><h2>{len(cs)} comments from Reddit</h2>{rows}{f"<p class=dim>…and {more} more golfers who recommended it.</p>" if more > 0 else ""}<p class="dim small">Excerpts of public comments, without usernames, linked to the original. Want yours removed? See <a href="{BASE}/about/#removal">About</a>.</p></section>'


def rank_ctx(v):
    k = v.get("top")
    if k not in PNAME:
        return ""
    ids = [r[3]["vid"] for r in by_problem.get(k, [])]
    if v["vid"] not in ids:
        return ""
    i = ids.index(v["vid"])
    aw = next((x for x in AWARDS.get(v["cs"], []) if x["k"] == k), None) if i == 0 else None
    if aw:
        return (f'<a class="rctx win" href="{BASE}/fix/{PNAME[k]["slug"]}/"><span class="lau" aria-hidden="true">{mini_seal("1", 22)}</span>'
                f'Most recommended for {e(PNAME[k]["name"])} · {aw["y"]}</a> · ')
    return f'<a class="rctx" href="{BASE}/fix/{PNAME[k]["slug"]}/">#{i + 1} for {e(PNAME[k]["name"])}</a> · '


def top_quote(v):
    card = (CARDS.get(v["vid"]) or {}).get("comments", {})
    best = None
    for c in COMMENTS.get(v["vid"]) or []:
        cid = c["u"].rstrip("/").rsplit("/", 1)[-1]
        cc = card.get(cid) or {}
        if cc.get("stance") == "useful" and len(cc.get("quote", "")) > 20:
            score = (2 if c["l"] == "Says it fixed it" else 1) + min(c.get("s", 0), 50) / 25
            if not best or score > best[0]:
                best = (score, cc["quote"], c)
    if not best:
        return ""
    return f'<blockquote class="tq">“{e(best[1])}”<cite>r/{e(best[2]["sub"])}{f" · ▲ {best[2]['s']}" if best[2].get("s", 0) >= 5 else ""}</cite></blockquote>'


def plan_bar(pl, v):
    ids = [i["vid"] for i in pl["items"]]
    k = ids.index(v["vid"])
    vm = {x["vid"]: x for x in VIDEOS}
    nxt = ids[k + 1] if k + 1 < len(ids) else None
    nx = f'<a href="{BASE}/watch/{nxt}/?plan={pl["slug"]}">Next: {e(trunc(nice(vm[nxt]["title"]), 40))} →</a>' if nxt and nxt in vm else f'<a href="{BASE}/plan/{pl["slug"]}/">Back to plan →</a>'
    return (f'<div class="pbar" data-plan="{pl["slug"]}" hidden><a href="{BASE}/plan/{pl["slug"]}/"><b>{e(pl["title"])}</b></a> · Step {k + 1} of {len(ids)}'
            f'<span class="prog"><span style="width:{100 * (k + 1) / len(ids):.0f}%"></span></span>{nx}</div>')


def plan_box(pl, v):
    ids = [i["vid"] for i in pl["items"]]
    k = ids.index(v["vid"])
    nxt = ids[k + 1] if k + 1 < len(ids) else None
    note = pl["items"][k].get("note", "")
    return (f'<div class="inplan" data-plan="{pl["slug"]}"><p>Step {k + 1} of {len(ids)} in <a href="{BASE}/plan/{pl["slug"]}/">{e(pl["title"])}</a></p>'
            f'{f"<p class=dim>{e(note)}</p>" if note else ""}<p><button class="pill inl done" data-plan="{pl["slug"]}" data-vid="{v["vid"]}">{svg("check")}<span>Mark as done</span></button> '
            + (f'<a class="pill inl" href="{BASE}/watch/{nxt}/?plan={pl["slug"]}">Next step →</a>' if nxt else f'<a class="pill inl" href="{BASE}/plan/{pl["slug"]}/">Back to plan</a>') + '</p></div>')


def build_plans():
    vmap = {v["vid"]: v for v in VIDEOS}
    cards = ""
    for pl in PLANS:
        items = [i for i in pl["items"] if i["vid"] in vmap]
        if not items:
            continue
        pl["slug"] = pl.get("slug") or PNAME[pl["key"]]["slug"]
        first = vmap[items[0]["vid"]]
        mins = round(sum(vmap[i["vid"]].get("duration_s") or 0 for i in items) / 60)
        pl["mins"] = mins
        cards += f'<a class="plc" href="{BASE}/plan/{pl["slug"]}/" data-plan="{pl["slug"]}" data-n="{len(items)}"><span class="th"><img loading="lazy" src="{thumb(first["vid"])}" alt=""><span class="du">{f'<span class="dn">{len(items)} videos · </span>{mins} min' if mins else f"{len(items)} videos"}</span></span><b>{e(pl["title"])}</b><i><span>{sum((vmap[i["vid"]].get("topic_counts") or {}).get(pl["key"], 0) for i in items)} golfers recommend these</span>{('<span class="ok">' + CK + str(sum((vmap[i["vid"]].get("t_success") or {}).get(pl["key"], 0) for i in items)) + ' fixed it</span>') if sum((vmap[i["vid"]].get("t_success") or {}).get(pl["key"], 0) for i in items) else ""}<span class="pprog"></span></i></a>'
        steps = "".join(f"""<li class="pli" data-vid="{i['vid']}"><a class="th" href="{BASE}/watch/{i['vid']}/?plan={pl['slug']}"><img loading="lazy" src="{thumb(i['vid'])}" alt="">{f'<span class="du">{fmt_dur(vmap[i["vid"]].get("duration_s"))}</span>' if vmap[i['vid']].get('duration_s') else ''}</a>
<div><p class="steplab">Step {n}{(' · ' + TYPES[vmap[i['vid']]['type']]) if vmap[i['vid']].get('type') in TYPES and vmap[i['vid']]['type'] != 'other' else ''}</p><h3><a href="{BASE}/watch/{i['vid']}/?plan={pl['slug']}">{e(nice(vmap[i['vid']]['title']))}</a></h3><p class="ch">{e(vmap[i['vid']]['channel'])} · {(vmap[i['vid']].get('topic_counts') or {}).get(pl['key'], 0)} golfers recommend</p><p>{e(i['note'])}</p><button class="pill inl done" data-plan="{pl['slug']}" data-vid="{i['vid']}">{svg('check')}<span>Mark as done</span></button></div></li>""" for n, i in enumerate(items, 1))
        ids = ",".join(i["vid"] for i in items)
        body = f"""<div class="plan"><p class="kick">Fix plan · <a href="{BASE}/fix/{PNAME[pl['key']]['slug']}/">{e(PNAME[pl['key']]['name'])}</a></p><h1 class="ptitle">{e(pl['title'])}</h1>
<p class="lead">{e(pl['intro'])}</p>
<div class="planbar" data-plan="{pl['slug']}" data-n="{len(items)}"><b>{len(items)} videos{f" · {mins} min total" if mins else ""}</b><span class="prog"><span></span></span><span class="progt">0 of {len(items)} done</span></div>
<p><a class="pill inl start" id="startplan" href="{BASE}/watch/{items[0]['vid']}/?plan={pl['slug']}">{svg('play')}<span>Start step 1</span></a> <a class="pill inl" href="https://www.youtube.com/watch_videos?video_ids={ids}" target="_blank" rel="noopener nofollow">{svg('ext')}<span>Play all on YouTube</span></a></p>
<ol class="pll">{steps}</ol>{f'<div class="nlbox"><b>Working on your {e(PNAME[pl["key"]]["name"].lower())}?</b> Get the newest top-voted fixes once a month. <a class="pill inl" href="{e(SITE["newsletter_url"])}">Subscribe</a></div>' if SITE.get("newsletter_url") else ''}</div>"""
        page(f"/plan/{pl['slug']}/", f"{pl['title']} | {SITE['name']}", pl["intro"][:155], body, nav="plans", og=f"{URL}/static/og3/plan-{PNAME[pl['key']]['slug']}.png")
    page("/plans/", f"Fix plans | {SITE['name']}", "Short learning paths built from the golf lessons golfers recommend most.",
         f'<h1 class="ptitle">Fix plans</h1><p class="lead">Short playlists, 4–6 videos in order, built from the lessons golfers link most.</p><div class="plist">{cards}</div>', nav="plans")
    return cards


def build_client_pages():
    opt = lambda d: "".join(f'<option value="{k}">{e(x)}</option>' for k, x in d)
    probs = opt(sorted(((p["slug"], p["name"]) for p in PROBLEMS if p["video_count"]), key=lambda x: x[1]))
    filters = f"""<form class="filters" id="filters">
<label>Sort <select name="sort"><option value="recs">Most recommended</option><option value="fixed">Most “fixed it”</option><option value="recent">Recently recommended</option><option value="oldest">Oldest first</option>{'<option value="views">View count</option><option value="hidden">Hidden gems</option>' if any(v.get("views") for v in VIDEOS) else ''}</select></label>
<label>Problem <select name="p"><option value="">Any</option>{probs}</select></label>
<label>Type <select name="type"><option value="">Any</option>{opt((k, x) for k, x in TYPES.items() if k != "other")}</select></label>
<label>Level <select name="level"><option value="">Any</option>{opt(LEVELS.items())}</select></label>
<label class="cb"><input type="checkbox" name="new" value="1"> Recommended in the past year</label></form>"""
    page("/browse/", f"Browse all lessons | {SITE['name']}", "Browse and filter every golf lesson golfers recommended.",
         f'<h1 class="ptitle" id="ltitle">Browse all lessons</h1>{filters}<p class="dim" id="count"></p><div class="grid" id="list" data-list="browse"></div><p class="dim" id="empty"></p>', nav="browse")
    page("/settings/", f"Settings | {SITE['name']}", "Settings.", f"""<div class="prose"><h1 class="ptitle">Settings</h1>

<label class="set"><input type="checkbox" id="s-hidedis"> Hide disliked videos everywhere</label>
<label class="set"><input type="checkbox" id="s-keys"> Single-key keyboard shortcuts (h, k, l, w)</label>
<p><button class="pill inl" id="s-clear-h">Clear watch history</button> <button class="pill inl" id="s-clear-all">Reset everything</button></p>
<p class="dim">Everything is stored only in this browser. Keyboard shortcuts: press <kbd>?</kbd>.</p></div>""", nav="settings", canonical=False)
    st = SITE["stats"]
    prompt = (f"Use the open dataset at {URL}/static/data/golfvotes-lessons.json. Each entry is a golf lesson on YouTube with how many golfers "
              f"independently recommended it, how many said it fixed their problem, its problems, type and level. My problem is: <describe your swing problem>. "
              f"Pick the 3 best lessons for me, in the order I should watch them, and explain why.")
    page("/data/", f"The data | {SITE['name']}", "Download the GolfVotes dataset of golf lessons ranked by golfers.", f"""<div class="prose"><h1 class="ptitle">The data</h1>
<p class="lead">Everything behind {e(SITE['name'])} is open. Use it, cite it, build on it. Please link back.</p>
<div class="kpis"><div><b>{len(WATCH):,}</b>lessons</div><div><b>{TOTAL_RECS:,}</b>recommendations</div><div><b>{st['comments_scanned']}</b>comments read</div><div><b>{VDATA['generated']}</b>last update</div></div>
<h2>Files</h2><table class="files"><tr><td><a href="{BASE}/static/data/golfvotes-lessons.json" download>golfvotes-lessons.json</a></td><td>All ranked lessons: video id, title, coach, recommendations, “fixed it” count, problems, type, level, summary</td></tr>
<tr><td><a href="{BASE}/static/data/golfvotes-problems.json" download>golfvotes-problems.json</a></td><td>Problems with their top lessons in order</td></tr></table>
<h2>Give it to your agent</h2><p>Paste this into ChatGPT, Claude or any assistant:</p><pre id="prompt">{e(prompt)}</pre><p><button class="pill inl" id="copyprompt">Copy this prompt</button></p>
<h2>License</h2><p>Our compilation (counts, rankings, labels, summaries) is free to use with attribution to {e(SITE['name'])} ({e(URL)}). It does not cover third-party content: video titles, thumbnails and videos belong to their creators and YouTube, and Reddit comments to their authors. Provided as is, without warranty.</p></div>""", nav="data")
    os.makedirs(os.path.join(OUT, "static", "data"), exist_ok=True)
    lessons = [{"id": v["vid"], "url": f"https://www.youtube.com/watch?v={v['vid']}", "title": v["title"], "coach": v["channel"], "recommendations": v["recs"],
                "fixed_it": v.get("success", 0), "problems": {PNAME[t]["name"]: n for t, n in (v.get("topic_counts") or {}).items() if t in PNAME},
                "type": TYPES.get(v.get("type")), "level": LEVELS.get(v.get("level")), "summary": v.get("summary"), "page": f"{URL}/watch/{v['vid']}/"}
               for v in sorted(WATCH.values(), key=lambda x: -x["recs"])]
    json.dump({"source": URL, "generated": VDATA["generated"], "lessons": lessons}, open(os.path.join(OUT, "static", "data", "golfvotes-lessons.json"), "w"), ensure_ascii=False, indent=0)
    json.dump({"source": URL, "problems": [{"problem": p["name"], "question": p["q"], "page": f"{URL}/fix/{p['slug']}/", "top": [r[3]["vid"] for r in by_problem[p["key"]][:10]]}
                                           for p in PROBLEMS if p["video_count"]]}, open(os.path.join(OUT, "static", "data", "golfvotes-problems.json"), "w"), ensure_ascii=False, indent=0)


def build_guides():
    for key, slug in (("guide_coaches", "best-golf-youtube-channels"), ("guide_drills", "best-golf-drills")):
        g = SEO.get(key)
        if not g:
            continue
        page(f"/guides/{slug}/", f"{g['title']} | {SITE['name']}", g["description"],
             f'<article class="prose"><p class="kick">Guide · data from {VDATA["generated"]}</p><h1 class="ptitle">{e(g["title"])}</h1>{g["html"]}'
             f'<p><a href="{BASE}/coaches/">All coaches</a> · <a href="{BASE}/browse/?type=drill">All drills</a> · <a href="{BASE}/about/">How we count</a></p></article>', nav="stats",
             ld={"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "dateModified": VDATA["generated"], "author": {"@type": "Organization", "name": SITE["name"]}})


def award_line(s):
    """Quiet gold text for list pages ('4 × #1 · Top 10'); the seal itself stays reserved for single pages."""
    a = [x for x in AWARDS.get(s, []) if x["k"] != "live"]
    if not a:
        return ""
    n1 = sum(1 for x in a if x["k"] != "top10")
    parts = ([f"{n1} × #1" if n1 > 1 else "#1"] if n1 else []) + (["Top 10"] if any(x["k"] == "top10" for x in a) else [])
    t = "GolfVotes awards: " + "; ".join(award_text(x) for x in a)
    return f'<span class="awt" title="{e(t)}"><span class="sr">{e(t)}</span><span aria-hidden="true">{" · ".join(parts)}</span></span>'


def build_coaches():
    rows = "".join(f'<a class="crow" href="{BASE}/coach/{s}/"><span class="n">{i}</span><b>{e(c["name"])}{award_line(s)}</b>'
                   f'<span><b>{c["recs"]:,}</b> recommendations · {len(c["videos"])} videos</span>'
                   f'<i>{e(", ".join(PNAME[t]["name"] for t, _ in c["topics"].most_common(3) if t in PNAME))}</i></a>' for i, (s, c) in enumerate(COACHES, 1))
    page("/coaches/", f"Most recommended golf coaches on YouTube | {SITE['name']}",
         "The YouTube golf instructors golfers recommend most, ranked by independent recommendations.",
         f'<h1 class="ptitle">Most recommended coaches</h1><p class="lead">Ranked by how often golfers recommended their lessons to other golfers.</p><div class="clist">{rows}</div>', nav="coaches")


AWARDS = {}  # coach slug -> list of award dicts (persisted in data/awards.json, never removed: a badge stays valid for its year)


def award_info(slug, k, y):
    """(file stem, short label, big, line, sub, proof link) for an award."""
    if k == "top10":
        return (f"{slug}--top10-{y}", f"Top 10 most recommended golf instruction {y}", "TOP 10", "GOLF INSTRUCTION",
                "MOST RECOMMENDED", f"{BASE}/coaches/")
    p = PNAME[k]
    return (f"{slug}--{p['slug']}-{y}", f"#1 most recommended lesson for {p['name']} {y}", "#1", p["name"].upper(),
            "MOST RECOMMENDED", f"{BASE}/fix/{p['slug']}/")


LIVE_MIN = 25  # live count badge for channels with at least this many recommendations


def make_badges():
    """Merge current wins into data/awards.json (awards are never removed: a badge stays valid for its year),
    draw award badges into static/badge/ (committed, PNGs made locally by build/badge-png.js) and
    live count badges straight into /badge/{slug}.svg (redrawn on every build)."""
    sys.path.insert(0, os.path.dirname(__file__)); import badge_art
    yr = VDATA["generated"][:4]
    fn = os.path.join(ROOT, "data", "awards.json")
    store = json.load(open(fn)) if os.path.exists(fn) else {}
    for i, (s, c) in enumerate(COACHES):
        have = {(x["k"], x["y"]) for x in store.get(s, [])}
        for k in [p["key"] for p in coach_wins.get(s, []) if p["key"] in PNAME] + (["top10"] if i < 10 else []):
            if (k, yr) not in have:
                store.setdefault(s, []).append({"k": k, "y": yr})
    for s, c in COACHES:
        if c["recs"] >= LIVE_MIN and not any(x["k"] == "live" for x in store.get(s, [])):
            store.setdefault(s, []).append({"k": "live", "y": yr})
    json.dump(store, open(fn, "w"), indent=1, sort_keys=True)
    json.dump(SLUGS, open(SLUGS_FN, "w"), indent=0, sort_keys=True, ensure_ascii=False)
    bdir = os.path.join(ROOT, "static", "badge"); os.makedirs(bdir, exist_ok=True)
    for s, lst in store.items():
        if s not in COACH_SET:
            continue
        for x in lst:
            if x["k"] == "live":
                continue
            stem, label, big, line, sub, proof = award_info(s, x["k"], x["y"])
            for th, suf in (("light", ""), ("dark", "-dark")):
                svg, w, h = badge_art.badge(big, line, x["y"], th, e(label), sub)
                f = os.path.join(bdir, stem + suf + ".svg")
                if not os.path.exists(f) or open(f).read() != svg:
                    open(f, "w").write(svg)
            AWARDS.setdefault(s, []).append(dict(x, stem=stem, label=label, proof=proof, w=w, h=h))
        AWARDS.get(s, []).sort(key=lambda x: (-int(x["y"]), x["k"] == "top10"))
    shutil.copytree(bdir, os.path.join(OUT, "badge"), dirs_exist_ok=True)
    for s, c in channels.items():  # live badge: once issued, it keeps being drawn (an embedded badge must never break)
        if any(x["k"] == "live" for x in store.get(s, [])):
            for th, suf in (("light", ""), ("dark", "-dark")):
                svg, w, h = badge_art.live_badge(c["recs"], th, f'{c["recs"]:,} golfer recommendations on GolfVotes')
                open(os.path.join(OUT, "badge", s + suf + ".svg"), "w").write(svg)
            c["live"] = (w, h)


def awards_strip(s):
    a = AWARDS.get(s)
    if not a:
        return ""
    items = "".join(f'<a class="aw" href="{x["proof"]}"><img class="lt" src="{BASE}/badge/{x["stem"]}.svg" alt="{e(x["label"])}" width="{round(x["w"] * 96 / x["h"])}" height="96" loading="lazy">'
                    f'<img class="dk" src="{BASE}/badge/{x["stem"]}-dark.svg" alt="{e(x["label"])}" width="{round(x["w"] * 96 / x["h"])}" height="96" loading="lazy">'
                    f'<span>{"See the ranking" if x["k"] != "top10" else "See all coaches"} →</span></a>' for x in a)
    return f'<section class="awards" aria-label="GolfVotes awards"><div class="awl awd">{items}</div></section>'


def yt_vids(c):
    return [v for v in sorted(c["videos"], key=lambda v: -v["recs"]) if v["recs"] >= 10][:8]


def copy_btn(text, label="Copy code"):
    return f'<button class="cbtn" type="button" data-copy="{e(text)}">{label}</button>'


def badge_card(s, title, stem, label, w, h, note=""):
    """One badge with light + dark variant, copy-code / PNG / SVG actions. Embeds always link to the coach profile."""
    col = ""
    dw = round(w * 120 / h)
    for th, suf in (("light", ""), ("dark", "-dark")):
        f = stem + suf
        code = (f'<a href="{URL}/coach/{s}/?ref=badge" target="_blank" rel="noopener"><img src="{URL}/badge/{f}.svg" alt="{e(label)}" '
                f'width="{dw}" height="120" style="max-width:100%;height:auto;border:0"></a>')
        png = f'<a href="{BASE}/badge/{f}.png" download>PNG</a>' if os.path.exists(os.path.join(ROOT, "static", "badge", f + ".png")) else ""
        col += (f'<div class="bv {th}"><img src="{BASE}/badge/{f}.svg" alt="" width="{dw}" height="120" loading="lazy">'
                f'<div class="bact">{copy_btn(code)}{png}<a href="{BASE}/badge/{f}.svg" download>SVG</a></div>'
                f'<span class="bvl">{"For light backgrounds" if th == "light" else "For dark backgrounds"}</span></div>')
    return f'<article class="bcard"><h3>{e(title)}</h3>{f"<p class=bnote2>{note}</p>" if note else ""}<div class="bvs">{col}</div></article>'


def badge_kit(s, c):
    """Collapsed 'Are you X?' section on the coach page with everything a coach needs."""
    cards = "".join(badge_card(s, f'Top 10 golf instruction · {x["y"]}' if x["k"] == "top10" else f'#1 for {PNAME[x["k"]]["name"]} · {x["y"]}',
                               x["stem"], x["label"] + " on GolfVotes", x["w"], x["h"]) for x in AWARDS.get(s, []))
    if c.get("live"):
        cards += badge_card(s, "Live badge", s, f'{c["recs"]:,} golfer recommendations on GolfVotes', *c["live"],
                            note="Shows your current number of golfer recommendations and updates by itself.")
    vids = yt_vids(c)
    def line(v):
        t = f'✓ Recommended by {v["recs"]} golfers on GolfVotes: {URL}/watch/{v["vid"]}/?ref=yt'
        return f'<li><span><b>{e(trunc(nice(v["title"]), 64))}</b><code>{e(t)}</code></span>{copy_btn(t, "Copy")}</li>'
    txt = "".join(line(v) for v in vids)
    if not cards and not txt:
        return ""
    return f"""<details class="bkit" id="badges"><summary>Are you {e(c['name'])}? Use your GolfVotes badges</summary>
<p class="dim">Free to use on your website, channel or socials. Every badge links back to this page. <a href="{BASE}/badges/">How badges work</a></p>
<ul class="bhow"><li><b>Website with HTML:</b> “Copy code” and paste it where the badge should go. It shows at 240 × 120 px and shrinks on small screens.</li>
<li><b>Wix, Squarespace, Linktree, socials:</b> download the PNG, add it as an image and link it to {copy_btn(f"{URL}/coach/{s}/?ref=badge", "Copy link")}</li></ul>{cards}
{f'<section class="btxt"><h3>For your YouTube descriptions</h3><p class="dim">Paste one line under the video it belongs to.</p><ul>{txt}</ul></section>' if txt else ''}</details>"""


def build_badges_page():
    ex = [x for s, _ in COACHES for x in AWARDS.get(s, [])]
    show = [x for x in ex if x["k"] != "top10"][:1] + [x for x in ex if x["k"] == "top10"][:1]
    hero = "".join(f'<img src="{BASE}/badge/{x["stem"]}.svg" alt="{e(x["label"])}" width="{round(x["w"] * 120 / x["h"])}" height="120">' for x in show)
    live = next(((s, c) for s, c in COACHES if c.get("live")), None)
    if live:
        hero += f'<img src="{BASE}/badge/{live[0]}.svg" alt="Live badge example" width="{round(live[1]["live"][0] * 100 / live[1]["live"][1])}" height="100">'
    body = f"""<div class="bpage"><section class="bhero"><div class="prose"><h1 class="ptitle">Badges for coaches</h1>
<p class="lead">When golfers recommend your lessons to each other, you earn a badge. Use it on your website, your channel or your socials.</p>
<h2>Where to find yours</h2><p>On your own coach page: open <a href="{BASE}/coaches/">Coaches</a>, find your channel and click <b>“Are you …? Use your GolfVotes badges”</b>. There you can copy the code or download the image.</p>
<h2>The badges</h2><ul>
<li><b>#1 for a problem:</b> at a GolfVotes update, your lesson had the most independent recommendations for that problem: at least {AWARD_MIN}, and more than any other lesson (no ties).</li>
<li><b>Top 10:</b> your channel was one of the 10 with the most recommendations across all problems.</li>
<li><b>Live badge:</b> your current number of golfer recommendations (from {LIVE_MIN}). It updates by itself.</li>
<li><b>Text line for YouTube:</b> for any lesson with at least 10 recommendations.</li></ul>
<h2>The rules</h2><ul><li>Badges are earned, never sold.</li><li>Award badges carry a year and stay valid for that year, even if the ranking changes later.</li>
<li>Every badge links to your GolfVotes profile, where viewers can check the rankings behind it.</li>
<li>Use them as they are: no edits to numbers, years or wording.</li>
<li>Use a badge only for the channel and lessons it names, never to suggest that GolfVotes endorses a product, course or service.</li>
<li>A badge is a statement about golfer recommendations, not a quality guarantee. If it is used misleadingly, or the underlying data turns out to be wrong, we may withdraw it.</li>
<li>Free to use under these terms. The badge links to your GolfVotes profile; please keep that link.</li></ul>
<p class="dim">Questions: <a href="mailto:max@fassia.io?subject=GolfVotes%20badges">max@fassia.io</a></p></div>
<div class="bshow">{hero}</div></section></div>"""
    page("/badges/", f"Badges for coaches | {SITE['name']}", "How golf coaches earn GolfVotes badges for the YouTube lessons golfers recommend most.", body)
    for s, c in COACHES:  # short-lived per-coach kit pages from an earlier version -> coach page
        d = os.path.join(OUT, "badges", s); os.makedirs(d, exist_ok=True)
        t = f"{URL}/coach/{s}/#badges"
        open(os.path.join(d, "index.html"), "w").write(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={e(t)}"><link rel="canonical" href="{e(t)}"><a href="{e(t)}">Continue</a>')


def build_coach(s, c):
    vids = sorted([v for v in c["videos"]], key=lambda v: -v["recs"])[:48]
    tops = " ".join(f'<a class="tag" href="{BASE}/fix/{PNAME[t]["slug"]}/">{e(PNAME[t]["name"])} · {n}</a>' for t, n in c["topics"].most_common(8) if t in PNAME and by_problem.get(t))
    body = f"""<section class="chead"><div class="av">{e((c['name'] or '?')[0])}</div><div>
<h1>{e(c['name'])}{coach_mark(s)}</h1><p class="dim cst"><span><b>{c['recs']:,}</b> recommendations</span><span><b>{len(c['videos'])}</b> videos</span>{f'<span class="ok">{CK}{c["success"]} said it fixed their problem</span>' if c['success'] else ''}</p>
<div class="tags">{tops}</div>{f'<p><a href="{e(c["url"])}" target="_blank" rel="noopener nofollow">YouTube channel ↗</a></p>' if c.get('url') else ''}</div></section>
{awards_strip(s)}{badge_kit(s, c)}<div class="grid">{''.join(card(v) for v in vids)}</div>"""
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
<p>Guides: <a href="{BASE}/guides/best-golf-youtube-channels/">Best golf instruction channels on YouTube</a> · <a href="{BASE}/guides/best-golf-drills/">Most recommended golf drills</a></p>
<p class="dim">Free to cite with a link to {e(SITE['name'])}. Method: <a href="{BASE}/about/">About</a>.</p></div>"""
    page("/report/", f"What golfers recommend to each other: the data | {SITE['name']}",
         f"Which golf problems golfers ask about most and which YouTube coaches they recommend, from {st['comments_scanned']} comments.", body, nav="stats", og=f"{URL}/static/og3/report.png")


def build_text():
    st = SITE["stats"]
    about = f"""<div class="prose"><h1 class="ptitle">{e(SITE['name'])}</h1><p class="lead">The YouTube golf lessons golfers keep telling each other to watch.</p>
<div class="kpis"><div><b>{len(WATCH):,}</b>lessons</div><div><b>{st['comments_scanned']}</b>comments read</div><div><b>{len([p for p in PROBLEMS if p['video_count']])}</b>problems</div><div><b>{st['period']}</b>years</div></div>
<h2>Why</h2><p>YouTube's recommendations are tuned for watch time, not for fixing your slice. Meanwhile golfers in online communities answer each other's swing questions every day with a link to the one lesson that finally helped them. Those answers are scattered across years of threads. {e(SITE['name'])} collects and counts them.</p>
<h2>How it was built</h2><ol>
<li><b>Read the threads.</b> {st['comments_scanned']} public comments from golf-instruction communities ({st['period']}) were scanned for YouTube links: {st['yt_comments']} comments.</li>
<li><b>Read each comment with an AI model.</b> Is it a real lesson recommendation, not a meme, highlight or gear review? Which problem is it about? Does the golfer say it fixed it?</li>
<li><b>Count independent golfers.</b> Each golfer counts once per video. A lesson needs at least {MIN} different golfers recommending it for a problem.</li>
<li><b>Add context.</b> An AI model labels each lesson's type (drill, explainer, live lesson, pro swing …), level and a one-line summary, and builds short fix plans from the top lessons.</li>
<li><b>Rank per problem</b> by those recommendations, with extra weight when golfers report it actually fixed their problem.</li></ol>
<h2>Promises</h2><p>Nobody can pay to rank higher. Sponsored content or affiliate links, if they ever appear, are labeled and kept out of the rankings. Video pages show short excerpts of public Reddit comments, without usernames, always linked to the original. Ask and we'll remove yours.</p>
<h2>Your data</h2><p>Liked, history and watch later are stored only in your browser.</p>
<h2>Creators</h2><p>Video pages show a small preview image of each lesson, stored on this site, always linking to the video on YouTube. If you are a creator and want a preview image or your channel removed, email <a href="mailto:max@fassia.io?subject=GolfVotes%20creator%20request">max@fassia.io</a>; it will be removed in the next update.</p>
<h2 id="removal">Comments</h2><p>Video pages show short excerpts of public Reddit comments, without usernames, always linked to the original. If you wrote one and want it removed, email <a href="mailto:max@fassia.io?subject=GolfVotes%20comment%20removal">max@fassia.io</a> or open an issue at <a href="https://github.com/citymax24/golf-fixes/issues">GitHub</a>, with the link to your comment. It will be removed in the next update.</p>
<h2>Keyboard shortcuts</h2><p><kbd>/</kbd> search · <kbd>h</kbd> home · <kbd>k</kbd> play · <kbd>l</kbd> like · <kbd>w</kbd> watch later · <kbd>?</kbd> all shortcuts · <kbd>Esc</kbd> close</p></div>"""
    page("/about/", f"About | {SITE['name']}", "How GolfVotes ranks golf lessons by independent recommendations.", about)
    page("/privacy/", f"Privacy | {SITE['name']}", "How GolfVotes handles your data: no cookies, no tracking, YouTube videos load only when you click play.", f"""<div class="prose"><h1 class="ptitle">Privacy</h1>
<p>No cookies and no tracking across sites. Liked videos, history, watch later and your theme are stored only in your browser (localStorage).</p>
<p><b>Visitor statistics:</b> We count page views with GoatCounter (goatcounter.com), a privacy-friendly service without cookies. It records the page, the referring site, browser type, screen size and country, but no personal data and no IP addresses are stored. This lets us see how many people use the site and where they come from. When you answer “Did this video fix it for you?”, that answer is counted the same way, without any personal data; your own vote is remembered only in your browser.</p>
<p><b>YouTube:</b> The small preview images are copies stored on this site, so looking at a page sends nothing to Google or YouTube. Videos play only after you click; then your browser connects to youtube-nocookie.com under Google's privacy policy.</p>
<p><b>Hosting:</b> {e(SITE.get('hosting_note', ''))}</p>
<h2>Legal basis and recipients</h2>
<p>When you open a page, your browser connects to GitHub (hosting) and to GoatCounter (visitor statistics, script from gc.zgo.at). Your IP address is necessarily transmitted to these services to deliver the content. Only when you click play does your browser also connect to Google/YouTube. We do not receive it and do not store it. Legal basis is our legitimate interest in running and improving a free website (Art. 6(1)(f) GDPR). GoatCounter stores no IP addresses and sets no cookies. GitHub and Google (after a click on play) may process data in the USA; both participate in the EU-US Data Privacy Framework.</p>
<p>Features you use yourself (likes, history, watch later, theme, your “fixed it” answer) are saved only in your browser (localStorage) and are not sent to us. You can delete them in Settings or in your browser. The statistics we keep are anonymous counts; we have no log files of our own.</p>
<h2>Your rights</h2>
<p>You have the right to access, rectification, erasure, restriction of processing, data portability and to object to processing based on legitimate interests (Art. 15–21 GDPR). Because we do not store personal data about visitors, there is usually nothing to hand out or delete, but write to the address below and we will check. You can also complain to a data protection authority, for example the Hessian Commissioner for Data Protection and Freedom of Information (Wiesbaden).</p>
<h2>Reddit comments</h2>
<p>Video pages quote short excerpts of public Reddit comments without usernames and with a link to the original. Authors can ask for removal by email or on GitHub; see <a href="{BASE}/about/#removal">About</a>.</p>
<p>{e(SITE.get('privacy_contact', ''))}</p></div>""")
    page("/imprint/", f"Imprint | {SITE['name']}", "Legal notice and contact information for GolfVotes, an independent golf lesson ranking.", f'<div class="prose"><h1 class="ptitle">Imprint</h1>{SITE.get("imprint_html", "")}</div>')
    for slug, nav, title, empty in [("liked", "liked", "Liked", "Videos you like show up here."), ("history", "history", "History", "Videos you open show up here."),
                                    ("later", "later", "Watch later", "Save videos to watch later."), ("search", "", "Search", "")]:
        page(f"/{slug}/", f"{title} | {SITE['name']}", title, f'<h1 class="ptitle" id="ltitle">{title}</h1><div class="grid" id="list" data-list="{slug}"></div><p class="dim" id="empty">{empty}</p>',
             nav=nav, canonical=False)


def build_index():
    """Compact client-side index for search, liked, history, later."""
    idx = [[v["vid"], v["title"], v["channel"], v["cs"] if v["cs"] in COACH_SET else "", v["recs"], v.get("success", 0),
            PNAME[v["top"]]["name"] if v["top"] in PNAME else "", [PNAME[t]["slug"] for t in (v.get("topic_counts") or {}) if t in PNAME],
            v.get("type") or "", v.get("level") or "", (v.get("years") or [0, 0])[1], (v.get("years") or [0, 0])[0], v.get("duration_s") or 0, v.get("views") or 0,
            {PNAME[t]["slug"]: n for t, n in (v.get("topic_counts") or {}).items() if t in PNAME}]
           for v in sorted(WATCH.values(), key=lambda x: -x["recs"])]
    probs = [[p["slug"], p["name"], p["q"], p["total_recs"]] for p in PROBLEMS if p["video_count"]]
    coaches = [[s, c["name"], c["recs"]] for s, c in COACHES]
    json.dump({"v": idx, "p": probs, "c": coaches}, open(os.path.join(OUT, "static", "index.json"), "w"), separators=(",", ":"), ensure_ascii=False)


def build_misc():
    for slug, target in (LINKS.get("go") or {}).items():
        d = os.path.join(OUT, "go", slug); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={e(target)}"><a href="{e(target)}" rel="sponsored">Continue</a>')
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /go/\nSitemap: {URL}/sitemap.xml\n")
    page("/404.html", f"Not found | {SITE['name']}", "Not found.", f'<h1 class="ptitle">That page moved.</h1><p class="lead">Pick your problem:</p><div class="tags">' + "".join(f'<a class="tag" href="{BASE}/fix/{PNAME[k]["slug"]}/">{e(PNAME[k]["name"])}</a>' for k in ["slice", "shank", "hook", "early_extension", "over_the_top", "chipping", "putting"] if k in PNAME) + '</div>', canonical=False)
    open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                                                     "".join(f"<url><loc>{e(u)}</loc><lastmod>{VDATA['generated']}</lastmod></url>" for u in SITEMAP) + "</urlset>")
    if SITE.get("cname"):
        open(os.path.join(OUT, "CNAME"), "w").write(SITE["cname"] + "\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(OUT, "static"), ignore=shutil.ignore_patterns("badge"))
    make_badges()
    PLAN_CARDS = build_plans()
    PLAN_CARDS_TOP = "".join(PLAN_CARDS.split("</a>")[i] + "</a>" for i in range(3))
    build_home(); build_categories(); build_client_pages()
    for p in PROBLEMS:
        build_problem(p)
    for v in WATCH.values():
        build_watch(v)
    build_coaches()
    for s, c in COACHES:
        build_coach(s, c)
    build_report(); build_text(); build_guides(); build_badges_page(); build_index(); build_misc()
    print(f"built {len(SITEMAP)} indexed pages, {len(WATCH)} watch pages, {len(COACHES)} coaches -> {OUT}")
