"""GolfVotes static site generator. No dependencies beyond the Python standard library.

Usage: python3 build/build.py            -> writes _site/
Inputs:  data/site.json, data/problems.json, data/videos.json, data/links.json (affiliate redirects, optional)
"""
import html, json, math, os, re, shutil, time
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
D = lambda f: json.load(open(os.path.join(ROOT, "data", f)))
SITE = D("site.json")
PROBLEMS = D("problems.json")
VDATA = D("videos.json")
VIDEOS = VDATA["videos"]
LINKS = D("links.json") if os.path.exists(os.path.join(ROOT, "data", "links.json")) else {}
BASE = SITE["base_path"].rstrip("/")          # "" for own domain, "/golf-fixes" for project pages
URL = SITE["base_url"].rstrip("/")
MIN_RECS = SITE.get("min_recs_per_problem", 2)
e = lambda s: html.escape(str(s or ""), quote=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "unknown"


def fmt_dur(s):
    if not s:
        return ""
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


# ---------- data shaping ----------
for v in VIDEOS:
    v["channel_slug"] = slugify(v.get("channel"))

by_problem = {}
for p in PROBLEMS:
    k = p["key"]
    rows = []
    for v in VIDEOS:
        n = (v.get("topic_counts") or {}).get(k, 0)
        if n >= MIN_RECS:
            ok = (v.get("t_success") or {}).get(k, 0)
            score = n + 0.75 * ok + 0.02 * min(v["recs"], 50)
            rows.append((score, n, ok, v))
    rows.sort(key=lambda r: -r[0])
    by_problem[k] = rows[: SITE.get("max_videos_per_problem", 30)]
    p["total_recs"] = sum(r[1] for r in rows)
    p["video_count"] = len(rows)

channels = defaultdict(lambda: {"recs": 0, "success": 0, "videos": [], "topics": Counter(), "url": None, "name": None})
for v in VIDEOS:
    c = channels[v["channel_slug"]]
    c["name"] = v.get("channel"); c["url"] = v.get("channel_url")
    c["recs"] += v["recs"]; c["success"] += v.get("success", 0); c["videos"].append(v)
    for t, n in (v.get("topic_counts") or {}).items():
        c["topics"][t] += n
COACHES = sorted([(s, c) for s, c in channels.items() if c["recs"] >= SITE.get("min_recs_per_coach", 10)],
                 key=lambda x: -x[1]["recs"])
PNAME = {p["key"]: p for p in PROBLEMS}

# #1 ranks per coach (for badges)
coach_wins = defaultdict(list)
for p in PROBLEMS:
    if by_problem[p["key"]]:
        top = by_problem[p["key"]][0][3]
        coach_wins[top["channel_slug"]].append(p)

TOTAL_RECS = sum(v["recs"] for v in VIDEOS)


# ---------- layout ----------
def page(path, title, desc, body, og_image=None, jsonld=None, canonical=True):
    full = f"{URL}{path}"
    og = og_image or f"{URL}/static/og/default.png"
    ld = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    nl = SITE.get("newsletter_url")
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{'<link rel="canonical" href="' + e(full) + '">' if canonical else ''}
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(full)}"><meta property="og:image" content="{e(og)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{BASE}/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE}/static/style.css?v={VDATA['generated']}">
{ld}
</head><body>
<header class="top"><div class="wrap">
  <a class="brand" href="{BASE}/"><span class="flag" aria-hidden="true"></span>{e(SITE['name'])}</a>
  <nav><a href="{BASE}/#problems">Problems</a><a href="{BASE}/coaches/">Coaches</a><a href="{BASE}/report/">Report</a><a href="{BASE}/about/">How it works</a></nav>
</div></header>
<main>{body}</main>
<footer class="foot"><div class="wrap">
  {f'<p class="nl">Get the most recommended fixes once a month. <a class="btn" href="{e(nl)}" rel="noopener">Subscribe</a></p>' if nl else ''}
  <p>{e(SITE['name'])}: {e(SITE['tagline'])} Rankings are based only on how often golfers independently recommended a video. Nobody can pay to rank higher.</p>
  <p><a href="{BASE}/about/">How it works</a> · <a href="{BASE}/privacy/">Privacy</a> · <a href="{BASE}/imprint/">Imprint</a> · Data updated {e(VDATA['generated'])}</p>
  <p class="small">Not affiliated with Reddit or YouTube. Video titles, thumbnails and players belong to their creators.</p>
