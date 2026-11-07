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
  var TH = settings.frames === false ? "mqdefault" : "mq2";
  var TYPES = { drill: "Drill", explainer: "Explainer", lesson: "Live lesson", pro_swing: "Pro swing", quick_tip: "Quick tip", practice_plan: "Practice plan", fitness: "Fitness" };

  // ---------- chrome ----------
  $("#menu").onclick = function () {
    if (window.innerWidth > 1000 && !document.body.classList.contains("wpage")) document.body.classList.toggle("mini");
    else document.body.classList.toggle("open");
  };
  $("#scrim").onclick = function () { document.body.classList.remove("open"); };
  $("#theme").onclick = function () {
    var r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    r.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("gv_theme", r.dataset.theme); } catch (e) {}
  };
  if (settings.frames === false) $$("img[src*='i.ytimg.com']").forEach(function (i) { i.src = i.src.replace("/mq2.jpg", "/mqdefault.jpg").replace("/hq2.jpg", "/hqdefault.jpg"); });
  document.addEventListener("error", function (ev) {
    var t = ev.target; if (t.tagName === "IMG" && /\/(mq2|hq2)\.jpg$/.test(t.src)) t.src = t.src.replace(/(mq2|hq2)\.jpg$/, "mqdefault.jpg");
  }, true);

  // ---------- player ----------
  function play() {
    var b = $("button.player[data-vid]"); if (!b) return;
    var f = document.createElement("iframe");
    f.className = "player";
    f.src = "https://www.youtube-nocookie.com/embed/" + b.dataset.vid + "?autoplay=1&rel=0&modestbranding=1";
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen"; f.allowFullscreen = true;
    f.referrerPolicy = "strict-origin-when-cross-origin"; f.title = "YouTube video";
    b.replaceWith(f);
  }
  document.addEventListener("click", function (ev) {
    if (ev.target.closest("button.player[data-vid]")) { play(); return; }
    var lb = ev.target.closest(".lb");
    if (lb) {
      ev.preventDefault();
      var art = lb.closest("[data-vid]"), vid = art.dataset.vid;
      var on = toggle("later", { v: vid });
      lb.classList.toggle("on", on); flash(on ? "Saved to Watch later" : "Removed from Watch later");
    }
  });
  function markLater() { $$(".thw").forEach(function (w) { var b = $(".lb", w); if (b) b.classList.toggle("on", has("later", w.dataset.vid)); }); }
  markLater();
  function flash(t) {
    var d = $("#toast") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "toast" }));
    d.textContent = t; d.className = "show"; clearTimeout(d._t); d._t = setTimeout(function () { d.className = ""; }, 1600);
  }

  // ---------- watch page ----------
  var acts = $(".acts");
  if (acts) {
    var item = { v: acts.dataset.vid, t: acts.dataset.t, c: acts.dataset.c };
    var h = load("history").filter(function (x) { return x.v !== item.v; }); h.unshift(item); save("history", h.slice(0, 300));
    var sync = function () { $$("[data-act]", acts).forEach(function (b) { b.classList.toggle("on", has(b.dataset.act, item.v)); }); };
    $$("[data-act]", acts).forEach(function (b) {
      b.onclick = function () { var on = toggle(b.dataset.act, item); sync(); flash(on ? ({ liked: "Liked", disliked: "We'll show you less like this", later: "Saved to Watch later" })[b.dataset.act] : "Removed"); };
    });
    sync();
  }

  // ---------- keyboard ----------
  var keys = [["/", "Search"], ["h", "Home"], ["k", "Play (on a video page)"], ["l", "Like (on a video page)"], ["w", "Watch later (on a video page)"], ["?", "Show these shortcuts"], ["Esc", "Close / leave the search box"]];
  document.addEventListener("keydown", function (ev) {
    var tag = (ev.target.tagName || "").toLowerCase();
    if (ev.key === "Escape") { var m = $("#keys"); if (m) m.remove(); document.body.classList.remove("open"); if (tag === "input") ev.target.blur(); return; }
    if (tag === "input" || tag === "textarea" || tag === "select" || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.key === "/") { ev.preventDefault(); $("#q").focus(); }
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
  if ($("#s-frames")) {
    $("#s-frames").checked = settings.frames !== false; $("#s-hidedis").checked = settings.hidedis !== false;
    $("#s-frames").onchange = function () { settings.frames = this.checked; save("settings", settings); flash("Saved"); };
    $("#s-hidedis").onchange = function () { settings.hidedis = this.checked; save("settings", settings); flash("Saved"); };
    $("#s-clear-h").onclick = function () { save("history", []); flash("Watch history cleared"); };
    $("#s-clear-all").onclick = function () { ["history", "liked", "disliked", "later", "settings", "plans"].forEach(function (k) { save(k, k === "settings" || k === "plans" ? {} : []); }); flash("Everything reset"); };
  }

  // ---------- welcome box ----------
  var wc = $("#wclose");
  if (wc) wc.onclick = function () { document.documentElement.classList.add("nowelcome"); try { localStorage.setItem("gv_nowelcome", "1"); } catch (e) {} };

  // ---------- fix plan progress ----------
  var plans = load("plans", {});
  function planSync() {
    $$("button.done[data-plan]").forEach(function (b) {
      var on = (plans[b.dataset.plan] || []).indexOf(b.dataset.vid) >= 0;
      b.classList.toggle("on", on); $("span", b).textContent = on ? "Done" : "Mark as done";
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
    return '<article class="vc" data-vid="' + v[0] + '"><div class="thw" data-vid="' + v[0] + '"><a class="th" href="' + href + '"><img loading="lazy" src="https://i.ytimg.com/vi/' + v[0] + "/" + TH + '.jpg" alt="">' +
      (v[12] ? '<span class="du">' + dur(v[12]) + "</span>" : "") + '</a><button class="lb" aria-label="Watch later" title="Watch later"><svg viewBox="0 0 24 24"><path d="M14.97 16.95 10 13.87V7h2v5.76l4.03 2.49-1.06 1.7zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg></button></div>' +
      '<div class="vm"><h3><a href="' + href + '">' + esc(v[1]) + '</a></h3><p class="ch">' + (v[3] ? '<a href="' + B + "/coach/" + v[3] + '/">' + esc(v[2]) + "</a>" : esc(v[2])) + (t ? " · " + t : "") +
      '</p><p class="st"><b>' + v[4] + "</b> golfers recommend" + (v[5] ? ' · <span class="ok">✓ ' + v[5] + " fixed it</span>" : "") + (v[6] ? " · " + esc(v[6]) : "") + "</p></div></article>";
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
      if (personal || Object.keys(seen).length) { feed.innerHTML = ""; paint(feed, scored.slice(0, 48)); infinite(feed, scored, 48); }
      else { var shown = {}; $$("[data-vid]", feed).forEach(function (a) { shown[a.dataset.vid] = 1; }); infinite(feed, scored.filter(function (v) { return !shown[v[0]]; }), 0); }
      return;
    }

    var kind = list.dataset.list, arr = [], extra = "";
    if (kind === "search") {
      var q = (new URLSearchParams(location.search).get("q") || "").trim().toLowerCase();
      $("#q").value = q; $("#ltitle").textContent = q ? 'Results for "' + q + '"' : "Search";
      if (q) {
        var words = q.split(/\s+/), hit = function (s) { s = s.toLowerCase(); return words.every(function (x) { return s.indexOf(x) >= 0; }); };
        var ps = ix.p.filter(function (p) { return hit(p[1] + " " + p[2]); }), cs = ix.c.filter(function (c) { return hit(c[1]); });
        if (ps.length) extra += '<div class="sres"><h2>Problems</h2><div class="tags">' + ps.map(function (p) { return '<a class="tag" href="' + B + "/fix/" + p[0] + '/">' + esc(p[1]) + " · " + p[3] + "</a>"; }).join("") + "</div></div>";
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
