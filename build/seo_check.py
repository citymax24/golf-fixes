#!/usr/bin/env python3
"""Indexing gate: checks the built site (_site/) before it is deployed. Standard library only.

Search Console reports a problem weeks after it went live. Everything here is something Google would
otherwise find for us: a sitemap URL that cannot be indexed, a link that goes through a redirect, a page
no other page links to, two pages with the same title. An ERROR stops the deploy; a WARNING is printed.

    python3 build/build.py && python3 build/seo_check.py
    python3 build/seo_check.py --live   # also compares with the sitemap that is online right now

The page classes are read from the HTML itself, as a crawler would:
    redirect   <meta http-equiv="refresh">            must not be linked or listed
    noindex    <meta name="robots" content="noindex"> may be linked, must not be listed
    indexable  everything else                        must be listed, canonical to itself, linked, unique
"""
import argparse, collections, html, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
SITE = json.load(open(os.path.join(ROOT, "data", "site.json")))
URL = SITE["base_url"].rstrip("/")
BASE = SITE.get("base_path", "").rstrip("/")
THIN_WORDS = 120       # fewer words of own text than this on an indexable page: warning
MAX_DEPTH = 4          # clicks from the home page; deeper pages are rarely crawled
MAX_VANISHED = 0.02    # share of live URLs that one deploy may drop without a redirect

errors, warnings = collections.defaultdict(list), collections.defaultdict(list)
err = lambda rule, where: errors[rule].append(where)
warn = lambda rule, where: warnings[rule].append(where)


def text_words(doc):
    """Words of the page's own text: <main> without the footer and the related-lessons column."""
    m = re.search(r"<main\b.*?>(.*?)(?:<footer\b|</main>)", doc, re.S)
    t = m.group(1) if m else doc
    t = re.sub(r"<(script|style|svg|aside)\b.*?</\1>", " ", t, flags=re.S)
    return len(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def load_pages():
    pages = {}
    for d, _, files in os.walk(OUT):
        for f in files:
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(d, f), OUT).replace(os.sep, "/")
            path = "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)
            doc = open(os.path.join(d, f), encoding="utf-8").read()
            head = doc.split("</head>")[0]
            robots = re.search(r'<meta name="robots" content="([^"]*)"', head)
            canon = re.search(r'<link rel="canonical" href="([^"]*)"', head)
            title = re.search(r"<title>(.*?)</title>", head, re.S)
            desc = re.search(r'<meta name="description" content="([^"]*)"', head)
            kind = "redirect" if re.search(r'http-equiv="refresh"', head, re.I) else "noindex" if robots and "noindex" in robots.group(1) else "indexable"
            pages[path] = {"kind": kind, "doc": doc, "canonical": html.unescape(canon.group(1)) if canon else None,
                           "title": html.unescape(title.group(1)).strip() if title else "", "desc": html.unescape(desc.group(1)).strip() if desc else "",
                           "links": set()}
    return pages


def internal(href):
    """Site path of an internal link, None for external, mail and in-page links."""
    href = html.unescape(href).strip()
    if href.startswith(URL):
        href = href[len(URL):] or "/"
    elif href.startswith("//") or re.match(r"[a-z][a-z0-9+.-]*:", href, re.I) or not href.startswith("/"):
        return None
    if BASE and href.startswith(BASE):
        href = href[len(BASE):] or "/"
    return href.split("#")[0].split("?")[0]


def check_pages(pages):
    titles, descs = collections.defaultdict(list), collections.defaultdict(list)
    for path, p in pages.items():
        for href in re.findall(r'<a\b[^>]*?\bhref="([^"]*)"', p["doc"]):
            t = internal(href)
            if t is None:
                continue
            if t in pages:
                p["links"].add(t)
                if pages[t]["kind"] == "redirect" and p["kind"] != "redirect":
                    err("link to a redirect page (link the target instead)", f"{path} -> {t}")
            elif t + "/" in pages:
                err("link without trailing slash (the server answers with a redirect)", f"{path} -> {t}")
            elif not os.path.exists(os.path.join(OUT, t.lstrip("/"))):
                err("broken internal link", f"{path} -> {t}")
        if p["kind"] != "indexable":
            continue
        if p["canonical"] != URL + BASE + path:
            err("indexable page whose canonical is not its own URL", f"{path} (canonical: {p['canonical']})")
        if not p["title"]:
            err("indexable page without <title>", path)
        if not p["desc"]:
            err("indexable page without meta description", path)
        if len(re.findall(r"<h1\b", p["doc"])) != 1:
            err("indexable page without exactly one <h1>", path)
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', p["doc"], re.S):
            try:
                json.loads(block)
            except ValueError:
                err("structured data is not valid JSON", path)
        titles[p["title"].lower()].append(path)
        descs[p["desc"].lower()].append(path)
        if text_words(p["doc"]) < THIN_WORDS:
            warn(f"indexable page with fewer than {THIN_WORDS} words of own text", path)
    for t, ps in titles.items():
        if len(ps) > 1 and t:
            err("same <title> on several indexable pages", " = ".join(sorted(ps)))
    for t, ps in descs.items():
        if len(ps) > 1 and t:
            warn("same meta description on several indexable pages", " = ".join(sorted(ps)))


