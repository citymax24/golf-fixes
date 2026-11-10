"""Draws the GolfVotes wordmark (the V is a check mark), the "G + check" icon and the favicon from Inter ExtraBold outlines.
Writes static/logo-word.svg, logo-mark.svg, logo-mark-24.svg, favicon.svg, apple-touch-icon.png. Run: python3 build/make_logo.py
(needs fontTools and the Inter font, Pillow for the PNG; the output files are committed, the site build does not run this)."""
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F = TTFont(FONT)
GS, CMAP, UPM = F.getGlyphSet(), F.getBestCmap(), F["head"].unitsPerEm
CAP = F["OS/2"].sCapHeight / UPM
TRACK = -0.03          # em
CK_SW = 0.170          # check stroke = the stem of Inter ExtraBold (l stem 0.1704 em), so the check is as heavy as the letters
CK_L = 0.045           # space between the advance of the letter before the check and the check box
CK_W = 0.60            # check advance: "otes" tucks under the long arm like a kerned "Vo"
CK_OT, CK_OB = 0.015, 0.012   # overshoot of the round ends above the cap line / below the baseline (like the round letters)
P1, P2X, P3X = (0.085, 0.47), 0.27, 0.60   # check points: short arm start (x, share of cap height), vertex x, long arm end x
MARK_DX = 0.01         # icon: the pair is centred on its ink box, then moved right by 1% of the tile (the white G is the heavier half)
TILE, MINT = "#0B3D2C", "#3ECF8E"


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


def ink(ch):
    """(left bearing, right bearing) of a glyph in em."""
    g = GS[CMAP[ord(ch)]]
    bp = BoundsPen(GS)
    g.draw(bp)
    return bp.bounds[0] / UPM, (g.width - bp.bounds[2]) / UPM


def check_pts(x, size, base):
    """The three points of the check mark: as tall as a capital letter plus overshoot, box starting at x."""
    h = CK_SW / 2
    return [(x + P1[0] * size, base - CAP * P1[1] * size), (x + P2X * size, base - (h - CK_OB) * size), (x + P3X * size, base - (CAP - h + CK_OT) * size)]


def check_d(pts):
    return "M" + "L".join("%.2f %.2f" % p for p in pts)


def word():
    size, base = 100, 78
    d1, x = glyphs("Golf", 0, size, base)
    cx = x + CK_L * size
    d2, x = glyphs("otes", cx + (CK_W + TRACK) * size, size, base)
    # The viewBox is the ink box in x (left edge of G to right edge of s) and the cap box plus 1/16 cap height above and
    # below in y. So a CSS height of 18px gives caps of exactly 16px, the box edge is the ink edge, and the caps are
    # centred in the box.
    x0 = ink("G")[0] * size
    x1 = x - TRACK * size - ink("s")[1] * size
    pad = CAP * size / 16
    vb = "%.2f %.2f %.2f %.2f" % (x0, base - CAP * size - pad, x1 - x0, CAP * size + 2 * pad)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" class="wm" role="img" aria-label="GolfVotes">'
            '<path fill="currentColor" d="%s%s"/><path class="wmc" fill="none" stroke="#0b7a4b" stroke-width="%.1f" '
            'stroke-linecap="round" stroke-linejoin="round" d="%s"/></svg>') % (vb, d1, d2, CK_SW * size, check_d(check_pts(cx, size, base)))


def tile(box, rx, inner):
    rect = '<rect width="%s" height="%s"%s fill="%s"/>' % (box, box, ' rx="%s"' % rx if rx else "", TILE)
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s">%s%s</svg>' % (box, box, rect, inner)


def stroke(pts, size):
    return ('<path fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round" d="%s"/>'
            % (MINT, CK_SW * size, check_d(pts)))


def mark_geo(box, size):
    """G origin x, baseline y and check points of the "G + check" pair on a tile of `box`."""
    cx = (GS[CMAP[ord("G")]].width / UPM + TRACK + CK_L) * size      # same space before the check as in the wordmark
    ink_l, ink_r = ink("G")[0] * size, cx + (P3X + CK_SW / 2) * size
    x0 = (box - (ink_r - ink_l)) / 2 - ink_l + MARK_DX * box
    base = (box + CAP * size) / 2
    return x0, base, check_pts(x0 + cx, size, base)


def mark(box, rx, size):
    """G + check on the tile (logo-mark, app icon)."""
    x0, base, pts = mark_geo(box, size)
    return tile(box, rx, '<path fill="#fff" d="%s"/>%s' % (glyphs("G", x0, size, base)[0], stroke(pts, size)))


def favicon(box, rx, size):
    """Browser-tab icon: the check alone (same angles and weight as the V of the wordmark), centred on its ink box.
    G + check does not survive 16px: the G is under 7px tall with a closed counter."""
    pts = check_pts(0, size, 0)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ox, oy = (box - max(xs) - min(xs)) / 2, (box - max(ys) - min(ys)) / 2
    return tile(box, rx, stroke([(x + ox, y + oy) for x, y in pts], size))


def touch_icon(path, box=180, size=100, ss=8):
    """App icon as PNG: square opaque tile (iOS masks the corners itself), same geometry as mark(), drawn 8x and scaled down."""
    from PIL import Image, ImageDraw, ImageFont
    x0, base, pts = mark_geo(box, size)
    im = Image.new("RGB", (box * ss, box * ss), TILE)
    dr = ImageDraw.Draw(im)
    dr.text((x0 * ss, base * ss), "G", font=ImageFont.truetype(FONT, size * ss, layout_engine=ImageFont.Layout.BASIC), anchor="ls", fill="#fff")
    r = CK_SW * size * ss / 2
    dr.line([(x * ss, y * ss) for x, y in pts], fill=MINT, width=round(2 * r), joint="curve")
    for x, y in pts:
        dr.ellipse([x * ss - r, y * ss - r, x * ss + r, y * ss + r], fill=MINT)
    im.resize((box, box), Image.LANCZOS).save(path, optimize=True)


if __name__ == "__main__":
    out = lambda n, s: open(os.path.join(ROOT, "static", n), "w").write(s + "\n")
    out("logo-word.svg", word())
    out("logo-mark.svg", mark(64, 15, 35))
    out("favicon.svg", favicon(64, 15, 56))
    out("logo-mark-24.svg", mark(24, 6, 13.5))
    try:
        touch_icon(os.path.join(ROOT, "static", "apple-touch-icon.png"))
    except ImportError:
        print("Pillow missing: static/apple-touch-icon.png not regenerated")
