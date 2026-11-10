"""Draws the GolfVotes wordmark (the V is a check mark) and the "G + check" icon from Inter ExtraBold outlines.
Writes static/logo-word.svg, logo-mark.svg, logo-mark-24.svg, favicon.svg. Run: python3 build/make_logo.py
(needs fontTools and the Inter font; the output files are committed, the site build does not run this)."""
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
F = TTFont("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf")
GS, CMAP, UPM = F.getGlyphSet(), F.getBestCmap(), F["head"].unitsPerEm
CAP = F["OS/2"].sCapHeight / UPM
TRACK = -0.03          # em
CK_W, CK_SW = 0.66, 0.158   # check: advance and stroke width in em


def glyphs(text, x, size, base):
    """Outline `text` starting at x; returns (path d, new x)."""
    d = []
    for ch in text:
        g = GS[CMAP[ord(ch)]]
        pen = SVGPathPen(GS, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip("."))
        s = size / UPM
        g.draw(TransformPen(pen, (s, 0, 0, -s, x, base)))
        d.append(pen.getCommands())
        x += (g.width / UPM + TRACK) * size
    return "".join(d), x


def check(x, size, base):
    """Check mark as tall as a capital letter, starting at x."""
    p = lambda fx, fy: "%.2f %.2f" % (x + fx * size, base - fy * size)
    h = CK_SW / 2
    return "M%sL%sL%s" % (p(0.085, CAP * 0.47), p(0.27, h + 0.005), p(0.60, CAP - h)), x + (CK_W + TRACK) * size


def word():
    size, base = 100, 78
    d1, x = glyphs("Golf", 0, size, base)
    ck, x = check(x + 1, size, base)
    d2, x = glyphs("otes", x + 1, size, base)
    w = x - TRACK * size
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f 100" class="wm" role="img" aria-label="GolfVotes">'
            '<path fill="currentColor" d="%s%s"/><path class="wmc" fill="none" stroke="#0b7a4b" stroke-width="%.1f" '
            'stroke-linecap="round" stroke-linejoin="round" d="%s"/></svg>') % (w + 1, d1, d2, CK_SW * size, ck)


def mark(box, rx, size):
    gw = GS[CMAP[ord("G")]].width / UPM * size
    total = gw + TRACK * size + 0.62 * size
    x0 = (box - total) / 2 + 0.01 * size
    base = (box + CAP * size) / 2
    d, x = glyphs("G", x0, size, base)
    ck, _ = check(x, size, base)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {b} {b}"><rect width="{b}" height="{b}" rx="{r}" fill="#0B3D2C"/>'
            '<path fill="#fff" d="{d}"/><path fill="none" stroke="#3ECF8E" stroke-width="{sw:.2f}" stroke-linecap="round" '
            'stroke-linejoin="round" d="{c}"/></svg>').format(b=box, r=rx, d=d, sw=CK_SW * size, c=ck)


if __name__ == "__main__":
    out = lambda n, s: open(os.path.join(ROOT, "static", n), "w").write(s + "\n")
    out("logo-word.svg", word())
    out("logo-mark.svg", mark(64, 15, 35))
    out("favicon.svg", mark(64, 15, 37))
    out("logo-mark-24.svg", mark(24, 6, 13.5))
