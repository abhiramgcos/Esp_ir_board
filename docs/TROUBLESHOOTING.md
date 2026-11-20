# Troubleshooting and debugging

Work top to bottom: power → USB → flashing → boot → Wi-Fi → IR. Most problems show up in the first two
steps.

**Tools that help:**
* a multimeter,
* a phone camera (it sees IR as purple light),
* the serial console at 115200 baud,
* a magnifier for the USB-C and ESP32 solder joints.

## 1. Power

Test points: C3 is 3V3, C1 is VIN. Probe them with the board unplugged first, then on USB.

| Symptom | Check | Likely cause |
|---|---|---|
| PWR LED (green) off | 3V3 across C3 | No 3V3: check VIN across C1 first |
| VIN ≈ 0 V on USB | VBUS at F1 | USB-C not soldered (A4/B9, A9/B4 pads), or a charge-only cable |
| VIN ≈ 0 V but VBUS 5 V | voltage across F1 | Fuse tripped by a short: unplug, find the short (often a solder bridge) |
| 3V3 low (< 3.2 V) or LDO hot | resistance 3V3→GND unpowered | Short or reversed part on the 3V3 rail; check C3/C5/C6 and U1 |
| Works on a PC, not on a phone charger | – | Charger doesn't see the CC pull-downs: check R1/R2 (5.1 k) on CC1/CC2 |
| Board resets when IR fires | VIN during transmit | Weak USB supply. C10 (22 µF) must be fitted; try another port or cable |

**Expected values:** VIN ≈ 4.4–4.6 V on USB (5 V minus the SS14 drop), 3V3 = 3.25–3.35 V. Idle current is
about 80 mA, with Wi-Fi peaks around 400 mA.

## 2. USB serial (CH340C)

**Linux:**

```bash
lsusb | grep -i 1a86          # expect "QinHeng Electronics CH340 serial converter"
ls /dev/ttyUSB*               # expect /dev/ttyUSB0
sudo dmesg -w                 # watch while plugging in
```

* **Port appears and immediately disappears.** `brltty` (a braille driver) is claiming the CH340:
  `sudo apt remove brltty`.
* **"Permission denied" on `/dev/ttyUSB0`.** Run `sudo usermod -aG dialout $USER`, then log out and back in.

**Windows:** Device Manager → *Ports (COM & LPT)*. If the device shows up with a yellow mark, install the
CH340 driver from WCH (wch-ic.com, "CH341SER").

**macOS:** recent versions include the driver; the port is `/dev/cu.wchusbserial*`.

**Not detected at all:**
* Use a USB-C cable that carries data.
* Check the U3 (USBLC6) and J1 D+/D− joints for bridges.
* Check C8 (100 nF) at U4, and that U4 pin 16 (VCC) and pin 4 (V3) are at 3.3 V.

## 3. Flashing

| Error | Fix |
|---|---|
| `Failed to connect to ESP32: Timed out waiting for packet header` | Auto-reset didn't enter the bootloader. Hold **BOOT**, tap **RESET**, release BOOT, retry. If manual mode works, check Q1/Q2, R6/R7 and their orientation. |
| `A fatal error occurred: ... chip stopped responding` | Lower the upload speed to 115200. Check the 3V3 rail under load. |
| Upload works, then nothing on the serial monitor | Wrong baud: use 115200. Press RESET. In the Arduino IDE, close other programs using the port. |
| `Sketch too big` (Arduino IDE) | Set *Partition Scheme* to **Minimal SPIFFS (1.9MB APP with OTA)**. |
| Compile errors in IRremoteESP8266 about timers (`timerBegin`, …) | You are on ESP32 core 3.x. Install core **2.0.17**. |
| `WiFiManager.h: No such file` | Install the WiFiManager library by **tzapu**. Several libraries share that name. |

**Manual flashing of a released binary:**

```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash          # optional: also wipes saved codes + Wi-Fi
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 921600 write_flash 0x0 esp32_ir_blaster_v2.1.1_full.bin
```

## 4. Boot and runtime

Open the serial console at 115200: `pio device monitor`, or the Arduino Serial Monitor. A normal boot
prints:

```
ESP32 IR Blaster firmware v2.1.1 (<build date>)
3 saved codes
Wi-Fi: 192.168.1.42
Web UI: http://irblaster.local  (http://192.168.1.42)
```

