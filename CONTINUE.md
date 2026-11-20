# CONTINUE.md: handoff for the local Claude session

You (Claude) are taking over the **ESP32 IR Blaster/Receiver board** project from a cloud session.
This file is everything you need. Read it fully before touching anything.

---

## 0. TL;DR: what to do first

```bash
cd ~/Desktop/projects/Esp_ir_board
git fetch && git checkout v2.1-optimize && git pull
./setup/install.sh --no-system        # refresh .venv (new 3D-render deps); add --conda for the conda env
source .venv/bin/activate
kicad-cli version                      # expect 9.x (Ubuntu 26.04 distro or PPA)
make check                             # v2.0 hardware/ must pass on this machine first
```

Then finish the **v2.1 optimized board** (section 5). After that, update the README with 3D views and photos,
then commit and push (section 6).

---

## 1. Who / where

* **User:** Abhiram (GitHub `abhiramgcos`), CSE student. He also works on embedded vision (Jetson Orin) and
  KUKA robots.
* **Messages:** He writes short, informal messages from his phone or laptop. Act on the clear intent, and ask
  only when a wrong guess is expensive.
* **Work updates:** He can't share AI-made pages with his manager or colleagues. Give him plain text he can
  check and summarise himself, not a hosted page.
* **Machine:** Lenovo LOQ 15AHP10, **Ubuntu 26.04.1 LTS** x64, user `cos777`. Miniconda is at `~/miniconda3`
  and the conda `(base)` env is **auto-activated** in his shell.
* **Repo:** <https://github.com/abhiramgcos/Esp_ir_board>, cloned at `~/Desktop/projects/Esp_ir_board`.
  * `main`: finished, verified **v2.0** board.
  * `v2.1-optimize`: unfinished **v2.1** (this handoff).
* **Bootstrap:** `~/Desktop/projects/get_esp_ir_board.sh` did the clone and install. He started it at about
  11:08 IST on 2026-11-20 and it was waiting on sudo. **Check it finished** (`kicad-cli version`, `ls .venv`).
  If the KiCad PPA step failed on 26.04, the fix is already on the branch: the installer now uses the distro
  KiCad on Ubuntu 25.04+.

## 2. What he asked for (in order) and status

| # | Request | Status |
|---|---|---|
| 1 | Verify his v1 board (Gerber zip only, no KiCad sources) | ✅ `docs/v1-review.md`: copper clean, 10 design/fab issues |
| 2 | Rebuild from scratch in the repo, fix every issue, "more advanced and optimised"; hybrid hand-solder priority; label everything + a doodle; size free | ✅ v2.0 on `main` |
| 3 | Push with README, diagrams/screenshots, build history per step | ✅ `README.md`, `docs/BUILD_LOG.md` (steps 1–5), one commit per step |
| 4 | Clone to `~/Desktop/projects/<repo>`, install tools, Python env / conda, viewer scripts; "use multiple agents" | ✅ `setup/`, `scripts/esp.sh`, `Makefile`, bootstrap script |
| 5 | **"modify the board to be more optimized, include 3D view and photos in README, commit and push"** | 🟡 **IN PROGRESS** on `v2.1-optimize` |
| 6 | "switch from cloud to this computer" | ➡️ this handoff |

"Photos" = rendered 3D images (there is no real hardware yet). Say so in the README.

## 3. The design (v2.0 = baseline)

* **Single source of truth:** `gen/circuit.py`. It lists every component, its footprint, its pin→net map,
  MPN/LCSC and schematic position. The schematic is generated from it; don't hand-edit the `.kicad_sch`
  unless you also update `circuit.py`.
