/* The home page's hole as a drawing on paper, seen from behind the tee (home page only).
   It upgrades the drawn finder in #bf: where WebGL 2 runs, a paper sheet with the hole is drawn in perspective with depth of
   field, model trees, shrubs and the flag stand on it as photographed sprites, and the ball flies each miss in 3D. The
   finder's own dots (.bfd), labels, answers and the left-handed switch stay as they are; app.js asks window.gvStage to fly
   the ball and gets its callback on landing. Without WebGL 2, or if anything fails to load, the drawn SVG hole stays.
   Images: static/stage/ (paper-light/-dark.webp are generated sheets of build/course.svg's hole, the rest keyed model
   photos). One world unit is 100 px of the 2048 x 1536 sheet; S() places the finder's 320 x 360 course on it. */
(function () {
  "use strict";
  function bail() { document.documentElement.classList.remove("gvwill"); }
  // a time limit: if the stage is not live in 4 s (slow network, a hanging image, an error), the drawn hole shows and the
  // stage does not take over later
  var gaveUp = false, giveUp = setTimeout(function () { if (live) return; gaveUp = true; try { teardown(); } catch (err) { bail(); } }, 4000);
  var bf = document.getElementById("bf"), welcome = document.querySelector(".welcome"), me = document.currentScript;
  if (!bf || !welcome || !me || !window.WebGL2RenderingContext) { bail(); return; }
  if (navigator.connection && navigator.connection.saveData) { bail(); return; }  // data saver: the drawn hole is enough
  var bfc = bf.querySelector(".bfc"); if (!bfc) { bail(); return; }
  var base = me.src.replace(/stage\.js.*$/, "stage/"), ver = (me.src.match(/[?&]v=([^&]+)/) || [])[1] || "";
  function src(n) { return base + n + ".webp" + (ver ? "?v=" + ver : ""); }
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var touch = window.matchMedia && matchMedia("(hover: none)").matches;

  // ---- the hole on the sheet
  var lefty = bf.classList.contains("lh");  // left-handed golfers see the hole mirrored; the dots' labels swap in CSS
  function S(x, y) { var px = 674.5 + 3.722 * x; return [lefty ? 2048 - px : px, 98 + 3.722 * y]; }
  function Wd(s, h) { return [s[0] / 100, h || 0, s[1] / 100]; }
  var TEE = [160, 326], CUP = [160, 46.5], MID = [160, 180];
  // The golfer always aims at the flag: slice and hook leave on the target line and bend, pull and shank leave off line.
  // Ends match MISSES in build.py. fly: pk apex height (units), ap how late the apex comes, land share of the path in the
  // air, b bounce, t time.
  var MISS = {
    slice: { c: [[160, 326], [160, 232], [178, 140], [262, 96]], fly: { pk: 1.9, ap: 1.45, land: .93, b: .7, t: 1.05 } },
    hook: { c: [[160, 326], [160, 232], [142, 140], [58, 96]], fly: { pk: 1.15, ap: 1.6, land: .83, b: 1.1, t: .95 } },
    over_the_top: { c: [[160, 326], [92, 44]], fly: { pk: 1.6, ap: 1.45, land: .9, b: 1, t: 1 } },
    shank: { c: [[160, 326], [252, 236]], fly: { pk: .32, ap: 1.1, land: .62, b: 1.5, t: .7 } },
    driver_distance: { c: [[160, 326], [160, 158]], fly: { pk: 1.05, ap: 1.5, land: .85, b: 1, t: 1 } },
    iron_contact: { c: [[160, 326], [160, 262]], fly: { pk: 1.45, ap: 1.15, land: .96, b: .45, t: 1.05 } }
  };
  Object.keys(MISS).forEach(function (k) {
    var m = MISS[k], n = m.c.length; m.cw = m.c;
    // hook and slice land a little shorter on phones, so their dots and labels clear the pull's (which lands just above)
    m.cn = m.c.map(function (p, i) { return [160 + (p[0] - 160) * .86, p[1] + (i === n - 1 && (k === "hook" || k === "slice") ? 30 : 0)]; });
  });
  var phone = false;
  function at(m, t) {
    var c = m.c; if (c.length === 2) return [c[0][0] + (c[1][0] - c[0][0]) * t, c[0][1] + (c[1][1] - c[0][1]) * t];
    var u = 1 - t; return [u * u * u * c[0][0] + 3 * u * u * t * c[1][0] + 3 * u * t * t * c[2][0] + t * t * t * c[3][0], u * u * u * c[0][1] + 3 * u * u * t * c[1][1] + 3 * u * t * t * c[2][1] + t * t * t * c[3][1]];
  }
  // Models in small groups: paper x, paper y, height in units, sprite. Placed so none stands in front of a dot.
  var SPR = ["tree-1", "tree-2", "tree-3", "tree-1", "tree-5", "grass-1", "grass-2", "bush-1", "bush-2"];
  var MODELS = [
    [1150, 90, 1.9, 1], [1060, 140, 1.3, 4], [1210, 150, .6, 7],
    [1430, 40, 2.2, 2], [1520, 80, 1.7, 0], [1380, 100, .3, 5],
    [760, 250, 1.8, 0], [830, 320, .6, 8], [780, 180, 1.4, 2],
    [880, 1160, 1.7, 2], [970, 1180, .32, 6], [950, 1060, .6, 7],
    [1880, 380, 2, 0], [1960, 310, 1.5, 1], [1830, 440, .3, 5],
    [1800, 840, 2.2, 1], [1700, 900, .65, 8], [1740, 770, 1.3, 4],
    [1560, 1250, 1.3, 0], [1510, 1300, .32, 6], [1660, 1230, .6, 7],
    [870, 960, .3, 5], [1120, 1000, .26, 6]];
  var FLAG_H = 1.15;
  // Tuned on the prototype (depth of field, focus at rest on the flag, flight, parallax, camera follow, easing).
  var CFG = { dof: 4.5, rest: 18, speed: 1, height: 1, parallax: 1, follow: 1, ease: .07 };

  // ---- the stage element, behind the welcome block (wide screens) or inside the finder box (narrow)
  var st = document.createElement("div"); st.className = "gvst"; st.setAttribute("aria-hidden", "true");
  st.innerHTML = '<div class="gvw"><canvas class="gvgl"></canvas><canvas class="gvtr"></canvas><div class="gvov"></div></div>';
  var wrap = st.firstChild, cv = wrap.children[0], trc = wrap.children[1], ov = wrap.children[2];
  var gl = cv.getContext("webgl2", { antialias: false, alpha: false, premultipliedAlpha: false, powerPreference: "low-power", failIfMajorPerformanceCaveat: true });
  if (!gl) { bail(); return; }

  // ---- camera: above the middle line of the hole, looking along it; foc (px) and the centre (cx0, cy0) are fitted so that
  // the whole hole and its six dots fill the finder box, wherever that box sits in the canvas
  var cam = { p: [0, 0, 0], R: [1, 0, 0], U: [0, 1, 0], F: [0, 0, -1] };
  var W = 1, H = 1, foc = 500, cx0 = 0, cy0 = 0, dpr = 1, narrow = false, offX = 0, offY = 0;
  var par = [0, 0], parT = [0, 0], camOff = [0, 0], camOffT = [0, 0], camRet = null;
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function nrm(a) { var l = Math.hypot(a[0], a[1], a[2]); return [a[0] / l, a[1] / l, a[2] / l]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function setCam() {
    var fl = phone ? CFG.follow * .35 : CFG.follow, ox = par[0] * .35 * CFG.parallax + camOff[0] * fl, oz = camOff[1] * fl, oy = par[1] * CFG.parallax, p, t;
    // camera and target share x, so the far edge of the sheet and the horizon stay level
    // a steeper view than the prototype's, so the hole fills the finder box's height instead of lying flat
    var hx = S(MID[0], MID[1])[0] / 100;
    if (narrow) { p = [hx + ox, 8.2 + oy * .15, 19.2 + oz]; t = [hx + ox, 0, 8.0 + oz * .5]; }
    else { var cxw = hx + (lefty ? 2.3 : -2.3); p = [cxw + ox, 4.0 + oy * .2, 20.4 + oz]; t = [cxw + ox, 0, 8.8 + oz * .5]; }
    cam.p = p; cam.F = nrm(sub(t, p)); cam.R = nrm(cross(cam.F, [0, 1, 0])); cam.U = cross(cam.R, cam.F);
  }
  function proj(w) {
    var d = sub(w, cam.p), z = dot(d, cam.F);
    return { x: cx0 + dot(d, cam.R) / z * foc, y: cy0 - dot(d, cam.U) / z * foc, z: z, s: foc / z };
  }
  function depthAt(px, py) {
    var a = (px - cx0) / foc, b = (cy0 - py) / foc;
    var d = nrm([cam.F[0] + cam.R[0] * a + cam.U[0] * b, cam.F[1] + cam.R[1] * a + cam.U[1] * b, cam.F[2] + cam.R[2] * a + cam.U[2] * b]);
    if (d[1] > -.01) return 24; var t = -cam.p[1] / d[1]; return Math.min(24, t * dot(d, cam.F));
  }
  var REST = CFG.rest, focus = REST, focusT = REST, started = false;
  function ap() { var a = touch ? CFG.dof * .6 : CFG.dof; return narrow ? Math.min(a, 3.6) : a; }
  function maxc() { return ap() * .9 + .4; }
  function coc(z) { return Math.min(maxc(), ap() * Math.abs(z - focus) / z); }

  // ---- GL: one full-screen pass draws paper, fog, the ink layer and depth of field
  var VS = "#version 300 es\nin vec2 a;void main(){gl_Position=vec4(a,0.,1.);}";
  var FS = "#version 300 es\nprecision highp float;uniform sampler2D uTex,uInk,uDyn;uniform vec3 uCam,uR,uU,uF,uPaper,uBg,uP00,uP10,uP01,uP11;" +
    "uniform float uLight,uFoc,uFocus,uAp,uMax,uDpr,uW,uH,uMir,uTaps;uniform vec2 uFog;uniform vec2 uRes,uC0;out vec4 o;\n" +
    "vec3 tn(vec3 t,vec2 uv){vec2 q=clamp(uv,0.,1.);vec3 pp=mix(mix(uP00,uP10,q.x),mix(uP01,uP11,q.x),q.y);return uLight>.5?t*(uPaper/pp):uPaper+(t-pp)*1.45;}\n" +
    "float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}\n" +
    "vec4 shade(vec2 px,float lod){float x=px.x/uDpr,y=(uRes.y-px.y)/uDpr;" +
    "vec3 d=normalize(uF+uR*(x-uC0.x)/uFoc+uU*(uC0.y-y)/uFoc);if(d.y>-.002)return vec4(uBg,1000.);\n" +
    "float t=-uCam.y/d.y;vec3 p=uCam+d*t;float z=dot(p-uCam,uF);vec2 uv=p.xz/vec2(20.48,15.36);\n" +
    "vec2 e=smoothstep(vec2(0.),vec2(.08,.16),uv)*smoothstep(vec2(0.),vec2(.08,.16),1.-uv);float m=e.x*e.y;\n" +
    "float fp=z/uFoc*100.*sqrt(max(1.,z/uCam.y));float L=log2(max(fp,1.))+lod;vec2 pv=vec2(mix(uv.x,1.-uv.x,uMir),uv.y);vec3 c=mix(uPaper,tn(textureLod(uTex,pv,L).rgb,pv),m);" +
    "vec4 k=textureLod(uInk,uv,max(L-1.,0.))*m;c=c*(1.-k.a)+k.rgb;vec4 k2=texture(uDyn,uv)*m;c=c*(1.-k2.a)+k2.rgb;\n" +
    "c=mix(c,uBg,smoothstep(uFog.x,uFog.y,z));c=mix(uBg,c,smoothstep(.0,.085,-d.y));return vec4(c,z);}\n" +
    "void main(){vec2 px=gl_FragCoord.xy;vec4 s=shade(px,0.);float z=s.a;float c=z>900.?0.:min(uMax,uAp*abs(z-uFocus)/z)*uDpr;vec3 col=s.rgb;\n" +
    "if(c>.7){vec3 a=vec3(0.);float lod=log2(max(c*.3,1.));float rot=hash(px+7.)*6.2832;for(int i=0;i<18;i++){if(float(i)>=uTaps)break;float fi=float(i)+.5;float r=sqrt(fi/uTaps)*c;float th=fi*2.39996+rot;a+=shade(px+r*vec2(cos(th),sin(th)),lod).rgb;}col=a/uTaps;}\n" +
    // the edges of the canvas melt into the page
    "float x=px.x/uDpr,y=(uRes.y-px.y)/uDpr;float ef=smoothstep(0.,44.,min(x,uW-x))*smoothstep(0.,44.,min(y,uH-y));col=mix(uBg,col,ef);\n" +
    "col+=(hash(px)-.5)*.012;o=vec4(col,1.);}";
  function shd(t, s) { var x = gl.createShader(t); gl.shaderSource(x, s); gl.compileShader(x); if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); return x; }
  var pr = gl.createProgram();
  try { gl.attachShader(pr, shd(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, shd(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr); if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error("link"); }
  catch (err) { bail(); return; }
  gl.useProgram(pr);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  var aLoc = gl.getAttribLocation(pr, "a"); gl.enableVertexAttribArray(aLoc); gl.vertexAttribPointer(aLoc, 2, gl.FLOAT, false, 0, 0);
  var U = {};
  ["uTex", "uInk", "uDyn", "uCam", "uR", "uU", "uF", "uPaper", "uBg", "uP00", "uP10", "uP01", "uP11", "uLight", "uFoc", "uFocus", "uAp", "uMax", "uDpr", "uW", "uH", "uRes", "uC0", "uMir", "uTaps", "uFog"].forEach(function (n) { U[n] = gl.getUniformLocation(pr, n); });
  function newTex() {
    var t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE); return t;
  }
  var TEX = {}, PAPER = {}, inkTex = newTex(), dynTex = newTex();
  gl.bindTexture(gl.TEXTURE_2D, dynTex); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  var ink = document.createElement("canvas"); ink.width = 1024; ink.height = 768; var ix = ink.getContext("2d");
  var dyn = document.createElement("canvas"); dyn.width = 512; dyn.height = 384; var dx = dyn.getContext("2d");
  function upload(name, img) {
    // the paper's own tone at the four corners: the shader flattens the generated sheet's lighting with it
    var c = document.createElement("canvas"); c.width = c.height = 8; var x = c.getContext("2d"), w = img.naturalWidth, h = img.naturalHeight;
    var tone = [[.03, .03], [.87, .03], [.03, .87], [.87, .87]].map(function (o) {
      x.drawImage(img, w * o[0], h * o[1], w * .1, h * .1, 0, 0, 8, 8);
      var d = x.getImageData(0, 0, 8, 8).data, r = 0, g = 0, b = 0; for (var i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
      return [r / 64 / 255, g / 64 / 255, b / 64 / 255];
    });
    var t = newTex(); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, img); gl.generateMipmap(gl.TEXTURE_2D);
    PAPER[name] = tone; TEX[name] = t;
  }

  // ---- theme: the page's own (data-theme, else the system)
  function isDark() { var t = document.documentElement.getAttribute("data-theme"); if (t) return t === "dark"; return !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches); }
  var mode = isDark() ? "dark" : "light";
  function bgCol() { return mode === "dark" ? [.059, .059, .059] : [1, 1, 1]; }
  function paperCol() { return mode === "dark" ? [.135, .137, .14] : [.985, .985, .985]; }

  // ---- models
  function mk(cls, tag) { var e = document.createElement(tag || "div"); e.className = cls; ov.appendChild(e); return e; }
  var models = MODELS.map(function (t) { var e = mk("gvsp", "img"); e.alt = ""; e.decoding = "async"; return { p: [t[0], t[1]], s: [t[0], t[1]], h: t[2], k: t[3], el: e, seed: t[0] * 7 + t[1] * 13 }; });
  function placeModels() { models.forEach(function (t) { t.s = [lefty ? 2048 - t.p[0] : t.p[0], t.p[1]]; }); }
  placeModels();
  var flag = mk("gvsp", "img"); flag.alt = "";
  var ball = mk("gvball");
  function crown(t) { var e = t.el, a = e.naturalWidth ? e.naturalWidth / e.naturalHeight : .8; return t.h * a * 50; }

  // ---- state
  var flight = null, landedK = null, ballS = S(TEE[0], TEE[1]), ballH = 0, rings = [], trail = [], trailA = 0;
  var inkDirty = true, staticDirty = true, raf = 0, userFocus = true, mouseFocus = false, ready = false, live = false, visible = true;
  var dots = Array.prototype.slice.call(bf.querySelectorAll(".bfd"));

  // ---- the ink layer: what lies on the paper itself (shadows, plan marks under each model, the rings of tee shot and landing)
  function shadow(s, r, a) {
    if (r <= 0) return; var k = .5, g = ix.createRadialGradient(s[0] * k, s[1] * k, 0, s[0] * k, s[1] * k, r * k);
    g.addColorStop(0, "rgba(0,0,0," + a + ")"); g.addColorStop(.6, "rgba(0,0,0," + a * .6 + ")"); g.addColorStop(1, "rgba(0,0,0,0)");
    ix.fillStyle = g; ix.beginPath(); ix.arc(s[0] * k, s[1] * k, r * k, 0, 7); ix.fill();
  }
  function planMark(t, pen, dark) {
    var k = .5, r = crown(t) * (t.k >= 5 && t.k <= 6 ? .7 : .74), x = t.s[0] * k, y = t.s[1] * k, rnd = t.seed;
    function rn() { rnd = (rnd * 9301 + 49297) % 233280; return rnd / 233280; }
    ix.save(); ix.strokeStyle = pen; ix.globalAlpha = dark ? .6 : .62; ix.lineWidth = .8; ix.lineCap = "round"; ix.lineJoin = "round";
    if (t.k >= 5 && t.k <= 6) {
      for (var i = 0; i < 5; i++) { var a = -Math.PI / 2 + (i - 2) * .38 + (rn() - .5) * .2, l = r * k * (.55 + rn() * .5), bx = x + (i - 2) * r * k * .22; ix.beginPath(); ix.moveTo(bx, y); ix.lineTo(bx + Math.cos(a) * l, y + Math.sin(a) * l); ix.stroke(); }
    } else {
      var n = t.k >= 7 ? 9 : 12, rr = r * k, px1 = 0, py1 = 0; ix.beginPath();
      for (var j = 0; j <= n; j++) {
        var a0 = j / n * Math.PI * 2, a1 = (j + .5) / n * Math.PI * 2, p0 = rr * (.92 + rn() * .1), p1 = rr * (1.1 + rn() * .1);
        var X0 = x + Math.cos(a0) * p0, Y0 = y + Math.sin(a0) * p0;
        if (!j) ix.moveTo(X0, Y0); else ix.quadraticCurveTo(px1, py1, X0, Y0);
        px1 = x + Math.cos(a1) * p1; py1 = y + Math.sin(a1) * p1;
      }
      ix.closePath(); ix.stroke(); ix.beginPath(); ix.arc(x, y, 1.1, 0, 7); ix.fillStyle = pen; ix.fill();
      ix.globalAlpha = dark ? .45 : .35; ix.strokeStyle = dark ? "#9cae6a" : "#7c9a4a"; ix.lineWidth = rr * .5;
      ix.beginPath(); ix.moveTo(x - rr * .55, y + rr * .25); ix.lineTo(x + rr * .45, y - rr * .3); ix.stroke();
    }
    ix.restore();
  }
  function drawStatic() {
    var k = .5, dark = mode === "dark", pen = dark ? "#f3f3ef" : "#161616", sa = dark ? .5 : .2;
    ix.clearRect(0, 0, 1024, 768);
    models.forEach(function (t) {
      var r = crown(t);
      ix.save(); ix.translate((t.s[0] + t.h * 30) * k, (t.s[1] + t.h * 18) * k); ix.scale(1.6, 1); shadow([0, 0], r * .95, sa * .8); ix.restore();
      ix.save(); ix.translate(t.s[0] * k, t.s[1] * k); ix.scale(1.25, .8); shadow([0, 0], r * .55, dark ? .75 : .42); ix.restore();
    });
    models.forEach(function (t) { planMark(t, pen, dark); });
    var c = S(CUP[0], CUP[1]); ix.strokeStyle = "rgba(0,0,0," + sa * .8 + ")"; ix.lineWidth = 1.6; ix.lineCap = "round";
    ix.beginPath(); ix.moveTo(c[0] * k, c[1] * k); ix.lineTo((c[0] + FLAG_H * 80) * k, (c[1] + FLAG_H * 50) * k); ix.stroke();
    gl.bindTexture(gl.TEXTURE_2D, inkTex); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, ink); gl.generateMipmap(gl.TEXTURE_2D);
  }
  function drawDyn() {  // a quarter-size layer: the ball's shadow and the rings
    var k = .25, dark = mode === "dark", b = [ballS[0] + ballH * 55, ballS[1] + ballH * 34], r = (15 + ballH * 7) * k, a = (dark ? .6 : .32) / (1 + ballH * 1.1);
    dx.clearRect(0, 0, 512, 384);
    rings.forEach(function (g) { var t = 1 - g.t; dx.beginPath(); dx.arc(g.s[0] * k, g.s[1] * k, (14 + g.t * 46) * k, 0, 7); dx.lineWidth = 1.2 * t + .3; dx.strokeStyle = dark ? "rgba(243,243,239," + .7 * t + ")" : "rgba(22,22,22," + .55 * t + ")"; dx.stroke(); });
    var gr = dx.createRadialGradient(b[0] * k, b[1] * k, 0, b[0] * k, b[1] * k, r); gr.addColorStop(0, "rgba(0,0,0," + a + ")"); gr.addColorStop(.6, "rgba(0,0,0," + a * .6 + ")"); gr.addColorStop(1, "rgba(0,0,0,0)");
    dx.fillStyle = gr; dx.beginPath(); dx.arc(b[0] * k, b[1] * k, r, 0, 7); dx.fill();
    gl.bindTexture(gl.TEXTURE_2D, dynTex); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, dyn);
  }

  // ---- layout: where the stage sits, and the camera that puts the hole where the finder box is
  function rel(el) { var a = el.getBoundingClientRect(), b = welcome.getBoundingClientRect(); return { x: a.left - b.left, y: a.top - b.top, w: a.width, h: a.height }; }
  var lastSig = "";
  // phones: the finder box ends above the bottom of the visible screen (room for Safari's floating bar); set once per
  // width, so the toolbar collapsing while scrolling does not resize it
  function phoneBox(force) {
    var w = document.documentElement.clientWidth;
    if (window.innerWidth >= 760) { if (phoneW) { bfc.style.height = ""; phoneW = 0; } return; }
    if (w === phoneW && !force) return;
    // after a turn the width updates before the height: measure again once the turn has settled
    if (w !== phoneW && phoneW) setTimeout(function () { phoneBox(true); if (ready) size(true); }, 400);
    phoneW = w;
    var vh = window.visualViewport ? Math.min(window.innerHeight, window.visualViewport.height) : window.innerHeight;
    var top = bfc.getBoundingClientRect().top + window.scrollY, h = Math.round(vh - top - 84);
    bfc.style.height = Math.max(360, Math.min(w * 1.5, 640, h)) + "px";
  }
  function size(force) {
    phoneBox();
    var wide = window.innerWidth >= 1200, box = rel(bfc), sx, sy, sw, sh;
    narrow = !wide; var ph = window.innerWidth < 760;
    if (ph !== phone) { phone = ph; Object.keys(MISS).forEach(function (k) { MISS[k].c = phone ? MISS[k].cn : MISS[k].cw; }); var le = landedK ? MISS[landedK].c[MISS[landedK].c.length - 1] : TEE; if (!flight) { ballS = S(le[0], le[1]); ballH = 0; } }
    if (wide) {  // the whole width of the page column, from the top of the welcome block to below the finder box
      var main = (welcome.closest(".main") || welcome.parentNode).getBoundingClientRect(), wb = welcome.getBoundingClientRect();
      sx = main.left - wb.left; sw = main.width; sy = 0; sh = Math.max(box.y + box.h + 40, Math.min(800, Math.max(560, sw * .52)));
    } else if (phone) {  // the stage runs edge to edge from the top of the welcome block, the headline stands on the paper
      var wb3 = welcome.getBoundingClientRect(); sx = -wb3.left; sw = document.documentElement.clientWidth; sy = 0; sh = box.y + box.h + 24;
    } else { sx = box.x; sy = box.y; sw = box.w; sh = box.h; }
    var sig = [wide, sx, sy, sw, sh, box.x, box.y, box.w, box.h, lefty, window.devicePixelRatio].map(function (v) { return typeof v === "number" ? Math.round(v) : v; }).join();
    if (sig === lastSig && !force) return; lastSig = sig;
    W = Math.max(1, sw); H = Math.max(1, sh);
    st.style.left = sx + "px"; st.style.top = sy + "px"; st.style.width = W + "px"; st.style.height = H + "px";
    offX = sx - box.x; offY = sy - box.y;
    dpr = Math.min(touch ? 1.25 : 1.35, window.devicePixelRatio || 1);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); trc.width = cv.width; trc.height = cv.height;
    gl.viewport(0, 0, cv.width, cv.height);
    // the headline's box in canvas px: models behind the text step back so it stays readable
    var fh = welcome.querySelector(".fh"); textBox = null; textRight = 0;
    if ((wide || phone) && fh) {
      // where the words end, not the column: the right edge of the headline's and the line under it's line boxes
      var rg = document.createRange(), wb2 = welcome.getBoundingClientRect(), y0 = 1e9, y1 = -1e9; rg.selectNodeContents(fh);
      Array.prototype.forEach.call(rg.getClientRects(), function (r) { if (!r.width) return; textRight = Math.max(textRight, r.right - wb2.left - sx); y0 = Math.min(y0, r.top - wb2.top - sy); y1 = Math.max(y1, r.bottom - wb2.top - sy); });
      if (textRight) textBox = { x1: textRight + 24, y0: y0 - 16, y1: y1 + 16 };
    }
    boxC = { x: box.x - sx, y: box.y - sy, w: box.w, h: box.h };
    if (wide) frameWide(); else fit(box.x - sx, box.y - sy, box.w, box.h);
    inkDirty = staticDirty = true; if (ready) frame(performance.now());
  }
  var foc0 = 500, ans = 0, ansT = 0, textBox = null, textRight = 0, base0 = null, base1 = null, boxC = null, phoneW = 0;
  function frameWide() {  // a centred pinhole with the prototype's field of view (tan .36 of half the height)
    foc0 = H / 2 / .36;
    var keepPar = par, keepOff = camOff; par = [0, 0]; camOff = [0, 0]; setCam();
    var A = Object.keys(MISS).map(function (k) { var c = MISS[k].c, e = c[c.length - 1], d = sub(Wd(S(e[0], e[1])), cam.p); return dot(d, cam.R) / dot(d, cam.F); });
    var amin = Math.min.apply(null, A), amax = Math.max.apply(null, A);
    // no dot or label may touch the words on the left (or, with an answer showing, the answer's column); shrink if it must
    function bounds(left) { var L = left + 60, R = W - 80, f = Math.min(foc0, (R - L) / (amax - amin)), c = W / 2; if (c + amin * f < L) c = L - amin * f; if (c + amax * f > R) c = R - amax * f; return [f, c]; }
    base0 = bounds(textRight || W * .3).concat([H / 2]);
    // with an answer showing, the hole fits the finder box under the question (the answer has the left column)
    base1 = boxC.w > 40 && boxC.h > 40 ? fit(boxC.x, boxC.y, boxC.w, boxC.h, true) : base0.slice();
    if (base1[0] > base0[0]) base1[0] = base0[0];  // the hole never grows when the answer opens
    par = keepPar; camOff = keepOff; applyAns(); setCam();
    REST = proj(Wd(S(CUP[0], CUP[1]), FLAG_H * .5)).z; if (userFocus && !flight && !landedK && !mouseFocus) { focusT = REST; if (!started) { focus = reduce ? REST : REST * .55; started = true; } }
  }
  // When the answer takes the headline's place, the hole steps right and a little back so the video does not cover it.
  function applyAns() { if (!base0) return; var e = ans * ans * (3 - 2 * ans); foc = base0[0] + (base1[0] - base0[0]) * e; cx0 = base0[1] + (base1[1] - base0[1]) * e; cy0 = base0[2] + (base1[2] - base0[2]) * e; }
  // The pin top, the tee and the six landing spots must fit the box (bx, by, bw, bh in canvas px), with room for labels.
  function fit(bx, by, bw, bh, onlyCompute) {
    var keepPar = par, keepOff = camOff; par = [0, 0]; camOff = [0, 0]; setCam();
    var pts = [Wd(S(CUP[0], CUP[1]), FLAG_H), Wd(S(TEE[0], TEE[1]))];
    Object.keys(MISS).forEach(function (k) { var c = MISS[k].c, e = c[c.length - 1]; pts.push(Wd(S(e[0], e[1]))); });
    var A = pts.map(function (w) { var d = sub(w, cam.p), z = dot(d, cam.F); return [dot(d, cam.R) / z, dot(d, cam.U) / z]; });
    var a0 = Math.min.apply(null, A.map(function (v) { return v[0]; })), a1 = Math.max.apply(null, A.map(function (v) { return v[0]; }));
    var b0 = Math.min.apply(null, A.map(function (v) { return v[1]; })), b1 = Math.max.apply(null, A.map(function (v) { return v[1]; }));
    var mx = phone ? .15 : .12, mtop = phone ? .1 : narrow ? .08 : .1, mbot = phone ? .08 : narrow ? .1 : .08;
    var f = Math.min(bw * (1 - 2 * mx) / (a1 - a0), bh * (1 - mtop - mbot) / (b1 - b0));
    var r = [f, bx + bw / 2 - (a0 + a1) / 2 * f, by + bh * mtop + (bh * (1 - mtop - mbot) - (b1 - b0) * f) / 2 + b1 * f];
    if (onlyCompute) { par = keepPar; camOff = keepOff; return r; }
    foc = r[0]; cx0 = r[1]; cy0 = r[2];
    par = keepPar; camOff = keepOff;
    REST = proj(Wd(S(CUP[0], CUP[1]), FLAG_H * .5)).z; if (userFocus && !flight && !landedK && !mouseFocus) { focusT = REST; if (!started) { focus = reduce ? REST : REST * .55; started = true; } }
  }

  // ---- pointer: the focus goes to what the pointer is on (a model, the ball, else the paper); the scene leans a little
  var alphaMaps = new Map();
  function alphaAt(img, u, v) {
    var m = alphaMaps.get(img.src);
    if (!m) {
      if (!img.naturalWidth) return 0;
      var c = document.createElement("canvas"), w = Math.min(256, img.naturalWidth), h = Math.round(w * img.naturalHeight / img.naturalWidth); c.width = w; c.height = h;
      var x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(img, 0, 0, w, h); m = { w: w, h: h, d: x.getImageData(0, 0, w, h).data }; alphaMaps.set(img.src, m);
    }
    var px = Math.floor(u * m.w), py = Math.floor(v * m.h); if (px < 0 || py < 0 || px >= m.w || py >= m.h) return 0; return m.d[(py * m.w + px) * 4 + 3];
  }
  function objectDepthAt(cx, cy) {
    var best = null, sr = st.getBoundingClientRect();
    models.concat([{ el: flag, s: S(CUP[0], CUP[1]), h: FLAG_H }]).forEach(function (t) {
      var r = t.el.getBoundingClientRect(), x = cx + sr.left, y = cy + sr.top;
      if (x < r.left || x > r.right || y < r.top || y > r.bottom) return;
      var u = (x - r.left) / r.width;
      if (alphaAt(t.el, u, (y - r.top) / r.height) < 60) return;
      var z = proj(Wd(t.s, t.h * (1 - (y - r.top) / r.height))).z; if (best === null || z < best) best = z;
    });
    var bp = proj(Wd(ballS, .13 + ballH)); if (Math.hypot(cx - bp.x, cy - bp.y) < .13 * bp.s * 1.4 && (best === null || bp.z < best)) best = bp.z;
    return best;
  }
  welcome.addEventListener("pointermove", function (e) {
    if (!ready || e.pointerType === "touch") return;
    var r = st.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    if (x < 0 || y < 0 || x > W || y > H) return;
    if (!reduce) parT = [x / W - .5, .5 - y / H];
    if (userFocus && !flight && !hoverK) { var oz = objectDepthAt(x, y); focusT = oz !== null ? oz : REST; mouseFocus = oz !== null; }
    kick();
  });
  welcome.addEventListener("pointerleave", function () { parT = [0, 0]; mouseFocus = false; if (!flight && !landedK && !hoverK) { focusT = REST; userFocus = true; } kick(); });
  var hoverK = null;
  function spotZ(k) { var m = MISS[k]; return proj(Wd(S(m.c[m.c.length - 1][0], m.c[m.c.length - 1][1]))).z; }
  dots.forEach(function (d) {
    var k = d.dataset.k; if (!MISS[k]) return;
    function on() { if (flight || !live) return; hoverK = k; focusT = spotZ(k); userFocus = false; kick(); }
    function off() { if (hoverK !== k) return; hoverK = null; userFocus = true; if (!landedK) focusT = REST; kick(); }
    d.addEventListener("mouseenter", on); d.addEventListener("mouseleave", off); d.addEventListener("focus", on); d.addEventListener("blur", off);
  });
  new MutationObserver(function () { kick(); }).observe(welcome, { attributes: true, attributeFilter: ["class"] });  // .ans
  new MutationObserver(function () {
    var l = bf.classList.contains("lh"); if (l === lefty) return;
    lefty = l; placeModels(); trail = []; trailA = 0; rings = [];
    var e = landedK ? MISS[landedK].c[MISS[landedK].c.length - 1] : TEE; ballS = S(e[0], e[1]); ballH = 0;
    staticDirty = true; if (ready) size(true);
  }).observe(bf, { attributes: true, attributeFilter: ["class"] });

  // ---- the shot: drag on the way out, a late apex, two hops and a roll; the focus and the camera ride with the ball
  function fly(k, done) {
    var m = MISS[k]; if (!m || !ready) { done(); return; }
    camRet = null; hoverK = null; landedK = null; flight = null;
    if (reduce || !visible || document.hidden) { var e = at(m, 1); ballS = S(e[0], e[1]); ballH = 0; landedK = k; focusT = spotZ(k); inkDirty = true; kick(); done(); return; }
    var end = m.c[m.c.length - 1], len = Math.hypot(end[0] - TEE[0], end[1] - TEE[1]) / 100;
    flight = { k: k, m: m, t0: performance.now(), carry: (900 + len * 190) * m.fly.t / CFG.speed, done: done };
    flight.guard = setTimeout(function () { if (flight && flight.k === k) land(); }, 7000);
    trail = []; trailA = 1; rings.push({ s: S(TEE[0], TEE[1]), t: 0 }); userFocus = false; kick();
  }
  function finish() {
    var f = flight; if (!f) return; flight = null; clearTimeout(f.guard); landedK = f.k; camRet = { from: camOff.slice(), t0: performance.now() + 750, dur: 2300 };
    focusT = proj(Wd(ballS)).z; inkDirty = true; kick(); f.done();
  }

  function land() {  // put the ball down at once (a hidden tab, a lost context, a stalled loop) and give app.js its answer
    if (!flight) return; var e = at(flight.m, 1); ballS = S(e[0], e[1]); ballH = 0; trail = []; trailA = 0; camOff = [0, 0]; camOffT = [0, 0]; finish();
  }
  document.addEventListener("visibilitychange", function () { if (document.hidden && flight) land(); });
  var trx = trc.getContext("2d");
  function drawTrail() {
    trx.setTransform(1, 0, 0, 1, 0, 0); trx.clearRect(0, 0, trc.width, trc.height); if (trailA <= 0 || trail.length < 2) return;
    trx.setTransform(dpr, 0, 0, dpr, 0, 0); var col = mode === "dark" ? "62,207,142" : "11,122,75"; trx.lineCap = "round"; trx.lineJoin = "round";
    var pts = trail.map(function (p) { return proj(Wd([p[0], p[1]], p[2] + .13)); });
    [[9, .10], [4, .22], [1.8, .95]].forEach(function (w) {
      trx.beginPath(); pts.forEach(function (p, i) { if (i) trx.lineTo(p.x, p.y); else trx.moveTo(p.x, p.y); });
      trx.lineWidth = w[0]; trx.strokeStyle = "rgba(" + col + "," + (w[1] * trailA) + ")"; trx.stroke();
    });
  }
  function stand(e, s, h, ax, sink) {
    var b = proj(Wd(s)), top = proj(Wd(s, h)), ph = b.y - top.y, r = e.naturalWidth ? e.naturalHeight / e.naturalWidth : 1.3, pw = ph / r, bl = coc(proj(Wd(s, h * .5)).z);
    e.style.width = pw.toFixed(1) + "px"; e.style.transform = "translate(" + (b.x - pw * ax).toFixed(1) + "px," + (b.y - ph * (1 - sink)).toFixed(1) + "px)";
    e.style.filter = bl > .4 ? "blur(" + bl.toFixed(1) + "px)" : "none"; e.style.zIndex = Math.round(2000 - b.z * 20);
    // like the paper, a model fades out towards the stage's edges instead of being cut off
    var op = Math.max(0, Math.min(1, (Math.min(b.x, W - b.x) - 8) / 64, (b.y - 20) / 48, (H - b.y) / 48));
    if (textBox && !welcome.classList.contains("ans") && b.x - pw / 2 < textBox.x1 && b.y > textBox.y0 && b.y - ph * .6 < textBox.y1) op *= .18;
    for (var si = 0; si < spotScr.length; si++) { var q = spotScr[si]; if (q.z > b.z && q.x > b.x - pw * .45 - 50 && q.x < b.x + pw * .45 + 50 && q.y > b.y - ph - 8 && q.y < b.y + 34) { op *= .22; break; } }
    e.style.opacity = op.toFixed(2);
  }
  var spotScr = [];
  function layout() {
    spotScr = Object.keys(MISS).map(function (k) { var c = MISS[k].c, e = c[c.length - 1]; return proj(Wd(S(e[0], e[1]))); });
    models.forEach(function (t) { stand(t.el, t.s, t.h, .5, t.k >= 5 && t.k <= 6 ? .07 : t.k >= 7 ? .05 : .015); });
    stand(flag, S(CUP[0], CUP[1]), FLAG_H, .06, .01);
    var bp = proj(Wd(ballS, .13 + ballH)), br = .13 * bp.s, bl = coc(bp.z);
    ball.style.width = ball.style.height = (2 * br).toFixed(1) + "px";
    ball.style.transform = "translate(" + (bp.x - br).toFixed(1) + "px," + (bp.y - br).toFixed(1) + "px)";
    ball.style.filter = bl > .4 ? "blur(" + bl.toFixed(1) + "px)" : "none"; ball.style.zIndex = Math.round(2000 - bp.z * 20) + 1;
    // the finder's own dots follow the drawing: their place on the paper, in the finder box's coordinates
    if (live) dots.forEach(function (d) {
      var m = MISS[d.dataset.k]; if (!m) return; var e = m.c[m.c.length - 1], p = proj(Wd(S(e[0], e[1])));
      d.style.left = (offX + p.x).toFixed(1) + "px"; d.style.top = (offY + p.y).toFixed(1) + "px";
    });
  }

  function kick() { if (!raf && ready && visible) raf = requestAnimationFrame(frame); }
  function frame(now) {
    raf = 0; try { step(now); } catch (err) { teardown(); }
  }
  function step(now) {
    var busy = false;
    if (flight) {
      var f = flight, m = f.m, P = m.fly, el = Math.max(0, now - f.t0), LAND = P.land, REM = 1 - LAND, u, h = 0, peak = P.pk * CFG.height,
        bh = Math.max(.07, peak * .13) * P.b, B1 = 280 * Math.min(1.3, P.b) / CFG.speed, B2 = 170 * Math.min(1.3, P.b) / CFG.speed, ROLL = (260 + REM * 1400) / CFG.speed, over = false;
      if (el < f.carry) { var t = el / f.carry, sd = (1 - Math.exp(-1.9 * t)) / (1 - Math.exp(-1.9)), q = Math.pow(sd, P.ap); u = LAND * sd; h = peak * 4 * q * (1 - q); }
      else {
        var r = el - f.carry;
        if (!f.hit) { f.hit = 1; var lp = at(m, LAND); rings.push({ s: S(lp[0], lp[1]), t: 0 }); }
        if (r < B1) { var b = r / B1; u = LAND + REM * .45 * b; h = bh * 4 * b * (1 - b); }
        else if (r < B1 + B2) { var b2 = (r - B1) / B2; u = LAND + REM * (.45 + .2 * b2); h = bh * .35 * 4 * b2 * (1 - b2); }
        else { var rr = Math.min(1, (r - B1 - B2) / ROLL); u = LAND + REM * (.65 + .35 * (1 - Math.pow(1 - rr, 2.2))); over = rr >= 1; }
      }
      var q2 = at(m, u), tee = S(TEE[0], TEE[1]); ballS = S(q2[0], q2[1]); ballH = h; inkDirty = true;
      focusT = proj(Wd(ballS, ballH)).z; focus += (focusT - focus) * .32;
      camOffT = [(ballS[0] - tee[0]) / 100 * .16, -Math.min(1.1, (tee[1] - ballS[1]) / 100 * .12)];
      trail.push([ballS[0], ballS[1], ballH]); busy = true;
      if (over) finish();
    }
    if (!flight && trailA > .4 && landedK) { trailA = Math.max(.4, trailA - .012); busy = true; }
    for (var gi = rings.length - 1; gi >= 0; gi--) { rings[gi].t += .04; inkDirty = true; busy = true; if (rings[gi].t >= 1) rings.splice(gi, 1); }
    if (camRet) {
      var rp = Math.max(0, Math.min(1, (now - camRet.t0) / camRet.dur)), re = rp < .5 ? 4 * rp * rp * rp : 1 - Math.pow(-2 * rp + 2, 3) / 2;
      camOff = [camRet.from[0] * (1 - re), camRet.from[1] * (1 - re)]; camOffT = camOff.slice(); if (rp >= 1) { camRet = null; camOff = [0, 0]; camOffT = [0, 0]; } busy = true;
    } else for (var ci = 0; ci < 2; ci++) { var dc = camOffT[ci] - camOff[ci]; if (Math.abs(dc) > .002) { camOff[ci] += dc * (reduce ? 1 : .06); busy = true; } }
    var df = focusT - focus; if (Math.abs(df) > .01) { focus += df * (reduce ? 1 : (mouseFocus && userFocus ? .2 : .085)); busy = true; } else focus = focusT;
    for (var i = 0; i < 2; i++) { var dp = parT[i] - par[i]; if (Math.abs(dp) > .002) { par[i] += dp * (reduce ? 1 : CFG.ease); busy = true; } }
    if (!narrow) { ansT = welcome.classList.contains("ans") ? 1 : 0; var da = ansT - ans; if (Math.abs(da) > .002) { ans += da * (reduce ? 1 : .06); busy = true; } else ans = ansT; applyAns(); }
    setCam();
    if (staticDirty) { drawStatic(); staticDirty = false; }
    if (inkDirty) { drawDyn(); inkDirty = false; }
    var pc = PAPER[mode], bg = bgCol();
    gl.useProgram(pr);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, TEX[mode]); gl.uniform1i(U.uTex, 0);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, inkTex); gl.uniform1i(U.uInk, 1);
    gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, dynTex); gl.uniform1i(U.uDyn, 2); gl.activeTexture(gl.TEXTURE0);
    gl.uniform3fv(U.uCam, cam.p); gl.uniform3fv(U.uR, cam.R); gl.uniform3fv(U.uU, cam.U); gl.uniform3fv(U.uF, cam.F);
    gl.uniform3fv(U.uPaper, paperCol()); gl.uniform3fv(U.uBg, bg); gl.uniform3fv(U.uP00, pc[0]); gl.uniform3fv(U.uP10, pc[1]); gl.uniform3fv(U.uP01, pc[2]); gl.uniform3fv(U.uP11, pc[3]);
    gl.uniform1f(U.uLight, mode === "light" ? 1 : 0); gl.uniform2f(U.uRes, cv.width, cv.height);
    gl.uniform1f(U.uFoc, foc); gl.uniform2f(U.uC0, cx0, cy0); gl.uniform1f(U.uFocus, focus); gl.uniform1f(U.uAp, ap()); gl.uniform1f(U.uMax, maxc()); gl.uniform1f(U.uDpr, dpr);
    gl.uniform1f(U.uW, W); gl.uniform1f(U.uH, H); gl.uniform1f(U.uMir, lefty ? 1 : 0); gl.uniform1f(U.uTaps, touch ? 10 : 18); gl.uniform2f(U.uFog, narrow ? 26 : 16, narrow ? 56 : 40);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    layout(); drawTrail();
    if (busy) kick();
  }

  // ---- loading: the paper for the current theme and every model, then the stage replaces the drawn hole
  function loadImg(s) { return new Promise(function (ok, no) { var im = new Image(); im.decoding = "async"; im.onload = function () { ok(im); }; im.onerror = no; im.src = s; }); }
  function loadPaper(name) { return TEX[name] ? Promise.resolve() : loadImg(src("paper-" + name)).then(function (im) { upload(name, im); }); }
  function setTheme() {
    var m = isDark() ? "dark" : "light"; if (m === mode && TEX[m]) return;
    loadPaper(m).then(function () { mode = m; inkDirty = staticDirty = true; kick(); }, function () {});
  }
  function teardown() {
    if (flight) { var f = flight; flight = null; clearTimeout(f.guard); try { f.done(); } catch (err) {} }
    ready = false; live = false; window.gvStage = null; welcome.classList.remove("gvon"); bail(); if (st.parentNode) st.remove();
    dots.forEach(function (d) { d.style.left = ""; d.style.top = ""; }); bfc.style.height = "";
  }
  var uniq = {}; SPR.forEach(function (n) { uniq[n] = 1; });
  function start() {
    if (bf.classList.contains("used")) { bail(); return; }  // the visitor is already on an answer: leave the drawn hole
    var spr = Object.keys(uniq).concat(["flag"]);
    Promise.all([loadPaper(mode)].concat(spr.map(function (n) { return loadImg(src(n)); }))).then(function (imgs) {
      try {
        if (bf.classList.contains("used")) { bail(); return; }
        var bySrc = {}; spr.forEach(function (n, i) { bySrc[n] = imgs[i + 1].src; });
        models.forEach(function (t) { t.el.src = bySrc[SPR[t.k]]; }); flag.src = bySrc.flag;
        welcome.insertBefore(st, welcome.firstChild);
        ready = true; size(true);
        var goLive = function () {
          if (live || !ready || gaveUp) return;
          if (bf.classList.contains("used")) { teardown(); return; }
          clearTimeout(giveUp); live = true; welcome.classList.add("gvon"); window.gvStage = { on: true, fly: fly }; kick();
        };
        st.addEventListener("transitionend", goLive, { once: true }); setTimeout(goLive, reduce ? 0 : 700);
        requestAnimationFrame(function () { st.classList.add("in"); });
        if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { phoneBox(true); if (ready) size(true); });
        window.addEventListener("orientationchange", function () { setTimeout(function () { phoneBox(true); if (ready) size(true); }, 400); });  // the headline's real width
        if ("ResizeObserver" in window) new ResizeObserver(function () { if (ready) size(); }).observe(welcome); else window.addEventListener("resize", function () { if (ready) size(); });
        if ("IntersectionObserver" in window) new IntersectionObserver(function (es) { visible = es[0].isIntersecting; if (visible) kick(); }).observe(st);
        new MutationObserver(setTheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
        if (window.matchMedia) { var mq = matchMedia("(prefers-color-scheme: dark)"); if (mq.addEventListener) mq.addEventListener("change", setTheme); }
      } catch (err) { teardown(); }
    }, function () { bail(); /* an image failed: the drawn hole stays */ });
  }
  cv.addEventListener("webglcontextlost", function (e) { e.preventDefault(); teardown(); });
  start();
})();
