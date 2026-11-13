# CLAUDE.md: GolfVotes (public site)

golfvotes.com: YouTube golf lessons ranked by how often golfers independently recommended them on Reddit,
sorted by problem (slice, shanks, chipping ...). Static site, Python standard library only, hosted on GitHub Pages.
README.md describes the project for readers; this file is what a Claude session needs to change it safely.

## This repository is PUBLIC
- Never put secrets, tokens, personal data, internal marketing notes or business plans in any file here,
  including this one, commit messages, issues and PR text.
- `docs/marketing/` exists locally on purpose and is excluded through `.git/info/exclude` (local-only).
  It must never be committed or pushed. Do not `git add -f` it, do not move its content into tracked files.
  Because the exclude lives in the shared git dir, it applies to every worktree of this checkout.
- Raw Reddit text and the classification pipeline are in a separate private repository (named in the owner's
  local notes, not here); it has its own CLAUDE.md. Nothing from it belongs here except the derived files below.

## Layout
- `build/build.py`: the whole static site generator (about 1,260 lines, stdlib only). Writes `_site/` (git-ignored).
- `build/seo_check.py`: indexing gate that reads `_site/` like a crawler (sitemap, canonicals, redirects, orphans,
  duplicate titles, thin pages). Any ERROR fails the run; warnings only print.
- `build/refresh_youtube.py`, `fetch_thumbs.py`: YouTube metadata refresh and self-hosted preview images.
- `build/gsc_report.py`: Search Console index report (needs `google-auth`, `requests`).
- `build/og.js` (Playwright): share images in `static/og4/`; `build/og-hashes.json` records what was drawn.
- `build/make_*.py`, `badge_art.py`, `badge-png.js`: one-off asset generators (logo, course art, coach badges).
- `data/`: JSON inputs, see next section. `static/`: CSS, JS, fonts, thumbs, badges, share images.
- `seo/`: written by the Index report workflow (`index_report.md`, `index_status.json`); it does not exist until that first runs.

## Build and check locally
Local `python3` may be 3.9; CI uses 3.12. Build with 3.12 so local and CI behave the same:

    uv run --python 3.12 --no-project python build/build.py
    uv run --python 3.12 --no-project python build/seo_check.py          # offline gate on _site/
    uv run --python 3.12 --no-project python build/seo_check.py --live   # also diff against the online sitemap

Run both after any change to build.py, data or static assets. `--live` needs network and is what CI runs;
it fails if a deploy would drop more than 2% of the live URLs without a redirect. Do not hand-edit `_site/`.

## Data files and who owns them
Written by the private pipeline's monthly run (publish.py, years.py); do not hand-edit counts or stats:
- `data/videos.json` (per-video counts, labels, `stats`), `data/comments.json` (excerpts), `data/recency.json`,
  `data/years.json` (recommendations per video and calendar year), and the `stats` block inside `data/site.json`
  (`comments_scanned`, `yt_comments`; the pipeline also adds `labelled` and `videos` counts to `videos.json`).
- Also machine-written: views, duration, publish date and title in `data/videos.json` (`refresh_youtube.py`),
  `static/thumbs/` (`fetch_thumbs.py`), `static/og4/` (share-images workflow).
A hand edit to these gets overwritten at the next run and can make counts disagree between pages.

Edited by hand (the source of truth for wording and rules):
- `data/site.json`: name, URLs, thresholds (`min_recs_per_problem`, `min_recs_per_coach`, `min_recs_indexed`,
  `max_videos_per_problem`), newsletter URL, legal contact lines and the imprint HTML.
- `data/problems.json`: problem taxonomy and intro texts. `data/links.json`: affiliate redirects and ad slots.
- Page texts and the remaining constants (`MIN`, `STRONG_MIN = 3`, `CLIP_S = 30` seconds) live in `build/build.py`.

## Ranking principle (do not weaken)
- Only independent recommendations count: each golfer once per video; a problem ranking needs at least
  `min_recs_per_problem` different golfers; clips under 30 s keep their page but are not ranked.
- Nobody can pay to rank higher. The About page promises this. Sponsored or affiliate content must stay outside
  the rankings, be visibly labeled, and use `rel="sponsored"`.
- `data/links.json` is currently empty (`go` and `problem_aids` have no entries), so nothing sponsored is shown.
  `/go/<slug>/` redirects are `noindex` and disallowed in robots.txt. A product/affiliate box per problem is
  postponed until the site has traffic; do not build it unprompted.

## Pages and sitemap
- Lesson pages `/watch/<vid>/`, coach pages `/coach/<slug>/`, problem pages, guides, badges, About, Privacy, Imprint.
- Year pages `/year/<y>/` come from `build_year(y)`, only for years in `YEARS`: a year must be finished (it appears
  from March of the following year), have at least 1,000 recommendations in `data/years.json`, and have a lesson
  with a page that is not a clip. Without `data/years.json` no year pages are built. Currently 2022 to 2025.
- The sitemap is split by kind: `sitemap-pages.xml`, `-coaches`, `-lessons`, `-lessons-tail`, `-years`; empty parts
  are omitted and `sitemap.xml` is the index. Lessons with fewer than `STRONG_MIN` (3) recommendations are the tail.
  Search Console reports indexing per part, so do not merge the parts or rename them without checking the
  `--live` diff: a renamed path can turn hundreds of URLs into 404s.
- Lesson titles are compared case-insensitively (`TITLE_COUNT` in build.py); seo_check fails on the same `<title>`
  on several indexable pages, and on indexable pages that nothing links to.

## Privacy, comments, legal texts
- Video pages show short excerpts of public Reddit comments and problem pages quote post titles, always without
  usernames and always linked to the original. Removal process: the About page (`#removal`), by email or GitHub issue;
  removal happens in the next data update. Never add an author name, user link or `u/` mention to a page or to data.
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
- `share-images.yml`: on push to `main` touching `data/**`, `build/og.js`, `static/logo-word.svg` or itself;
  runs `node build/og.js` and commits only changed images to `static/og4/` and `build/og-hashes.json`,
  then triggers `pages.yml`.
- Bots commit to `main` as golfvotes-bot, so expect rebases and `git pull --rebase` before pushing manually.
- Actions are pinned by commit SHA; keep that when editing workflows. Never print secrets in logs.

## Working rules
- Work on a branch and open a PR; do not push to `main` directly. Merging to `main` is a production deploy, so
  before merging have an architect review and a devops review (agents `project-architect` and
  `devops-deployment-specialist`).
- Do not commit or push unless asked.
- Documentation goes through the `docs-guardian` agent, in English, under `docs/` in a fitting subdirectory
  (check the existing structure first). `docs/marketing/` is not a place for committed docs.
- Keep this file under 500 lines and update it whenever workflows, data ownership or the rules above change.
- Ad-hoc model work (classifying comments, labelling lessons, summaries) runs in the Claude session through
  subagents. Do not use an Anthropic API key, and do not copy keys from the private repository's secrets.
- Site copy is English only.
