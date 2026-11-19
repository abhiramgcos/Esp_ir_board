#!/usr/bin/env bash
# Rebuild the whole board from gen/circuit.py + gen/placement.py.
# Needs: KiCad 7+ (pcbnew python module, kicad-cli), python3 with kiutils, numpy, scipy, pillow, scikit-image.
# NOTE: regenerating the schematic creates new symbol UUIDs, so always rebuild the PCB from the same run.
set -euo pipefail
cd "$(dirname "$0")"
OUT=${1:-../build}
mkdir -p "$OUT"
python3 sch.py "$OUT/esp_ir_board.kicad_sch"
kicad-cli sch export netlist --format kicadsexpr -o "$OUT/esp_ir_board.net" "$OUT/esp_ir_board.kicad_sch"
python3 erc.py "$OUT/esp_ir_board.net"                                     # netlist-level ERC
rm -f "$OUT/esp_ir_board.kicad_pcb" "$OUT/esp_ir_board.kicad_pro"
python3 pcb.py "$OUT/esp_ir_board.kicad_sch" "$OUT/placed.kicad_pcb"         # footprints, nets, outline, rules
python3 zones.py keepout "$OUT/placed.kicad_pcb"                             # no top tracks under ESP32
python3 router.py "$OUT/placed.kicad_pcb" "$OUT/esp_ir_board.kicad_pcb"      # 2-layer maze router
cp ../hardware/esp_ir_board.kicad_dru "$OUT/"
python3 zones.py pour "$OUT/esp_ir_board.kicad_pcb"                          # antenna keepout, GND pours, stitching
python3 silk.py "$OUT/esp_ir_board.kicad_pcb" || true                        # labels + doodle (step 4)
python3 drc.py "$OUT/esp_ir_board.kicad_pcb" "$OUT/drc.rpt" fill
