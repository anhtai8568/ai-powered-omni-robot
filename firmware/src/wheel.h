// Một bánh: motor + encoder + bộ điều khiển tốc độ.
//
// PWM = feedforward (đoán trước PWM cần dùng, từ đường thẳng đo được trong robot_config.h)
//     + Kp * sai số + tích phân (Ki * tổng sai số theo thời gian)
// Feedforward làm bánh phản ứng ngay; PI sửa phần còn sai (motor khác nhau, ma sát, pin yếu).
// Tốc độ dùng đơn vị chuẩn hóa: 1.0 = MAX_CPS xung/giây.
#pragma once
#include <ESP32Encoder.h>

#include "motor.h"

struct Gains {
  // Tinh chỉnh khi bánh lơ lửng (kịch bản "s"): sai số xác lập 0.2-1.2%, vọt lố 0.04-0.07
  // (bánh trước phải 0.14 do ma sát tĩnh lớn). Trên mặt đất nên chạy lại "s" để kiểm tra.
  float kp = 0.8f;
  float ki = 6.0f;
  float ff = 1.0f;  // tỉ lệ feedforward (0 = tắt, 1 = dùng đủ đường thẳng đo được)
};

const float MAX_WHEEL_ACCEL = 4.0f;  // tốc độ muốn đổi tối đa 4.0/giây (0 -> 0.8 trong 0.2 s)
const float STALL_SECONDS = 0.7f;    // PWM kịch mà bánh đứng yên lâu hơn mức này -> ngắt (bảo vệ kẹt)

class Wheel {
 public:
  inline static Gains gains;

  void begin(int idx) {
    idx_ = idx;
    motor_.begin(MOTOR_PINS[idx], MOTOR_INVERT[idx]);
    enc_.attachFullQuad(ENCODER_PINS[idx].a, ENCODER_PINS[idx].b);
    enc_.setFilter(ENCODER_FILTER);
    last_count_ = enc_.getCount();
  }

  void set_target(float t) { goal_ = constrain(t, -1.0f, 1.0f); }

  // Gọi đều đặn mỗi dt giây
  void update(float dt) {
    // Tốc độ muốn tiến dần về lệnh, không nhảy bậc (giảm giật và giảm vọt lố)
    float step = MAX_WHEEL_ACCEL * dt;
    target_ += constrain(goal_ - target_, -step, step);

    int64_t c = enc_.getCount();
    float cps = (c - last_count_) / dt;
    last_count_ = c;
    if (ENCODER_INVERT[idx_]) cps = -cps;
    speed_ += 0.3f * (cps / MAX_CPS - speed_);  // lọc thông thấp: 1 xung trong 10 ms = 2% tốc độ, rất nhiễu

    if (fabsf(target_) < 0.01f && fabsf(goal_) < 0.01f) {  // dừng hẳn: thả motor, xóa tích phân
      integral_ = 0;
      duty_ = 0;
      stalled_ = false;  // lệnh về 0 -> cho phép chạy lại sau khi bị ngắt vì kẹt
      motor_.set(0);
      return;
    }
    // Bảo vệ kẹt: PWM gần kịch mà bánh gần như đứng yên (húc tường, kẹt, mất nguồn motor)
    // -> dòng kẹt làm nóng motor và L298N. Ngắt bánh đến khi lệnh về 0.
    stall_time_ = (fabsf(duty_) >= 0.95f && fabsf(speed_) < 0.05f) ? stall_time_ + dt : 0;
    if (stall_time_ > STALL_SECONDS) stalled_ = true;
    if (stalled_) {
      integral_ = 0;
      duty_ = 0;
      motor_.set(0);
      return;
    }
    float err = target_ - speed_;
    float ff = feedforward(target_);
    float u = ff + gains.kp * err + integral_;
    // Chống tích phân bị dồn:
    // - đang tăng/giảm tốc (tốc độ muốn chưa tới lệnh): không cộng tích phân, nếu không phần
    //   cộng dồn này làm bánh vọt quá tốc độ muốn khi tới nơi. Đã tới lệnh thì luôn cộng, kể cả
    //   sai số lớn (bánh nặng cần tích phân bù phần feedforward thiếu).
    // - PWM đã kịch mà sai số còn đẩy tiếp cùng chiều: cộng thêm cũng vô ích
    bool ramping = target_ != goal_;
    bool saturated = (u >= 1.0f && err > 0) || (u <= -1.0f && err < 0);
    if (!ramping && !saturated) integral_ += gains.ki * err * dt;
    duty_ = constrain(ff + gains.kp * err + integral_, -1.0f, 1.0f);
    motor_.set(duty_);
  }

  void stop() {
    goal_ = 0;
    target_ = 0;
    integral_ = 0;
    duty_ = 0;
    motor_.set(0);
  }

  float goal() const { return goal_; }
  float target() const { return target_; }
  bool stalled() const { return stalled_; }
  float speed() const { return speed_; }
  float duty() const { return duty_; }

 private:
  // PWM ước lượng để đạt tốc độ t, theo đường thẳng đo riêng cho từng bánh
  float feedforward(float t) const {
    return copysignf(gains.ff * (FF_OFFSET[idx_] + FF_SLOPE[idx_] * fabsf(t)), t);
  }

  int idx_ = 0;
  Motor motor_;
  ESP32Encoder enc_;
  int64_t last_count_ = 0;
  float goal_ = 0;    // lệnh nhận được
  float target_ = 0;  // tốc độ muốn sau giới hạn gia tốc (tiến dần về goal_)
  float speed_ = 0, duty_ = 0, integral_ = 0;
  float stall_time_ = 0;
  bool stalled_ = false;
};
