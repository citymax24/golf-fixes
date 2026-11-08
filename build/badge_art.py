"""Badges as self-contained SVG. Text is drawn as outlines (looks identical everywhere, no web font needed).
Glyph outlines come from build/glyphs.json (made once from Inter with fontTools: python3 build/badge_art.py),
so the site build itself needs no extra packages."""
import json
import math
import os

FONT_DIR = "/usr/share/fonts/opentype/inter/"
FONTS = ["Inter-Bold.otf", "Inter-ExtraBold.otf", "Inter-SemiBold.otf", "InterDisplay-Black.otf"]
CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#&,.·-'’/+()"
GLYPHS = os.path.join(os.path.dirname(__file__), "glyphs.json")
_G = None


def make_glyph_cache():
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen
    out = {}
    for name in FONTS:
        f = TTFont(FONT_DIR + name); gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
        d = {"upm": f["head"].unitsPerEm, "g": {}}
        for ch in CHARS:
            g = cmap.get(ord(ch))
            if g is None:
                continue
            pen = RecordingPen(); gs[g].draw(pen)
            d["g"][ch] = [hmtx[g][0], [[op, [[round(x, 1), round(y, 1)] for x, y in pts]] for op, pts in pen.value]]
        out[name] = d
    json.dump(out, open(GLYPHS, "w"), separators=(",", ":"))


def _glyphs(font):
    global _G
    if _G is None:
        _G = json.load(open(GLYPHS))
    return _G[font]


def text_width(s, font, size, track=0):
    F = _glyphs(font)
    return sum(F["g"].get(ch, F["g"][" "])[0] for ch in s) * size / F["upm"] + track * max(len(s) - 1, 0)


