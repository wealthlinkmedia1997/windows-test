"""RECKVISION 18s vertical brand-identity reel (1080x1920 @ 30fps).

Shot structure follows the supplied reference reel (cuts on a 120 BPM grid); all
artwork is RECKVISION's own: the RV monogram is taken from source-logo.webp and the
wordmark / UI are set in Inter.
"""
import math
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 18.0
NF = int(FPS * DUR)
BLUE = (10, 44, 255)
INK = (11, 11, 16)
PAPER = (220, 220, 224)
WHITE = (255, 255, 255)
F_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
F_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
F_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
F_REG = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
SRC = "../reckvision-logo-reveal/source-logo.webp"

# ------------------------------------------------------------------ easing
def bezier(p1x, p1y, p2x, p2y):
    def bx(s): return 3 * p1x * s * (1 - s) ** 2 + 3 * p2x * s * s * (1 - s) + s ** 3
    def by(s): return 3 * p1y * s * (1 - s) ** 2 + 3 * p2y * s * s * (1 - s) + s ** 3
    def f(t):
        if t <= 0: return 0.0
        if t >= 1: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(32):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if bx(m) < t else (lo, m)
        return by((lo + hi) / 2)
    return f

OUT = bezier(0.16, 1, 0.3, 1)
IO = bezier(0.65, 0, 0.35, 1)
EXPO = bezier(0.87, 0, 0.13, 1)

def P(u, a, b, e=OUT):
    return e((u - a) / (b - a))

def lerp(a, b, t): return a + (b - a) * t

# ------------------------------------------------------------------ monogram assets
src = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
CX0, CY0, CX1, CY1 = 330, 560, 1670, 1445
crop = src[CY0:CY1, CX0:CX1]
CW, CH = CX1 - CX0, CY1 - CY0
r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
yy, xx = np.mgrid[CY0:CY1, CX0:CX1].astype(np.float32)
is_blue = (b - r) > 30
lit = crop.max(2) > 8
SLOPE = 0.735
below = yy >= 916
m_left = lit & ~is_blue & below & (xx < 712 + SLOPE * (yy - 1000))
m_rleg = lit & ~is_blue & below & ~m_left & (xx <= 1040 + SLOPE * (yy - 1100))
m_bar = lit & ~is_blue & ~m_left & ~m_rleg
m_blue = lit & is_blue
lum = crop.max(2) / 255
CONTENT = (18, 20, 1317, 864)                      # x0,y0,x1,y1 of the symbol in crop
CCEN = np.array([(CONTENT[0] + CONTENT[2]) / 2, (CONTENT[1] + CONTENT[3]) / 2])
CONT_H = CONTENT[3] - CONTENT[1]
CONT_W = CONTENT[2] - CONTENT[0]


class Sprite:
    """An alpha mask (+ optional texture) living in monogram-crop coordinates."""
    def __init__(self, alpha, tex=None):
        ys, xs = np.where(alpha > 0.004)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        self.o = np.array([x0, y0], float)
        self.alpha = Image.fromarray((alpha[y0:y1, x0:x1] * 255).astype(np.uint8), "L")
        self.tex = None if tex is None else Image.fromarray(tex[y0:y1, x0:x1].astype(np.uint8), "RGB")
        w = alpha[y0:y1, x0:x1]
        gy, gx = np.mgrid[y0:y1, x0:x1]
        self.c = np.array([(gx * w).sum() / w.sum(), (gy * w).sum() / w.sum()])


PIECES = {k: Sprite(lum * m, crop) for k, m in
          [("bar", m_bar), ("left", m_left), ("rleg", m_rleg), ("blue", m_blue)]}
ORDER = ["bar", "left", "rleg", "blue"]
ALL = Sprite(lum * lit, crop)

# shards: monogram cut on a triangular grid
SHARDS = []
_rng = np.random.default_rng(3)
cell = 170
for gy0 in range(0, CH, cell):
    for gx0 in range(0, CW, cell):
        for tri in range(2):
            cy_, cx_ = np.mgrid[0:CH, 0:CW]
            lx, ly = (cx_ - gx0) / cell, (cy_ - gy0) / cell
            inside = (lx >= 0) & (lx < 1) & (ly >= 0) & (ly < 1)
            inside &= (lx + ly < 1) if tri == 0 else (lx + ly >= 1)
            for name, m in [("w", lit & ~is_blue), ("b", m_blue)]:
                a = lum * (m & inside)
                if (a > 0.5).sum() > 900:
                    s = Sprite(a, crop)
                    s.kind = name
                    s.seed = _rng.uniform(-1, 1, 5)
                    SHARDS.append(s)

