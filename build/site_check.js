#!/usr/bin/env node
/* Browser check of the built site (_site/), run before a merge to main. Needs Playwright (as build/og.js does);
   axe-core is optional (`npm i --no-save axe-core`, or point AXE_PATH at a node_modules folder that has it); without it the
   accessibility part is skipped and check.sh says so.

     node build/site_check.js                 # serves _site/ itself on a free port and checks it
     node build/site_check.js --url https://golfvotes.com/   # checks a running site instead (e.g. after a deploy)

   Everything runs at once in separate browser contexts, so a full run takes 10 to 20 seconds:
     sweep     every page in PAGES at five widths (phone to wide desktop, light and dark): HTTP status, script errors,
               console errors, Content-Security-Policy violations, sideways scrolling
     light     the ambient light: none at load, it shows around the finder's answer after a tap, it goes on Play,
               and no other page builds one (lesson cards hovered on watch, problem and browse pages)
     field     "Or pick it by name": lit on desktop hover and on a phone when the block crosses the middle of the screen
     a11y      axe WCAG 2 A/AA on the home page with the finder's light and with the topic field showing, plus a problem
               page and browse, light and dark
   Exit code 1 if anything fails; the summary lists each failure. */
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium, devices } = require('playwright');

const ROOT = path.join(__dirname, '..', '_site');
const PAGES = ['/', '/fix/slice/', '/fix/chipping/', '/watch/DFwz9o5QWzg/', '/coaches/', '/coach/athletic-motion-golf/', '/plans/',
  '/plan/chipping/', '/categories/', '/browse/', '/search/?q=slice', '/guides/best-golf-drills/', '/about/', '/privacy/',
  '/settings/', '/year/2025/', '/404.html'];
const WIDTHS = [[320, 'light', true], [390, 'dark', true], [768, 'light', false], [1280, 'dark', false], [1440, 'light', false]];
const NOISE = /goatcounter|gc\.zgo\.at|ERR_TUNNEL|ERR_CONNECTION|Failed to load resource|youtube-nocookie|GPU stall/i;  // the sandbox and CI have no access to these hosts
const fails = [], notes = [];
const fail = (part, what) => fails.push(`${part}: ${what}`);

function serve() {  // a tiny static server for _site/ (pretty URLs, 404 page), on a free port
  const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
    '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.xml': 'application/xml', '.txt': 'text/plain', '.ico': 'image/x-icon' };
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      let p; try { p = decodeURIComponent(req.url.split('?')[0]); } catch (e) { rsp.writeHead(400); return rsp.end(); }
      let f = path.join(ROOT, p);
      if (f !== ROOT && !f.startsWith(ROOT + path.sep)) { rsp.writeHead(403); return rsp.end(); }
      if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
      let code = 200;
      if (!fs.existsSync(f)) { f = path.join(ROOT, '404.html'); code = 404; }
      rsp.writeHead(code, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
      fs.createReadStream(f).on('error', () => rsp.end()).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}

async function watchPage(p, errs) {  // collect script errors, console errors and CSP violations of one page
  p.on('pageerror', e => errs.push('script: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' && !NOISE.test(m.text())) errs.push('console: ' + m.text().slice(0, 160)); });
  await p.addInitScript(() => document.addEventListener('securitypolicyviolation', e => console.error('CSP violation: ' + e.violatedDirective + ' ' + e.blockedURI)));
}

async function sweep(b, base) {
  await Promise.all(WIDTHS.map(async ([w, scheme, touch]) => {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, colorScheme: scheme, hasTouch: touch, isMobile: touch });
    for (const u of PAGES) {
      const p = await ctx.newPage(), errs = [];
      await watchPage(p, errs);
      const r = await p.goto(base + u.replace(/^\//, ''), { waitUntil: 'load' }).catch(e => ({ status: () => 0, err: e.message }));
      const over = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth).catch(() => 0);
      const st = r.status();
      if (!st || (st >= 400 && u !== '/404.html')) fail('sweep', `${u} at ${w}px: HTTP ${st}`);
      if (over > 0) fail('sweep', `${u} at ${w}px ${scheme}: scrolls sideways by ${over}px`);
      errs.forEach(e => fail('sweep', `${u} at ${w}px ${scheme}: ${e}`));
      await p.close();
    }
    await ctx.close();
  }));
  return `${PAGES.length * WIDTHS.length} loads`;
}

