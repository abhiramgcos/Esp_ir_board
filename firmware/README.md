# Firmware

Arduino-framework firmware for the ESP32 IR board (hardware v2.0 and v2.1 share the same pin map).
Using Home Assistant? The [ESPHome configuration](../esphome/README.md) is an alternative to this firmware.

**What it does:**
* Learns IR codes from almost any remote:
  * decoded protocols (NEC, Sony, RC5/RC6, Samsung, LG, Panasonic, JVC, …),
  * full A/C state frames,
  * raw timings for anything unknown.
* Stores codes by name in flash (`/codes.json` on LittleFS). They survive reboots and OTA updates.
* Sends codes from:
  * a web page,
  * a JSON REST API,
  * the serial console,
  * the USER button.
* Wi-Fi is set up through a captive portal, so no credentials are compiled in.
* OTA updates after the first USB flash.

```
firmware/
├── esp32_ir_blaster/          Arduino sketch folder (open this in the Arduino IDE)
│   ├── esp32_ir_blaster.ino   application
│   ├── config.h               pins, timeouts, hostname, version
│   └── web_ui.h               single-page web UI (embedded, works offline)
└── platformio.ini             PlatformIO build of the same sketch
```

| GPIO | Function |
|---|---|
| IO4 | IR TX → AO3400A → 2× TSAL6200 (HIGH = on) |
| IO16 | IR RX ← TSOP38238 (active low) |
| IO2 | blue status LED |
| IO13 | USER button (active low) |
| IO21 / IO22 | I²C SDA / SCL on J4 |

## Flashing

Pick one method. The board has a CH340C with auto-reset, so none of them needs a button press: plug in USB-C
and flash.

### Option 1: prebuilt binary, from the browser (no install)