</div></footer>
<script src="{BASE}/static/app.js?v={VDATA['generated']}" defer></script>
</body></html>"""
    dest = os.path.join(OUT, path.strip("/"), "index.html") if not path.endswith(".html") else os.path.join(OUT, path.strip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(doc)
    SITEMAP.append(full)


def video_card(rank, v, n, ok, k=None):
    notes = []
    for x in ((v.get("t_notes") or {}).get(k) or [])[:3]:
        x = x.strip().rstrip(".")
        if re.search(r"[\"'“”‘’]", x) or len(x) < 8:
            continue  # skip anything that looks like a quote from a comment
        if x and x.lower() not in {y.lower() for y in notes}:
            notes.append(x[0].upper() + x[1:])
    dur = fmt_dur(v.get("duration_s"))
    ok_txt = f'<span class="ok" title="Golfers who said this video fixed it for them">✓ {ok} said it fixed it</span>' if ok else ""
    return f"""<li class="card" id="v-{e(v['vid'])}">
  <div class="rank">{rank}</div>
  <div class="media"><button class="player" data-vid="{e(v['vid'])}" aria-label="Play: {e(v['title'])}">
    <span class="ph"><span class="play" aria-hidden="true"></span>{f'<span class="dur">{dur}</span>' if dur else ''}</span></button></div>
  <div class="info">
    <h3>{e(v['title'])}</h3>
    <p class="by"><a href="{BASE}/coach/{e(v['channel_slug'])}/">{e(v['channel'])}</a>{f' · {e(v["years"][0])}–{e(v["years"][1])}' if v.get('years') else ''}</p>
    <p class="votes"><strong>{n}</strong> golfers recommended it for this {ok_txt}</p>
    {('<ul class="why">' + ''.join(f'<li>{e(x)}</li>' for x in notes) + '</ul>') if notes else ''}
    <p class="links"><a href="https://www.youtube.com/watch?v={e(v['vid'])}" rel="noopener nofollow" target="_blank">Watch on YouTube ↗</a></p>
  </div>
</li>"""


def write_static():
    src = os.path.join(ROOT, "static")
    shutil.copytree(src, os.path.join(OUT, "static"), dirs_exist_ok=True)


# ---------- pages ----------
def build_home():
    groups = defaultdict(list)
    for p in PROBLEMS:
        if p["video_count"]:
            groups[p["group"]].append(p)
    order = ["Ball flight", "Contact", "Swing faults", "Swing sequence", "Setup", "Clubs", "Short game", "Training", "On the course"]
    tiles = ""
    for g in order:
        ps = sorted(groups.get(g, []), key=lambda p: -p["total_recs"])
        if not ps:
            continue
        tiles += f'<section class="group"><h2>{e(g)}</h2><div class="tiles">'
        for p in ps:
            tiles += (f'<a class="tile" href="{BASE}/fix/{p["slug"]}/" data-name="{e(p["name"].lower())} {e(p["q"].lower())}">'
                      f'<span class="t">{e(p["name"])}</span><span class="n">{p["total_recs"]:,} recommendations · {p["video_count"]} videos</span></a>')
        tiles += "</div></section>"
    top = sorted(VIDEOS, key=lambda v: -v["recs"])[:6]
    toplist = "".join(video_card(i + 1, v, v["recs"], v.get("success", 0), max(v["topic_counts"], key=v["topic_counts"].get) if v.get("topic_counts") else None)
                      for i, v in enumerate(top))
    body = f"""
<section class="hero"><div class="wrap">
  <h1>The golf fixes golfers <em>actually</em> recommend.</h1>
  <p class="lede">We read {SITE['stats']['comments_scanned']} comments from golf communities and counted which YouTube lessons golfers kept sending each other for each problem: {TOTAL_RECS:,} independent recommendations across {len(VIDEOS):,} videos. No algorithm, no sponsors, just what helped.</p>
  <label class="search"><span class="sr">Find your problem</span><input id="q" type="search" placeholder="What's wrong with your game? e.g. slice, shanks, chipping" autocomplete="off"></label>
</div></section>
<div class="wrap" id="problems">{tiles}</div>
<section class="wrap"><h2>Most recommended overall</h2><ol class="cards">{toplist}</ol></section>
"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE["name"], "url": URL + "/",
          "description": SITE["tagline"]}
    page("/", f"{SITE['name']}: {SITE['tagline']}", SITE["description"], body, jsonld=ld)


