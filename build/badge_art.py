"""Laurel award badges as self-contained SVG (text converted to outlines, so they look identical everywhere).
Needs fontTools + Inter (only where badges are (re)generated; the results are committed under static/badge/)."""
import math
import re
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT_DIR = "/usr/share/fonts/opentype/inter/"
_fonts = {}


def _font(name):
    if name not in _fonts:
        f = TTFont(FONT_DIR + name)
        _fonts[name] = (f, f.getGlyphSet(), f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    return _fonts[name]


def text_width(s, font, size, track=0):
    f, gs, cmap, hmtx, upm = _font(font)
    return sum(hmtx[cmap.get(ord(ch), cmap[32])][0] for ch in s) * size / upm + track * max(len(s) - 1, 0)


def text_path(s, font, size, x, y, track=0, anchor="middle"):
    """SVG path data for string s with baseline at y. anchor: start|middle."""
    f, gs, cmap, hmtx, upm = _font(font)
    k = size / upm
    if anchor == "middle":
        x -= text_width(s, font, size, track) / 2
    pen = SVGPathPen(gs)
    for ch in s:
        g = cmap.get(ord(ch), cmap[32])
        gs[g].draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
        x += hmtx[g][0] * k + track
    return re.sub(r"-?\d+\.\d+", lambda m: f"{float(m[0]):.1f}".rstrip("0").rstrip("."), pen.getCommands())


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
    # distance from badge centre to the left branch's circle centre, so that no line touches the inner leaves
    d = 0
    for t, f, sz, tr, y, _ in lines:
        hw = text_width(t, f, sz, tr) / 2
        dy = min(abs(y - sz * .35 - cy), R - 1)
        d = max(d, hw + 10 + LEAF * .55 - math.sqrt(R * R - dy * dy))
    d = max(d, 30)
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
