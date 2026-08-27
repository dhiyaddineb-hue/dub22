#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT="${1:-$ROOT/assets/input/source.mp4}"
OUTPUT="${2:-$ROOT/outputs/arabic_dub_latest.mp4}"

mkdir -p "$(dirname "$OUTPUT")"

ffmpeg -y \
  -i "$INPUT" \
  -i "$ROOT/assets/audio/line_01.wav" \
  -i "$ROOT/assets/audio/line_02.wav" \
  -i "$ROOT/assets/audio/line_03.wav" \
  -i "$ROOT/assets/audio/line_04.wav" \
  -i "$ROOT/assets/audio/line_05.wav" \
  -i "$ROOT/assets/audio/line_06.wav" \
  -filter_complex \
  "anullsrc=r=24000:cl=mono:d=24.842[bed];\
   [1:a]atempo=1.5,adelay=700:all=1[a1];\
   [2:a]adelay=1900:all=1[a2];\
   [3:a]adelay=8100:all=1[a3];\
   [4:a]adelay=11100:all=1[a4];\
   [5:a]atempo=1.2,adelay=14000:all=1[a5];\
   [6:a]adelay=15900:all=1[a6];\
   [bed][a1][a2][a3][a4][a5][a6]amix=inputs=7:duration=first:dropout_transition=0:normalize=0[a]" \
  -map 0:v:0 -map "[a]" \
  -c:v copy -c:a aac -b:a 160k -movflags +faststart \
  "$OUTPUT"

echo "Wrote $OUTPUT"