def build_problem(p):
    rows = by_problem[p["key"]]
    if not rows:
        return
    cards = "".join(video_card(i + 1, v, n, ok, p["key"]) for i, (s, n, ok, v) in enumerate(rows))
    total_ok = sum(r[2] for r in rows)
    related = [q for q in PROBLEMS if q["group"] == p["group"] and q["key"] != p["key"] and q["video_count"]]
    rel = "".join(f'<a href="{BASE}/fix/{q["slug"]}/">{e(q["name"])}</a>' for q in related)
    # Reserved monetization slots (empty until switched on in data/links.json)
    aids = LINKS.get("problem_aids", {}).get(p["key"], [])
    aids_html = ""
    if aids:
        aids_html = '<aside class="slot"><h3>Training aids golfers mention <span class="ad">Ad</span></h3><ul>' + "".join(
            f'<li><a href="{BASE}/go/{e(a["slug"])}/" rel="sponsored noopener">{e(a["name"])}</a> <span class="ad">Ad</span></li>' for a in aids) + "</ul></aside>"
    body = f"""
<section class="hero small"><div class="wrap">
  <p class="crumb"><a href="{BASE}/">All problems</a> › {e(p['group'])}</p>
  <h1>{e(p['q'])}</h1>
  <p class="lede">{e(p['intro'])}</p>
  <p class="meta"><strong>{len(rows)}</strong> videos golfers recommended for <strong>{e(p['name'].lower())}</strong>, ranked by <strong>{p['total_recs']:,}</strong> independent recommendations{f', including <strong>{total_ok}</strong> golfers who said it fixed it for them' if total_ok else ''}.</p>
</div></section>
<div class="wrap two">
  <ol class="cards">{cards}</ol>
  <aside class="side">
    {aids_html}
    <div class="slot"><h3>How this list works</h3><p>Every number is a different golfer who recommended the video to someone with this problem. Videos need at least {MIN_RECS} independent recommendations to appear. <a href="{BASE}/about/">Method</a></p></div>
    {f'<div class="slot"><h3>Related</h3><p class="rel">{rel}</p></div>' if rel else ''}
    {f'<div class="slot nl"><h3>Still {e(p["name"].lower())}?</h3><p>Get the newest top-voted fixes once a month.</p><a class="btn" href="{e(SITE["newsletter_url"])}">Subscribe</a></div>' if SITE.get("newsletter_url") else ''}
  </aside>
</div>"""
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": p["q"],
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"https://www.youtube.com/watch?v={r[3]['vid']}", "name": r[3]["title"]}
                              for i, r in enumerate(rows[:10])]}
    page(f"/fix/{p['slug']}/", f"{p['q']} The {len(rows)} videos golfers recommend most | {SITE['name']}",
         f"{p['intro']} Ranked by {p['total_recs']:,} independent recommendations from golfers.", body,
         og_image=f"{URL}/static/og/{p['slug']}.png", jsonld=ld)


def build_coaches():
    rows = ""
    for i, (s, c) in enumerate(COACHES, 1):
        tops = ", ".join(PNAME[t]["name"] for t, _ in c["topics"].most_common(3) if t in PNAME)
        rows += f'<tr><td>{i}</td><td><a href="{BASE}/coach/{s}/">{e(c["name"])}</a></td><td>{c["recs"]:,}</td><td>{len(c["videos"])}</td><td>{e(tops)}</td></tr>'
    body = f"""<section class="hero small"><div class="wrap"><h1>Most recommended golf coaches on YouTube</h1>
<p class="lede">Ranked by how many times golfers recommended their videos to other golfers.</p></div></section>
<div class="wrap"><table class="tbl"><thead><tr><th>#</th><th>Coach / channel</th><th>Recommendations</th><th>Videos</th><th>Most recommended for</th></tr></thead><tbody>{rows}</tbody></table></div>"""
    page("/coaches/", f"Most recommended golf coaches on YouTube | {SITE['name']}",
         "The YouTube golf instructors golfers recommend most, ranked by independent recommendations.", body)


