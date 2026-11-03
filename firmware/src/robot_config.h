// Cấu hình phần cứng, theo docs/pinout.png.
// Chỉ số bánh dùng trong toàn bộ firmware: 0 trước trái, 1 trước phải, 2 sau trái, 3 sau phải.
#pragma once
#include <Arduino.h>

struct MotorPins {
  uint8_t pwm, in1, in2;
};
struct EncoderPins {
  uint8_t a, b;
};

const char* const WHEEL_NAMES[4] = {"Trước trái", "Trước phải", "Sau trái", "Sau phải"};
const MotorPins MOTOR_PINS[4] = {{25, 26, 27}, {13, 23, 22}, {21, 19, 18}, {17, 16, 4}};
const EncoderPins ENCODER_PINS[4] = {{36, 39}, {34, 35}, {32, 33}, {14, 5}};
// Motor nối dây ngược (PWM dương làm bánh quay lùi) -> đảo dấu trong phần mềm
const bool MOTOR_INVERT[4] = {false, false, false, true};

// Encoder đếm ngược dấu (motor 2 bên lắp đối xứng). Đo bằng: pio run -e motor_test
const bool ENCODER_INVERT[4] = {false, true, false, true};

const int COUNTS_PER_REV = 8112;  // xung mỗi vòng bánh: 26 xung/kênh x4 x hộp số 78

// Lệnh 1.0 = MAX_CPS xung/giây. motor_test đo được tốc độ tối đa 4552..4869 xung/giây;
// lấy thấp hơn bánh chậm nhất để PID còn dư PWM mà bù.
const float MAX_CPS = 4300;

// Feedforward: PWM ~ FF_OFFSET + FF_SLOPE * tốc độ (chuẩn hóa). Khớp bình phương tối thiểu từ
// các điểm xác lập khi bánh lơ lửng (lệch <= 0.045 PWM). Motor rất phi tuyến: 44% PWM đã ra
// 80% tốc độ. Trên mặt đất có tải thì cần PWM cao hơn, phần thiếu do PI bù.
const float FF_OFFSET[4] = {0.076, 0.148, 0.055, 0.060};
const float FF_SLOPE[4] = {0.470, 0.594, 0.453, 0.464};

const uint32_t PWM_FREQ = 1000;  // L298N dùng transistor BJT, đóng cắt chậm: 1 kHz là hợp lý
const uint8_t PWM_BITS = 10;     // duty 0..1023
const uint16_t ENCODER_FILTER = 1000;  // lọc nhiễu PCNT, đơn vị 12.5 ns -> 12.5 µs
