# Build log

One entry per build step, newest at the bottom. Each step is its own git commit, so you can check out any stage.

## Step 1: Archive v1 and review it

* The v1 fab outputs are kept in `v1/fab/` for reference.
* The review is in [v1-review.md](v1-review.md). The copper connectivity is clean, but there are ten design and fab issues.
* The Gerber analysis scripts are in `tools/`.

## Step 2: v2 schematic

The whole circuit is described in one Python file, `gen/circuit.py`. Running `gen/sch.py` turns it into
`hardware/esp_ir_board.kicad_sch`, which you can open in KiCad 7 or newer.

```mermaid
flowchart LR
  USB[USB-C J1] -->|D+/D-| ESD[USBLC6 ESD U3] --> CH[CH340C U4]
  USB -->|VBUS| F[PTC fuse F1] --> D1[SS14 D1]
  EXT[EXT 5V J2] --> D2[SS14 D2]
  D1 --> VIN((VIN ~4.5V))
  D2 --> VIN
  VIN --> LDO[AP2112K-3.3 U2] --> V33((3V3))
  V33 --> ESP[ESP32-WROOM-32E U1]
  CH -->|TX/RX| ESP
  CH -->|DTR/RTS| AR[Auto-reset Q1/Q2] -->|EN, IO0| ESP
  ESP -->|IO4| DRV[AO3400A Q3] --> IRLED[2x TSAL6200 D3/D4]
  VIN --> IRLED
  RX[TSOP38238 U5] -->|IO27| ESP
  ESP --> UI[LEDs, RESET/BOOT/USER buttons]
  ESP --> HDR[UART J3 + 14-pin expansion J4]
```

![v2 schematic](img/v2_schematic.png)

**Checks.** KiCad 7's command line has no ERC command, so `gen/erc.py` compares the exported netlist with
`circuit.py` instead.

* Result: 162 pin assignments checked, 41 nets, 0 problems (no mismatches, no single-pin nets).
* Unused pins carry no-connect flags. Passive-driven power nets have PWR_FLAGs.

**Key design decisions**

| Block | Choice | Reason |
|---|---|---|
| 3.3 V | AP2112K-3.3, 600 mA, ~250 mV dropout | Stays in regulation from a 4.3 V VIN (v1's LD1117 did not) |
| Programming | CH340C (no crystal) at 3.3 V + 2× MMBT3904 auto-reset | One-click flashing over USB-C |
| UART override | 1 k between CH340 TXD and ESP RX | An external adapter on J3 still works |
| IR TX | 2× TSAL6200 in series, 18 Ω from VIN, AO3400A low-side | ≈100 mA at 38 kHz for room-wide range |
| IR RX | TSOP38238 + 100 Ω/10 µF supply filter | Vishay-recommended supply filter |
| User I/O | Blue LED on IO2, USER button on IO13, I²C pull-ups 4.7 k | Ready for firmware and sensors |
| Protection | USBLC6-2SC6 ESD, 0.75 A PTC, Schottky diode-OR | Plugging in USB and external 5 V together is safe |

**GPIO map**

| Function | GPIO | | Function | GPIO |
|---|---|---|---|---|
| IR TX | IO4 | | I²C SDA / SCL | IO21 / IO22 |
| IR RX | IO27 | | Expansion | IO18, 19, 23, 25, 26, 32, 33, 34*, 35* |
| User LED | IO2 | | UART0 | IO1 (TX), IO3 (RX) |
| User button | IO13 | | Boot / reset | IO0 / EN |

\* IO34 and IO35 are input-only.

## Step 3: PCB placement, routing and ground pours

**Board:** 76 × 56 mm, 2 layers, 1.6 mm thick, four M2 holes at the corners.

**Placement** (`gen/placement.py`). The parts are grouped by function:

* ESP32 at the top centre, with the antenna hanging ≈5.5 mm past the board edge.
* Power and USB on the left.
* IR transmit and receive on the right edge, facing out.
* Buttons in a row under the module.
* Headers along the bottom edge.

![placement](img/v2_placement.png)

**Routing** (`gen/router.py`). Freerouting couldn't be run in the build sandbox, so the board uses a
purpose-written 2-layer maze router:

* Each net is a cost grid at 0.05 mm with three planes: F.Cu, vias and B.Cu.
* scikit-image's minimum-cost-path solver connects each pad to the net's tree, nearest pad first.
* Failed nets are ripped up and retried first on the next pass.
* Paths are then straightened by string-pulling, and stubs are cleaned up.

Track widths:

| Nets | Width |
|---|---|
| VIN, +3V3, GND, IR LED | 0.5 mm |
| VBUS | 0.3 mm |
| Signals | 0.25 mm |
| USB D+/D− and CC (0.5 mm-pitch USB-C pins) | 0.15 mm |

Other routing rules:

* No top-layer tracks under the ESP32 body.
* No copper under the 1 mm of antenna that sits over the board.

**Pours.** There is a GND pour on both layers, with ≈110 stitching vias. Any via that lands on an isolated
island is removed automatically.

| Top (F.Cu + silk) | Bottom (B.Cu) |
|---|---|
| ![top](img/v2_routed_top.png) | ![bottom](img/v2_routed_bottom.png) |

**DRC** (KiCad 7 `pcbnew` engine, `gen/drc.py`)

* 0 clearance errors, 0 hole-clearance errors, 0 unconnected items, 0 dangling tracks or vias.
* What remains is silkscreen cosmetics (cleaned up in step 4). There is also a "library not in configuration"
  notice, which only means the build machine had no global footprint library table.
* `hardware/esp_ir_board.kicad_dru` allows one thermal spoke on GND pins hemmed in by tracks.

**Note:** the routing is automatic and functional, but not hand-polished. Open it in KiCad and tidy
traces if you want a neater look. The DRC rules travel with the project.
