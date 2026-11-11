// Share images (1200x630) for link previews (WhatsApp, Reddit, X, Slack). Run: node build/og.js
// Writes static/og4/*.png in the look of the site: wordmark, the question in display type, the top three lessons as
// leaderboard rows. Pictures come from static/thumbs, so no network is needed. Needs Playwright and the Inter font.
// The folder name is part of the image URL: bump it (og4 -> og5, here, in build.py and in .github/workflows/share-images.yml)
// when the design changes, because networks cache preview images by URL.
// Only images whose content changed are drawn again (build/og-hashes.json remembers what each one was drawn from), so a
// data update commits the few images whose numbers moved, not all fifty. `node build/og.js --all` draws everything.
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const root = path.join(__dirname, '..');
const OUT = 'og4';
const J = f => JSON.parse(fs.readFileSync(path.join(root, 'data', f)));
const problems = J('problems.json'), plans = fs.existsSync(path.join(root, 'data/plans.json')) ? J('plans.json') : [];
const videos = J('videos.json').videos.filter(v => v.recs >= 2), site = J('site.json');
const byId = Object.fromEntries(videos.map(v => [v.vid, v]));
const word = fs.readFileSync(path.join(root, 'static/logo-word.svg'), 'utf8');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const n = x => x.toLocaleString('en-US');
const totalRecs = J('videos.json').videos.reduce((a, v) => a + v.recs, 0);
// same clean-up of video titles as nice() in build.py: no emoji, typographic apostrophes, no shouting
function nice(t) {
  t = (t || '').replace(/[\p{Extended_Pictographic}\u{FE0F}\u{200D}]/gu, '').replace(/(?<=\w)'(?=\w)/g, '\u2019').replace(/\s{2,}/g, ' ').trim();
  const letters = [...t].filter(c => /\p{L}/u.test(c));
  if (letters.length && letters.filter(c => c === c.toUpperCase() && c !== c.toLowerCase()).length / letters.length > 0.7) {
    const small = new Set(['a', 'an', 'the', 'and', 'or', 'to', 'for', 'of', 'in', 'on', 'with', 'your', 'at', 'by']);
    t = t.toLowerCase().split(' ').map((x, i) => (i && small.has(x)) ? x : x.slice(0, 1).toUpperCase() + x.slice(1)).join(' ');
  }
  return t;
}

function rankFor(key) {
  return videos.filter(v => (v.topic_counts || {})[key] >= site.min_recs_per_problem && !(v.duration_s > 0 && v.duration_s < 30))  // clips under 30 s are not ranked (CLIP_S in build.py)
    .map(v => [v.topic_counts[key] + 0.75 * ((v.t_success || {})[key] || 0) + 0.02 * Math.min(v.recs, 50), v]).sort((a, b) => b[0] - a[0]).map(x => x[1]);
}
function pic(vid) {  // the self-hosted preview picture as a data URI
  for (const q of ['hq2', 'mq2']) {
    const f = path.join(root, 'static/thumbs', q, vid + '.webp');
    if (fs.existsSync(f)) return 'data:image/webp;base64,' + fs.readFileSync(f).toString('base64');
  }
  return '';
}

// rows: [{v, n, ok}] ; the bar is each lesson's share of the first row's count
const tpl = (kicker, title, sub, rows) => {
  const mx = Math.max(...rows.slice(0, 3).map(r => r.n), 1);
  const size = title.length > 52 ? 48 : title.length > 30 ? 56 : 68;
  return `<!doctype html><html><head><style>
*{box-sizing:border-box;margin:0}body{width:1200px;height:630px;font-family:Inter,sans-serif;background:#fff;color:#0f0f0f;overflow:hidden}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) 548px;column-gap:48px;height:630px;padding:56px}
.l{display:flex;flex-direction:column;min-width:0}
.wm{height:34px}.wm svg{height:34px;width:auto;display:block;color:#0f0f0f}
.k{margin-top:60px;font:700 16px/20px Inter;letter-spacing:2.2px;text-transform:uppercase;color:#606060}
h1{margin-top:14px;font:800 ${size}px/1.04 Inter;letter-spacing:-.035em;word-spacing:.06em;text-wrap:balance}
.s{margin-top:20px;font:700 26px/1.3 Inter;letter-spacing:-.3px;color:#606060;text-wrap:balance}
.url{margin-top:auto;font:700 16px/20px Inter;letter-spacing:2.2px;text-transform:uppercase;color:#606060}
.r{align-self:center;border-top:1px solid #e5e5e5}
.row{display:grid;grid-template-columns:36px 192px minmax(0,1fr);column-gap:20px;align-items:center;padding:18px 0;border-bottom:1px solid #e5e5e5}
.p{font:800 34px/1 Inter;letter-spacing:-.02em;font-variant-numeric:tabular-nums}.row:nth-child(n+2) .p{color:#606060}
.th{width:192px;height:108px;border-radius:10px;background:#eaeaea center/cover no-repeat}
.t{min-width:0}
.t>b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font:600 21px/1.24 Inter;letter-spacing:-.1px}
.m{display:block;margin-top:8px;font:500 17px/20px Inter;color:#606060;white-space:nowrap}.m b{font-weight:800;color:#0f0f0f;font-variant-numeric:tabular-nums}.m i{font-style:normal;color:#0b7a4b;margin-left:12px}
.bar{display:block;height:5px;margin-top:10px;border-radius:3px;background:#e5e5e5;overflow:hidden}.bar i{display:block;height:100%;border-radius:3px;background:#0b7a4b}
</style></head><body><div class="wrap"><div class="l">
<div class="wm">${word}</div>
${kicker ? `<div class="k">${esc(kicker)}</div>` : '<div class="k" style="visibility:hidden">.</div>'}<h1>${esc(title)}</h1><div class="s">${esc(sub)}</div><div class="url">golfvotes.com</div></div>
<div class="r">${rows.slice(0, 3).map((r, i) => `<div class="row"><span class="p">${i + 1}</span><span class="th" style="background-image:url(${pic(r.v.vid)})"></span>
<span class="t"><b>${esc(nice(r.v.title))}</b><span class="m"><b>${n(r.n)}</b> recommend${r.n === 1 ? 's' : ''}${r.ok ? `<i>✓ ${r.ok} fixed it</i>` : ''}</span><span class="bar"><i style="width:${(100 * r.n / mx).toFixed(1)}%"></i></span></span></div>`).join('')}</div>
</div></body></html>`;
};

(async () => {
  const out = path.join(root, 'static', OUT); fs.mkdirSync(out, { recursive: true });
  const hashFile = path.join(root, 'build/og-hashes.json');
  const old = fs.existsSync(hashFile) && !process.argv.includes('--all') ? JSON.parse(fs.readFileSync(hashFile)) : {};
  const hashes = {}; let drawn = 0;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  await p.setContent('<body style="font:800 20px Inter">x</body>'); await p.evaluate(() => document.fonts.ready);
  if (!(await p.evaluate(() => document.fonts.check('800 20px Inter') && document.fonts.check('500 20px Inter')))) {
    console.error('The Inter font is not installed: the images would be drawn in a fallback font. Nothing written.'); await b.close(); process.exit(1);
  }
  const shot = async (name, html) => {
    const h = crypto.createHash('sha1').update(html).digest('hex'); hashes[name] = h;
    const file = path.join(out, name + '.png');
    if (old[name] === h && fs.existsSync(file)) return;
    await p.setContent(html, { waitUntil: 'load' }); await p.evaluate(() => document.fonts.ready); await p.screenshot({ path: file }); drawn++;
  };
  const top = [...videos].sort((a, b) => (b.recs + 0.75 * (b.success || 0)) - (a.recs + 0.75 * (a.success || 0)));
  const all = top.map(v => ({ v, n: v.recs, ok: v.success || 0 }));
  await shot('default', tpl('', 'Golf lessons, ranked by golfers.', `${n(totalRecs)} Reddit recommendations for YouTube lessons.`, all));
  await shot('report', tpl('The data', 'What golfers recommend to each other', `${site.stats.comments_scanned} comments read. ${n(totalRecs)} recommendations counted.`, all));
  for (const pr of problems) {
    const r = rankFor(pr.key); if (!r.length) continue;
    const tot = r.reduce((a, v) => a + v.topic_counts[pr.key], 0);
    await shot(pr.slug, tpl(pr.name, pr.q, `${n(tot)} recommendations for ${r.length} lesson${r.length === 1 ? '' : 's'}.`,
      r.map(v => ({ v, n: v.topic_counts[pr.key], ok: (v.t_success || {})[pr.key] || 0 }))));
  }
  for (const pl of plans) {
    const items = pl.items.map(i => byId[i.vid]).filter(v => v && !(v.duration_s > 0 && v.duration_s < 30)); if (!items.length) continue;
    pl.title = pl.title.replace(/in \d+ videos/, `in ${items.length} videos`);
    const pr = problems.find(x => x.key === pl.key); const mins = Math.round(items.reduce((a, v) => a + (v.duration_s || 0), 0) / 60);
    await shot('plan-' + pr.slug, tpl('Fix plan · ' + pr.name, pl.title, `${items.length} videos${mins ? `, ${mins} minutes` : ''}, in the order that makes sense.`,
      items.map(v => ({ v, n: (v.topic_counts || {})[pl.key] || v.recs, ok: 0 }))));
  }
  await b.close();
  fs.writeFileSync(hashFile, JSON.stringify(hashes, Object.keys(hashes).sort(), 1) + '\n');
  console.log(`share images: ${drawn} drawn, ${Object.keys(hashes).length - drawn} unchanged (static/${OUT})`);
})();
