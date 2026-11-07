// GolfVotes: click-to-load videos, opt-in thumbnails, problem filter. No cookies, no tracking.
(function () {
  var KEY = "gv_previews";
  function get() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function set(v) { try { v ? localStorage.setItem(KEY, "1") : localStorage.removeItem(KEY); } catch (e) {} }

  function thumbs() {
    document.querySelectorAll(".player[data-vid]").forEach(function (b) {
      if (b.querySelector("img")) return;
      var img = new Image();
      img.loading = "lazy"; img.alt = "";
      img.src = "https://i.ytimg.com/vi/" + b.dataset.vid + "/mqdefault.jpg";
      b.insertBefore(img, b.firstChild);
    });
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest(".player[data-vid]");
    if (!b) return;
    var f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + b.dataset.vid + "?autoplay=1&rel=0";
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    f.allowFullscreen = true;
    f.referrerPolicy = "strict-origin-when-cross-origin";
    f.title = b.getAttribute("aria-label") || "YouTube video";
    b.replaceWith(f);
  });

  if (document.querySelector(".player[data-vid]")) {
    if (get()) thumbs();
    else {
      var bar = document.createElement("div");
      bar.className = "previews";
      bar.innerHTML = 'Show video thumbnails? They load from YouTube. <button type="button">Show</button>';
      bar.querySelector("button").onclick = function () { set(true); thumbs(); bar.remove(); };
      document.body.appendChild(bar);
    }
  }

  var q = document.getElementById("q");
  if (q) q.addEventListener("input", function () {
    var s = q.value.trim().toLowerCase();
    document.querySelectorAll(".tile").forEach(function (t) {
      t.classList.toggle("hide", s && t.dataset.name.indexOf(s) < 0);
    });
    document.querySelectorAll(".group").forEach(function (g) {
      g.style.display = g.querySelector(".tile:not(.hide)") ? "" : "none";
    });
  });
})();