* **Blocks:**
  * **Power:** USB-C (HRO TYPE-C-31-M-12) → USBLC6-2SC6 ESD → 0.75 A PTC → SS14. EXT 5V header → SS14.
    The two diodes are OR'd into **VIN ≈4.5 V** → **AP2112K-3.3** → 3V3.
  * **Programming:** CH340C at 3.3 V (V3 tied to VCC). D+/D− go through ESD to the CH340. DTR/RTS drive
    2× MMBT3904 auto-reset (EN, IO0). 1 k from CH340 TXD → ESP RX so an external UART on J3 can override it.
  * **MCU:** ESP32-WROOM-32E (KiCad footprint `ESP32-WROOM-32D`, pin-compatible). The antenna **overhangs**
    the top board edge by ≈5.5 mm.
  * **IR TX:** IO4 → 100 Ω → AO3400A low-side switch, gate 100 k pulldown. **2× TSAL6200 in series** from VIN
    via **18 Ω 1206** ≈ 100 mA.
  * **IR RX:** TSOP38238 (`OptoDevice:Vishay_MOLD-3Pin`) → **IO16**; supply 100 Ω + 10 µF.
  * **User I/O:**
    * Green PWR LED on 3V3, blue LED on IO2 (1 k each).
    * Buttons: RESET (EN), BOOT (IO0), USER (IO13, 10 k pull-up), all 6×6 THT.
    * I²C IO21/IO22 with 4.7 k pull-ups.
  * **Headers:** J3 UART 1×6 (GND TX RX EN IO0 3V3). J4 expansion 1×14 (VIN 3V3 GND SDA SCL 18 19 23 25 26 32 33 34 35).
* **Hand-solder priority:** all SMD footprints use the `_HandSolder` variants (0805/1206, SOIC-16, SOT-23, SMA).
  Through-hole parts are LEDs, TSOP, buttons and headers. JLC BOM/CPL cover SMD only.

## 4. Pipeline (all in `gen/`, run with `.venv/bin/python`)

| Step | Script | Notes |
|---|---|---|
| Schematic | `sch.py out.kicad_sch` | kiutils; a net label on every pin; NC flags; PWR_FLAGs. **Every run makes NEW symbol UUIDs**, so always build the PCB from the same run's schematic. |
| Netlist ERC | `erc.py netlist.net` | Compares the kicad-cli netlist with `circuit.py`. Expect `162 pin assignments checked, 41 nets, 0 problems`. |
| PCB | `pcb.py sch out.kicad_pcb` | Places footprints from `placement.py`, nets, outline, 0.3 mm thermal vias; writes rules/netclasses into `.kicad_pro`. |
| Keepouts | `zones.py keepout pcb` | No F.Cu tracks under the ESP32 body; nothing under the antenna strip (both layers). |
| Route | `router.py in out` | Own 2-layer maze router (scikit-image MCP on a 0.05 mm grid, 3 planes F/via/B). Rip-up + order jitter (`ROUTER_ROUNDS`, default 40). 45° segments. Power first. |
| Pour | `zones.py pour pcb` | Antenna pour keepout, GND pours both layers, stitching vias (isolated ones auto-removed). |
| Silk | `silk.py pcb` | Pin labels, auto-placed refs, back-side title + GPIO map + passives table + robot doodle. |
| DRC | `drc.py pcb report [fill]` | pcbnew `WriteDRCReport`. Ignore `lib_footprint_issues` (no global fp-lib-table). |
| BOM/CPL | `bom.py pos.csv outdir` | `BOM_full.csv`, `BOM_JLCPCB.csv`, `CPL_JLCPCB.csv`. |
| All | `build.sh [outdir]` | Chains the steps; never writes into `hardware/`. |

Other tools:
* `tools/gerber_connectivity.py fab/gerbers --circuit gen`: independent check (renders Gerbers, joins
  through plated holes, compares with `circuit.py`). Expect `nets: 41 shorts: 0 opens: 0` and
  `162 ... mismatches: 0`.
* `tools/render3d.py pcb outdir [--mask black|green|blue] [--models DIR]`: offscreen pyrender. Uses the real
  KiCad `.wrl` models, falling back to boxes. Writes `3d_top_iso.png`, `3d_bottom_iso.png`, `3d_top.png`.
* `scripts/esp.sh` and the `Makefile`: `make help | open | sch | pcb | 3d | render3d | gerbers | render | check | bom | fab | rebuild | clean`.

