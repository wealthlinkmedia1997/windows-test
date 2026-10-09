"""Original 120 BPM UI-electronic score + sound design for the RECKVISION reel.

Groove and hit placement mirror the reference reel's edit (kick/clap grid, drop at the
shard shot, UI accents on cuts); every sound is synthesised here from scratch.
"""
import wave

import numpy as np

SR, DUR = 48000, 18.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(21)
L = np.zeros(N); R = np.zeros(N)
BUS = {k: [np.zeros(N), np.zeros(N)] for k in ("drums", "music", "sfx")}


def put(sig, start, bus, pan=0.0, gain=1.0):
    """Add a short signal at time `start` on a bus with constant-power pan."""
    i0 = int(start * SR)
    if i0 >= N: return
    sig = sig[: N - max(i0, 0)]
    if i0 < 0: sig, i0 = sig[-i0:], 0
    a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    BUS[bus][0][i0:i0 + len(sig)] += sig * np.cos(a) * gain
    BUS[bus][1][i0:i0 + len(sig)] += sig * np.sin(a) * gain


def fft_filter(sig, lo=0.0, hi=None):
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    S = np.fft.rfft(sig)
    m = np.ones_like(f)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(S * m, len(sig))


def tt(d): return np.arange(int(d * SR)) / SR
def midi(n): return 440 * 2 ** ((n - 69) / 12)


# ------------------------------------------------------------------ drums
def kick(gain=1.0):
    x = tt(0.45)
    f = 45 + 110 * np.exp(-x / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-x / 0.22)
    click = fft_filter(rng.standard_normal(len(x)), 1500, 7000) * np.exp(-x / 0.004) * 0.25
    return np.tanh((body + click) * 1.6) * gain


def clap():
    x = tt(0.35)
    n = fft_filter(rng.standard_normal(len(x)), 900, 6000)
    e = sum(np.exp(-np.clip(x - d, 0, None) / 0.006) * (x >= d) for d in (0, 0.011, 0.023))
    e += 0.5 * np.exp(-np.clip(x - 0.03, 0, None) / 0.09) * (x >= 0.03)
    return n * e * 0.7


def hat(open_=False):
    x = tt(0.25 if open_ else 0.06)
    n = fft_filter(rng.standard_normal(len(x)), 7000)
    return n * np.exp(-x / (0.07 if open_ else 0.012))


KICKS = [2.0, 2.8, 3.8, 4.8, 5.5, 5.8, 6.0, 6.8, 7.8, 8.0, 8.8, 10.0, 10.8, 11.8, 12.8,
         13.5, 14.0, 14.8, 15.5, 15.8, 16.0, 16.4, 16.8, 17.3, 17.6]
CLAPS = [3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0]
for k in KICKS: put(kick(), k, "drums", 0, 0.9)
for c in CLAPS: put(clap(), c, "drums", 0.05, 0.55)
for i in range(int(2.0 / 0.125), int(17.75 / 0.125)):
    s = i * 0.125
    if 11.0 <= s < 11.75: continue                # leave room for the typing clicks
    accent = 1.0 if i % 2 else 0.55
    put(hat(), s, "drums", 0.35 if i % 4 == 1 else -0.3, 0.07 * accent)
for s in np.arange(2.25, 17.5, 0.5):
    if (5.0 <= s < 7.0) or (13.5 <= s < 16.5):
        put(hat(True), s, "drums", 0.2, 0.07)

# sidechain envelope (music ducks under the kick)
duck = np.ones(N)
for k in KICKS:
    x = t - k
    duck -= 0.55 * np.exp(-np.clip(x, 0, None) / 0.13) * (x >= 0)
duck = np.clip(duck, 0.3, 1)

# ------------------------------------------------------------------ harmony
#            bar start: chord (midi notes), bass root
CHORDS = [(2, [52, 59, 62, 66, 67], 40), (4, [48, 55, 59, 64, 67], 36), (6, [55, 59, 62, 64, 66], 43),
          (8, [54, 57, 62, 64, 69], 42), (10, [52, 59, 62, 66, 67], 40), (12, [48, 55, 59, 64, 67], 36),
          (14, [57, 60, 64, 67, 71], 45), (16, [52, 59, 64, 66, 71], 40)]


def supersaw(freq, dur, voices=5, det=0.12):
    x = tt(dur)
    out = np.zeros(len(x))
    for v in range(voices):
        cents = (v - (voices - 1) / 2) * det * 10
        fv = freq * 2 ** (cents / 1200)
        ph = rng.uniform(0, 2 * np.pi)
        for h in range(1, 14):
            if fv * h > 9000: break
            out += np.sin(2 * np.pi * fv * h * x + ph * h) / h
    return out / voices


pad = np.zeros(N)
for start, notes, _ in CHORDS:
    d = 2.05
    x = tt(d)
    env = np.clip(x / 0.25, 0, 1) * np.clip((d - x) / 0.3, 0, 1)
    chord = sum(supersaw(midi(n), d) for n in notes) * env
    i0 = int(start * SR)
    pad[i0:i0 + len(chord)] += chord[: N - i0]
