#!/usr/bin/env bash
# Copper layout images in KiCad's default colours on the editor's dark background:
#   <prefix>_routing.png        F.Cu (red) + B.Cu (blue) overlaid, GND pours hidden -> every trace and via visible
#   <prefix>_copper_top.png     F.Cu with pours
#   <prefix>_copper_bottom.png  B.Cu with pours, mirrored (as seen from below)
# Usage: scripts/copper_views.sh [board.kicad_pcb] [out_prefix]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PCB=${1:-$ROOT/hardware/esp_ir_board.kicad_pcb}
OUT=${2:-$ROOT/docs/img/v2.1}
PY=$ROOT/.venv/bin/python3; [[ -x $PY ]] || PY=python3
BG='#001023'; W=2400
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# copy of the board without copper pours (rule-area keep-outs stay, they are not drawn on copper)
"$PY" - "$PCB" "$TMP/nopour.kicad_pcb" <<'PY' 2>/dev/null
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
keep = []
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z); keep.append(z)   # keep a reference (KiCad 9 SWIG frees removed items otherwise)
pcbnew.SaveBoard(sys.argv[2], b)
PY

svg() {  # svg <board> <layers> <out.svg> [--mirror]
  kicad-cli pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet --drill-shape-opt 2 \
    ${4:-} -l "$2" -o "$3" "$1" >/dev/null
}
png() {  # render on the dark background, then crop to the board with an even margin
  rsvg-convert -w $W -b "$BG" "$1" -o "$2"
  "$PY" - "$2" "$BG" <<'PY'
import sys
from PIL import Image, ImageChops
f, bg = sys.argv[1], sys.argv[2]
im = Image.open(f).convert("RGB")
diff = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L").point(lambda v: 255 if v > 24 else 0)
l, t, r, b = diff.getbbox()
pad = 40
out = Image.new("RGB", (r - l + 2 * pad, b - t + 2 * pad), bg)
out.paste(im.crop((l, t, r, b)), (pad, pad))
out.save(f, optimize=True)
PY
}

svg "$TMP/nopour.kicad_pcb" B.Cu,F.Cu,Edge.Cuts "$TMP/routing.svg"
svg "$PCB" F.Cu,Edge.Cuts "$TMP/top.svg"
svg "$PCB" B.Cu,Edge.Cuts "$TMP/bottom.svg" --mirror
png "$TMP/routing.svg" "${OUT}_routing.png"
png "$TMP/top.svg" "${OUT}_copper_top.png"
png "$TMP/bottom.svg" "${OUT}_copper_bottom.png"
echo "${OUT}_routing.png ${OUT}_copper_top.png ${OUT}_copper_bottom.png"
