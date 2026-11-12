"""Self-host the small video preview images the site shows (no request from visitors to Google/YouTube).
Scans the built site (_site) for /static/thumbs/<q>/<vid>.webp references, adds the small picture of every lesson in
the search index, and downloads the missing ones.
Run after `python3 build/build.py`; then rebuild. Needs Pillow (pip install pillow)."""
import os, re, sys, glob, urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "static", "thumbs")
refs = set()
for f in glob.glob(os.path.join(ROOT, "_site", "**", "*.*"), recursive=True):
    if f.endswith((".html", ".json", ".js")):
        refs.update(re.findall(r"/static/thumbs/(mq2|hq2)/([A-Za-z0-9_-]{11})\.webp", open(f, encoding="utf-8", errors="ignore").read()))
# Search, browse and the saved lists are drawn in the browser from index.json and show the small picture of every lesson,
# so every lesson in the index needs one, not only those a built page points to.
ix = os.path.join(ROOT, "_site", "static", "index.json")
if os.path.exists(ix):
    import json
    refs.update(("mq2", v[0]) for v in json.load(open(ix, encoding="utf-8"))["v"])
need = sorted(r for r in refs if not os.path.exists(os.path.join(OUT, r[0], r[1] + ".webp")))
print(f"referenced {len(refs)}, missing {len(need)}")


def get(r):
    q, vid = r
    for variant in (q, "mqdefault" if q == "mq2" else "hqdefault"):
        try:
            req = urllib.request.Request(f"https://i.ytimg.com/vi/{vid}/{variant}.jpg", headers={"User-Agent": "GolfVotes-build/1.0"})
            im = Image.open(BytesIO(urllib.request.urlopen(req, timeout=20).read())).convert("RGB")
            os.makedirs(os.path.join(OUT, q), exist_ok=True)
            im.save(os.path.join(OUT, q, vid + ".webp"), "WEBP", quality=70, method=6)
            return True
        except Exception:
            continue
    return False


with ThreadPoolExecutor(12) as ex:
    ok = list(ex.map(get, need))
print(f"downloaded {sum(ok)}, failed {len(ok) - sum(ok)}")
sys.exit(0)
