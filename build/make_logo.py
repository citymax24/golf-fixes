"""Draws the GolfVotes wordmark (the V is a check mark), the "G + check" icon and the favicon from Inter ExtraBold outlines.
Writes static/logo-word.svg, logo-mark.svg, logo-mark-24.svg, favicon.svg, apple-touch-icon.png. Run: python3 build/make_logo.py
(needs fontTools and the Inter font, Pillow for the PNG; the output files are committed, the site build does not run this).
`python3 build/make_logo.py --inline` prints the small check used in running text (CK in build.py and app.js).

The check is built like the letters around it: two straight strokes, cut flat on the cap line (long arm), at its own
height (short arm) and on the baseline, where it has a flat foot like Inter's V. No round ends."""
import math
import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F = TTFont(FONT)
GS, CMAP, UPM = F.getGlyphSet(), F.getBestCmap(), F["head"].unitsPerEm
CAP = F["OS/2"].sCapHeight / UPM
TRACK = -0.03          # em
CK_H = 0.47            # top of the short arm, as a share of the cap height
CK_A, CK_B = 36, 27    # lean of the short and the long arm, degrees from vertical (the short arm is the more open one)
CK_T = 0.178           # thickness across both arms, em (stem of Inter ExtraBold 0.170, across the arms of its V 0.184)
CK_FLAT = 0.13         # width of the flat foot on the baseline
CK_GAP = 0.085         # from the right edge of the f's stem to the tip of the short arm
CK_TUCK = 0.135        # "otes" moves this far under the long arm, like a kerned "Vo"
MARK_GAP = 0.05        # icon: space between the G and the tip of the short arm
MARK_DX = 0.01         # icon: the pair is centred on its ink box, then moved right by 1% of the tile (the white G is the heavier half)
TILE, MINT, GREEN = "#0B3D2C", "#3ECF8E", "#0b7a4b"

_TA, _TB = math.tan(math.radians(CK_A)), math.tan(math.radians(CK_B))
CK_LEFT = -CK_H * CAP * _TA            # x of the short arm's tip, relative to the left end of the foot (negative)
CK_RIGHT = CK_FLAT + CAP * _TB         # x of the long arm's outer top corner


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


def stem_right(ch):
    """x of the right edge of a letter's stem where it stands on the baseline, em."""
    pen = RecordingPen()
    GS[CMAP[ord(ch)]].draw(pen)
    return max(p[0] for _, pts in pen.value for p in pts if p[1] == 0) / UPM


def check_pts(x, size, base):
    """The seven corners of the check; x is the left end of its foot on the baseline."""
    wl, wr = CK_T / math.cos(math.radians(CK_A)), CK_T / math.cos(math.radians(CK_B))   # widths of the flat cuts
    hy = CK_H * CAP
    yc = (wl - (CK_FLAT - wr)) / (_TA + _TB)                                             # height of the inner corner
    em = [(CK_LEFT, hy), (0, 0), (CK_FLAT, 0), (CK_RIGHT, CAP), (CK_RIGHT - wr, CAP), (wl - yc * _TA, yc), (CK_LEFT + wl, hy)]
    return [(x + px * size, base - py * size) for px, py in em]


def check_d(pts):
    return "M" + "L".join(("%.2f %.2f" % p) for p in pts) + "Z"


def word():
    size, base = 100, 78
    d1, x = glyphs("Golf", 0, size, base)
    f_origin = x - (GS[CMAP[ord("f")]].width / UPM + TRACK) * size
    cx = f_origin + (stem_right("f") + CK_GAP - CK_LEFT) * size       # the f is open below its crossbar: the short arm starts there
    d2, x = glyphs("otes", cx + (CK_RIGHT - CK_TUCK + TRACK) * size, size, base)
    # The viewBox is the ink box in x (left edge of G to right edge of s) and the cap box plus 1/16 cap height above and
    # below in y. So a CSS height of 18px gives caps of exactly 16px, the box edge is the ink edge, and the caps are
    # centred in the box.
    x0 = ink("G")[0] * size
    x1 = x - TRACK * size - ink("s")[1] * size
    pad = CAP * size / 16
    vb = "%.2f %.2f %.2f %.2f" % (x0, base - CAP * size - pad, x1 - x0, CAP * size + 2 * pad)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" class="wm" role="img" aria-label="GolfVotes">'
            '<path fill="currentColor" d="%s%s"/><path class="wmc" fill="%s" d="%s"/></svg>') % (vb, d1, d2, GREEN, check_d(check_pts(cx, size, base)))


