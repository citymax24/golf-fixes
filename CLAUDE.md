# CLAUDE.md: GolfVotes (public site)

golfvotes.com: YouTube golf lessons ranked by how often golfers independently recommended them on Reddit,
sorted by problem (slice, shanks, chipping ...). Static site, Python standard library only, hosted on GitHub Pages.
README.md describes the project for readers; this file is what a Claude session needs to change it safely.

## This repository is PUBLIC
- Never put secrets, tokens, personal data, internal marketing notes or business plans in any file here,
  including this one, commit messages, issues and PR text.
- Local-only notes stay untracked. Never `git add -f` ignored or excluded files, and do not move their content
  into tracked files.
- Raw Reddit text and the classification pipeline live in a separate private repository with its own CLAUDE.md.
  Nothing from it belongs here except the derived data files described below.

## Layout
- `build/build.py`: the whole static site generator (stdlib only). Writes `_site/` (git-ignored).
- `build/seo_check.py`: indexing gate that reads `_site/` like a crawler (sitemap, canonicals, redirects, orphans,
  duplicate titles, thin pages). Any ERROR fails the run; warnings only print.
- `build/refresh_youtube.py`, `fetch_thumbs.py`: YouTube metadata refresh and self-hosted preview images.
- `build/gsc_report.py`: Search Console index report (needs `google-auth`, `requests`).
- `build/og.js` (Playwright): share images in `static/og4/`; `build/og-hashes.json` records what was drawn.
- `build/make_*.py`, `badge_art.py`, `badge-png.js`: asset generators (logo, course art, coach badges).
- `data/`: JSON inputs, see next section. `static/`: CSS, JS, fonts, thumbs, badges, share images.
- `seo/`: written by the Index report workflow (`index_report.md`, `index_status.json`); it does not exist until that first runs.

## Build and check locally
The build needs Python 3.12 (as in CI); the system `python3` may be older. Use uv:

    uv run --python 3.12 --no-project python build/build.py
    uv run --python 3.12 --no-project python build/seo_check.py          # offline gate on _site/
    uv run --python 3.12 --no-project python build/seo_check.py --live   # also diff against the online sitemap

Run both after any change to build.py, data or static assets. `--live` needs network and is what CI runs;
it fails if a deploy would drop more than 2% of the live URLs without a redirect. Do not hand-edit `_site/`.

## Data files and who owns them
Machine-written, do not hand-edit counts or stats; a hand edit is overwritten at the next run and can make counts
disagree between pages:
- `data/videos.json` (per-video counts, labels, `stats`), `data/comments.json` (excerpts), `data/recency.json`,
  `data/years.json`, and in `data/site.json` only the `stats` keys `comments_scanned` and `yt_comments`.
  All of these come from the monthly pipeline run in a separate private repo.
- `data/videos.json` fields views, duration, publish date and title: `refresh_youtube.py` (refresh workflow).
- `data/awards.json`: written by `make_badges()` in build.py (awards are only ever added, a badge stays valid for its year).
  `data/coach_slugs.json`: written by build.py (first slug seen per channel URL and name). Changing a slug changes
  a public URL and breaks embedded badges: add a redirect and run `seo_check.py --live`.
- `static/thumbs/`: `fetch_thumbs.py`. `static/badge/`: drawn by the build, committed by the monthly run.
  `static/og4/` and `build/og-hashes.json`: share-images workflow. Do not hand-edit any of these.

Written in Claude sessions and committed like code (no workflow writes them; source of truth is the file):
- `data/seo.json` (problem explainer texts), `data/cards.json` (lesson cards), `data/video_meta.json` (type, level,
  summary per video), `data/plans.json` (fix plans), `data/reddit.json` (symptom threads and insights per problem).

Edited by hand:
- `data/site.json`: name, URLs, thresholds, newsletter URL, legal contact lines and the imprint HTML.
- `data/problems.json`: problem taxonomy and intro texts. `data/links.json`: affiliate redirects and ad slots.
- Page texts and two constants live in `build/build.py`.

Constants and where they come from:
- `MIN` = `min_recs_per_problem` in site.json. `min_recs_per_coach` and `max_videos_per_problem` also come from there.
- `min_recs_indexed` in site.json is optional and defaults to `MIN` (read as `INDEX_MIN`).
- Literals in build.py: `STRONG_MIN` (lessons below it go to the sitemap tail) and `CLIP_S` (clips shorter than this
  many seconds are not ranked). The year-page threshold on total recommendations is hardcoded where `YEARS` is computed.
- Change a value in one place only and let this file name the constant, not repeat the number.