pad = fft_filter(pad, 120, 2200) * duck
intro_swell = np.clip((t - 0.2) / 1.8, 0, 1) ** 2
padL = pad * 0.06 + fft_filter(rng.standard_normal(N), 2000, 8000) * intro_swell * (t < 2.0) * 0.02
put(padL, 0, "music", -0.25, 1.0)
put(np.roll(pad, int(0.012 * SR)) * 0.06, 0, "music", 0.25, 1.0)

# intro drone + riser into the first cut
drone = (np.sin(2 * np.pi * midi(28) * t) + 0.4 * np.sin(2 * np.pi * midi(40) * t)) * intro_swell * (t < 2.05)
put(drone, 0, "music", 0, 0.12)
rx = tt(0.9)
rf = 300 * 2 ** (3 * (rx / 0.9) ** 2)
riser = fft_filter(rng.standard_normal(len(rx)), 400) * (rx / 0.9) ** 2 * 0.25 + np.sin(2 * np.pi * np.cumsum(rf) / SR) * (rx / 0.9) ** 3 * 0.12
put(riser, 1.1, "sfx", 0, 0.8)

# sub bass on the kicks from the first downbeat
for k in KICKS:
    root = [r for s, _, r in CHORDS if s <= k][-1] if k >= 2 else 40
    x = tt(0.42)
    f = midi(root)
    sig = (np.sin(2 * np.pi * f * x) + 0.25 * np.sin(4 * np.pi * f * x)) * np.clip(x / 0.01, 0, 1) * np.exp(-x / 0.3)
    heavy = 1.4 if (5.0 <= k < 7.0 or 13.5 <= k < 16.5) else 1.0
    put(np.tanh(sig * 1.5) * heavy, k + 0.005, "music", 0, 0.22)

# pluck arpeggio (8ths) through the wordmark / UI section
def pluck(f, dur=0.3):
    x = tt(dur)
    s = sum(np.sin(2 * np.pi * f * h * x) * np.exp(-x * (6 + 8 * h)) / h for h in range(1, 7))
    return s * np.clip(x / 0.002, 0, 1)

for i, s in enumerate(np.arange(7.5, 17.0, 0.25)):
    if 13.5 <= s < 14.0: continue
    notes = [n for st, n, _ in CHORDS if st <= s][-1]
    seq = [0, 2, 4, 3, 1, 4, 2, 3]
    n = notes[seq[i % 8]] + 12
    put(pluck(midi(n)), s, "music", 0.45 * np.sin(i * 0.9), 0.05 if i % 2 else 0.065)

# ------------------------------------------------------------------ UI sound design
def pad15(x):
    """Pad short UI sounds to a common length so they can be layered with +."""
    n = int(0.15 * SR)
    return np.pad(x, (0, max(0, n - len(x))))


def blip(f, d=0.07, g=1.0):
    x = tt(d)
    return pad15((np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 2 * f * x)) * np.exp(-x / (d / 4)) * np.clip(x / 0.001, 0, 1) * g)


def click(d=0.03):
    x = tt(d)
    return pad15(fft_filter(rng.standard_normal(len(x)), 2500, 9000) * np.exp(-x / 0.003))


def whoosh(d, lo=500, hi=5000, rise=True):
    x = tt(d)
    n = rng.standard_normal(len(x))
    out = np.zeros(len(x))
    bands = np.geomspace(lo, hi, 6)
    if not rise: bands = bands[::-1]
    for i, c in enumerate(bands):
        w = np.sin(np.pi * np.clip((x / d) * 6 / 4 - i / 4, 0, 1)) ** 2
        out += fft_filter(n, c * 0.7, c * 1.4) * w
    return out * np.sin(np.pi * x / d)


def glitch(d=0.25):
    x = tt(d)
    sq = np.sign(np.sin(2 * np.pi * 220 * x * (1 + 3 * (rng.random(len(x)) > 0.995).cumsum() % 3)))
    gate = (np.floor(x * 60) % 2)
    return fft_filter(sq * gate, 300, 6000) * np.exp(-x / 0.12) * 0.5


# construction clacks (pieces snapping in)
for s, f in [(0.25, 900), (0.6, 1100), (0.95, 1350), (1.3, 1600), (1.62, 1900), (1.86, 2400)]:
    put(blip(f, 0.05) + click() * 0.6, s, "sfx", (f - 1500) / 1500, 0.22)
put(blip(3136, 0.12), 2.0, "sfx", 0.1, 0.15)                      # crisp logo reveal
put(whoosh(0.45, rise=True), 3.6, "sfx", -0.4, 0.12)             # into paper
put(whoosh(0.4, rise=False), 4.0, "sfx", 0.4, 0.14)              # blue grid
put(blip(1318, 0.09), 4.0, "sfx", 0, 0.12)
for i in range(14):                                               # shard scatter / snap
    put(click(0.02) + blip(rng.uniform(1800, 4200), 0.03) * 0.5, 5.0 + i * 0.05 + rng.uniform(0, 0.03), "sfx", rng.uniform(-0.8, 0.8), 0.18)
