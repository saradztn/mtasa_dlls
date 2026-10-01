# mtasa_dlls

This repository currently contains the `z1000_sound/` MTA:SA client resource: a configurable, layered, 3D motorcycle-audio mixer and an offline quality-check/build pipeline for user-supplied Kawasaki Z1000 reference recordings.

**Audio source status:** no genuine Z1000 recordings were present in the checkout. The bundled WAVs are silence placeholders and `Config.AudioReady` is deliberately `false`; no synthetic or GTA:SA engine audio is presented as the requested real reference sound. See [`z1000_sound/README.txt`](z1000_sound/README.txt) and [`z1000_sound/audio/reference/README.txt`](z1000_sound/audio/reference/README.txt) for setup, recording inputs, processing, tuning, and the MTA limitation around selectively muting native vehicle sounds.
