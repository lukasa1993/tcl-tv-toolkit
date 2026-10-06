#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <Update.h>
#include <driver/uart.h>
#include <driver/gpio.h>
#include "config.h"
#include "sequence.h"
#include "web_page.h"

constexpr int RX_PIN = 25;
constexpr int TX_PIN = 26;
constexpr uint32_t BAUD = 115200;
constexpr size_t CAPACITY = 32768;
HardwareSerial tv(2);
WebServer server(8080);
Preferences settings;
uint8_t history[CAPACITY];
uint64_t received = 0;
portMUX_TYPE guard = portMUX_INITIALIZER_UNLOCKED;
uint32_t interruptUntil = 0;
uint32_t lastEnter = 0;
uint8_t armedSeconds = 0;
bool commissioned = false;
bool loopback = false;
automation::Profile profile;
// Profiles are too large for HTTP callbacks' small Arduino loop stack.
automation::Profile incomingProfile;
automation::Runner runner;
bool sequenceArmed = false;
struct SequenceEvent { uint32_t ms; char name[24]; int step; };
SequenceEvent events[32];
size_t eventCount = 0;
bool uploadAllowed = false, uploadComplete = false;
String uploadError;
uint32_t restartAt = 0;
uint32_t rxHighSamples = 0, rxLowSamples = 0;
uint32_t rxEdges = 0;
int lastRxLevel = -1;
uint32_t rxStartupMilliVolts = 0;
uint32_t rxStartupRaw = 0;
uint32_t rxStartupMinMv = UINT32_MAX, rxStartupMaxMv = 0;

void event(const char *name, int step = -1) {
  if (eventCount >= 32) return;
  auto &e = events[eventCount++];
  e.ms = millis() - runner.started;
  snprintf(e.name, sizeof(e.name), "%s", name);
  e.step = step;
}

bool cancelSequence() {
  runner.stop();
  portENTER_CRITICAL(&guard);
  interruptUntil = 0;
  portEXIT_CRITICAL(&guard);
  sequenceArmed = false;
  armedSeconds = 0;
  // Clear both the old Enter-only flag and the full-sequence flag.
  const bool clearedSequence = settings.putBool("seq-armed", false) == 1;
  const bool clearedEnter = settings.putUChar("enter", 0) == 1;
  event("disarmed");
  return clearedSequence && clearedEnter;
}

String quote(const char *value) {
  String out = "\"";
  for (const char *p = value; *p; ++p) {
    if (*p == '"' || *p == '\\') out += '\\';
    if ((uint8_t)*p >= 32) out += *p;
  }
  return out + "\"";
}

String profileJson() {
  String out = "{\"start\":" + String(profile.startMs);
  out += ",\"enter\":" + String(profile.enterMs);
  out += ",\"interval\":" + String(profile.intervalMs);
  out += ",\"settle\":" + String(profile.settleMs) + ",\"steps\":[";
  for (size_t i = 0; i < profile.count; ++i) {
    if (i) out += ',';
    out += "{\"command\":" + quote(profile.steps[i].command);
    out += ",\"wait\":" + String(profile.steps[i].waitMs) + "}";
  }
  return out + "]}";
}

