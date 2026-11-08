#!/bin/sh
# One-command build: sound events → picture → score and foley → final film.
# Needs the Lemo-Opuscar library (set LIB, or keep it at ~/lemo-opuscar) with `setup.sh deps`
# and the vsco2ce + vcsl sample libraries (sh tools/fetch.sh instruments vsco2ce vcsl).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
LIB=${LIB:-$HOME/lemo-opuscar}
export LIB
[ -f "$LIB/core/render/video.mjs" ] || { echo "set LIB to the library folder"; exit 1; }
SIZE=1080x1350
cd "$LIB"
node core/render/events.mjs "$HERE" --size $SIZE
node core/render/video.mjs "$HERE" --fps 24 --workers 6 --size $SIZE --out "$HERE/out/video.mp4"
"$LIB/.venv/bin/python" "$HERE/mix.py"
sh core/render/mux.sh "$HERE/out/video.mp4" "$HERE/out/mix.wav" "$HERE/rakesh-steels-diwali.mp4" 24 1
node core/render/still.mjs "$HERE" 36 --size $SIZE --out "$HERE/out" --prefix poster_
cp "$HERE/out/poster_36.jpg" "$HERE/poster.jpg"
