// ESP32 IR Blaster / Receiver - firmware for the ESP32 IR board (v2.x)
//
//  * Learns IR codes from any remote (decoded protocols like NEC/Sony/RC5/Samsung/AC units, or raw timings)
//  * Saves them by name in flash (LittleFS, /codes.json) and replays them with the 2x TSAL6200 IR LEDs
//  * Web UI + JSON REST API at http://irblaster.local (Wi-Fi set up through a captive portal)
//  * USER button: short press = send "button" code, hold 1 s = learn "button", hold 5 s = forget Wi-Fi
//  * Serial console (115200): help | list | send <name> | learn <name> | del <name> | dump | wifi-reset
//  * OTA updates (ArduinoOTA, host "irblaster")
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <WiFiManager.h>
#include <IRremoteESP8266.h>
#include <IRrecv.h>
#include <IRsend.h>
#include <IRutils.h>
#include "config.h"
#include "web_ui.h"

// ---------------------------------------------------------------- globals
IRrecv irrecv(PIN_IR_RX, IR_CAPTURE_BUF, IR_TIMEOUT_MS, true);
IRsend irsend(PIN_IR_TX);
decode_results results;
WebServer server(80);
WiFiManager wm;
JsonDocument codes;            // JSON array of saved codes (see codeFromResult for the format)
JsonDocument lastRx;           // last code seen by the receiver (for the UI / sniffing)

struct {
  bool active = false;
  String name;
  uint32_t until = 0;
  String result;               // "", "ok", "timeout"
} learn;

bool dumpAll = false;          // print every received code on Serial
bool fsOk = false;

// ---------------------------------------------------------------- status LED
// pattern: off / solid / blink with period. Non-blocking, driven from loop().
uint32_t ledUntil = 0;
void ledPulse(uint32_t ms) { digitalWrite(PIN_LED, HIGH); ledUntil = millis() + ms; }
void ledTask() {
  if (learn.active) {                       // fast blink while waiting for a remote
    digitalWrite(PIN_LED, (millis() / 100) % 2);
  } else if (ledUntil && (int32_t)(millis() - ledUntil) >= 0) {
    digitalWrite(PIN_LED, LOW); ledUntil = 0;
  }
}

// ---------------------------------------------------------------- storage
void saveCodes() {
  if (!fsOk) return;
  File f = LittleFS.open(CODES_FILE, "w");
  if (!f) { Serial.println("! cannot write " + String(CODES_FILE)); return; }
  serializeJson(codes, f);
  f.close();
}

void loadCodes() {
  codes.clear();
  if (fsOk && LittleFS.exists(CODES_FILE)) {
    File f = LittleFS.open(CODES_FILE, "r");
    DeserializationError e = deserializeJson(codes, f);
    f.close();
    if (e || !codes.is<JsonArray>()) {
      Serial.println("! codes.json unreadable, starting empty: " + String(e.c_str()));
      codes.clear();
    }
  }
  if (!codes.is<JsonArray>()) codes.to<JsonArray>();
}

int findCode(const String &name) {
  JsonArray a = codes.as<JsonArray>();
  for (size_t i = 0; i < a.size(); i++)
    if (name.equalsIgnoreCase(a[i]["name"].as<const char *>())) return i;
  return -1;
}

// ---------------------------------------------------------------- IR <-> JSON
// Saved code formats:
//   {"name","protocol":"NEC","bits":32,"value":"20DF10EF"}                 simple protocols (<= 64 bits)
//   {"name","protocol":"DAIKIN","bits":280,"state":"11DA27..."}            A/C protocols (byte state)
//   {"name","protocol":"UNKNOWN","freq":38,"raw":[9000,4500,560,...]}      anything not decoded
static String toHex(const uint8_t *b, size_t n) {
  static const char *h = "0123456789ABCDEF";
  String s; s.reserve(n * 2);
  for (size_t i = 0; i < n; i++) { s += h[b[i] >> 4]; s += h[b[i] & 15]; }
  return s;
}
static size_t fromHex(const char *s, uint8_t *out, size_t max) {
  size_t n = 0;
  auto nib = [](char c) -> int { return isdigit(c) ? c - '0' : (toupper(c) - 'A' + 10); };
  for (; s && s[0] && s[1] && n < max; s += 2) out[n++] = (nib(s[0]) << 4) | nib(s[1]);
  return n;
}

