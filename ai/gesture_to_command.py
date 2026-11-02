"""
Chuyển cử chỉ thành lệnh robot (vx, vy, w), quy ước ROS:
  vx > 0 tiến, vy > 0 sang trái, w > 0 xoay ngược chiều kim đồng hồ (xoay trái).

Ảnh camera đã lật gương, nên "trái" trên màn hình là bên trái của người điều khiển.
"""

# Mỗi cử chỉ -> hướng (vx, vy, w). Cử chỉ không có trong bảng (fist, palm, None) -> dừng.
COMMANDS = {
    "point_up":    (1.0, 0.0, 0.0),
    "point_down":  (-1.0, 0.0, 0.0),
    "point_left":  (0.0, 1.0, 0.0),
    "point_right": (0.0, -1.0, 0.0),
    "v_left":      (0.0, 0.0, 1.0),
    "v_right":     (0.0, 0.0, -1.0),
}


class GestureFilter:
    """Chống nhiễu: một cử chỉ chỉ được chấp nhận khi thấy đủ số khung liên tiếp.

    - Di chuyển: `hold` khung (4 khung ~ 0.13 s ở 30 fps). AI thỉnh thoảng đoán
      sai 1-2 khung; nếu dùng thẳng thì robot giật cục.
    - Dừng (nắm tay, xòe tay, mất tay): `stop_hold` khung (6 khung ~ 0.2 s).
      Lâu hơn di chuyển vì khi chuyển từ chỉ lên sang chỉ xuống, bàn tay thường
      đi qua tư thế nắm/xòe hoặc mất dấu trong chốc lát. Nắm tay có chủ đích thì
      giữ lâu hơn thế. Cần dừng ngay thì dùng nút Dừng khẩn cấp / phím Space.
    """

    def __init__(self, hold=4, stop_hold=6):
        self.hold = hold
        self.stop_hold = stop_hold
        self._candidate = None
        self._count = 0
        self.stable = None

    def update(self, gesture):
        if gesture == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = gesture, 1
        need = self.hold if gesture in COMMANDS else self.stop_hold
        if self._count >= need:
            self.stable = gesture
        return self.stable


def to_command(gesture, speed=0.5):
    """Tên cử chỉ -> (vx, vy, w), mỗi giá trị trong -speed..speed."""
    vx, vy, w = COMMANDS.get(gesture, (0.0, 0.0, 0.0))
    return vx * speed, vy * speed, w * speed