1. Download `esp32_ir_blaster_v2.1.1_full.bin` from the
   [latest release](https://github.com/abhiramgcos/Esp_ir_board/releases/latest).
2. Open the **[ESP Tool web flasher](https://espressif.github.io/esptool-js/)** in Chrome or Edge.
   (Web Serial doesn't work in Firefox or Safari.)
3. Click **Connect** and pick the **USB-SERIAL CH340** port.
4. Set flash address **`0x0`**, choose the `_full.bin` file, and click **Program**.
5. When it finishes, press **RESET** on the board.

Command-line equivalent:

```bash
pip install esptool
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 921600 write_flash 0x0 esp32_ir_blaster_v2.1.1_full.bin
```

On Windows the port is `COM3` or similar; on macOS it is `/dev/cu.wchusbserial*`.

### Option 2: Arduino IDE 2.x

One-time setup:
1. *File → Preferences → Additional boards manager URLs*: add
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
2. *Tools → Board → Boards Manager*: install **esp32 by Espressif Systems, version `2.0.17`**.
   Core 3.x is not supported by IRremoteESP8266 2.8.6 yet.
3. *Tools → Manage Libraries*: install these exact versions:

   | Library | Author | Version |
   |---|---|---|
   | IRremoteESP8266 | David Conran | 2.8.6 |
   | ArduinoJson | Benoît Blanchon | 7.x |
   | WiFiManager | tzapu | 2.0.17 |

Flash:
1. *File → Open* and choose `firmware/esp32_ir_blaster/esp32_ir_blaster.ino`. The `.h` files open as tabs.
2. Set the *Tools* menu:

   | Setting | Value |
   |---|---|
   | Board | **ESP32 Dev Module** |
   | Partition Scheme | **Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)** |
   | Upload Speed | 921600 (use 115200 if uploads fail) |
   | Core Debug Level | None (use "Info" or "Debug" when troubleshooting) |
   | Port | the CH340 port (`/dev/ttyUSB0`, `COM3`, `/dev/cu.wchusbserial…`) |

3. Click **Upload** (→). Then open the **Serial Monitor** at **115200** baud.

### Option 3: PlatformIO (CLI or VS Code)

```bash
cd firmware
pio run                        # build (first run downloads the toolchain)
pio run -t upload              # flash over USB
pio device monitor             # serial console at 115200, with ESP32 exception decoding
```

In VS Code, install the *PlatformIO IDE* extension, open the `firmware/` folder, and use the Build / Upload / Serial Monitor buttons in
the status bar. `platformio.ini` pins the platform and library versions, so builds are reproducible.

## First boot

1. The blue LED blinks once. The serial console prints the firmware version and how many codes are saved.
2. With no Wi-Fi saved, the board opens an access point called **`ESP32-IR-Setup`**:
   * Join it from a phone. The setup page opens by itself; if not, browse to `http://192.168.4.1`.
   * Pick your 2.4 GHz network and enter its password.
3. The board joins your network and serves the UI at **http://irblaster.local**. Android does not resolve
   `.local` names; use the IP address printed on the serial console or shown in your router.

IR learning and the USER button work even before Wi-Fi is configured.

## Using it

### Web UI
* **Learn:** type a name (e.g. `tv_power`) and press *Learn*. Point the remote at the TSOP from 5–30 cm and
  press the key within 15 s. The blue LED blinks fast while waiting.
* **Send / Rename / Delete** each saved code from its card.
* **Export / Import:** back up or restore all codes as JSON.

### USER button (IO13)

| Press | Action |
|---|---|
| tap | send the code named `button` (or the first saved code) |
| hold 1–5 s | learn a new `button` code |
| hold > 5 s | forget Wi-Fi and reboot into the setup portal |

### Serial console (115200 baud)

| Command | Action |
|---|---|
| `list` | list saved codes |
| `send <name>` | transmit a code |
| `learn <name>` | learn a code (15 s window) |
| `del <name>` | delete a code |
| `dump` | toggle sniffer mode: print every received frame as C source |
| `wifi-reset` | forget Wi-Fi and reboot |

### REST API

All responses are JSON. Actions return `{"ok": true|false, "msg": "..."}`.

| Method | Path | Body / query | Notes |
|---|---|---|---|
| GET | `/api/codes` | | array of saved codes |
| GET | `/api/status` | | version, IP, RSSI, uptime, heap, learn state, last received frame |
| POST | `/api/learn` | `?name=` | start a 15 s learn window |
| POST | `/api/send` | `?name=` | send a saved code |
| POST | `/api/send` | JSON code object | send an ad-hoc code without saving |
| POST | `/api/rename` | `?from=&to=` | |
| POST | `/api/delete` | `?name=` | |
| GET | `/api/export` | | download all codes |
| POST | `/api/import` | JSON array | merge codes (same name = replace) |
| POST | `/api/wifi-reset` | | forget Wi-Fi, reboot |

```bash
curl -X POST "http://irblaster.local/api/learn?name=tv_power"
curl -X POST "http://irblaster.local/api/send?name=tv_power"
curl -X POST http://irblaster.local/api/send -d '{"protocol":"NEC","bits":32,"value":"20DF10EF"}'
curl http://irblaster.local/api/export -o ir_codes.json
```

Saved code format (one object per code in `/codes.json`):

```jsonc
{"name":"tv_power","protocol":"NEC","bits":32,"value":"20DF10EF"}         // value protocols (≤64 bit)
{"name":"ac_cool","protocol":"DAIKIN","bits":280,"state":"11DA2700..."}   // A/C state protocols
{"name":"fan","protocol":"UNKNOWN","freq":38,"raw":[9000,4500,560,...]}    // raw marks/spaces in µs
```

Add `"repeat": n` to a value code to send it with `n` repeats (useful for Sony and some RC5/RC6 devices).

### Home Assistant

```yaml
# configuration.yaml
rest_command:
  tv_power:
    url: "http://irblaster.local/api/send?name=tv_power"
    method: POST
```

Call `rest_command.tv_power` from a script, an automation or a dashboard button.

## OTA updates

After the first USB flash, the board accepts updates over Wi-Fi:

* **PlatformIO:** `pio run -t upload --upload-port irblaster.local`
* **Arduino IDE:** *Tools → Port* → the network port `irblaster at <ip>`, then Upload.

Saved codes are kept: they live in the filesystem partition, which OTA does not touch.

## Configuration

Edit `esp32_ir_blaster/config.h`:

| Constant | Default | Meaning |
|---|---|---|
| `HOSTNAME` | `irblaster` | mDNS name and OTA host |
| `SETUP_AP` | `ESP32-IR-Setup` | setup portal SSID |
| `IR_CAPTURE_BUF` | 1024 | raw capture buffer (raise for very long A/C frames) |
| `IR_TIMEOUT_MS` | 50 | gap that ends a frame |
| `IR_TOLERANCE` | 25 | % timing tolerance when decoding |
| `LEARN_TIMEOUT_MS` | 15000 | learn window |

Debugging and common problems are covered in [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md).

## Dependencies

| Library | Version | License |
|---|---|---|
| [IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266) | 2.8.6 | LGPL-2.1 |
| [ArduinoJson](https://arduinojson.org) | 7.2.1 | MIT |
| [WiFiManager](https://github.com/tzapu/WiFiManager) | 2.0.17 | MIT |
| Arduino-ESP32 core | 2.0.17 (PlatformIO `espressif32@6.9.0`) | LGPL-2.1 |
