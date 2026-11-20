# Firmware: ESP32 IR Blaster / Receiver

Full working firmware for the board (v2.0 and v2.1 have the same pin map).

* **Learn** codes from any IR remote: TVs, set-top boxes, ACs, fans, LED strips.
  * Decoded protocols (NEC, Sony, RC5/RC6, Samsung, LG, Panasonic, the A/C protocols…) are stored compactly.
  * Anything else is stored as raw timings.
* **Store** codes by name in flash (`/codes.json` on LittleFS). They survive reboots and firmware updates.
* **Send** them from a web page on your phone, a REST API (scripts, Home Assistant), the serial console, or the
  USER button.
* **Wi-Fi setup portal**: no passwords in the code.
* **OTA updates** after the first USB flash.

| Pin | Use |
|---|---|
| IO4 | IR transmit → AO3400A → 2× TSAL6200 (HIGH = on) |
| IO16 | IR receive ← TSOP38238 (active low) |
| IO2 | blue user LED |
| IO13 | USER button (active low) |
| IO21 / IO22 | I²C SDA / SCL on J4 (4.7 k pull-ups) |

## 1. Flash it (USB-C, no buttons needed)

The board has a CH340C USB-serial chip with DTR/RTS auto-reset, so the computer can put the ESP32 into
bootloader mode by itself.

### Option A: PlatformIO CLI (recommended, what this repo is tested with)

```bash
cd ~/Desktop/projects/Esp_ir_board
source .venv/bin/activate
pip install platformio
cd firmware
pio run                       # build (the first run downloads the ESP32 toolchain, ~5 min)
pio run -t upload             # flash over USB-C (auto-detects /dev/ttyUSB0)
pio device monitor            # serial console, 115200 baud (Ctrl+C to quit)
```

On Linux, if the upload fails with "permission denied" on `/dev/ttyUSB0`:

```bash
sudo usermod -aG dialout $USER
```

Then log out and back in. Ubuntu's `brltty` package can also grab CH340 adapters. If the port keeps
disappearing, remove it with `sudo apt remove brltty`.

### Option B: VS Code + PlatformIO extension

1. Install VS Code and the **PlatformIO IDE** extension.
2. In VS Code, use *File → Open Folder* and pick `firmware/`.
3. Click ✓ (Build), then → (Upload), then the plug icon (Serial Monitor).

### Option C: Arduino IDE 2

1. Go to *Boards Manager* and install **esp32 by Espressif, version 2.0.17**. The 3.x cores are not yet
   supported by IRremoteESP8266 2.8.6.
2. Go to *Library Manager* and install **IRremoteESP8266 2.8.6**, **ArduinoJson 7.x** and **WiFiManager 2.0.17**
   (tzapu).
3. Create a sketch folder `esp32_ir/`:
   * Copy `src/main.cpp` to `esp32_ir/esp32_ir.ino`.
   * Copy `config.h` and `web_ui.h` next to it.
4. Set *Tools*:
   * Board: **ESP32 Dev Module**
   * Partition scheme: **Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)**
   * Upload speed: 921600
5. Upload.

### If auto-reset ever fails (manual bootloader mode)

1. Hold **BOOT** and tap **RESET**.
2. Release **BOOT**.
3. Upload.
4. Press **RESET** when it finishes.

This also works through the J3 UART header with an external 3.3 V USB-serial adapter. Wire:

| J3 | Adapter |
|---|---|
| TX | RX |
| RX | TX |
| GND | GND |

Don't power the board from the adapter's 5 V and USB-C at the same time.

## 2. First start: connect it to Wi-Fi

1. Power the board. The blue LED blinks once.
2. On your phone, join the open Wi-Fi network **ESP32-IR-Setup**. A setup page opens; if it doesn't, browse to
   `http://192.168.4.1`.
3. Choose your home Wi-Fi (2.4 GHz only), enter the password and save.
4. The board joins your network. Open **http://irblaster.local**, or the IP address printed on the serial
   console. On Android, mDNS (`.local`) may not work, so use the IP.

