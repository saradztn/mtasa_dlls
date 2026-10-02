#!/usr/bin/env python3
"""Generate an openly labelled synthetic inline-four engine approximation.

This is procedural audio, NOT a Kawasaki recording and NOT a claim of an authentic
Z1000 sound. It models evenly spaced four-stroke inline-four firing pulses, RPM orders,
load coloration, light combustion variation, broadband exhaust/intake texture, and a
missed-fire limiter pattern. Standard library only; no source audio is downloaded or
used. Running this script overwrites the bundled z1000_*.wav files.
"""

from __future__ import annotations

import argparse
import array
import math
import random
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

RESOURCE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_DIR = RESOURCE_DIR / "audio"
SAMPLE_RATE = 48_000
LOOP_SECONDS = 2.4
LOOP_FRAMES = round(SAMPLE_RATE * LOOP_SECONDS)


@dataclass(frozen=True)
class Profile:
    filename: str
    rpm: int
    load: float
    kind: str
    peak: float
    noise: float
    seed: int


# RPM anchors match Config.RPM.LayerAnchors / OverlayAnchors. All are multiples of
# 50 RPM, so 2.4-second loops contain an integer number of firing events and 720-degree
# engine cycles; the core orders return to their start phase at the loop boundary.
PROFILES: Dict[str, Profile] = {
    "idle": Profile("z1000_idle.wav", 1200, 0.12, "base", 0.50, 0.020, 1101),
    "low": Profile("z1000_low.wav", 2350, 0.20, "base", 0.50, 0.020, 1102),
    "mid": Profile("z1000_mid.wav", 4400, 0.34, "base", 0.50, 0.022, 1103),
    "high": Profile("z1000_high.wav", 7400, 0.48, "base", 0.51, 0.025, 1104),
    "redline": Profile("z1000_redline.wav", 10200, 0.60, "base", 0.51, 0.028, 1105),
    "accel": Profile("z1000_accel.wav", 4700, 0.78, "accel", 0.48, 0.032, 1201),
    "light_accel": Profile("z1000_light_accel.wav", 3000, 0.38, "light", 0.45, 0.026, 1202),
    "hard_accel": Profile("z1000_hard_accel.wav", 7600, 0.96, "hard", 0.47, 0.038, 1203),
    "decel": Profile("z1000_decel.wav", 4200, 0.10, "decel", 0.44, 0.034, 1301),
    "engine_brake": Profile("z1000_enginebrake.wav", 5000, 0.06, "brake", 0.45, 0.030, 1302),
    "throttle_release": Profile("z1000_throttle_release.wav", 4300, 0.08, "release", 0.43, 0.034, 1303),
    "coast": Profile("z1000_coast.wav", 2600, 0.03, "coast", 0.42, 0.030, 1304),
    "limiter": Profile("z1000_limiter.wav", 11000, 1.00, "limiter", 0.50, 0.034, 1401),
    "intake": Profile("z1000_intake.wav", 5000, 0.80, "intake", 0.42, 0.060, 1501),
    "exhaust": Profile("z1000_exhaust.wav", 4800, 0.66, "exhaust", 0.45, 0.035, 1502),
    "helmet": Profile("z1000_helmet.wav", 5000, 0.55, "helmet", 0.43, 0.014, 1503),
}

BASE_CYLINDER_BALANCE = (0.985, 1.025, 0.975, 1.015)
LIMITER_CYLINDER_CUT = (1.00, 0.16, 0.92, 0.10)


def gaussian(value: float, center: float, width: float) -> float:
    ratio = (value - center) / width
    return math.exp(-0.5 * ratio * ratio)


