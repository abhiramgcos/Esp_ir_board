#!/usr/bin/env bash
# ESP32 IR board - local toolchain installer.
#
#   bash setup/install.sh            # system packages (sudo) + .venv + self-test
#   bash setup/install.sh --conda    # ...plus the optional conda env "esp-ir"
#   bash setup/install.sh --no-system  # skip sudo installs (KiCad etc. already present)
#
# Safe to re-run: installed packages are skipped, the venv is reused and updated.
set -euo pipefail

# ------------------------------------------------------------------ helpers
if [[ -t 1 ]]; then
  B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; C=$'\e[36m'; N=$'\e[0m'
else
  B=; G=; Y=; R=; C=; N=
fi
step() { printf '\n%s==>%s %s%s%s\n' "$C" "$N" "$B" "$*" "$N"; }
ok()   { printf '  %s✔%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
err()  { printf '  %s✘%s %s\n' "$R" "$N" "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
  cat <<EOF
Options:
  --no-system   skip installing system packages (no sudo needed)
  --conda       also create/update the conda env 'esp-ir' from setup/environment.yml
  -h, --help    show this help
EOF
}

DO_SYSTEM=1; DO_CONDA=0
for a in "$@"; do
  case "$a" in
    --no-system) DO_SYSTEM=0 ;;
    --conda) DO_CONDA=1 ;;
    -h|--help) usage; exit 0 ;;
    *) err "unknown option: $a"; usage; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SUDO=""; [[ $(id -u) -ne 0 ]] && SUDO="sudo"
FAILS=()

kicad_major() {
  have kicad-cli || { echo 0; return; }
  kicad-cli version 2>/dev/null | grep -oE '^[0-9]+' | head -1 || echo 0
}

