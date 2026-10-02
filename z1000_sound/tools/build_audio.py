#!/usr/bin/env python3
"""Prepare MTA-ready Z1000 WAV layers from user-supplied clean reference WAVs.

Standard-library only. This tool does not synthesize an engine sound, download
recordings, or claim that any sound is a real Kawasaki recording.
"""

from __future__ import annotations

import argparse
import array
import math
import os
import sys
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RESOURCE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE_DIR = RESOURCE_DIR / "audio" / "reference"
DEFAULT_AUDIO_DIR = RESOURCE_DIR / "audio"
REPORT_NAME = "build_report.txt"

# (reference filename, output filename, loop?)
REQUIRED_SOURCES = {
    "idle": ("idle.wav", "z1000_idle.wav", True),
    "low RPM": ("low_rpm.wav", "z1000_low.wav", True),
    "mid RPM": ("mid_rpm.wav", "z1000_mid.wav", True),
    "high RPM": ("high_rpm.wav", "z1000_high.wav", True),
    "redline": ("redline.wav", "z1000_redline.wav", True),
    "acceleration": ("acceleration.wav", "z1000_accel.wav", True),
    "deceleration": ("deceleration.wav", "z1000_decel.wav", True),
    "engine braking": ("engine_brake.wav", "z1000_enginebrake.wav", True),
    "rev limiter": ("limiter.wav", "z1000_limiter.wav", True),
}

OPTIONAL_SOURCES = {
    "light acceleration": ("light_acceleration.wav", "z1000_light_accel.wav", True),
    "hard acceleration": ("hard_acceleration.wav", "z1000_hard_accel.wav", True),
    "throttle release": ("throttle_release.wav", "z1000_throttle_release.wav", True),
    "coasting": ("coasting.wav", "z1000_coast.wav", True),
    "intake": ("intake.wav", "z1000_intake.wav", True),
    "exhaust": ("exhaust.wav", "z1000_exhaust.wav", True),
    "gear shift transient": ("gear_shift.wav", "z1000_shift.wav", False),
    "helmet / onboard": ("helmet.wav", "z1000_helmet.wav", True),
}

SILENCE_THRESHOLD = 10.0 ** (-55.0 / 20.0)
TRIM_PADDING_SECONDS = 0.030
MINIMUM_PEAK = 10.0 ** (-48.0 / 20.0)


class AudioBuildError(Exception):
    """A user-facing source or processing validation error."""


def decode_pcm(raw: bytes, sample_width: int) -> array.array:
    """Decode little-endian integer PCM into a compact float array."""
    values = array.array("f")
    if sample_width == 1:
        for value in raw:
            values.append((value - 128) / 128.0)
        return values

    if sample_width == 2:
        decoded = array.array("h")
        decoded.frombytes(raw)
        if sys.byteorder != "little":
            decoded.byteswap()
        scale = 1.0 / 32768.0
        for value in decoded:
            values.append(value * scale)
        return values

    if sample_width == 3:
        for offset in range(0, len(raw), 3):
            value = raw[offset] | (raw[offset + 1] << 8) | (raw[offset + 2] << 16)
            if value & 0x800000:
                value -= 0x1000000
            values.append(value / 8388608.0)
        return values

    if sample_width == 4:
        decoded = array.array("i")
        decoded.frombytes(raw)
        if sys.byteorder != "little":
            decoded.byteswap()
        scale = 1.0 / 2147483648.0
        for value in decoded:
            values.append(value * scale)
        return values

    raise AudioBuildError("Unsupported PCM bit depth. Use integer PCM WAV at 8, 16, 24, or 32 bit.")


def frame_stats(values: array.array) -> Tuple[float, float, int]:
    peak = 0.0
    sum_squares = 0.0
    clipped = 0
    for value in values:
        absolute = abs(value)
        if absolute > peak:
            peak = absolute
        sum_squares += value * value
        if absolute >= 0.9995:
            clipped += 1
    rms = math.sqrt(sum_squares / max(1, len(values)))
    return peak, rms, clipped