def smoothstep01(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def spectrum_weight(frequency: float, profile: Profile) -> float:
    """Broad, RPM-dependent resonances; these are design choices, not measurements."""
    kind = profile.kind
    if kind == "intake":
        formants = (
            0.12
            + 1.00 * gaussian(frequency, 620.0, 390.0)
            + 0.82 * gaussian(frequency, 1750.0, 1050.0)
            + 0.26 * gaussian(frequency, 3900.0, 1800.0)
        )
        rolloff = 8200.0
    elif kind == "helmet":
        formants = (
            0.58
            + 0.48 * gaussian(frequency, 180.0, 180.0)
            + 0.44 * gaussian(frequency, 510.0, 420.0)
        )
        rolloff = 2600.0
    elif kind == "exhaust":
        formants = (
            0.70
            + 0.78 * gaussian(frequency, 145.0, 155.0)
            + 0.90 * gaussian(frequency, 470.0, 340.0)
            + 0.36 * gaussian(frequency, 1180.0, 820.0)
        )
        rolloff = 7200.0 + profile.load * 1600.0
    else:
        formants = (
            0.66
            + 0.60 * gaussian(frequency, 155.0, 170.0)
            + 0.82 * gaussian(frequency, 490.0, 360.0)
            + 0.38 * gaussian(frequency, 1260.0, 900.0)
        )
        rolloff = 4200.0 + profile.load * 5300.0 + min(1300.0, profile.rpm * 0.08)

    if kind in ("decel", "brake", "release"):
        formants *= 0.92 + 0.14 * gaussian(frequency, 760.0, 510.0)
        rolloff *= 0.82
    elif kind == "coast":
        formants *= 0.85
        rolloff *= 0.76
    elif kind in ("accel", "light", "hard", "limiter"):
        formants *= 1.0 + 0.18 * profile.load * gaussian(frequency, 1850.0, 1200.0)

    return formants * math.exp(-frequency / max(500.0, rolloff))


def build_tone_oscillators(profile: Profile) -> List[List[float]]:
    """Return sine oscillators: [amplitude, sin, cos, sin_step, cos_step]."""
    firing_hz = profile.rpm / 30.0  # 4 firings / 2 crank revolutions.
    duty = 0.145 if profile.load < 0.5 else 0.125
    if profile.kind in ("decel", "brake", "release"):
        duty = 0.105
    elif profile.kind == "limiter":
        duty = 0.115

    oscillators: List[List[float]] = []
    harmonic_count = min(44, max(18, int(17_500.0 / firing_hz)))
    for order in range(1, harmonic_count + 1):
        frequency = firing_hz * order
        if frequency >= SAMPLE_RATE * 0.47:
            break

        # Fourier terms form a compact, softened firing-pulse train. The extra broad
        # resonances give it body without claiming to reproduce a measured exhaust.
        pulse_coefficient = (2.0 / (math.pi * order)) * math.sin(math.pi * order * duty)
        amplitude = pulse_coefficient * spectrum_weight(frequency, profile)
        if profile.kind == "intake":
            amplitude *= 0.80 if frequency < 230.0 else 1.35
        elif profile.kind == "helmet":
            amplitude *= 0.90
        elif profile.kind == "coast":
            amplitude *= 0.74
        elif profile.kind in ("decel", "brake", "release"):
            amplitude *= 0.90

        phase = -math.pi * order * duty
        angle_step = 2.0 * math.pi * frequency / SAMPLE_RATE
        oscillators.append([
            amplitude,
            math.sin(phase),
            math.cos(phase),
            math.sin(angle_step),
            math.cos(angle_step),
        ])

        # A quiet delayed reflection of each firing order approximates exhaust-body
        # resonance. It remains a mathematical overlay, not a field recording.
        echo_gain = 0.13 if profile.kind not in ("intake", "helmet") else 0.06
        echo_phase = phase - 2.0 * math.pi * frequency * 0.0085
        oscillators.append([
            amplitude * echo_gain,
            math.sin(echo_phase),
            math.cos(echo_phase),
            math.sin(angle_step),
            math.cos(angle_step),
        ])

    # Very quiet crankshaft/cam orders supply a mechanical texture beneath the
    # dominant firing pulses. A four-stroke 4-cylinder has one firing event every 180°.
    for order, gain in ((0.5, 0.045), (0.25, 0.030), (1.0, 0.035)):
        frequency = firing_hz * order
        angle_step = 2.0 * math.pi * frequency / SAMPLE_RATE
        phase = 0.37 * order
        amplitude = gain * (0.75 + profile.load * 0.35)
        oscillators.append([
            amplitude,
            math.sin(phase),
            math.cos(phase),
            math.sin(angle_step),
            math.cos(angle_step),
        ])
    return oscillators


def render_loop(profile: Profile) -> Tuple[array.array, Dict[str, float]]:
    frames = LOOP_FRAMES
    firing_hz = profile.rpm / 30.0
    # Integer phase accumulation avoids long-loop drift and guarantees the authored
    # RPM anchors close on an exact firing/cylinder phase after 2.4 seconds.
    phase_denominator = 30 * SAMPLE_RATE
    phase_numerator = 0
    event_index = 0
    oscillators = build_tone_oscillators(profile)
    rng = random.Random(profile.seed)

    # One-pole bands shape a quiet, deterministic noise bed. It is intentionally kept
    # below the firing tones and differs by state (intake hiss vs. exhaust/wind texture).
    low_alpha = 1.0 - math.exp(-2.0 * math.pi * 260.0 / SAMPLE_RATE)
    mid_alpha = 1.0 - math.exp(-2.0 * math.pi * 2600.0 / SAMPLE_RATE)
    low_state = 0.0
    mid_state = 0.0
    for _ in range(1600):
        white = rng.random() * 2.0 - 1.0
        low_state += low_alpha * (white - low_state)
        mid_state += mid_alpha * (white - mid_state)

    if profile.kind == "limiter":
        balance = LIMITER_CYLINDER_CUT
    else:
        balance = BASE_CYLINDER_BALANCE

    if profile.kind == "intake":
        noise_low, noise_mid, noise_high = 0.04, 0.38, 0.86
    elif profile.kind == "helmet":
        noise_low, noise_mid, noise_high = 0.38, 0.24, 0.08
    elif profile.kind == "coast":
        noise_low, noise_mid, noise_high = 0.16, 0.50, 0.76
    elif profile.kind in ("decel", "brake", "release"):
        noise_low, noise_mid, noise_high = 0.18, 0.45, 0.68
    else:
        noise_low, noise_mid, noise_high = 0.20, 0.42, 0.65

    output = array.array("f")
    peak = 0.0
    square_sum = 0.0
    for _ in range(frames):
        tone = 0.0
        for oscillator in oscillators:
            amplitude, sine_value, cosine_value, sine_step, cosine_step = oscillator
            tone += amplitude * sine_value
            oscillator[1] = sine_value * cosine_step + cosine_value * sine_step
            oscillator[2] = cosine_value * cosine_step - sine_value * sine_step

        # Smoothly vary cylinder contribution over each firing interval. The sequence
        # repeats every four events and the chosen loop anchors contain whole sequences.
        phase = phase_numerator / phase_denominator
        blend = smoothstep01((phase - 0.78) / 0.22)
        cylinder_gain = balance[event_index & 3] * (1.0 - blend) \
            + balance[(event_index + 1) & 3] * blend
        cam_wobble = 1.0 + 0.030 * math.sin(2.0 * math.pi * phase * 0.25 + 0.6)
        crank_wobble = 1.0 + 0.018 * math.sin(2.0 * math.pi * phase * 0.5 + 0.25)
        engine = tone * cylinder_gain * cam_wobble * crank_wobble

        white = rng.random() * 2.0 - 1.0
        low_state += low_alpha * (white - low_state)
        mid_state += mid_alpha * (white - mid_state)
        mid_band = mid_state - low_state
        high_band = white - mid_state
        texture = noise_low * low_state + noise_mid * mid_band + noise_high * high_band
        engine += profile.noise * texture

        # Mild lift-off/overrun flutter; no invented gunshot pops or limiter recordings.
        if profile.kind in ("decel", "brake", "release"):
            flutter = 1.0 + 0.026 * math.sin(2.0 * math.pi * phase * 0.5 + 1.1)
            engine *= flutter
        elif profile.kind == "coast":
            engine *= 0.93 + 0.025 * math.sin(2.0 * math.pi * phase * 0.25)

        output.append(engine)
        absolute = abs(engine)
        peak = max(peak, absolute)
        square_sum += engine * engine

        phase_numerator += profile.rpm
        if phase_numerator >= phase_denominator:
            phase_numerator -= phase_denominator
            event_index += 1

    if peak < 1e-8:
        raise RuntimeError("Internal error: generated a silent loop for " + profile.filename)

    # Keep each separate loop comfortably below full scale; runtime layer gains and
    # crossfades are applied by the MTA mixer. No compression or hard clipping.
    gain = min(profile.peak / peak, 8.0)
    for index in range(len(output)):
        output[index] *= gain

    peak_after = peak * gain
    rms_after = math.sqrt(square_sum / frames) * gain
    seam = abs(output[-1] - output[0])
    return output, {
        "rpm": float(profile.rpm),
        "peak": peak_after,
        "rms": rms_after,
        "duration": frames / SAMPLE_RATE,
        "seam_step": seam,
        "event_count": float(event_index),
    }


def render_shift(seed: int = 1601) -> Tuple[array.array, Dict[str, float]]:
    """A short synthetic transmission/clutch tick for the optional shift transient."""
    frames = int(round(0.48 * SAMPLE_RATE))
    rng = random.Random(seed)
    output = array.array("f")
    low_state = 0.0
    high_state = 0.0
    low_alpha = 1.0 - math.exp(-2.0 * math.pi * 220.0 / SAMPLE_RATE)
    high_alpha = 1.0 - math.exp(-2.0 * math.pi * 1800.0 / SAMPLE_RATE)
    for index in range(frames):
        time = index / SAMPLE_RATE
        white = rng.random() * 2.0 - 1.0
        low_state += low_alpha * (white - low_state)
        high_state += high_alpha * (white - high_state)
        high_noise = white - high_state
        impact = math.exp(-time / 0.055)
        click = 0.31 * high_noise * impact
        thump = 0.28 * math.sin(2.0 * math.pi * 118.0 * time) * math.exp(-time / 0.095)
        gear_whine = 0.10 * math.sin(2.0 * math.pi * (430.0 * time + 470.0 * time * time)) \
            * math.exp(-time / 0.16)
        low_body = 0.18 * low_state * math.exp(-time / 0.11)
        envelope = min(1.0, time / 0.006) * min(1.0, (frames - 1 - index) / (SAMPLE_RATE * 0.010))
        output.append((click + thump + gear_whine + low_body) * max(0.0, envelope))

    peak = max(abs(value) for value in output)
    gain = min(0.42 / max(peak, 1e-8), 5.0)
    for index in range(len(output)):
        output[index] *= gain
    peak_after = max(abs(value) for value in output)
    rms_after = math.sqrt(sum(value * value for value in output) / frames)
    return output, {
        "rpm": 0.0,
        "peak": peak_after,
        "rms": rms_after,
        "duration": frames / SAMPLE_RATE,
        "seam_step": abs(output[-1]),
        "event_count": 0.0,
    }


def write_pcm16(path: Path, samples: Sequence[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array.array("h")
    for sample in samples:
        sample = min(0.999, max(-0.999, float(sample)))
        pcm.append(int(round(sample * 32767.0)))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())


def read_pcm16(path: Path) -> array.array:
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2 or source.getframerate() != SAMPLE_RATE:
            raise RuntimeError("Preview source has unexpected format: " + str(path))
        samples = array.array("h")
        samples.frombytes(source.readframes(source.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    return array.array("f", (value / 32768.0 for value in samples))


def crossfade_join(left: Sequence[float], right: Sequence[float], fade_frames: int) -> array.array:
    fade = min(fade_frames, len(left) // 3, len(right) // 3)
    if fade <= 0:
        return array.array("f", list(left) + list(right))
    output = array.array("f", left[:-fade])
    for index in range(fade):
        amount = (index + 1) / (fade + 1)
        left_gain = math.cos(amount * math.pi * 0.5)
        right_gain = math.sin(amount * math.pi * 0.5)
        output.append(left[len(left) - fade + index] * left_gain + right[index] * right_gain)
    output.extend(right[fade:])
    return output


def make_preview(audio_dir: Path) -> Tuple[Path, int]:
    """Create a short crossfaded RPM-step demo for listening; not loaded by MTA."""
    names = (
        "z1000_idle.wav",
        "z1000_low.wav",
        "z1000_mid.wav",
        "z1000_high.wav",
        "z1000_redline.wav",
        "z1000_limiter.wav",
    )
    segment_frames = int(0.92 * SAMPLE_RATE)
    fade_frames = int(0.070 * SAMPLE_RATE)
    segments: List[array.array] = []
    for name in names:
        loop = read_pcm16(audio_dir / name)
        start = int(0.18 * SAMPLE_RATE)
        segment = array.array("f", loop[start : start + segment_frames])
        if len(segment) != segment_frames:
            raise RuntimeError("Not enough audio for preview segment: " + name)
        segments.append(segment)

    combined = segments[0]
    for segment in segments[1:]:
        combined = crossfade_join(combined, segment, fade_frames)
    preview_path = audio_dir / "synthetic_preview.wav"
    write_pcm16(preview_path, combined)
    return preview_path, len(combined)


def write_manifest(audio_dir: Path, reports: Dict[str, Dict[str, float]]) -> Path:
    lines = [
        "PROCEDURALLY GENERATED SYNTHETIC ENGINE APPROXIMATION",
        "=======================================================",
        "Not a genuine Kawasaki recording. Not measured from a Z1000. No source audio was used.",
        "Model: simplified, evenly fired four-stroke inline-four pulse series with RPM orders,",
        "soft cylinder imbalance, broad designed resonances, state-dependent noise, and an",
        "illustrative missed-fire pattern for the rev-limiter layer.",
        "Format: mono 16-bit PCM WAV, 48 kHz. Loop layers: 2.400 s nominal duration.",
        "The approximate character is a procedural sound-design choice, not model authentication.",
        "",
        "Generated layers:",
    ]
    for name, profile in PROFILES.items():
        report = reports[name]
        lines.append(
            "  {:<20} {:<28} {:>5} RPM | peak {:.3f} | RMS {:.3f} | loop edge {:.4f}".format(
                name, profile.filename, profile.rpm, report["peak"], report["rms"], report["seam_step"]
            )
        )
    shift = reports["shift"]
    lines.append(
        "  {:<20} {:<28} {:>5}       | peak {:.3f} | RMS {:.3f} | end {:.4f}".format(
            "shift", "z1000_shift.wav", 0, shift["peak"], shift["rms"], shift["seam_step"]
        )
    )
    lines.extend([
        "",
        "synthetic_preview.wav is a short RPM-step listening demo and is not listed in meta.xml.",
        "To replace the approximation with authentic audio, use licensed real source WAVs and",
        "the separate tools/build_audio.py processing workflow.",
    ])
    manifest = audio_dir / "synthetic_manifest.txt"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def validate_outputs(audio_dir: Path, expected_count: int) -> None:
    wav_paths = [audio_dir / profile.filename for profile in PROFILES.values()]
    wav_paths.append(audio_dir / "z1000_shift.wav")
    if len(wav_paths) != expected_count:
        raise RuntimeError("Internal expected WAV count mismatch")
    for path in wav_paths:
        with wave.open(str(path), "rb") as source:
            if source.getnchannels() != 1 or source.getsampwidth() != 2 or source.getframerate() != SAMPLE_RATE:
                raise RuntimeError("Invalid output format: " + str(path))
            minimum_frames = SAMPLE_RATE // 4 if path.name == "z1000_shift.wav" else SAMPLE_RATE // 2
            if source.getnframes() < minimum_frames:
                raise RuntimeError("Output unexpectedly short: " + str(path))
            raw = source.readframes(source.getnframes())
        values = array.array("h")
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        if not values or max(abs(value) for value in values) < 250:
            raise RuntimeError("Output is silent or too quiet: " + str(path))


def build(audio_dir: Path) -> int:
    audio_dir.mkdir(parents=True, exist_ok=True)
    reports: Dict[str, Dict[str, float]] = {}
    print("Generating synthetic inline-four approximation; this is not a real Z1000 recording.")
    for name, profile in PROFILES.items():
        samples, report = render_loop(profile)
        output_path = audio_dir / profile.filename
        write_pcm16(output_path, samples)
        reports[name] = report
        print("  {:<18} {:>5} RPM | {:.2f}s | peak {:.3f} | RMS {:.3f} | seam step {:.4f}".format(
            name, profile.rpm, report["duration"], report["peak"], report["rms"], report["seam_step"]
        ))

    shift_samples, shift_report = render_shift()
    write_pcm16(audio_dir / "z1000_shift.wav", shift_samples)
    reports["shift"] = shift_report
    print("  {:<18}       one-shot | {:.2f}s | peak {:.3f} | RMS {:.3f}".format(
        "shift", shift_report["duration"], shift_report["peak"], shift_report["rms"]
    ))

    preview_path, preview_frames = make_preview(audio_dir)
    validate_outputs(audio_dir, 17)
    manifest = write_manifest(audio_dir, reports)
    print("  Preview: {} ({:.2f}s; not loaded by MTA)".format(preview_path, preview_frames / SAMPLE_RATE))
    print("  Manifest: {}".format(manifest))
    print("Done. Files are synthetic and must not be described as authentic Kawasaki recordings.")
    return 0


def self_test() -> None:
    expected_cycles = round((2350 / 30.0) * LOOP_SECONDS)
    assert expected_cycles == 188 and expected_cycles % 4 == 0
    for name in ("idle", "limiter", "intake"):
        samples, report = render_loop(PROFILES[name])
        assert len(samples) == LOOP_FRAMES
        assert report["peak"] > 0.1 and report["rms"] > 0.01
        assert math.isfinite(report["seam_step"])
    shift, _ = render_shift()
    assert len(shift) == int(0.48 * SAMPLE_RATE)
    print("Self-test passed: non-silent 48 kHz loop models, integer firing-cycle anchors, and shift transient.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate clearly labelled synthetic inline-four audio layers (not a real Kawasaki recording)."
    )
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR,
                        help="output directory for the 17 resource WAVs and listening preview")
    parser.add_argument("--self-test", action="store_true",
                        help="exercise synthesis invariants without writing output files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    return build(args.audio_dir.resolve())


if __name__ == "__main__":
    sys.exit(main())
