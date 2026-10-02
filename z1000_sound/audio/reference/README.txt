Z1000 AUDIO REFERENCE INPUTS
============================

This folder contains no source recordings. The distributed z1000_*.wav files are a
procedurally generated synthetic inline-four approximation. They are NOT recordings of a
Kawasaki Z1000 and must not be represented as authentic bike audio. See
../synthetic_manifest.txt for the generator's explicit design notes and generated layers.

Use this input folder only if replacing the synthetic approximation with recordings you own
or are licensed to process and redistribute inside an MTA resource. Keep source files local;
the folder's WAV/MP3/OGG/FLAC inputs are excluded from Git by .gitignore.

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
hard_acceleration.wav   Strong acceleration/load, clean and not distorted
throttle_release.wav    Short, natural lift-off response; processed as a loop layer
coasting.wav            Low-load/freewheel recording, distinct from engine braking
intake.wav              Intake/front-side recording
exhaust.wav             Exhaust/rear-side recording
gear_shift.wav          A short shift/re-engagement transient; output is not looped
helmet.wav              Separate onboard/helmet recording; played 2D only for local driver

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

The nine required sources must exist for a successful core build. Supplied required sources
replace the matching synthetic core WAVs. Optional sources replace their matching layer only
when supplied; missing optional sources leave the current WAV untouched (synthetic in this
checkout), so disable those Config.LayerEnabled flags if you want a real-recordings-only mix.
The optional gear-shift WAV likewise replaces z1000_shift.wav only when gear_shift.wav exists.
Keep Config.ShiftTransientEnabled=false if you want a real-only mix but have no real shift take.

The builder reports clipping, input sample rate/bit depth/channel count, phase correlation,
trimmed silence, normalization gain, and loop seam discontinuity in audio/build_report.txt.
It does not denoise, EQ, compress, limit, download audio, or fabricate missing source content.
