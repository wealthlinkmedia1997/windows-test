"""Synthesizes the 15 s launch soundtrack at 120 BPM (30 beats) from ../cues.json.

Bright pluck-pop bed (airy, like the reference) + UI foley placed on the cue
sheet: clicks, keyboard ticks while text types, whooshes on scene changes.
Writes track.wav.
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
CUES = json.loads((HERE.parent / "cues.json").read_text())
SR = 48000
B = 60 / CUES["bpm"]
DUR = CUES["duration"]
N = int(SR * DUR)
rng = np.random.default_rng(11)


def T(n):
    return np.arange(n) / SR


def ex(n, d):
    return np.exp(-T(n) / d)


def place(buf, sig, at, gain=1.0):
    i = int(round(at * SR))
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def lp(x, cutoff):
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def hp(x, cutoff):
    return x - lp(x, cutoff)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


# ---------- instruments ----------
def kick(g=1.0):
    n = int(0.4 * SR)
    t = T(n)
    f = 48 + 120 * np.exp(-t / 0.03)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * ex(n, 0.14)
    return np.tanh(1.6 * s) * g


def clap():
    n = int(0.28 * SR)
    e = np.zeros(n)
    for k, o in enumerate([0, 0.009, 0.018]):
        i = int(o * SR)
        e[i:] += ex(n - i, 0.01 if k < 2 else 0.08)
    return hp(rng.standard_normal(n) * e, 900) * 0.7


def hat(d=0.03):
    n = int(0.15 * SR)
    return hp(rng.standard_normal(n), 7000) * ex(n, d) * 0.35


def pluck(m, d=0.22):
    n = int(0.6 * SR)
    t = T(n)
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 * np.exp(-t * (6 + 5 * k)) for k in range(1, 7))
    return s * ex(n, d) * 0.5


def bell(m):
    n = int(1.6 * SR)
    t = T(n)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t + 1.6 * np.sin(2 * np.pi * f * 3.5 * t) * ex(n, 0.25))
    return s * ex(n, 0.6) * 0.3


def pad(ms, n):
    t = T(n)
    s = np.zeros(n)
    for m in ms:
        for d in (-0.006, 0, 0.006):
            ph = 2 * np.pi * hz(m) * (1 + d) * t
            s += 2 * ((ph / (2 * np.pi)) % 1) - 1
    s /= 3 * len(ms)
    env = np.minimum(1, t / 0.25) * np.minimum(1, (n / SR - t) / 0.2)
    return lp(s, 1800) * env


def ui_click():
    n = int(0.07 * SR)
    t = T(n)
    return (np.sin(2 * np.pi * 1900 * t) * ex(n, 0.01) * 0.6
            + hp(rng.standard_normal(n), 3000) * ex(n, 0.0015) * 0.7
            + np.sin(2 * np.pi * 180 * t) * ex(n, 0.012) * 0.5)


def key_tick():
    n = int(0.035 * SR)
    return hp(rng.standard_normal(n), 2500) * ex(n, 0.004) * 0.35


def whoosh(length=0.45):
    n = int(length * SR)
    t = T(n) / (n / SR)
    shape = np.sin(np.pi * t) ** 2
    return lp(rng.standard_normal(n), 400 + 5000 * shape) * shape * 0.45


def impact():
    n = int(1.2 * SR)
    sub = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-T(n) / 0.05)) / SR) * ex(n, 0.35)
    air = lp(rng.standard_normal(n), 3000) * ex(n, 0.25) * 0.4
    return np.tanh(1.4 * (sub + air)) * 0.9


# ---------- arrangement ----------
# I–V–vi–IV in D major, one chord per bar (2 s).
CH = [[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]]
ROOT = [38, 33, 35, 31]
drums = np.zeros(N)
mus = np.zeros(N)
fx = np.zeros(N)

beats = int(DUR / B)
for b in range(beats):
    at = b * B
    full = 4 <= b < 24 and not (18 <= b < 20)  # break around the word wall
    if full or (b >= 24 and b % 2 == 0 and b < 29):
        place(drums, kick(), at)
    if full and b % 2 == 1:
        place(drums, clap(), at)
    if b >= 2 and b < 29:
        place(drums, hat(), at + B / 2)
        if full:
            place(drums, hat(0.012), at + B / 4, 0.6)
            place(drums, hat(0.012), at + 3 * B / 4, 0.6)

bar = 4 * B
for k in range(int(DUR / bar) + 1):
    at = k * bar
    ch = CH[k % 4]
    place(mus, pad([m + 12 for m in ch], int(bar * SR)), at, 0.5)
    # 8th-note pluck arpeggio
    arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 24]
    for s in range(8):
        place(mus, pluck(arp[s % 4]), at + s * B / 2, 0.55 if at >= 1.0 else 0.35)
    # offbeat bass
    if 2 <= at < 12:
        for s in range(4):
            n = int(B / 2 * SR)
            t = T(n)
            sq = np.sign(np.sin(2 * np.pi * hz(ROOT[k % 4]) * t)) * ex(n, 0.12)
            place(mus, lp(sq, 900), at + s * B + B / 2, 0.45)

# bell motifs on key moments
for at, m in [(0.0, 86), (2.5, 85), (6.0, 83), (9.0, 86), (12.0, 90), (13.5, 86), (14.0, 93)]:
    place(mus, bell(m), at, 0.8)

# riser into the lockup (11.75–12.0) and a reverse swell before the drop at 2.5
for a, b_ in [(1.75, 2.5), (11.0, 12.0)]:
    n = int((b_ - a) * SR)
    r = lp(rng.standard_normal(n), np.linspace(500, 9000, n)) * np.linspace(0, 1, n) ** 2.5 * 0.6
    place(fx, r, a)

for t in CUES["clicks"]:
    place(fx, ui_click(), t, 0.9)
for ty in CUES["typing"]:
    n = len(ty["text"])
    for i in range(0, n, 2):
        place(fx, key_tick(), ty["start"] + (ty["end"] - ty["start"]) * i / n, 0.8 + 0.4 * rng.random())
for t in CUES["whoosh"]:
    place(fx, whoosh(), t - 0.22)
for t in CUES["impacts"]:
    place(fx, impact(), t, 0.7)

# gentle sidechain from kicks
pump = np.ones(N)
for b in range(beats):
    if 4 <= b < 24 and not (18 <= b < 20):
        i = int(b * B * SR)
        n = min(N - i, int(0.2 * SR))
        pump[i:i + n] = 1 - 0.45 * np.exp(-T(n) / 0.06)
mus *= pump

tail = np.ones(N)
f0 = int(14.0 * SR)
tail[f0:] = np.linspace(1, 0, N - f0) ** 1.5
mix = (drums * 0.75 + mus * 0.7 + fx * 0.85) * tail
mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix)) * 1.05

# stereo: delay plucks/pads slightly on the right for width
R = mix.copy()
d = int(0.011 * SR)
R[d:] = 0.8 * mix[d:] + 0.2 * (mus * 0.7)[:-d] / (np.max(np.abs(mus)) + 1e-9)
st = np.stack([mix, R], 1)
st /= np.max(np.abs(st)) * 1.03

out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
with wave.open(str(out / "track.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("ok", DUR)
