"""Draws the hole of the home page finder as an architect's plan and writes build/course.svg (an SVG fragment in a
320 x 360 box that build.py inlines). Run: python3 build/make_course.py (needs shapely; the site build does not).

Pen weights like a set of technical pens: 0.7 for the edges of play (fairway, green, bunkers, water, tee), 0.35 for
everything inside them (mowing line, green contours, hatching, centre line, yardage ticks), trees as plan symbols
(canopy circle with a centre point), sand stippled, water hatched, a dash-dot centre line with yardages to the green,
a north arrow and a scale bar."""
import importlib.util
import math
import os
import re

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "build.py"), encoding="utf-8").read()
grab = lambda name: eval(re.search(rf"^{name} = (.*)$", src, re.M).group(1))
FAIRWAY, GREEN, POND = grab("COURSE_FAIRWAY"), grab("COURSE_GREEN"), grab("COURSE_POND")
BUNKERS, TREES = grab("COURSE_BUNKERS"), grab("COURSE_TREES")
TEE, CUP = (160, 327), (160, 46)
YARDS = 380                      # length of the hole in the drawing (tee to cup), for the yardage marks


def path_pts(d, n=8):
    """Points of an SVG path made of M/L/C/c/Z segments."""
    tok = re.findall(r"[MLCcZz]|-?\d*\.?\d+", d)
    pts, cur, i, cmd = [], (0, 0), 0, None
    while i < len(tok):
        t = tok[i]
        if t in "MLCcZz":
            cmd = t; i += 1
            if t in "Zz":
                continue
        if cmd in "ML":
            cur = (float(tok[i]), float(tok[i + 1])); pts.append(cur); i += 2
        elif cmd in "Cc":
            v = [float(x) for x in tok[i:i + 6]]; i += 6
            if cmd == "c":
                v = [v[k] + cur[k % 2] for k in range(6)]
            p0, p1, p2, p3 = cur, (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            for k in range(1, n + 1):
                t_ = k / n
                pts.append(tuple((1 - t_) ** 3 * p0[j] + 3 * (1 - t_) ** 2 * t_ * p1[j] + 3 * (1 - t_) * t_ ** 2 * p2[j] + t_ ** 3 * p3[j] for j in (0, 1)))
            cur = p3
    return pts


def d_of(geom):
    """SVG path data of a polygon, multipolygon or line."""
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty:
            continue
        rings = [g.exterior, *g.interiors] if g.geom_type == "Polygon" else [g]
        for r in rings:
            c = list(r.coords)
            if len(c) > 12:
                c = list(LineString(c).simplify(0.15).coords)
            f = lambda v: f"{v:.1f}".rstrip("0").rstrip(".")
            out.append("M" + "L".join(f"{f(x)} {f(y)}" for x, y in c) + ("Z" if g.geom_type == "Polygon" else ""))
    return "".join(out)


def hatch(poly, step, angle=0):
    """Parallel lines across a polygon."""
    minx, miny, maxx, maxy = poly.bounds
    lines, y = [], miny - (maxx - minx)
    a = math.radians(angle)
    while y < maxy + (maxx - minx):
        ln = LineString([(minx - 50, y), (maxx + 50, y + (maxx - minx + 100) * math.tan(a))]).intersection(poly)
        if not ln.is_empty:
            lines.append(ln)
        y += step
    return d_of(unary_union(lines)) if lines else ""


fair, green, pond = Polygon(path_pts(FAIRWAY)).buffer(0), Polygon(path_pts(GREEN)).buffer(0), Polygon(path_pts(POND)).buffer(0)
sand = unary_union([Point(x, y).buffer(r, 8) for x, y, r in BUNKERS]).buffer(5, 12).buffer(-5.8, 12)   # one smooth shape per bunker
tee = Polygon([(146, 316), (174, 313.5), (176, 337.5), (148, 340)])

el = []
# trees: plan symbols, the larger ones first so the smaller sit on top
for x, y, r in sorted(TREES, key=lambda t: -t[2]):
    el.append(f'<circle class="yt" cx="{x:.1f}" cy="{y:.1f}" r="{r * .92:.1f}"/><circle class="ytc" cx="{x:.1f}" cy="{y:.1f}" r=".6"/>')
el.append(f'<path class="yf" d="{d_of(fair)}"/>')
el.append(f'<path class="yh" d="{d_of(fair.buffer(-4.5, 8).exterior)}" stroke-dasharray="3 2"/>')            # mowing line of the first cut
el.append(f'<path class="yw" d="{d_of(pond)}"/><path class="yh" d="{hatch(pond.buffer(-1.2), 2.4)}"/>')
el.append(f'<path class="yb" d="{d_of(tee)}"/><path class="yh" d="{hatch(tee.buffer(-1), 3, 35)}"/>')
el.append(f'<path class="yh" d="{d_of(green.buffer(3.2, 8).exterior)}" stroke-dasharray="1.5 1.5"/>')          # fringe
el.append(f'<path class="yg" d="{d_of(green)}"/>')
for k in (4, 8.5, 13):                                                                                          # contours on the green
    c = green.buffer(-k, 8)
    if not c.is_empty:
        el.append(f'<path class="yh" d="{d_of(c.exterior)}"/>')
el.append(f'<path class="ys" d="{d_of(sand)}"/>')
# centre line: middle of the fairway at each height, from the tee to the cup
mids = []
for y in range(326, 40, -6):
    seg = LineString([(0, y), (320, y)]).intersection(fair if y > 76 else green.buffer(6))
    if not seg.is_empty:
        b = seg.bounds; mids.append(((b[0] + b[2]) / 2, y))
mids = [TEE] + mids[1:] + [CUP]
el.append(f'<path class="yc" d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in mids)}"/>')
# yardages to the cup: a tick across the fairway and the number beside it
u = (TEE[1] - CUP[1]) / YARDS
for yd in (100, 150, 200, 250):
    y = CUP[1] + yd * u
    seg = LineString([(0, y), (320, y)]).intersection(fair)
    if seg.is_empty:
        continue
    b = seg.bounds
    el.append(f'<path class="yh" d="M{b[0]:.1f} {y:.1f}H{b[2]:.1f}"/><text class="yn" x="{b[2] + 3:.1f}" y="{y + 2:.1f}">{yd}</text>')
# north arrow and scale bar
el.append('<g class="yna" transform="translate(296 334)"><circle class="yh" r="7"/><path class="yfill" d="M0 -6L2.4 2.5L0 1L-2.4 2.5Z"/><text class="yn" x="0" y="-9" text-anchor="middle">N</text></g>')
s50 = 50 * u
el.append(f'<g transform="translate(14 346)"><path class="yh" d="M0 0H{2 * s50:.1f}M0 -2.5V0M{s50:.1f} -2.5V0M{2 * s50:.1f} -2.5V0"/><path class="yfill" d="M0 -1H{s50:.1f}V0H0Z"/>'
          f'<text class="yn" x="0" y="-5">0</text><text class="yn" x="{s50:.1f}" y="-5" text-anchor="middle">50</text><text class="yn" x="{2 * s50:.1f}" y="-5" text-anchor="end">100 yd</text></g>')
open(os.path.join(HERE, "course.svg"), "w").write("".join(el) + "\n")
print("course.svg:", len("".join(el)), "bytes")
