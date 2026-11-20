# ESPHome / Home Assistant

Run the board on [ESPHome](https://esphome.io) instead of the stand-alone firmware. Home Assistant then gets
native entities and actions. Use either this or the firmware in [`firmware/`](../firmware); flashing one
replaces the other.

| File | Purpose |
|---|---|
| `esp32-ir-blaster.yaml` | **Board package**: pins, IR TX/RX, button, LED, I²C, diagnostics, HA actions. No secrets. |
| `example.yaml` | **Your config.** Copy it, edit the lines marked `# <- EDIT`, add your remote's buttons. |
| `factory.yaml` | Builds the prebuilt image on the Releases page (no Wi-Fi credentials; adopt in Home Assistant). |

**What you get in Home Assistant:**

| Entity / action | Purpose |
|---|---|
| Your buttons (`button.tv_power`, …) | one per learned code |
| **Last IR code** (sensor) | the most recent decoded remote key, for learning without reading logs |
| USER button (binary sensor) | the on-board USER button, usable in automations |
| Wi-Fi signal, uptime, IP, status, restart | diagnostics |
| `esphome.<name>_send_nec`, `_send_samsung`, `_send_sony`, `_send_pronto`, `_send_raw` | send any code from scripts and automations, no re-flash needed |
| Optional climate entity | full A/C control (mode, temperature, fan) for supported brands |

## Option A: flash the prebuilt image and adopt it (easiest)

1. Download `esp32-ir-blaster-esphome_v2.1.0.factory.bin` from the
   [latest release](https://github.com/abhiramgcos/Esp_ir_board/releases/latest).
2. Open **<https://web.esphome.io>** in Chrome or Edge.
3. Plug the board in over USB-C, click **Connect**, and choose the CH340 port.
4. Click **Install** and select the `.factory.bin` file.
5. Connect it to Wi-Fi. Either:
   * on the same web.esphome.io page, click **Configure Wi-Fi** (Improv over USB), or
   * join the **`ESP32 IR Blaster`** hotspot from a phone and pick your network in the page that opens.
6. In Home Assistant:
   * *Settings → Devices & services* shows the discovered **ESPHome** device. Click **Configure** to add it.
   * To edit it later, open the **ESPHome Device Builder** add-on, find the board, and click **Adopt**.
     ESPHome creates your own config (with the package from this repo and a fresh API key) and re-flashes it
     over Wi-Fi.
7. Add your remote's buttons to the adopted config (see [Learning codes](#learning-codes)) and click
   **Install**.

## Option B: build your own config in the ESPHome dashboard

1. Install the **ESPHome Device Builder** add-on in Home Assistant (*Settings → Add-ons → Add-on store*),
   or run ESPHome on your PC (`pip install esphome && esphome dashboard config/`).
2. Open the dashboard. Click **Secrets** (top right) and add:

   ```yaml
   wifi_ssid: "YourNetwork"
   wifi_password: "your-wifi-password"
   ir_blaster_api_key: "<32-byte base64 key>"     # e.g. from the key generator on esphome.io/components/api
   ota_password: "choose-any-password"
   ```

3. Click **+ New device** → *Continue* → give it a name → **Skip** the board selection. Then click **Edit** on
   the new card, replace everything with the contents of [`example.yaml`](example.yaml), and save.
4. Change the lines marked **`# <- EDIT`**:

   | Line | Change it to |
   |---|---|
   | `name` | the hostname, e.g. `bedroom-ir` (lowercase, dashes) |
   | `friendly_name` | the display name in Home Assistant |
   | `secrets.yaml` entries | your Wi-Fi, an API key, an OTA password |
   | `button:` section | your own learned codes (the examples are LG TV codes) |
   | `climate:` (optional) | uncomment and set `platform:` to your A/C brand |

5. First install: **Install → Plug into the computer running ESPHome Dashboard**, or **Manual download** and
   flash the `.factory.bin` via web.esphome.io. Every later install goes over Wi-Fi.
6. Home Assistant discovers the device. Accept it and enter the API key if asked.

**From the command line:**

```bash
pip install esphome
cd esphome
cp example.yaml living-room-ir.yaml               # then edit it, and create secrets.yaml next to it
esphome run living-room-ir.yaml                   # compile + flash over USB (first time) or OTA
esphome logs living-room-ir.yaml                  # live logs, including received IR codes
```

## Learning codes

1. Open the device **Logs** (ESPHome dashboard → *Logs*), or watch the **Last IR code** sensor in Home
   Assistant.
2. Point the remote at the black receiver (5–30 cm) and press a key. The log shows lines like:

   ```
   [I][remote.nec:...]: Received NEC: address=0xFB04, command=0xF708
   [I][remote.samsung:...]: Received Samsung: data=0xE0E040BF, nbits=32
   [I][remote.raw:...]: Received Raw: 9000, -4500, 560, -560, ...
   ```

3. Put the values into a button in your config and install:

   ```yaml
   button:
     - platform: template
       name: "TV Power"
       on_press:
         - remote_transmitter.transmit_nec:
             address: 0xFB04
             command: 0xF708
   ```

   Other protocols use the matching action: `transmit_samsung` (`data`, `nbits`), `transmit_sony`, `transmit_rc5`,
   `transmit_lg`, `transmit_panasonic`, `transmit_pronto`, `transmit_raw` (`code: [...]`,
   `carrier_frequency: 38kHz`). See the
   [remote_transmitter docs](https://esphome.io/components/remote_transmitter).

**Without re-flashing:** call an action from Home Assistant (*Developer tools → Actions*):

```yaml
action: esphome.living_room_ir_send_nec
data:
  address: 0xFB04
  command: 0xF708
```

You can use the same call in automations and scripts, for example "turn the TV off at midnight".

## Air conditioners

A/C remotes send the whole state (mode, temperature, fan) in every press, so learning single buttons scales
badly. ESPHome has [climate_ir](https://esphome.io/components/climate/climate_ir) platforms for many brands:
Daikin, Mitsubishi, Toshiba, LG, Fujitsu, Gree, Midea, Coolix, Hitachi, Whirlpool and more. Uncomment the
`climate:` block in your config and set `platform:` to your brand. You then get a full thermostat card in
Home Assistant. With `receiver_id: ir_rx` set, using the original remote keeps the HA state in sync.

## Notes

* **Pins** are fixed by the PCB; the package already sets them. Only change them if you modify the hardware.
* **Range and aiming** are the same as with the stand-alone firmware: about 8–10 m line of sight, and the
  LEDs can be bent toward the target.
* **Switching back** to the stand-alone firmware: flash `esp32_ir_blaster_v2.1.0_full.bin` (see
  [firmware/README.md](../firmware/README.md)). ESPHome and the stand-alone firmware store codes
  differently, so codes are not carried over.
* **Troubleshooting:**
  * If nothing appears in the logs when you press a remote key, follow
    [docs/TROUBLESHOOTING.md §6](../docs/TROUBLESHOOTING.md#6-ir-receive-learning).
  * If the device shows *offline* in HA, check the API key and that both are on the same network/VLAN
    (mDNS).
