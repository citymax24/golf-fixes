"""Refresh YouTube metadata (views, duration, publish date, title) in data/videos.json.
YouTube API Services policy: stored API data must be refreshed within 30 days. Runs via GitHub Actions.
Needs env YOUTUBE_API_KEY; exits quietly without it.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

KEY = os.environ.get("YOUTUBE_API_KEY")
if not KEY:
    print("YOUTUBE_API_KEY not set, skipping"); sys.exit(0)
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "videos.json")
data = json.load(open(P))
vids = data["videos"]


def iso(s):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    return None if not m else sum(int(x or 0) * k for x, k in zip(m.groups(), (86400, 3600, 60, 1)))


found = {}
ids = [v["vid"] for v in vids]
for i in range(0, len(ids), 50):
    q = urllib.parse.urlencode({"part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50]), "key": KEY})
    try:
        d = json.load(urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}")  # never print the URL (contains the key)
    for it in d.get("items", []):
        found[it["id"]] = it
    time.sleep(0.1)

gone = 0
for v in vids:
    it = found.get(v["vid"])
    if not it:
        v["views"] = v["duration_s"] = None; gone += 1
        continue
    v["title"] = it["snippet"]["title"]
    v["published"] = it["snippet"]["publishedAt"][:10]
    v["views"] = int(it.get("statistics", {}).get("viewCount", 0))
    v["duration_s"] = iso(it["contentDetails"].get("duration"))
data["youtube_refreshed"] = time.strftime("%Y-%m-%d")
json.dump(data, open(P, "w"), ensure_ascii=False)
print(f"refreshed {len(found)} videos, {gone} unavailable")