# ------------------------------------------------------------------ 1. system packages
install_system() {
  step "System packages"
  [[ -r /etc/os-release ]] && . /etc/os-release
  local id="${ID:-unknown}" like="${ID_LIKE:-}"
  ok "Detected: ${PRETTY_NAME:-$id}"

  if have pacman; then
    # Arch / CachyOS / Manjaro / EndeavourOS
    local pkgs=(kicad kicad-library gerbv librsvg git python python-pip xdg-utils) missing=()
    for p in "${pkgs[@]}"; do pacman -Qi "$p" >/dev/null 2>&1 || missing+=("$p"); done
    if ((${#missing[@]})); then
      ok "Installing: ${missing[*]}"
      $SUDO pacman -S --needed --noconfirm "${missing[@]}"
    else ok "All packages already installed"; fi

  elif have apt-get; then
    local pkgs=(kicad gerbv librsvg2-bin git python3 python3-venv python3-pip xdg-utils) missing=()
    # Ubuntu (and derivatives): KiCad 9 from the official PPA unless KiCad 8+ is already there
    if [[ "$id" == "ubuntu" || "$like" == *ubuntu* ]] && (( $(kicad_major) < 8 )); then
      if ! grep -rqs "kicad/kicad-9.0-releases" /etc/apt/sources.list /etc/apt/sources.list.d/; then
        ok "Adding PPA kicad/kicad-9.0-releases"
        $SUDO apt-get update -qq
        $SUDO apt-get install -y -qq software-properties-common
        $SUDO add-apt-repository -y ppa:kicad/kicad-9.0-releases || warn "PPA could not be added; using distro KiCad"
      fi
      missing+=(kicad)   # force upgrade from the PPA
    fi
    for p in "${pkgs[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
    if ((${#missing[@]})); then
      mapfile -t missing < <(printf '%s\n' "${missing[@]}" | sort -u)
      ok "Installing: ${missing[*]}"
      $SUDO apt-get update -qq
      $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
    else ok "All packages already installed"; fi

  elif have dnf; then
    local pkgs=(kicad gerbv librsvg2-tools git python3 python3-pip xdg-utils) missing=()
    for p in "${pkgs[@]}"; do rpm -q "$p" >/dev/null 2>&1 || missing+=("$p"); done
    if ((${#missing[@]})); then
      ok "Installing: ${missing[*]}"
      $SUDO dnf install -y "${missing[@]}"
    else ok "All packages already installed"; fi

  else
    warn "No pacman/apt/dnf found. Install KiCad 8+, gerbv, librsvg, git, python3 manually, then re-run with --no-system."
  fi
}

# ------------------------------------------------------------------ 2. python venv
setup_venv() {
  step "Python venv (.venv)"
  # pcbnew is a compiled module that KiCad installs for the *system* python only,
  # so the venv must inherit system site-packages to see it.
  # Prefer the system interpreter: an active conda base would otherwise shadow it and pcbnew won't import.
  local py=/usr/bin/python3; [[ -x $py ]] || { py=python3; have python3 || py=python; }
  if [[ ! -x .venv/bin/python ]]; then
    "$py" -m venv --system-site-packages .venv
    ok "Created .venv (inherits system site-packages for pcbnew)"
  else ok ".venv already exists - updating"; fi
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r setup/requirements.txt
  ok "Installed setup/requirements.txt"
  if .venv/bin/python -c "import pcbnew" 2>/dev/null; then
    ok "pcbnew $(.venv/bin/python -c 'import pcbnew; print(pcbnew.Version())') importable"
  else
    err "pcbnew NOT importable from .venv"
    warn "The .venv python must be the same python KiCad was built for (usually /usr/bin/python3)."
    warn "Fix: rm -rf .venv && /usr/bin/python3 -m venv --system-site-packages .venv && re-run this script."
    FAILS+=("pcbnew import")
  fi
}

# ------------------------------------------------------------------ 3. optional conda env
setup_conda() {
  step "Conda env 'esp-ir' (optional)"
  # Conda's python is a different interpreter from the one KiCad compiled pcbnew
  # against, so pcbnew cannot be imported there. Use this env only for the Gerber
  # checker / viewers; run the KiCad generators from .venv.
  local conda=""
  for c in "$(command -v conda 2>/dev/null || true)" "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" "$HOME/.anaconda/bin/conda"; do
    [[ -n "$c" && -x "$c" ]] && { conda="$c"; break; }
  done
  if [[ -z "$conda" ]]; then warn "conda not found (looked in PATH, ~/miniconda3, ~/anaconda3) - skipping"; return; fi
  ok "Using $conda"
  if "$conda" env list | awk '{print $1}' | grep -qx esp-ir; then
    "$conda" env update -n esp-ir -f setup/environment.yml --prune
    ok "Updated env esp-ir"
  else
    "$conda" env create -f setup/environment.yml
    ok "Created env esp-ir  (activate: conda activate esp-ir)"
  fi
}

# ------------------------------------------------------------------ 4. self-test
self_test() {
  step "Self-test"
  local km; km=$(kicad_major)
  if have kicad-cli; then
    ok "kicad-cli $(kicad-cli version 2>/dev/null)"
    if (( km < 8 )); then warn "KiCad $km: 'kicad-cli sch erc' / 'pcb drc' need KiCad 8+ (gen/drc.py uses the Python API and still works)"; fi
  else
    err "kicad-cli not found"; FAILS+=("kicad-cli")
  fi

  if .venv/bin/python -c "import pcbnew, kiutils, skimage, pygerber, scipy, PIL, numpy" 2>/dev/null; then
    ok "Python imports: pcbnew kiutils skimage pygerber scipy PIL numpy"
  else
    err "Python imports failed:"; .venv/bin/python -c "import pcbnew, kiutils, skimage, pygerber" || true
    FAILS+=("python imports")
  fi

  local out
  if out=$(.venv/bin/python tools/gerber_connectivity.py fab/gerbers --circuit gen 2>&1); then
    if grep -q "shorts: 0  opens: 0" <<<"$out" && grep -q "mismatches: 0" <<<"$out"; then
      ok "Gerber check: $(grep -E '^nets:' <<<"$out")"
    else err "Gerber check reported problems:"; echo "$out" | grep -vi warn | tail -10; FAILS+=("gerber check"); fi
  else err "Gerber check crashed:"; echo "$out" | tail -10; FAILS+=("gerber check"); fi

  if have kicad-cli; then
    local tmp; tmp=$(mktemp -d)
    if kicad-cli sch export netlist --format kicadsexpr -o "$tmp/esp_ir_board.net" hardware/esp_ir_board.kicad_sch >/dev/null 2>&1 \
       && out=$(.venv/bin/python gen/erc.py "$tmp/esp_ir_board.net" 2>&1) && grep -q " 0 problems" <<<"$out"; then
      ok "Schematic ERC: $(tail -1 <<<"$out")"
    else err "Schematic ERC failed:"; echo "${out:-netlist export failed}" | tail -10; FAILS+=("schematic erc"); fi
    rm -rf "$tmp"
  fi
}

# ------------------------------------------------------------------ run
printf '%sESP32 IR board toolchain installer%s  (%s)\n' "$B" "$N" "$ROOT"
if (( DO_SYSTEM )); then install_system; else step "System packages: skipped (--no-system)"; fi
setup_venv
if (( DO_CONDA )); then setup_conda; fi
self_test

echo
if ((${#FAILS[@]})); then
  printf '%s%sSetup finished with problems:%s %s\n' "$B" "$R" "$N" "${FAILS[*]}"
  echo "See setup/README.md -> Troubleshooting."
  exit 1
fi
printf '%s%sAll good.%s Next:\n' "$B" "$G" "$N"
cat <<EOF
  source .venv/bin/activate        # use the toolchain in this shell
  make help                        # list viewer / check / build targets
  make open                        # open the board in KiCad
  make render                      # PNG renders of schematic + both sides
  make check                       # ERC/DRC/Gerber verification
  kicad hardware/esp_ir_board.kicad_pro
  gerbv fab/gerbers/*.g* fab/gerbers/*.drl
EOF
