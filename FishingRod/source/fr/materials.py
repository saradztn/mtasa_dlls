# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# materials.py - single source of truth for the material / texture set.
#
# Every entry becomes (a) one RenderWare material in the DFF, (b) one diffuse
# texture in the TXD (DXT1/DXT5) and (c) two companion maps (normal + ORM) that
# are written as DXT DDS files for the MTA shader.
#
#   env   : MatFX environment-map coefficient (in-game reflection w/o shader)
#   size  : (w, h) of the diffuse / normal / ORM maps (power of two, DXT safe)
#   rgb   : fallback flat colour used only by the debug renderer

MATS = [
    dict(key='carbon',   tex='fr_carbon',      size=(1024, 1024), env=0.22, rgb=(0.02, 0.02, 0.025), rough=0.20, metal=0.0),
    dict(key='label',    tex='fr_blank_label', size=(512, 2048),  env=0.22, rgb=(0.02, 0.02, 0.025), rough=0.20, metal=0.0),
    dict(key='eva',      tex='fr_eva',         size=(1024, 1024), env=0.0,  rgb=(0.04, 0.04, 0.04),   rough=0.85, metal=0.0),
    dict(key='cork',     tex='fr_cork',        size=(1024, 1024), env=0.0,  rgb=(0.42, 0.28, 0.16),   rough=0.75, metal=0.0),
    dict(key='rubber',   tex='fr_rubber',      size=(512, 512),   env=0.0,  rgb=(0.03, 0.03, 0.03),   rough=0.90, metal=0.0),
    dict(key='alu_dark', tex='fr_alu_dark',    size=(1024, 1024), env=0.38, rgb=(0.13, 0.13, 0.14),   rough=0.38, metal=1.0),
    dict(key='alu_gold', tex='fr_alu_gold',    size=(1024, 1024), env=0.42, rgb=(0.70, 0.50, 0.18),   rough=0.34, metal=1.0),
    dict(key='paint',    tex='fr_paint',       size=(512, 512),   env=0.30, rgb=(0.04, 0.045, 0.05),  rough=0.28, metal=0.6),
    dict(key='chrome',   tex='fr_chrome',      size=(512, 512),   env=0.70, rgb=(0.78, 0.80, 0.83),   rough=0.12, metal=1.0),
    dict(key='ceramic',  tex='fr_ceramic',     size=(256, 256),   env=0.35, rgb=(0.10, 0.11, 0.13),   rough=0.10, metal=0.0),
    dict(key='thread',   tex='fr_thread',      size=(512, 512),   env=0.18, rgb=(0.50, 0.04, 0.04),   rough=0.14, metal=0.0),
    dict(key='plastic',  tex='fr_plastic',     size=(512, 512),   env=0.0,  rgb=(0.03, 0.03, 0.035),  rough=0.55, metal=0.0),
    dict(key='plate',    tex='fr_reel_plate',  size=(1024, 1024), env=0.30, rgb=(0.05, 0.05, 0.055),  rough=0.35, metal=1.0),
    dict(key='linewound', tex='fr_line_wound', size=(512, 512),   env=0.0,  rgb=(0.60, 0.66, 0.46),   rough=0.45, metal=0.0),
    dict(key='line',     tex='fr_line',        size=(64, 64),     env=0.0,  rgb=(0.62, 0.68, 0.50),   rough=0.20, metal=0.0),
]
IDX = {m['key']: i for i, m in enumerate(MATS)}
ENV_TEX = 'fr_env'          # environment map referenced by MatFX (256x256 DXT1)
ENV_SIZE = (256, 256)


def M(key):
    return IDX[key]
