# Ordering the PCB: JLCPCB and PCBWay, step by step

Everything a fab needs is in [`fab/`](../fab), produced by `make fab` and verified by `make check`.

| File | What it is | Used for |
|---|---|---|
| `fab/esp_ir_board_v2_gerbers.zip` | copper, mask, silk, paste, outline, drill (Excellon) | **bare PCB order** (any fab) |
| `fab/BOM_JLCPCB.csv` | Comment, Designator, Footprint, LCSC Part # | JLCPCB assembly |
| `fab/CPL_JLCPCB.csv` | Designator, Mid X, Mid Y, Layer, Rotation | JLCPCB assembly (pick-and-place) |
| `fab/BOM_full.csv` | every part with MPN and description | PCBWay assembly / buying parts yourself |
| `hardware/docs/esp_ir_board_schematic.pdf`, `assembly_top.pdf` | schematic + top assembly drawing | reference for assembly |

**Board facts** (fabs ask for these):

The board is designed for **black solder mask with white silkscreen**, as in the renders. Black looks best,
but it makes traces harder to follow when you're debugging. Green is fine if you prefer that.


| Property | Value |
|---|---|
| Size | 68 × 48 mm |
| Layers | 2 |
| Thickness | 1.6 mm FR-4 |
| Copper | 1 oz |
| Min track / clearance | 0.15 / 0.2 mm (6 / 8 mil) |
| Min hole | 0.3 mm |
| Min via | 0.6 / 0.3 mm |
| Castellated holes / impedance control / blind vias | no |

These all fit the cheapest standard process at both fabs.

> Re-generate the files after any change: `source .venv/bin/activate && make fab && make check`.
> Upload the zip **as is**. Don't unzip it or rename the files inside.

## A. JLCPCB

### A1. Bare boards (you solder everything)

1. Go to <https://jlcpcb.com>, sign in, and click **Order now** → **Add gerber file**. Upload
   `fab/esp_ir_board_v2_gerbers.zip`.
2. Wait for the auto-detection and the preview. It should say *"Detected 2 layer board of 48×68mm"*.
   * **The Dimensions boxes should read 68 × 48 (or 48 × 68).** If PCB Assembly is switched on with
     **Standard** PCBA, JLC changes them to **78 × 70**: Standard assembly needs every side ≥ 70 mm, so JLC
     adds edge rails. That's expected and harmless; you snap the rails off afterwards. With assembly off, or
     with Economic PCBA, it stays 68 × 48.
   * Click **Gerber Viewer** and check both sides look like the images in the README.
   * The ESP32 antenna area at the top edge is empty copper on purpose.
