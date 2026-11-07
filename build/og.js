// Generates 1200x630 share images into static/og/. Run after build.py: node build/og.js
// Needs Playwright with Chromium (preinstalled in the build environment).
const { chromium } = require('playwright');
const fs = require('fs'); const path = require('path');
const root = path.join(__dirname, '..');
const problems = JSON.parse(fs.readFileSync(path.join(root, 'data/problems.json')));
const videos = JSON.parse(fs.readFileSync(path.join(root, 'data/videos.json'))).videos;
const site = JSON.parse(fs.readFileSync(path.join(root, 'data/site.json')));
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const tpl = (kicker, title, sub) => `<!doctype html><html><body style="margin:0">
<div style="width:1200px;height:630px;box-sizing:border-box;padding:70px 80px;background:#f7f4ec;font-family:Georgia,serif;position:relative;overflow:hidden">
 <div style="position:absolute;right:-120px;top:-120px;width:520px;height:520px;border-radius:50%;background:#0f3d2e;opacity:.08"></div>
 <div style="font:700 30px system-ui,sans-serif;color:#0f3d2e;display:flex;align-items:center;gap:14px">
  <span style="display:inline-block;width:4px;height:40px;background:#14211b;position:relative"><span style="position:absolute;left:4px;top:0;border-left:26px solid #d6452c;border-top:11px solid transparent;border-bottom:11px solid transparent"></span></span>${esc(site.name)}</div>
 <div style="font:600 28px system-ui,sans-serif;color:#1d6b4f;margin-top:56px;text-transform:uppercase;letter-spacing:2px">${esc(kicker)}</div>
 <div style="font-size:76px;line-height:1.05;font-weight:700;color:#14211b;margin-top:14px;max-width:1000px">${esc(title)}</div>
 <div style="font:400 32px system-ui,sans-serif;color:#5b6b62;margin-top:26px;max-width:1000px">${esc(sub)}</div>
</div></body></html>`;
(async () => {
  const out = path.join(root, 'static/og'); fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  const shot = async (name, html) => { await p.setContent(html); await p.screenshot({ path: path.join(out, name + '.png') }); };
  const total = videos.reduce((a, v) => a + v.recs, 0);
  await shot('default', tpl('Golf lessons, ranked by golfers', site.tagline, `${total.toLocaleString('en-US')} independent recommendations across ${videos.length.toLocaleString('en-US')} videos`));
  await shot('report', tpl('Data report', 'What golfers recommend to each other', `${site.stats.comments_scanned} comments analyzed · ${site.stats.period}`));
  for (const pr of problems) {
    const n = videos.reduce((a, v) => a + ((v.topic_counts || {})[pr.key] >= site.min_recs_per_problem ? v.topic_counts[pr.key] : 0), 0);
    if (!n) continue;
    await shot(pr.slug, tpl(pr.name, pr.q, `The videos golfers recommend most, ranked by ${n.toLocaleString('en-US')} independent recommendations`));
  }
  await b.close(); console.log('og images written');
})();
