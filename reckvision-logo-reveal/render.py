"""RECKVISION 9s logo reveal: renders 3840x2160 @ 30fps frames and pipes them to ffmpeg.

The RV monogram is taken pixel-for-pixel from source-logo.webp and only split into
its geometric pieces (bar+bowl, left leg, R leg, blue diagonal) for the build.
Every piece ends at zero offset with a fully open mask, so the final frame is the
untouched artwork.
"""
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 3840, 2160, 30, 9.0
NFRAMES = int(round(FPS * DUR))
BLUE = np.array([10, 44, 255], np.float32)          # #0A2CFF
WHITE = np.array([255, 255, 255], np.float32)
GRAY = np.array([180, 184, 194], np.float32)        # tagline light gray
FONT_WORD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_TAG = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

# ---------------------------------------------------------------- easing
def bezier(p1x, p1y, p2x, p2y):
    """CSS-style cubic-bezier timing function."""
    def bx(s): return 3 * p1x * s * (1 - s) ** 2 + 3 * p2x * s * s * (1 - s) + s ** 3
    def by(s): return 3 * p1y * s * (1 - s) ** 2 + 3 * p2y * s * s * (1 - s) + s ** 3
    def f(t):
        t = min(max(t, 0.0), 1.0)
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if bx(mid) < t: lo = mid
            else: hi = mid
        return by((lo + hi) / 2)
    return f

EASE_OUT = bezier(0.16, 1.0, 0.3, 1.0)      # confident landing, no overshoot
EASE_IO = bezier(0.65, 0.0, 0.35, 1.0)
EASE_BLUE = bezier(0.7, 0.0, 0.12, 1.0)     # sharper accel, smooth lock
EASE_SOFT = bezier(0.4, 0.0, 0.2, 1.0)