// Capture independently of Wi-Fi association and HTTP requests.
void capture(void *) {
  for (;;) {
    const int level = gpio_get_level(GPIO_NUM_25);
    portENTER_CRITICAL(&guard);
    if (level) ++rxHighSamples; else ++rxLowSamples;
    if (lastRxLevel >= 0 && lastRxLevel != level) ++rxEdges;
    lastRxLevel = level;
    portEXIT_CRITICAL(&guard);
    uint8_t data[256];
    size_t count = 0;
    while (count < sizeof(data) && tv.available()) data[count++] = tv.read();
    if (count) {
      portENTER_CRITICAL(&guard);
      for (size_t i = 0; i < count; ++i) history[received++ % CAPACITY] = data[i];
      portEXIT_CRITICAL(&guard);
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

bool authorized() {
  if (server.header("Authorization") == String("Bearer ") + ACCESS_TOKEN) return true;
  server.send(401, "text/plain", "Authentication required\n");
  return false;
}

void status() {
  if (!authorized()) return;
  uint64_t total;
  uint32_t until;
  uint32_t highs, lows, edges;
  int level;
  portENTER_CRITICAL(&guard);
  total = received;
  until = interruptUntil;
  highs = rxHighSamples; lows = rxLowSamples; edges = rxEdges; level = lastRxLevel;
  portEXIT_CRITICAL(&guard);
  String json = "{\"firmware\":\"tcl-uart-bridge-2\",\"ip\":\"" + WiFi.localIP().toString();
  json += "\",\"hostname\":\"tcl-uart-bridge\",\"baud\":115200,\"rx_gpio\":25,\"tx_gpio\":26";
  json += ",\"uptime_ms\":" + String(millis());
  json += ",\"received\":" + String((unsigned long long)total);
  json += ",\"retained\":" + String((unsigned long)min(total, uint64_t(CAPACITY)));
  json += ",\"rssi\":" + String(WiFi.RSSI());
  json += ",\"next_boot_enter_seconds\":" + String(armedSeconds);
  json += ",\"commissioned\":" + String(commissioned ? "true" : "false");
  json += ",\"loopback\":" + String(loopback ? "true" : "false");
  json += ",\"sequence_armed\":" + String(sequenceArmed ? "true" : "false");
  json += ",\"sequence_phase\":" + quote(automation::phaseName(runner.phase));
  json += ",\"ota_supported\":true";
  json += ",\"rx_pin_level\":" + String(level);
  json += ",\"rx_high_samples\":" + String(highs);
  json += ",\"rx_low_samples\":" + String(lows);
  json += ",\"rx_sampled_edges\":" + String(edges);
  json += ",\"rx_startup_mv\":" + String(rxStartupMilliVolts);
  json += ",\"rx_startup_raw\":" + String(rxStartupRaw);
  json += ",\"rx_startup_min_mv\":" + String(rxStartupMinMv);
  json += ",\"rx_startup_max_mv\":" + String(rxStartupMaxMv);
  json += ",\"interrupt_active\":" + String(until && int32_t(until - millis()) > 0 ? "true" : "false") + "}";
  server.send(200, "application/json", json);
}

void readUart() {
  if (!authorized()) return;
  uint64_t requested = server.hasArg("since") ? strtoull(server.arg("since").c_str(), nullptr, 10) : 0;
  uint64_t end;
  portENTER_CRITICAL(&guard);
  end = received;
  portEXIT_CRITICAL(&guard);
  uint64_t earliest = end > CAPACITY ? end - CAPACITY : 0;
  uint64_t start = max(requested, earliest);
  if (start > end) {
    server.send(409, "text/plain", "Cursor is ahead of capture; bridge may have restarted\n");
    return;
  }
  String data;
  data.reserve(size_t(end - start));
  // Copy in bounded chunks so UART capture is never blocked for an entire response.
  for (uint64_t pos = start; pos < end;) {
    char chunk[256];
    size_t n = min(uint64_t(sizeof(chunk)), end - pos);
    portENTER_CRITICAL(&guard);
    uint64_t currentEarliest = received > CAPACITY ? received - CAPACITY : 0;
    if (pos < currentEarliest) {
      portEXIT_CRITICAL(&guard);
      server.send(409, "text/plain", "Capture wrapped during request; retry from latest cursor\n");
      return;
    }
    for (size_t i = 0; i < n; ++i) chunk[i] = history[(pos + i) % CAPACITY];
    portEXIT_CRITICAL(&guard);
    data.concat(chunk, n);
    pos += n;
  }
  server.sendHeader("X-UART-Start", String((unsigned long long)start));
  server.sendHeader("X-UART-End", String((unsigned long long)end));
  server.sendHeader("X-UART-Lost", String((unsigned long long)(start - requested)));
  server.send(200, "application/octet-stream", data);
}

void writeUart() {
  if (!authorized()) return;
  if (runner.active() || sequenceArmed || restartAt) {
    server.send(409, "text/plain", "Disarm/stop automation before manual transmission\n");
    return;
  }
  // Hex keeps binary UART bytes intact through WebServer's text body parser.
  String body = server.arg("plain");
  if (body.length() > 8192) {
    server.send(413, "text/plain", "Maximum UART write is 4096 bytes\n");
    return;
  }
  static uint8_t decoded[4096];
  auto digit = [](char c) -> int {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  };
  if (body.length() % 2) {
    server.send(400, "text/plain", "UART payload must be hexadecimal\n");
    return;
  }
  for (size_t i = 0; i < body.length(); i += 2) {
    int high = digit(body[i]), low = digit(body[i + 1]);
    if (high < 0 || low < 0) {
      server.send(400, "text/plain", "UART payload must be hexadecimal\n");
      return;
    }
    decoded[i / 2] = (high << 4) | low;
  }
  size_t written = tv.write(decoded, body.length() / 2);
  server.send(200, "application/json", "{\"written\":" + String(written) + "}");
}

void scheduleEnter(bool nextBoot) {
  if (!authorized()) return;
  if (runner.active() || sequenceArmed || restartAt) {
    server.send(409, "text/plain", "Disarm/stop automation before manual Enter\n");
    return;
  }
  String body = server.arg("plain");
  char *tail;
  long seconds = strtol(body.c_str(), &tail, 10);
  if (body.isEmpty() || *tail != '\0' || seconds < 0 || seconds > 30) {
    server.send(400, "text/plain", "Body must be an integer from 0 through 30\n");
    return;
  }
  if (nextBoot) {
    armedSeconds = seconds;
    settings.putUChar("enter", armedSeconds);
  } else {
    portENTER_CRITICAL(&guard);
    interruptUntil = seconds ? millis() + seconds * 1000 : 0;
    portEXIT_CRITICAL(&guard);
  }
  server.send(200, "application/json", "{\"seconds\":" + String(seconds) + "}");
}

void automationStatus() {
  if (!authorized()) return;
  String out = "{\"armed\":" + String(sequenceArmed ? "true" : "false");
  out += ",\"active\":" + String(runner.active() ? "true" : "false");
  out += ",\"dry_run\":" + String(runner.dry ? "true" : "false");
  out += ",\"phase\":" + quote(automation::phaseName(runner.phase));
  uint32_t elapsed = runner.active() ? millis() - runner.started :
    (runner.phase != automation::IDLE && eventCount ? events[eventCount - 1].ms : 0);
  out += ",\"elapsed_ms\":" + String(elapsed);
  out += ",\"enter_count\":" + String(runner.enters);
  out += ",\"commands_sent\":" + String(runner.sent);
  out += ",\"profile\":" + profileJson() + ",\"events\":[";
  for (size_t i = 0; i < eventCount; ++i) {
    if (i) out += ',';
    out += "{\"ms\":" + String(events[i].ms) + ",\"name\":" + quote(events[i].name);
    out += ",\"step\":" + String(events[i].step) + "}";
  }
  server.send(200, "application/json", out + "]}");
}

bool numberArg(const String &key, uint32_t &value, uint32_t maximum, uint32_t minimum = 0) {
  if (!server.hasArg(key)) return false;
  const String raw = server.arg(key);
  if (raw.isEmpty() || raw.length() > 6) return false;
  for (size_t i = 0; i < raw.length(); ++i) if (raw[i] < '0' || raw[i] > '9') return false;
  value = strtoul(raw.c_str(), nullptr, 10);
  return value >= minimum && value <= maximum;
}

bool parseProfile(automation::Profile &next) {
  uint32_t count;
  if (!numberArg("start", next.startMs, 120000) || !numberArg("enter", next.enterMs, 120000) ||
      !numberArg("interval", next.intervalMs, 1000, 20) || !numberArg("settle", next.settleMs, 30000) ||
      !numberArg("count", count, automation::MAX_STEPS)) return false;
  next.count = count;
  for (size_t i = 0; i < count; ++i) {
    const String command = server.arg("cmd" + String(i));
    if (command.isEmpty() || command.length() > automation::MAX_COMMAND ||
        !numberArg("wait" + String(i), next.steps[i].waitMs, 60000)) return false;
    memcpy(next.steps[i].command, command.c_str(), command.length() + 1);
  }
  return automation::valid(next);
}

bool saveProfile(const automation::Profile &next) {
  if (settings.putBytes("seq-profile", &next, sizeof(next)) != sizeof(next)) return false;
  profile = next;
  return true;
}

void configureSequence() {
  if (!authorized()) return;
  if (runner.active() || sequenceArmed || restartAt) {
    server.send(409, "text/plain", "Disarm/stop before editing the saved sequence\n"); return;
  }
  automation::Profile &next = incomingProfile;
  if (!parseProfile(next)) {
    server.send(400, "text/plain", "Invalid timing or commands: up to 12 printable ASCII commands, 256 characters each\n"); return;
  }
  if (!saveProfile(next)) { server.send(500, "text/plain", "Could not save settings\n"); return; }
  // Clear old event indexes when the profile changes.
  eventCount = 0; runner.clear();
  server.send(200, "application/json", "{\"saved\":true}");
}

void startSequence() {
  if (!authorized()) return;
  if (runner.active() || sequenceArmed || restartAt ||
      (interruptUntil && int32_t(interruptUntil - millis()) > 0)) {
    server.send(409, "text/plain", "Disarm/stop the existing operation first\n"); return;
  }
  const String mode = server.arg("mode");
  if (mode != "dry" && mode != "now" && mode != "arm") {
    server.send(400, "text/plain", "Mode must be dry, now, or arm\n"); return;
  }
  if (mode != "dry" && server.arg("risk") != "ack") {
    server.send(400, "text/plain", "Acknowledge that unlock commands can factory-reset the TV and erase its setup\n"); return;
  }
  automation::Profile &next = incomingProfile;
  if (!parseProfile(next)) { server.send(400, "text/plain", "Invalid sequence\n"); return; }
  if (!cancelSequence() || !saveProfile(next)) {
    server.send(500, "text/plain", "Could not safely save/disarm the sequence\n"); return;
  }
  eventCount = 0;
  runner.clear();
  runner.started = millis();
  if (mode == "arm") {
    if (settings.putBool("seq-armed", true) != 1) {
      server.send(500, "text/plain", "Could not arm persistent sequence\n"); return;
    }
    sequenceArmed = true;
    event("armed-next-esp-boot");
  } else {
    runner.start(profile, millis(), mode == "dry");
    event(mode == "dry" ? "dry-run-start" : "start");
  }
  server.send(200, "application/json", "{\"accepted\":true}");
}

void disarmSequence() {
  if (!authorized()) return;
  if (!cancelSequence()) { server.send(500, "text/plain", "Stopped now, but persistent flag could not be cleared\n"); return; }
  server.send(200, "application/json", "{\"disarmed\":true}");
}

// Updates only the ESP application. Every upload clears automation before writing.
void firmwareUpload() {
  HTTPUpload &upload = server.upload();
  if (upload.status == UPLOAD_FILE_START) {
    uploadAllowed = false; uploadComplete = false; uploadError = "";
    if (server.header("Authorization") != String("Bearer ") + ACCESS_TOKEN) return;
    if (!cancelSequence()) { uploadError = "Could not clear ARM flags"; return; }
    uploadAllowed = true;
    if (!Update.begin(UPDATE_SIZE_UNKNOWN, U_FLASH)) uploadError = Update.errorString();
  } else if (upload.status == UPLOAD_FILE_WRITE && uploadAllowed && uploadError.isEmpty()) {
    if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) uploadError = Update.errorString();
  } else if (upload.status == UPLOAD_FILE_END && uploadAllowed) {
    if (uploadError.isEmpty()) {
      uploadComplete = Update.end(true);
      if (!uploadComplete) uploadError = Update.errorString();
    } else Update.abort();
  } else if (upload.status == UPLOAD_FILE_ABORTED && uploadAllowed) {
    Update.abort(); uploadAllowed = false; uploadError = "Upload aborted";
  }
}

void finishUpdate() {
  if (!authorized()) return;
  if (!uploadAllowed || !uploadComplete) {
    server.send(400, "text/plain", uploadError.isEmpty() ? "Firmware upload incomplete\n" : uploadError); return;
  }
  server.send(200, "application/json", "{\"updated\":true,\"disarmed\":true,\"restarting\":true}");
  restartAt = millis() + 1000;
}

// Used once on the Mac, before any TV wiring, to verify the full network/UART path.
// Closing commissioning permanently disables this diagnostic endpoint.
void commissioningLoopback() {
  if (!authorized()) return;
  if (commissioned) {
    server.send(409, "text/plain", "Commissioning is closed\n");
    return;
  }
  String body = server.arg("plain");
  if (body != "1" && body != "0") {
    server.send(400, "text/plain", "Use 1 to enable internal loopback or 0 to close commissioning\n");
    return;
  }
  loopback = body == "1";
  if (uart_set_loop_back(UART_NUM_2, loopback) != ESP_OK) {
    server.send(500, "text/plain", "Could not set UART loopback\n");
    return;
  }
  if (!loopback) {
    commissioned = true;
    settings.putBool("commissioned", true);
  }
  server.send(200, "application/json", "{\"loopback\":" + String(loopback ? "true" : "false") + "}");
}

void setup() {
  Serial.begin(115200);
  // GPIO25 is ADC2: sample before Wi-Fi starts and before UART owns the pin.
  // This is an approximate voltage diagnostic, with no pull-up or output drive.
  analogReadResolution(12);
  analogSetPinAttenuation(RX_PIN, ADC_11db);
  for (int i = 0; i < 32; ++i) {
    const uint32_t mv = analogReadMilliVolts(RX_PIN);
    rxStartupMilliVolts += mv;
    rxStartupRaw += analogRead(RX_PIN);
    rxStartupMinMv = min(rxStartupMinMv, mv);
    rxStartupMaxMv = max(rxStartupMaxMv, mv);
    delay(1);
  }
  rxStartupMilliVolts /= 32;
  rxStartupRaw /= 32;
  tv.setRxBufferSize(8192);
  tv.begin(BAUD, SERIAL_8N1, RX_PIN, TX_PIN);
  // Keep the service-port receive line unbiased. Continuous console activity
  // appeared after the diagnostic pull-up; restore passive capture.
  gpio_set_pull_mode(GPIO_NUM_25, GPIO_FLOATING);
  settings.begin("tcl-bridge", false);
  commissioned = settings.getBool("commissioned", false);
  bool loadedProfile = false;
  if (settings.getBytesLength("seq-profile") == sizeof(profile)) {
    automation::Profile &saved = incomingProfile;
    settings.getBytes("seq-profile", &saved, sizeof(saved));
    if (automation::valid(saved)) { profile = saved; loadedProfile = true; }
  }
  const bool bootSequence = settings.getBool("seq-armed", false);
  uint8_t bootSeconds = settings.getUChar("enter", 0);
  // Consume the persistent ARM flag before the first UART byte. Never retry on reset.
  bool consumed = !bootSequence || settings.putBool("seq-armed", false) == 1;
  if (bootSeconds && settings.putUChar("enter", 0) != 1) bootSeconds = 0;
  interruptUntil = !bootSequence && bootSeconds ? millis() + bootSeconds * 1000 : 0;
  if (bootSequence && consumed && loadedProfile) {
    runner.start(profile, millis(), false);
    event("one-shot-boot-start");
  }
  xTaskCreatePinnedToCore(capture, "uart-capture", 4096, nullptr, 3, nullptr, 1);

  WiFi.setHostname("tcl-uart-bridge");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const char *headers[] = {"Authorization"};
  server.collectHeaders(headers, 1);
  server.on("/", HTTP_GET, [] {
    server.sendHeader("Cache-Control", "no-store");
    server.sendHeader("X-Frame-Options", "DENY");
    server.send_P(200, "text/html; charset=utf-8", CONTROL_PAGE);
  });
  server.on("/status", HTTP_GET, status);
  server.on("/rx", HTTP_GET, readUart);
  server.on("/tx", HTTP_POST, writeUart);
  server.on("/enter", HTTP_POST, [] { scheduleEnter(false); });
  server.on("/arm-next-boot", HTTP_POST, [] { scheduleEnter(true); });
  server.on("/commissioning-loopback", HTTP_POST, commissioningLoopback);
  server.on("/automation", HTTP_GET, automationStatus);
  server.on("/automation/config", HTTP_POST, configureSequence);
  server.on("/automation/start", HTTP_POST, startSequence);
  server.on("/automation/disarm", HTTP_POST, disarmSequence);
  server.on("/update", HTTP_POST, finishUpdate, firmwareUpload);
  server.onNotFound([] { server.send(404, "text/plain", "Not found\n"); });
  server.begin();
  Serial.println("TCL UART bridge: GPIO25 RX, GPIO26 TX, 115200 8N1; capture started.");
}

void loop() {
  runner.tick(millis(), [](const char *data, size_t n) { tv.write((const uint8_t *)data, n); },
              [](const char *name, int step) { event(name, step); });
  uint32_t now = millis();
  if (!runner.active() && interruptUntil && int32_t(interruptUntil - now) > 0 && now - lastEnter >= 100) {
    tv.write('\r'); lastEnter = now;
  }
  if (restartAt && int32_t(now - restartAt) >= 0) ESP.restart();
  static bool announced = false;
  static uint32_t lastRetry = 0;
  if (WiFi.status() == WL_CONNECTED) {
    if (!announced) {
      Serial.print("Wi-Fi connected; bridge IP: ");
      Serial.println(WiFi.localIP());
      if (MDNS.begin("tcl-uart-bridge")) MDNS.addService("http", "tcp", 8080);
      announced = true;
    }
    server.handleClient();
  } else {
    if (announced) {
      MDNS.end();
      announced = false;
    }
    if (millis() - lastRetry > 15000) {
      WiFi.reconnect();
      lastRetry = millis();
    }
  }
  delay(1);
}
