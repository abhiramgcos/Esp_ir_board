# Components: what each part does, what to buy, and safe alternatives

**Board:** ESP32 IR Blaster/Receiver v2.1.2, 68 × 48 mm, 2 layers, 51 parts.

The machine-readable BOM is in `fab/BOM_full.csv`; the JLCPCB-format BOM and pick-and-place files are in
`fab/`. Values come from [`gen/circuit.py`](../gen/circuit.py), the single source of truth for the design.

**Hand-solder friendly.** All passives are 0805 or 1206 with the long `_HandSolder` pads. The ICs are SOT-23,
SOT-23-5/6, SOIC-16 and the ESP32 module (castellated pads). Everything else is through-hole.

> "Alternative" means **drop-in**: same footprint and pinout, no PCB change. Parts that look similar but
> do **not** fit are listed too, marked *no*.

## 1. Bill of materials

| Ref | Qty | Part | Package | Job on this board | LCSC # |
|---|---|---|---|---|---|
| U1 | 1 | **ESP32-WROOM-32E-N4** | module | Wi-Fi MCU, 4 MB flash | C701341 |
| U4 | 1 | **CH340C** | SOIC-16 | USB ↔ serial for flashing; internal clock (no crystal) | C84681 |
| U2 | 1 | **AP2112K-3.3TRG1** | SOT-23-5 | 3.3 V LDO, 600 mA | C51118 |
| U3 | 1 | **USBLC6-2SC6** | SOT-23-6 | ESD protection on USB D+/D− | C7519 |
| U5 | 1 | **Vishay TSOP38238** | 3-pin THT | IR receiver, 38 kHz demodulator → IO16; dome faces out of the right edge | C141632 |
| Q1, Q2 | 2 | **MMBT3904** | SOT-23 | DTR/RTS auto-reset into the bootloader | C20526 |
| Q3 | 1 | **AO3400A** | SOT-23 | N-MOSFET low-side switch for the IR LEDs | C20917 |
| D1, D2 | 2 | **SS14** | SMA | Schottky "OR" of USB 5 V and EXT 5 V (no back-feeding) | C2480 |
| D3, D4 | 2 | **Vishay TSAL6200** | 5 mm THT, **lying flat** | 940 nm IR LEDs in series, ~100 mA pulses; leads bent 90°, lenses point out of the right edge | C55528 |
| D5 | 1 | LED green (KENTO KT-0805G) | 0805 | power indicator | C2297 |
| D6 | 1 | LED blue (KENTO KT-0805B) | 0805 | user LED on IO2 | C2293 |
| F1 | 1 | PTC fuse, 0.75 A hold, 8 V (PTTC SMD1206P075TFT) | 1206 | USB over-current protection | C545214 |
| J1 | 1 | **HRO TYPE-C-31-M-12** | USB-C 16P SMD | power + programming | C165948 |
| J2 | 1 | pin header 1×2, 2.54 mm | THT | external 5 V input | – |
| J3 | 1 | pin header 1×6, 2.54 mm | THT | UART: GND TX RX EN IO0 3V3 | – |
| J4 | 1 | pin header 1×14, 2.54 mm | THT | expansion: VIN 3V3 GND SDA SCL 18 19 23 25 26 32 33 34 35 | – |
| SW1–SW3 | 3 | tactile switch 6×6 mm, H 5 mm | THT | RESET (EN), BOOT (IO0), USER (IO13) | – |
| R10 | 1 | 18 Ω 1 % (Yageo RC1206FR-0718RL) | **1206** | IR LED current: (4.5 V − 2×1.35 V) / 18 Ω ≈ 100 mA | C137378 |
| R1, R2 | 2 | 5.1 kΩ | 0805 | USB-C CC pull-downs (asks the charger for 5 V) | C27834 |
| R3, R4, R6, R7, R14 | 5 | 10 kΩ | 0805 | EN/IO0/button pull-ups, transistor base resistors | C17414 |
| R5, R12, R13 | 3 | 1 kΩ | 0805 | CH340 TX series, LED resistors | C17513 |
| R8, R11 | 2 | 100 Ω | 0805 | MOSFET gate resistor, TSOP supply filter | C17408 |
| R9 | 1 | 100 kΩ | 0805 | MOSFET gate pull-down (LEDs off during boot) | C149504 |
| R15, R16 | 2 | 4.7 kΩ | 0805 | I²C pull-ups | C17673 |
| C1, C5, C10 | 3 | 22 µF 25 V X5R (Samsung CL31A226KAHNNNE) | **1206** | bulk: VIN, 3V3 at the ESP32, IR LED reservoir | C12891 |
| C3, C11 | 2 | 10 µF 25 V X5R | 0805 | LDO output, TSOP supply filter | C15850 |
| C2, C7 | 2 | 1 µF 50 V X7R | 0805 | LDO input, EN reset delay | C28323 |
| C6, C8 | 2 | 100 nF 50 V X7R | 0805 | decoupling (ESP32, CH340) | C49678 |
| H1–H4 | 4 | M2 mounting holes | – | – | – |

