#!/usr/bin/env python3
"""Index report: asks Google, URL by URL, whether each sitemap URL is indexed (Search Console URL Inspection API).

Search Console mails say "some pages"; this says which ones. It reads the sitemap of the built site, inspects the
URLs that were checked longest ago, and writes

    seo/index_status.json   what Google said last about every URL
    seo/index_report.md     indexed share per sitemap part, what changed, and what needs a fix

The API allows 2,000 inspections per day and property, so one run checks up to BUDGET URLs and the next run continues
where this one stopped. The run fails (and GitHub sends a mail) only when a URL shows a fault that is new since the
last run and ours to fix. "Crawled - currently not indexed" is Google's choice, not a fault, and is only counted.

    pip install google-auth requests
    GSC_SERVICE_ACCOUNT='{...key json...}' python3 build/gsc_report.py

The service account must be added as a user of the property in Search Console (Settings > Users and permissions).
"""
import collections, concurrent.futures, datetime, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site")
SITE = json.load(open(os.path.join(ROOT, "data", "site.json")))
URL = SITE["base_url"].rstrip("/")
HOST = URL.split("//")[1]
STATUS = os.path.join(ROOT, "seo", "index_status.json")
REPORT = os.path.join(ROOT, "seo", "index_report.md")
BUDGET = int(os.environ.get("GSC_BUDGET", 1900))
# Stop asking before the workflow's own time limit: the first run hit it after 45 minutes and lost every answer,
# because nothing was saved until the end. Answers are now saved as they come and the next run continues.
DEADLINE_S = 60 * int(os.environ.get("GSC_DEADLINE_MIN", 35))
SAVE_EVERY = 100
TODAY = datetime.date.today().isoformat()

INDEXED = {"Submitted and indexed", "Indexed, not submitted in sitemap"}
# Google knows the page and has not taken it (yet). Nothing is broken; the lever is the indexing threshold.
WAITING = {"Crawled - currently not indexed", "Discovered - currently not indexed", "URL is unknown to Google"}


def sitemap_parts():
    """{part name: [urls]} from the built sitemap index."""
    locs = lambda f: re.findall(r"<loc>(.*?)</loc>", open(os.path.join(OUT, f), encoding="utf-8").read())
    return {p.rsplit("/", 1)[1]: locs(p.rsplit("/", 1)[1]) for p in locs("sitemap.xml")}


def session():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    key = os.environ.get("GSC_SERVICE_ACCOUNT", "").strip()
    if not key:
        sys.exit("GSC_SERVICE_ACCOUNT is not set (repository secret with the service account's JSON key)")
    info = json.loads(key)
    print(f"service account: {info.get('client_email')}")
    return AuthorizedSession(service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"]))


def find_property(s):
    """The Search Console property for this site: the domain property if the account can see it, else the URL prefix."""
    r = s.get("https://www.googleapis.com/webmasters/v3/sites", timeout=30)
    if r.status_code != 200:
        sys.exit(f"Search Console API answered {r.status_code}: {r.text[:300]}")
    seen = {x["siteUrl"]: x.get("permissionLevel") for x in r.json().get("siteEntry", [])}
    for cand in (os.environ.get("GSC_PROPERTY"), f"sc-domain:{HOST}", f"{URL}/"):
        if cand and cand in seen and seen[cand] != "siteUnverifiedUser":
            print(f"property: {cand} ({seen[cand]})")
            return cand
    sys.exit(f"the service account cannot see a property for {HOST} (it sees: {sorted(seen) or 'none'}). "
             "Add its e-mail address as a user in Search Console > Settings > Users and permissions.")


class Quota(Exception):
    pass


def inspect(s, prop, url):
    r = s.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
               json={"inspectionUrl": url, "siteUrl": prop, "languageCode": "en-US"}, timeout=60)
    if r.status_code == 429:
        raise Quota(r.text[:200])
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:200]}")
    x = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
    row = {"s": x.get("coverageState", "unknown"), "t": TODAY}
    if x.get("lastCrawlTime"):
        row["c"] = x["lastCrawlTime"][:10]
    if x.get("googleCanonical") and x["googleCanonical"] != url:
        row["g"] = x["googleCanonical"]
    return row


def fault(row):
    """What is wrong with a URL in a way that is ours to fix, or None."""
    if row["s"] not in INDEXED | WAITING:
        return row["s"]
    if row.get("g"):
        return f"Google indexes another URL instead: {row['g']}"
    return None


def save_status(status, urls):
    keep = {p: status[p] for p in sorted(status) if URL + p in urls}  # URLs that left the sitemap are forgotten
    os.makedirs(os.path.dirname(STATUS), exist_ok=True)
    tmp = STATUS + ".tmp"
    json.dump(keep, open(tmp, "w"), indent=0, sort_keys=True)
    os.replace(tmp, STATUS)
    return keep


