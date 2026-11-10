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
  var TYPES = { drill: "Drill", explainer: "Explainer", lesson: "Live lesson", pro_swing: "Pro swing", quick_tip: "Quick tip", practice_plan: "Practice plan", fitness: "Fitness" };

  // ---------- chrome ----------
  function closeMenu(focusBack) {
    if (!document.body.classList.contains("open")) return;
    document.body.classList.remove("open"); $("#menu").setAttribute("aria-expanded", "false");
    if (focusBack) $("#menu").focus();
  }
  $("#menu").onclick = function () {
    if (window.innerWidth > 1000 && !document.body.classList.contains("wpage")) {
      document.body.classList.toggle("mini"); $("#menu").setAttribute("aria-expanded", String(!document.body.classList.contains("mini")));
    } else if (document.body.classList.contains("open")) closeMenu(true);
    else { document.body.classList.add("open"); $("#menu").setAttribute("aria-expanded", "true"); var f = $("#side a"); if (f) setTimeout(function () { f.focus(); }, 50); }
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
  }, true);

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
    var q = $("#q"), box = $("#sugg"), ix = null, items = [], sel = -1;
    var SYN = { slicing: "slice", sliced: "slice", shank: "shanks", shanking: "shanks", hooking: "hook", chunk: "fat", chunking: "fat", topped: "topping",
      chip: "chipping", putt: "putting", drive: "driver", irons: "iron", sand: "bunker", ott: "over the top", ee: "early extension" };
    function get(cb) { if (ix) return cb(ix); fetch(B + "/static/index.json").then(function (r) { return r.json(); }).then(function (d) { ix = d; cb(d); }); }
    function close() { box.hidden = true; q.setAttribute("aria-expanded", "false"); sel = -1; }
    function render() {
      box.innerHTML = items.map(function (it, i) { return '<li role="option" id="sg' + i + '"' + (i === sel ? ' aria-selected="true" class="on"' : "") + '><a href="' + it.h + '"><b>' + esc(it.t) + "</b><span>" + esc(it.s) + "</span></a></li>"; }).join("");
      box.hidden = !items.length; q.setAttribute("aria-expanded", String(!!items.length));
      if (sel >= 0) q.setAttribute("aria-activedescendant", "sg" + sel); else q.removeAttribute("aria-activedescendant");
    }
    q.addEventListener("input", function () {
      var v = q.value.trim().toLowerCase(); if (v.length < 2) { items = []; return render(); }
      v = SYN[v] || v;
      get(function (d) {
        var m = function (s) { return s.toLowerCase().split(/[^a-z0-9]+/).some(function (w) { return w.indexOf(v) === 0; }) || s.toLowerCase().indexOf(v) === 0; };
        var ps = d.p.filter(function (p) { return m(p[1]) || m(p[2]); }).slice(0, 4).map(function (p) { return { h: B + "/fix/" + p[0] + "/", t: p[1], s: "Problem · " + p[3].toLocaleString() + " recommendations" }; });
        var cs = d.c.filter(function (c) { return m(c[1]); }).slice(0, 2).map(function (c) { return { h: B + "/coach/" + c[0] + "/", t: c[1], s: "Coach · " + c[2].toLocaleString() + " recommendations" }; });
        var vs = d.v.filter(function (x) { return m(x[1]); }).slice(0, 3).map(function (x) { return { h: B + "/watch/" + x[0] + "/", t: x[1], s: x[2] + " · " + x[4] + " golfers recommend" }; });
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
    $$(".bfd", bff).forEach(function (a) {
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        var k = a.dataset.k;
        if (a.classList.contains("on")) return;
        bff.classList.add("used");
        $$(".bfd", bff).forEach(function (x) { x.classList.toggle("on", x === a); x.setAttribute("aria-pressed", String(x === a)); });
        $$(".bfl", bff).forEach(function (p) { p.classList.toggle("on", p.dataset.k === k); });
        $$("iframe.bfvid", bff).forEach(function (f) { f.replaceWith(f._btn); });  // stop a lesson that is playing
        $$(".bfp", bff).forEach(function (p) { p.hidden = p.id !== "bf-" + k; });
        if (window.innerWidth < 760) $(".bfr", bff).scrollIntoView({ block: "nearest", behavior: "smooth" });
      });
    });
  }

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
  var sa = $("#showall"); if (sa) sa.onclick = function () { $("#ranked").classList.add("showall"); sa.parentNode.remove(); };
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
    $$(".plc[data-plan]").forEach(function (c) { var d = (plans[c.dataset.plan] || []).length; $(".pprog", c).textContent = d ? " · " + d + "/" + c.dataset.n + " done" : ""; });
  }
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button.done[data-plan]"); if (!b) return;
    var l = plans[b.dataset.plan] || [], i = l.indexOf(b.dataset.vid);
    if (i >= 0) l.splice(i, 1); else l.push(b.dataset.vid);
    plans[b.dataset.plan] = l; save("plans", plans); planSync(); flash(i >= 0 ? "Marked as not done" : "Nice, step done");
  });
  planSync();

  // ---------- index-driven views ----------
  var list = $("#list"), feed = $("#feed");
  if (!list && !feed) return;
  function card(v) {
    var href = B + "/watch/" + v[0] + "/", t = TYPES[v[8]];
    return '<article class="vc" data-vid="' + v[0] + '"><div class="thw" data-vid="' + v[0] + '"><a class="th" href="' + href + '"><img loading="lazy" src="' + B + '/static/thumbs/mq2/' + v[0] + '.webp" alt="" onerror="this.onerror=null;this.style.visibility=\'hidden\'">' +
      (v[12] ? '<span class="du">' + dur(v[12]) + "</span>" : "") + '</a><button class="lb" aria-label="Watch later" title="Watch later"><svg viewBox="0 0 24 24"><path d="M14.97 16.95 10 13.87V7h2v5.76l4.03 2.49-1.06 1.7zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg></button></div>' +
      '<div class="vm"><h3><a href="' + href + '">' + esc(v[1]) + '</a></h3><p class="ch">' + (v[3] ? '<a href="' + B + "/coach/" + v[3] + '/">' + esc(v[2]) + "</a>" : esc(v[2])) + (t ? " · " + t : "") +
      '</p><p class="st"><span><b>' + v[4] + "</b> recommend" + (v[4] == 1 ? "s" : "") + "</span>" + (v[5] ? '<span class="ok">✓ ' + v[5] + " fixed it</span>" : "") + (v[6] ? '<span class="nw">' + esc(v[6]) + "</span>" : "") + "</p></div></article>";
  }
  function dur(s) { var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60; return (h ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (x < 10 ? "0" : "") + x; }
  function paint(el, arr, append) { el.insertAdjacentHTML(append ? "beforeend" : "afterbegin", arr.map(card).join("")); if (!append) {} markLater(); }
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
      var scored = ix.v.filter(ok).map(function (v, i) {
        var aff = v[7].reduce(function (a, p) { return a + (w[p] || 0); }, 0);
        var s = Math.log(1 + v[4]) + 0.4 * Math.log(1 + v[5]) + (personal ? 0.6 * aff : 0) - (seen[v[0]] ? 1.5 : 0) + 0.8 * rnd(seed + i);
        return [s, v];
      }).sort(function (a, b) { return b[0] - a[0]; }).map(function (x) { return x[1]; });
      if (personal || Object.keys(seen).length) { feed.innerHTML = ""; paint(feed, scored.slice(0, 24)); }
      return;
    }

    var kind = list.dataset.list, arr = [], extra = "";
    if (kind === "search") {
      var q = (new URLSearchParams(location.search).get("q") || "").trim().toLowerCase();
      $("#q").value = q; $("#ltitle").textContent = q ? 'Results for "' + q + '"' : "Search";
      if (q) {
        var SYN = { slicing: "slice", sliced: "slice", slices: "slice", hooking: "hook", hooks: "hook", shanking: "shanks", shank: "shanks", shanked: "shanks",
          topping: "topping", topped: "topping", tops: "topping", chunk: "fat", chunking: "fat", chunked: "fat", fat: "fat", thin: "thin", sculled: "thin",
          chipping: "chipping", chip: "chipping", chips: "chipping", putt: "putting", putts: "putting", driver: "driver", drive: "driver", irons: "iron", iron: "iron",
          bunker: "bunker", sand: "bunker", ott: "over the top", "over-the-top": "over the top", ee: "early extension", casting: "casting", lag: "lag", speed: "speed" };
        var words = q.split(/\s+/).map(function (w) { return SYN[w] || w; });
        var rx = words.map(function (w) { return new RegExp("\\b" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")); });
        var hit = function (s) { s = s.toLowerCase(); return rx.every(function (r) { return r.test(s); }); };
        var hitAny = function (s) { s = s.toLowerCase(); return rx.some(function (r) { return r.test(s); }); };
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
      var run = function () {
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
        $("#count").textContent = a.length + " lessons"; paint(list, a.slice(0, 48)); infinite(list, a, 48);
        $("#empty").textContent = a.length ? "" : "No lessons match these filters.";
      };
      f.onchange = run; run(); return;
    } else {
      arr = load(kind).map(function (x) { return byId[x.v]; }).filter(Boolean);
      if (kind !== "disliked") arr = arr.filter(ok);
    }
    paint(list, arr.slice(0, 48)); infinite(list, arr, 48);
    $("#empty").style.display = arr.length || extra ? "none" : "";
    if (kind === "search" && !arr.length && !extra) $("#empty").textContent = "No results. Try a problem like slice, shanks or chipping.";
  });
})();
