#!/usr/bin/env bash
# Render front/back copper+silk of a board to PNGs for checking silk placement.
# Usage: scripts/silk_preview.sh board.kicad_pcb outdir
set -euo pipefail
PCB=$1; OUT=$2; mkdir -p "$OUT"
for s in F B; do
  m=""; [[ $s == B ]] && m="--mirror"
  kicad-cli pcb export svg $m --mode-single --fit-page-to-board --exclude-drawing-sheet \
    -l $s.Cu,$s.SilkS,$s.Mask,Edge.Cuts -o "$OUT/silk_$s.svg" "$PCB" >/dev/null
  rsvg-convert -w 1600 -b white "$OUT/silk_$s.svg" -o "$OUT/silk_$s.png"
done
echo "$OUT/silk_F.png $OUT/silk_B.png"