3. Settings: leave the defaults except where noted.

   | Setting | Choice |
   |---|---|
   | Base material | FR-4 |
   | Layers | 2 |
   | Quantity | 5 (minimum) |
   | Product type | Industrial/Consumer electronics |
   | Different design | 1 |
   | Delivery format | Single PCB |
   | PCB thickness | 1.6 mm |
   | PCB color | **Black** (the design is drawn for black mask + white silk); green is the cheapest and fastest |
   | Silkscreen | white |
   | Surface finish | **LeadFree HASL** or **ENIG** (gold, flattest, best for the 0.5 mm USB-C pins) for hand-soldering. HASL (with lead) is cheapest. **OSP** (JLC's new default) is fine if JLC assembles the board, but it's the worst choice for hand-soldering or storing bare boards, because the coating degrades within months and after heating |
   | Outer copper weight | 1 oz |
   | Via covering | Tented |
   | Mark on PCB | **Remove Mark** (no order number printed on the board) |

4. **Save to cart** → **Checkout**. Pick shipping, then pay. Production usually takes 1–2 days; shipping is
   extra.

### A2. Assembled boards (JLCPCB solders the SMD parts)

1. Do steps A1.1–A1.3, then switch on **PCB Assembly** at the bottom of the page.
2. Assembly settings:
   * **PCBA type:** Economic is the cheapest. If it's greyed out, change one of your PCB options and check
     whether it becomes available; JLC restricts Economic to certain options, for example colour and surface
     finish. Standard works, but it adds 5 mm edge rails (board becomes 78 × 70 mm, rails are snapped off
     afterwards), a $1.50 feeder fee per unique part, and a larger setup cost.
   * **Assembly side:** Top side.
   * **Tooling holes:** Added by JLCPCB.
   * **Confirm parts placement:** Yes. They send you a placement preview to approve.
3. **NEXT** → upload the **BOM** `fab/BOM_JLCPCB.csv` and the **CPL** `fab/CPL_JLCPCB.csv` → **Process BOM & CPL**.
4. Bill of Materials page:
   * **Every line has an LCSC number**, checked in stock on 2026-11-20, so the BOM matches automatically. If
     a part has gone out of stock, click **Search** on that line and pick a substitute from
     [COMPONENTS.md](COMPONENTS.md).
   * Prefer **Basic** parts. Each **Extended** part (the ESP32, CH340C and USB-C usually are) adds a one-time
     loading fee of about $3.
   * Through-hole parts are **not** in the CPL: the buttons, headers, TSOP and IR LEDs. Solder them yourself;
     it takes about 10 minutes. The IR LEDs must be bent 90° to lie flat, which machine assembly doesn't do,
     so they're best done by hand. See [COMPONENTS.md §3](COMPONENTS.md#3-what-to-buy-for-hand-assembly).
     Order the TSOP38238 and TSAL6200 alongside the boards (LCSC C141632 and C55528), or locally.
   * See [COMPONENTS.md](COMPONENTS.md) for allowed substitutes if a part is out of stock.
5. **NEXT** → Component Placements preview. **Check every part's rotation and pin 1.** Rotation offsets
   differ between libraries and JLC's database. Common ones to fix with the rotate button:
   * **U4** CH340C: pin-1 dot.
   * **U2** AP2112K: the 3-pin side goes toward VIN/GND/EN.
   * **U3**, **Q1–Q3**: SOT-23 single pin.
   * **D1/D2**: cathode bar toward the "VIN" side.
   * **D5/D6**: LED cathode.
   * **J1**: USB-C opening must face the board edge.
6. **NEXT** → quote → **Save to cart** → pay. You still need to solder the through-hole parts and flash the
   firmware ([firmware/README.md](../firmware/README.md)).

Optional: order a **stencil** in the same cart ("SMT-Stencil", framework off, 100 × 100 mm is enough) if
you'll reflow with paste at home.

## B. PCBWay

### B1. Bare boards

1. Go to <https://www.pcbway.com> → **PCB Instant Quote** → **Quick-order PCB**. Upload
   `fab/esp_ir_board_v2_gerbers.zip`.
2. PCBWay auto-fills the size from the Gerbers. If it doesn't, enter:

   | Setting | Value |
   |---|---|
   | Size | **68 × 48 mm** |
   | Quantity | 5 |
   | Layers | 2 |
   | Material | FR-4, TG130 |
   | Thickness | 1.6 mm |
   | Min track/spacing | 6/6 mil |
   | Min hole size | 0.3 mm |
   | Solder mask | **Black** |
   | Silkscreen | white |
   | Edge connector | No |
   | Surface finish | HASL lead-free or Immersion gold (ENIG) |
   | Via process | Tenting vias |
   | Finished copper | 1 oz |

3. **Calculate** → **Add to cart**. PCBWay's engineers review the files, usually within 1–2 h; you'll get an
   email if they have a question. Then pay.

### B2. Assembled boards at PCBWay

1. In the quote form, open **PCB Assembly** (or "Turnkey assembly"):
   * Type: **Turnkey** (they buy the parts).
   * Assembly side: top.
   * Unique parts: about 30.
   * SMD pads: about 160.
   * THT parts: 13, or 0 if you'll solder the through-hole parts yourself.
2. Upload:
   * **BOM**: `fab/BOM_full.csv`. PCBWay works from manufacturer part numbers (the MPN column), not LCSC
     numbers.
   * **Centroid**: `fab/CPL_JLCPCB.csv`. The columns are the same; rename it `centroid.csv` if you like.
   * The Gerber zip.
   * Optionally `hardware/docs/assembly_top.pdf`.
3. Write in the comments:
   > "Generic passives OK. Polarity per assembly_top.pdf. ESP32-WROOM-32E-N4 or -N8 OK. Please send photos
   > before shipping."
4. PCBWay sends a parts quote (1–2 days) and a confirmation of any substitutions. Check them against
   [COMPONENTS.md](COMPONENTS.md).

## C. Before you press "pay": checklist

- [ ] Dimensions show **68 × 48 mm** and Layers **2**.
- [ ] PCB color **Black**, silkscreen **White**.

- [ ] `make check` printed **ALL CHECKS PASSED** after the last change.
- [ ] The fab's Gerber viewer shows 68 × 48 mm, 2 layers, drills present, silk readable.
- [ ] The antenna strip at the top edge has no copper (only the ESP32 module's antenna overhangs it).
- [ ] The USB-C footprint is on the left edge, facing outward.
- [ ] For assembly: every rotation in the placement preview checked; no through-hole parts in the CPL.
- [ ] Surface finish: ENIG or lead-free HASL if you'll hand-solder the ESP32 and USB-C.

## D. After the boards arrive

1. Solder the remaining parts. [COMPONENTS.md](COMPONENTS.md) §3 gives the order and the power-up checks.
2. Flash the firmware: [firmware/README.md](../firmware/README.md).
3. Test:
   * Learn a TV remote button in the web UI.
   * Send it back.
   * Confirm the IR LEDs flash purple through a phone camera.
