Z1000 AUDIO REFERENCE INPUTS
============================

This directory intentionally contains no Kawasaki recordings. Add clean recordings that
are yours or that you are licensed to use. The resource's distributed z1000_*.wav files
are silence placeholders, not engine samples.

REQUIRED PCM WAV source files
-----------------------------
idle.wav             Stable warm idle; no starter/cranking transient in the loop section
low_rpm.wav          Steady low RPM under light load
mid_rpm.wav          Steady mid RPM with a full inline-four harmonic character
high_rpm.wav         Steady high RPM, below limiter
redline.wav          Steady high/redline region, not a limiter cut
acceleration.wav     Sustained real acceleration/load recording for a loop layer

deceleration.wav     Throttle-off roll-down / exhaust overrun layer
engine_brake.wav     Real closed-throttle engine-braking layer
limiter.wav          Actual rev-limiter pulse/cut recording; choose a loopable section

OPTIONAL WAV source files
-------------------------
light_acceleration.wav  Gentle throttle/load, useful for 10-40% throttle
hard_acceleration.wav  Strong acceleration/load, clean and not distorted
throttle_release.wav   Short, natural lift-off response; processed as a loop layer
coasting.wav           Low-load/freewheel pass, distinct from engine braking
intake.wav             Intake/front-side recording
exhaust.wav            Exhaust/rear-side recording
gear_shift.wav         A short shift/re-engagement transient; output is not looped
helmet.wav             Separate onboard/helmet recording; played 2D only for local driver

Capture notes
-------------
- Record a real Kawasaki Z1000, preferably the generation/engine you want to represent.
- Keep music, speech, wind blasts, traffic, and other engines out of the useful segment.
- Capture PCM WAV (24-bit/48 kHz preferred); the build tool also accepts integer PCM 8/16/24/32-bit
  WAV at 16-96 kHz and retains its sample rate. It outputs mono 16-bit PCM WAV.
- Record RPM for each steady loop and use Config.RPM.LayerAnchors / OverlayAnchors to match
  the real recorded RPM. For dynamic layers, record a stable repeated texture, not a whole
  gear-changing ride with varying RPM.
- Avoid clipping, limiter pumping from the recorder, wind noise, abrupt cuts, long silence,
  or different microphone distances between adjacent RPM loops. Do not normalize the recorder
  so aggressively that the exhaust is already distorted.
- For stereo captures, the tool checks left/right phase and downmixes to mono for 3D playback.
  A strongly out-of-phase capture is reduced to its louder channel with a warning; correct the
  microphone/phase issue at the source whenever possible.

Build from the resource directory with:
    python3 tools/build_audio.py --self-test
    python3 tools/build_audio.py

The nine required sources must exist for a successful core build. Optional sources that are
absent are not rebuilt; on a fresh checkout their matching output remains a silence placeholder.
Keep their Config.LayerEnabled flag false unless you have supplied and reviewed that sample.
The builder reports clipping, input sample rate/bit depth/channel count, phase correlation,
trimmed silence, normalization gain, and loop seam discontinuity in audio/build_report.txt.
It does not denoise, EQ, compress, limit, or fabricate missing source content.