def badge_svg(text1, text2):
    w = 8 + 7 * len(text1) + 8 + 7 * len(text2) + 8
    w1 = 8 + 7 * len(text1) + 4
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="28" role="img" aria-label="{e(text1)}: {e(text2)}">
<rect width="{w}" height="28" rx="6" fill="#0f3d2e"/><rect x="{w1}" width="{w - w1}" height="28" rx="6" fill="#f4efe3"/><rect x="{w1}" width="8" height="28" fill="#f4efe3"/>
<g font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" font-size="12" font-weight="600">
<text x="8" y="18" fill="#f4efe3">{e(text1)}</text><text x="{w1 + 6}" y="18" fill="#0f3d2e">{e(text2)}</text></g></svg>"""


def build_coach(s, c):
    vids = sorted(c["videos"], key=lambda v: -v["recs"])[:20]
    cards = "".join(video_card(i + 1, v, v["recs"], v.get("success", 0),
                               max(v["topic_counts"], key=v["topic_counts"].get) if v.get("topic_counts") else None) for i, v in enumerate(vids))
    tops = "".join(f'<li><a href="{BASE}/fix/{PNAME[t]["slug"]}/">{e(PNAME[t]["name"])}</a> <span>{n}</span></li>'
                   for t, n in c["topics"].most_common(8) if t in PNAME)
    wins = coach_wins.get(s, [])
    os.makedirs(os.path.join(OUT, "badge"), exist_ok=True)
    badges = ""
    for p in wins[:3]:
        fn = f"{s}--{p['slug']}.svg"
        open(os.path.join(OUT, "badge", fn), "w").write(badge_svg(SITE["name"], f"#1 recommended for {p['name'].lower()}"))
        snippet = f'<a href="{URL}/fix/{p["slug"]}/"><img src="{URL}/badge/{fn}" alt="#1 recommended for {e(p["name"].lower())} on {e(SITE["name"])}"></a>'
        badges += f'<div class="badge"><img src="{BASE}/badge/{fn}" alt=""><textarea readonly rows="2">{e(snippet)}</textarea></div>'
    body = f"""<section class="hero small"><div class="wrap">
<p class="crumb"><a href="{BASE}/coaches/">Coaches</a></p>
<h1>{e(c['name'])}</h1>
<p class="lede">Recommended <strong>{c['recs']:,}</strong> times by golfers across <strong>{len(c['videos'])}</strong> videos{f' · <strong>{c["success"]}</strong> golfers said a video fixed their problem' if c['success'] else ''}.</p>
{f'<p><a href="{e(c["url"])}" rel="noopener nofollow" target="_blank">YouTube channel ↗</a></p>' if c.get('url') else ''}
</div></section>
<div class="wrap two"><ol class="cards">{cards}</ol>
<aside class="side"><div class="slot"><h3>Most recommended for</h3><ul class="topics">{tops}</ul></div>
{f'<div class="slot"><h3>Badges for {e(c["name"])}</h3><p>Ranked #1 on {e(SITE["name"])}. Copy the code to show it on your site.</p>{badges}</div>' if badges else ''}
</aside></div>"""
    page(f"/coach/{s}/", f"{c['name']}: most recommended videos | {SITE['name']}",
         f"The {c['name']} videos golfers recommend most, ranked by {c['recs']:,} independent recommendations.", body)


def build_report():
    ps = sorted([p for p in PROBLEMS if p["total_recs"]], key=lambda p: -p["total_recs"])
    mx = ps[0]["total_recs"] if ps else 1
    bars = "".join(f'<div class="bar"><span class="l"><a href="{BASE}/fix/{p["slug"]}/">{e(p["name"])}</a></span>'
                   f'<span class="b" style="--w:{100 * p["total_recs"] / mx:.1f}%"></span><span class="v">{p["total_recs"]:,}</span></div>' for p in ps)
    cs = COACHES[:15]
    cmx = cs[0][1]["recs"] if cs else 1
    cbars = "".join(f'<div class="bar"><span class="l"><a href="{BASE}/coach/{s}/">{e(c["name"])}</a></span>'
                    f'<span class="b" style="--w:{100 * c["recs"] / cmx:.1f}%"></span><span class="v">{c["recs"]:,}</span></div>' for s, c in cs)
    st = SITE["stats"]
    body = f"""<section class="hero small"><div class="wrap"><h1>What golfers recommend to each other</h1>
<p class="lede">A data report from {st['comments_scanned']} comments in golf communities ({st['period']}).</p></div></section>
<div class="wrap prose">
<div class="kpis"><div><b>{st['comments_scanned']}</b><span>comments scanned</span></div><div><b>{st['yt_comments']}</b><span>comments with a YouTube link</span></div>
<div><b>{TOTAL_RECS:,}</b><span>independent lesson recommendations</span></div><div><b>{len(VIDEOS):,}</b><span>different videos</span></div></div>
<h2>Which problems golfers ask about most</h2><p>Recommendations per problem. A video can count for several problems.</p><div class="bars">{bars}</div>
<h2>The most recommended coaches</h2><div class="bars">{cbars}</div>
<h2>Method</h2><p>See <a href="{BASE}/about/">How it works</a>. The data is free to cite with a link to {e(SITE['name'])}.</p>
</div>"""
    page("/report/", f"What golfers recommend to each other: the data | {SITE['name']}",
         f"Which golf problems golfers ask about most and which YouTube coaches they recommend, based on {st['comments_scanned']} comments.", body,
         og_image=f"{URL}/static/og/report.png")


def build_text_pages():
    st = SITE["stats"]
    about = f"""<section class="hero small"><div class="wrap"><h1>How {e(SITE['name'])} works</h1></div></section>
