# Components: what each part does, what to buy, and safe alternatives

**Board:** ESP32 IR Blaster/Receiver v2.1, 68 × 48 mm, 2 layers, 51 parts.

The machine-readable BOM is in `fab/BOM_full.csv`; the JLCPCB-format BOM and pick-and-place files are in
`fab/`. Values come from [`gen/circuit.py`](../gen/circuit.py), the single source of truth for the design.

**Hand-solder friendly.** All passives are 0805 or 1206 with the long `_HandSolder` pads. The ICs are SOT-23,
SOT-23-5/6, SOIC-16 and the ESP32 module (castellated pads). Everything else is through-hole.

> "Alternative" here means **drop-in**: same footprint and pinout, so no PCB change. Anything that needs a
> different footprint is marked ⚠️.

## 1. Bill of materials

| Ref | Qty | Part | Package | Job on this board | LCSC # |
|---|---|---|---|---|---|
| U1 | 1 | **ESP32-WROOM-32E-N4** | module | Wi-Fi MCU, 4 MB flash | add before ordering |
| U4 | 1 | **CH340C** | SOIC-16 | USB ↔ serial for flashing; internal clock (no crystal) | C84681 |
| U2 | 1 | **AP2112K-3.3TRG1** | SOT-23-5 | 3.3 V LDO, 600 mA | C51118 |
| U3 | 1 | **USBLC6-2SC6** | SOT-23-6 | ESD protection on USB D+/D− | C7519 |
| U5 | 1 | **Vishay TSOP38238** | 3-pin THT | IR receiver, 38 kHz demodulator → IO16 | add before ordering |
| Q1, Q2 | 2 | **MMBT3904** | SOT-23 | DTR/RTS auto-reset into the bootloader | C20526 |
| Q3 | 1 | **AO3400A** | SOT-23 | N-MOSFET low-side switch for the IR LEDs | C20917 |
| D1, D2 | 2 | **SS14** | SMA | Schottky "OR" of USB 5 V and EXT 5 V (no back-feeding) | C2480 |
| D3, D4 | 2 | **Vishay TSAL6200** | 5 mm THT | 940 nm IR LEDs in series, ~100 mA pulses | add before ordering |
| D5 | 1 | LED green | 0805 | power indicator | any |
| D6 | 1 | LED blue | 0805 | user LED on IO2 | any |
| F1 | 1 | PTC fuse, 0.75 A hold, ≥6 V | 1206 | USB over-current protection | add before ordering |
| J1 | 1 | **HRO TYPE-C-31-M-12** | USB-C 16P SMD | power + programming | C165948 |
| J2 | 1 | pin header 1×2, 2.54 mm | THT | external 5 V input | – |
| J3 | 1 | pin header 1×6, 2.54 mm | THT | UART: GND TX RX EN IO0 3V3 | – |
| J4 | 1 | pin header 1×14, 2.54 mm | THT | expansion: VIN 3V3 GND SDA SCL 18 19 23 25 26 32 33 34 35 | – |
| SW1–SW3 | 3 | tactile switch 6×6 mm, H 5 mm | THT | RESET (EN), BOOT (IO0), USER (IO13) | – |
| R10 | 1 | 18 Ω 1 % | **1206** | IR LED current: (4.5 V − 2×1.35 V) / 18 Ω ≈ 100 mA | – |
| R1, R2 | 2 | 5.1 kΩ | 0805 | USB-C CC pull-downs (asks the charger for 5 V) | C27834 |
| R3, R4, R6, R7, R14 | 5 | 10 kΩ | 0805 | EN/IO0/button pull-ups, transistor base resistors | – |
| R5, R12, R13 | 3 | 1 kΩ | 0805 | CH340 TX series, LED resistors | – |
| R8, R11 | 2 | 100 Ω | 0805 | MOSFET gate resistor, TSOP supply filter | – |
| R9 | 1 | 100 kΩ | 0805 | MOSFET gate pull-down (LEDs off during boot) | – |
| R15, R16 | 2 | 4.7 kΩ | 0805 | I²C pull-ups | – |
| C1, C5, C10 | 3 | 22 µF 16 V X5R | **1206** | bulk: VIN, 3V3 at the ESP32, IR LED reservoir | – |
| C3, C11 | 2 | 10 µF 10 V+ X5R | 0805 | LDO output, TSOP supply filter | – |
| C2, C7 | 2 | 1 µF 16 V | 0805 | LDO input, EN reset delay | – |
| C6, C8 | 2 | 100 nF | 0805 | decoupling (ESP32, CH340) | – |
| H1–H4 | 4 | M2 mounting holes | – | – | – |