def run_inspections(s, prop, todo, status, urls):
    """Inspect with 4 threads, never more than 4 in flight, until done, the daily quota or the deadline."""
    done = failed = 0
    stop = None
    start = time.monotonic()
    queue = iter(todo)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        running = {}

        def refill():
            while not stop and len(running) < 4 and time.monotonic() - start < DEADLINE_S:
                u = next(queue, None)
                if u is None:
                    return
                running[pool.submit(inspect, s, prop, u)] = u
        refill()
        while running:
            fin, _ = concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
            for f in fin:
                u = running.pop(f)
                try:
                    status[u[len(URL):]] = f.result()
                    done += 1
                    if done % SAVE_EVERY == 0:
                        save_status(status, urls)
                        print(f"{done} inspected in {(time.monotonic() - start) / 60:.1f} min", flush=True)
                except Quota as ex:
                    stop = stop or str(ex)
                except Exception as ex:
                    failed += 1
                    if failed <= 5:
                        print(f"inspection failed for {u}: {ex}", flush=True)
                    if failed > 20 and not done:
                        sys.exit("every inspection fails; see the messages above")
            refill()
    if stop:
        print(f"daily quota reached after {done} URLs: {stop}", flush=True)
    elif done + failed < len(todo):
        print(f"deadline of {DEADLINE_S // 60} min reached after {done} URLs; the next run continues", flush=True)
    return done, failed


def write_report(parts, status, before, done):
    lines = [f"# Index report {TODAY}", "",
             f"What Google says about every URL in the sitemap. {done} URLs asked in this run; "
             "each line of the table counts the latest answer per URL.", "",
             "| Sitemap part | URLs | Indexed | Share | Crawled, not indexed | Discovered, not indexed | Unknown to Google | Fault | Not asked yet |",
             "|---|---|---|---|---|---|---|---|---|"]
    listed = set()
    for name, urls in list(parts.items()) + [("all", [u for us in parts.values() for u in us])]:
        c = collections.Counter()
        for u in urls:
            row = status.get(u[len(URL):])
            c["none" if not row else "fault" if fault(row) else "indexed" if row["s"] in INDEXED else row["s"]] += 1
        asked = len(urls) - c["none"]
        share = f"{100 * c['indexed'] / asked:.0f}%" if asked else "–"
        lines.append(f"| {name} | {len(urls)} | {c['indexed']} | {share} | {c['Crawled - currently not indexed']} | "
                     f"{c['Discovered - currently not indexed']} | {c['URL is unknown to Google']} | {c['fault']} | {c['none']} |")
        listed.update(u[len(URL):] for u in urls)
    is_in = lambda rows, p: p in rows and rows[p]["s"] in INDEXED and not fault(rows[p])
    gained = sorted(p for p in listed if is_in(status, p) and p in before and not is_in(before, p))
    lost = sorted(p for p in listed if is_in(before, p) and not is_in(status, p))
    faults = {p: fault(status[p]) for p in sorted(listed) if p in status and fault(status[p])}
    new_faults = {p: f for p, f in faults.items() if p not in before or fault(before[p]) != f}

    def block(title, items, fmt):
        lines.extend(["", f"## {title} ({len(items)})", ""])
        lines.extend([fmt(x) for x in items[:50]] + ([f"- … {len(items) - 50} more"] if len(items) > 50 else []) if items else ["None."])
    block("Needs a fix", list(faults), lambda p: f"- {'**new** ' if p in new_faults else ''}`{p}` {faults[p]}")
    block("Dropped out of the index since the last answer", lost, lambda p: f"- `{p}` now: {status[p]['s']}")
    block("Newly indexed", gained, lambda p: f"- `{p}`")
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    open(REPORT, "w").write("\n".join(lines) + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12 + len(parts)]))
    return new_faults


if __name__ == "__main__":
    parts = sitemap_parts()
    urls = [u for us in parts.values() for u in us]
    status = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    before = json.loads(json.dumps(status))
    s = session()
    prop = find_property(s)
    # never asked first, then the answers that are oldest; the sitemap order puts the important pages first among equals
    todo = sorted(urls, key=lambda u: status.get(u[len(URL):], {}).get("t", ""))[:BUDGET]
    print(f"{len(todo)} URLs to inspect (of {len(urls)}), deadline {DEADLINE_S // 60} min", flush=True)
    done, failed = run_inspections(s, prop, todo, status, set(urls))
    status = save_status(status, set(urls))
    new_faults = write_report(parts, status, before, done)
    if not done:
        sys.exit("no URL could be inspected")
    if new_faults:
        sys.exit(f"{len(new_faults)} URL(s) with a new fault, see seo/index_report.md")
