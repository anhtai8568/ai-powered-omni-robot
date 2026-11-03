// Chương trình chính ESP32: nhận lệnh (vx, vy, w) qua WiFi -> động học omni -> PID 4 bánh.
//
// Tinh chỉnh qua Serial (USB, không cần WiFi), KÊ ROBOT LÊN:
//   s            chạy kịch bản thử, in log 50 lần/giây:
//                "L <ms> <lệnh0> <đo0> <pwm0> ... <lệnh3> <đo3> <pwm3>"
//   g kp ki ff   đổi hệ số PID và tỉ lệ feedforward ngay lúc chạy (vd "g 0.6 4 1"), không cần nạp lại
#include <Arduino.h>

#include "command_link.h"
#include "kinematics.h"
#include "wheel.h"

const char* WIFI_SSID = "omni-robot";
const char* WIFI_PASSWORD = "omnirobot";  // tối thiểu 8 ký tự
const uint16_t UDP_PORT = 4210;
const uint32_t CMD_TIMEOUT_MS = 300;      // quá thời gian này không có lệnh -> dừng
const uint32_t CONTROL_PERIOD_US = 10000; // vòng điều khiển 100 Hz
const int LED_PIN = 2;                    // LED xanh trên bo DevKit

CommandLink comms(WIFI_SSID, WIFI_PASSWORD, UDP_PORT, CMD_TIMEOUT_MS);
Wheel wheels[4];

// Kịch bản thử: mỗi bước giữ một lệnh trong ms mili giây
struct Step {
  uint16_t ms;
  float vx, vy, w;
};
const Step TEST[] = {
    {1000, 0, 0, 0},      {2000, 0.3, 0, 0},  {2000, 0.8, 0, 0}, {1000, 0, 0, 0},
    {2000, -0.5, 0, 0},   {2000, 0, 0.5, 0},  {2000, 0, 0, 0.5}, {2000, 0.4, 0.4, 0},
    {1500, 0, 0, 0},
};
const int TEST_STEPS = sizeof(TEST) / sizeof(TEST[0]);
int test_step = -1;  // -1 = không chạy kịch bản
uint32_t test_step_start = 0;

void handle_serial() {
  static char line[48];
  static int len = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch != '\n' && ch != '\r') {
      if (len < (int)sizeof(line) - 1) line[len++] = ch;
      continue;
    }
    line[len] = '\0';
    len = 0;
    Gains& g = Wheel::gains;
    if (line[0] == 's') {
      test_step = 0;
      test_step_start = millis();
      Serial.printf("TEST kp=%.3f ki=%.3f ff=%.2f\n", g.kp, g.ki, g.ff);
    } else if (line[0] == 'g') {
      sscanf(line + 1, "%f %f %f", &g.kp, &g.ki, &g.ff);
      Serial.printf("GAINS kp=%.3f ki=%.3f ff=%.2f\n", g.kp, g.ki, g.ff);
    }
  }
}

// Lệnh hiện tại: kịch bản thử (nếu đang chạy) được ưu tiên hơn lệnh WiFi
Command current_command() {
  if (test_step < 0) return comms.command();
  while (test_step < TEST_STEPS && millis() - test_step_start >= TEST[test_step].ms) {
    test_step_start += TEST[test_step].ms;
    test_step++;
  }
  if (test_step >= TEST_STEPS) {
    test_step = -1;
    Serial.println("END");
    return Command{};
  }
  const Step& s = TEST[test_step];
  return Command{s.vx, s.vy, s.w};
}

void setup() {
  ESP32Encoder::useInternalWeakPullResistors = puType::none;  // encoder tự kéo mức (push-pull)
  for (int i = 0; i < 4; i++) wheels[i].begin(i);  // khởi tạo motor sớm nhất để motor đứng yên
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  comms.begin();
  Serial.printf("\nWiFi: %s  mật khẩu: %s  IP: %s  cổng UDP: %u\n", WIFI_SSID, WIFI_PASSWORD,
                WiFi.softAPIP().toString().c_str(), UDP_PORT);
}

void loop() {
  comms.poll();
  handle_serial();

  static uint32_t last_us = micros();
  uint32_t now = micros();
  if (now - last_us < CONTROL_PERIOD_US) return;
  float dt = (now - last_us) * 1e-6f;
  last_us = now;

  Command c = current_command();
  float t[4];
  inverse_kinematics(c.vx, c.vy, c.w, t);
  for (int i = 0; i < 4; i++) {
    bool was_stalled = wheels[i].stalled();
    wheels[i].set_target(t[i]);
    wheels[i].update(dt);
    if (!was_stalled && wheels[i].stalled()) Serial.printf("KẸT bánh %s -> ngắt đến khi nhả lệnh\n", WHEEL_NAMES[i]);
  }

  // Số liệu 4 bánh gửi kèm gói trả lời: "<muốn> <đo> <pwm>" x 4 (laptop ghi log)
  char tel[128];
  int n = 0;
  for (auto& w : wheels) n += snprintf(tel + n, sizeof(tel) - n, "%.3f %.3f %.3f ", w.target(), w.speed(), w.duty());
  comms.set_telemetry(tel);

  bool active = test_step >= 0 || comms.alive();
  digitalWrite(LED_PIN, active ? HIGH : (millis() / 500) % 2);  // sáng = đang chạy, nháy = chờ

  static uint32_t tick = 0;
  tick++;
  if (test_step >= 0 && tick % 2 == 0) {  // log 50 lần/giây khi chạy kịch bản
    Serial.printf("L %lu", (unsigned long)millis());
    for (auto& w : wheels) Serial.printf(" %.3f %.3f %.3f", w.goal(), w.speed(), w.duty());
    Serial.println();
  } else if (test_step < 0 && tick % 100 == 0) {  // trạng thái mỗi giây
    Serial.printf("máy kết nối: %d  vx=%.2f vy=%.2f w=%.2f  tốc độ bánh: %.2f %.2f %.2f %.2f\n",
                  comms.clients(), c.vx, c.vy, c.w, wheels[0].speed(), wheels[1].speed(),
                  wheels[2].speed(), wheels[3].speed());
  }
}
