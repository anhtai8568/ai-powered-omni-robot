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
STOP_GESTURES = {"fist", "palm"}


class GestureFilter:
    """Chống nhiễu: dừng có hiệu lực ngay, di chuyển phải thấy `hold` khung liên tiếp.

    AI thỉnh thoảng đoán sai 1-2 khung; nếu dùng thẳng thì robot giật cục.
    """

    def __init__(self, hold=4):
        self.hold = hold
        self._candidate = None
        self._count = 0
        self.stable = None

    def update(self, gesture):
        if gesture == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = gesture, 1
        if gesture in STOP_GESTURES or self._count >= self.hold:
            self.stable = gesture
        return self.stable


def to_command(gesture, speed=0.5):
    """Tên cử chỉ -> (vx, vy, w), mỗi giá trị trong -speed..speed."""
    vx, vy, w = COMMANDS.get(gesture, (0.0, 0.0, 0.0))
    return vx * speed, vy * speed, w * speed