# outline band + angular reveal map for the line-drawing shot
_al = Image.fromarray((lum * lit * 255).astype(np.uint8), "L")
_edge = ImageChops.subtract(_al.filter(ImageFilter.MaxFilter(13)), _al)
_ang = (np.arctan2(yy - CY0 - CCEN[1], xx - CX0 - CCEN[0]) + np.pi) / (2 * np.pi)
_ang = (_ang + 0.25) % 1.0
EDGE = np.asarray(_edge, np.float32) / 255
ANG = _ang.astype(np.float32)

# ------------------------------------------------------------------ drawing core
def rot(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s], [s, c]])


def place(canvas, spr, cx, cy, h, fill, rot_a=0.0, sx=1.0, sy=1.0, d=(0, 0), op=1.0,
          pivot=None, alpha_override=None):
    """Draw sprite with monogram content height h centred at (cx, cy).

    fill: RGB tuple | "tex" | callable(x0, y0, w, h) -> RGB Image in canvas space.
    rot/sx/sy apply about the sprite's own centroid (or pivot)."""
    if op <= 0.003: return
    s = h / CONT_H
    pc = spr.c if pivot is None else np.asarray(pivot, float)
    M = rot(rot_a) @ np.diag([sx, sy])
    A = s * M
    bvec = np.array([cx, cy]) + s * (pc - M @ pc + np.asarray(d, float) - CCEN)
    alpha = spr.alpha if alpha_override is None else alpha_override
    w0, h0 = alpha.size
    corners = np.array([[0, 0], [w0, 0], [0, h0], [w0, h0]], float) + spr.o
    out = corners @ A.T + bvec
    x0, y0 = np.floor(out.min(0)).astype(int) - 2
    x1, y1 = np.ceil(out.max(0)).astype(int) + 2
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, canvas.width), min(y1, canvas.height)
    if X1 <= X0 or Y1 <= Y0: return
    try:
        Ai = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        return
    t = A @ spr.o + bvec - np.array([X0, Y0])
    data = (Ai[0, 0], Ai[0, 1], -(Ai[0] @ t), Ai[1, 0], Ai[1, 1], -(Ai[1] @ t))
    size = (X1 - X0, Y1 - Y0)
    a = alpha.transform(size, Image.AFFINE, data, Image.BICUBIC)
    if op < 1: a = a.point(lambda v: int(v * op + 0.5))
    if fill == "tex":
        f = spr.tex.transform(size, Image.AFFINE, data, Image.BICUBIC)
    elif callable(fill):
        f = fill(X0, Y0, *size)
    else:
        f = tuple(int(c) for c in fill)
    canvas.paste(f, (X0, Y0), a) if not isinstance(f, tuple) else canvas.paste(f, (X0, Y0, X1, Y1), a)


def mono(canvas, cx, cy, h, fills, xf=None, op=1.0):
    """Whole monogram from its four pieces. fills: dict piece->fill or single fill."""
    for k in ORDER:
        f = fills[k] if isinstance(fills, dict) else fills
        kw = (xf or {}).get(k, {})
        place(canvas, PIECES[k], cx, cy, h, f, op=op, **kw)


def mono_bbox(cx, cy, h):
    s = h / CONT_H
    return (cx - CONT_W * s / 2, cy - CONT_H * s / 2, cx + CONT_W * s / 2, cy + CONT_H * s / 2)


