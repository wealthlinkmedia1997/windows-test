# RECKVISION logo reveal (9 s)

| File | What |
|---|---|
| `RECKVISION_logo_reveal_4K.mp4` | Master: 3840×2160, 30 fps, H.264 + AAC 320k stereo |
| `RECKVISION_logo_reveal_1080p.mp4` | 1920×1080 web/social copy |
| `sound.wav` | Sonic identity alone, 48 kHz / 24-bit stereo |
| `source-logo.webp` | The supplied RV monogram (source of truth) |
| `render.py` / `audio.py` | Reproducible render: `python3 audio.py && python3 render.py video_silent.mp4`, then mux with ffmpeg |

Timeline: 0–1.2 s blue trace · 1.2–2.8 s monogram build (blue diagonal locks at 2.82 s) ·
3.4–4.7 s wordmark · 5.2–6.25 s tagline · 6.55–7.6 s light sweep + ambient glow ·
7.6–9.0 s frame-identical hold on pure black.

The monogram pixels come straight from `source-logo.webp`. The wordmark and tagline were not
in the supplied file, so they are set in Inter Display Bold / Inter Medium (RECK #FFFFFF,
VISION #0A2CFF, tagline #B4B8C2). Replace them with the official lockup artwork if one exists.