def check_reach(pages):
    """Every indexable page must be reachable from the home page by following links, within MAX_DEPTH clicks."""
    depth, queue = {"/": 0}, collections.deque(["/"])
    while queue:
        cur = queue.popleft()
        for t in pages[cur]["links"]:
            if t not in depth:
                depth[t] = depth[cur] + 1
                queue.append(t)
    for path, p in pages.items():
        if p["kind"] != "indexable" or path == "/":
            continue
        if path not in depth:
            err("indexable page that no page links to (orphan)", path)
        elif depth[path] > MAX_DEPTH:
            warn(f"indexable page more than {MAX_DEPTH} clicks from the home page", f"{path} ({depth[path]} clicks)")


def sitemap_locs(xml):
    return [html.unescape(x) for x in re.findall(r"<loc>(.*?)</loc>", xml)]


def read_sitemap():
    """All page URLs of sitemap.xml; follows a sitemap index into its parts. Returns {url: part file}."""
    root = os.path.join(OUT, "sitemap.xml")
    if not os.path.exists(root):
        err("sitemap.xml is missing", "/sitemap.xml")
        return {}
    xml = open(root, encoding="utf-8").read()
    if "<sitemapindex" not in xml:
        return {u: "sitemap.xml" for u in sitemap_locs(xml)}
    urls = {}
    for part in sitemap_locs(xml):
        name = part[len(URL + BASE):].lstrip("/")
        if not part.startswith(URL + BASE + "/") or not os.path.exists(os.path.join(OUT, name)):
            err("sitemap index lists a part that was not built", part)
            continue
        locs = sitemap_locs(open(os.path.join(OUT, name), encoding="utf-8").read())
        if not locs:
            err("empty sitemap part", name)
        for u in locs:
            if u in urls:
                err("URL listed in two sitemap parts", u)
            urls[u] = name
    return urls


def check_sitemap(pages):
    listed = read_sitemap()
    indexable = {URL + BASE + p for p, x in pages.items() if x["kind"] == "indexable"}
    for u in sorted(set(listed) - indexable):
        path = u[len(URL + BASE):]
        kind = pages[path]["kind"] if path in pages else "missing"
        err(f"sitemap lists a URL that is {kind}", u)
    for u in sorted(indexable - set(listed)):
        err("indexable page missing from the sitemap (add it, or mark it noindex)", u)
    robots = os.path.join(OUT, "robots.txt")
    txt = open(robots).read() if os.path.exists(robots) else ""
    if f"Sitemap: {URL}{BASE}/sitemap.xml" not in txt:
        err("robots.txt does not name the sitemap", "/robots.txt")
    for rule in re.findall(r"(?m)^Disallow:\s*(\S+)", txt):
        hit = [u for u in indexable if u[len(URL):].startswith(rule)]
        if hit:
            err(f"robots.txt blocks indexable pages (Disallow: {rule})", hit[0])
    return listed


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "seo-check"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def check_live(pages, listed):
    """URLs that are online now and would disappear with this deploy. A few go with the data (a lesson lost its
    recommendations); many at once means a slug or path changed and every old URL would turn into a 404."""
    try:
        xml = fetch(f"{URL}{BASE}/sitemap.xml")
        live = set()
        for u in sitemap_locs(xml):
            live.update(sitemap_locs(fetch(u))) if "<sitemapindex" in xml else live.add(u)
    except Exception as ex:  # the gate must not block a deploy because the old site is unreachable
        print(f"live comparison skipped: {ex}")
        return
    gone = sorted(u for u in live - set(listed) if u[len(URL + BASE):] not in pages)
    kept = sorted(u for u in live - set(listed) if u[len(URL + BASE):] in pages)
    print(f"live sitemap: {len(live)} URLs, {len(set(listed) - live)} new, {len(kept)} kept but no longer listed, {len(gone)} removed")
    for u in gone:
        warn("URL is online now and gone after this deploy (becomes a 404)", u)
    if live and len(gone) / len(live) > MAX_VANISHED:
        err(f"more than {MAX_VANISHED:.0%} of the live URLs disappear in one deploy (renamed paths need redirect pages)", f"{len(gone)} of {len(live)}, e.g. {gone[0]}")


def report(pages, listed):
    kinds = collections.Counter(p["kind"] for p in pages.values())
    parts = collections.Counter(listed.values())
    lines = ["## Indexing gate", "",
             f"{kinds['indexable']} indexable, {kinds['noindex']} noindex, {kinds['redirect']} redirect pages. "
             + "Sitemap: " + ", ".join(f"{n} in {f}" for f, n in sorted(parts.items())) + ".", ""]
    for label, found in (("ERROR", errors), ("WARNING", warnings)):
        for rule, items in found.items():
            lines.append(f"**{label}: {rule}** ({len(items)})")
            lines += [f"- `{x}`" for x in items[:10]] + ([f"- … {len(items) - 10} more"] if len(items) > 10 else []) + [""]
    if not errors:
        lines.append("No errors.")
    out = "\n".join(lines)
    print(out)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(out + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--live", action="store_true", help="compare with the sitemap that is online now")
    args = ap.parse_args()
    pages = load_pages()
    if "/" not in pages:
        sys.exit("no built site in _site/ (run build/build.py first)")
    check_pages(pages)
    check_reach(pages)
    listed = check_sitemap(pages)
    if args.live:
        check_live(pages, listed)
    report(pages, listed)
    sys.exit(1 if errors else 0)