Every LCSC number was checked against JLCPCB's parts library on 2026-11-20, and all were in stock. Stock and
Basic/Extended status change over time, so JLC's BOM tool has the final word. Parts with a "–" (headers,
buttons) are generic through-hole parts you solder yourself.

**Extra parts to buy:**
* 2.54 mm female headers if you want plug-in modules on J4.
* 4× M2 screws and standoffs.
* A USB-C cable *with data lines*. Some charge-only cables don't work for flashing.

## 2. Alternatives, part by part

### ESP32 module (U1)

| Option | Notes |
|---|---|
| ESP32-WROOM-32E-N4 | Default. 4 MB flash, PCB antenna, rev 3 silicon. |
| ESP32-WROOM-32E-N8 / -N16 | Drop-in, more flash. |
| ESP32-WROOM-32D / ESP32-WROOM-32 | Drop-in (older silicon; works with this firmware). |
| ESP32-WROOM-32UE | Drop-in, but U.FL connector for an external antenna. Good inside a metal box. |
| ESP32-C3 / S3 / C6 modules | *No*: different pinout and footprint. |

### USB-serial (U4)

| Option | Notes |
|---|---|
| CH340C | Default. Built-in oscillator. |
| CH340G | *No*: same SOIC-16, but **needs a 12 MHz crystal** on pins 7/8. |
| CH340K, CP2102N, FT231X | *No*: different packages and pinouts. |

Linux and macOS have CH340 drivers built in. On Windows 10/11 the driver installs automatically or from
wch-ic.com.

### 3.3 V regulator (U2)

All of these use the same SOT-23-5 pinout as AP2112K: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT.

| Option | Notes |
|---|---|
| AP2112K-3.3 (600 mA) | Default. |
| ME6211C33M5G (500 mA) | Cheap and common at LCSC. |
| XC6220B331MR (700 mA) | |
| RT9013-33**GB** (500 mA) | The **GB** suffix has pin 4 NC. The PB version has a bypass pin, which is also OK. |
| AMS1117-3.3 | *No*: SOT-223 package, ~1.1 V dropout is too much from a 4.5 V VIN. |

ESP32 Wi-Fi bursts draw about 350–500 mA, so don't use regulators under 500 mA (e.g. MCP1700, HT7333).

### USB ESD (U3)

USBLC6-2SC6 (ST) is the default, and pin-compatible copies are sold under the same name by Techpublic, UMW
and others.

The board also works without U3 if you bridge the D+/D− pads straight through:
* pin 1 → pin 6
* pin 3 → pin 4

This loses ESD protection. Not recommended for a board you'll plug in often.

### IR LEDs (D3, D4)

| Option | Notes |
|---|---|
| TSAL6200 (940 nm, ±17°, 100 mA) | Default. Good range and spread. |
| TSAL6100 (±10°) | Longer range, narrower beam. |
| TSAL6400 (±25°) | Wider beam, slightly less range. |
| Any 5 mm **940 nm** IR LED rated ≥100 mA, Vf ≈1.2–1.5 V | e.g. generic "IR333" types. |
| 850 nm LEDs | *No*: most TV/AC receivers are far less sensitive at 850 nm. |

**Polarity:** the longer leg is the anode (+). The flat side of the rim is the cathode, which matches the
square pad on the PCB.

### IR receiver (U5)

