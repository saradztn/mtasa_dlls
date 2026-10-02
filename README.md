# mtasa_dlls

This repository contains the `z1000_sound/` MTA:SA client resource: a configurable, layered 3D motorcycle-audio mixer with RPM/load-driven states, cleanup, test commands, and an offline WAV workflow. It now targets vehicle model ID `522` by default. To make the server start it automatically at boot, add the line in [`z1000_sound/mtaserver.conf-snippet.txt`](z1000_sound/mtaserver.conf-snippet.txt) to the existing `<resources>` section of `mods/deathmatch/mtaserver.conf`.

**Audio status:** the bundled WAVs are a procedurally generated synthetic inline-four approximation. They are audible, but they are **not genuine Kawasaki Z1000 recordings** and must not be described as authentic model-specific audio. No GTA:SA stock samples or generic bike recordings were used. `z1000_sound/audio/synthetic_preview.wav` is a short listening demo; the MTA resource does not load it. See [`z1000_sound/README.txt`](z1000_sound/README.txt) for installation, configuration, and how to replace the simulation with properly licensed real recordings.

Regenerate the synthetic layers with `python3 z1000_sound/tools/synthesize_engine.py`. This overwrites the bundled `z1000_*.wav` files. To process user-owned/licensed genuine recordings instead, follow [`z1000_sound/audio/reference/README.txt`](z1000_sound/audio/reference/README.txt) and use `tools/build_audio.py`.
