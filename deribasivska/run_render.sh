#!/bin/bash
# Full render: colour frames (resumable; existing frames are skipped), depth frames in parallel.
cd "$(dirname "$0")"
mkdir -p out/exr
python3 render.py -- --range 1 480 --res 1280 720 --out out/exr --depth > out/depth.log 2>&1 &
python3 render.py -- --range 1 300 --res 1280 720 --spp 7 --out out/exr > out/render_a.log 2>&1
python3 render.py -- --range 301 480 --res 1280 720 --spp 8 --out out/exr > out/render_b.log 2>&1
wait
touch out/exr/DONE