def _n(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def text_path(s, font, size, x, y, track=0, anchor="middle"):
    """SVG path data for string s with baseline at y, centred on x by default."""
    F = _glyphs(font); k = size / F["upm"]
    if anchor == "middle":
        x -= text_width(s, font, size, track) / 2
    cmd = {"moveTo": "M", "lineTo": "L", "curveTo": "C", "qCurveTo": "Q", "closePath": "Z", "endPath": ""}
    out = []
    for ch in s:
        adv, ops = F["g"].get(ch, F["g"][" "])
        for op, pts in ops:
            out.append(cmd[op] + " ".join(f"{_n(x + px * k)} {_n(y - py * k)}" for px, py in pts))
        x += adv * k + track
    return "".join(out)


def _leaf(px, py, ang, L, W):
    """Almond leaf from base (px,py) pointing at angle ang (radians, 0 = right, -pi/2 = up)."""
    c, s = math.cos(ang), math.sin(ang)
    def P(a, b):  # a along leaf, b across
        return f"{px + a * c - b * s:.2f} {py + a * s + b * c:.2f}"
    return f"M{P(0, 0)}C{P(L * .3, W)} {P(L * .75, W * .9)} {P(L, 0)}C{P(L * .75, -W * .9)} {P(L * .3, -W)} {P(0, 0)}Z"


def laurel(cx, cy, R, a0, a1, n, size):
    """Left-side branch on circle (cx,cy,R) from angle a0 (bottom) to a1 (top), degrees, going clockwise in screen space.
    Returns (stem path, leaves path)."""
    pts = []
    leaves = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    stem = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts)
    for i in range(1, n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        sg = 1 if a1 > a0 else -1
        tang = a + sg * math.pi / 2  # direction of travel
        L = size * (1.0 - 0.3 * t)
        W = L * 0.34
        if i == n:
            leaves.append(_leaf(x, y, tang, L * 1.05, W))
            continue
        spread = math.radians(38)
        leaves.append(_leaf(x, y, tang - sg * spread, L, W))  # outer
        leaves.append(_leaf(x, y, tang + sg * spread, L * .92, W * .95))  # inner
    return stem, "".join(leaves)


# One fixed canvas for every badge, so several badges line up and drop into any layout the same way.
W, H = 280, 140
R, CY, LEAF = 60, 72, 20
D = W / 2 - 4 - LEAF * 1.15 - R  # centre -> branch circle centre


def _room(y, size):
    """Half-width available for a text line with baseline y between the two branches."""
    dy = min(abs(y - size * .35 - CY), R - 1)
    return D - 10 - LEAF * .55 + math.sqrt(R * R - dy * dy)


def _sized(t, font, smax, smin, track, y):
    """Largest font size (<= smax) at which t fits between the branches, or None below smin."""
    sz = smax
    while sz >= smin:
        if text_width(t, font, sz, track) / 2 <= _room(y, sz):
            return sz
        sz -= .25
    return None


def _wrap(t):
    w = t.split(" ")
    if "&" in w:
        i = w.index("&") + 1
        return " ".join(w[:i]), " ".join(w[i:])
    best = min(range(1, len(w)), key=lambda i: abs(len(" ".join(w[:i])) - len(" ".join(w[i:]))))
    return " ".join(w[:best]), " ".join(w[best:])


def _render(kick, big, line, sub, theme, label):
    th = THEMES[theme]
    B, X, S = "InterDisplay-Black.otf", "Inter-ExtraBold.otf", "Inter-Bold.otf"
    rows = [(kick, S, 10.5, 1.8, 36, th["kick"])]
    one = _sized(line, X, 15, 11.5, 1, 102)
    if one:
        rows += [(big, B, _sized(big, B, 40, 20, 0, 80), 0, 80, th["big"]), (line, X, one, 1, 102, th["line"])]
    else:
        l1, l2 = _wrap(line)
        sz = min(_sized(l1, X, 13, 9, .8, 94) or 9, _sized(l2, X, 13, 9, .8, 109) or 9)
        rows += [(big, B, _sized(big, B, 34, 18, 0, 73), 0, 73, th["big"]), (l1, X, sz, .8, 94, th["line"]), (l2, X, sz, .8, 109, th["line"])]
    rows.append((sub, S, _sized(sub, S, 10, 8, 1.3, 125) or 8, 1.3, 125, th["kick"]))
    mid = W / 2
    stemL, leavesL = laurel(mid - D, CY, R, 112, 240, 9, LEAF)
    stemR, leavesR = laurel(mid + D, CY, R, 68, -60, 9, LEAF)
    parts = [f'<path d="{stemL}{stemR}" fill="none" stroke="{th["stem"]}" stroke-width="1.8" stroke-linecap="round"/>',
             f'<path d="{leavesL}{leavesR}" fill="{th["leaf"]}"/>']
    parts += [f'<path d="{text_path(t, f, sz, mid, y, tr)}" fill="{c}"/>' for t, f, sz, tr, y, c in rows]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
            f'<title>{label}</title>{"".join(parts)}</svg>'), W, H


THEMES = {
    "light": {"leaf": "#B8892B", "stem": "#B8892B", "kick": "#0B7A4B", "big": "#0B3D2C", "line": "#0B3D2C"},
    "dark": {"leaf": "#E3C16F", "stem": "#E3C16F", "kick": "#3ECF8E", "big": "#FFFFFF", "line": "#FFFFFF"},
}


def badge(big, line, year, theme="light", label="", sub="MOST RECOMMENDED"):
    """Award badge: 'GOLFVOTES 2026 / #1 / EARLY EXTENSION / MOST RECOMMENDED'."""
    return _render(f"GOLFVOTES {year}", big, line, sub, theme, label)


def live_badge(n, theme="light", label=""):
    """Live count badge: 'GOLFVOTES / 1,408 / RECOMMENDATIONS / FROM GOLFERS'."""
    return _render("GOLFVOTES", f"{n:,}", "RECOMMENDATIONS", "FROM GOLFERS", theme, label)


if __name__ == "__main__":
    make_glyph_cache(); print("wrote", GLYPHS, os.path.getsize(GLYPHS) // 1024, "KB")
