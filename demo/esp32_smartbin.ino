#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- UPDATE THESE ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
// Use the public ngrok URL or your public server endpoint, e.g. "https://abcd1234.ngrok.io"
const char* serverUrl = "https://REPLACE_WITH_YOUR_PUBLIC_URL"; // no trailing slash
const char* binId = "smartbin-01";
// Threshold to treat as FULL (percent)
const int FULL_THRESHOLD = 95;
// ----------------------

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected, IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // --- Simulate a sensor fill level for demo ---
  // Replace this with your real sensor reading (ultrasonic / load cell).
  static int simulated = 0;
  simulated = (simulated + 10) % 110; // cycles 0..100
  int fillLevel = simulated;
  Serial.printf("Fill level: %d%%\n", fillLevel);

  if (fillLevel >= FULL_THRESHOLD) {
    Serial.println("Detected FULL, sending notification to backend...");
    sendStatusToBackend(fillLevel);
    // Wait longer after sending to avoid spamming; in real device you'd wait until state changes or use debounce.
    delay(60 * 1000); // 1 minute
  } else {
    delay(5000);
  }
}

void sendStatusToBackend(int fillLevel) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, abort send");
    return;
  }

  HTTPClient http;
  String url = String(serverUrl) + "/api/bin-status";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["bin_id"] = binId;
  doc["status"] = "FULL";
  doc["fill_level"] = fillLevel;
  String body;
  serializeJson(doc, body);

  int httpCode = http.POST(body);
  Serial.printf("POST %s -> code: %d\n", url.c_str(), httpCode);
  if (httpCode > 0) {
    String resp = http.getString();
    Serial.println("Response: " + resp);
  } else {
    Serial.printf("POST failed, error: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();
}