def stereo_correlation(values: array.array, frame_count: int) -> Tuple[float, float, float]:
    if frame_count <= 1:
        return 1.0, 0.0, 0.0

    sum_left = 0.0
    sum_right = 0.0
    for frame in range(frame_count):
        sum_left += values[frame * 2]
        sum_right += values[frame * 2 + 1]
    mean_left = sum_left / frame_count
    mean_right = sum_right / frame_count

    covariance = 0.0
    variance_left = 0.0
    variance_right = 0.0
    rms_left = 0.0
    rms_right = 0.0
    for frame in range(frame_count):
        left = values[frame * 2]
        right = values[frame * 2 + 1]
        centered_left = left - mean_left
        centered_right = right - mean_right
        covariance += centered_left * centered_right
        variance_left += centered_left * centered_left
        variance_right += centered_right * centered_right
        rms_left += left * left
        rms_right += right * right

    denominator = math.sqrt(max(0.0, variance_left * variance_right))
    correlation = covariance / denominator if denominator > 0 else 1.0
    left_rms = math.sqrt(rms_left / frame_count)
    right_rms = math.sqrt(rms_right / frame_count)
    return max(-1.0, min(1.0, correlation)), left_rms, right_rms


def stereo_to_mono(values: array.array, frame_count: int, correlation: float) -> Tuple[array.array, str]:
    mono = array.array("f")
    if correlation < -0.20:
        correlation_value, left_rms, right_rms = stereo_correlation(values, frame_count)
        del correlation_value
        channel = 0 if left_rms >= right_rms else 1
        for frame in range(frame_count):
            mono.append(values[frame * 2 + channel])
        return mono, "selected the louder single channel to avoid phase cancellation"

    for frame in range(frame_count):
        mono.append((values[frame * 2] + values[frame * 2 + 1]) * 0.5)
    return mono, "averaged stereo to mono"


def trim_silence(samples: array.array, sample_rate: int) -> Tuple[array.array, int, int]:
    first = None
    last = None
    for index, value in enumerate(samples):
        if abs(value) >= SILENCE_THRESHOLD:
            if first is None:
                first = index
            last = index

    if first is None or last is None:
        raise AudioBuildError("The source is silent (or below -55 dBFS); refusing to build a silent engine layer.")

    padding = max(1, int(round(TRIM_PADDING_SECONDS * sample_rate)))
    start = max(0, first - padding)
    end = min(len(samples), last + padding + 1)
    return array.array("f", samples[start:end]), start, len(samples) - end


def remove_dc(samples: array.array) -> Tuple[array.array, float]:
    mean = sum(samples) / max(1, len(samples))
    if abs(mean) > 0.000001:
        for index in range(len(samples)):
            samples[index] -= mean
    return samples, mean