| Option | Notes |
|---|---|
| TSOP38238 | Default. Pinout 1 OUT, 2 GND, 3 VS, matching the footprint. |
| TSOP4838 | Same pinout, older series. |
| TSOP38438 | Same pinout, AGC4: better for A/C remotes with long frames. |
| VS1838B / HX1838 | Same OUT-GND-VCC order and very cheap; shorter range and more noise. |
| TSOP38236 / 38240 / 38256 | Use when your remotes are 36, 40 or 56 kHz. |
| TSOP1838, KY-022 modules, some no-name parts | *Check first*: several have VS and GND swapped. |

### Transistors

| Part | Options |
|---|---|
| Q1, Q2 (NPN) | MMBT3904 (default), MMBT2222A, S8050 (J3Y), BC847. All SOT-23 with 1 B, 2 E, 3 C. |
| Q3 (N-MOSFET, logic level at 3.3 V gate) | AO3400A (default), AO3402, SI2302CDS, IRLML6344, IRLML2502. All SOT-23 with 1 G, 2 S, 3 D. |

Avoid 2N7002 for Q3: its R<sub>DS(on)</sub> at 3.3 V gate drive is too high for 100 mA pulses.

### Diodes and fuse

| Part | Options |
|---|---|
| D1, D2 | SS14 (default), SS16, SS24, SS34, B140, MBRA140. All SMA Schottky, ≥1 A. SOD-123 parts (e.g. 1N5819W) do not fit. |
| F1 | Any 1206 PTC with 0.5–1.1 A hold and ≥6 V, e.g. Bourns MF-NSMF075, Littelfuse 1206L075. In a pinch, a 0 Ω 1206 jumper works (no over-current protection). |

### Passives, LEDs, buttons, headers

* **Resistors:** any 0805 1 % thick film. R10 should be 1206, rated at least 0.25 W.
* **Capacitors:**
  * X5R or X7R ceramic, rated ≥10 V (16 V preferred for the 22 µF). Don't use Y5V.
  * The 22 µF parts must be 1206.
  * Any capacitor can go one size up in value (e.g. 10 µF → 22 µF) without harm.
* **LEDs (D5, D6):** any 0805 colour. Change R12/R13 (1 kΩ) to adjust brightness. The cathode mark faces the
  "–"/bar on the silkscreen.
* **Buttons:** any 6×6 mm 4-pin THT tactile switch, any height (4.3 / 5 / 7 / 9.5 mm).
* **Headers:** any 2.54 mm male or female. J4 can take a 14-pin female header for plug-in sensors.

## 3. What to buy for hand assembly

The cheapest path is to order bare PCBs and buy the parts listed above. Buy 10 % extra small passives, since
they're easy to lose.

**Tools:**
* temperature-controlled iron, 0.5–1 mm tip
* 0.5 mm solder wire
* flux pen
* tweezers
* desoldering wick
* multimeter
* a hot-air station or hot plate makes the ESP32 module and USB-C connector easier, but isn't required

**Recommended order** (smallest and flattest first):
1. USB-C J1 and the ESD chip U3. Check D+/D− for bridges with a magnifier.
2. CH340C, LDO, MOSFET, transistors, diodes, fuse.
3. 0805/1206 passives and LEDs.
4. ESP32 module. Tack two opposite corners, check alignment, then do the rest. The ground pad underneath can
   be soldered through the vias from the back.
5. Through-hole last: buttons, TSOP, IR LEDs, headers.
   * **IR LEDs (D3, D4)** lie flat, lens pointing out of the right edge (footprint
     `LED_D5.0mm_Horizontal_O1.27mm_Z3.0mm`). Bend both leads 90° about 3 mm from the LED body, so the lens
     centre sits ~3 mm above the board and the body starts ~1.3 mm from the holes. The short leg (cathode,
     flat side of the rim) goes in the **square pad**. The lens tip ends at the board edge.
   * **TSOP38238 (U5)** stands upright with its dome facing out of the right edge, the same direction as the
     LEDs. OUT goes in the square pad.

**Before first power-up**, measure resistance:

| Between | Expect |
|---|---|
| VIN and GND | more than ~1 kΩ (no short) |
| 3V3 and GND | more than ~1 kΩ (no short) |

Then plug in USB-C:
* the green PWR LED lights,
* 3V3 measures 3.25–3.35 V,
* `lsusb` shows "QinHeng Electronics CH340".

Flash the firmware next: [firmware/README.md](../firmware/README.md).
