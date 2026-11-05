"""
Phân loại cử chỉ lái robot (tay không thuận) từ 21 điểm bàn tay, bằng luật hình học, không cần train.

Cử chỉ: fist, palm, point_<8 hướng>, v_left, v_right. Chuyển cử chỉ thành lệnh: ai/drive/command.py.
"""
import math

from ai.hands import INDEX_MCP, INDEX_TIP, MIDDLE_MCP, MIDDLE_TIP, extended_fingers

DIRECTIONS = ["right", "up_right", "up", "up_left", "left", "down_left", "down", "down_right"]


def direction(base, tip, sectors=8):
    """Hướng của vector base -> tip trên màn hình, làm tròn về 8 (hoặc 4) hướng.

    8 hướng: mỗi hướng chiếm một góc 45° (±22.5°), vd chỉ ở 30° -> 'up_right'.
    4 hướng: chỉ 'right' | 'up' | 'left' | 'down', mỗi hướng ±45°.
    """
    # Trục y của ảnh hướng xuống, nên đổi dấu dy để góc tính theo kiểu toán học (lên = 90°)
    angle = math.degrees(math.atan2(-(tip[1] - base[1]), tip[0] - base[0]))
    if sectors == 8:
        return DIRECTIONS[round(angle / 45) % 8]
    return DIRECTIONS[round(angle / 90) % 4 * 2]


def classify(pts):
    """21 điểm -> tên cử chỉ, hoặc None nếu không khớp cử chỉ nào."""
    if pts is None:
        return None
    up = extended_fingers(pts)
    if not up:
        return "fist"
    if up == {"index", "middle", "ring", "pinky"}:
        return "palm"
    if up == {"index"}:
        return "point_" + direction(pts[INDEX_MCP], pts[INDEX_TIP], 8)
    if up == {"index", "middle"}:
        d = direction(pts[INDEX_MCP], pts[INDEX_TIP], 4)
        if d in ("left", "right") and d == direction(pts[MIDDLE_MCP], pts[MIDDLE_TIP], 4):
            return "v_" + d
    return None
