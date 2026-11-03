// Điều khiển 1 motor qua L298N: chân PWM (ENA/ENB) quyết định công suất, IN1/IN2 quyết định chiều.
#pragma once
#include "robot_config.h"

class Motor {
 public:
  // invert = true khi motor nối dây ngược: phần mềm tự đảo dấu, PWM dương luôn là quay tiến
  void begin(const MotorPins& p, bool invert = false) {
    pins_ = p;
    invert_ = invert;
    pinMode(p.in1, OUTPUT);
    pinMode(p.in2, OUTPUT);
    digitalWrite(p.in1, LOW);
    digitalWrite(p.in2, LOW);
    ledcAttach(p.pwm, PWM_FREQ, PWM_BITS);
    ledcWrite(p.pwm, 0);
  }

  // duty trong -1..1: dấu là chiều quay, độ lớn là công suất. 0 = thả trôi (cả IN về LOW).
  void set(float duty) {
    duty = constrain(invert_ ? -duty : duty, -1.0f, 1.0f);
    digitalWrite(pins_.in1, duty > 0);
    digitalWrite(pins_.in2, duty < 0);
    ledcWrite(pins_.pwm, (uint32_t)(fabsf(duty) * ((1 << PWM_BITS) - 1)));
  }

 private:
  MotorPins pins_{};
  bool invert_ = false;
};