## Pipeline contract
The data files above are produced by the monthly pipeline run in a separate private repo; this repo is its only consumer.
- `data/site.json` is changed by that run only in `stats` (`comments_scanned`, `yt_comments`).
- `data/years.json` is copied in by that run and must come from the same run as `data/videos.json`. Shape:
  `{"generated": "YYYY-MM-DD", "videos": {vid: {year: [recs, fixed_it, {topic: [recs, fixed_it]}]}}}`, counted like
  `videos.json` (each golfer once per video and year). `build.py` reads it as `YDATA`.
- Changing a data schema, a reader in build.py or a threshold needs a matching change in the pipeline.

## Ranking principle (do not weaken)
- Only independent recommendations count: each golfer once per video; a problem ranking needs at least
  `min_recs_per_problem` different golfers; clips under `CLIP_S` seconds keep their page but are not ranked.
- Nobody can pay to rank higher. The About page promises this. Sponsored or affiliate content must stay outside
  the rankings, be visibly labeled, and use `rel="sponsored"`.
- `/go/<slug>/` redirects from `data/links.json` are `noindex` and disallowed in robots.txt. Do not add
  product or affiliate boxes unprompted.

## Pages and sitemap
- Lesson pages `/watch/<vid>/`, coach pages `/coach/<slug>/`, problem pages, guides, badges, About, Privacy, Imprint.
- Year pages `/year/<y>/` come from `build_year(y)`, only for years in `YEARS`: a year must be finished (it appears
  from March of the following year), reach the recommendation threshold in `data/years.json`, and have a lesson
  with a page that is not a clip. Without `data/years.json` no year pages are built.
- The sitemap is split by kind: `sitemap-pages.xml`, `-coaches`, `-lessons`, `-lessons-tail`, `-years`; empty parts
  are omitted and `sitemap.xml` is the index. Lessons with fewer than `STRONG_MIN` recommendations are the tail.
  Search Console reports indexing per part, so do not merge the parts or rename them without checking the
  `--live` diff: a renamed path can turn hundreds of URLs into 404s.
- Lesson titles are compared case-insensitively (`TITLE_COUNT` in build.py); seo_check fails on the same `<title>`
  on several indexable pages, and on indexable pages that nothing links to.

## Privacy, comments, legal texts
- Video pages show short excerpts of public Reddit comments and problem pages quote post titles, always without
  usernames and always linked to the original. Removal process: the About page (`#removal`), by email or GitHub issue;
  removal happens in the next data update. Never add an author name, user link or `u/` mention to a page or to data.
- Do not render new data fields on pages without checking that they contain no usernames.
- Privacy and Imprint pages are built by `build.py` and `data/site.json` (`privacy_contact`, `imprint_html`,
  `hosting_note`). The Privacy text states the current tracking facts: GoatCounter page counts without cookies,
  YouTube videos load only on click (youtube-nocookie.com), self-hosted preview images. A CSP meta tag in
  `build.py` allows only those hosts. If you add or change tracking, a script, an embed, an external host or an
  affiliate link, update the Privacy text, the CSP and, if relevant, the About page in the same change.
- Contact address everywhere: `hello@golfvotes.com`. Do not reintroduce another address.

## CI workflows (.github/workflows/)
- `pages.yml`: on push to `main` (and manual): Python 3.12, `build.py`, then `seo_check.py --live` as gate, then
  deploy `_site/` to GitHub Pages. A gate error blocks the deploy.
- `refresh-youtube.yml`: every 14 days (YouTube API terms need data refreshed within 30 days), secret
  `YOUTUBE_API_KEY`; commits `data/videos.json` and `static/thumbs`, then triggers `pages.yml` itself
  (a push by Actions does not start it).
- `index-report.yml`: Mondays and Thursdays, secret `GSC_SERVICE_ACCOUNT`; commits `seo/`.
- `share-images.yml`: on push to `main` touching `data/**`, `build/og.js`, `build/course.svg`, `static/style.css`,
  `static/logo-word.svg` or itself; runs `node build/og.js` and commits only changed images to `static/og4/` and
  `build/og-hashes.json`, then triggers `pages.yml`. The home page's card (`home.png`, also the fallback for pages
  without their own card) is drawn with the site's stylesheet and the course drawing, hence those two paths.
  `default.png` is the card it replaced: no longer drawn, kept for links shared before.
- Bots commit to `main` as golfvotes-bot, so expect rebases and `git pull --rebase` before pushing manually.
- Actions are pinned by commit SHA; keep that when editing workflows. Never print secrets in logs.

## Working rules
- Work on a branch and open a PR; do not push to `main` directly. Merging to `main` is a production deploy, so
  review before merging: an architecture review and a devops review.
- Do not commit or push unless asked.
- Documentation is written in English under `docs/` in a fitting subdirectory (check the existing structure first).
- Keep this file under 500 lines and update it whenever workflows, data ownership or the rules above change.
- Ad-hoc model work in a Claude session (classifying, labelling, summaries) runs through subagents, never with an
  API key; the scheduled pipeline run is separate.
- Site copy is English only.
