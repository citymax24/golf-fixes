"""Draws the hole of the home page finder the way a golf architect draws a plan by hand, and writes build/course.svg
(an SVG fragment in a 320 x 360 box that build.py inlines). Run: python3 build/make_course.py
(needs shapely; the output is committed, the site build does not run this).

The techniques are those of a hand-drafted plan:
- natural edges are inked freehand: a slight wobble, the pen lifted and set down again so strokes overlap;
- construction is ruled: the line of play is a straight dash-dot line, the distances are compass arcs from the pin;
- three pen weights (0.6 edges of sand, green and water; 0.42 fairway; 0.26 everything fine);
- colour is marker: one green laid in parallel strokes whose overlaps show as darker seams, kept a little inside the
  ink line, a second layer on the green;
- sand is stippled by hand, denser on the shadow side; light comes from the north-west, so trees throw a shadow to
  the south-east and bunkers are darker along their north-west edge;
- trees are plan symbols (canopy, trunk point, a few branches), water has shore lines, the tee has crossed corners;
- a title, a scale bar and a north arrow.
Everything is deterministic (fixed seed), so the drawing only changes when this file does."""
import math
import os
import random
import re

from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "build.py"), encoding="utf-8").read()
grab = lambda name: eval(re.search(rf"^{name} = (.*)$", src, re.M).group(1))
FAIRWAY, GREEN, POND = grab("COURSE_FAIRWAY"), grab("COURSE_GREEN"), grab("COURSE_POND")
BUNKERS, TREES = grab("COURSE_BUNKERS"), grab("COURSE_TREES")
TEE, CUP = (160, 326), (160, 46)   # the ball on the tee, the hole
YARDS = 150                       # tee to pin: the plan is true to scale as a par 3 of 150 yards
U = (TEE[1] - CUP[1]) / YARDS     # drawing units per yard (1.87): green 36 x 31 yd, approach 40 to 48 yd wide, tee 10 x 16 yd
R = random.Random(11)
LIGHT = (-0.7071, -0.7071)        # direction towards the light (north-west)


