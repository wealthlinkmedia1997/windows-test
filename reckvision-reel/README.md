# RECKVISION brand reel (18 s, 9:16)

`RECKVISION_brand_reel_1080x1920.mp4`: 1080×1920, 30 fps, H.264 + AAC 320k stereo.
`music.wav` holds the score and sound design on their own (48 kHz / 24-bit).

The shot structure follows the supplied reference reel: hard cuts on a 120 BPM grid. All
visuals and audio are RECKVISION's own. The music is an original synthesized composition
(`music.py`), and none of the reference audio is used.

| Time | Shot |
|---|---|
| 0–2 | Monogram pieces spin in "3D" and assemble over drafting lines |
| 2–3 | Small white monogram on ink |
| 3–4 | Dark monogram on paper |
| 4–5 | Tonal monogram on an electric-blue grid |
| 5–6 | Shards converge into the monogram (bass drop) |
| 6–7 | Gradient-glow monogram |
| 7–7.5 | White monogram on blue |
| 7.5–9 | Monogram slides left, RECKVISION letters land one by one |
| 9–10 | Construction lines + angle annotations (53.7° / 56.2°) |
| 10–11 | Clean lockup |
| 11–12 | Typing "reck vision" → space removed → "reckvision" |
| 12–13 | Blue outline draws the monogram, then it fills |
| 13–14 | Paper lockup, tracking tightens · monogram flip |
| 14–15.5 | Phone mockup: social profile with brand post grid |
| 15.5–16 | App icon |
| 16–18 | Logo variations: silver, holographic, blue, graphite |

Rebuild: `python3 music.py && python3 reel.py reel_silent.mp4`, then mux with ffmpeg.
Uses `../reckvision-logo-reveal/source-logo.webp` for the monogram.
