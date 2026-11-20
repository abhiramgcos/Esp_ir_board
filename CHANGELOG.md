# Changelog

Hardware and firmware share one version number. Hardware revisions are printed on the PCB silkscreen.

## [2.1.4] - 2026-11-20

Silkscreen only; copper, drills, BOM and pick-and-place are unchanged from 2.1.3.

* **Pick-and-place fix (CPL re-uploaded to the release):** JLC's part models are zeroed differently from
  KiCad for some packages, so its preview showed U1 (ESP32), U2, U3, U4 turned 90° and Q1–Q3 turned 180°.
  `gen/bom.py` now applies the offsets (ESP32 module, SOIC, SOT-23-5/6: −90°; SOT-23: 180°).
* Back: the portrait is replaced by text credits: *Inspired by T.K.V* (github.com/tkv-04, tkv.in.net) and
  *Designed by abhiramgcos* (github.com/abhiramgcos, abhiramg.in). The portrait art and tracing script were
  removed from the repository.

## [2.1.3] - 2026-11-20

* Buttons (SW1–SW3) and the pull-up/LED row below them moved 2 mm down, away from the ESP32. The gap from
  the module's bottom pads to the button pads grows from 1.5 mm to 3.5 mm (bodies 2.1 → 4.1 mm), leaving
  room for a soldering iron or hot-air nozzle on the module's bottom pins.
* Fixed the ESP32 3D model position: the -32E model was rendered 2.99 mm too low on the -32D footprint
  (different footprint origins), which made the module look like it overlapped the buttons. Renders only;
  copper and manufacturing files were never affected.
* Board re-routed; BOM unchanged, pick-and-place updated. Firmware stays 2.1.1.

## [2.1.2] - 2026-11-20

Silkscreen only; copper, drills and BOM are unchanged from 2.1.1. Firmware stays 2.1.1.

* Back silkscreen: a line-art portrait tribute traced into filled silkscreen polygons
  (`gen/art/trace_portrait.py`; strokes kept ≥ 0.15 mm), with the credit underneath: *"Inspired by the one
  and only T.K.V legend — visit his official site tkv.in.net"*.
* The other back-side blocks (title, GPIO map, passives table, robot) are re-placed around it, clear of every
  through-hole pad.

## [2.1.1] - 2026-11-20

### Hardware
* **IR front:** the TSOP38238 now faces out of the right board edge instead of inward toward the USB-C side.
  The two TSAL6200 LEDs lie flat (leads bent 90°, `LED_D5.0mm_Horizontal_O1.27mm_Z3.0mm` footprint) and point
  the same way, so the receiver and transmitter share one edge.
* Board re-routed; DRC and Gerber connectivity re-verified.
* **JLCPCB assembly ready:** every SMD part now has an LCSC number, checked in stock. The ESP32 (C701341),
  PTC fuse, 22 µF and 18 Ω 1206 parts and both LEDs were added. TSOP38238 (C141632) and TSAL6200 (C55528)
  numbers were added to the full BOM.

### Firmware
* Version bumped to 2.1.1 to match the hardware; no functional change.

## [2.1.0] - 2026-11-20

Same circuit and pin map as 2.0.0. Firmware, Gerbers and accessories are interchangeable between the two.

### Hardware
* Board shrunk from 76 × 56 mm to **68 × 48 mm** (−23 % area).
* Router:
  * 45° (octilinear) routing; power nets routed first; rip-up and retry.
  * Total track 1733 → 1624 mm; vias 220 → 201.
* USB-C:
  * Dedicated fine-pitch clearance for D+/D−/CC (0.15 mm tracks).
  * VBUS exits its pad straight, which fixes 4 clearance violations at J1.
* ESP32 antenna: track, via and copper-pour keep-out on both layers, in addition to the edge overhang.
* Vias keep ≥ 0.25 mm hole-to-hole from all drilled holes.
* Silkscreen placed automatically from the outline and footprints: no silk on pads, no overlaps.
* 3D models: real ESP32-WROOM-32E model; stand-in model for the USB-C receptacle.

### Firmware (new)
* Learn, store and send IR codes: decoded protocols, A/C state frames, raw timings.
* Web UI, JSON REST API, serial console, USER-button actions.
* Wi-Fi captive-portal setup, mDNS (`irblaster.local`), OTA updates.
* Arduino IDE sketch and PlatformIO project from the same sources.

### ESPHome / Home Assistant (new)
* `esphome/esp32-ir-blaster.yaml` board package: IR TX/RX, button, LED, I²C, diagnostics, and send actions
  (NEC, Samsung, Sony, Pronto, raw).
* `example.yaml` user config with learnable buttons and an optional A/C climate entity.
* Prebuilt factory image with captive portal, Improv and Home Assistant adoption.

### Tooling
* Generators ported to KiCad 9 (still run on KiCad 7).
* `silk.py` re-runs are idempotent; `scripts/silk_preview.sh` added.
* Official renders via `kicad-cli pcb render`.

### Verification
* KiCad DRC: 0 errors, 0 unconnected.
* Gerber connectivity: 41 nets, 0 shorts, 0 opens, 162/162 pins.
* Firmware builds clean (1.08 MB flash, 50.8 kB RAM).
* Not yet built or run on physical hardware.

## [2.0.0] - 2026-11-19

Full redesign. Every issue from the [v1 review](docs/v1-review.md) is fixed:

| v1 problem | 2.0.0 |
|---|---|
| LD1117 needs ~1.2 V headroom; it browns out after the input diode | **AP2112K-3.3** (0.25 V dropout) |
| 100 nF on the regulator input only | 22 µF + 1 µF on VIN; 10 µF + 22 µF + 100 nF on 3V3 |
| IR LED ≈20 mA from 3.3 V (short range) | **2 LEDs in series from VIN at ≈100 mA**, MOSFET switched |
| IR receiver missing from the BOM | **TSOP38238 on board** |
| Needs an external USB-UART adapter | **CH340C + auto-reset**: one-click flashing |
| No protection | USB ESD diode, resettable fuse, diode-OR of USB and EXT 5V |
| Mounting holes in the BOM, one part on the bottom, 0.2 mm vias | Holes excluded, all parts on top, 0.3 mm vias |
| No part numbers, no revision | MPN + LCSC columns, revision on silkscreen |
| No I²C pull-ups | 4.7 k on SDA/SCL |

Also new: a hand-solder-friendly footprint set, a GPIO map and passives table on the back silkscreen, and
JLCPCB BOM/CPL files.

## [1.0.0]

Original board. Only fab files exist; they are kept in `v1/fab/`. The review is in
[docs/v1-review.md](docs/v1-review.md).

[2.1.4]: https://github.com/abhiramgcos/Esp_ir_board/releases/tag/v2.1.4
[2.1.3]: https://github.com/abhiramgcos/Esp_ir_board/releases/tag/v2.1.3
[2.1.2]: https://github.com/abhiramgcos/Esp_ir_board/releases/tag/v2.1.2
[2.1.1]: https://github.com/abhiramgcos/Esp_ir_board/releases/tag/v2.1.1
[2.1.0]: https://github.com/abhiramgcos/Esp_ir_board/releases/tag/v2.1.0
[2.0.0]: https://github.com/abhiramgcos/Esp_ir_board/releases/tag/v2.0.0
