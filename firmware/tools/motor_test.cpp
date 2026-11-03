// Nhận diện phần cứng motor + encoder. KÊ ROBOT LÊN, BÁNH KHÔNG CHẠM ĐẤT.
//
// Nạp:  pio run -e motor_test -t upload, mở Serial Monitor rồi gõ t để bắt đầu.
// Đã áp MOTOR_INVERT: PWM dương phải làm MỌI bánh quay tiến.
// Gõ 1..4 để chạy riêng 1 bánh +60% trong 3 s (1 trước trái, 2 trước phải, 3 sau trái, 4 sau phải),
// in số xung của cả 4 encoder.
//
// Giai đoạn A (người quan sát, ~16 s): lần lượt đầu ra motor 0..3 quay +40% trong 2 s, nghỉ 2 s.
//   -> nhìn xem bánh nào quay, quay tiến hay lùi.
// Giai đoạn B (tự đo, ~40 s): với từng đầu ra motor
//   - encoder nào chạy, đếm lên hay xuống khi PWM dương  (tự dò cặp motor-encoder)
//   - PWM tối thiểu để bánh bắt đầu quay                  (vùng chết)
//   - tốc độ tối đa tiến / lùi, đơn vị xung/giây
// Kết quả in lại mỗi 3 giây.
#include <ESP32Encoder.h>

#include "../src/motor.h"

Motor motor[4];
ESP32Encoder enc[4];

struct Result {
  int encoder = -1;    // encoder nào phản hồi
  int sign = 0;        // +1: PWM dương -> encoder đếm lên
  float deadband = 0;  // PWM nhỏ nhất làm bánh quay
  float max_fwd = 0, max_rev = 0;  // xung/giây ở PWM +100% / -100%
};
Result res[4];

void stop_all() {
  for (auto& m : motor) m.set(0);
}

int64_t counts[4];
void snapshot() {
  for (int j = 0; j < 4; j++) counts[j] = enc[j].getCount();
}
int64_t delta(int j) { return enc[j].getCount() - counts[j]; }

// Chạy motor i ở duty trong ms; đo tốc độ (xung/giây) của encoder j ở nửa sau (bỏ lúc tăng tốc)
float run_and_measure(int i, int j, float duty, uint32_t ms) {
  motor[i].set(duty);
  delay(ms / 2);
  int64_t c0 = enc[j].getCount();
  delay(ms / 2);
  float cps = (enc[j].getCount() - c0) * 1000.0f / (ms / 2);
  motor[i].set(0);
  delay(800);  // chờ bánh dừng hẳn
  return cps;
}

void run_test() {
  stop_all();
  for (int s = 5; s > 0; s--) {
    Serial.printf("Bắt đầu sau %d giây. Robot phải được kê lên!\n", s);
    delay(1000);
  }

  Serial.println("== Giai đoạn A: quan sát (mỗi đầu ra +40% trong 2 s) ==");
  for (int i = 0; i < 4; i++) {
    Serial.printf("Đầu ra motor %d (%s) đang quay +40%%\n", i, WHEEL_NAMES[i]);
    snapshot();
    motor[i].set(0.4f);
    delay(2000);
    motor[i].set(0);
    // encoder nào chạy nhiều nhất là encoder của motor này
    int best = 0;
    for (int j = 1; j < 4; j++)
      if (llabs(delta(j)) > llabs(delta(best))) best = j;
    if (llabs(delta(best)) > 50) {
      res[i].encoder = best;
      res[i].sign = delta(best) > 0 ? 1 : -1;
    }
    delay(2000);
  }

  Serial.println("== Giai đoạn B: tự đo ==");
  for (int i = 0; i < 4; i++) {
    int j = res[i].encoder;
    if (j < 0) continue;
    // Vùng chết: tăng PWM từ 0 tới khi bánh quay đều (> 200 xung/giây)
    for (float d = 0.0f; d <= 0.8f; d += 0.02f) {
      motor[i].set(d);
      delay(150);
      int64_t c0 = enc[j].getCount();
      delay(100);
      if (llabs(enc[j].getCount() - c0) * 10 > 200) {
        res[i].deadband = d;
        break;
      }
    }
    motor[i].set(0);
    delay(800);
    res[i].max_fwd = run_and_measure(i, j, 1.0f, 2000) * res[i].sign;
    res[i].max_rev = run_and_measure(i, j, -1.0f, 2000) * res[i].sign;
    Serial.printf("Đo xong đầu ra %d\n", i);
  }
  stop_all();
}

void print_results() {
  Serial.println("\n== KẾT QUẢ ==");
  for (int i = 0; i < 4; i++) {
    const Result& r = res[i];
    if (r.encoder < 0) {
      Serial.printf("motor %d (%s): KHÔNG encoder nào chạy\n", i, WHEEL_NAMES[i]);
      continue;
    }
    Serial.printf("motor %d (%s): encoder %d (%s) dấu %+d | vùng chết %.2f | max tiến %.0f, lùi %.0f xung/giây\n",
                  i, WHEEL_NAMES[i], r.encoder, WHEEL_NAMES[r.encoder], r.sign, r.deadband, r.max_fwd,
                  r.max_rev);
  }
}

void setup() {
  for (int i = 0; i < 4; i++) motor[i].begin(MOTOR_PINS[i], MOTOR_INVERT[i]);  // dừng motor sớm nhất
  Serial.begin(115200);
  ESP32Encoder::useInternalWeakPullResistors = puType::none;  // encoder tự kéo mức (push-pull)
  for (int j = 0; j < 4; j++) {
    enc[j].attachFullQuad(ENCODER_PINS[j].a, ENCODER_PINS[j].b);
    enc[j].setFilter(ENCODER_FILTER);
  }
  Serial.println("Sẵn sàng (robot phải được kê lên). Gõ 1-4 chạy từng bánh, t để test đầy đủ.");
}

void loop() {
  static bool done = false;
  int c = Serial.available() ? Serial.read() : -1;
  if (c == 't') {
    run_test();
    done = true;
  } else if (c >= '1' && c <= '4') {
    int i = c - '1';
    Serial.printf("Chạy riêng bánh %d (%s) +60%% trong 3 s...\n", i + 1, WHEEL_NAMES[i]);
    snapshot();
    motor[i].set(0.6f);
    delay(3000);
    motor[i].set(0);
    for (int j = 0; j < 4; j++) Serial.printf("  encoder %d (%s): %+lld xung\n", j, WHEEL_NAMES[j], delta(j));
  }
  static uint32_t last = 0;
  if (done && millis() - last >= 3000) {
    last = millis();
    print_results();
  }
}