<div class="wrap prose">
<p>Golf instruction on YouTube is endless, and the algorithm shows you what gets clicks, not what fixes swings. In golf communities, golfers constantly answer each other's questions with a link to the one lesson that helped them. {e(SITE['name'])} counts those answers.</p>
<h2>The method</h2>
<ol>
<li>We collected {st['comments_scanned']} public comments from golf-instruction communities ({st['period']}) and kept the {st['yt_comments']} that link to a YouTube video.</li>
<li>A language model read each comment and decided: is this a lesson recommendation (not a meme, highlight or equipment review)? Which problem is it about? Does the golfer say it fixed their problem?</li>
<li>Each golfer counts once per video. A video needs at least {MIN_RECS} independent recommendations for a problem to appear on that problem's list.</li>
<li>Videos are ranked by the number of recommendations for that problem, with extra weight when golfers report it actually fixed it.</li>
</ol>
<h2>What we don't do</h2>
<p>Nobody can pay to rank higher. If we ever show sponsored content or affiliate links, they are labeled and kept separate from the rankings. We don't republish anyone's comments or usernames, only counts and short summaries.</p>
<h2>Limits</h2>
<p>The data reflects what an online community recommends, mostly English-speaking golfers. Automated classification makes mistakes; the counts are large enough that single errors rarely change a ranking. Always check with a coach if something hurts.</p>
</div>"""
    page("/about/", f"How it works | {SITE['name']}", "How GolfVotes ranks golf lessons by independent recommendations.", about)
    privacy = f"""<section class="hero small"><div class="wrap"><h1>Privacy</h1></div></section><div class="wrap prose">
<p>This site sets no cookies and uses no tracking or analytics.</p>
<p><b>Videos:</b> Videos are not loaded until you click play. Only then does your browser connect to YouTube (youtube-nocookie.com), which receives your IP address and may store data under Google's privacy policy. If you turn on "Show previews", thumbnail images are loaded from YouTube (i.ytimg.com); this choice is stored only in your browser (localStorage) and can be turned off at any time.</p>
<p><b>Hosting:</b> {e(SITE.get('hosting_note', ''))}</p>
<p>{e(SITE.get('privacy_contact', ''))}</p></div>"""
    page("/privacy/", f"Privacy | {SITE['name']}", "Privacy information.", privacy)
    imprint = f"""<section class="hero small"><div class="wrap"><h1>Imprint</h1></div></section><div class="wrap prose">{SITE.get('imprint_html', '<p>Coming soon.</p>')}</div>"""
    page("/imprint/", f"Imprint | {SITE['name']}", "Imprint.", imprint)


def build_redirects():
    for slug, target in (LINKS.get("go") or {}).items():
        d = os.path.join(OUT, "go", slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(
            f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={e(target)}">'
            f'<link rel="canonical" href="{e(target)}"><a href="{e(target)}" rel="sponsored">Continue</a>')


def build_misc():
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /go/\nSitemap: {URL}/sitemap.xml\n")
    sm = "".join(f"<url><loc>{e(u)}</loc><lastmod>{VDATA['generated']}</lastmod></url>" for u in SITEMAP)
    open(os.path.join(OUT, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
    if SITE.get("cname"):
        open(os.path.join(OUT, "CNAME"), "w").write(SITE["cname"] + "\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    nf = f'<section class="hero small"><div class="wrap"><h1>Not found</h1><p class="lede"><a href="{BASE}/">Find your golf fix</a></p></div></section>'
    page("/404.html", f"Not found | {SITE['name']}", "Page not found.", nf, canonical=False)
    SITEMAP.pop()


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    SITEMAP = []
    write_static()
    build_home()
    for p in PROBLEMS:
        build_problem(p)
    build_coaches()
    for s, c in COACHES:
        build_coach(s, c)
    build_report()
    build_text_pages()
    build_redirects()
    build_misc()
    print(f"built {len(SITEMAP)} pages, {len(VIDEOS)} videos, {len(COACHES)} coaches -> {OUT}")
