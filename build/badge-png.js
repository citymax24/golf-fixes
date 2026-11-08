// PNG versions of the award badges (2x, transparent). Run locally after build.py created new SVGs: node build/badge-png.js
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const dir = path.join(__dirname, '..', 'static', 'badge');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ deviceScaleFactor: 2 });
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.svg'))) {
    const out = path.join(dir, f.replace(/\.svg$/, '.png')); if (fs.existsSync(out)) continue;
    const svg = fs.readFileSync(path.join(dir, f), 'utf8'); const [, w, h] = svg.match(/width="(\d+)" height="(\d+)"/);
    await p.setViewportSize({ width: +w, height: +h });
    await p.setContent(`<style>*{margin:0}html,body{background:transparent}</style>${svg}`);
    await p.screenshot({ path: out, omitBackground: true });
  }
  await b.close(); console.log('badge PNGs written');
})();
