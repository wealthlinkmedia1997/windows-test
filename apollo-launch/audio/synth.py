"""Synthesizes the 15 s launch soundtrack: 128 BPM, 32 beats = exactly 15.0 s.

Writes track.wav (music + UI clicks) and beats.json (the beat grid the video
uses so every UI click lands on a kick).
"""
import json
import sys
import wave

import numpy as np

SR = 48000
BPM = 128
BEAT = 60 / BPM  # 0.46875 s
BEATS = 32
DUR = BEAT * BEATS  # 15.0 s
N = int(SR * DUR)
rng = np.random.default_rng(7)


def t_of(n):
    return np.arange(n) / SR


def place(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def env_exp(n, decay):
    return np.exp(-t_of(n) / decay)


def kick():
    n = int(0.45 * SR)
    t = t_of(n)
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(n, 0.16)
    click = rng.standard_normal(n) * env_exp(n, 0.002) * 0.3
    return np.tanh(1.8 * (body + click))


def clap():
    n = int(0.3 * SR)
    noise = rng.standard_normal(n)
    e = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022]):
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.012 if k < 2 else 0.09)
    sig = noise * e
    # crude band-pass: diff then smooth
    sig = np.diff(sig, prepend=0)
    sig = np.convolve(sig, np.ones(6) / 6, mode="same")
    return sig * 0.9


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    sig = np.diff(rng.standard_normal(n), prepend=0)
    return sig * env_exp(n, 0.06 if open_ else 0.012) * 0.25


def ui_click():
    """Short UI tick: a bright sine blip plus a transient."""
    n = int(0.06 * SR)
    t = t_of(n)
    blip = np.sin(2 * np.pi * 2400 * t) * env_exp(n, 0.008)
    tick = rng.standard_normal(n) * env_exp(n, 0.0012)
    return (blip * 0.5 + tick * 0.4)


def saw(freq, n, detune=0.0):
    t = t_of(n)
    return 2 * ((t * freq * (1 + detune)) % 1) - 1


def supersaw(freq, n, voices=7, spread=0.012):
    out = np.zeros(n)
    for v in range(voices):
        d = (v - voices // 2) / (voices // 2) * spread
        out += saw(freq, n, d)
    return out / voices


def lowpass(x, cutoff):
    """One-pole low-pass; cutoff may be a per-sample array."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


# Progression, one chord per bar (4 beats): Am – F – C – G, A-minor feel.
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [33, 29, 36, 31]

# Structure (beats): 0-7 intro (filtered), 8 drop, 28-31 outro hit + tail.
DROP = 8

drums = np.zeros(N)
music = np.zeros(N)
clicks = np.zeros(N)

K, C = kick(), clap()
for b in range(BEATS):
    at = b * BEAT
    if b >= 4 and b < 30:
        place(drums, K, at)
    if b < 4 and b % 2 == 0:
        place(drums, K * 0.6, at)
    if b >= DROP and b < 30 and b % 2 == 1:
        place(drums, C * 0.55, at)
    if b >= DROP and b < 30:
        place(drums, hat(open_=True), at + BEAT / 2)
        place(drums, hat(), at + BEAT / 4)
        place(drums, hat(), at + 3 * BEAT / 4)
place(drums, K * 1.2, 30 * BEAT)  # final impact

# Pads + bass, bar by bar.
bar_n = int(4 * BEAT * SR)
for bar in range(BEATS // 4):
    at = bar * 4 * BEAT
    ch = CHORDS[bar % 4]
    pad = sum(supersaw(midi(m + 12), bar_n) for m in ch) / 3
    music_bar = pad * 0.33
    if bar * 4 >= 4:
        # sidechain-style pumping bass on 8ths
        bass = np.zeros(bar_n)
        eighth = int(BEAT / 2 * SR)
        for e in range(8):
            seg = saw(midi(ROOTS[bar % 4]), eighth) * env_exp(eighth, 0.09)
            bass[e * eighth:(e + 1) * eighth] += seg
        music_bar = music_bar + bass * 0.45
    place(music, music_bar, at)

# Filter sweep: closed during intro, opens into the drop.
tt = t_of(N)
cut = np.where(tt < DROP * BEAT, 300 + 3200 * (tt / (DROP * BEAT)) ** 3, 9000)
music = lowpass(music, cut)

# Sidechain pump on music from the kick grid.
pump = np.ones(N)
for b in range(4, 30):
    i = int(b * BEAT * SR)
    n = int(0.22 * SR)
    j = min(N, i + n)
    pump[i:j] = 1 - 0.7 * np.exp(-t_of(j - i) / 0.07)
music *= pump

# Riser into the drop (beats 4-8): rising noise.
r0, r1 = 4 * BEAT, DROP * BEAT
rn = int((r1 - r0) * SR)
riser = rng.standard_normal(rn) * np.linspace(0, 1, rn) ** 2
riser = lowpass(riser, np.linspace(800, 9000, rn)) * 0.5
place(music, riser, r0)

# Outro: fade the bed after the last impact.
fade = np.ones(N)
f0 = int(30 * BEAT * SR)
fade[f0:] = np.exp(-t_of(N - f0) / 0.35)
music *= fade

# UI clicks on the beat: the video's click events, from the cue list below.
CLICK_BEATS = [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
U = ui_click()
for b in CLICK_BEATS:
    place(clicks, U, b * BEAT)

mix = drums * 0.8 + music * 0.75 + clicks * 0.6
mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) * 1.06
stereo = np.stack([mix, mix], axis=1)
# small Haas widening on the pad bed
d = int(0.012 * SR)
stereo[d:, 1] = 0.85 * stereo[d:, 1] + 0.15 * mix[:-d]

out = sys.argv[1] if len(sys.argv) > 1 else "."
with wave.open(f"{out}/track.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype("<i2").tobytes())

with open(f"{out}/beats.json", "w") as f:
    json.dump({"bpm": BPM, "beat": BEAT, "beats": BEATS, "duration": DUR,
               "drop": DROP, "clickBeats": CLICK_BEATS}, f, indent=2)
print("wrote", out, DUR, "s")
