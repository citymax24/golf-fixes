// GolfVotes client. Everything personal stays in localStorage. No cookies, no tracking.
(function () {
  var B = document.body.dataset.base || "";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function load(k, d) { try { var v = localStorage.getItem("gv_" + k); return v ? JSON.parse(v) : (d === undefined ? [] : d); } catch (e) { return d === undefined ? [] : d; } }
  function save(k, v) { try { localStorage.setItem("gv_" + k, JSON.stringify(v)); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function has(k, vid) { return load(k).some(function (x) { return x.v === vid; }); }
  function toggle(k, item) {
    var l = load(k).filter(function (x) { return x.v !== item.v; }), on = !has(k, item.v);
    if (on) l.unshift(item);
    save(k, l);
    if (on && k === "liked") toggleOff("disliked", item.v);
    if (on && k === "disliked") toggleOff("liked", item.v);
    return on;
  }
  function toggleOff(k, vid) { save(k, load(k).filter(function (x) { return x.v !== vid; })); }
  var settings = load("settings", {});
  // touch screens: the chip row starts at "All"; bring the active chip into view once, without animation [fix-13]
  (function () { var o = $(".chips .chip.on"); if (!o || !window.matchMedia || !matchMedia("(pointer:coarse)").matches) return; var c = o.parentNode, r = o.getBoundingClientRect(), cr = c.getBoundingClientRect(); if (r.right > cr.right - 48 || r.left < cr.left) c.scrollLeft += r.left - cr.left - 48; })();
  var CK = '<svg class="ck" viewBox="0 0 74.91 72.75" aria-hidden="true"><path d="M0 38.56L24.84 72.75L37.84 72.75L74.91 0L54.94 0L29.81 49.31L22 38.56Z"/></svg>';
  var TYPES = { drill: "Drill", explainer: "Explainer", lesson: "Live lesson", pro_swing: "Pro swing", quick_tip: "Quick tip", practice_plan: "Practice plan", fitness: "Fitness" };

  // ---------- chrome ----------
  function closeMenu(focusBack) {
    if (!document.body.classList.contains("open")) return;
    document.body.classList.remove("open"); $("#menu").setAttribute("aria-expanded", "false"); $("#menu").setAttribute("aria-label", "Menu");
    if (focusBack) $("#menu").focus();
  }
  $("#menu").onclick = function () {
    if (window.innerWidth > 1000 && !document.body.classList.contains("wpage")) {
      document.body.classList.toggle("mini"); $("#menu").setAttribute("aria-expanded", String(!document.body.classList.contains("mini")));
    } else if (document.body.classList.contains("open")) closeMenu(true);
    else {
      document.body.classList.add("open"); $("#menu").setAttribute("aria-expanded", "true"); $("#menu").setAttribute("aria-label", "Close menu");
      var sd = $("#side"); sd.style.touchAction = sd.scrollHeight <= sd.clientHeight ? "none" : "";  // a menu that fits does not drag the page behind it
      var f = $("#side a"); if (f) setTimeout(function () { f.focus({ preventScroll: true }); }, 50);
    }
  };
  if (window.innerWidth > 1000 && !document.body.classList.contains("wpage")) $("#menu").setAttribute("aria-expanded", "true");
  $("#scrim").onclick = function () { closeMenu(true); };
  $("#theme").onclick = function () {
    var r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    r.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("gv_theme", r.dataset.theme); } catch (e) {}
    themeState();
  };
  function themeState() {
    var r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    $("#theme").setAttribute("aria-pressed", String(dark)); $("#theme").textContent = dark ? "Light mode" : "Dark mode";
  }
  themeState();
  document.addEventListener("error", function (ev) {
    var t = ev.target; if (t.tagName === "IMG" && /\/(mq2|hq2)\.jpg$/.test(t.src)) t.src = t.src.replace(/(mq2|hq2)\.jpg$/, "mqdefault.jpg");
    else if (t.tagName === "IMG" && window.thumbFail && /\/thumbs\/(mq2|hq2)\//.test(t.src) && t.closest(".vc")) window.thumbFail(t);  // no inline handler: the content policy forbids them
  }, true);

  // ---------- ambient light ----------
  // Like a TV lighting the wall: each edge of a lesson's picture throws its own colour outward, strongest from the middle of
  // the edge, fading toward the corners. The colours come from a 32x18 copy of the picture already on the page; colourful
  // pixels count most, grey and black throw little or no light, and muddy tones are freshened. Only the part of the picture that
  // shows counts (the large previews carry black bars that the page crops away).
  var ambCv;
  function hsl2rgb(h, s, l) {
    var f = function (n) { var k = (n + h / 30) % 12, a = s * Math.min(l, 1 - l); return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))); };
    return f(0) + "," + f(8) + "," + f(4);
  }
  function ambCol(d, x0, x1, y0, y1) {  // one patch -> [clean colour, strength 0..1]
    var r = 0, g = 0, b = 0, w = 0, lum = 0, n = 0;
    for (var y = y0; y < y1; y++) for (var x = x0; x < x1; x++) {
      var i = (y * 32 + x) * 4, R = d[i], G = d[i + 1], Bl = d[i + 2], mx = Math.max(R, G, Bl), mn = Math.min(R, G, Bl), c = (mx - mn) / 255, k = c * c + .015;
      r += R * k; g += G * k; b += Bl * k; w += k; lum += (mx + mn) / 510; n++;
    }
    r /= w * 255; g /= w * 255; b /= w * 255; lum /= n;
    var mx2 = Math.max(r, g, b), mn2 = Math.min(r, g, b), l = (mx2 + mn2) / 2, dd = mx2 - mn2, s = dd ? dd / (1 - Math.abs(2 * l - 1)) : 0, h = 0;
    if (dd) h = mx2 === r ? 60 * (((g - b) / dd) % 6) : mx2 === g ? 60 * ((b - r) / dd + 2) : 60 * ((r - g) / dd + 4);
    if (h < 0) h += 360;
    var lit = Math.min(1, lum / .2);  // black throws no light
    if (s < .14) return ["255,255,255", Math.max(0, (lum - .45) / .45) * .6 * lit];  // grey or white: soft white light (on a white page it simply disappears)
    if (h >= 12 && h <= 52 && s < .6) return [hsl2rgb(h, .35, .82), (.45 + .3 * Math.min(1, s * 2)) * lit];  // skin, sand, tan: a warm white, since dim orange reads as brown
    if (h > 52 && h < 110) h += (135 - h) * .6;  // olive, khaki and lime grass turns fresh green
    var vivid = s >= .25, L2 = vivid ? .5 + .12 * Math.min(1, Math.max(0, (l - .25) * 2)) : .74;  // faint colour becomes a tinted white light
    if (h < 70 || h > 330) L2 += .08;  // warm light kept light: dim orange would read as brown
    return [hsl2rgb(h, vivid ? Math.min(.78, Math.max(.55, s * 1.3 + .15)) : .4, L2), (.55 + .45 * Math.min(1, s * 2)) * lit];
  }
  var ambAll = [], ambY = window.scrollY, ambV = 0, ambRM = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)"), ambStill = !!(ambRM && ambRM.matches);
  var gray = function (r, g, b) { var mx = Math.max(r, g, b); return mx - Math.min(r, g, b) < mx * .1; };
  // the ten pools: edge (0 top, 1 bottom, 2 left, 3 right), place along the edge, size along it (%), strength, quickness, scroll lag
  var POOLS = [[0, .2, 62, .8, .06, .55], [0, .5, 78, 1, .09, .8], [0, .8, 62, .8, .075, 1],
    [1, .2, 62, .8, .07, .95], [1, .5, 78, 1, .1, .7], [1, .8, 62, .8, .055, .5],
    [2, .3, 72, .85, .08, .9], [2, .7, 72, .85, .065, .6], [3, .3, 72, .85, .06, .65], [3, .7, 72, .85, .085, 1]];
  // Build the light for a loaded picture (nothing is drawn until a class asks for it). Returns its state, or null for a picture with no colour to give.
  function ambBuild(w, fly) {
    var im = w && w.querySelector("img"); if (!im || !im.complete || !im.naturalWidth) return null;
      var d;
      try { ambCv = ambCv || document.createElement("canvas"); ambCv.width = 32; ambCv.height = 18; var cx = ambCv.getContext("2d", { willReadFrequently: true }); var nw = im.naturalWidth, nh = im.naturalHeight, ar = (im.clientWidth / im.clientHeight) || 16 / 9, sw = Math.min(nw, nh * ar), sh = Math.min(nh, nw / ar); var sx0 = (nw - sw) / 2, sy0 = (nh - sh) / 2; cx.drawImage(im, sx0, sy0, sw, sh, 0, 0, 32, 18); d = cx.getImageData(0, 0, 32, 18).data;
        // black bars inside the picture (old 4:3 lessons, phone videos) throw no light: read the colours from the picture between them
        var lumAt = function (x, y) { var i = (y * 32 + x) * 4; return (d[i] + d[i + 1] + d[i + 2]) / 765; }, colL = function (x) { var t = 0; for (var y = 0; y < 18; y++) t += lumAt(x, y); return t / 18; }, rowL = function (y) { var t = 0; for (var x = 0; x < 32; x++) t += lumAt(x, y); return t / 32; };
        var bl = 0, br = 31, bt = 0, bb = 17;
        while (bl < 8 && colL(bl) < .06) bl++; while (br > 23 && colL(br) < .06) br--; while (bt < 4 && rowL(bt) < .06) bt++; while (bb > 13 && rowL(bb) < .06) bb--;
        if (bl || br < 31 || bt || bb < 17) { cx.drawImage(im, sx0 + sw * bl / 32, sy0 + sh * bt / 18, sw * (br - bl + 1) / 32, sh * (bb - bt + 1) / 18, 0, 0, 32, 18); d = cx.getImageData(0, 0, 32, 18).data; }
      } catch (e) { return null; }
      var patch = function (e, u) {  // the part of the picture behind each pool
        return e < 2 ? (u < .4 ? [0, 12] : u > .6 ? [20, 32] : [10, 22]).concat(e ? [13, 18] : [0, 5]) : (e === 2 ? [0, 6] : [26, 32]).concat(u < .5 ? [2, 10] : [8, 16]);
      };
      // each pool's colour, then blended with its neighbours round the picture, so the light flows instead of breaking into spots
      var C = POOLS.map(function (q) { var pt = patch(q[0], q[1]), c = ambCol(d, pt[0], pt[1], pt[2], pt[3]); return c[0].split(",").map(Number).concat(c[1] * q[3]); });
      var RING = [0, 1, 2, 8, 9, 5, 4, 3, 7, 6];  // the pools in order round the picture: top left to right, right side down, bottom right to left, left side up
      var M = C.map(function (c, i) {
        var at = RING.indexOf(i), nb = [[i, .5], [RING[(at + 9) % 10], .25], [RING[(at + 1) % 10], .25]], r = 0, g = 0, bl = 0, wsum = 0, st = 0;
        nb.forEach(function (n) { var o = C[n[0]], k = n[1] * o[3]; r += o[0] * k; g += o[1] * k; bl += o[2] * k; wsum += k; st += k; });
        return wsum ? [Math.round(r / wsum), Math.round(g / wsum), Math.round(bl / wsum), st] : [255, 255, 255, 0];
      });
      var box = document.createElement("span"); box.className = "ambl"; box.setAttribute("aria-hidden", "true");
      var P = [], tot = 0, wr = 0, wg = 0, wb = 0;
      M.forEach(function (m) { tot += m[3]; wr += m[0] * m[3]; wg += m[1] * m[3]; wb += m[2] * m[3]; });
      if (tot > .2) {  // under the pools, one even wash of the picture's main colour all round, so there are no gaps
        var wash = document.createElement("i"); wash.className = "ambw";
        wash.style.boxShadow = "0 0 calc(var(--amby)*1.2) calc(var(--amby)*.12 + 32px) rgba(" + Math.round(wr / tot) + "," + Math.round(wg / tot) + "," + Math.round(wb / tot) + "," + Math.min(.6, .2 + tot / 10 * .5).toFixed(2) + ")";
        if (gray(wr / tot, wg / tot, wb / tot)) wash.classList.add("ambg");  // a grey or white wash only reads as haze on dark: the dark theme hides it
        box.appendChild(wash);
        wash.style.transition = "transform 1.1s cubic-bezier(.2,.8,.3,1),opacity 1.2s ease";
        if (!ambStill) { wash.style.animationName = "ambdw"; wash.style.animationDuration = "20s"; wash.style.animationDelay = "-5.1s"; }
        P.push({ el: wash, e: 4, u: .5, lag: .6 });
      }
      POOLS.forEach(function (q, qi) {
        var e = q[0], u = q[1], z = q[2], m = M[qi], a = m[3];
        if (a < .05) return;
        var g = function (f) { return "rgba(" + m[0] + "," + m[1] + "," + m[2] + "," + (a * f).toFixed(3) + ")"; };
        var el = document.createElement("i"), T = "var(--ambt,var(--amby))";
        el.style.cssText = (e < 2 ? "left:calc(" + (u * 100 - z / 2) + "%);width:" + z + "%;" + (e ? "bottom:calc(var(--amby)*-1);height:calc(var(--amby)*2)" : "top:calc(" + T + "*-1);height:calc(" + T + "*2)")
          : "top:calc(" + (u * 100 - z / 2) + "%);height:" + z + "%;width:calc(var(--ambx)*2);" + (e === 2 ? "left" : "right") + ":calc(var(--ambx)*-1)")
          + ";background:radial-gradient(closest-side," + g(1) + "," + g(.82) + " 18%," + g(.55) + " 38%," + g(.3) + " 56%," + g(.12) + " 74%," + g(.03) + " 90%,rgba(" + m[0] + "," + m[1] + "," + m[2] + ",0))";
        if (gray(m[0], m[1], m[2])) el.classList.add("ambg");
        box.appendChild(el);
        var dur = (.045 / q[4]).toFixed(2);  // softer pools take longer to arrive, so the pools part and meet again: the light changes shape
        el.style.transition = "transform " + dur + "s cubic-bezier(.22,1.25,.36,1),opacity " + (dur * 1.3).toFixed(2) + "s ease";
        var loop = [14.6, 18.4, 16.3, 20.6, 13.4, 17.2, 21.4, 15.1, 19.3, 14][qi];  // its own slow drift, so no two pools keep step
        if (!ambStill) { el.style.animationName = "ambd" + (qi % 3 + 1); el.style.animationDuration = loop + "s"; el.style.animationDelay = (-loop * ((qi * .37) % 1)).toFixed(1) + "s"; }  // only name, length, start: pausing stays with the style sheet
        P.push({ el: el, e: e, u: u, lag: q[5] });
      });
      if (w._onpal) {  // the picture's light in three colours: its main colour and its two strongest edges
        var strong = M.map(function (m, i) { return [m[3], i]; }).sort(function (x, y) { return y[0] - x[0]; });
        w._onpal(tot > .2 ? [[Math.round(wr / tot), Math.round(wg / tot), Math.round(wb / tot)], M[strong[0][1]], M[strong[1][1]]] : null, M, POOLS);  // and all ten pools with their places
      }
      if (!P.length) return null;
      var old = w.querySelector(".ambl");
      if (old) { old.classList.add("ambo"); setTimeout(function () { old.remove(); }, 500); }  // the old light fades out as the new one comes in
      w.insertBefore(box, w.firstChild);
      var A = w._amb;
      if (A && fly) { A.P = P; A.box = box; requestAnimationFrame(function () { box.classList.add("in"); ambGo(); }); return A; }
      A = w._amb = { w: w, P: P, box: box, vis: true, mx: 0, my: 0, on: 0, ax: 20, fly: !!fly, vx: 0, vy: 0, tr: window.innerWidth < 760 ? 6 : 12 };
      if (fly) { if (!ambStill) ambAll.push(A); requestAnimationFrame(function () { box.classList.add("in"); ambGo(); }); }
      return A;
  }
  function amb(w, fly) { return ambBuild(w, fly); }  // the floating topic preview calls this on every new picture

  // ----- When the light shows. It means "this is your answer": only around the #1 lesson the finder reveals after the golfer's tap.
  // The first answer of a visit blooms (sessionStorage, per tab), later answers just glow quietly. It waits until the ball has
  // landed and the answer has settled, and it goes when Play is pressed, another miss is picked, the picture is scrolled away,
  // or after about 25 seconds. Nothing exists before that moment or after it.
  var ambLive = null, ambCueT = 0, ambOnce = false;
  function ambUsed() { if (ambOnce) return true; try { return sessionStorage.getItem("gv_amb") === "1"; } catch (e) { return false; } }
  function ambSpend() { ambOnce = true; try { sessionStorage.setItem("gv_amb", "1"); } catch (e) {} }
  function ambCue(p) {
    clearTimeout(ambCueT); ambOff(ambLive, "cut");
    var w = p && $(".bfv", p), im = w && w.querySelector("img"); if (!im) return;
    var t0 = performance.now(), wait = window.innerWidth < 760 ? 1300 : 700;  // phones first scroll the answer up
    var tryStart = function () {
      if (!p.isConnected || p.hidden || !w.querySelector("img")) return;
      var r = w.getBoundingClientRect(), seen = r.height ? Math.max(0, Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 56)) / r.height : 0;
      if (im.complete && im.naturalWidth && seen >= .6) { var A = ambBuild(w); if (A) ambStart(A, !ambUsed()); return; }
      if (performance.now() - t0 < wait + 3000) ambCueT = setTimeout(tryStart, 200);  // not ready in time: this answer gets no light
    };
    ambCueT = setTimeout(tryStart, wait);
  }
  function ambStart(A, bloom) {
    var w = A.w; if (bloom) ambSpend();
    ambLive = A; A.off = 0; void A.box.offsetWidth;  // commit the start state, so the entrance transitions
    w.classList.remove("amb-off"); w.classList.add(bloom && !ambStill ? "amb-up" : "amb-rest");
    if (bloom && !ambStill) A.t1 = setTimeout(function () { w.classList.remove("amb-up"); w.classList.add("amb-rest"); }, 1400);
    if (window.IntersectionObserver) { A.io = new IntersectionObserver(function (es) { var e = es[es.length - 1]; A.vis = e.isIntersecting; if (e.intersectionRatio < .3) ambOff(A, "away"); }, { threshold: [0, .3] }); A.io.observe(w); }
    var left = 23800, since = performance.now();
    var cap = function () { if (A.hover) { A.late = 1; return; } ambOff(A, "out"); };  // about 20 s of rest, then a slow dusk
    A.t2 = setTimeout(cap, left);
    A.vz = function () { if (document.hidden) { clearTimeout(A.t2); left -= performance.now() - since; } else { since = performance.now(); A.t2 = setTimeout(cap, Math.max(0, left)); } };  // the clock waits while the tab is hidden
    document.addEventListener("visibilitychange", A.vz);
    A.pm = function (ev) { if (ev.pointerType !== "mouse") return; var r = A.r || (A.r = w.getBoundingClientRect()); A.mx = Math.max(-1, Math.min(1, (ev.clientX - r.left) / r.width * 2 - 1)); A.my = Math.max(-1, Math.min(1, (ev.clientY - r.top) / r.height * 2 - 1)); A.on = 1; A.hover = 1; ambGo(); };
    A.pl = function () { A.on = 0; A.hover = 0; ambGo(); if (A.late) A.t2 = setTimeout(function () { ambOff(A, "out"); }, 2000); };
    w.addEventListener("pointermove", A.pm, { passive: true }); w.addEventListener("pointerleave", A.pl, { passive: true });
    A.ax = parseFloat(getComputedStyle(w).getPropertyValue("--ambx")) || 20; A.tr = window.innerWidth < 760 ? 6 : 12;
    if (!ambStill && ambAll.indexOf(A) < 0) ambAll.push(A);
    ambGo();
  }
  function ambOff(A, kind) {
    if (!A || A.off) return; A.off = 1;
    var w = A.w, ms = ambStill ? 600 : { cut: 200, away: 800, out: 4000, play: 600 }[kind] || 600;
    clearTimeout(A.t1); clearTimeout(A.t2);
    w.style.setProperty("--amout", ms + "ms"); w.style.setProperty("--amease", kind === "out" ? "cubic-bezier(.45,0,.55,1)" : "cubic-bezier(.4,0,1,1)");
    w.classList.remove("amb-up", "amb-rest"); w.classList.add("amb-off");
    if (A.io) A.io.disconnect(); document.removeEventListener("visibilitychange", A.vz);
    w.removeEventListener("pointermove", A.pm); w.removeEventListener("pointerleave", A.pl);
    if (ambLive === A) ambLive = null;
    setTimeout(function () {
      var i = ambAll.indexOf(A); if (i >= 0) ambAll.splice(i, 1);
      if (A.box) A.box.remove(); w.classList.remove("amb-off"); w.style.removeProperty("--amout"); w.style.removeProperty("--amease");
      if (w._amb === A) w._amb = null;
    }, ms + 50);
  }
  function ambStop(kind) { clearTimeout(ambCueT); ambOff(ambLive, kind); }

  // ----- How the light moves while it shows. The motion runs on the graphics card as CSS transitions and the slow keyframe drift;
  // this only sets new goals, about twelve times a second at most, and only while something moves.
  var ambTm = 0, ambLast = 0, ambEnd = 0;
  function ambGo() {
    if (ambTm || !ambAll.length || ambStill) return;
    ambTm = setTimeout(function () { ambTm = 0; requestAnimationFrame(ambTick); }, Math.max(0, 80 - (performance.now() - ambLast)));
  }
  function ambTick() {  // read every position first, then write only transforms and opacities, and only where they changed
    var now = performance.now(), y = window.scrollY, vh = window.innerHeight, dt = Math.max(16, now - ambLast);
    ambV = ambV * .35 + Math.max(-40, Math.min(40, (y - ambY) / dt * 16)) * .65; ambY = y; ambLast = now;  // scroll speed in px per frame
    if (Math.abs(ambV) < .3) ambV = 0; else ambGo();  // keep easing back until the page is still
    ambAll.forEach(function (a) { if (a.fly && a.vis && Math.abs(a.vx) + Math.abs(a.vy) > .3) ambGo(); });
    ambAll = ambAll.filter(function (a) { return a.w.isConnected; });  // forget lights whose picture has left the page
    var on = ambAll.filter(function (a) { return a.vis && !a.off; });
    var R = on.map(function (a) { return a.w.getBoundingClientRect(); });
    var cl = function (x, lo, hi) { return Math.max(lo, Math.min(hi, x)); };
    on.forEach(function (a, i) {
      var r = a.r = R[i]; if (!r.width) return;
      var p = a.fly ? 0 : cl((r.top + r.height / 2 - vh / 2) / vh, -.6, .6);  // below the middle of the screen: the light leans up, above it: down
      var gx = a.fly ? -a.vx : 0, gy = a.fly ? -a.vy : ambV;  // where the light is pushed: down by scrolling, behind a preview that flies with the pointer
      var kf = a.fly ? .03 : .015, kc = a.fly ? .5 : .25, kt = a.fly ? 1.1 : .55, tc = a.fly ? 24 : a.tr;  // the finder's light moves at half the amplitude, so it stays off the text
      var sv = cl(gy * kf, -kc, kc), sx = cl(gx * kf, -kc, kc);  // how hard
      a.P.forEach(function (b) {
        var e = b.e, ux = b.u * 2 - 1, side = e < 2, along = side ? a.mx : a.my, len = side ? r.width : r.height;
        var toward = e === 0 ? -a.my : e === 1 ? a.my : e === 2 ? -a.mx : a.mx;  // 1: the mouse is at this edge, -1: at the opposite one
        var prox = a.on * Math.exp(-(along - ux) * (along - ux) / .5) * (.55 + .45 * toward);
        var lean = e === 0 ? p : e === 1 ? -p : 0, trail = cl(gy * b.lag * kt, -tc, tc), trailX = cl(gx * b.lag * kt, -tc, tc);
        var pullX = e === 3 ? Math.max(0, sx) : e === 2 ? Math.max(0, -sx) : 0;
        var pull = e === 1 ? Math.max(0, sv) : Math.max(0, -sv);  // the trailing side stretches
        var slide = cl(a.on * (along - ux) * .2 * len, -(side ? a.ax * .7 : 60), side ? a.ax * .7 : 60);
        var T = e === 4 ? [cl(a.on * a.mx * 6 + trailX * .4, -8, 8), cl(a.on * a.my * 5 + trail * .4, -8, 8), 1 + .02 * a.on + .01 * Math.abs(sv), 1 + .02 * a.on + .03 * Math.abs(sv), 0, .7 + .2 * a.on + .1 * Math.abs(sv)] : side
          ? [slide + trailX, trail, 1 + .2 * prox - .12 * Math.abs(sv) + .25 * Math.abs(sx), 1 + .6 * prox + .3 * Math.max(0, lean) + .9 * pull - .2 * Math.abs(sv), (along - ux) * prox * 9 * (e ? -1 : 1) + (b.u - .5) * sv * 16, .55 + .35 * prox + .25 * lean - .12 * a.on * Math.max(0, -toward)]
          : [trailX, slide + trail, 1 + .6 * prox + .9 * pullX - .2 * Math.abs(sx), 1 + .2 * prox + .7 * Math.abs(sv), (b.u - .5) * sv * 14 * (e === 2 ? 1 : -1), .55 + .35 * prox - .12 * a.on * Math.max(0, -toward)];
        var tf = "translate3d(" + T[0].toFixed(1) + "px," + T[1].toFixed(1) + "px,0) rotate(" + T[4].toFixed(1) + "deg) scale(" + T[2].toFixed(3) + "," + T[3].toFixed(3) + ")", op = cl(T[5], .2, 1).toFixed(2);
        if (tf !== b.tf) { b.el.style.transform = b.tf = tf; }
        if (op !== b.op) { b.el.style.opacity = b.op = op; }
      });
    });
  }
  window.addEventListener("scroll", function () { ambGo(); clearTimeout(ambEnd); ambEnd = setTimeout(ambGo, 140); }, { passive: true });  // and once more when scrolling stops
  window.addEventListener("resize", function () { ambAll.forEach(function (a) { a.r = null; a.ax = parseFloat(getComputedStyle(a.w).getPropertyValue("--ambx")) || 20; }); }, { passive: true });
  if (ambRM) {  // "Reduce motion" switched on while the page is open: the light keeps its glow but stops moving
    var ambRMc = function () { ambStill = ambRM.matches; if (ambStill) ambAll.forEach(function (a) { a.P.forEach(function (b) { b.el.style.animationName = ""; b.el.style.transform = ""; b.tf = ""; }); }); };
    if (ambRM.addEventListener) ambRM.addEventListener("change", ambRMc); else if (ambRM.addListener) ambRM.addListener(ambRMc);
  }

  // ---------- player ----------
  function play() {
    var b = $("button.player[data-vid]"); if (!b) { var fb = $(".bfp:not([hidden]) .bfplay"); if (fb) fb.click(); return; }
    var f = document.createElement("iframe");
    f.className = "player";
    f.src = "https://www.youtube-nocookie.com/embed/" + b.dataset.vid + "?autoplay=1&rel=0&modestbranding=1";
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen"; f.allowFullscreen = true;
    f.referrerPolicy = "strict-origin-when-cross-origin";
    var h1 = $("h1"); f.title = "Video: " + (h1 ? h1.textContent : "YouTube");
    b.replaceWith(f); f.setAttribute("tabindex", "0"); f.focus();
  }
  document.addEventListener("click", function (ev) {
    if (ev.target.closest("button.player[data-vid]")) { play(); return; }
    var lb = ev.target.closest(".lb");
    if (lb) {
      ev.preventDefault();
      var art = lb.closest("[data-vid]"), vid = art.dataset.vid;
      var on = toggle("later", { v: vid });
      lb.classList.toggle("on", on); lb.setAttribute("aria-pressed", String(on)); flash(on ? "Saved to Watch later" : "Removed from Watch later");
    }
  });
  function markLater() { $$(".thw").forEach(function (w) { var b = $(".lb", w); if (b) { var on = has("later", w.dataset.vid); b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); } }); }
  markLater();
  function flash(t) {
    var d = $("#toast") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "toast" }));
    d.setAttribute("role", "status"); d.setAttribute("aria-live", "polite");
    d.textContent = t; d.className = "show"; clearTimeout(d._t); d._t = setTimeout(function () { d.className = ""; }, 1600);
  }

  // ---------- watch page ----------
  var acts = $(".acts");
  if (acts) {
    var item = { v: acts.dataset.vid, t: acts.dataset.t, c: acts.dataset.c };
    var h = load("history").filter(function (x) { return x.v !== item.v; }); h.unshift(item); save("history", h.slice(0, 300));
    var sync = function () { $$("[data-act]", acts).forEach(function (b) { var on = has(b.dataset.act, item.v); b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); }); };
    $$("[data-act]", acts).forEach(function (b) {
      b.onclick = function () { var on = toggle(b.dataset.act, item); sync(); flash(on ? ({ liked: "Liked", disliked: "We'll show you less like this", later: "Saved to Watch later" })[b.dataset.act] : "Removed"); };
    });
    sync();
  }

  // ---------- keyboard ----------
  var keys = [["/", "Search"], ["h", "Home"], ["k", "Play (on a video page)"], ["l", "Like (on a video page)"], ["w", "Watch later (on a video page)"], ["?", "Show these shortcuts"], ["Esc", "Close / leave the search box"]];
  document.addEventListener("keydown", function (ev) {
    var tag = (ev.target.tagName || "").toLowerCase();
    if (ev.key === "Escape") { var m = $("#keys"); if (m) m.remove(); closeMenu(true); if (tag === "input") ev.target.blur(); return; }
    if (tag === "input" || tag === "textarea" || tag === "select" || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.key === "/") { ev.preventDefault(); openSearch(); }
    else if (settings.keys === false && /^[hklw]$/.test(ev.key)) return;
    else if (ev.key === "h") location.href = B + "/";
    else if (ev.key === "k") play();
    else if (ev.key === "l" && acts) $("[data-act=liked]", acts).click();
    else if (ev.key === "w" && acts) $("[data-act=later]", acts).click();
    else if (ev.key === "?") {
      if ($("#keys")) return $("#keys").remove();
      var d = document.createElement("div"); d.id = "keys";
      d.innerHTML = "<div><h2>Keyboard shortcuts</h2>" + keys.map(function (k) { return "<p><kbd>" + k[0] + "</kbd> " + k[1] + "</p>"; }).join("") + "</div>";
      d.onclick = function () { d.remove(); }; document.body.appendChild(d);
    }
  });

  // ---------- data page ----------
  var cp = $("#copyprompt");
  if (cp) cp.onclick = function () { navigator.clipboard.writeText($("#prompt").textContent).then(function () { flash("Prompt copied"); }); };

  // ---------- settings page ----------
  if ($("#s-hidedis")) {
    $("#s-hidedis").checked = settings.hidedis !== false;
    $("#s-hidedis").onchange = function () { settings.hidedis = this.checked; save("settings", settings); flash("Saved"); };
    $("#s-keys").checked = settings.keys !== false;
    $("#s-keys").onchange = function () { settings.keys = this.checked; save("settings", settings); flash("Saved"); };
    $("#s-clear-h").onclick = function () { save("history", []); flash("Watch history cleared"); };
    $("#s-clear-all").onclick = function () { ["history", "liked", "disliked", "later", "settings", "plans"].forEach(function (k) { save(k, k === "settings" || k === "plans" ? {} : []); }); flash("Everything reset"); };
  }

  // ---------- header: mobile search, hairline ----------
  function openSearch() { document.body.classList.add("searching"); $("#stoggle").setAttribute("aria-expanded", "true"); $("#q").focus(); }
  function closeSearch() { document.body.classList.remove("searching"); $("#stoggle").setAttribute("aria-expanded", "false"); }
  $("#stoggle").onclick = function () { document.body.classList.contains("searching") ? closeSearch() : openSearch(); };
  $("#q").addEventListener("keydown", function (ev) { if (ev.key === "Escape") { closeSearch(); $("#stoggle").focus(); } });
  var topbar = $("#top"), onScroll = function () { topbar.classList.toggle("scrolled", window.scrollY > 0); };
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  // ---------- top nav: Saved link when something is saved ----------
  if (load("liked").length || load("later").length) { var ts = $("#tsaved"); if (ts) ts.hidden = false; }

  // ---------- search suggestions ----------
  (function () {
    var q = $("#q"), box = $("#sugg"), ix = null, items = [], sel = -1, cur = "";
    // the part of a title that matched, set in heavier type
    function hl(t) {
      var low = t.toLowerCase(), i = low.indexOf(cur); while (i > 0 && /[a-z0-9]/.test(low.charAt(i - 1))) i = low.indexOf(cur, i + 1);
      return i < 0 || !cur ? esc(t) : esc(t.slice(0, i)) + "<mark>" + esc(t.slice(i, i + cur.length)) + "</mark>" + esc(t.slice(i + cur.length));
    }
    var SYN = { slicing: "slice", sliced: "slice", shank: "shanks", shanking: "shanks", hooking: "hook", chunk: "fat", chunking: "fat", topped: "topping",
      chip: "chipping", putt: "putting", drive: "driver", irons: "iron", sand: "bunker", ott: "over the top", ee: "early extension" };
    function get(cb) { if (ix) return cb(ix); fetch(B + "/static/index.json").then(function (r) { return r.json(); }).then(function (d) { ix = d; cb(d); }); }
    function close() { box.hidden = true; q.setAttribute("aria-expanded", "false"); sel = -1; }
    function render() {
      box.innerHTML = items.map(function (it, i) { return '<li role="presentation"' + (i === sel ? ' class="on"' : "") + '><a role="option" id="sg' + i + '" aria-selected="' + (i === sel) + '" tabindex="-1" href="' + it.h + '"><span class="sgt"><b>' + hl(it.t) + "</b><span>" + esc(it.s) + "</span></span>" + (it.i ? '<img src="' + B + "/static/thumbs/mq2/" + it.i + '.webp" alt="" width="64" height="36">' : "") + "</a></li>"; }).join("");
      box.hidden = !items.length; q.setAttribute("aria-expanded", String(!!items.length));
      if (sel >= 0) q.setAttribute("aria-activedescendant", "sg" + sel); else q.removeAttribute("aria-activedescendant");
    }
    q.addEventListener("input", function () {
      var v = q.value.trim().toLowerCase(); if (v.length < 2) { items = []; return render(); }
      v = SYN[v] || v; cur = v;
      get(function (d) {
        var m = function (s) { return s.toLowerCase().split(/[^a-z0-9]+/).some(function (w) { return w.indexOf(v) === 0; }) || s.toLowerCase().indexOf(v) === 0; };
        var ps = d.p.filter(function (p) { return m(p[1]) || m(p[2]); }).slice(0, 4).map(function (p) { return { h: B + "/fix/" + p[0] + "/", t: p[1], s: "Problem · " + p[3].toLocaleString() + " recommendations" }; });
        var cs = d.c.filter(function (c) { return m(c[1]); }).slice(0, 2).map(function (c) { return { h: B + "/coach/" + c[0] + "/", t: c[1], s: "Coach · " + c[2].toLocaleString() + " recommendations" }; });
        var vs = d.v.filter(function (x) { return m(x[1]); }).slice(0, 3).map(function (x) { return { h: B + "/watch/" + x[0] + "/", t: x[1], s: x[2] + " · " + x[4] + " golfers recommend", i: x[0] }; });
        items = ps.concat(cs, vs).slice(0, 7); sel = -1; render();
      });
    });
    q.addEventListener("keydown", function (ev) {
      if (box.hidden) return;
      if (ev.key === "ArrowDown") { ev.preventDefault(); sel = Math.min(items.length - 1, sel + 1); render(); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); sel = Math.max(-1, sel - 1); render(); }
      else if (ev.key === "Enter" && sel >= 0) { ev.preventDefault(); location.href = items[sel].h; }
      else if (ev.key === "Escape") close();
    });
    q.addEventListener("blur", function () { setTimeout(close, 150); });
  })();

  // ---------- "Did this fix it?" votes (counted as GoatCounter events, no cookies) ----------
  var vote = $(".vote");
  if (vote) {
    var vid = vote.dataset.vid, votes = load("votes", {});
    var done = function (v) { $$("[data-vote]", vote).forEach(function (b) { b.disabled = true; b.classList.toggle("on", b.dataset.vote === v); b.setAttribute("aria-pressed", String(b.dataset.vote === v)); }); $(".vthanks", vote).hidden = false; };
    if (votes[vid]) done(votes[vid]);
    $$("[data-vote]", vote).forEach(function (b) {
      b.onclick = function () {
        var v = b.dataset.vote; votes[vid] = v; save("votes", votes); done(v);
        try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "vote-" + v + "/" + vid, title: (v === "yes" ? "Fixed it: " : "Did not help: ") + vote.dataset.t, event: true }); } catch (e) {}
      };
    });
  }

  // ---------- ball-flight finder ----------
  var bff = $("#bf");
  if (bff) {
    var lh = $("#bflh");
    if (load("lefty", false) === true) { lh.checked = true; bff.classList.add("lh"); }
    lh.onchange = function () { bff.classList.toggle("lh", lh.checked); save("lefty", lh.checked); };
    bff.addEventListener("click", function (ev) {
      var pb = ev.target.closest(".bfplay"); if (!pb) return;
      ambStop("play");  // the video takes over: the light draws back into the picture
      var f = document.createElement("iframe");
      f.className = "bfvid"; f._btn = pb;
      f.src = "https://www.youtube-nocookie.com/embed/" + pb.dataset.vid + "?autoplay=1&playsinline=1&rel=0&modestbranding=1";
      f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen"; f.allowFullscreen = true;
      f.referrerPolicy = "strict-origin-when-cross-origin"; f.title = "Video: " + pb.dataset.t;
      var hi = { v: pb.dataset.vid, t: pb.dataset.t, c: pb.dataset.c || "" };
      var hh = load("history").filter(function (x) { return x.v !== hi.v; }); hh.unshift(hi); save("history", hh.slice(0, 300));
      pb.replaceWith(f); f.setAttribute("tabindex", "0"); f.focus();
    });
    bff.addEventListener("keydown", function (ev) { if (ev.key === " " && ev.target.classList.contains("bfd")) { ev.preventDefault(); ev.target.click(); } });
    bff.addEventListener("click", function (ev) {  // "Change": back to the hole, which still shows the flight drawn
      var ch = ev.target.closest(".fm a"); if (!ch) return; ev.preventDefault();
      var q = $(".bfq", bff); window.scrollTo({ top: q.getBoundingClientRect().top + window.scrollY - 68, behavior: still ? "auto" : "smooth" });
    });
    $$(".bfd", bff).forEach(function (a) {
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        var k = a.dataset.k;
        if (a.classList.contains("on")) return;
        bff.classList.add("used");
        ambStop("cut");  // another miss: the old light goes at once
        var nim = $("#bf-" + k + " .bfv img", bff); if (nim) { nim.loading = "eager"; if (nim.decode) nim.decode().catch(function () {}); }  // the answer's picture is ready when the ball lands
        $$(".bfd", bff).forEach(function (x) { x.classList.toggle("on", x === a); x.classList.remove("hit"); x.setAttribute("aria-pressed", String(x === a)); });
        var line = null;
        $$(".bfl", bff).forEach(function (p) { var on = p.dataset.k === k; p.classList.toggle("on", on); p.classList.remove("fly"); p.style.strokeDashoffset = ""; if (on) line = p; });
        $$("iframe.bfvid", bff).forEach(function (f) { f.replaceWith(f._btn); });  // stop a lesson that is playing
        var land = function () {  // the ball is down: show the lesson for this miss
          a.classList.add("hit");
          $$(".bfp", bff).forEach(function (p) { p.hidden = p.id !== "bf-" + k; p.classList.toggle("in", !p.hidden); });
          ambCue($("#bf-" + k, bff));  // the light comes last, once the answer has settled
          var c = $("#bf-" + k + " [data-cnt]", bff); if (c && !still) countUp(c);
          // phones: let the landing be seen for a moment, then bring the answer to the top of the screen
          if (window.innerWidth < 760) setTimeout(function () { var r = $(".bfr", bff); window.scrollTo({ top: r.getBoundingClientRect().top + window.scrollY - 60, behavior: still ? "auto" : "smooth" }); }, still ? 0 : 650);
        };
        if (still || !line || !line.getTotalLength) land(); else shot(line, land);
      });
    });
    // The list of misses beside the course: a row and its dot light up together, the flight shows as a preview, a click plays it.
    function hot(k, on) {
      $$('.bfd[data-k="' + k + '"], .bfi[data-k="' + k + '"]', bff).forEach(function (x) { x.classList.toggle("hot", on); });
      $$('.bfl[data-k="' + k + '"]', bff).forEach(function (x) { x.classList.toggle("pre", on); });
    }
    $$(".bfd, .bfi", bff).forEach(function (x) {
      x.addEventListener("mouseenter", function () { hot(x.dataset.k, true); });
      x.addEventListener("mouseleave", function () { hot(x.dataset.k, false); });
      x.addEventListener("focus", function () { hot(x.dataset.k, true); });
      x.addEventListener("blur", function () { hot(x.dataset.k, false); });
    });
    $$(".bfi", bff).forEach(function (x) {
      x.addEventListener("click", function (ev) { ev.preventDefault(); hot(x.dataset.k, false); var d = $('.bfd[data-k="' + x.dataset.k + '"]', bff); if (d) d.click(); });
    });
    var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches, raf = 0;
    // The shot: a ball leaves the tee and flies the line of this miss, the tracer draws behind it. The ball is an HTML
    // element above the labels (it is in the air), its shadow stays in the drawing, on the ground.
    function shot(line, done) {
      var svg = line.ownerSVGElement, box = svg.parentNode, tee = $("circle.bfball", svg), ns = "http://www.w3.org/2000/svg";
      cancelAnimationFrame(raf); $$(".bffly", box).forEach(function (n) { n.remove(); });
      var len = line.getTotalLength(), ms = Math.max(480, Math.min(1000, len * 3.3)), top = Math.min(24, len * .085);
      var sh = document.createElementNS(ns, "ellipse"), ball = document.createElement("i"), lh = bff.classList.contains("lh");
      sh.setAttribute("class", "bffly bfgs"); ball.className = "bffly bfb";
      svg.appendChild(sh); box.appendChild(ball);
      line.classList.add("fly"); line.style.strokeDashoffset = 1; tee.style.opacity = 0;
      var t0 = performance.now();
      (function step(now) {
        var t = Math.min(1, Math.max(0, (now - t0) / ms)), e = 1 - Math.pow(1 - t, 2.4);  // fast off the club, slower as it comes down
        var p = line.getPointAtLength(len * e), h = Math.sin(Math.PI * e) * top;
        ball.style.left = (lh ? 320 - p.x : p.x) / 3.2 + "%"; ball.style.top = p.y / 3.6 + "%";
        ball.style.transform = "translate(-50%,-50%) scale(" + (1 + h * .022) + ")";
        sh.setAttribute("cx", p.x + h * .45); sh.setAttribute("cy", p.y + h * .6); sh.setAttribute("rx", 5 + h * .1); sh.setAttribute("ry", 2.6 + h * .05);
        sh.style.opacity = .3 - h * .007;
        line.style.strokeDashoffset = 1 - e;
        if (t < 1) { raf = requestAnimationFrame(step); return; }
        sh.remove(); ball.classList.add("out"); tee.style.opacity = "";
        setTimeout(function () { ball.remove(); }, 260);
        done();
      })(t0);
    }
  }

  // ---------- motion ----------
  var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function countUp(el, wait) {  // a number runs up to its value; it keeps the width of the final number, so nothing beside it moves
    var n = +el.dataset.cnt, t0 = performance.now() + (wait || 0), w = el.getBoundingClientRect().width;
    if (w) { el.style.display = "inline-block"; el.style.minWidth = w + "px"; }
    el.textContent = "0";
    (function step(now) {
      var t = Math.min(1, Math.max(0, (now - t0) / 700));
      el.textContent = Math.round(n * (1 - Math.pow(1 - t, 3))).toLocaleString("en-US");
      if (t < 1) requestAnimationFrame(step); else { el.style.display = ""; el.style.minWidth = ""; }
    })(performance.now());
  }
  // Reveal on scroll: only for what is below the fold when the page loads, so nothing visible ever blinks.
  // Leaderboard rows also grow their bar and run their count up.
  if (!calm && "IntersectionObserver" in window) {
    var rvs = $$(".ldi, .un, .ftw, .pgrid.row1, #feed > .vc").filter(function (el) { return el.getBoundingClientRect().top > window.innerHeight * .95; });
    if (rvs.length) {
      var rio = new IntersectionObserver(function (es) {
        var i = 0;
        es.forEach(function (x) {
          if (!x.isIntersecting) return;
          var el = x.target, d = Math.min(i++, 8) * 55; rio.unobserve(el);
          el.style.setProperty("--d", d + "ms"); el.classList.add("in");
          var c = $("[data-cnt]", el); if (c) countUp(c, d + 150);
        });
      }, { rootMargin: "0px 0px -6% 0px" });
      rvs.forEach(function (el) { el.classList.add("rv"); rio.observe(el); });
    }
  }
  if (!calm) $$(".vsb [data-cnt]").forEach(function (el, i) { countUp(el, 150 + i * 120); });  // lesson page: the counts run up
  // The colour field of the "Or pick it by name" block (see the comment inside). src is the element whose picture's light feeds it;
  // touch: driven by scrolling instead of a mouse.
  function ixField(blk, ixs, src, touch) {
      var fld = document.createElement("div"); fld.className = "ixf"; fld.setAttribute("aria-hidden", "true");
      fld.innerHTML = "<div class=ixg><i class=ixb></i><i class=ixb></i><i class=ixb></i><i class=ixb></i></div>"; blk.insertBefore(fld, blk.firstChild);
      var BL = $$(".ixb", fld);
      // --- colour: OKLCH, so lightness and colourfulness can be set evenly whatever the hue ---
      var lin = function (c) { c /= 255; return c <= .04045 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4); };
      var gam = function (c) { c = Math.max(0, Math.min(1, c)); return Math.round(255 * (c <= .0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - .055)); };
      var oklch = function (c) {
        var r = lin(c[0]), g = lin(c[1]), b = lin(c[2]);
        var l = Math.cbrt(.4122214708 * r + .5363325363 * g + .0514459929 * b), m = Math.cbrt(.2119034982 * r + .6806995451 * g + .1073969566 * b), s = Math.cbrt(.0883024619 * r + .2817188376 * g + .6299787005 * b);
        var A = 1.9779984951 * l - 2.428592205 * m + .4505937099 * s, Bb = .0259040371 * l + .7827717662 * m - .808675766 * s;
        return [.2104542553 * l + .793617785 * m - .0040720468 * s, Math.sqrt(A * A + Bb * Bb), (Math.atan2(Bb, A) * 180 / Math.PI + 360) % 360];
      };
      var rgbOf = function (L, C, h) {  // back to screen colour; too colourful for the screen: the colour is softened, its hue and lightness kept
        for (var k = 0; k < 16; k++, C *= .9) {
          var a = C * Math.cos(h * Math.PI / 180), b = C * Math.sin(h * Math.PI / 180);
          var l = L + .3963377774 * a + .2158037573 * b, m = L - .1055613458 * a - .0638541728 * b, s = L - .0894841775 * a - 1.291485548 * b;
          l *= l * l; m *= m * m; s *= s * s;
          var R = 4.0767416621 * l - 3.3077115913 * m + .2309699292 * s, G = -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s, B2 = -.0041960863 * l - .7034186147 * m + 1.707614701 * s;
          if (Math.min(R, G, B2) > -.003 && Math.max(R, G, B2) < 1.003) return [gam(R), gam(G), gam(B2)];
        }
        return [gam(L * L * L), gam(L * L * L), gam(L * L * L)];
      };
      // The colour rules. The brand green sits at hue 159 (OKLCH; #0b7a4b and #3ecf8e alike). The picture's natural colours (grass,
      // trees, water, sky: hue 100-275) keep their direction but are pulled 40% toward the brand green and kept between fresh green
      // (138) and sky (222), so a field is never yellow, olive or gold. Skin, sand, wood, red shirts and grey have no hue of their own
      // here: they become a faint brand-tinted light (never cream, never brown). Lightness is fixed per theme (dark: a luminous band like
      // #3ecf8e and #9be7c4; light: pastels that keep black text readable), and colourfulness follows the picture within a band.
      var H0 = 159;
      // role: [lightness low, lightness high, chroma min, chroma max] per theme. Dark: a deep body under brighter lights, so the
      // field has depth instead of one flat slab. Light: a pale wash under deeper pastel tints, multiplied like ink.
      var ROLE = { dk: { body: [.44, .52, .07, .12], lead: [.72, .8, .12, .18], mid: [.64, .72, .1, .16] },
        lt: { body: [.91, .95, .035, .06], lead: [.77, .84, .08, .13], mid: [.83, .88, .06, .11] } };
      var hueOf = function (o, dk) { var d = o[2] - H0; return o[2] > 100 && o[2] < 275 && o[1] > .03 ? Math.max(dk ? 154 : 162, Math.min(230, H0 + d * (d < 0 ? .2 : .65))) : -1; };  // -1: no hue of its own. Light: a little bluer, as multiplied layers lean yellow
      var tune = function (c, dk, role, bold) {
        var o = oklch(c), L = o[0], C = o[1], h = hueOf(o, dk), R = ROLE[dk ? "dk" : "lt"][role];
        var t = Math.max(0, Math.min(1, (L - .3) / .5));
        return h < 0 ? rgbOf(R[0] + (R[1] - R[0]) * t, R[2] * .7, H0 + 6) : rgbOf(R[0] + (R[1] - R[0]) * t, Math.max(R[2], Math.min(R[3], (R[2] + C * .8) * bold)), h);
      };
      var BRAND = [[11, 122, 75], [62, 207, 142, .6], [155, 231, 196, .5]];  // a grey picture: the brand's own greens
      var rgba = function (c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a.toFixed(2) + ")"; };
      var dirOf = function (q) { var u = (q[1] - .5) * 1.4; return q[0] === 0 ? [u, -1] : q[0] === 1 ? [u, 1] : q[0] === 2 ? [-1, u] : [1, u]; };
      // --- motion: one spring per blob (stiffness, damping); the blobs follow at different speeds, so the field stretches and re-forms ---
      var S = [{ k: .02, d: .87 }, { k: .065, d: .8 }, { k: .026, d: .85 }, { k: .014, d: .89 }];
      S.forEach(function (s) { s.x = s.y = s.vx = s.vy = s.tx = s.ty = 0; s.tf = ""; });
      var W = 0, H = 0, ox = 0, oy = 0, px = 0, py = 0, fxp = 1, fyp = 1, d1 = [0, 1], d2 = [-1, -.3], pls = 0, plv = 0, run = 0, last = 0;
      var measure = function () { var r = fld.getBoundingClientRect(); W = r.width; H = r.height; ox = r.left + window.scrollX; oy = r.top + window.scrollY; };
      var aim = function () {  // where each blob wants to be
        var cx0 = W / 2, cy0 = H / 2, dx = px - cx0, dy = py - cy0;
        var qx = px + 144 * fxp, qy = py + 92 * fyp;  // the centre of the floating picture (it flips left/up near the window edge)
        S[0].tx = cx0 + dx * .18; S[0].ty = cy0 + dy * .18;  // the body: the picture's main colour over the whole block, heavy and slow
        S[1].tx = qx + d1[0] * 80; S[1].ty = qy + d1[1] * 56;  // the lead: its strongest colour, right behind the picture, on the side where it is in the picture
        S[2].tx = cx0 + d2[0] * W * .3 - dx * .25; S[2].ty = cy0 + d2[1] * H * .28 - dy * .25;  // the second colour, across the block, moving against the pointer
        S[3].tx = cx0 - d2[0] * W * .22 + dx * .45; S[3].ty = cy0 - d2[1] * H * .2 + dy * .45;  // the fourth colour (brand green, violet on dark), slowest of all
      };
      var step = function (now) {
        var dt = Math.min(3, Math.max(.5, (now - last) / 16.7)), mv = false; last = now;
        plv += -pls * .09 * dt; plv *= Math.pow(.8, dt); pls += plv * dt;  // a short swell when a new picture arrives
        S.forEach(function (s, i) {
          s.vx += (s.tx - s.x) * s.k * dt; s.vy += (s.ty - s.y) * s.k * dt; var f = Math.pow(s.d, dt); s.vx *= f; s.vy *= f;
          s.x += s.vx * dt; s.y += s.vy * dt;
          var sp = Math.sqrt(s.vx * s.vx + s.vy * s.vy), st = Math.min(.5, sp * .02), a = (Math.atan2(s.vy, s.vx) * 57.3).toFixed(1), g = 1 + pls * (i === 1 ? 1 : .45);
          // stretched along the way it moves, without turning its own shape
          var tf = "translate3d(" + s.x.toFixed(1) + "px," + s.y.toFixed(1) + "px,0) rotate(" + a + "deg) scale(" + ((1 + st) * g).toFixed(3) + "," + (g / (1 + st * .55)).toFixed(3) + ") rotate(" + (-a) + "deg)";
          if (tf !== s.tf) BL[i].style.transform = s.tf = tf;
          if (sp > .04 || Math.abs(s.tx - s.x) + Math.abs(s.ty - s.y) > .4) mv = true;
        });
        run = mv || Math.abs(pls) + Math.abs(plv) > .002 ? requestAnimationFrame(step) : 0;
      };
      var kick = function () { if (!run) { last = performance.now(); run = requestAnimationFrame(step); } };
      var point = function (ev) {
        px = ev.pageX - ox; py = ev.pageY - oy;
        fxp = ev.clientX + 272 > window.innerWidth ? -1 : 1; fyp = ev.clientY + 167 > window.innerHeight ? -1 : 1;
        aim();
      };
      src._onpal = function (pal, M, Q) {
        var dk = getComputedStyle(document.documentElement).colorScheme.indexOf("dark") >= 0, at = null;
        if (pal && M) {  // the lead is the strongest pool; the second is the strongest one that differs most from it after tuning (sky against grass, say)
          var O = M.map(function (m) { var o = oklch(m); return [hueOf(o, dk), o[0], m[3]]; }), li = 0;
          O.forEach(function (o, i) { if (o[2] > O[li][2]) li = i; });
          var mi = -1, best = -1;
          O.forEach(function (o, i) {
            if (i === li) return;
            var dh = o[0] < 0 || O[li][0] < 0 ? (o[0] === O[li][0] ? 0 : .5) : Math.abs(o[0] - O[li][0]) / 30, sc = o[2] * (.3 + Math.min(1.6, dh) + Math.abs(o[1] - O[li][1]) * 1.5) * (o[0] < 0 ? .6 : 1);
            if (sc > best) { best = sc; mi = i; }
          });
          pal = [pal[0], M[li], M[mi]]; at = [Q[li], Q[mi]];
        }
        var p = pal && pal[1][3] >= .25 ? pal : BRAND, vivid = p === BRAND ? 0 : Math.min(1, p[1][3]), bold = .85 + .35 * vivid;
        var c = [tune(p[0], dk, "body", bold), tune(p[1], dk, "lead", bold * 1.1), tune(p[2], dk, "mid", bold), dk ? rgbOf(.68, .13, 300) : rgbOf(.8, .1, H0 + 5)];
        var A = dk ? [.6, .8, .6, .34 + .2 * (1 - vivid)] : [.9, .85, .8, .4 + .25 * (1 - vivid)];
        BL.forEach(function (b, i) { b.style.backgroundColor = rgba(c[i], A[i]); });
        if (p !== BRAND && at) { d1 = dirOf(at[0]); d2 = dirOf(at[1]); if (d1[0] * d2[0] + d1[1] * d2[1] > .5) d2 = [-d2[0], -d2[1]]; }  // the two colours never pile up on one side
        if (blk.classList.contains("lit")) { aim(); plv += calm ? 0 : .045; kick(); }
      };
      if (touch) {  // no pointer: the topic in the middle of the screen leads, and the field flows to it as the page scrolls
        fxp = fyp = 0;
        return {
          focus: function (a) {
            measure(); var r = a.getBoundingClientRect(), f = fld.getBoundingClientRect(); px = r.left + r.width / 2 - f.left; py = r.top + r.height / 2 - f.top; aim();
            if (!blk.classList.contains("lit")) { S.forEach(function (s) { s.x = s.tx * .6 + px * .4; s.y = s.ty * .6 + py * .4; s.vx = s.vy = 0; }); pls = calm ? 0 : -.18; plv = 0; }
            if (calm) S.forEach(function (s) { s.x = s.tx; s.y = s.ty; });
            kick();
          },
          lit: function (on) { if (on === blk.classList.contains("lit")) return; blk.classList.toggle("lit", on); if (!on && !calm) { plv += .03; } kick(); }
        };
      }
      ixs.addEventListener("mouseenter", function (ev) {
        measure(); point(ev);
        if (!blk.classList.contains("lit")) {  // it blooms out from where the pointer came in, instead of flying in from a corner
          S.forEach(function (s) { s.x = s.tx * .6 + px * .4; s.y = s.ty * .6 + py * .4; s.vx = s.vy = 0; });
          pls = calm ? 0 : -.22; plv = 0;
        }
        blk.classList.add("lit"); kick();
      });
      ixs.addEventListener("mousemove", function (ev) { point(ev); if (calm) S.forEach(function (s) { s.x = s.tx; s.y = s.ty; }); kick(); });
      ixs.addEventListener("mouseleave", function () { blk.classList.remove("lit"); if (!calm) { plv += .03; kick(); } });  // it swells a little as it fades, like steam
      window.addEventListener("resize", function () { if (blk.classList.contains("lit")) measure(); }, { passive: true });
      }
  // Home index of problems: the picture of a problem's top lesson floats beside the pointer (mouse only).
  var ixs = $(".ixs");
  if (ixs && window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    var pv = document.createElement("div"), pvi = document.createElement("img"), tx = 0, ty = 0, cx = 0, cy = 0, pr = 0;
    pv.className = "ixp"; pvi.alt = ""; pv.appendChild(pvi); document.body.appendChild(pv);
    pvi.addEventListener("load", function () { amb(pv, true); });  // each topic's picture brings its own light, which trails behind as it flies
    var follow = function () {
      var k = calm ? 1 : .2, ox = cx, oy = cy; cx += (tx - cx) * k; cy += (ty - cy) * k;
      pv.style.transform = "translate3d(" + cx.toFixed(1) + "px," + cy.toFixed(1) + "px,0)";
      var A = pv._amb; if (A) { A.vx = A.vx * .6 + (cx - ox) * .4; A.vy = A.vy * .6 + (cy - oy) * .4; if (Math.abs(A.vx) + Math.abs(A.vy) > .3) ambGo(); }
      pr = pv.classList.contains("on") || Math.abs(tx - cx) + Math.abs(ty - cy) > .5 ? requestAnimationFrame(follow) : 0;
    };
    ixs.addEventListener("mousemove", function (ev) {
      var x = ev.clientX + 24, y = ev.clientY + 24;
      if (x + 248 > window.innerWidth) x = ev.clientX - 264;
      if (y + 143 > window.innerHeight) y = ev.clientY - 159;
      tx = x; ty = y; if (!pr) pr = requestAnimationFrame(follow);
    });
    $$(".ix", ixs).forEach(function (a) {
      a.addEventListener("mouseenter", function () {
        if (!a.dataset.vid) { pv.classList.remove("on"); if (pv._amb) pv._amb.vis = false; return; }
        pvi.src = B + "/static/thumbs/mq2/" + a.dataset.vid + ".webp";
        if (!pv.classList.contains("on")) { cx = tx; cy = ty; }
        pv.classList.add("on"); if (pv._amb) pv._amb.vis = true;
      });
    });
    ixs.addEventListener("mouseleave", function () { pv.classList.remove("on"); if (pv._amb) { pv._amb.vis = false; pv._amb.vx = pv._amb.vy = 0; } });
    // On the home page the whole "Or pick it by name" block takes on the colours of the topic under the pointer. Four soft colour
    // blobs sit in ONE container with a large blur, so they melt into a single field: on dark they add up like light in fog, on
    // light they lie over each other like ink in water. The picture's colours are first pulled into the brand's family (fresh green
    // to sky, see tune), and one blob always carries the brand green, on dark a violet that works against the greens. The blobs only move, stretch and turn (transform), drift
    // slowly on their own (CSS), and fade to a new colour from the picture outward; nothing runs while the pointer is elsewhere.
    var blk = ixs.closest(".pickb"); if (blk) ixField(blk, ixs, pv, false);
  }
  // Phones and tablets have no pointer: on the home page the topic passing through the middle of the screen turns green and the
  // block takes on the colours of its #1 lesson, flowing on to the next topic as the page scrolls. Only while the block is on screen.
  if (ixs && window.matchMedia && window.matchMedia("(hover: none)").matches && window.IntersectionObserver) {
    var tblk = ixs.closest(".pickb");
    if (tblk) {
      var smp = document.createElement("div"), smi = document.createElement("img"), tAct = null, tOn = false;
      smp.className = "ixsmp"; smp.setAttribute("aria-hidden", "true"); smi.alt = ""; smp.appendChild(smi); tblk.appendChild(smp);
      smi.addEventListener("load", function () { amb(smp); });  // the picture is only read for its colours; it is never shown
      var TF = ixField(tblk, ixs, smp, true);
      var pick = function (a) {
        if (a === tAct) return; if (tAct) tAct.classList.remove("act"); tAct = a; a.classList.add("act");
        if (a.dataset.vid) smi.src = B + "/static/thumbs/mq2/" + a.dataset.vid + ".webp";
        TF.focus(a); TF.lit(tOn);
      };
      var band = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) pick(e.target); }); }, { rootMargin: "-44% 0px -44% 0px" });
      $$(".ix", ixs).forEach(function (a) { band.observe(a); });
      new IntersectionObserver(function (es) { tOn = es[es.length - 1].intersectionRatio > .25; TF.lit(tOn && !!tAct); if (!tOn && tAct) { tAct.classList.remove("act"); tAct = null; } }, { threshold: [0, .25] }).observe(tblk);
    }
  }
  // Page transition: the picture you pick becomes the player of the lesson page (browsers without view transitions just navigate).
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href*="/watch/"]'); if (!a) return;
    var box = a.closest(".vc, .ldr, .bfp, .frow, li") || a, img = $("img", a) || $("img", box);
    $$("img").forEach(function (x) { if (x.style.viewTransitionName) x.style.viewTransitionName = ""; });
    if (img) img.style.viewTransitionName = "vtl";
  }, true);

  // ---------- badges page: find your channel, select-all on focus ----------
  var bf = $("#bfind");
  if (bf) bf.addEventListener("input", function () {
    var v = bf.value.trim().toLowerCase(), n = 0;
    $$(".brow").forEach(function (r) { r.hidden = !!v && r.dataset.name.indexOf(v) < 0; if (!r.hidden) n++; });
    var no = $("#bnone"); if (no) no.hidden = n > 0;
  });
  var kit = $("#badges");
  function openKit() { if (kit && location.hash === "#badges") { kit.open = true; kit.scrollIntoView(); } }
  openKit(); window.addEventListener("hashchange", openKit);
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest("[data-copy]"); if (!b) return;
    var t = b.dataset.copy, done = function () { flash("Copied"); var o = b.textContent; b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = o; }, 1400); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(done, function () { window.prompt("Copy:", t); });
    else window.prompt("Copy:", t);
  });

  // ---------- welcome box ----------
  try { localStorage.removeItem("gv_nowelcome"); } catch (e) {}  // the old dismissible welcome box is gone; never hide the home intro

  // ---------- review 3: plan bar, show all, saved menu, search page ----------
  var pp = new URLSearchParams(location.search).get("plan");
  $$(".pbar[data-plan]").forEach(function (b) { if (b.dataset.plan === pp) b.hidden = false; });
  var sa = $("#showall"); if (sa) sa.onclick = function () { document.getElementById(sa.getAttribute("aria-controls")).classList.add("showall"); sa.parentNode.remove(); };
  [["liked", "/liked/"], ["later", "/later/"], ["history", "/history/"]].forEach(function (x) {
    var a = $('#side a[href="' + B + x[1] + '"]'); if (a && !load(x[0]).length && location.pathname !== B + x[1]) a.hidden = true;
  });
  if (location.pathname === B + "/search/" && window.innerWidth <= 760) document.body.classList.add("searching");

  // ---------- plan box only when following a plan ----------
  var planParam = new URLSearchParams(location.search).get("plan");
  $$(".inplan[data-plan]").forEach(function (b) { if (b.dataset.plan !== planParam && !(load("plans", {})[b.dataset.plan] || []).length) b.style.display = "none"; });

  // ---------- fix plan progress ----------
  var plans = load("plans", {});
  function planSync() {
    $$("button.done[data-plan]").forEach(function (b) {
      var on = (plans[b.dataset.plan] || []).indexOf(b.dataset.vid) >= 0;
      b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); $("span", b).textContent = on ? "Done" : "Mark as done";
      var li = b.closest(".pli"); if (li) li.classList.toggle("isdone", on);
    });
    $$(".planbar").forEach(function (bar) {
      var n = +bar.dataset.n, d = (plans[bar.dataset.plan] || []).length;
      $(".prog span", bar).style.width = Math.min(100, 100 * d / n) + "%"; $(".progt", bar).textContent = d + " of " + n + " done";
      var st = $("#startplan"), lis = $$(".pli");
      if (st && d && d < n) { var nx = lis.filter(function (li) { return !li.classList.contains("isdone"); })[0]; if (nx) { st.href = $("a.th", nx).href; $("span", st).textContent = "Continue: step " + (lis.indexOf(nx) + 1); } }
      if (st && d >= n) $("span", st).textContent = "Watch again";
    });
    $$(".plc[data-plan],.plr[data-plan]").forEach(function (c) {
      var done = plans[c.dataset.plan] || [], d = done.length; $(".pprog", c).textContent = d ? d + "/" + c.dataset.n + " done" : "";
      $$(".pt", c).forEach(function (t) { t.classList.toggle("dn", done.indexOf(t.dataset.v) >= 0); });
    });
  }
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button.done[data-plan]"); if (!b) return;
    var l = plans[b.dataset.plan] || [], i = l.indexOf(b.dataset.vid);
    if (i >= 0) l.splice(i, 1); else l.push(b.dataset.vid);
    plans[b.dataset.plan] = l; save("plans", plans); planSync(); flash(i >= 0 ? "Marked as not done" : "Nice, step done");
  });
  planSync();

  // A small preview picture that is missing: try the large one, and only hide the image if that fails too.
  window.thumbFail = function (im) {
    if (im.src.indexOf("/mq2/") > 0) { im.removeAttribute("srcset"); im.src = im.src.replace("/mq2/", "/hq2/"); }
    else { im.onerror = null; im.style.visibility = "hidden"; }
  };
  // ---------- index-driven views ----------
  var list = $("#list"), feed = $("#feed");
  if (!list && !feed) return;
  function card(v, hq) {
    var href = B + "/watch/" + v[0] + "/", t = TYPES[v[8]], th = B + "/static/thumbs/";
    return '<article class="vc" data-vid="' + v[0] + '"><div class="thw" data-vid="' + v[0] + '"><a class="th" href="' + href + '"><img loading="lazy" src="' + th + "mq2/" + v[0] + '.webp"' + (hq ? ' srcset="' + th + "mq2/" + v[0] + ".webp 320w, " + th + "hq2/" + v[0] + '.webp 480w" sizes="(max-width:600px) 100vw, (max-width:1000px) 50vw, 33vw"' : "") + ' alt="">' +
      (v[12] ? '<span class="du">' + dur(v[12]) + "</span>" : "") + '</a><button class="lb" aria-label="Watch later" title="Watch later"><svg viewBox="0 0 24 24"><path d="M14.97 16.95 10 13.87V7h2v5.76l4.03 2.49-1.06 1.7zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg></button></div>' +
      '<div class="vm"><h3><a href="' + href + '">' + esc(v[1]) + '</a></h3><p class="ch">' + (v[3] ? '<a href="' + B + "/coach/" + v[3] + '/">' + esc(v[2]) + "</a>" : esc(v[2])) + (t ? " · " + t : "") +
      '</p><p class="st"><span><b>' + v[4] + "</b> recommend" + (v[4] == 1 ? "s" : "") + "</span>" + (v[5] ? '<span class="ok">' + CK + v[5] + " fixed it</span>" : "") + (v[6] ? '<span class="nw">' + esc(v[6]) + "</span>" : "") + "</p></div></article>";
  }
  function dur(s) { var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (x < 10 ? "0" : "") + x; }
  function paint(el, arr, append) { el.insertAdjacentHTML(append ? "beforeend" : "afterbegin", arr.map(function (v) { return card(v, el === feed); }).join("")); if (!append) {} markLater(); }
  function infinite(el, arr, start) {
    var i = start, step = 24, sentinel = document.createElement("div"); sentinel.className = "sentinel"; el.after(sentinel);
    var io = new IntersectionObserver(function (es) {
      if (!es[0].isIntersecting) return;
      paint(el, arr.slice(i, i + step), true); i += step;
      if (i >= arr.length) { io.disconnect(); sentinel.remove(); }
    }, { rootMargin: "600px" });
    io.observe(sentinel);
  }

  fetch(B + "/static/index.json").then(function (r) { return r.json(); }).then(function (ix) {
    var byId = {}; ix.v.forEach(function (v) { byId[v[0]] = v; });
    var dis = {}; load("disliked").forEach(function (x) { dis[x.v] = 1; });
    var hideDis = settings.hidedis !== false;
    var ok = function (v) { return !(hideDis && dis[v[0]]); };
    var year = new Date().getFullYear();

    // personalized home feed
    if (feed) {
      var liked = load("liked"), seen = {}; load("history").forEach(function (x) { seen[x.v] = 1; });
      var w = {};
      liked.forEach(function (x) { var v = byId[x.v]; if (v) v[7].forEach(function (p) { w[p] = (w[p] || 0) + 1; }); });
      load("disliked").forEach(function (x) { var v = byId[x.v]; if (v) v[7].forEach(function (p) { w[p] = (w[p] || 0) - 0.5; }); });
      var personal = liked.length + load("disliked").length > 0;
      var seed = Math.floor(Date.now() / 36e5);
      var rnd = function (s) { var x = Math.sin(s) * 1e4; return x - Math.floor(x); };
      var scored = ix.v.filter(ok).filter(function (v) { return !(v[12] > 0 && v[12] < 30); }).map(function (v, i) {  // clips are not lessons (CLIP_S in build.py)
        var aff = v[7].reduce(function (a, p) { return a + (w[p] || 0); }, 0);
        var s = Math.log(1 + v[4]) + 0.4 * Math.log(1 + v[5]) + (personal ? 0.6 * aff : 0) - (seen[v[0]] ? 1.5 : 0) + 0.8 * rnd(seed + i);
        return [s, v];
      }).sort(function (a, b) { return b[0] - a[0]; }).map(function (x) { return x[1]; });
      var onBoard = {}; $$("#board .ldr").forEach(function (r) { onBoard[r.dataset.vid] = 1; });
      if (personal || Object.keys(seen).length) { feed.innerHTML = ""; paint(feed, scored.filter(function (v) { return !onBoard[v[0]]; }).slice(0, 6)); }
      return;
    }

    var kind = list.dataset.list, arr = [], extra = "";
    if (kind === "search") {
      var q = (new URLSearchParams(location.search).get("q") || "").trim().toLowerCase().replace(/\u2019/g, "'");
      $("#q").value = q; $("#ltitle").textContent = q ? "Results for \u201c" + q + "\u201d" : "Search";
      if (q) {
        var SYN = { slicing: "slice", sliced: "slice", slices: "slice", hooking: "hook", hooks: "hook", shanking: "shanks", shank: "shanks", shanked: "shanks",
          topping: "topping", topped: "topping", tops: "topping", chunk: "fat", chunking: "fat", chunked: "fat", fat: "fat", thin: "thin", sculled: "thin",
          chipping: "chipping", chip: "chipping", chips: "chipping", putt: "putting", putts: "putting", driver: "driver", drive: "driver", irons: "iron", iron: "iron",
          bunker: "bunker", sand: "bunker", ott: "over the top", "over-the-top": "over the top", ee: "early extension", casting: "casting", lag: "lag", speed: "speed" };
        var words = q.split(/\s+/).map(function (w) { return SYN[w] || w; });
        var rx = words.map(function (w) { return new RegExp("\\b" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")); });
        var low = function (s) { return s.toLowerCase().replace(/\u2019/g, "'"); };  // titles carry typographic apostrophes
        var hit = function (s) { s = low(s); return rx.every(function (r) { return r.test(s); }); };
        var hitAny = function (s) { s = low(s); return rx.some(function (r) { return r.test(s); }); };
        var ps = ix.p.filter(function (p) { return hitAny(p[1] + " " + p[0].replace(/-/g, " ")); }), cs = ix.c.filter(function (c) { return hit(c[1]); });
        if (ps.length) extra += '<div class="sres"><h2>Problems</h2><div class="tags">' + ps.map(function (p) { return '<a class="tag" href="' + B + "/fix/" + p[0] + '/">' + esc(p[1]) + " · " + p[3] + " recommendations</a>"; }).join("") + "</div></div>";
        if (cs.length) extra += '<div class="sres"><h2>Coaches</h2><div class="tags">' + cs.slice(0, 12).map(function (c) { return '<a class="tag" href="' + B + "/coach/" + c[0] + '/">' + esc(c[1]) + "</a>"; }).join("") + "</div></div>";
        var sl = ps.map(function (p) { return p[0]; });
        var pscore = function (v) { return sl.reduce(function (a, p) { return a + ((v[14] || {})[p] || 0); }, 0); };
        arr = ix.v.filter(ok).filter(function (v) { return pscore(v) > 0 || hit(v[1] + " " + v[2] + " " + v[6]); });
        arr.sort(function (x, y) { return pscore(y) - pscore(x) || (hit(y[1]) - hit(x[1])) || y[4] - x[4]; });
        if (extra) list.insertAdjacentHTML("beforebegin", extra + '<h2 class="row">Lessons</h2>');
      }
    } else if (kind === "browse") {
      var f = $("#filters"), P = new URLSearchParams(location.search);
      ["sort", "p", "type", "level"].forEach(function (k) { if (P.get(k)) f.elements[k].value = P.get(k); });
      f.elements["new"].checked = P.get("new") === "1";
      // every choice in the sentence is as wide as the words it shows
      var fitSel = function () {
        $$(".fs select", f).forEach(function (s) {
          var m = document.createElement("span"); m.textContent = s.options[s.selectedIndex].text; m.style.cssText = "position:absolute;visibility:hidden;white-space:pre";
          s.parentNode.appendChild(m); s.style.width = Math.ceil(m.getBoundingClientRect().width) + 22 + "px"; m.remove();
        });
      };
      window.addEventListener("resize", fitSel); if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitSel);
      var run = function () {
        fitSel();
        var o = {}; ["sort", "p", "type", "level"].forEach(function (k) { if (f.elements[k].value) o[k] = f.elements[k].value; }); if (f.elements["new"].checked) o["new"] = "1";
        history.replaceState(null, "", "?" + new URLSearchParams(o).toString());
        var a = ix.v.filter(ok).filter(function (v) {
          return (!o.p || v[7].indexOf(o.p) >= 0) && (!o.type || v[8] === o.type) && (!o.level || v[9] === o.level) && (!o["new"] || v[10] >= year - 1);
        });
        var srt = o.sort || "recs";
        a.sort(srt === "fixed" ? function (x, y) { return y[5] - x[5] || y[4] - x[4]; } : srt === "recent" ? function (x, y) { return y[10] - x[10] || y[4] - x[4]; } :
          srt === "oldest" ? function (x, y) { return x[11] - y[11] || y[4] - x[4]; } : srt === "views" ? function (x, y) { return y[13] - x[13]; } :
          srt === "hidden" ? function (x, y) { return (y[4] / Math.log(10 + y[13])) - (x[4] / Math.log(10 + x[13])); } : function (x, y) { return y[4] - x[4]; });
        list.innerHTML = ""; $$(".sentinel").forEach(function (s) { s.remove(); });
        $("#count").textContent = a.length.toLocaleString("en-US") + " lessons"; paint(list, a.slice(0, 48)); infinite(list, a, 48);
        $("#empty").textContent = a.length ? "" : "No lessons match these filters.";
      };
      f.onchange = run; run(); return;
    } else {
      arr = load(kind).map(function (x) { return byId[x.v]; }).filter(Boolean);
      if (kind !== "disliked") arr = arr.filter(ok);
    }
    paint(list, arr.slice(0, 48)); infinite(list, arr, 48);
    $("#empty").style.display = arr.length || extra ? "none" : "";
    var ex = $("#emptyx"); if (ex) ex.hidden = !!(arr.length || extra);
    if (kind === "search" && !arr.length && !extra) $("#empty").textContent = "No results. Try a problem like slice, shanks or chipping.";
  });
})();
