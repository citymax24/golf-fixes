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


THEMES = {
    "light": {"leaf": "#B8892B", "stem": "#B8892B", "kick": "#0B7A4B", "big": "#0B3D2C", "line": "#0B3D2C", "rule": "#D9C08A"},
    "dark": {"leaf": "#E3C16F", "stem": "#E3C16F", "kick": "#3ECF8E", "big": "#FFFFFF", "line": "#FFFFFF", "rule": "#6E5E35"},
}


def _fit(lines, R, cy, LEAF, dmin):
    """Distance from badge centre to each branch's circle centre so that no text line touches the inner leaves."""
    d = dmin
    for t, f, sz, tr, y, _ in lines:
        dy = min(abs(y - sz * .35 - cy), R - 1)
        d = max(d, text_width(t, f, sz, tr) / 2 + 10 + LEAF * .55 - math.sqrt(R * R - dy * dy))
    return d


def badge(big, line, year, theme="light", label="", sub="MOST RECOMMENDED LESSON"):
    """big: '#1' or 'TOP 10'; line: e.g. 'EARLY EXTENSION'. Returns (svg, width, height)."""
    th = THEMES[theme]
    kick = f"GOLFVOTES {year}"
    H, R, cy, LEAF, n = 150, 64, 76, 21, 9
    fs_line = 15 if len(line) <= 18 else 13.5
    lines = [  # (text, font, size, track, baseline, fill)
        (kick, "Inter-Bold.otf", 10.5, 1.8, 38, th["kick"]),
        (big, "InterDisplay-Black.otf", 44, 0, 84, th["big"]),
        (line, "Inter-ExtraBold.otf", fs_line, 1.1, 106, th["line"]),
        (sub, "Inter-SemiBold.otf", 9, 1.4, 129, th["kick"]),
    ]
    d = _fit(lines, R, cy, LEAF, 30)
    mid = d + R + LEAF * 1.15 + 4
    W = round(2 * mid)
    stemL, leavesL = laurel(mid - d, cy, R, 112, 240, n, LEAF)
    stemR, leavesR = laurel(mid + d, cy, R, 68, -60, n, LEAF)
    parts = [f'<path d="{stemL}{stemR}" fill="none" stroke="{th["stem"]}" stroke-width="1.8" stroke-linecap="round"/>',
             f'<path d="{leavesL}{leavesR}" fill="{th["leaf"]}"/>',
             f'<rect x="{mid - 16:.1f}" y="114" width="32" height="1.5" rx=".75" fill="{th["rule"]}"/>']
    parts += [f'<path d="{text_path(t, f, sz, mid, y, tr)}" fill="{c}"/>' for t, f, sz, tr, y, c in lines]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
           f'<title>{label}</title>{"".join(parts)}</svg>')
    return svg, W, H


def live_badge(n, theme="light", label=""):
    """Live count badge: 'GOLFVOTES · 1,408 · GOLFER RECOMMENDATIONS' with a single laurel sprig on each side."""
    th = THEMES[theme]
    num = f"{n:,}"
    lines = [("GOLFVOTES", "Inter-Bold.otf", 10.5, 2.2, 30, th["kick"]),
             (num, "InterDisplay-Black.otf", 38, 0, 70, th["big"]),
             ("GOLFER RECOMMENDATIONS", "Inter-ExtraBold.otf", 11, 1.1, 90, th["line"])]
    H, R, cy, LEAF = 112, 46, 58, 17
    d = _fit(lines, R, cy, LEAF, 24)
    mid = d + R + LEAF * 1.1 + 4
    W = round(2 * mid)
    stemL, leavesL = laurel(mid - d, cy, R, 115, 235, 7, LEAF)
    stemR, leavesR = laurel(mid + d, cy, R, 65, -55, 7, LEAF)
    parts = [f'<path d="{stemL}{stemR}" fill="none" stroke="{th["stem"]}" stroke-width="1.6" stroke-linecap="round"/>',
             f'<path d="{leavesL}{leavesR}" fill="{th["leaf"]}"/>']
    parts += [f'<path d="{text_path(t, f, sz, mid, y, tr)}" fill="{c}"/>' for t, f, sz, tr, y, c in lines]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
            f'<title>{label}</title>{"".join(parts)}</svg>'), W, H


if __name__ == "__main__":
    make_glyph_cache(); print("wrote", GLYPHS, os.path.getsize(GLYPHS) // 1024, "KB")
