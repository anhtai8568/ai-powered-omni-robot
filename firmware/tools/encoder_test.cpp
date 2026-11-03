// Công cụ đo encoder: đếm xung 4 bánh và in ra Serial.
//
// Nạp:  pio run -e encoder_test -t upload && pio device monitor
// Cách đo số xung mỗi vòng bánh: gõ r (reset), quay tay 1 bánh đúng 10 vòng theo
// chiều TIẾN, đọc số đếm của bánh đó rồi chia 10.
// Số dương = bánh quay tiến đếm lên; nếu âm thì đổi chiều trong firmware chính.
//
// Giải mã quadrature x4: mỗi lần kênh A hoặc B đổi mức, đọc cả hai rồi tra bảng
// (trạng thái cũ, trạng thái mới) -> +1 / -1 / 0. Nhiễu ngắn làm trạng thái không
// đổi -> 0, nên không đếm sai.
#include <Arduino.h>

struct Encoder {
  const char* name;
  uint8_t pin_a, pin_b;
  volatile long count;
  volatile uint8_t state;
  volatile uint32_t errors;  // nhảy 2 trạng thái 1 lần = mất xung (quay quá nhanh / nhiễu)
};

Encoder enc[4] = {
    {"Trước trái", 36, 39, 0, 0, 0},
    {"Trước phải", 34, 35, 0, 0, 0},
    {"Sau trái", 32, 33, 0, 0, 0},
    {"Sau phải", 14, 5, 0, 0, 0},
};

// Bảng chuyển trạng thái, chỉ số = (cũ << 2) | mới, mỗi trạng thái = (A << 1) | B
const int8_t QEM[16] = {0, -1, 1, 2, 1, 0, 2, -1, -1, 2, 0, 1, 2, 1, -1, 0};

void IRAM_ATTR on_edge(void* arg) {
  Encoder* e = (Encoder*)arg;
  uint8_t now = (digitalRead(e->pin_a) << 1) | digitalRead(e->pin_b);
  int8_t d = QEM[(e->state << 2) | now];
  if (d == 2) e->errors = e->errors + 1;
  else e->count = e->count + d;
  e->state = now;
}

void setup() {
  Serial.begin(115200);
  for (auto& e : enc) {
    // GPIO 34-39 không có điện trở kéo lên trong; các chân khác thì bật lên
    pinMode(e.pin_a, e.pin_a >= 34 ? INPUT : INPUT_PULLUP);
    pinMode(e.pin_b, e.pin_b >= 34 ? INPUT : INPUT_PULLUP);
    e.state = (digitalRead(e.pin_a) << 1) | digitalRead(e.pin_b);
    attachInterruptArg(e.pin_a, on_edge, &e, CHANGE);
    attachInterruptArg(e.pin_b, on_edge, &e, CHANGE);
  }
  Serial.println("\nĐo encoder. Gõ r + Enter để reset số đếm.");
}

void loop() {
  if (Serial.available() && Serial.read() == 'r') {
    for (auto& e : enc) {
      e.count = 0;
      e.errors = 0;
    }
    Serial.println("--- reset ---");
  }
  static uint32_t last = 0;
  if (millis() - last >= 500) {
    last = millis();
    for (auto& e : enc) {
      Serial.printf("%s: %6ld (A=%d B=%d lỗi=%lu)   ", e.name, e.count,
                    digitalRead(e.pin_a), digitalRead(e.pin_b), (unsigned long)e.errors);
    }
    Serial.println();
  }
}
