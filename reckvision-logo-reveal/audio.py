"""RECKVISION sonic identity, synthesised to the render.py timeline (48 kHz stereo WAV)."""
import wave

import numpy as np

SR, DUR = 48000, 9.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)


def env(t0, a, d, shape=4.0):
    """Smooth attack (raised cosine) then exponential-ish decay, zero before t0."""
    x = t - t0
    att = np.where(x < a, 0.5 - 0.5 * np.cos(np.pi * np.clip(x / a, 0, 1)), 1.0)
    dec = np.where(x > a, np.exp(-shape * (x - a) / d), 1.0)
    return np.where(x >= 0, att * dec, 0.0)


def window(t0, t1):
    """Raised-cosine bump spanning t0..t1."""
    x = np.clip((t - t0) / (t1 - t0), 0, 1)
    return np.sin(np.pi * x) ** 2


def bandpass(sig, lo, hi):
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    S = np.fft.rfft(sig)
    m = np.clip((f - lo * 0.8) / (lo * 0.4 + 1e-9), 0, 1) * np.clip((hi * 1.25 - f) / (hi * 0.5), 0, 1)
    return np.fft.irfft(S * m, len(sig))


def place(sig, pan=0.0, gain=1.0):
    """Constant-power pan; pan may be an array for movement."""
    global L, R
    a = (np.asarray(pan) + 1) * np.pi / 4
    L += sig * np.cos(a) * gain
    R += sig * np.sin(a) * gain


# 0.0-1.2 opening: low atmospheric swell + airy texture (slow drift L->R)
swell = window(0.15, 2.6) ** 0.8
pad = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.5 * t + 0.3)
       + 0.25 * np.sin(2 * np.pi * 110.2 * t)) * swell
place(pad, 0.0, 0.035)
air = bandpass(rng.standard_normal(N), 3000, 9000) * window(0.2, 2.4)
place(air, np.linspace(-0.5, 0.5, N), 0.02)

# trace "breath" as the blue line draws (0.45-1.15)
glide_f = 900 + 700 * np.clip((t - 0.45) / 0.7, 0, 1)
place(np.sin(2 * np.pi * np.cumsum(glide_f) / SR) * window(0.45, 1.3), 0.25, 0.012)


def tick(t0, freq, pan, gain):
    x = t - t0
    e = np.where(x >= 0, np.exp(-x / 0.018), 0.0) * np.clip(x / 0.0015, 0, 1)
    body = np.sin(2 * np.pi * freq * x) + 0.4 * np.sin(2 * np.pi * freq * 2.01 * x)
    click = bandpass(rng.standard_normal(N), 4000, 12000) * np.exp(-np.clip(x, 0, None) / 0.003) * (x >= 0)
    place(body * e + 0.3 * click, pan, gain)


# 1.2-3.4 monogram: two tonal ticks for the white geometry...
tick(1.22, 1760, -0.3, 0.16)   # bar + bowl begins
tick(1.62, 2349, 0.1, 0.13)    # R leg begins
tone_tail = np.sin(2 * np.pi * 440 * t) * env(1.22, 0.01, 0.5) + np.sin(2 * np.pi * 587.3 * t) * env(1.62, 0.01, 0.5)
place(tone_tail, 0.0, 0.035)

# ...and a smooth tonal sweep for the blue diagonal (2.30-2.82, accelerating like the visual)
p = np.clip((t - 2.30) / 0.52, 0, 1)
sweep_f = 330 * (2 ** (1.5 * p ** 2.2))           # rises 1.5 octaves
ph = 2 * np.pi * np.cumsum(sweep_f) / SR
sweep = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * window(2.25, 2.95) ** 0.7
place(sweep, np.clip((t - 2.3) / 0.5, 0, 1) * 0.6 - 0.1, 0.10)
tick(2.82, 3136, 0.45, 0.10)                       # blue locks in

# 3.4-5.2 wordmark: stereo whoosh following the left->right reveal
noise = rng.standard_normal(N)
woosh = np.zeros(N)
centers = np.geomspace(400, 4000, 8)
for i, c in enumerate(centers):
    tc = 3.45 + i * 0.12
    woosh += bandpass(noise, c * 0.7, c * 1.4) * window(tc - 0.25, tc + 0.45)
pan_w = np.clip((t - 3.42) / 1.3, 0, 1) * 1.5 - 0.75
place(woosh * window(3.35, 4.9), pan_w, 0.07)

# 5.2-6.5 tagline: light high shimmer
shim = np.zeros(N)
for k, f in enumerate([3520, 4186, 4699, 5274]):
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * (5 + k) * t + k)
    shim += np.sin(2 * np.pi * f * t + k) * trem
shim *= window(5.15, 6.6)
place(shim, np.sin(2 * np.pi * 0.7 * t) * 0.5, 0.014)

# 6.5+ final lockup: warm sub accent + crystalline tone, blooming then decaying to silence
sub_f = 58 * (1 + 0.15 * np.exp(-(t - 6.55).clip(0) / 0.06))
sub = np.sin(2 * np.pi * np.cumsum(sub_f) / SR) * env(6.55, 0.012, 1.1, 3.5)
place(sub, 0.0, 0.30)
bell = np.zeros(N)
for ratio, amp, dec in [(1, 1, 2.2), (2.0, 0.35, 1.4), (2.76, 0.22, 0.9), (5.4, 0.08, 0.5)]:
    bell += amp * np.sin(2 * np.pi * 1318.5 * ratio * t) * env(6.56, 0.004, dec, 4.5)
place(bell, -0.15, 0.07)
place(bell * 0.8, 0.2, 0.05)
chord = sum(np.sin(2 * np.pi * f * t) for f in (329.6, 493.9, 659.3, 830.6)) * env(6.6, 0.5, 2.2, 3.0)
place(chord, 0.0, 0.025)

# light, short room (FFT convolution), kept restrained
ir_t = np.arange(int(SR * 1.2)) / SR
def room(seed):
    r = np.random.default_rng(seed).standard_normal(len(ir_t)) * np.exp(-ir_t / 0.28)
    return bandpass(np.concatenate([r, np.zeros(N - len(r))]), 200, 8000)[: len(ir_t)]
def conv(x, h):
    n = len(x) + len(h)
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[: len(x)]
irL, irR = room(1), room(2)
irL /= np.abs(irL).sum() ** 0.5 * 6; irR /= np.abs(irR).sum() ** 0.5 * 6
L, R = L + 0.18 * conv(L, irL), R + 0.18 * conv(R, irR)

# gentle fade of the tail so the file resolves to true silence at 9.0 s
tail = np.clip((DUR - t) / 0.6, 0, 1) ** 2
L *= tail; R *= tail
st = np.stack([L, R], 1)
st -= st.mean(0)
st *= 10 ** (-1.0 / 20) / np.abs(st).max()          # peak -1 dBFS
pcm = (st * 8388607).astype(np.int32)
b24 = pcm.astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
with wave.open("sound.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b24)
print("wrote sound.wav")