def prog(t, t0, t1, ease):
    return ease((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t1)

# ---------------------------------------------------------------- monogram
src = np.asarray(Image.open("source-logo.webp").convert("RGB")).astype(np.float32)
src[src.max(axis=2) < 8] = 0                         # clean codec noise to pure black
CX0, CY0, CX1, CY1 = 330, 560, 1670, 1445            # crop around the symbol
crop = src[CY0:CY1, CX0:CX1]
r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
yy, xx = np.mgrid[CY0:CY1, CX0:CX1].astype(np.float32)

is_blue = (b - r) > 30
lit = crop.max(axis=2) > 0
SLOPE = 0.735                                        # dx/dy of the white diagonals
below = yy >= 916                                    # counter bottom: legs start here
left_leg = lit & ~is_blue & below & (xx < 712 + SLOPE * (yy - 1000))
r_leg = lit & ~is_blue & below & ~left_leg & (xx <= 1040 + SLOPE * (yy - 1100))
bar = lit & ~is_blue & ~left_leg & ~r_leg
parts_src = {"bar": bar, "left": left_leg, "rleg": r_leg, "blue": is_blue & lit}

SCALE = 0.80
MW, MH = int(round((CX1 - CX0) * SCALE)), int(round((CY1 - CY0) * SCALE))

def resize_f(arr):
    return np.asarray(Image.fromarray(arr.astype(np.float32), "F").resize((MW, MH), Image.LANCZOS))

def resize_rgb(arr):
    return np.clip(np.stack([resize_f(arr[..., c]) for c in range(3)], -1), 0, 255)

parts = {k: resize_rgb(crop * m[..., None]) for k, m in parts_src.items()}
blue_alpha = np.clip(resize_f(parts_src["blue"].astype(np.float32) * 255) / 255, 0, 1)
full_alpha = np.clip(resize_f(lit.astype(np.float32) * crop.max(axis=2)) / 255, 0, 1)

# ---------------------------------------------------------------- typography
def tracked_text(text, font, tracking):
    """Return (L-mask, advances) rendering text with kerning plus extra tracking."""
    xs, x = [], 0.0
    for i, ch in enumerate(text):
        xs.append(x)
        adv = font.getlength(text[: i + 1]) - font.getlength(text[:i])
        x += adv + tracking
    width = int(np.ceil(x - tracking)) + 8
    asc, desc = font.getmetrics()
    img = Image.new("L", (width, asc + desc + 8), 0)
    d = ImageDraw.Draw(img)
    for ch, px in zip(text, xs):
        d.text((px + 4, 4), ch, font=font, fill=255)
    bbox = img.getbbox()
    return img.crop(bbox), xs, bbox

word_font = ImageFont.truetype(FONT_WORD, 208)
word_track = 0.045 * 208
word_img, word_xs, word_bbox = tracked_text("RECKVISION", word_font, word_track)
word_mask = np.asarray(word_img, np.float32) / 255
split_x = int(round(word_xs[4] + 4 - word_bbox[0] - word_track / 2))  # between K and V
word_col = np.empty(word_mask.shape + (3,), np.float32)
word_col[:, :split_x] = WHITE
word_col[:, split_x:] = BLUE
word_rgb = word_col * word_mask[..., None]

tag_font = ImageFont.truetype(FONT_TAG, 46)
tag_text = "MARKETING THAT DRIVES GROWTH"
# solve tracking so the tagline spans the wordmark width exactly
base_w = tag_font.getlength(tag_text)
tag_track = (word_mask.shape[1] - base_w) / (len(tag_text) - 1)
tag_img, _, _ = tracked_text(tag_text, tag_font, tag_track)
tag_mask = np.asarray(tag_img, np.float32) / 255
tag_rgb = GRAY * tag_mask[..., None]

# ---------------------------------------------------------------- layout
GAP1, GAP2 = 118, 74
total_h = MH + GAP1 + word_mask.shape[0] + GAP2 + tag_mask.shape[0]
top = (H - total_h) // 2
lit_cols = np.where(full_alpha.max(axis=0) > 0.02)[0]
mono_vis_cx = (lit_cols[0] + lit_cols[-1]) / 2
MX, MY = int(round(W / 2 - mono_vis_cx)), top
WX, WY = (W - word_mask.shape[1]) // 2, MY + MH + GAP1
TX, TY = (W - tag_mask.shape[1]) // 2, WY + word_mask.shape[0] + GAP2

# local grids (monogram space, final pixels)
my, mx = np.mgrid[0:MH, 0:MW].astype(np.float32)
def to_m(xs, ys):  # source coords -> monogram local coords
    return (xs - CX0) * SCALE, (ys - CY0) * SCALE

# blue diagonal centre line (for the opening trace and the finish sweep)
bl = parts_src["blue"]
rows = [y for y in range(800, 1360, 10) if bl[y - CY0].any()]
mids = [np.where(bl[y - CY0])[0].mean() + CX0 for y in rows]
k, c0 = np.polyfit(rows, mids, 1)                    # x = k*y + c0
ya, yb = 1395.0, 760.0                               # bottom (V tip) -> top end
pa = np.array(to_m(k * ya + c0, ya)); pb = np.array(to_m(k * yb + c0, yb))
axis = (pb - pa) / np.linalg.norm(pb - pa)
axis_len = np.linalg.norm(pb - pa)
along = (mx - pa[0]) * axis[0] + (my - pa[1]) * axis[1]
across = np.abs(-(mx - pa[0]) * axis[1] + (my - pa[1]) * axis[0])

# glow + contact shadow layers (precomputed, monogram space with padding)
PAD = 360
def pad_blur(alpha, radius, dy=0):
    big = np.zeros((MH + 2 * PAD, MW + 2 * PAD), np.float32)
    big[PAD + dy: PAD + dy + MH, PAD: PAD + MW] = alpha
    im = Image.fromarray((big * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(im, np.float32) / 255
glow = pad_blur(full_alpha, 150)
glow /= glow.max()
glow_tight = pad_blur(blue_alpha, 40)
glow_tight /= glow_tight.max()
shadow = pad_blur(full_alpha, 16, dy=12)

# ---------------------------------------------------------------- helpers
def shift(arr, dx, dy):
    """Sub-pixel translate (bilinear), zero fill."""
    ix, iy = int(np.floor(dx)), int(np.floor(dy))
    fx, fy = dx - ix, dy - iy
    def roll(a, sx, sy):
        out = np.zeros_like(a)
        h, w = a.shape[:2]
        xs0, xs1 = max(0, -sx), min(w, w - sx)
        ys0, ys1 = max(0, -sy), min(h, h - sy)
        if xs1 > xs0 and ys1 > ys0:
            out[ys0 + sy: ys1 + sy, xs0 + sx: xs1 + sx] = a[ys0:ys1, xs0:xs1]
        return out
    if abs(dx) < 1e-4 and abs(dy) < 1e-4:
        return arr
    return ((1 - fx) * (1 - fy) * roll(arr, ix, iy) + fx * (1 - fy) * roll(arr, ix + 1, iy)
            + (1 - fx) * fy * roll(arr, ix, iy + 1) + fx * fy * roll(arr, ix + 1, iy + 1))

def ramp(d, front, feather):
    return np.clip((front - d) / feather + 0.5, 0, 1)

def add(canvas, layer, x, y):
    h, w = layer.shape[:2]
    canvas[y:y + h, x:x + w] += layer

# ---------------------------------------------------------------- frame
def render(fi):
    t = fi / FPS
    frame = np.zeros((H, W, 3), np.float32)
    mono = np.zeros((MH, MW, 3), np.float32)

    # --- 0.0-1.2 anticipation: faint reflection + thin blue trace hinting the diagonal
    refl = prog(t, 0.25, 1.0, EASE_SOFT) * (1 - prog(t, 1.3, 2.4, EASE_SOFT))
    trace_draw = prog(t, 0.45, 1.15, EASE_IO)
    trace_lvl = 0.42 * prog(t, 0.45, 0.8, EASE_SOFT) * (1 - 0.55 * prog(t, 1.2, 1.8, EASE_SOFT))
    trace_lvl *= 1 - prog(t, 2.3, 2.75, EASE_SOFT)
    if trace_lvl > 1e-3:
        line = np.exp(-(across / 1.6) ** 2) + 0.18 * np.exp(-(across / 9.0) ** 2)
        tip = trace_draw * axis_len
        reveal = np.clip((tip - along) / 40 + 0.5, 0, 1) * (along > -10) * (along < axis_len + 10)
        head = np.exp(-((along - tip) / 55) ** 2) * 0.6 * (1 - prog(t, 1.1, 1.4, EASE_SOFT))
        mono += (BLUE * 0.85 + WHITE * 0.15) * (line * (reveal + head) * trace_lvl)[..., None]
    if refl > 1e-3:   # drawn on a frame-level patch so it is never clipped
        cx, cy = (pa + pb) / 2 + (MX, MY)
        R = 900
        gy, gx = np.mgrid[-R:R, -R:R].astype(np.float32)
        spot = 0.055 * refl * np.exp(-(gx ** 2 + gy ** 2) / 260.0 ** 2)
        add(frame, BLUE * spot[..., None], int(cx) - R, int(cy) - R)

    # --- 1.2-3.4 monogram construction
    def piece(name, p, slide_vec, d, f0, f1, feather=3.0):
        if p <= 1e-4: return
        layer = parts[name]
        if p < 1:   # mask travels with the piece, so nothing leaks before the reveal
            layer = shift(layer * ramp(d, f0 + (f1 - f0) * p, feather)[..., None],
                          *(np.array(slide_vec) * (1 - p)))
        mono[:] += layer * (0.9 + 0.1 * p)       # restrained light-up as it locks

    sx, sy = to_m(np.array([348.0, 1155.0]), np.array([916.0, 1424.0]))
    # bar+bowl: front parallel to the logo diagonals, travelling left->right
    nrm = np.array([1.0, -SLOPE]) / np.hypot(1, SLOPE)
    dbar = mx * nrm[0] + my * nrm[1]
    piece("bar", prog(t, 1.20, 2.05, EASE_OUT), (-46, 0), dbar, dbar.min() - 4, dbar.max() + 4)
    # legs: horizontal fronts (matching their flat cut ends) travelling down
    piece("left", prog(t, 1.38, 2.12, EASE_OUT), (-30 * SLOPE, -30), my, sy[0] - 4, MH + 4)
    piece("rleg", prog(t, 1.62, 2.38, EASE_OUT), (-30 * SLOPE, -30), my, sy[0] - 4, MH + 4)
    # blue diagonal: signature sweep up along its own axis
    pblue = prog(t, 2.30, 2.82, EASE_BLUE)
    if pblue > 0:
        piece("blue", pblue, tuple(-axis * 110), along, -20, axis_len + 30, feather=4.0)
        if pblue < 1:   # crisp light on the leading edge while travelling
            lead = -20 + pblue * (axis_len + 50) - 110 * (1 - pblue)
            edge = np.exp(-((along - lead) / 26) ** 2) * blue_alpha
            mono += (WHITE * 0.15 + BLUE * 0.6) * (edge * 0.4 * (1 - pblue))[..., None]

    # --- 6.5-7.6 signature finish: sweep along the blue diagonal
    ps = prog(t, 6.55, 7.15, EASE_IO)
    if 0 < ps < 1:
        pos = -120 + ps * (axis_len + 240)
        band = np.exp(-((along - pos) / 70) ** 2) * blue_alpha
        env = np.sin(np.pi * ps) ** 0.6
        mono += (np.array([120, 140, 255], np.float32) - BLUE * 0.4) * (band * env * 0.55)[..., None]

    # ambient glow + contact shadow (visible only while the glow exists)
    gl = prog(t, 6.58, 6.95, EASE_SOFT) * (1 - prog(t, 6.95, 7.58, EASE_SOFT))
    if gl > 1e-4:
        amb = (0.16 * glow + 0.10 * glow_tight) * (1 - 0.85 * shadow) * gl
        add(frame, BLUE[None, None, :] * amb[..., None], MX - PAD, MY - PAD)

    add(frame, mono, MX, MY)

    # --- 3.4-5.2 wordmark: slanted geometric wipe, left -> right with forward drift
    pw = prog(t, 3.42, 4.72, EASE_OUT)
    if pw > 0:
        h, w = word_mask.shape
        layer = shift(word_rgb, -42 * (1 - pw), 0)
        if pw < 1:
            wy, wx = np.mgrid[0:h, 0:w].astype(np.float32)
            dd = wx + (h - wy) * SLOPE * 0.55          # slant echoes the RV diagonal
            front = -h * SLOPE * 0.55 - 10 + pw * (w + h * SLOPE * 0.55 + 30)
            m = ramp(dd, front, 5.0)
            glint = np.exp(-((dd - front + 24) / 22) ** 2) * shift(word_mask, -42 * (1 - pw), 0)
            layer = layer * m[..., None] + (WHITE - layer) * (0.22 * glint * (1 - pw))[..., None]
        add(frame, layer, WX, WY)

    # --- 5.2-6.5 tagline: opacity + rising mask, settles onto baseline
    pt = prog(t, 5.22, 6.25, EASE_OUT)
    if pt > 0:
        h, w = tag_mask.shape
        oy = 16 * (1 - pt)
        layer = shift(tag_rgb, 0, oy)
        if pt < 1:
            ty = np.arange(h, dtype=np.float32)[:, None]
            m = np.clip(((h + 14) * pt - (h - ty)) / 14 + 0.5, 0, 1)
            layer = layer * (m * min(1.0, pt * 1.25))[..., None]
        add(frame, layer, TX, TY)

    return np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "frames.rgb"
    if out == "--stills":
        for s in map(float, sys.argv[2:]):
            fi = int(round(s * FPS))
            Image.frombytes("RGB", (W, H), render(fi)).save(f"still_{s:04.1f}.png")
        return
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-tune", "animation",
        "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, buf in enumerate(pool.imap(render, range(NFRAMES), chunksize=2)):
            ff.stdin.write(buf)
            if i % 30 == 0: print("frame", i, flush=True)
    ff.stdin.close(); ff.wait()


if __name__ == "__main__":
    main()