| Output | Meaning / fix |
|---|---|
| `rst:0x10 (RTCWDT_RTC_RESET)` boot loop, `invalid header` | Flash is empty or corrupt. Re-flash the `_full.bin` at 0x0. |
| `Brownout detector was triggered` | 3V3 dips under load. Check the LDO and C5/C6, or try a better USB supply. |
| `Guru Meditation Error` + backtrace | A crash. `pio device monitor` decodes the backtrace into file:line (`esp32_exception_decoder` filter). In the Arduino IDE, use the *ESP Exception Decoder* tool. Please include it in bug reports. |
| `! LittleFS mount failed` | The partition scheme has no filesystem. Use *Minimal SPIFFS*, or `min_spiffs.csv` in PlatformIO. |
| `! codes.json unreadable` | The file got corrupted (e.g. power loss while saving). The firmware starts empty; restore from an Export. |

**More logging:** set *Tools → Core Debug Level → Debug* (Arduino IDE), or `-DCORE_DEBUG_LEVEL=4` in
`platformio.ini` `build_flags`. Wi-Fi, HTTP and filesystem internals then log to the serial console.

**Health check over the network:**

```bash
curl -s http://irblaster.local/api/status | python3 -m json.tool
```

This shows the firmware version, IP, RSSI (Wi-Fi signal; below −80 dBm is weak), uptime, free heap
(should stay roughly constant), and the last received IR frame.

## 5. Wi-Fi

* **No `ESP32-IR-Setup` network.** A Wi-Fi network is already saved: hold USER for 5 s, or type
  `wifi-reset` in the serial console.
* **Can't join your network.** The ESP32 supports **2.4 GHz only**. Check the band, then the password. Hidden
  SSIDs need the name typed exactly.
* **`irblaster.local` doesn't open.**
  * Android and some corporate networks don't resolve mDNS; use the IP.
  * On Linux, `avahi-daemon` must be running.
  * On Windows 10 and newer, `.local` works in most browsers.
* **Web UI slow or drops out.** Check RSSI in `/api/status`. Keep the antenna end of the board (top edge, the
  overhanging module) clear of metal.

## 6. IR receive (learning)

1. Type `dump` in the serial console and press remote keys at 10–30 cm from the TSOP.
   * **Frames print:** reception works. If learning still fails, the frames are probably shorter than the
     noise threshold (`IR_MIN_UNKNOWN`) or are repeats. Press the key briefly.
   * **Nothing prints:**
     * Check the TSOP orientation: the dome faces outward and OUT goes in the square pad.
     * Check 3.3 V at IR_VS (C11), and that R11 is 100 Ω, not 100 kΩ.
     * Check the remote with a phone camera: its LED should flash purple.
2. **Codes decode as `UNKNOWN` with odd lengths.**
   * Sunlight and fluorescent or LED lamps add noise; try it in shade.
   * Some remotes use 36, 40 or 56 kHz carriers. A 38 kHz TSOP still often works up close; for reliable
     use, fit the matching TSOP variant ([COMPONENTS.md](COMPONENTS.md)).
3. **A/C remote frames cut short.** Raise `IR_CAPTURE_BUF` (e.g. 2048) and `IR_TIMEOUT_MS` (up to 90) in
   `config.h`.

## 7. IR transmit

1. Send a code and look at D3/D4 through a phone camera.
   * Phone front cameras usually lack an IR filter and show it best.
   * Both LEDs should flicker purple for the length of the frame.
2. **No light.**
   * Check LED polarity: the flat side / short leg goes in the square pad. One reversed LED blocks both,
     because they are in series.
   * Check Q3 (AO3400A) orientation.
   * Check R10 is 18 Ω, not 18 kΩ.
   * With a multimeter on DC, IO4 should read 0 V idle and briefly ~1.5–2 V (averaged) while sending.
3. **Light but the device doesn't react.**
   * Aim directly. The beam is ±17°, and range is about 8–10 m in line of sight.
   * Re-learn the code from closer.
   * Try `"repeat": 1–3` for Sony/RC5/RC6 devices.
   * Toggle-bit protocols (RC5/RC6) may need two different learned codes for alternate presses.
4. **Short range only.** Measure VIN while sending. If it sags below 4 V, the supply is weak. Check the C10
   (22 µF) reservoir.

## 8. Reporting a bug

Please include:
* the firmware version (`/api/status` or the boot banner),
* the hardware version (silkscreen),
* how it was flashed,
* the serial log from boot to the problem (with a decoded backtrace if it crashed),
* for IR issues, the `dump` output for the remote key in question.