void codeFromResult(const decode_results &r, JsonObject o) {
  o["protocol"] = typeToString(r.decode_type, r.repeat);
  o["bits"] = r.bits;
  if (r.decode_type == decode_type_t::UNKNOWN) {
    uint16_t *raw = resultToRawArray(&r);
    uint16_t len = getCorrectedRawLength(&r);
    o["protocol"] = "UNKNOWN";
    o["freq"] = 38;
    JsonArray a = o["raw"].to<JsonArray>();
    for (uint16_t i = 0; i < len; i++) a.add(raw[i]);
    delete[] raw;
  } else if (hasACState(r.decode_type)) {
    o["state"] = toHex(r.state, r.bits / 8);
  } else {
    o["value"] = uint64ToString(r.value, 16);
  }
  o["text"] = resultToHumanReadableBasic(&r);
}

bool sendCode(JsonObjectConst c) {
  const char *proto = c["protocol"] | "";
  bool ok = false;
  irrecv.disableIRIn();                       // don't capture our own transmission
  if (c["raw"].is<JsonArrayConst>()) {
    JsonArrayConst a = c["raw"];
    std::vector<uint16_t> buf;
    buf.reserve(a.size());
    for (JsonVariantConst v : a) buf.push_back(v.as<uint16_t>());
    irsend.sendRaw(buf.data(), buf.size(), c["freq"] | 38);
    ok = !buf.empty();
  } else {
    decode_type_t t = strToDecodeType(proto);
    uint16_t bits = c["bits"] | 0;
    if (c["state"].is<const char *>()) {
      uint8_t st[kStateSizeMax];
      size_t n = fromHex(c["state"], st, sizeof(st));
      ok = irsend.send(t, st, n);
    } else if (c["value"].is<const char *>()) {
      uint64_t v = strtoull(c["value"].as<const char *>(), nullptr, 16);
      ok = irsend.send(t, v, bits ? bits : IRsend::defaultBits(t), c["repeat"] | 0);
    }
  }
  irrecv.enableIRIn();
  ledPulse(120);
  return ok;
}

bool sendByName(const String &name) {
  int i = findCode(name);
  if (i < 0) return false;
  return sendCode(codes[i].as<JsonObjectConst>());
}

void startLearn(const String &name) {
  learn.active = true; learn.name = name; learn.result = "";
  learn.until = millis() + LEARN_TIMEOUT_MS;
  irrecv.resume();
  Serial.printf("Learning '%s': point a remote at the receiver and press a key...\n", name.c_str());
}

void irTask() {
  if (learn.active && (int32_t)(millis() - learn.until) >= 0) {
    learn.active = false; learn.result = "timeout";
    digitalWrite(PIN_LED, LOW);
    Serial.println("Learn timed out");
  }
  if (!irrecv.decode(&results)) return;
  bool noise = results.decode_type == decode_type_t::UNKNOWN && results.rawlen < IR_MIN_UNKNOWN;
  if (!noise && !results.repeat) {
    lastRx.clear();
    codeFromResult(results, lastRx.to<JsonObject>());
    lastRx["ms"] = millis();
    if (dumpAll) Serial.println(resultToSourceCode(&results));
    if (learn.active) {
      int i = findCode(learn.name);
      JsonObject o = (i >= 0) ? codes[i].to<JsonObject>() : codes.as<JsonArray>().add<JsonObject>();
      o["name"] = learn.name;
      codeFromResult(results, o);
      saveCodes();
      learn.active = false; learn.result = "ok";
      digitalWrite(PIN_LED, LOW); ledPulse(600);
      Serial.printf("Saved '%s': %s\n", learn.name.c_str(), o["text"].as<const char *>());
    }
  }
  irrecv.resume();
}

