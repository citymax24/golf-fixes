#!/usr/bin/env bash
# One command for everything that must pass before a merge to main:
#   1. build the site with Python 3.12 (as CI does; through uv when it is installed)
#   2. then, at the same time: the indexing gate (build/seo_check.py) and the browser check (build/site_check.js)
# Usage:  build/check.sh           offline gate
#         build/check.sh --live    the gate also compares with the sitemap online, exactly as CI does before a deploy
# Exit code 1 if any step fails. The output of each step is kept in _site/.check/ for a closer look.
set -u
cd "$(dirname "$0")/.."
t0=$(date +%s)
if command -v uv >/dev/null 2>&1; then PY=(uv run --quiet --python 3.12 --no-project python); else PY=(python3); echo "note: uv not found, building with $(python3 --version)"; fi

echo "build ..."
blog=$(mktemp)  # its own log per run: several runs at once (worktrees, reviews) must not mix up their output
if ! "${PY[@]}" build/build.py > "$blog" 2>&1; then cat "$blog"; rm -f "$blog"; echo "FAIL build"; exit 1; fi
tail -1 "$blog"
mkdir -p _site/.check && mv "$blog" _site/.check/build.log

echo "indexing gate and browser check, side by side ..."
"${PY[@]}" build/seo_check.py "$@" > _site/.check/seo.log 2>&1 & seo=$!
node build/site_check.js > _site/.check/site.log 2>&1 & site=$!
wait $seo; seo_rc=$?
wait $site; site_rc=$?

echo; echo "--- indexing gate"; grep -E "^\*\*ERROR|^\*\*WARNING|^No errors|ERROR" _site/.check/seo.log | head -20
echo; echo "--- browser check"; grep -v -E "agent-proxy|^- www\.|For details" _site/.check/site.log
echo
rc=0
[ $seo_rc -ne 0 ] && { echo "FAIL indexing gate (see _site/.check/seo.log)"; rc=1; }
[ $site_rc -ne 0 ] && { echo "FAIL browser check (see _site/.check/site.log)"; rc=1; }
if [ $rc -eq 0 ]; then
  if grep -q "a11y skipped" _site/.check/site.log; then echo "PASSED in $(( $(date +%s) - t0 )) s, but accessibility and contrast were NOT checked: npm i --no-save axe-core"; else echo "ALL PASSED in $(( $(date +%s) - t0 )) s"; fi
fi
exit $rc
