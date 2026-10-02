#!/bin/sh
# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# Builds the reference-loader check (source/tools/librw_check.cpp) against aap/librw WITHOUT cmake:
# every librw .cpp is compiled directly (RW_NULL platform + the d3d/ps2/gl plugin sources, needed to read D3D9 TXDs).
# Needs: git, g++.   Output: /tmp/librw_check   usage: /tmp/librw_check model.dff texture.txd
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -d /tmp/librw ] || git clone --depth 1 https://github.com/aap/librw.git /tmp/librw
mkdir -p /tmp/lrw && cd /tmp/lrw
for f in /tmp/librw/src/*.cpp /tmp/librw/src/lodepng/lodepng.cpp /tmp/librw/src/d3d/*.cpp /tmp/librw/src/ps2/*.cpp /tmp/librw/src/gl/*.cpp; do
  n=$(echo "$f" | sed 's#/tmp/librw/src/##; s#/#_#g')
  g++ -std=c++14 -O1 -w -DRW_NULL -DLODEPNG_NO_COMPILE_DISK -I/tmp/librw -I/tmp/librw/src -I/tmp/librw/src/gl -c "$f" -o "$n.o" &
done
wait
g++ -O1 -w -DRW_NULL -I/tmp/librw -I/tmp/librw/src "$HERE/librw_check.cpp" /tmp/lrw/*.o -o /tmp/librw_check
echo built /tmp/librw_check
