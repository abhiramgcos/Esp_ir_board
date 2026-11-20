#!/usr/bin/env bash
# One entry point for viewing, checking and regenerating the ESP32 IR board.
# Usage: scripts/esp.sh <command>   (run "scripts/esp.sh help" for the list)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -f "$ROOT/.venv/bin/activate" && -z "${VIRTUAL_ENV:-}" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

PRO=hardware/esp_ir_board.kicad_pro
SCH=hardware/esp_ir_board.kicad_sch
PCB=hardware/esp_ir_board.kicad_pcb
RENDER=build/render
PY=${PYTHON:-python3}

c_ok=$'\e[32m'; c_bad=$'\e[31m'; c_dim=$'\e[2m'; c_off=$'\e[0m'
[[ -t 1 ]] || { c_ok=; c_bad=; c_dim=; c_off=; }

need() {  # need <tool> [package hint]
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "${c_bad}Missing: $1${c_off} ${2:+($2)}" >&2
    echo "Run ./setup/install.sh to install the toolchain." >&2
    exit 1
  fi
}
launch() {  # run a GUI app detached
  if [[ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    echo "No display found; would run: $*" >&2; return 0
  fi
  nohup "$@" >/dev/null 2>&1 &
  disown || true
}
kicad_major() { kicad-cli version 2>/dev/null | grep -oE '^[0-9]+' | head -1 || echo 0; }
has_cli() { kicad-cli "$@" --help >/dev/null 2>&1; }   # e.g. has_cli sch erc
svg2png() {  # svg2png <in.svg> <out.png> [width]
  rsvg-convert -w "${3:-2000}" -b white "$1" -o "$2"
}
open_dir() {
  if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && command -v xdg-open >/dev/null; then
    launch xdg-open "$1"
  fi
}

cmd_help() {
  cat <<H
ESP32 IR board toolkit  (repo: $ROOT)

  open      KiCad project manager on $PRO
  sch       Schematic editor
  pcb       PCB editor
  3d        PCB editor + 3D viewer hint; renders PNGs if kicad-cli has 'pcb render' (KiCad 9+)
  gerbers   View fab/gerbers in gerbv
  render    Schematic + top/bottom/back-silk PNGs into $RENDER/
  check     ERC (netlist vs design), DRC, independent Gerber connectivity check
  bom       Print fab/BOM_full.csv as a table
  fab       Regenerate Gerbers, drills, BOMs, CPL and the zip in fab/
  rebuild   Regenerate the whole board from gen/ into build/ (does not touch hardware/)
  help      This list

Missing tools? Run ./setup/install.sh
H
}

cmd_open() { need kicad; launch kicad "$PRO"; echo "Opening KiCad: $PRO"; }
cmd_sch()  { need eeschema; launch eeschema "$SCH"; echo "Opening schematic: $SCH"; }
cmd_pcb()  { need pcbnew; launch pcbnew "$PCB"; echo "Opening PCB: $PCB"; }

cmd_3d() {
  need kicad-cli
  if has_cli pcb render; then
    mkdir -p "$RENDER"
    kicad-cli pcb render --side top    --quality high -w 1600 -h 1200 -o "$RENDER/3d_top.png"    "$PCB"
    kicad-cli pcb render --side bottom --quality high -w 1600 -h 1200 -o "$RENDER/3d_bottom.png" "$PCB"
    echo "3D renders: $RENDER/3d_top.png, $RENDER/3d_bottom.png"
    open_dir "$RENDER"
  else
    echo "${c_dim}kicad-cli $(kicad_major) has no 'pcb render' (needs KiCad 9+); skipping PNG renders.${c_off}"
  fi
  if command -v pcbnew >/dev/null; then
    launch pcbnew "$PCB"
    echo "In the PCB editor: View -> 3D Viewer (Alt+3)."
  fi
}

cmd_gerbers() {
  need gerbv "gerbv package"
  shopt -s nullglob
  local files=(fab/gerbers/*.g* fab/gerbers/*.drl)
  ((${#files[@]})) || { echo "No Gerbers in fab/gerbers - run: scripts/esp.sh fab" >&2; exit 1; }
  launch gerbv "${files[@]}"
  echo "gerbv: ${#files[@]} files"
}

cmd_render() {
  need kicad-cli; need rsvg-convert "librsvg / librsvg2-bin"
  local t; t=$(mktemp -d); mkdir -p "$RENDER"
  kicad-cli sch export svg -o "$t/sch" "$SCH" >/dev/null
  for s in "$t"/sch/*.svg; do svg2png "$s" "$RENDER/schematic.png" 3000; done
  kicad-cli pcb export svg --page-size-mode 2 --exclude-drawing-sheet \
    --layers F.Cu,F.SilkS,F.Mask,Edge.Cuts -o "$t/top.svg" "$PCB" >/dev/null
  kicad-cli pcb export svg --mirror --page-size-mode 2 --exclude-drawing-sheet \
    --layers B.Cu,Edge.Cuts -o "$t/bottom_copper.svg" "$PCB" >/dev/null
  kicad-cli pcb export svg --mirror --page-size-mode 2 --exclude-drawing-sheet \
    --layers B.SilkS,B.Mask,Edge.Cuts -o "$t/back_silk.svg" "$PCB" >/dev/null
  for n in top bottom_copper back_silk; do svg2png "$t/$n.svg" "$RENDER/$n.png" 1600; done
  rm -rf "$t"
  ls -1 "$RENDER"/*.png
  open_dir "$RENDER"
}

# shellcheck disable=SC2329  # helpers below are invoked indirectly via run()
cmd_check() {
  need kicad-cli; need "$PY"
  local fail=0 major; major=$(kicad_major); mkdir -p build/check
  run() {  # run <label> <cmd...>
    local label=$1; shift
    if "$@" >"build/check/$label.log" 2>&1; then echo "${c_ok}PASS${c_off}  $label"
    else echo "${c_bad}FAIL${c_off}  $label  (see build/check/$label.log)"; fail=1; fi
  }
  erc_netlist() {
    kicad-cli sch export netlist --format kicadsexpr -o build/check/esp_ir_board.net "$SCH" >/dev/null
    "$PY" gen/erc.py build/check/esp_ir_board.net | tee /dev/stderr | grep -q ', 0 problems'
  }
  run netlist-vs-design erc_netlist
  if has_cli sch erc; then
    kicad_erc() {
      kicad-cli sch erc --severity-error --exit-code-violations -o build/check/erc.rpt "$SCH"
    }
    run kicad-erc kicad_erc
  else
    echo "${c_dim}skip  kicad-erc (KiCad $major has no 'sch erc'; netlist check above covers connectivity)${c_off}"
  fi
  if has_cli pcb drc; then
    kicad_drc() {
      kicad-cli pcb drc --severity-error --exit-code-violations -o build/check/drc.rpt "$PCB"
    }
    run kicad-drc kicad_drc
  else
    py_drc() {
      local out; out=$("$PY" gen/drc.py "$PCB" build/check/drc.rpt fill 2>&1 | grep -v -i leak)
      echo "$out"
      ! grep -qE "'(clearance|shorting_items|unconnected_items|hole_clearance|track_dangling|via_dangling|tracks_crossing|copper_edge_clearance|items_not_allowed)'" <<<"$out"
    }
    run drc-pcbnew py_drc
  fi
  gerber_check() {
    local out; out=$("$PY" tools/gerber_connectivity.py fab/gerbers --circuit gen 2>&1 | grep -viE 'warn')
    echo "$out"
    grep -q 'shorts: 0  opens: 0' <<<"$out" && grep -q 'mismatches: 0' <<<"$out"
  }
  run gerber-connectivity gerber_check
  echo
  if ((fail)); then echo "${c_bad}CHECK FAILED${c_off}"; return 1; fi
  echo "${c_ok}ALL CHECKS PASSED${c_off}"
}

cmd_bom() {
  "$PY" - fab/BOM_full.csv <<'PY'
import csv, sys, shutil, signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
rows = list(csv.reader(open(sys.argv[1])))
cols = [0, 1, 2, 4, 5, 6]          # Qty, Designators, Value, MPN, LCSC, Assembly (skip long footprint)
rows = [[r[i] for i in cols] for r in rows]
width = shutil.get_terminal_size((160, 20)).columns
w = [min(max(len(r[i]) for r in rows), 34) for i in range(len(cols))]
cut = lambda s, n: s if len(s) <= n else s[:n - 1] + '…'
for k, r in enumerate(rows):
    print('  '.join(cut(c, w[i]).ljust(w[i]) for i, c in enumerate(r))[:width])
    if k == 0:
        print('  '.join('-' * x for x in w)[:width])
print(f"\n{sum(int(r[0]) for r in rows[1:])} parts in {len(rows) - 1} lines")
PY
}

cmd_fab() {
  need kicad-cli; need zip
  local F=fab
  rm -rf "$F/gerbers" && mkdir -p "$F/gerbers"
  kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
    -o "$F/gerbers/" "$PCB"
  kicad-cli pcb export drill --format excellon --excellon-separate-th --excellon-units mm \
    --generate-map --map-format pdf -o "$F/gerbers/" "$PCB"
  kicad-cli pcb export pos --format csv --units mm --side both -o "$F/pos_raw.csv" "$PCB"
  "$PY" gen/bom.py "$F/pos_raw.csv" "$F" && rm -f "$F/pos_raw.csv"
  rm -f "$F/esp_ir_board_v2_gerbers.zip"
  (cd "$F/gerbers" && zip -q -r ../esp_ir_board_v2_gerbers.zip . -x '*.pdf')
  kicad-cli pcb export pdf --layers F.Fab,F.SilkS,Edge.Cuts -o hardware/docs/assembly_top.pdf "$PCB" >/dev/null
  kicad-cli sch export pdf -o hardware/docs/esp_ir_board_schematic.pdf "$SCH" >/dev/null
  echo "Fab outputs refreshed in $F/ (run 'scripts/esp.sh check' to verify)"
}

cmd_rebuild() {
  echo "Regenerating the board from gen/ into build/ (new symbol UUIDs; takes a few minutes)."
  echo "hardware/ is NOT touched. Compare, then copy over by hand if you want it."
  need kicad-cli; need "$PY"
  bash gen/build.sh "$ROOT/build"
}

case "${1:-help}" in
  open|sch|pcb|3d|gerbers|render|check|bom|fab|rebuild|help) "cmd_${1:-help}" ;;
  -h|--help) cmd_help ;;
  *) echo "Unknown command: $1" >&2; cmd_help; exit 2 ;;
esac
