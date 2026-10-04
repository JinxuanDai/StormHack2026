# Temporary Lab Panic sound effects

## Background music

`background_music.ogg` is the user-supplied background track. The main game
streams it continuously through the menu, gameplay and results, at a mixer
volume of 0.30 with an 800 ms fade-in. It loops until application exit and uses
Pygame's dedicated music channel. Missing files or unavailable audio leave
the game usable. Source/author/license information has not been supplied for
this track; the procedural SFX provenance below applies only to the WAV files.

## Generated sound effects

These are temporary procedurally generated development SFX, generated locally
for Lab Panic using Python's standard library. No external audio source,
recording, sample pack, website, or third-party synthesis library was used.
They are original development placeholders, intended to be replaced by final
sounds later. No external author or license is claimed.

All ten files are mono, 16-bit signed PCM WAV at 44,100 Hz. One-shot peaks are
normalized to 55% of full scale; the processing loop peaks at 25%. Mixer gains
below provide additional attenuation. Files have headroom and do not clip.
One-shots have short fades to avoid edge clicks. The one-second loop uses whole
cycles of 120/240/360 Hz with a periodic two-Hz pulse for a continuous seam.

| Filename | Duration | Mixer gain | Character |
| --- | --- | --- | --- |
| `pickup.wav` | 0.16 s | 0.55 | Soft high chime |
| `machine_insert.wav` | 0.18 s | 0.55 | Low mechanical click/thud |
| `machine_remove.wav` | 0.20 s | 0.55 | Light upward mechanical release |
| `processing_start.wav` | 0.36 s | 0.50 | Startup beep over a low hum |
| `processing_loop.wav` | 1.00 s | 0.18 | Quiet periodic machine hum/pulse |
| `processing_complete.wav` | 0.38 s | 0.62 | Positive two-note beep |
| `package_insert.wav` | 0.22 s | 0.55 | Soft packing noise and confirmation |
| `trash.wav` | 0.28 s | 0.50 | Dull low disposal thud |
| `round_success.wav` | 1.12 s | 0.65 | Ascending four-note chime |
| `round_failure.wav` | 1.08 s | 0.60 | Restrained descending three-note cue |

Gains are centralized in `src/lab_panic/ui/audio.py` as `CUE_VOLUMES`; they are
linear mixer multipliers, not percentages of perceived loudness. The processing
loop is deliberately quieter than the completion and result sounds.

From the repository root, listen using:

```sh
python -m lab_panic.ui.audio_demo
```

Keys 1–4 preview pickup, insertion, removal and startup; 5 toggles the loop;
6–0 preview completion, packaging, trash, success and failure. Escape quits.
Nothing is integrated into live gameplay. There is no general drop sound.

To reproduce the placeholders exactly:

```sh
python assets/audio/generate_sfx.py
```

This explicitly overwrites the ten WAVs; do not run it over replacement final
assets you want to keep. The generator uses deterministic oscillators, envelopes
and seeded filtered noise with only `math`, `random`, `struct`, `wave` and
`pathlib`. It is not run by the game or demo.

Replace each WAV under the same filename to keep the cue mapping unchanged, then
restart the preview to reload its cache. All ten sounds still need subjective
listening review; mechanical textures and repeated-machine hum in particular
may need refinement before final production use.