### ⚠️ KiCad version gotchas (generators were written and tested on **KiCad 7.0.11**; this laptop has 9+)
* **Footprint fields:** `pcb.py` uses `fp.SetProperty(k, v)` for MPN/LCSC. That was removed in KiCad 8.
  Replace it with the field API (e.g. `f = pcbnew.PCB_FIELD(fp, fp.GetFieldCount(), k); f.SetText(v); f.SetVisible(False); fp.AddField(f)`).
  Check against `dir(pcbnew)` on this machine.
* **Likely changed names in 8/9:**
  * `pcbnew.EDA_UNITS_MILLIMETRES` (used in `drc.py`, `zones.py`): check, it may be `EDA_UNITS_MM`.
  * `FP_EXCLUDE_FROM_BOM` / `FP_EXCLUDE_FROM_POS_FILES`.
  * `ZONE_CONNECTION_THT_THERMAL`.
  * `SHAPE_T_*`, `SetArcAngleAndEnd`, `EDA_ANGLE`.
  * `pad.TransformShapeToPolygon` signature.
  * `ref.SetKeepUpright`.
* **Approach:** run each step and fix API errors as they appear. **Keep it working on KiCad 7 too** if cheap
  (`hasattr` checks).
* **kiutils** writes KiCad-7-format schematics. KiCad 9 opens them fine and upgrades them on save.
* **On KiCad 9 you get real tools**, so prefer them for verification:
  * `kicad-cli sch erc --severity-error --exit-code-violations`
  * `kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations`
  * `kicad-cli pcb render` for official 3D images.
  * Make sure ERC passes there. PWR_FLAGs exist on GND/VIN/VBUS/IR_VS; CH340 V3 was changed to power_in in
    the embedded symbol.
* **Freerouting:** the cloud sandbox couldn't run it. Here you can, if Abhiram agrees. KiCad 9: export
  Specctra DSN → Freerouting jar → import SES (in the GUI, or `pcbnew.ImportSpecctraSES`). Only switch if the
  custom router can't reach DRC = 0.

## 5. v2.1: current state and exact remaining work

**Branch `v2.1-optimize` contains:**
* **`gen/placement.py`:** compact **68 × 48 mm** layout (v2.0 was 76 × 56), holes at (103.2, 103.2),
  (164.8, 103.2), (103.2, 144.8), (164.8, 144.8). A placement-only DRC was clean (no courtyard overlaps).
* **`gen/router.py`:**
  * octilinear pulling
  * power-first order
  * `VIA_COST=60`
  * rip-up with jitter
  * tight-margin "fine_zone" within 1 mm of J1 SMD pads (width 0.15 for USB_DP/DN/CC1/CC2, 0.3 for VBUS)
* **`gen/zones.py`:**
  * reads `BOARD`/`HOLES` from `placement.py`
  * antenna track+via+pour keepout `x 127–149, y 99–101.6` on both layers
* **`gen/sch.py`:** revision 2.1.
* **`wip/v2.1/`:** the last fully routed v2.1 board, made **before** the fine_zone change.
  * All nets routed. Track length 1634 mm (v2.0: 1733). 79 stitching vias (v2.0: about 110).
  * **DRC: 7 clearance errors, 0.177–0.189 mm.**
    * VBUS track near J1 A1/B12 GND (around 107–109, 119)
    * USB_DN near U4 pin 14 (around 116.6, 129.4)
  * The fine_zone change is the intended fix. It has **not** been tested.
  * Routing takes ≈5 min (about 30 s per rip-up round).
* **`tools/render3d.py` + `make render3d`:** done, working. v2.0 samples are in `docs/img/v2.0_3d_*.png`.