async function light(b, base) {
  const one = async (name, opts, tap) => {
    const ctx = await b.newContext(opts), p = await ctx.newPage(), errs = [];
    await watchPage(p, errs);
    await p.goto(base, { waitUntil: 'networkidle' });
    const n0 = await p.evaluate(() => document.querySelectorAll('.ambl').length);
    if (n0) fail('light', `${name}: ${n0} light(s) at page load, expected none`);
    const dot = await p.$('.bfd[data-k="slice"]'); if (!dot) { fail('light', `${name}: no finder dot`); return ctx.close(); }
    if (tap) await dot.tap(); else await dot.click();
    // ball flight, then the light waits for the answer to settle (and on phones for the scroll); a busy machine is slower
    const on = await p.waitForFunction(() => { const w = document.querySelector('.bfp:not([hidden]) .bfv'); return !!(w && w.querySelector('.ambl') && /amb-(up|rest)/.test(w.className)); }, null, { timeout: 7000 }).then(() => true, () => false);
    if (!on) fail('light', `${name}: no light around the finder's answer within 7 s of the tap`);
    const play = await p.$('.bfp:not([hidden]) .bfplay');
    if (!play) fail('light', `${name}: no play button (.bfplay) in the answer`);
    if (play) { await play.click(); await p.waitForTimeout(1000); const left = await p.evaluate(() => document.querySelectorAll('.bfp:not([hidden]) .ambl').length); if (left) fail('light', `${name}: the light is still there 1 s after Play`); }
    errs.forEach(e => fail('light', `${name}: ${e}`));
    await ctx.close();
  };
  await Promise.all([
    one('desktop light', { viewport: { width: 1280, height: 800 }, colorScheme: 'light' }, false),
    one('desktop dark', { viewport: { width: 1280, height: 800 }, colorScheme: 'dark' }, false),
    one('phone', { ...devices['iPhone 14'] }, true),
    (async () => {  // nothing else glows: lesson cards hovered on other pages
      const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } }), p = await ctx.newPage();
      for (const u of ['watch/DFwz9o5QWzg/', 'fix/slice/', 'browse/']) {
        await p.goto(base + u, { waitUntil: 'networkidle' });
        const cards = (await p.$$('.vc .thw')).slice(0, 3);
        if (!cards.length && u !== 'watch/DFwz9o5QWzg/') fail('light', `/${u}: no lesson cards found to hover, so nothing was tested`);
        for (const t of cards) await t.hover();
        await p.waitForTimeout(300);
        const n = await p.evaluate(() => document.querySelectorAll('.ambl').length);
        if (n) fail('light', `/${u}: ${n} light(s) built, expected none`);
      }
      await ctx.close();
    })()]);
  return 'finder light on desktop and phone, none elsewhere';
}

async function field(b, base) {
  const desk = async () => {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } }), p = await ctx.newPage();
    await p.goto(base, { waitUntil: 'networkidle' });
    await p.evaluate(() => window.scrollTo(0, document.querySelector('.pickb').getBoundingClientRect().top + scrollY - 100));
    const ix = (await p.$$('.ixs .ix'))[2]; const bb = await ix.boundingBox();
    await p.mouse.move(bb.x + 10, bb.y + bb.height / 2, { steps: 5 }); await p.waitForTimeout(800);
    if (!(await p.evaluate(() => document.querySelector('.pickb').classList.contains('lit')))) fail('field', 'desktop: not lit while the pointer is over a topic');
    await p.mouse.move(5, 795, { steps: 5 }); await p.waitForTimeout(400);
    if (await p.evaluate(() => document.querySelector('.pickb').classList.contains('lit'))) fail('field', 'desktop: still lit after the pointer left');
    await ctx.close();
  };
  const phone = async () => {
    const ctx = await b.newContext({ ...devices['iPhone 14'] }), p = await ctx.newPage();
    await p.goto(base, { waitUntil: 'networkidle' });
    const y = await p.evaluate(() => document.querySelector('.pickb').getBoundingClientRect().top + scrollY - 250);
    await p.evaluate(y => window.scrollTo(0, y), y);
    for (let i = 0; i < 15; i++) { await p.evaluate(() => window.scrollBy(0, 10)); await p.waitForTimeout(40); }
    await p.waitForTimeout(600);
    const st = await p.evaluate(() => [document.querySelector('.pickb').classList.contains('lit'), !!document.querySelector('.ix.act')]);
    if (!st[0] || !st[1]) fail('field', `phone: lit ${st[0]}, topic in the middle marked ${st[1]}, expected both`);
    await ctx.close();
  };
  await Promise.all([desk(), phone()]);
  return 'desktop hover and phone scroll';
}

