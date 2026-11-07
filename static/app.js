// GolfVotes client: menu, theme, click-to-play, like/later/history (localStorage only), search. No cookies, no tracking.
(function () {
  var B = document.body.dataset.base || "";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  function load(k) { try { return JSON.parse(localStorage.getItem("gv_" + k) || "[]"); } catch (e) { return []; } }
  function save(k, v) { try { localStorage.setItem("gv_" + k, JSON.stringify(v)); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // menu + theme
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

  // click-to-play
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button.player[data-vid]");
    if (!b) return;
    var f = document.createElement("iframe");
    f.className = "player";
    f.src = "https://www.youtube-nocookie.com/embed/" + b.dataset.vid + "?autoplay=1&rel=0&modestbranding=1";
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    f.allowFullscreen = true; f.referrerPolicy = "strict-origin-when-cross-origin"; f.title = "YouTube video";
    b.replaceWith(f);
  });

  // watch page: history + like/later
  var acts = $(".acts");
  if (acts) {
    var item = { v: acts.dataset.vid, t: acts.dataset.t, c: acts.dataset.c };
    var h = load("history").filter(function (x) { return x.v !== item.v; }); h.unshift(item); save("history", h.slice(0, 200));
    acts.querySelectorAll("[data-act]").forEach(function (btn) {
      var k = btn.dataset.act, has = function () { return load(k).some(function (x) { return x.v === item.v; }); };
      btn.classList.toggle("on", has());
      btn.onclick = function () {
        var l = load(k).filter(function (x) { return x.v !== item.v; });
        if (!has()) l.unshift(item);
        save(k, l); btn.classList.toggle("on", has());
      };
    });
  }

  // liked / history / later / search pages
  var list = $("#list");
  if (!list) return;
  function card(v) {
    var h = B + "/watch/" + v[0] + "/";
    return '<article class="vc"><a class="th" href="' + h + '"><img loading="lazy" src="https://i.ytimg.com/vi/' + v[0] + '/mqdefault.jpg" alt=""></a>' +
      '<div class="vm"><h3><a href="' + h + '">' + esc(v[1]) + '</a></h3><p class="ch">' + (v[3] ? '<a href="' + B + "/coach/" + v[3] + '/">' + esc(v[2]) + "</a>" : esc(v[2])) +
      '</p><p class="st"><b>' + v[4] + "</b> golfers recommend" + (v[5] ? ' · <span class="ok">✓ ' + v[5] + " fixed it</span>" : "") + (v[6] ? " · " + esc(v[6]) : "") + "</p></div></article>";
  }
  fetch(B + "/static/index.json").then(function (r) { return r.json(); }).then(function (ix) {
    var byId = {}; ix.v.forEach(function (v) { byId[v[0]] = v; });
    var kind = list.dataset.list, out = "", extra = "";
    if (kind === "search") {
      var q = (new URLSearchParams(location.search).get("q") || "").trim().toLowerCase();
      $("#q").value = q;
      $("#ltitle").textContent = q ? 'Results for "' + q + '"' : "Search";
      if (q) {
        var words = q.split(/\s+/), hit = function (s) { s = s.toLowerCase(); return words.every(function (w) { return s.indexOf(w) >= 0; }); };
        var ps = ix.p.filter(function (p) { return hit(p[1] + " " + p[2]); }), cs = ix.c.filter(function (c) { return hit(c[1]); });
        if (ps.length) extra += '<div class="sres"><h2>Problems</h2><div class="tags">' + ps.map(function (p) { return '<a class="tag" href="' + B + "/fix/" + p[0] + '/">' + esc(p[1]) + " · " + p[3] + "</a>"; }).join("") + "</div></div>";
        if (cs.length) extra += '<div class="sres"><h2>Coaches</h2><div class="tags">' + cs.slice(0, 12).map(function (c) { return '<a class="tag" href="' + B + "/coach/" + c[0] + '/">' + esc(c[1]) + "</a>"; }).join("") + "</div></div>";
        var vs = ix.v.filter(function (v) { return hit(v[1] + " " + v[2] + " " + v[6]); }).slice(0, 120);
        out = vs.map(card).join("");
        if (extra) list.insertAdjacentHTML("beforebegin", extra + '<h2 class="ptitle" style="font-size:16px;margin-top:20px">Lessons</h2>');
      }
    } else {
      out = load(kind).map(function (x) { return byId[x.v] ? card(byId[x.v]) : ""; }).join("");
    }
    list.innerHTML = out;
    $("#empty").style.display = out || extra ? "none" : "";
    if (kind === "search" && !out && !extra && list.dataset.list) $("#empty").textContent = "No results. Try a problem like slice, shanks or chipping.";
  });
})();
