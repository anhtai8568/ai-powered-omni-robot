"""
Con trỏ điều khiển giao diện bằng tay thuận.

Tư thế của tay thuận (tính từ các ngón duỗi, xem ai/hands.py):
  point  chỉ ngón trỏ          -> con trỏ di chuyển; trình duyệt giữ yên để click (dwell)
  click  ngón trỏ + ngón giữa  -> bấm; giữ rồi di chuyển là kéo
  idle   mọi tư thế khác       -> con trỏ ẩn, không bấm được (đặt tay nghỉ không click nhầm)
  none   không thấy tay

Vị trí gửi đi là tọa độ chuẩn hóa 0..1 trong KHUNG CAMERA (x, y), nên trình duyệt đặt con trỏ đúng
chỗ đầu ngón trỏ trên hình camera. Có thêm điểm tác động (ax, ay): giống (x, y) khi chỉ trỏ, còn
khi bấm thì giữ ở chỗ ngón trỏ đứng TRƯỚC lúc duỗi ngón giữa, để bấm trúng nút dù đầu ngón trỏ xê dịch.

File này chỉ lo phần thị giác: vị trí con trỏ (đã lọc mượt) và tư thế ổn định. Phần tương tác
(rê, giữ yên để click, kéo thanh trượt, thẻ thông số) nằm ở web/static/handcursor.js, vì chỉ
trình duyệt biết phần tử nào đang nằm dưới con trỏ.
"""
import math
from collections import deque

from ai.hands import INDEX_TIP, extended_fingers


def ui_pose(pts):
    """21 điểm -> 'point' | 'click' | 'idle'."""
    up = extended_fingers(pts)
    if up == {"index"}:
        return "point"
    if up == {"index", "middle"}:
        return "click"
    return "idle"


class OneEuro:
    """Bộ lọc One Euro: tay đứng yên thì lọc mạnh (hết rung), tay di nhanh thì lọc nhẹ (không trễ).

    cutoff = min_cutoff + beta * tốc_độ. Đơn vị vị trí là chuẩn hóa 0..1 nên beta lớn.
    """

    def __init__(self, min_cutoff=1.0, beta=8.0, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.reset()

    def reset(self):
        self._x = self._dx = self._t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self._x is None or t <= self._t:
            self._x, self._dx, self._t = x, 0.0, t
            return x
        dt = t - self._t
        dx = (x - self._x) / dt
        self._dx += self._alpha(self.d_cutoff, dt) * (dx - self._dx)
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        self._x += self._alpha(cutoff, dt) * (x - self._x)
        self._t = t
        return self._x


class Cursor:
    FREEZE_BACK = 0.2   # giây: khi bắt đầu click, lấy vị trí của trước đó chừng này (trước khi ngón giữa làm lệch đầu ngón trỏ)
    OFFSET_TAU = 0.15   # giây: sau khi nhả click, độ lệch giữ lại tan dần để điểm tác động không giật

    def __init__(self, region=1.0, cy=0.5, debounce=3, lost_grace=0.3):
        """region: phần khung camera (theo mỗi chiều) ứng với toàn bộ màn hình. 1.0 = con trỏ nằm đúng
        đầu ngón tay trên hình. Nhỏ hơn = nhạy hơn (tay đi ít) nhưng con trỏ không còn trùng đầu ngón tay.
        cy: độ cao tâm vùng trong khung (0 trên, 1 dưới)."""
        self.region, self.cy = region, cy
        self.debounce, self.lost_grace = debounce, lost_grace
        self._fx, self._fy = OneEuro(), OneEuro()
        self.reset()

    def reset(self):
        self.pose = "none"
        self.x = self.y = 0.5       # vị trí con trỏ = đầu ngón trỏ (đã lọc mượt)
        self.ax = self.ay = 0.5     # điểm tác động (khi bấm: chỗ ngón trỏ đứng trước lúc duỗi ngón giữa)
        self._cand, self._count = "none", 0
        self._hist = deque()          # (t, x, y) vị trí đã lọc khi đang ở tư thế point
        self._off = (0.0, 0.0)
        self._last_t = None
        self._seen_t = -1e9
        self._fx.reset()
        self._fy.reset()

    def _map(self, p, w, h):
        u = (p[0] / w - 0.5) / self.region + 0.5
        v = (p[1] / h - self.cy) / self.region + 0.5
        return min(1.0, max(0.0, u)), min(1.0, max(0.0, v))

    def update(self, pts, w, h, t):
        """pts: 21 điểm của tay thuận (hoặc None), w/h: kích thước ảnh, t: thời gian (giây)."""
        if pts is None:
            if self.pose != "none" and t - self._seen_t > self.lost_grace:
                self.reset()
            return self.state()
        self._seen_t = t

        raw = ui_pose(pts)
        if raw == self._cand:
            self._count += 1
        else:
            self._cand, self._count = raw, 1
        prev = self.pose
        if self._count >= self.debounce:
            self.pose = raw

        u, v = self._map(pts[INDEX_TIP], w, h)
        sx, sy = self._fx(u, t), self._fy(v, t)
        dt =(t - self._last_t) if self._last_t is not None else 0.0
        self._last_t = t

        if self.pose == "point":
            self._hist.append((t, sx, sy))
        while self._hist and t - self._hist[0][0] > 0.6:
            self._hist.popleft()

        if prev != "click" and self.pose == "click" and self._hist:
            # Vừa bắt đầu click: đầu ngón trỏ đã xê dịch do duỗi ngón giữa. Lấy vị trí trước đó
            # FREEZE_BACK giây làm gốc, rồi giữ độ lệch này suốt lúc click (kéo vẫn đi theo tay).
            old = [e for e in self._hist if t - e[0] >= self.FREEZE_BACK]
            _, ax, ay = old[-1] if old else self._hist[0]
            self._off = (ax - sx, ay - sy)
        elif self.pose != "click":
            k = math.exp(-dt / self.OFFSET_TAU) if dt > 0 else 1.0
            self._off = (self._off[0] * k, self._off[1] * k)

        self.x, self.y = sx, sy
        self.ax = min(1.0, max(0.0, sx + self._off[0]))
        self.ay = min(1.0, max(0.0, sy + self._off[1]))
        return self.state()

    def state(self):
        return {"pose": self.pose, "x": round(self.x, 4), "y": round(self.y, 4),
                "ax": round(self.ax, 4), "ay": round(self.ay, 4)}