An "–" in the LCSC column means a generic part: JLCPCB's "basic" resistors and capacitors match by value
and package.

**Extra parts to buy:**
* 2.54 mm female headers if you want plug-in modules on J4.
* 4× M2 screws and standoffs.
* A USB-C cable *with data lines*. Some charge-only cables don't work for flashing.

## 2. Alternatives, part by part

### ESP32 module (U1)

| Option | Notes |
|---|---|
| ESP32-WROOM-32E-N4 | ✅ Default. 4 MB flash, PCB antenna, rev 3 silicon. |
| ESP32-WROOM-32E-N8 / -N16 | ✅ Drop-in, more flash. |
| ESP32-WROOM-32D / ESP32-WROOM-32 | ✅ Drop-in (older silicon; works with this firmware). |
| ESP32-WROOM-32UE | ✅ Drop-in, but U.FL connector for an external antenna. Good inside a metal box. |
| ESP32-C3 / S3 / C6 modules | ⚠️ Different pinout and footprint. Not compatible. |

### USB-serial (U4)

| Option | Notes |
|---|---|
| CH340C | ✅ Default. Built-in oscillator. |
| CH340G | ⚠️ Same SOIC-16 but **needs a 12 MHz crystal** on pins 7/8. Will not work as-is. |
| CH340K, CP2102N, FT231X | ⚠️ Different packages and pinouts. |

Linux and macOS have CH340 drivers built in. On Windows 10/11 the driver installs automatically or from
wch-ic.com.

### 3.3 V regulator (U2)

All of these use the same SOT-23-5 pinout as AP2112K: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT.

| Option | Notes |
|---|---|
| AP2112K-3.3 (600 mA) | ✅ Default. |
| ME6211C33M5G (500 mA) | ✅ Cheap and common at LCSC. |
| XC6220B331MR (700 mA) | ✅ |
| RT9013-33**GB** (500 mA) | ✅ The **GB** suffix has pin 4 NC. The PB version has a bypass pin, which is also OK. |
| AMS1117-3.3 | ⚠️ SOT-223 package and about 1.1 V dropout. Not suitable here (VIN is only ~4.5 V). |

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
| TSAL6200 (940 nm, ±17°, 100 mA) | ✅ Default. Good range and spread. |
| TSAL6100 (±10°) | ✅ Longer range, narrower beam. |
| TSAL6400 (±25°) | ✅ Wider beam, slightly less range. |
| Any 5 mm **940 nm** IR LED rated ≥100 mA, Vf ≈1.2–1.5 V | ✅ e.g. generic "IR333" types. |
| 850 nm LEDs | ⚠️ Many TV/AC receivers are far less sensitive at 850 nm. Avoid. |

**Polarity:** the longer leg is the anode (+). The flat side of the rim is the cathode, which matches the
square pad on the PCB.

### IR receiver (U5)

| Option | Notes |
|---|---|
| TSOP38238 | ✅ Default. Pinout 1 OUT, 2 GND, 3 VS, matching the footprint. |
| TSOP4838 | ✅ Same pinout, older series. |
| TSOP38438 | ✅ Same pinout, AGC4: better for A/C remotes with long frames. |
| VS1838B / HX1838 | ✅ Same OUT-GND-VCC order and very cheap; shorter range and more noise. |
| TSOP38236 / 38240 / 38256 | ✅ Use when your remotes are 36, 40 or 56 kHz. |
| TSOP1838, KY-022 modules, some no-name parts | ⚠️ Check the datasheet pin order; several have VS and GND swapped. |

### Transistors

| Part | Options |
|---|---|
| Q1, Q2 (NPN) | ✅ MMBT3904 (default), MMBT2222A, S8050 (J3Y), BC847. All SOT-23 with 1 B, 2 E, 3 C. |
| Q3 (N-MOSFET, logic level at 3.3 V gate) | ✅ AO3400A (default), AO3402, SI2302CDS, IRLML6344, IRLML2502. All SOT-23 with 1 G, 2 S, 3 D. |

⚠️ For Q3, avoid 2N7002: its R<sub>DS(on)</sub> at 3.3 V is too high for 100 mA pulses.

### Diodes and fuse

| Part | Options |
|---|---|
| D1, D2 | ✅ SS14 (default), SS16, SS24, SS34, B140, MBRA140. All SMA Schottky, ≥1 A. ⚠️ Not SOD-123 (e.g. 1N5819W). |
| F1 | ✅ Any 1206 PTC with 0.5–1.1 A hold and ≥6 V, e.g. Bourns MF-NSMF075, Littelfuse 1206L075. In a pinch, a 0 Ω 1206 jumper works (no over-current protection). |

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
