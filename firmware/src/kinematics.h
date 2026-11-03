// Động học ngược robot omni 4 bánh chéo 45° (kiểu X): (vx, vy, w) -> tốc độ 4 bánh.
//
// Quy ước ROS: vx > 0 tiến, vy > 0 sang trái, w > 0 xoay trái (ngược chiều kim đồng hồ).
// Tốc độ bánh dương = bánh quay về phía trước. Mỗi bánh đẩy theo đường chéo, ví dụ bánh
// trước trái đẩy chéo "tiến + sang phải", nên muốn sang trái thì bánh đó phải quay lùi.
#pragma once
#include <math.h>

// out theo thứ tự: trước trái, trước phải, sau trái, sau phải. Mỗi giá trị trong -1..1.
inline void inverse_kinematics(float vx, float vy, float w, float out[4]) {
  out[0] = vx - vy - w;
  out[1] = vx + vy + w;
  out[2] = vx + vy - w;
  out[3] = vx - vy + w;
  // Nếu có bánh vượt 1 thì thu nhỏ cả 4 cùng tỉ lệ: giữ đúng hướng đi, chỉ chậm lại
  float m = 1.0f;
  for (int i = 0; i < 4; i++) m = fmaxf(m, fabsf(out[i]));
  for (int i = 0; i < 4; i++) out[i] /= m;
}