def tile(box, rx, inner):
    rect = '<rect width="%s" height="%s"%s fill="%s"/>' % (box, box, ' rx="%s"' % rx if rx else "", TILE)
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s">%s%s</svg>' % (box, box, rect, inner)


def mark_geo(box, size):
    """G origin x, baseline y and check corners of the "G + check" pair on a tile of `box`."""
    gw = GS[CMAP[ord("G")]].width / UPM
    gl, gr = ink("G")
    total = (gw - gl - gr + MARK_GAP + CK_RIGHT - CK_LEFT) * size
    x0 = (box - total) / 2 - gl * size + MARK_DX * box
    base = (box + CAP * size) / 2
    return x0, base, check_pts(x0 + (gw - gr + MARK_GAP - CK_LEFT) * size, size, base)


def mark(box, rx, size):
    """G + check on the tile (logo-mark, app icon)."""
    x0, base, pts = mark_geo(box, size)
    return tile(box, rx, '<path fill="#fff" d="%s"/><path fill="%s" d="%s"/>' % (glyphs("G", x0, size, base)[0], MINT, check_d(pts)))


def favicon(box, rx, size):
    """Browser-tab icon: the check alone, centred on its ink box. G + check does not survive 16px."""
    x = (box - (CK_RIGHT - CK_LEFT) * size) / 2 - CK_LEFT * size
    return tile(box, rx, '<path fill="%s" d="%s"/>' % (MINT, check_d(check_pts(x, size, (box + CAP * size) / 2))))


def touch_icon(path, box=180, size=96, ss=8):
    """App icon as PNG: square opaque tile (iOS masks the corners itself), same geometry as mark(), drawn 8x and scaled down."""
    from PIL import Image, ImageDraw, ImageFont
    x0, base, pts = mark_geo(box, size)
    im = Image.new("RGB", (box * ss, box * ss), TILE)
    dr = ImageDraw.Draw(im)
    dr.text((x0 * ss, base * ss), "G", font=ImageFont.truetype(FONT, size * ss, layout_engine=ImageFont.Layout.BASIC), anchor="ls", fill="#fff")
    dr.polygon([(x * ss, y * ss) for x, y in pts], fill=MINT)
    im.resize((box, box), Image.LANCZOS).save(path, optimize=True)


def inline_check():
    """The check for running text, in a box of its own ink (100 units = 1 em)."""
    w, h = (CK_RIGHT - CK_LEFT) * 100, CAP * 100
    return '<svg class="ck" viewBox="0 0 %.2f %.2f" aria-hidden="true"><path d="%s"/></svg>' % (w, h, check_d(check_pts(-CK_LEFT * 100, 100, h)))


if __name__ == "__main__":
    if "--inline" in sys.argv:
        print(inline_check())
        print("width / height = %.4f" % ((CK_RIGHT - CK_LEFT) / CAP))
        sys.exit()
    out = lambda n, s: open(os.path.join(ROOT, "static", n), "w").write(s + "\n")
    out("logo-word.svg", word())
    out("logo-mark.svg", mark(64, 15, 34))
    out("favicon.svg", favicon(64, 15, 56))
    out("logo-mark-24.svg", mark(24, 6, 13))
    try:
        touch_icon(os.path.join(ROOT, "static", "apple-touch-icon.png"))
    except ImportError:
        print("Pillow missing: static/apple-touch-icon.png not regenerated")