def gradient(stops, angle_deg, span=None):
    """Linear gradient fill in canvas space. stops: [(pos, (r,g,b)), ...]."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    def f(x0, y0, w, h):
        gy, gx = np.mgrid[y0:y0 + h, x0:x0 + w].astype(np.float32)
        lo, hi = span if span else (0, 1)
        d = (gx * ux + gy * uy)
        d = (d - lo) / (hi - lo)
        d = np.clip(d, 0, 1)
        ps = np.array([p for p, _ in stops], np.float32)
        out = np.stack([np.interp(d, ps, [c[i] for _, c in stops]) for i in range(3)], -1)
        return Image.fromarray(out.astype(np.uint8), "RGB")
    return f


def bg(color):
    return Image.new("RGB", (W, H), color)


SS = 2  # supersampling for line work


def lines_layer(segments, width=1.5):
    """Anti-aliased line mask. segments: list of (x0,y0,x1,y1,alpha)."""
    m = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(m)
    for x0, y0, x1, y1, a in segments:
        d.line([(x0 * SS, y0 * SS), (x1 * SS, y1 * SS)], fill=int(255 * a), width=max(1, int(width * SS)))
    return m.resize((W, H), Image.BILINEAR)


def circles_layer(items, width=1.5):
    m = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(m)
    for x, y, rr, a in items:
        d.ellipse([(x - rr) * SS, (y - rr) * SS, (x + rr) * SS, (y + rr) * SS], outline=int(255 * a), width=int(width * SS))
    return m.resize((W, H), Image.BILINEAR)


# ------------------------------------------------------------------ type
_fonts = {}
def font(path, size):
    k = (path, int(size))
    if k not in _fonts: _fonts[k] = ImageFont.truetype(path, int(size))
    return _fonts[k]


def letter_xs(text, f, tracking):
    xs, x = [], 0.0
    for i in range(len(text)):
        xs.append(x)
        x += f.getlength(text[: i + 1]) - f.getlength(text[:i]) + tracking
    return xs, x - tracking


def draw_text(canvas, text, x, baseline, f, color, tracking=0.0, alphas=None, dys=None, op=1.0):
    """Left-aligned at x, per-letter opacity / y-offset."""
    xs, _ = letter_xs(text, f, tracking)
    m = Image.new("L", canvas.size, 0)
    d = ImageDraw.Draw(m)
    for i, ch in enumerate(text):
        a = (alphas[i] if alphas is not None else 1.0) * op
        if a <= 0.003 or ch == " ": continue
        dy = dys[i] if dys is not None else 0
        d.text((x + xs[i], baseline + dy), ch, font=f, fill=int(255 * min(a, 1)), anchor="ls")
    canvas.paste(color, (0, 0, canvas.width, canvas.height), m)


def text_w(text, f, tracking=0.0):
    return letter_xs(text, f, tracking)[1]


# ------------------------------------------------------------------ lockup geometry
LOCK_H = 112                                        # monogram content height in lockup
WORD_F = font(F_BOLD, 96)
WORD_TRACK = 0.02 * 96
WORD_W = text_w("RECKVISION", WORD_F, WORD_TRACK)
CAP = 96 * 0.727
GAP = 30
LOCK_MW = LOCK_H * CONT_W / CONT_H
LOCK_TOTAL = LOCK_MW + GAP + WORD_W


def lockup(canvas, cy, mono_fill, reck_col, vis_col, alphas=None, dys=None, track_extra=0.0,
           mono_op=1.0, word_op=1.0, scale=1.0):
    k = scale
    f = font(F_BOLD, 96 * k)
    tr = (WORD_TRACK + track_extra) * k
    ww = text_w("RECKVISION", f, tr)
    mw = LOCK_MW * k
    total = mw + GAP * k + ww
    x0 = W / 2 - total / 2
    mono(canvas, x0 + mw / 2, cy, LOCK_H * k, mono_fill, op=mono_op)
    base = cy + CAP * k / 2
    xs, _ = letter_xs("RECKVISION", f, tr)
    tx = x0 + mw + GAP * k
    al = alphas or [1.0] * 10
    dy = dys or [0] * 10
    draw_text(canvas, "RECK", tx, base, f, reck_col, tr, al[:4], dy[:4], op=word_op)
    draw_text(canvas, "VISION", tx + xs[4], base, f, vis_col, tr, al[4:], dy[4:], op=word_op)
    return x0, tx, base, mw, ww, f, tr


# ------------------------------------------------------------------ shots
def s_construct(u):                                 # 0.0 - 2.0
    c = bg(INK)
    rng = np.random.default_rng(11)
    segs = []
    # drafting lines drifting into alignment with the monogram's geometry
    for i in range(7):
        p = P(u, 0.1 + 0.1 * i, 1.8, IO)
        a = 0.10 + 0.08 * math.sin(u * 3 + i)
        if i < 3:   # near-horizontal
            yv = 760 + i * 170 + (1 - p) * rng.uniform(-200, 200)
            tilt = (1 - p) * rng.uniform(-60, 60)
            segs.append((-50, yv - tilt, W + 50, yv + tilt, a))
        else:       # diagonals following the RV slope
            xv = 300 + (i - 3) * 150 + (1 - p) * rng.uniform(-200, 200)
            segs.append((xv - 700 * SLOPE, 960 - 700, xv + 700 * SLOPE, 960 + 700, a))
    c.paste((120, 120, 132), (0, 0, W, H), lines_layer(segs, 1.2))
    h = lerp(300, 360, P(u, 0, 2.0, IO))
    spin = {"bar": (0.0, 1.35), "left": (0.15, 1.5), "rleg": (0.3, 1.65), "blue": (0.45, 1.85)}
    seeds = {"bar": (-1.0, -0.6, 0.9), "left": (-0.7, 0.9, -1.1), "rleg": (0.8, 0.7, 0.8), "blue": (1.0, -0.8, -0.7)}
    for k in ORDER:
        t0, t1 = spin[k]
        p = P(u, t0, t1, bezier(0.5, 0, 0.1, 1))
        sdx, sdy, sr = seeds[k]
        ang3d = (1 - p) * 2.4 * sr                  # fake rotation about a vertical axis
        sx = max(0.06, abs(math.cos(ang3d)))
        shade = 0.55 + 0.45 * abs(math.cos(ang3d * 0.8 + 0.6))
        base = np.array([235, 235, 240]) if k != "blue" else np.array([150, 160, 230])
        col = tuple((base * shade * (0.35 + 0.65 * P(u, t0 - 0.35, t0 + 0.3, IO))).astype(int))
        place(c, PIECES[k], W / 2, 960, h, col, rot_a=(1 - p) * 0.9 * sr, sx=sx,
              d=((1 - p) * 420 * sdx, (1 - p) * 380 * sdy))
    return c


def s_small_white(u):                               # 2.0 - 3.0
    c = bg(INK)
    mono(c, W / 2, 960, lerp(96, 104, u), "tex")
    return c


def s_dark_on_paper(u):                             # 3.0 - 4.0
    c = bg(PAPER)
    h = lerp(180, 190, u)
    mono(c, W / 2, 960, h, {"bar": (20, 20, 26), "left": (20, 20, 26), "rleg": (20, 20, 26), "blue": BLUE})
    return c


def s_blue_grid(u):                                 # 4.0 - 5.0
    c = bg(BLUE)
    segs = []
    step = 54
    off = (u * 18) % step
    for x in range(-step, W + step, step):
        segs.append((x + off, 0, x + off, H, 0.55))
    for y in range(-step, H + step, step):
        segs.append((0, y + off, W, y + off, 0.55))
    c.paste((6, 32, 214), (0, 0, W, H), lines_layer(segs, 1.6))
    h = lerp(250, 270, P(u, 0, 1, IO))
    tone = {"bar": (5, 26, 170), "left": (4, 20, 140), "rleg": (6, 30, 196), "blue": (3, 16, 120)}
    mono(c, W / 2 + 10, 975, h, (2, 12, 90), op=0.35)  # soft cast shadow
    mono(c, W / 2, 960, h, tone)
    return c


def s_shards(u):                                    # 5.0 - 6.0
    c = bg(INK)
    h = 440
    for s in SHARDS:
        sd = s.seed
        delay = 0.08 * (sd[4] + 1)
        p = P(u, delay, 0.82 + delay * 0.4, OUT)
        q = 1 - p
        ang3d = q * 3.0 * sd[2]
        sx = max(0.08, abs(math.cos(ang3d)))
        shade = 0.6 + 0.4 * abs(math.cos(ang3d + 0.8))
        if s.kind == "b":
            col = tuple(int(v * lerp(shade, 1, p)) for v in (10, 44, 255)) if p > 0.85 else tuple(int(v * shade) for v in (200, 205, 220))
        else:
            col = tuple([int(255 * lerp(shade, 0.97, p ** 3))] * 3)
        rad = 520 * (0.6 + 0.4 * abs(sd[3]))
        dirv = s.c - CCEN
        dirv = dirv / (np.linalg.norm(dirv) + 1e-6)
        dvec = dirv * rad * q + np.array([sd[0], sd[1]]) * 160 * q
        place(c, s, W / 2, 960, h, col, rot_a=q * 1.6 * sd[2], sx=sx, d=tuple(dvec))
    return c


GLOW_FILL = gradient([(0, (0, 210, 255)), (0.45, (10, 44, 255)), (1, (98, 40, 255))], 55, span=(520, 1320))


def s_glow(u):                                      # 6.0 - 7.0
    c = bg((0, 0, 0))
    h = lerp(200, 228, P(u, 0, 1, OUT))
    g = bg((0, 0, 0))
    mono(g, W / 2, 960, h, (30, 80, 255))
    g = g.filter(ImageFilter.GaussianBlur(26))
    c = ImageChops.screen(c, g.point(lambda v: int(v * 0.9)))
    mono(c, W / 2, 960, h, {"bar": GLOW_FILL, "left": GLOW_FILL, "rleg": GLOW_FILL,
                             "blue": gradient([(0, (60, 230, 255)), (1, (10, 44, 255))], 120, span=(-700, 400))})
    return c


def s_white_on_blue(u):                             # 7.0 - 7.5
    c = bg(BLUE)
    mono(c, W / 2, 960, 84, WHITE)
    return c


def s_wordmark_build(u):                            # 7.5 - 9.0
    c = bg(INK)
    if u < 0.38:
        h = lerp(300, 270, P(u, 0, 0.38, OUT))
        mono(c, W / 2, 960, h, "tex")
        return c
    p = P(u, 0.38, 0.75, EXPO)
    x0 = W / 2 - LOCK_TOTAL / 2
    mx = lerp(W / 2, x0 + LOCK_MW / 2, p)
    mono(c, mx, 960, lerp(270, LOCK_H, p), "tex")
    # letters arrive one by one behind a travelling hairline
    tx = x0 + LOCK_MW + GAP
    al, dys = [], []
    for i in range(10):
        a = P(u, 0.55 + i * 0.05, 0.72 + i * 0.05, OUT)
        al.append(a); dys.append((1 - a) * 18)
    base = 960 + CAP / 2
    xs, _ = letter_xs("RECKVISION", WORD_F, WORD_TRACK)
    draw_text(c, "RECK", tx, base, WORD_F, WHITE, WORD_TRACK, al[:4], dys[:4])
    draw_text(c, "VISION", tx + xs[4], base, WORD_F, BLUE, WORD_TRACK, al[4:], dys[4:])
    lp = P(u, 0.45, 0.95, IO)
    if 0 < lp < 1:
        a = math.sin(math.pi * lp) * 0.6
        c.paste((150, 150, 165), (0, 0, W, H), lines_layer([(0, 960, lp * W * 1.2, 960, a)], 1.2))
    return c


def s_annotate(u):                                  # 9.0 - 10.0
    c = bg(INK)
    x0, tx, base, mw, ww, f, tr = lockup(c, 960, (34, 34, 42), (34, 34, 42), (30, 38, 92))
    s = LOCK_H / CONT_H
    mcx = x0 + mw / 2
    def mpt(px, py):  # crop px -> canvas
        return (mcx + (px - CCEN[0]) * s, 960 + (py - CCEN[1]) * s)
    p = P(u, 0.0, 0.55, OUT)
    L = 1400 * p
    segs = []
    for (px, py), sl in [((137, 440), SLOPE), ((512, 540), SLOPE), ((866, 640), -0.67), ((1030, 640), -0.67)]:
        X, Y = mpt(px, py)
        n = math.hypot(sl, 1)
        segs.append((X - L * sl / n, Y - L / n, X + L * sl / n, Y + L / n, 0.85))
    for yv in [960 - CAP / 2, base, mpt(0, 20)[1], mpt(0, 864)[1]]:
        segs.append((W / 2 - L * 0.5, yv, W / 2 + L * 0.5, yv, 0.45))
    c.paste(BLUE, (0, 0, W, H), lines_layer(segs, 1.3))
    pc = P(u, 0.25, 0.6, OUT)
    cs = [(*mpt(137, 440), 7 * pc + 0.01, pc), (*mpt(1030, 640), 7 * pc + 0.01, pc),
          (*mpt(512, 540), 5 * pc + 0.01, pc)]
    c.paste(WHITE, (0, 0, W, H), circles_layer(cs, 1.4))
    lf = font(F_MED, 17)
    la = P(u, 0.35, 0.6, OUT)
    X, Y = mpt(137, 440)
    draw_text(c, "53.7°", X - 92, Y + 6, lf, (150, 160, 255), 1.0, op=la)
    X, Y = mpt(1030, 640)
    draw_text(c, "56.2°", X + 18, Y + 6, lf, (150, 160, 255), 1.0, op=la)
    if u < 0.12:                                    # glitch on the downbeat
        a = np.asarray(c).copy()
        rr = np.random.default_rng(int(u * 1000))
        for _ in range(9):
            y = rr.integers(700, 1220); hgt = rr.integers(6, 30)
            a[y:y + hgt] = np.roll(a[y:y + hgt], rr.integers(-60, 60), axis=1)
        c = Image.fromarray(a)
    return c


def s_lockup(u):                                    # 10.0 - 11.0
    c = bg(INK)
    lockup(c, 960, "tex", WHITE, BLUE, scale=lerp(1.0, 1.03, u))
    return c


def s_typing(u):                                    # 11.0 - 12.0
    c = bg(PAPER)
    f = font(F_MED, 64)
    full = "reck vision"
    n = min(len(full), int(u / 0.05) + (1 if u > 0.02 else 0))
    join = P(u, 0.62, 0.78, EXPO)
    sp = f.getlength(" ")
    vis_col = tuple(int(lerp(a, b, P(u, 0.8, 0.95, IO))) for a, b in zip((20, 20, 26), BLUE))
    if n < len(full) or join == 0:
        txt = full[:n]
        tw = f.getlength(txt) if txt else 0
        x = W / 2 - f.getlength(full) / 2
        draw_text(c, txt[:5], x, 980, f, (20, 20, 26))
        if n > 5: draw_text(c, txt[5:], x + f.getlength("reck "), 980, f, (20, 20, 26))
        cur_x = x + tw + 6
    else:
        wfull = f.getlength(full)
        wjoin = f.getlength("reckvision")
        tot = lerp(wfull, wjoin, join)
        x = W / 2 - tot / 2
        draw_text(c, "reck", x, 980, f, (20, 20, 26))
        draw_text(c, "vision", x + f.getlength("reck") + sp * (1 - join), 980, f, vis_col)
        cur_x = x + tot + 6
    if (u * 4) % 1 < 0.6:
        ImageDraw.Draw(c).rectangle([cur_x, 928, cur_x + 4, 994], fill=BLUE)
    return c


def s_outline(u):                                   # 12.0 - 13.0
    c = bg(PAPER)
    h = lerp(300, 320, u)
    p = P(u, 0.0, 0.7, IO)
    band = EDGE * (ANG < p)
    spr = ALL
    x0, y0 = spr.o.astype(int)
    hh, ww = spr.alpha.size[1], spr.alpha.size[0]
    ov = Image.fromarray((np.clip(band[y0:y0 + hh, x0:x0 + ww], 0, 1) * 255).astype(np.uint8), "L")
    fill_p = P(u, 0.72, 0.9, OUT)
    if fill_p > 0:
        mono(c, W / 2, 960, h, {"bar": (20, 20, 26), "left": (20, 20, 26), "rleg": (20, 20, 26), "blue": BLUE}, op=fill_p)
    place(c, spr, W / 2, 960, h, BLUE, alpha_override=ov, op=1 - fill_p * 0.9)
    return c


def s_paper_lockup(u):                              # 13.0 - 13.5
    c = bg(PAPER)
    k = P(u, 0, 0.5, OUT)
    lockup(c, 960, {"bar": (20, 20, 26), "left": (20, 20, 26), "rleg": (20, 20, 26), "blue": BLUE},
           (20, 20, 26), BLUE, track_extra=lerp(14, 0, k))
    return c


def s_flip(u):                                      # 13.5 - 14.0
    c = bg((74, 74, 84))
    a = P(u, 0, 1, IO) * math.pi
    sx = math.cos(a)
    if abs(sx) < 0.04: sx = 0.04
    for k in ORDER:
        place(c, PIECES[k], W / 2, 960, 170, WHITE, sx=abs(sx), pivot=CCEN, sy=lerp(1, 0.86, math.sin(a)))
    return c


# --- phone mockup (built once)
def build_phone():
    S = 2
    pw, ph = 720, 1480
    im = Image.new("RGBA", (pw * S, ph * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw * S - 1, ph * S - 1], radius=118 * S, fill=(52, 52, 60, 255))
    d.rounded_rectangle([5 * S, 5 * S, (pw - 5) * S, (ph - 5) * S], radius=113 * S, fill=(14, 14, 18, 255))
    sx0, sy0 = 24 * S, 24 * S
    sw, sh = (pw - 48) * S, (ph - 48) * S
    scr = Image.new("RGB", (sw // S, sh // S), (247, 248, 250))
    sd = ImageDraw.Draw(scr)
    Wd = scr.width
    sd.rounded_rectangle([Wd / 2 - 70, 14, Wd / 2 + 70, 52], radius=19, fill=(0, 0, 0))
    sd.text((48, 34), "9:41", font=font(F_SEMI, 24), fill=(20, 20, 26), anchor="lm")
    for i, hgt in enumerate([8, 12, 16, 20]):
        sd.rectangle([Wd - 120 + i * 9, 44 - hgt, Wd - 114 + i * 9, 44], fill=(20, 20, 26))
    sd.rounded_rectangle([Wd - 72, 26, Wd - 30, 44], radius=5, outline=(20, 20, 26), width=2)
    sd.rectangle([Wd - 69, 29, Wd - 40, 41], fill=(20, 20, 26))
    sd.text((36, 112), "reckvision", font=font(F_BOLD, 36), fill=(15, 15, 20), anchor="lm")
    # avatar
    av = Image.new("RGB", (170, 170), (0, 0, 0))
    am = Image.new("L", (680, 680), 0)
    ImageDraw.Draw(am).ellipse([0, 0, 679, 679], fill=255)
    ring = gradient([(0, (0, 210, 255)), (1, (10, 44, 255))], 45, span=(0, 240))(0, 0, 170, 170)
    rm = Image.new("L", (680, 680), 0)
    ImageDraw.Draw(rm).ellipse([0, 0, 679, 679], fill=255)
    ImageDraw.Draw(rm).ellipse([22, 22, 657, 657], fill=0)
    scr.paste(ring, (36, 160), rm.resize((170, 170), Image.LANCZOS))
    inner = Image.new("RGB", (146, 146), INK)
    mono(inner, 73, 73, 52, "tex")
    scr.paste(inner, (48, 172), am.resize((146, 146), Image.LANCZOS))
    for i, (num, lab) in enumerate([("128", "posts"), ("48.2K", "followers"), ("312", "following")]):
        x = 300 + i * 125
        sd.text((x, 228), num, font=font(F_BOLD, 32), fill=(15, 15, 20), anchor="mm")
        sd.text((x, 266), lab, font=font(F_REG, 21), fill=(90, 90, 100), anchor="mm")
    sd.text((36, 372), "RECKVISION", font=font(F_SEMI, 25), fill=(15, 15, 20), anchor="lm")
    sd.text((36, 408), "Marketing that drives growth.", font=font(F_REG, 23), fill=(40, 40, 48), anchor="lm")
    sd.text((36, 440), "SaaS growth · Performance · Brand", font=font(F_REG, 23), fill=(110, 110, 120), anchor="lm")
    sd.rounded_rectangle([36, 482, Wd / 2 - 8, 540], radius=14, fill=BLUE)
    sd.text(((36 + Wd / 2 - 8) / 2, 511), "Follow", font=font(F_SEMI, 24), fill=WHITE, anchor="mm")
    sd.rounded_rectangle([Wd / 2 + 8, 482, Wd - 36, 540], radius=14, fill=(228, 229, 234))
    sd.text(((Wd / 2 + 8 + Wd - 36) / 2, 511), "Message", font=font(F_SEMI, 24), fill=(15, 15, 20), anchor="mm")
    # post grid with brand tiles
    tw = (Wd - 4) / 3
    th = tw * 1.25
    gy0 = 576
    tiles = []
    for i in range(9):
        cx_, cy_ = i % 3, i // 3
        x0 = int(cx_ * (tw + 2)); y0 = int(gy0 + cy_ * (th + 2))
        t = Image.new("RGB", (int(tw), int(th)), INK)
        kind = i % 6
        if kind == 0:
            mono(t, t.width / 2, t.height / 2, 70, "tex")
        elif kind == 1:
            t.paste(BLUE, (0, 0, t.width, t.height)); mono(t, t.width / 2, t.height / 2, 70, WHITE)
        elif kind == 2:
            t.paste(PAPER, (0, 0, t.width, t.height))
            draw_text(t, "GROWTH", 18, t.height / 2 + 14, font(F_BOLD, 40), (15, 15, 20), 0.5)
            draw_text(t, "ENGINEERED.", 18, t.height / 2 + 52, font(F_BOLD, 26), BLUE, 0.5)
        elif kind == 3:
            t = gradient([(0, (0, 210, 255)), (0.5, (10, 44, 255)), (1, (98, 40, 255))], 60, span=(0, 400))(0, 0, t.width, t.height)
            mono(t, t.width / 2, t.height / 2, 70, WHITE)
        elif kind == 4:
            draw_text(t, "+248%", 16, t.height / 2 + 10, font(F_BOLD, 48), BLUE, 0)
            draw_text(t, "pipeline growth", 18, t.height / 2 + 46, font(F_MED, 20), (170, 170, 180), 0)
        else:
            t.paste(WHITE, (0, 0, t.width, t.height))
            mono(t, t.width / 2, t.height / 2 - 20, 60, {"bar": INK, "left": INK, "rleg": INK, "blue": BLUE})
            draw_text(t, "RECKVISION", t.width / 2 - text_w("RECKVISION", font(F_BOLD, 20), 1) / 2,
                      t.height / 2 + 50, font(F_BOLD, 20), INK, 1)
        scr.paste(t, (x0, y0))
    scr_big = scr.resize((sw, sh), Image.LANCZOS)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=96 * S, fill=255)
    im.paste(scr_big, (sx0, sy0), mask)
    return im.resize((pw, ph), Image.LANCZOS)


PHONE = None


def s_phone(u):                                     # 14.0 - 15.5
    global PHONE
    if PHONE is None: PHONE = build_phone()
    c = gradient([(0, (20, 22, 34)), (1, INK)], 90, span=(0, H))(0, 0, W, H)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([140, 520, 940, 1520], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    c.paste(BLUE, (0, 0, W, H), glow)
    p = P(u, 0, 0.45, OUT)
    ang = lerp(-16, -7, p) + 2.5 * P(u, 0.45, 1.5, IO)
    sc = lerp(0.92, 1.0, p) + 0.03 * P(u, 0.45, 1.5, IO)
    ph = PHONE.resize((int(PHONE.width * sc), int(PHONE.height * sc)), Image.BICUBIC).rotate(ang, Image.BICUBIC, expand=True)
    sh = Image.new("L", ph.size, 0)
    sh.paste(ph.getchannel("A").point(lambda v: v * 0.6), (0, 0))
    sh = sh.filter(ImageFilter.GaussianBlur(30))
    x = int(W / 2 - ph.width / 2 + lerp(380, 120, p))
    y = int(H / 2 - ph.height / 2 + lerp(1100, 330, p) - 40 * P(u, 0.45, 1.5, IO))
    c.paste((0, 0, 0), (x + 30, y + 50), sh)
    c.paste(ph, (x, y), ph)
    return c


def build_icon():
    S = 3
    sz = 440
    im = Image.new("RGBA", (sz * S, sz * S), (0, 0, 0, 0))
    m = Image.new("L", (sz * S, sz * S), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, sz * S - 1, sz * S - 1], radius=100 * S, fill=255)
    body = gradient([(0, (30, 30, 40)), (1, (6, 6, 10))], 90, span=(0, sz * S))(0, 0, sz * S, sz * S)
    mono(body, sz * S / 2, sz * S / 2, 175 * S, "tex")
    im.paste(body, (0, 0), m)
    return im.resize((sz, sz), Image.LANCZOS)


ICON = None


def s_icon(u):                                      # 15.5 - 16.0
    global ICON
    if ICON is None: ICON = build_icon()
    c = bg(PAPER)
    k = lerp(0.86, 1.0, P(u, 0, 0.35, bezier(0.2, 1.4, 0.4, 1)))
    ic = ICON.resize((int(440 * k), int(440 * k)), Image.BICUBIC)
    x, y = W // 2 - ic.width // 2, 900 - ic.height // 2
    sh = Image.new("L", (W, H), 0)
    sh.paste(ic.getchannel("A").point(lambda v: v * 0.45), (x, y + 34))
    c.paste((60, 60, 70), (0, 0), sh.filter(ImageFilter.GaussianBlur(34)))
    c.paste(ic, (x, y), ic)
    f = font(F_SEMI, 34)
    draw_text(c, "RECKVISION", W / 2 - text_w("RECKVISION", f, 1) / 2, 900 + 220 * k + 70, f, (20, 20, 26), 1,
              op=P(u, 0.1, 0.35, OUT))
    return c


SILVER = gradient([(0, (250, 250, 252)), (0.4, (150, 152, 162)), (0.55, (230, 232, 238)), (1, (110, 112, 122))], 75, span=(700, 1220))
HOLO = gradient([(0, (0, 230, 255)), (0.35, (10, 44, 255)), (0.65, (150, 60, 255)), (1, (255, 90, 190))], 60, span=(650, 1300))


def s_variants(u):                                  # 16.0 - 18.0
    i = min(3, int(u / 0.5))
    v = u - i * 0.5
    bgc = [(0, 0, 0), (0, 0, 0), (0, 0, 0), (24, 24, 30)][i]
    c = bg(bgc)
    turn = P(v, 0, 0.5, OUT)
    sx = lerp(0.55, 1.0, turn) if i < 2 else 1.0
    fill = [SILVER, HOLO, BLUE, (64, 64, 76)][i]
    h = lerp(190, 205, v * 2)
    for k in ORDER:
        f = fill if not (i == 0 and k == "blue") else gradient([(0, (120, 150, 255)), (1, (10, 44, 255))], 75, span=(700, 1220))
        place(c, PIECES[k], W / 2, 960, h, f, sx=sx, pivot=CCEN)
    cf = font(F_MED, 19)
    txt = "RECKVISION  ·  BRAND IDENTITY"
    draw_text(c, txt, W / 2 - text_w(txt, cf, 4) / 2, 1560, cf, (110, 110, 122), 4)
    return c


SHOTS = [
    (0.0, 2.0, s_construct), (2.0, 3.0, s_small_white), (3.0, 4.0, s_dark_on_paper),
    (4.0, 5.0, s_blue_grid), (5.0, 6.0, s_shards), (6.0, 7.0, s_glow),
    (7.0, 7.5, s_white_on_blue), (7.5, 9.0, s_wordmark_build), (9.0, 10.0, s_annotate),
    (10.0, 11.0, s_lockup), (11.0, 12.0, s_typing), (12.0, 13.0, s_outline),
    (13.0, 13.5, s_paper_lockup), (13.5, 14.0, s_flip), (14.0, 15.5, s_phone),
    (15.5, 16.0, s_icon), (16.0, 18.0, s_variants),
]


def render(fi):
    t = fi / FPS
    for a, b_, fn in SHOTS:
        if a <= t < b_:
            return np.asarray(fn(t - a).convert("RGB")).tobytes()
    return np.asarray(SHOTS[-1][2](SHOTS[-1][1] - SHOTS[-1][0] - 1e-3).convert("RGB")).tobytes()


def main():
    if sys.argv[1] == "--stills":
        for s in map(float, sys.argv[2:]):
            Image.frombytes("RGB", (W, H), render(int(round(s * FPS)))).save(f"{sys.argv[0][:0]}still_{s:05.2f}.png")
        return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                           "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", sys.argv[1]],
                          stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, buf in enumerate(pool.imap(render, range(NF), chunksize=3)):
            ff.stdin.write(buf)
            if i % 60 == 0: print("frame", i, flush=True)
    ff.stdin.close(); ff.wait()


if __name__ == "__main__":
    main()
