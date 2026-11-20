// Pin map of the ESP32 IR board (v2.0 / v2.1). Matches gen/circuit.py and the GPIO map on the PCB back.
#pragma once

constexpr uint8_t PIN_IR_TX   = 4;    // -> 100R -> AO3400A gate; HIGH = IR LEDs on (2x TSAL6200, ~100 mA)
constexpr uint8_t PIN_IR_RX   = 16;   // TSOP38238 output, active LOW, 38 kHz demodulated
constexpr uint8_t PIN_LED     = 2;    // blue user LED, HIGH = on (also a boot strap pin: keep it an output)
constexpr uint8_t PIN_BUTTON  = 13;   // USER button to GND, 10k pull-up on board
constexpr uint8_t PIN_SDA     = 21;   // I2C on J4 (4.7k pull-ups on board)
constexpr uint8_t PIN_SCL     = 22;

constexpr const char *HOSTNAME   = "irblaster";        // http://irblaster.local
constexpr const char *SETUP_AP   = "ESP32-IR-Setup";   // Wi-Fi setup portal (open AP) when no network is saved
constexpr const char *CODES_FILE = "/codes.json";

constexpr uint16_t IR_CAPTURE_BUF  = 1024;   // raw timings buffer (AC remotes send long frames)
constexpr uint8_t  IR_TIMEOUT_MS   = 50;     // gap that ends a frame (50 ms covers most AC units)
constexpr uint8_t  IR_TOLERANCE    = 25;     // % timing tolerance when decoding
constexpr uint16_t IR_MIN_UNKNOWN  = 12;     // ignore noise bursts shorter than this many marks/spaces
constexpr uint32_t LEARN_TIMEOUT_MS = 15000; // how long "learn" waits for a remote press