To change networks later:
* hold the USER button for 5 s,
* press "Reset Wi-Fi" on the web page, or
* type `wifi-reset` in the serial console.

## 3. Use it

**Web page:**
* Type a name (e.g. `tv_power`) and press **Learn**.
* Point the remote at the black TSOP receiver from about 5–30 cm and press the key. The blue LED blinks fast
  while it waits (15 s), then stays on briefly when the code is saved.
* Use **Send**, **Rename** and **✕** on the saved codes. **Export** and **Import** back them up as JSON.

**USER button (IO13):**

| Action | Effect |
|---|---|
| Tap | Send the code named `button` (or the first saved code) |
| Hold 1–5 s | Learn a new `button` code |
| Hold 5 s | Forget Wi-Fi and reboot into the setup portal |

**Serial console (115200):**

| Command | Effect |
|---|---|
| `list` | List saved codes |
| `send tv_power` | Send a code |
| `learn tv_power` | Learn a code |
| `del tv_power` | Delete a code |
| `dump` | Print every received code as C source (sniffer mode) |
| `wifi-reset` | Forget Wi-Fi |

**REST API (JSON):**

```bash
curl http://irblaster.local/api/codes                                    # list
curl -X POST "http://irblaster.local/api/learn?name=tv_power"             # start learning (15 s)
curl http://irblaster.local/api/status                                    # learning state, last code, Wi-Fi
curl -X POST "http://irblaster.local/api/send?name=tv_power"              # send a saved code
curl -X POST http://irblaster.local/api/send -d '{"protocol":"NEC","bits":32,"value":"20DF10EF"}'  # ad-hoc
curl -X POST "http://irblaster.local/api/rename?from=tv_power&to=tv"
curl -X POST "http://irblaster.local/api/delete?name=tv"
curl http://irblaster.local/api/export -o ir_codes.json                   # backup
curl -X POST http://irblaster.local/api/import --data-binary @ir_codes.json
```

**Home Assistant** (`configuration.yaml`):

```yaml
rest_command:
  tv_power:
    url: "http://irblaster.local/api/send?name=tv_power"
    method: POST
```

## 4. Update over Wi-Fi (OTA)

After the first USB flash:

```bash
pio run -t upload --upload-port irblaster.local
```

On the Arduino IDE, pick the network port `irblaster`.

## 5. Tips and troubleshooting

* **Range.** The two TSAL6200 run at about 100 mA (pulsed), which reaches roughly 8–10 m with a direct line
  of sight. Aim the LEDs at the device, or bend them up toward the ceiling to reflect around a room.
* **A/C remotes** send the full state (mode, temperature, fan) in every press. Learn one code per setting you
  need, e.g. `ac_cool_24`, `ac_off`.
* **A code learns but the device ignores it.**
  * Learn it again holding the remote closer, and press briefly.
  * Some remotes (Sony, RC5/RC6) need repeats or toggle bits. Use the API with `"repeat": 2`.
* **Nothing is received.**
  * Run `dump` in the serial console and press keys. If nothing prints, check the TSOP38238 orientation
    (dome facing out) and that IR_VS has 3.3 V.
  * Most remotes are 38 kHz. A few are 36 or 56 kHz; use the matching TSOP variant (see
    [docs/COMPONENTS.md](../docs/COMPONENTS.md)).
* **Check the IR LEDs are firing.** Look at them through a phone camera while sending; most phone cameras show
  IR as a purple flash. Front cameras usually work better.
* **Partition scheme.** `min_spiffs.csv` gives two 1.9 MB app slots (needed for OTA) and a 190 kB filesystem.
  That is about 300 decoded codes, or fewer large raw/A/C ones.

## Libraries

* [IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266) 2.8.6 (LGPL-2.1)
* [ArduinoJson](https://arduinojson.org) 7.2.1 (MIT)
* [WiFiManager](https://github.com/tzapu/WiFiManager) 2.0.17 (MIT)

All three are fetched automatically by PlatformIO (`platformio.ini`).