put(whoosh(0.6, 200, 3000, rise=False), 5.0, "sfx", 0, 0.16)
shim = sum(np.sin(2 * np.pi * f * tt(0.9) + i) for i, f in enumerate([2637, 3136, 3951, 5274])) * np.exp(-tt(0.9) / 0.35)
put(shim, 6.0, "sfx", 0.2, 0.035)                                 # glow shimmer
put(blip(2093, 0.08), 7.0, "sfx", 0, 0.14)
put(whoosh(0.35, 800, 6000), 7.85, "sfx", -0.5, 0.1)              # monogram slides left
for i in range(10):                                               # letters landing
    put(blip(midi(76 + [0, 2, 4, 7, 9, 12, 14, 16, 19, 21][i]), 0.05), 7.5 + (0.6 + i * 0.05) * 1.5, "sfx", -0.6 + i * 0.13, 0.07)
put(glitch(0.3), 9.0, "sfx", 0.15, 0.2)
for i in range(4): put(blip(4186, 0.03), 9.2 + i * 0.09, "sfx", 0.5 - i * 0.3, 0.06)
put(whoosh(0.3, 1000, 6000, rise=False), 10.0, "sfx", 0, 0.08)
for i in range(11):                                               # typing
    put(click(0.04) * 1.2 + blip(rng.uniform(1500, 1900), 0.02) * 0.4, 11.02 + i * 0.05, "sfx", rng.uniform(-0.2, 0.2), 0.22)
put(blip(988, 0.06) + click(), 11.62, "sfx", 0.1, 0.24)          # space removed
put(blip(1976, 0.12), 11.8, "sfx", 0.1, 0.1)
sw = tt(0.7)
sweep = np.sin(2 * np.pi * np.cumsum(700 + 1400 * sw / 0.7) / SR) * np.sin(np.pi * sw / 0.7) ** 2
put(sweep, 12.0, "sfx", np.linspace(-0.5, 0.5, len(sw)), 0.05)  # outline drawing
put(blip(659, 0.15) + blip(1318, 0.15) * 0.5, 12.72, "sfx", 0, 0.16)
put(whoosh(0.4, 300, 4000), 13.4, "sfx", 0.3, 0.12)              # flip
put(whoosh(0.55, 200, 3500, rise=False), 14.0, "sfx", 0.5, 0.16) # phone slides in
put(blip(1568, 0.08) + blip(2349, 0.1) * 0.7, 14.75, "sfx", 0.3, 0.12)  # notification pop
put(blip(784, 0.06) + click() * 0.5, 15.52, "sfx", 0, 0.2)        # icon tap
for s in (16.0, 16.5, 17.0, 17.5):
    put(whoosh(0.25, 1500, 7000), s - 0.08, "sfx", 0.6 if s % 1 else -0.6, 0.08)
# closing chord bloom + bell into silence
bx = tt(1.2)
bell = sum(a * np.sin(2 * np.pi * 1318.5 * rr * bx) * np.exp(-bx / d) for rr, a, d in [(1, 1, 0.45), (2, 0.3, 0.3), (2.76, 0.18, 0.2)])
put(bell, 17.0, "sfx", -0.1, 0.07)

# ------------------------------------------------------------------ mix + master
gains = {"drums": 1.0, "music": 1.0, "sfx": 1.0}
L = sum(BUS[k][0] * g for k, g in gains.items())
R = sum(BUS[k][1] * g for k, g in gains.items())
# short room on music+sfx
ir_t = np.arange(int(SR * 0.9)) / SR
def room(seed):
    h = np.random.default_rng(seed).standard_normal(len(ir_t)) * np.exp(-ir_t / 0.22)
    return h / np.sqrt((h ** 2).sum()) * 0.25
def conv(x, h):
    n = len(x) + len(h)
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[: len(x)]
wetL = conv(BUS["music"][0] + BUS["sfx"][0], room(1))
wetR = conv(BUS["music"][1] + BUS["sfx"][1], room(2))
L, R = L + 0.35 * wetL, R + 0.35 * wetR
st = np.stack([L, R], 1)
st -= st.mean(0)
st /= np.abs(st).max()
st = np.tanh(st * 1.8) / np.tanh(1.8)          # gentle glue / soft clip
fade = np.clip((DUR - t) / 0.35, 0, 1) ** 1.5
st *= fade[:, None]
st *= 10 ** (-1.0 / 20) / np.abs(st).max()
pcm = (st * 8388607).astype("<i4")
with wave.open("music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR)
    w.writeframes(pcm.view(np.uint8).reshape(-1, 4)[:, :3].tobytes())
print("wrote music.wav")
