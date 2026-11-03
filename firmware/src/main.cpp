// Chương trình chính ESP32.
// Bước hiện tại: chỉ nhận lệnh từ laptop và in ra Serial, chưa điều khiển motor.
#include <Arduino.h>

#include "command_link.h"

const char* WIFI_SSID = "omni-robot";
const char* WIFI_PASSWORD = "omnirobot";   // tối thiểu 8 ký tự
const uint16_t UDP_PORT = 4210;
const uint32_t CMD_TIMEOUT_MS = 300;       // quá thời gian này không có lệnh -> dừng
const int LED_PIN = 2;                     // LED xanh trên bo DevKit

CommandLink comms(WIFI_SSID, WIFI_PASSWORD, UDP_PORT, CMD_TIMEOUT_MS);

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  comms.begin();
  Serial.printf("\nWiFi: %s  mật khẩu: %s  IP: %s  cổng UDP: %u\n",
                WIFI_SSID, WIFI_PASSWORD, WiFi.softAPIP().toString().c_str(), UDP_PORT);
}

void loop() {
  comms.poll();
  bool alive = comms.alive();
  Command c = comms.command();

  // LED sáng liên tục = đang nhận lệnh; nhấp nháy chậm = chờ laptop
  digitalWrite(LED_PIN, alive ? HIGH : (millis() / 500) % 2);

  // TODO bước sau: c -> động học omni -> PID -> motor

  static bool was_alive = false;
  if (was_alive && !alive) Serial.println("Mất lệnh quá 300 ms -> DỪNG");
  was_alive = alive;

  static uint32_t last_print = 0, last_packets = 0;
  if (millis() - last_print >= 1000) {
    uint32_t n = comms.packets();
    Serial.printf("máy kết nối: %d  gói/giây: %lu  vx=%.2f vy=%.2f w=%.2f\n",
                  comms.clients(), (unsigned long)(n - last_packets), c.vx, c.vy, c.w);
    last_packets = n;
    last_print = millis();
  }
}
