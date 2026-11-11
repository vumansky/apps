#!/bin/bash
# Wait for the patch pass, then assemble the final film.
cd "$(dirname "$0")"
until [ -f out/exr_hero/DONE ]; do sleep 20; done
python3 make_video.py out/exr out/deribasivska_autumn.mp4 --music out/music.wav --stills 24,110,150,170,185,200,262,312,380,440 out/stills > out/final.log 2>&1