async function a11y(b, base) {
  let src;
  try { src = fs.readFileSync(require.resolve('axe-core/axe.min.js', { paths: [process.cwd(), __dirname, ...(process.env.AXE_PATH ? [process.env.AXE_PATH] : [])] }), 'utf8'); }
  catch (e) { notes.push('a11y skipped: axe-core not installed (npm i --no-save axe-core)'); return 'skipped'; }
  const run = async (name, opts, prep, scope) => {
    const ctx = await b.newContext({ ...opts, bypassCSP: true }), p = await ctx.newPage();
    await p.goto(base + (prep.url || ''), { waitUntil: 'networkidle' });
    if (prep.fn) await prep.fn(p);
    await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => e.classList.add('in'))); await p.waitForTimeout(900);
    await p.addScriptTag({ content: src });
    const v = await p.evaluate(async sc => { const x = await axe.run(sc || document, { runOnly: ['wcag2a', 'wcag2aa'] }); return x.violations.flatMap(v => v.nodes.map(n => v.id + ' ' + n.target.join(' '))); }, scope || null);
    v.forEach(x => fail('a11y', `${name}: ${x}`));
    await ctx.close();
  };
  const until = (p, fn, what) => p.waitForFunction(fn, null, { timeout: 8000 }).catch(() => { throw new Error(what + ' did not show, so axe would check the wrong state'); });
  const tapSlice = touch => async p => { const d = await p.$('.bfd[data-k="slice"]'); if (touch) await d.tap(); else await d.click(); await until(p, () => !!document.querySelector('.bfp:not([hidden]) .bfv.amb-rest'), 'the finder light'); };
  const toField = async p => { const y = await p.evaluate(() => document.querySelector('.pickb').getBoundingClientRect().top + scrollY - 200); await p.evaluate(y => window.scrollTo(0, y), y); for (let i = 0; i < 20; i++) { await p.evaluate(() => window.scrollBy(0, 10)); await p.waitForTimeout(40); } await until(p, () => document.querySelector('.pickb').classList.contains('lit'), 'the topic field'); await p.waitForTimeout(1500); };
  const hoverField = async p => { await p.evaluate(() => window.scrollTo(0, document.querySelector('.pickb').getBoundingClientRect().top + scrollY - 120)); const ix = (await p.$$('.ixs .ix'))[3]; const bb = await ix.boundingBox(); await p.mouse.move(bb.x + 20, bb.y + bb.height / 2, { steps: 6 }); await until(p, () => document.querySelector('.pickb').classList.contains('lit'), 'the topic field'); await p.waitForTimeout(1500); };
  const D = s => ({ viewport: { width: 1280, height: 800 }, colorScheme: s }), P = s => ({ ...devices['iPhone 14'], colorScheme: s });
  const jobs = [];
  for (const s of ['light', 'dark']) {
    jobs.push(run(`home desktop ${s}, finder light`, D(s), { fn: tapSlice(false) }));
    jobs.push(run(`home phone ${s}, finder light`, P(s), { fn: tapSlice(true) }));
    jobs.push(run(`home phone ${s}, topic field`, P(s), { fn: toField }, { include: [['.pickb']] }));
    jobs.push(run(`home desktop ${s}, topic field`, D(s), { fn: hoverField }, { include: [['.pickb']], exclude: [['.ixs .ix:not(:hover)']] }));  // the other topics fade on purpose while one is hovered
  }
  jobs.push(run('/fix/slice/ desktop light', D('light'), { url: 'fix/slice/' }));
  jobs.push(run('/browse/ phone dark', P('dark'), { url: 'browse/' }));
  await Promise.all(jobs);
  return `${jobs.length} views`;
}

(async () => {
  const i = process.argv.indexOf('--url');
  let srv = null, base = i > 0 ? process.argv[i + 1] : null;
  if (!base) {
    if (!fs.existsSync(path.join(ROOT, 'index.html'))) { console.error('No _site/ build. Run build/build.py first.'); process.exit(2); }
    srv = await serve(); base = `http://127.0.0.1:${srv.address().port}/`;
  }
  if (!base.endsWith('/')) base += '/';
  const t0 = Date.now(), b = await chromium.launch();
  const parts = { sweep, light, field, a11y };
  const out = await Promise.all(Object.entries(parts).map(async ([k, f]) => {
    try { return `${k}: ${await f(b, base)}`; } catch (e) { fail(k, 'crashed: ' + e.message.split('\n')[0]); return `${k}: crashed`; }
  }));
  await b.close(); if (srv) srv.close();
  console.log(`site_check on ${base} in ${Math.round((Date.now() - t0) / 1000)} s`);
  out.forEach(l => console.log('  ' + l));
  notes.forEach(n => console.log('  note: ' + n));
  if (fails.length) { console.log(`\n${fails.length} problem(s):`); fails.forEach(f => console.log('  - ' + f)); process.exit(1); }
  console.log('\nAll checks passed.');
})();