def f(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    if s == "-0":
        s = "0"
    return s[1:] if s.startswith("0.") else ("-" + s[2:] if s.startswith("-0.") else s)


def path_pts(d, n=10):
    """Points of an SVG path made of M/L/C/c/Z segments."""
    tok = re.findall(r"[MLCcZz]|-?\d*\.?\d+", d)
    pts, cur, i, cmd = [], (0, 0), 0, None
    while i < len(tok):
        t = tok[i]
        if t in "MLCcZz":
            cmd = t
            i += 1
            if t in "Zz":
                continue
        if cmd in "ML":
            cur = (float(tok[i]), float(tok[i + 1]))
            pts.append(cur)
            i += 2
        else:
            v = [float(x) for x in tok[i:i + 6]]
            i += 6
            if cmd == "c":
                v = [v[k] + cur[k % 2] for k in range(6)]
            p0, p1, p2, p3 = cur, (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            for k in range(1, n + 1):
                t_ = k / n
                pts.append(tuple((1 - t_) ** 3 * p0[j] + 3 * (1 - t_) ** 2 * t_ * p1[j] + 3 * (1 - t_) * t_ ** 2 * p2[j] + t_ ** 3 * p3[j] for j in (0, 1)))
            cur = p3
    return pts


def resample(coords, step, closed):
    """Points at equal distances along a polyline."""
    line = LineString(list(coords) + ([coords[0]] if closed else []))
    n = max(6, round(line.length / step))
    return [line.interpolate(i / (n if closed else n - 1), normalized=True).coords[0] for i in range(n)]


def noise(waves=((29, 1), (13, .55), (61, .8))):
    """Smooth pseudo-random function of the distance along a line, between about -1 and 1."""
    ph = [R.uniform(0, 6.283) for _ in waves]
    tot = sum(a for _, a in waves)
    return lambda s: sum(a * math.sin(6.283 * s / w + p) for (w, a), p in zip(waves, ph)) / tot


def normals(pts, closed):
    """Unit normals to the right of the direction of travel (outward for a counter-clockwise ring in y-down... see use)."""
    n, out = len(pts), []
    for i in range(n):
        a = pts[(i - 1) % n] if closed or i > 0 else pts[i]
        b = pts[(i + 1) % n] if closed or i < n - 1 else pts[i]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1
        out.append((ty / ln, -tx / ln))
    return out


def cr(pts, closed=False):
    """A smooth curve through the points (Catmull-Rom as cubic Beziers), written with relative coordinates."""
    n = len(pts)
    g = (lambda i: pts[i % n]) if closed else (lambda i: pts[min(max(i, 0), n - 1)])
    cur = (round(pts[0][0], 1), round(pts[0][1], 1))
    d = [f"M{f(cur[0])} {f(cur[1])}"]
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = g(i - 1), g(i), g(i + 1), g(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        end = (round(p2[0] - cur[0], 1), round(p2[1] - cur[1], 1))                     # relative to where the pen really is, so rounding does not add up
        d.append("c" + " ".join(f(v) for v in (c1[0] - cur[0], c1[1] - cur[1], c2[0] - cur[0], c2[1] - cur[1], end[0], end[1])).replace(" -", "-"))
        cur = (round(cur[0] + end[0], 1), round(cur[1] + end[1], 1))
    return "".join(d) + ("z" if closed else "")


def poly_d(geom, tol=.25):
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty or g.geom_type != "Polygon":
            continue
        c = list(g.exterior.simplify(tol).coords)[:-1]
        out.append("M" + "L".join(f"{f(x)} {f(y)}" for x, y in c) + "Z")
    return "".join(out)


def ring(poly, step):
    """Evenly spaced points on the outline, with unit normals pointing out of the shape."""
    pts = resample(list(orient(poly, 1.0).exterior.coords)[:-1], step, True)
    nr = normals(pts, True)
    c = poly.centroid
    if sum((p[0] - c.x) * n[0] + (p[1] - c.y) * n[1] for p, n in zip(pts, nr)) < 0:
        nr = [(-a, -b) for a, b in nr]
    return pts, nr


def freehand(poly, step=4.0, amp=.32, strokes=3):
    """The outline inked by hand: several strokes that overlap where the pen was set down again."""
    pts, nr = ring(poly, step)
    n = len(pts)
    starts = sorted({int((k + R.uniform(-.25, .25)) * n / strokes) % n for k in range(strokes)})
    d = []
    for k, a in enumerate(starts):
        b = starts[(k + 1) % len(starts)]
        length = (b - a) % n or n
        nz, lift = noise(), R.uniform(-.12, .12)
        seg = []
        for j in range(length + R.randint(1, 2) + 1):
            i = (a + j) % n
            off = amp * nz(j * step) + lift
            seg.append((pts[i][0] + nr[i][0] * off, pts[i][1] + nr[i][1] * off))
        d.append(cr(seg))
    return "".join(d)


def lit_side(poly, step=3.0, want=-1, limit=.25):
    """The parts of the outline that face the light (want=1) or away from it (want=-1), as open curves."""
    pts, nr = ring(poly, step)
    n = len(pts)
    flag = [want * (a * LIGHT[0] + b * LIGHT[1]) > limit for a, b in nr]
    if all(flag) or not any(flag):
        return ""
    start = next(i for i in range(n) if flag[i] and not flag[i - 1])
    d, run = [], []
    for j in range(n + 1):
        i = (start + j) % n
        if flag[i] and j < n:
            run.append(pts[i])
        elif run:
            if len(run) > 2:
                d.append(cr(run))
            run = []
    return "".join(d)


def marker(poly, angle, width=9.5, lap=1.7, inset=.55, ragged=.75):
    """A marker fill: (the area the marker covered, the seams where two strokes overlap). The area stays a little
    inside the ink line and does not follow it exactly."""
    pts, nr = ring(poly, 3.0)
    nz = noise(((17, 1), (41, .8)))
    area = Polygon([(p[0] - n[0] * (inset + ragged * nz(i * 3.0)), p[1] - n[1] * (inset + ragged * nz(i * 3.0))) for i, (p, n) in enumerate(zip(pts, nr))]).buffer(0)
    c = area.centroid
    seams, k = [], -40
    while k <= 40:
        w = lap * R.uniform(.7, 1.3)
        strip = Polygon([(-900, -w / 2), (900, -w / 2), (900, w / 2), (-900, w / 2)])
        strip = affinity.translate(affinity.rotate(strip, angle, origin=(0, 0)), c.x - math.sin(math.radians(angle)) * (k * (width - lap) + R.uniform(-.6, .6)),
                                   c.y + math.cos(math.radians(angle)) * (k * (width - lap) + R.uniform(-.6, .6)))
        hit = strip.intersection(area)
        if not hit.is_empty:
            seams.append(hit)
        k += 1
    return poly_d(area), "".join(poly_d(s, .15) for s in seams)


def stipple(poly, grid=1.42):
    """Dots set by hand: evenly spaced, dense along the north-west edge and thinning out across the sand."""
    minx, miny, maxx, maxy = poly.bounds
    span = max(maxx - minx, maxy - miny)
    c, edge, d = poly.centroid, poly.exterior, []
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            px, py = x + R.uniform(.1, grid - .1), y + R.uniform(.1, grid - .1)
            pt = Point(px, py)
            if poly.contains(pt):
                t = ((px - c.x) * LIGHT[0] + (py - c.y) * LIGHT[1]) / span          # > 0 towards the light
                near = math.exp(-edge.distance(pt) / 1.6)
                if R.random() < .07 + .62 * max(0, min(1, t * 1.7 + .42)) ** 1.5 + .16 * near:
                    d.append((round(px, 1), round(py, 1)))
            x += grid
        y += grid
    out, cur = [], None
    for q in d:
        out.append(f"M{f(q[0])} {f(q[1])}h0" if cur is None else ("m" + f(q[0] - cur[0]) + " " + f(q[1] - cur[1]) + "h0").replace(" -", "-"))
        cur = q
    return "".join(out)


fair, green, pond = (Polygon(path_pts(d)).buffer(0) for d in (FAIRWAY, GREEN, POND))
# A par 3 has no fairway from the tee: the mown approach starts about 45 yards out and is a little narrower than the
# shape the page used before. The tee is its own pad, longer than wide, square to the line of play.
# Measures follow real holes: the approach is about as wide as the green (27 to 36 yards), the green is 33 x 28 yards,
# the bunkers sit at the green and at the approach, the pond lies beside the approach on the left.
fair = affinity.scale(fair, .6, 1, origin=(160, 0)).intersection(Polygon([(0, 0), (320, 0), (320, 246), (0, 246)])).buffer(-8, 16).buffer(8, 16)
green = affinity.scale(green, .9, .9, origin=CUP)
pond = affinity.rotate(affinity.scale(pond, 1.3, 2.05), -24)
pond = affinity.translate(pond, 85 - pond.centroid.x, 215 - pond.centroid.y)
tee = affinity.rotate(Polygon([(151, 311), (169, 311), (169, 341), (151, 341)]), -4, origin=TEE)
# bunkers: one shape per group of circles, the edge made irregular like a real sand line
sands = []
for g in unary_union([Point(x, y).buffer(r, 16) for x, y, r in BUNKERS]).buffer(5, 12).buffer(-5.8, 12).geoms:
    pts, nr = ring(g, 2.2)
    nz = noise(((9, 1), (21, .9), (5, .35)))
    sands.append(Polygon([(p[0] + n[0] * .95 * nz(i * 2.2), p[1] + n[1] * .95 * nz(i * 2.2)) for i, (p, n) in enumerate(zip(pts, nr))]).buffer(0))
# room for the title (bottom left) and the north arrow (bottom right)
trees = [(x, y, r) for x, y, r in TREES if not (y > 306 and (x < 112 or x > 268)) and not (abs(x - 262) < 20 and abs(y - 96) < 10)]

MASK = ('<defs><linearGradient id="ybgh"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".09" stop-color="#fff"/><stop offset=".91" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><linearGradient id="ybgv" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".04" stop-color="#fff"/><stop offset=".95" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<mask id="ybmh" maskUnits="userSpaceOnUse" x="0" y="0" width="320" height="360"><rect width="320" height="360" fill="url(#ybgh)"/></mask>'
        '<mask id="ybmv" maskUnits="userSpaceOnUse" x="0" y="0" width="320" height="360"><rect width="320" height="360" fill="url(#ybgv)"/></mask>')
el = [MASK]
INK = "fill:none;stroke:var(--pen);stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke"
for i, lobes in enumerate((9, 11, 8), 1):       # three tree symbols of radius 1, placed with <use>
    ph, nz = R.uniform(0, 6.283), noise(((2.1, 1), (.9, .5)))
    rad = lambda a: 1 + .06 * math.sin(lobes * a + ph) + .03 * nz(a)
    can = [(rad(a) * math.cos(a), rad(a) * math.sin(a)) for a in (k * 6.283 / 30 + .2 for k in range(29))]     # stops short of closing: a pen lift
    g2 = lambda v: (lambda t: t[1:] if t.startswith("0.") else ("-" + t[2:] if t.startswith("-0.") else t))(f"{v:.2f}".rstrip("0").rstrip(".") or "0")
    cd = f"M{g2(can[0][0])} {g2(can[0][1])}"
    for k in range(len(can) - 1):
        p0, p1, p2, p3 = can[max(k - 1, 0)], can[k], can[k + 1], can[min(k + 2, len(can) - 1)]
        cd += f"C{g2(p1[0] + (p2[0] - p0[0]) / 6)} {g2(p1[1] + (p2[1] - p0[1]) / 6)} {g2(p2[0] - (p3[0] - p1[0]) / 6)} {g2(p2[1] - (p3[1] - p1[1]) / 6)} {g2(p2[0])} {g2(p2[1])}"
    twigs = "".join(f"M{g2(math.cos(a) * .15)} {g2(math.sin(a) * .15)}L{g2(math.cos(a + w) * ln)} {g2(math.sin(a + w) * ln)}"
                    for a, w, ln in ((k * 6.283 / 5 + R.uniform(-.3, .3), R.uniform(-.25, .25), R.uniform(.4, .7)) for k in range(5)))
    el.append(f'<g id="yt{i}"><circle style="fill:var(--paper)" r="1"/><circle style="fill:var(--acc2);fill-opacity:.09" cx="-.07" cy="-.06" r=".86"/>'
              f'<path style="{INK};stroke-width:.55px;stroke-opacity:.6" d="{cd}"/><path style="{INK};stroke-width:.4px;stroke-opacity:.34" d="{twigs}"/>'
              f'<circle style="fill:var(--pen);fill-opacity:.65" r=".07"/></g>')
el.append('</defs><g mask="url(#ybmh)"><g mask="url(#ybmv)">')      # no frame: the drawing runs out softly at the edges

# 1 tree shadows, then the canopies (large ones first)
el.append('<g class="ysh">' + "".join(f'<circle cx="{f(x + r * .3)}" cy="{f(y + r * .3)}" r="{f(r * .94)}"/>' for x, y, r in trees) + '</g>')
for x, y, r in sorted(trees, key=lambda t: -t[2]):
    el.append(f'<use href="#yt{R.randint(1, 3)}" transform="translate({f(x)} {f(y)})rotate({R.randint(0, 359)})scale({f(r * .92)})"/>')

# 3 fairway: marker first, ink on top
area, seams = marker(fair, 28, width=12.5, lap=1.5)
el.append(f'<path class="ywf" d="{area}"/><path class="yws" d="{seams}"/>')
el.append(f'<path class="y2" d="{freehand(fair, 4.2, .34, 4)}"/>')

# 4 water: the shore, one shore line inside, and broken ripple lines that thin out towards the far side
el.append(f'<path class="yp" d="{poly_d(pond, .1)}"/><path class="y1" d="{freehand(pond, 3.2, .22, 2)}"/>')
el.append(f'<path class="y3" stroke-dasharray="13 2.4 6 3" d="{cr(resample(list(pond.buffer(-1.9, 12).exterior.coords)[:-1], 3.5, True), True)}"/>')
inner, rip = pond.buffer(-4.2, 12), ""
minx, miny, maxx, maxy = inner.bounds
y, k = miny + 1.2, 0
while y < maxy:
    hit = LineString([(minx - 5, y), (maxx + 5, y)]).intersection(inner)
    for g in getattr(hit, "geoms", [hit]):
        if g.is_empty:
            continue
        x0, x1 = g.bounds[0], g.bounds[2]
        x = x0 + R.uniform(0, 3)
        while x < x1 - 1.5:
            ln = min(R.uniform(3.5, 9) * (1 - .45 * k / 6), x1 - x)
            rip += f"M{f(x)} {f(y + R.uniform(-.2, .2))}h{f(ln)}"
            x += ln + R.uniform(2.2, 4.5) * (1 + .5 * k / 6)
    y += 2.7 + .25 * k
    k += 1
el.append(f'<path class="y3" d="{rip}"/>')

# 5 tee: marker, ruled edges that cross at the corners, two tee markers
ta, ts = marker(tee, 28, inset=.8, ragged=.3)
c = list(tee.exterior.coords)[:-1]
ruled = ""
for i in range(4):
    a, b = c[i], c[(i + 1) % 4]
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / ln * 1.5, (b[1] - a[1]) / ln * 1.5
    ruled += f"M{f(a[0] - ux)} {f(a[1] - uy)}L{f(b[0] + ux)} {f(b[1] + uy)}"
el.append(f'<path class="ywf" d="{ta}"/><path class="y2" d="{ruled}"/>'
          f'<circle class="yi" cx="{f(TEE[0] - 6.4)}" cy="{f(TEE[1] - 3.6)}" r=".7"/><circle class="yi" cx="{f(TEE[0] + 6.4)}" cy="{f(TEE[1] - 4.5)}" r=".7"/>')   # tee markers, the ball just behind them

# 6 green: collar, two layers of marker, ink, contours that fall towards the front right
el.append(f'<path class="y3" stroke-dasharray="1.6 1.5" d="{cr(resample(list(green.buffer(3.4, 12).exterior.coords)[:-1], 4, True), True)}"/>')
area, seams = marker(green, 28, inset=.5, ragged=.5)
area2, seams2 = marker(green, -24, width=8, inset=.9, ragged=.6)
el.append(f'<path class="ywf" d="{area}"/><path class="ywg" d="{area2}"/><path class="yws" d="{seams}{seams2}"/>')
el.append(f'<path class="y1" d="{freehand(green, 3.6, .26, 3)}"/>')
gc = green.centroid
for scale, dx, dy in ((.72, -2.2, -2.6), (.44, -4.2, -5)):
    con = affinity.translate(affinity.scale(green, scale, scale, origin=gc), dx, dy)
    pts, nr = ring(con, 3.2)
    nz = noise(((11, 1), (23, .8)))
    el.append(f'<path class="y3" d="{cr([(p[0] + n[0] * .5 * nz(i * 3.2), p[1] + n[1] * .5 * nz(i * 3.2)) for i, (p, n) in enumerate(zip(pts, nr))][:-2])}"/>')

# 7 bunkers: paper, stipple, ink, a heavier line where the face is in shadow
el.append('<path class="yp" d="' + "".join(poly_d(s, .1) for s in sands) + '"/>')
el.append('<path class="yst" d="' + "".join(stipple(s) for s in sands) + '"/>')
el.append('<path class="y1" d="' + "".join(freehand(s, 3.0, .2, 2) for s in sands) + '"/>')
el.append('<path class="ya" d="' + "".join(lit_side(s.buffer(-.25, 8), 2.6, 1, .35) for s in sands) + '"/>')

# 8 construction: line of play (ruled) and the distances to the pin (compass), the way course markers count
el.append(f'<path class="yc" d="M{TEE[0]} {TEE[1] + 19}V{CUP[1] + 3}"/>')
for yd in (50, 100):
    r = yd * U
    arc = Point(CUP).buffer(r, 128).exterior.intersection(fair.buffer(5.5))
    for g in getattr(arc, "geoms", [arc]):
        cs = sorted(g.coords)
        if len(cs) < 3:
            continue
        el.append(f'<path class="y3 yr" d="M{f(cs[0][0])} {f(cs[0][1])}A{f(r)} {f(r)} 0 0 0 {f(cs[-1][0])} {f(cs[-1][1])}"/>'
                  f'<text class="yn" x="{f(cs[0][0] - 2.6)}" y="{f(cs[0][1] + 1.9)}" text-anchor="end">{yd}</text>')

# 9 title, scale bar, north arrow (outside the fade)
el.append('</g></g><g class="yfix">')
s50 = 25 * U
el.append(f'<text class="yn ytl" x="10" y="325">HOLE 7</text><text class="yn" x="10" y="333.5">PAR 3 · {YARDS} YDS · HCP 15</text>'
          f'<g transform="translate(10 348)"><path class="y3" d="M0 0H{f(2 * s50)}M0 -2.6V0M{f(s50)} -2.6V0M{f(2 * s50)} -2.6V0"/><path class="yi" d="M0 -1.3H{f(s50)}V0H0Z"/>'
          f'<text class="yn" x="0" y="-4.6">0</text><text class="yn" x="{f(s50)}" y="-4.6" text-anchor="middle">25</text><text class="yn" x="{f(2 * s50)}" y="-4.6" text-anchor="end">50 YDS</text></g>')
el.append('<g transform="translate(296 336)"><circle class="y3" r="7.5"/><path class="y3" d="M0 9.5V-9.5M-9.5 0H-7.5M7.5 0H9.5"/><path class="yi" d="M0 -6.2L-2.5 2.6L0 1.2Z"/>'
          '<path class="y3" d="M0 -6.2L2.5 2.6L0 1.2Z"/><text class="yn" x="0" y="-12" text-anchor="middle">N</text></g>')

el.append('</g>')
out = "".join(el)
open(os.path.join(HERE, "course.svg"), "w").write(out + "\n")
print("course.svg:", len(out), "bytes,", len(trees), "trees")