// ---------------------------------------------------------------- USER button (IO13, active low)
void buttonTask() {
  static bool was = false; static uint32_t down = 0; static bool longDone = false;
  bool now = digitalRead(PIN_BUTTON) == LOW;
  uint32_t t = millis();
  if (now && !was) { down = t; longDone = false; }
  if (now && !longDone && t - down >= 5000) {                 // 5 s: forget Wi-Fi, reboot into setup portal
    longDone = true;
    Serial.println("Button held 5 s: clearing Wi-Fi settings");
    wm.resetSettings(); delay(200); ESP.restart();
  }
  if (!now && was && !longDone) {
    uint32_t held = t - down;
    if (held >= 1000) startLearn("button");                   // 1-5 s: learn the "button" code
    else if (held >= 30) {                                     // short: send it (or the first saved code)
      if (!sendByName("button") && codes.as<JsonArray>().size())
        sendCode(codes[0].as<JsonObjectConst>());
    }
  }
  was = now;
}

// ---------------------------------------------------------------- web server
void sendJson(int code, const JsonDocument &d) {
  String s; serializeJson(d, s);
  server.send(code, "application/json", s);
}
void reply(int code, const char *msg) {    // {"ok":true,"msg":...} or {"ok":false,"msg":...}
  JsonDocument d; d["ok"] = code < 300; d["msg"] = msg; sendJson(code, d);
}
String argName() { return server.hasArg("name") ? server.arg("name") : String(); }

void setupWeb() {
  server.on("/", HTTP_GET, [] { server.send_P(200, "text/html", INDEX_HTML); });

  server.on("/api/codes", HTTP_GET, [] { sendJson(200, codes); });

  server.on("/api/status", HTTP_GET, [] {
    JsonDocument d;
    d["learning"] = learn.active; d["learn_name"] = learn.name; d["learn_result"] = learn.result;
    d["learn_left_ms"] = learn.active ? (int32_t)(learn.until - millis()) : 0;
    if (!lastRx.isNull()) d["last"] = lastRx;
    d["ip"] = WiFi.localIP().toString(); d["rssi"] = WiFi.RSSI();
    d["version"] = FW_VERSION; d["uptime_s"] = millis() / 1000; d["heap"] = ESP.getFreeHeap(); d["codes"] = codes.size();
    sendJson(200, d);
  });

  server.on("/api/learn", HTTP_POST, [] {
    String n = argName(); n.trim();
    if (n.isEmpty() || n.length() > 32) return reply(400, "name (1-32 chars) required");
    startLearn(n);
    JsonDocument d; d["learning"] = n; d["timeout_ms"] = LEARN_TIMEOUT_MS; sendJson(200, d);
  });

  server.on("/api/send", HTTP_POST, [] {
    if (server.hasArg("plain") && server.arg("plain").startsWith("{")) {   // ad-hoc code in the body
      JsonDocument c;
      if (deserializeJson(c, server.arg("plain"))) return reply(400, "bad JSON");
      return sendCode(c.as<JsonObjectConst>()) ? reply(200, "sent") : reply(400, "could not send");
    }
    String n = argName();
    if (findCode(n) < 0) return reply(404, "no such code");
    sendByName(n) ? reply(200, "sent") : reply(500, "send failed");
  });

  server.on("/api/delete", HTTP_POST, [] {
    int i = findCode(argName());
    if (i < 0) return reply(404, "no such code");
    codes.as<JsonArray>().remove(i); saveCodes(); reply(200, "deleted");
  });

  server.on("/api/rename", HTTP_POST, [] {
    int i = findCode(server.arg("from")); String to = server.arg("to"); to.trim();
    if (i < 0) return reply(404, "no such code");
    if (to.isEmpty() || findCode(to) >= 0) return reply(400, "new name empty or taken");
    codes[i]["name"] = to; saveCodes(); reply(200, "renamed");
  });

  server.on("/api/export", HTTP_GET, [] {
    server.sendHeader("Content-Disposition", "attachment; filename=ir_codes.json");
    sendJson(200, codes);
  });

  server.on("/api/import", HTTP_POST, [] {
    JsonDocument in;
    if (deserializeJson(in, server.arg("plain")) || !in.is<JsonArray>()) return reply(400, "expected a JSON array");
    for (JsonObject c : in.as<JsonArray>()) {
      const char *n = c["name"] | "";
      if (!*n) continue;
      int i = findCode(n);
      if (i >= 0) codes[i].set(c); else codes.as<JsonArray>().add(c);
    }
    saveCodes(); reply(200, "imported");
  });

  server.on("/api/wifi-reset", HTTP_POST, [] {
    reply(200, "rebooting into setup portal");
    delay(300); wm.resetSettings(); ESP.restart();
  });

  server.onNotFound([] { reply(404, "not found"); });
  server.begin();
}

