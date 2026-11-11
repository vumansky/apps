#!/bin/bash
# After the main render: re-render the hero-facade frames with the corrected facade colour.
cd "$(dirname "$0")"
until [ -f out/exr/DONE ]; do sleep 20; done
python3 render.py -- --blend out/scene_hero.blend --range 118 236 --res 1280 720 --spp 7 --out out/exr_hero > out/render_hero.log 2>&1
touch out/exr_hero/DONE