def crossfade_loop(samples: array.array, sample_rate: int, fade_milliseconds: float) -> Tuple[array.array, int, float, float]:
    if len(samples) < int(sample_rate * 0.5):
        raise AudioBuildError("A loop recording must contain at least 0.5 seconds after silence trimming.")

    fade_frames = max(16, int(round(sample_rate * fade_milliseconds / 1000.0)))
    fade_frames = min(fade_frames, max(16, len(samples) // 8))
    if len(samples) <= fade_frames * 2 + 1:
        raise AudioBuildError("Recording is too short for a click-safe loop crossfade.")

    original_seam = abs(samples[-1] - samples[0])
    output = array.array("f", samples[fade_frames : len(samples) - fade_frames])
    for index in range(fade_frames):
        alpha = index / float(fade_frames)
        tail = samples[len(samples) - fade_frames + index]
        head = samples[index]
        output.append(tail * (1.0 - alpha) + head * alpha)

    output_seam = abs(output[-1] - output[0])
    return output, fade_frames, original_seam, output_seam


def apply_one_shot_edge_fade(samples: array.array, sample_rate: int) -> None:
    fade_frames = min(max(1, int(round(sample_rate * 0.006))), len(samples) // 4)
    if fade_frames <= 0:
        return
    for index in range(fade_frames):
        fade_in = 0.5 - 0.5 * math.cos(math.pi * index / fade_frames)
        fade_out = 0.5 - 0.5 * math.cos(math.pi * index / fade_frames)
        samples[index] *= fade_in
        samples[len(samples) - 1 - index] *= fade_out


def normalize(samples: array.array, target_peak_db: float, max_gain_db: float) -> Tuple[array.array, float, float, float]:
    peak, _, _ = frame_stats(samples)
    if peak < MINIMUM_PEAK:
        raise AudioBuildError("The trimmed source is too quiet (below -48 dBFS peak); refusing unsafe normalization.")

    target_peak = 10.0 ** (target_peak_db / 20.0)
    maximum_gain = 10.0 ** (max_gain_db / 20.0)
    gain = min(target_peak / peak, maximum_gain)
    for index in range(len(samples)):
        samples[index] *= gain

    output_peak, _, _ = frame_stats(samples)
    return samples, peak, gain, output_peak


def write_pcm16_wav(path: Path, samples: array.array, sample_rate: int) -> None:
    pcm = array.array("h")
    for sample in samples:
        sample = max(-1.0, min(1.0, sample))
        pcm.append(int(round(sample * 32767.0)))
    if sys.byteorder != "little":
        pcm.byteswap()

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def process_source(
    label: str,
    source_path: Path,
    output_path: Path,
    is_loop: bool,
    target_peak_db: float,
    max_gain_db: float,
    fade_milliseconds: float,
    allow_clipped: bool,
) -> Dict[str, object]:
    if not source_path.is_file():
        raise AudioBuildError("Missing source file: " + str(source_path))

    try:
        with wave.open(str(source_path), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
            compression = source.getcomptype()
            raw = source.readframes(frame_count)
    except (wave.Error, OSError) as error:
        raise AudioBuildError("Could not read " + str(source_path) + ": " + str(error)) from error

    if compression != "NONE":
        raise AudioBuildError(str(source_path) + " is not uncompressed PCM WAV. Convert it to PCM WAV first.")
    if channels not in (1, 2):
        raise AudioBuildError(str(source_path) + " must be mono or stereo (1 or 2 channels).")
    if sample_rate < 16000 or sample_rate > 96000:
        raise AudioBuildError(str(source_path) + " sample rate must be between 16 kHz and 96 kHz.")
    if frame_count <= 0:
        raise AudioBuildError(str(source_path) + " contains no audio frames.")

    decoded = decode_pcm(raw, sample_width)
    source_peak, source_rms, clipped_count = frame_stats(decoded)
    if clipped_count:
        percentage = clipped_count * 100.0 / max(1, len(decoded))
        message = "{} has {} clipped source samples ({:.4f}%).".format(source_path.name, clipped_count, percentage)
        if not allow_clipped:
            raise AudioBuildError(message + " Re-record or pass --allow-clipped only if you accept the damage.")
        print("WARNING: " + message + " No declipping is performed.")

    correlation = 1.0
    downmix_note = "source was mono"
    if channels == 2:
        correlation, left_rms, right_rms = stereo_correlation(decoded, frame_count)
        mono, downmix_note = stereo_to_mono(decoded, frame_count, correlation)
        if correlation < -0.20:
            print("WARNING: {} has negative L/R phase correlation ({:.3f}); {}.".format(
                source_path.name, correlation, downmix_note
            ))
        elif correlation < 0.15:
            print("WARNING: {} stereo correlation is low ({:.3f}); verify stereo phase/placement.".format(
                source_path.name, correlation
            ))
        del decoded
    else:
        mono = decoded
        left_rms = source_rms
        right_rms = source_rms

    if source_peak < MINIMUM_PEAK:
        raise AudioBuildError(str(source_path) + " is nearly silent; no output was built.")

    trimmed, leading_trim, trailing_trim = trim_silence(mono, sample_rate)
    trimmed, dc_offset = remove_dc(trimmed)
    trimmed, pre_normalization_peak, gain, normalized_peak = normalize(trimmed, target_peak_db, max_gain_db)

    original_seam = None
    processed_seam = None
    crossfade_frames = 0
    if is_loop:
        trimmed, crossfade_frames, original_seam, processed_seam = crossfade_loop(
            trimmed, sample_rate, fade_milliseconds
        )
    else:
        apply_one_shot_edge_fade(trimmed, sample_rate)

    final_peak, final_rms, output_clipped = frame_stats(trimmed)
    if output_clipped:
        raise AudioBuildError(str(source_path) + " clipped after processing; output was not written.")

    write_pcm16_wav(output_path, trimmed, sample_rate)
    duration = len(trimmed) / float(sample_rate)
    report: Dict[str, object] = {
        "label": label,
        "source": str(source_path),
        "output": str(output_path),
        "sample_rate": sample_rate,
        "source_channels": channels,
        "source_bit_depth": sample_width * 8,
        "source_duration": frame_count / float(sample_rate),
        "source_peak": source_peak,
        "source_rms": source_rms,
        "clipped_samples": clipped_count,
        "stereo_correlation": correlation if channels == 2 else None,
        "left_rms": left_rms,
        "right_rms": right_rms,
        "downmix": downmix_note,
        "leading_trim_ms": leading_trim * 1000.0 / sample_rate,
        "trailing_trim_ms": trailing_trim * 1000.0 / sample_rate,
        "dc_offset_removed": dc_offset,
        "normalization_gain_db": 20.0 * math.log10(max(gain, 1.0e-12)),
        "peak_before_normalization": pre_normalization_peak,
        "peak_after_processing": final_peak,
        "rms_after_processing": final_rms,
        "duration_after_processing": duration,
        "loop": is_loop,
        "crossfade_ms": crossfade_frames * 1000.0 / sample_rate if is_loop else 0.0,
        "seam_jump_before": original_seam,
        "seam_jump_after": processed_seam,
        "output_format": "mono 16-bit integer PCM WAV",
    }

    if sample_rate != 48000:
        print("NOTE: {} is {} Hz; that rate is preserved. 48 kHz PCM is recommended for source capture.".format(
            source_path.name, sample_rate
        ))
    if is_loop and processed_seam is not None and processed_seam > 0.08:
        print("WARNING: {} loop seam step is {:.4f}; listen-test this loop and choose a steadier source segment.".format(
            source_path.name, processed_seam
        ))
    if abs(dc_offset) > 0.01:
        print("WARNING: {} had DC offset {:.4f}; mean DC was removed. This does not remove hum/noise.".format(
            source_path.name, dc_offset
        ))

    print("Built {:<22} {} | {} Hz | {}ch/{}bit -> mono/16bit | {:.2f}s | trim {:.0f}/{:.0f} ms | gain {:+.2f} dB | peak {:.3f} | seam {}".format(
        label,
        output_path.name,
        sample_rate,
        channels,
        sample_width * 8,
        duration,
        report["leading_trim_ms"],
        report["trailing_trim_ms"],
        report["normalization_gain_db"],
        final_peak,
        "{:.4f}".format(processed_seam) if processed_seam is not None else "one-shot",
    ))
    return report


def format_report(reports: List[Dict[str, object]], missing_optional: List[str]) -> str:
    lines = [
        "MTA:SA Z1000 audio build quality report",
        "========================================",
        "Output is 16-bit mono PCM WAV. Source sample rate is preserved.",
        "No EQ, compression, noise removal, limiting, or synthetic engine audio was applied.",
        "Normalization is peak-only and limited by the selected maximum gain.",
        "Loop seams use the configured linear tail-to-head crossfade.",
        "",
    ]
    for report in reports:
        lines.extend([
            "Layer: {}".format(report["label"]),
            "  Source: {}".format(report["source"]),
            "  Output: {}".format(report["output"]),
            "  Source format: {} Hz, {} channel(s), {} bit, {:.3f} s".format(
                report["sample_rate"], report["source_channels"], report["source_bit_depth"], report["source_duration"]
            ),
            "  Source peak / RMS: {:.5f} / {:.5f}; clipped samples: {}".format(
                report["source_peak"], report["source_rms"], report["clipped_samples"]
            ),
            "  Stereo correlation: {}".format(
                "n/a (mono source)" if report["stereo_correlation"] is None else "{:.4f}".format(report["stereo_correlation"])
            ),
            "  Downmix: {}".format(report["downmix"]),
            "  Trimmed leading/trailing: {:.1f} / {:.1f} ms".format(
                report["leading_trim_ms"], report["trailing_trim_ms"]
            ),
            "  Removed DC mean: {:.7f}; normalization gain: {:+.2f} dB".format(
                report["dc_offset_removed"], report["normalization_gain_db"]
            ),
            "  Output: {:.3f} s, peak {:.5f}, RMS {:.5f}, {}".format(
                report["duration_after_processing"], report["peak_after_processing"],
                report["rms_after_processing"], report["output_format"]
            ),
            "  Loop crossfade: {:.1f} ms; seam step before/after: {} / {}".format(
                report["crossfade_ms"],
                "n/a" if report["seam_jump_before"] is None else "{:.5f}".format(report["seam_jump_before"]),
                "n/a" if report["seam_jump_after"] is None else "{:.5f}".format(report["seam_jump_after"]),
            ),
            "",
        ])
    if missing_optional:
        lines.append("Optional sources not supplied; matching WAVs were left unchanged (synthetic in the bundled resource). Disable them for a real-recordings-only mix:")
        for name in missing_optional:
            lines.append("  - " + name)
        lines.append("")
    lines.extend([
        "Listening on the target MTA client is still required. Numeric seam checks cannot detect every click,",
        "bad take, unwanted ambience, or aesthetic issue. Reference rights/consent remain the user's responsibility.",
    ])
    return "\n".join(lines) + "\n"


def self_test() -> None:
    sample_rate = 48000
    samples = array.array("f")
    for index in range(sample_rate):
        # Test-only signal to exercise trim/crossfade math. It is never written as a game sound.
        value = 0.30 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate)
        samples.append(value)
    samples = array.array("f", [0.0] * 4800 + list(samples) + [0.0] * 4800)

    trimmed, leading, trailing = trim_silence(samples, sample_rate)
    assert leading > 0 and trailing > 0
    trimmed, _ = remove_dc(trimmed)
    trimmed, _, _, _ = normalize(trimmed, -2.0, 3.0)
    loop, fade_frames, before, after = crossfade_loop(trimmed, sample_rate, 80.0)
    assert len(loop) > 0 and fade_frames > 0
    assert after < 0.05

    one_shot = array.array("f", [0.2] * 1000)
    apply_one_shot_edge_fade(one_shot, sample_rate)
    assert abs(one_shot[0]) < 0.001 and abs(one_shot[-1]) < 0.001
    print("Self-test passed: silence trim, gentle normalization, loop crossfade, and one-shot edge fades.")


def build(args: argparse.Namespace) -> int:
    reference_dir: Path = args.reference_dir.resolve()
    audio_dir: Path = args.audio_dir.resolve()

    missing_required = []
    for label, (source_name, _, _) in REQUIRED_SOURCES.items():
        path = reference_dir / source_name
        if not path.is_file():
            missing_required.append("{} -> {}".format(label, path))
    if missing_required:
        print("Cannot build: genuine reference WAVs are required for the core mix.", file=sys.stderr)
        for item in missing_required:
            print("  Missing " + item, file=sys.stderr)
        print("See audio/reference/README.txt for the capture naming and recording guide.", file=sys.stderr)
        return 2

    available = []
    missing_optional = []
    for label, (source_name, output_name, is_loop) in REQUIRED_SOURCES.items():
        available.append((label, source_name, output_name, is_loop))
    for label, (source_name, output_name, is_loop) in OPTIONAL_SOURCES.items():
        if (reference_dir / source_name).is_file():
            available.append((label, source_name, output_name, is_loop))
        else:
            missing_optional.append(label)

    reports: List[Dict[str, object]] = []
    temporary_outputs: List[Tuple[Path, Path]] = []
    temporary_dir = Path(tempfile.mkdtemp(prefix="z1000-audio-", dir=str(audio_dir)))
    try:
        for index, (label, source_name, output_name, is_loop) in enumerate(available):
            source_path = reference_dir / source_name
            temporary_path = temporary_dir / output_name
            final_path = audio_dir / output_name
            report = process_source(
                label,
                source_path,
                temporary_path,
                is_loop,
                args.target_peak_db,
                args.max_gain_db,
                args.crossfade_ms,
                args.allow_clipped,
            )
            report["output"] = str(final_path)
            reports.append(report)
            temporary_outputs.append((temporary_path, final_path))

        # Replace outputs only after every supplied source passed validation.
        for temporary_path, final_path in temporary_outputs:
            os.replace(str(temporary_path), str(final_path))

        report_path = audio_dir / REPORT_NAME
        report_temporary = temporary_dir / REPORT_NAME
        report_temporary.write_text(format_report(reports, missing_optional), encoding="utf-8")
        os.replace(str(report_temporary), str(report_path))
        print("\nQuality report written to {}".format(report_path))
        print("Core layers built. Set Config.AudioReady = true in config.lua only after listening to the outputs.")
        if missing_optional:
            print("Optional layers were not rebuilt (bundled synthetic WAVs remain unchanged): " + ", ".join(missing_optional))
        return 0
    except (AudioBuildError, OSError, wave.Error) as error:
        print("Audio build failed: " + str(error), file=sys.stderr)
        return 1
    finally:
        for child in temporary_dir.glob("*"):
            try:
                child.unlink()
            except OSError:
                pass
        try:
            temporary_dir.rmdir()
        except OSError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process supplied genuine WAV reference captures into MTA-ready Z1000 layers."
    )
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR,
                        help="folder containing the named reference WAVs")
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR,
                        help="folder where the MTA WAV layers are written")
    parser.add_argument("--target-peak-db", type=float, default=-2.0,
                        help="conservative PCM peak target in dBFS (default: -2 dBFS)")
    parser.add_argument("--max-gain-db", type=float, default=3.0,
                        help="maximum normalization boost; no compression is applied (default: +3 dB)")
    parser.add_argument("--crossfade-ms", type=float, default=80.0,
                        help="linear loop-boundary crossfade length (default: 80 ms)")
    parser.add_argument("--allow-clipped", action="store_true",
                        help="permit clipped source input with a warning; clipping is not repaired")
    parser.add_argument("--self-test", action="store_true",
                        help="run processing math tests without writing audio outputs")
    args = parser.parse_args()
    if args.self_test:
        return args
    if not (-12.0 <= args.target_peak_db <= -0.1):
        parser.error("--target-peak-db must be between -12 and -0.1 dBFS")
    if not (0.0 <= args.max_gain_db <= 12.0):
        parser.error("--max-gain-db must be between 0 and 12 dB")
    if not (10.0 <= args.crossfade_ms <= 250.0):
        parser.error("--crossfade-ms must be between 10 and 250 ms")
    args.audio_dir.mkdir(parents=True, exist_ok=True)
    return args


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