// ---------------------------------------------------------------- serial console
void serialTask() {
  static String line;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch != '\n') { if (line.length() < 120) line += ch; continue; }
    line.trim();
    String cmd = line, arg; int sp = line.indexOf(' ');
    if (sp > 0) { cmd = line.substring(0, sp); arg = line.substring(sp + 1); arg.trim(); }
    line = "";
    if (cmd == "list") {
      for (JsonObject c : codes.as<JsonArray>())
        Serial.printf("  %-20s %s\n", c["name"].as<const char *>(), c["protocol"].as<const char *>());
    } else if (cmd == "send") {
      Serial.println(sendByName(arg) ? "sent" : "no such code");
    } else if (cmd == "learn" && arg.length()) {
      startLearn(arg);
    } else if (cmd == "del") {
      int i = findCode(arg);
      if (i >= 0) { codes.as<JsonArray>().remove(i); saveCodes(); Serial.println("deleted"); }
      else Serial.println("no such code");
    } else if (cmd == "dump") {
      dumpAll = !dumpAll; Serial.printf("dump %s\n", dumpAll ? "on" : "off");
    } else if (cmd == "wifi-reset") {
      wm.resetSettings(); ESP.restart();
    } else if (cmd.length()) {
      Serial.println("commands: list | send <name> | learn <name> | del <name> | dump | wifi-reset");
    }
  }
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  pinMode(PIN_LED, OUTPUT); digitalWrite(PIN_LED, LOW);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  Serial.begin(115200);
  delay(50);
  Serial.println("\nESP32 IR Blaster firmware v" FW_VERSION " (" __DATE__ ")");

  irsend.begin();
  irrecv.setTolerance(IR_TOLERANCE);
  irrecv.setUnknownThreshold(IR_MIN_UNKNOWN);
  irrecv.enableIRIn();

  fsOk = LittleFS.begin(true);               // formats on first boot
  if (!fsOk) Serial.println("! LittleFS mount failed - codes will not persist");
  loadCodes();
  Serial.printf("%u saved codes\n", (unsigned)codes.size());

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  wm.setConfigPortalBlocking(false);         // IR + button keep working while the portal is up
  wm.setConfigPortalTimeout(0);
  if (wm.autoConnect(SETUP_AP)) Serial.println("Wi-Fi: " + WiFi.localIP().toString());
  else Serial.printf("Wi-Fi setup: join AP '%s' and open http://192.168.4.1\n", SETUP_AP);

  ledPulse(300);
}

// The setup portal owns port 80 while it runs, so the app's web server, mDNS and OTA start once connected.
bool netUp = false;
void netTask() {
  if (netUp || WiFi.status() != WL_CONNECTED || wm.getConfigPortalActive()) return;
  netUp = true;
  setupWeb();
  if (MDNS.begin(HOSTNAME)) MDNS.addService("http", "tcp", 80);
  ArduinoOTA.setHostname(HOSTNAME);
  ArduinoOTA.begin();
  Serial.printf("Web UI: http://%s.local  (http://%s)\n", HOSTNAME, WiFi.localIP().toString().c_str());
}

void loop() {
  wm.process();
  netTask();
  if (netUp) { server.handleClient(); ArduinoOTA.handle(); }
  irTask();
  buttonTask();
  serialTask();
  ledTask();
  delay(1);
}
