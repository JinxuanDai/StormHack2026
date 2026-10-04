"""Regenerate Lab Panic's original temporary SFX using only Python's stdlib.

Run explicitly: python assets/audio/generate_sfx.py
Overwrites the ten named placeholder WAV files beside this script. No downloads,
external samples, Pygame, or third-party libraries are used.
"""

import math
from pathlib import Path
import random
import struct
import wave


RATE = 44100
TAU = 2 * math.pi
DURATIONS = {
    "pickup": 0.16,
    "machine_insert": 0.18,
    "machine_remove": 0.20,
    "processing_start": 0.36,
    "processing_loop": 1.00,
    "processing_complete": 0.38,
    "package_insert": 0.22,
    "trash": 0.28,
    "round_success": 1.12,
    "round_failure": 1.08,
}


def envelope(t: float, duration: float) -> float:
    """Soft attack with a smooth decaying tail; both ends reach zero."""
    attack = min(0.008, duration / 5)
    return min(1.0, t / attack) ** 2 * max(0.0, 1 - t / duration) ** 2


def tone(samples, start, duration, frequency, gain=1.0, end_frequency=None):
    first = round(start * RATE)
    slope = ((end_frequency or frequency) - frequency) / duration
    for j in range(min(round(duration * RATE), len(samples) - first)):
        t = j / RATE
        phase = TAU * (frequency * t + slope * t * t / 2)
        samples[first + j] += gain * envelope(t, duration) * (
            math.sin(phase) + 0.08 * math.sin(2 * phase))


def soft_noise(samples, start, duration, gain, seed, smoothing=0.14):
    rng = random.Random(seed)
    first, filtered = round(start * RATE), 0.0
    for j in range(min(round(duration * RATE), len(samples) - first)):
        filtered += smoothing * (rng.uniform(-1, 1) - filtered)
        samples[first + j] += gain * envelope(j / RATE, duration) * filtered


def synthesize(cue: str) -> list[float]:
    samples = [0.0] * round(DURATIONS[cue] * RATE)
    if cue == "pickup":
        tone(samples, 0, 0.16, 1047, 0.75)
        tone(samples, 0.012, 0.14, 1568, 0.22)
    elif cue == "machine_insert":
        tone(samples, 0, 0.18, 170, 0.8, 85)
        soft_noise(samples, 0, 0.07, 1.2, 10)
        tone(samples, 0.055, 0.10, 280, 0.22)
    elif cue == "machine_remove":
        soft_noise(samples, 0, 0.09, 0.65, 20)
        tone(samples, 0.02, 0.18, 380, 0.55, 620)
    elif cue == "processing_start":
        tone(samples, 0, 0.36, 120, 0.3)
        tone(samples, 0.015, 0.22, 240, 0.65, 480)
        tone(samples, 0.20, 0.16, 240, 0.28)
    elif cue == "processing_loop":
        # Integer cycles over one second, including modulation. No noise or
        # endpoint fade: the waveform and its slope continue across the seam.
        for i in range(len(samples)):
            t = i / RATE
            pulse = 0.82 + 0.18 * math.cos(TAU * 2 * t)
            samples[i] = pulse * (0.70 * math.sin(TAU * 120 * t)
                                  + 0.22 * math.sin(TAU * 240 * t)
                                  + 0.08 * math.sin(TAU * 360 * t))
    elif cue == "processing_complete":
        tone(samples, 0, 0.20, 659, 0.65)
        tone(samples, 0.12, 0.26, 880, 0.75)
    elif cue == "package_insert":
        soft_noise(samples, 0, 0.16, 1.0, 30, smoothing=0.08)
        tone(samples, 0.045, 0.17, 440, 0.35)
        tone(samples, 0.10, 0.12, 554, 0.22)
    elif cue == "trash":
        soft_noise(samples, 0, 0.28, 1.1, 40, smoothing=0.06)
        tone(samples, 0, 0.24, 110, 0.75, 60)
    elif cue == "round_success":
        for start, frequency, duration in (
            (0, 523, 0.38), (0.16, 659, 0.38),
            (0.32, 784, 0.42), (0.52, 1047, 0.60),
        ):
            tone(samples, start, duration, frequency, 0.65)
    elif cue == "round_failure":
        for start, frequency, duration in ((0, 440, 0.42), (0.22, 349, 0.46), (0.46, 262, 0.62)):
            tone(samples, start, duration, frequency, 0.65)
    else:
        raise ValueError(f"Unknown cue: {cue}")
    return samples


def write_wav(path: Path, samples: list[float], *, loop: bool = False) -> None:
    if not loop:
        mean = sum(samples) / len(samples)
        fade = round(0.004 * RATE)
        samples = [(value - mean) * min(1.0, i / fade, (len(samples) - 1 - i) / fade)
                   for i, value in enumerate(samples)]
    peak = max(abs(value) for value in samples)
    target = 0.25 if loop else 0.55  # Leave generous headroom before mixer gains.
    pcm = [round(value * target / peak * 32767) for value in samples]
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))


def main() -> None:
    root = Path(__file__).resolve().parent
    for cue, duration in DURATIONS.items():
        write_wav(root / f"{cue}.wav", synthesize(cue), loop=cue == "processing_loop")
        print(f"{cue}.wav: {duration:.2f}s, mono 16-bit PCM, {RATE} Hz")


if __name__ == "__main__":
    main()
