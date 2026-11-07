// Share images (1200x630) for link previews (WhatsApp, Reddit, X, Slack). Run: node build/og.js
// Writes static/og2/*.png. Needs Playwright + network access to i.ytimg.com for video frames.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const root = path.join(__dirname, '..');
const J = f => JSON.parse(fs.readFileSync(path.join(root, 'data', f)));
const problems = J('problems.json'), plans = fs.existsSync(path.join(root, 'data/plans.json')) ? J('plans.json') : [];
const videos = J('videos.json').videos.filter(v => v.recs >= 2), site = J('site.json');
const byId = Object.fromEntries(videos.map(v => [v.vid, v]));
const mark = fs.readFileSync(path.join(root, 'static/logo-mark.svg'), 'utf8');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const n = x => x.toLocaleString('en-US');
const totalRecs = J('videos.json').videos.reduce((a, v) => a + v.recs, 0);

function rankFor(key) {
  return videos.filter(v => (v.topic_counts || {})[key] >= site.min_recs_per_problem)
    .map(v => [v.topic_counts[key] + 0.75 * ((v.t_success || {})[key] || 0) + 0.02 * Math.min(v.recs, 50), v]).sort((a, b) => b[0] - a[0]).map(x => x[1]);
}

const tpl = (kicker, title, sub, thumbs) => `<!doctype html><html><head><style>
*{box-sizing:border-box;margin:0}body{width:1200px;height:630px;font-family:Inter,sans-serif;background:#fff;overflow:hidden}
.wrap{display:grid;grid-template-columns:640px 560px;height:630px}
.l{padding:56px 40px 48px 64px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:14px;font:700 34px Inter;letter-spacing:-.5px;color:#0f0f0f}.brand svg{width:56px;height:56px}.brand b{color:#0b7a4b}
.k{margin-top:48px;font:700 20px Inter;letter-spacing:2px;text-transform:uppercase;color:#0b7a4b}
h1{margin-top:12px;font:800 ${title.length > 48 ? 52 : 60}px/1.08 "Inter Display",Inter;letter-spacing:-1.5px;color:#0f0f0f}
.s{margin-top:22px;font:500 24px/1.35 Inter;color:#606060}
.url{margin-top:auto;font:600 22px Inter;color:#0b3d2c;background:#e8f5ee;border-radius:999px;padding:10px 20px;align-self:flex-start}
.r{background:#0b3d2c;position:relative;display:flex;flex-direction:column;justify-content:center;gap:18px;padding:0 48px 0 40px}
.v{position:relative;display:flex;gap:16px;align-items:center;background:rgba(255,255,255,.07);border-radius:16px;padding:12px}
.v img{width:208px;height:117px;object-fit:cover;border-radius:10px;flex:none;background:#123}
.v .t{color:#fff;font:600 19px/1.25 Inter;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.v .m{margin-top:8px;font:600 16px Inter;color:#3ecf8e;white-space:nowrap}
.rk{position:absolute;left:20px;top:20px;background:#3ecf8e;color:#0b3d2c;font:800 15px Inter;border-radius:6px;padding:2px 8px}
</style></head><body><div class="wrap"><div class="l">
<div class="brand">${mark}<span>Golf<b>Votes</b></span></div>
<div class="k">${esc(kicker)}</div><h1>${esc(title)}</h1><div class="s">${esc(sub)}</div><div class="url">golfvotes.com</div></div>
<div class="r">${thumbs.slice(0, 3).map((t, i) => `<div class="v"><img src="https://i.ytimg.com/vi/${t.v.vid}/hq2.jpg" onerror="this.src='https://i.ytimg.com/vi/${t.v.vid}/hqdefault.jpg'"><span class="rk">#${i + 1}</span><div><div class="t">${esc(t.v.title)}</div><div class="m">${esc(t.m)}</div></div></div>`).join('')}</div>
</div></body></html>`;

(async () => {
  const out = path.join(root, 'static/og2'); fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  const shot = async (name, html) => { await p.setContent(html, { waitUntil: 'networkidle' }); await p.screenshot({ path: path.join(out, name + '.png') }); };
  const top = [...videos].sort((a, b) => (b.recs + 0.75 * (b.success || 0)) - (a.recs + 0.75 * (a.success || 0)));
  const m = v => `${n(v.recs)} recommend` + (v.success ? ` · ✓ ${v.success} fixed it` : '');
  await shot('default', tpl('Golf lessons, ranked by golfers', 'Which golf video actually helps? Ask the golfers who tried them.',
    `${n(totalRecs)} recommendations from golfers · ${n(videos.length)} ranked lessons`, top.map(v => ({ v, m: m(v) }))));
  await shot('report', tpl('Data report', 'What golfers recommend to each other',
    `${site.stats.comments_scanned} comments read · ${n(totalRecs)} lesson recommendations`, top.map(v => ({ v, m: m(v) }))));
  for (const pr of problems) {
    const r = rankFor(pr.key); if (!r.length) continue;
    const tot = r.reduce((a, v) => a + v.topic_counts[pr.key], 0);
    await shot(pr.slug, tpl(pr.name, pr.q, `${r.length} lessons ranked by ${n(tot)} golfer recommendations`,
      r.map(v => ({ v, m: `${v.topic_counts[pr.key]} recommend` + ((v.t_success || {})[pr.key] ? ` · ✓ ${v.t_success[pr.key]} fixed it` : '') }))));
  }
  for (const pl of plans) {
    const items = pl.items.map(i => byId[i.vid]).filter(Boolean); if (!items.length) continue;
    const pr = problems.find(x => x.key === pl.key); const mins = Math.round(items.reduce((a, v) => a + (v.duration_s || 0), 0) / 60);
    await shot('plan-' + pr.slug, tpl('Fix plan · ' + pr.name, pl.title, `${items.length} videos${mins ? ` · ${mins} min` : ''} · in the order that makes sense`,
      items.map((v, i) => ({ v, m: `Step ${i + 1} · ${(v.topic_counts || {})[pl.key] || v.recs} golfers recommend` }))));
  }
  await b.close(); console.log('og images written to static/og2');
})();