**Remaining:**
1. Port the generators to KiCad 9 APIs (see the gotchas above).
2. Build v2.1: `cd gen && ./build.sh ../build`, or step by step. Get **DRC = 0 errors**, with
   `kicad-cli pcb drc` *and* `gen/drc.py`, plus `make check`-style Gerber connectivity = 0 shorts/0 opens/0
   mismatches.
   * If errors remain, re-run the router, raise the margin, or nudge placement (e.g. move U3/R1/R2 or U4 by
     0.5–1 mm).
3. **`gen/silk.py` is still hard-coded for 76 × 56:**
   * The score bounds `100.4/175.6/155.6`.
   * The positions of the "USB-C", "PWR", "IO2", "IR TX x2", "IR RX", "38 kHz" and "ESP32 IR v2.x"/github
     labels.
   * The back-side title (≈134, 104.2).
   * GPIO map (≈104, 129.5).
   * The passives table, which must fit between the SW pads (y ≤ 128.5) and J3/J4 (pads at y = 145). Use
     1.05 mm line spacing.
   * The robot doodle (≈157, 135.5).

   Derive positions from `BOARD` and footprint positions, change the title to **v2.1**, render with
   `kicad-cli pcb export svg` (+ `--mirror` for the back), and **look at the PNGs**. Iterate until there's no
   silk on pads and no overlaps.
4. Copy the final `.kicad_sch/.kicad_pcb/.kicad_pro/.kicad_dru` into `hardware/` (same run, so the UUIDs
   match). Then:
   * `make fab`: Gerbers/drill/BOM/CPL/zip.
   * Regenerate the schematic PDF + `hardware/docs/assembly_top.pdf`.
   * `make render`.
   * `make render3d`, plus `kicad-cli pcb render` (KiCad 9) for official top/bottom/iso images.
   * `tools/gerber_connectivity.py fab/gerbers --circuit gen`.
5. **README:**
   * A "3D views" section near the top with the renders (top iso, bottom iso, top), clearly labelled as
     **renders**.
   * Update the board size to 68 × 48 and the images.
   * A v2.0 → v2.1 table: area −23 %, track length, via count, 45° routing, antenna keepout.
   * Update the verification numbers.
6. **`docs/BUILD_LOG.md`:** add **Step 6: v2.1 optimisation + 3D renders**, with before/after images and
   numbers. Keep the v2.0 images under `docs/img/v2_*` for history; add `v2.1_*`.
7. Delete `wip/` and this file's "remaining" list (or move it into BUILD_LOG). Commit in logical steps, push,
   then merge `v2.1-optimize` → `main` **only after Abhiram says OK** (or open a PR with `gh pr create`).

## 6. Conventions

* **Commits:** one per logical step, descriptive message, push after each. Keep `main` always passing checks.
* **Per step:** screenshot(s) into `docs/img/` and an entry in `docs/BUILD_LOG.md`. He reads the history later.
* **Checks:**
  * Never claim "clean" without running the checks.
  * Report real numbers.
  * Look at every rendered image before committing it.
* **Untouched:** `v1/` (original v1 fab files) and `docs/v1-review.md` stay as they are.
* **3D models:** Ubuntu package `kicad-packages3d` (~424 MB download, ~5.7 GB installed). Or extract only the
  needed `.wrl` files from it and pass `--models` / `MODELS3D=`. Ask before installing 5 GB.
  `render3d.py` falls back to boxes; only J1 (USB-C HRO) has no stock model.
* **Offscreen rendering:** Ubuntu 26.04's Mesa may have no OSMesa. Use EGL (`PYOPENGL_PLATFORM=egl`); his
  NVIDIA/AMD GPU should work.
* **Conda:** don't build `.venv` from conda's python. `pcbnew` only imports from `/usr/bin/python3`; the
  installer already handles this.

## 7. Known caveats to keep telling him

* **Routing:** functional but auto-generated. A manual tidy in KiCad is welcome.
* **LCSC numbers:** filled only for common parts. Add part numbers for the ESP32, TSOP, TSAL6200, PTC and LEDs
  before JLC assembly, and check CPL rotations in JLC's preview.
* **Enclosure:** the ESP32 antenna overhangs the edge on purpose; the enclosure needs room for it.
