"""
Tìm tối đa 2 bàn tay (MediaPipe Hand Landmarker) và biết tay nào là tay trái / phải của người dùng.

MediaPipe trả về 21 điểm khớp trên bàn tay (tọa độ chuẩn hóa 0..1):

        8   12  16  20        đầu ngón (TIP)
        7   11  15  19
        6   10  14  18        khớp giữa (PIP)
    4   5    9  13  17        gốc ngón (MCP)
    3
    2            0            0 = cổ tay
    1

Vai trò (bản 2): tay thuận điều khiển giao diện (ai/ui), tay không thuận lái robot (ai/drive).
File này chỉ lo phần chung: tìm tay, gán vai trò, hình học ngón tay, vẽ khung xương.
"""
import math
import time
import urllib.request
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/latest/hand_landmarker.task")

WRIST = 0
INDEX_MCP, INDEX_TIP = 5, 8
MIDDLE_MCP, MIDDLE_TIP = 9, 12
# (đầu ngón, khớp giữa) của trỏ, giữa, áp út, út. Bỏ ngón cái vì khó đo ổn định.
FINGERS = {"index": (8, 6), "middle": (12, 10), "ring": (16, 14), "pinky": (20, 18)}

CONNECTIONS = [(c.start, c.end) for c in vision.HandLandmarksConnections.HAND_CONNECTIONS]


@dataclass
class Hand:
    pts: list          # 21 điểm (x, y) theo pixel
    label: str         # "Left" | "Right" do MediaPipe đoán
    side: str = ""     # "left" | "right": tay của người dùng, sau khi RoleAssigner sửa cho ổn định


def ensure_model() -> Path:
    """Tải model về lần đầu chạy (~8 MB), các lần sau dùng file có sẵn."""
    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Đang tải model nhận diện tay về {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


class HandTracker:
    """Tìm tối đa 2 bàn tay trong ảnh. detect() trả về list[Hand] (có thể rỗng)."""

    def __init__(self, min_confidence=0.6):
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ensure_model())),
            running_mode=vision.RunningMode.VIDEO,  # dùng thông tin khung trước để bám tay nhanh hơn
            num_hands=2,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = 0

    def detect(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        # Chế độ VIDEO bắt buộc timestamp tăng dần
        ts = max(int(time.monotonic() * 1000), self._last_ts + 1)
        self._last_ts = ts
        result = self._landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
        return [Hand(pts=[(p.x * w, p.y * h) for p in pts], label=cats[0].category_name)
                for pts, cats in zip(result.hand_landmarks, result.handedness)]

    def close(self):
        self._landmarker.close()


class RoleAssigner:
    """Quyết định tay nào là tay trái / phải của người dùng, ổn định theo thời gian.

    Ảnh camera đã lật gương, nên tay trái của người dùng nằm bên trái ảnh.
    - 2 tay: tay nằm bên trái ảnh là tay trái (không tin nhãn của MediaPipe, vì nhãn đôi khi
      cho cả hai tay cùng một nhãn). Dùng luôn các khung này để kiểm tra nhãn có bị ngược không.
    - 1 tay: bỏ phiếu theo nhãn của MediaPipe trong VOTE_FRAMES khung gần nhất, nên vài khung nhãn
      nhầm không đổi vai. Tay vừa thấy ở khung có 2 tay thì giữ vai theo vị trí lúc đó.

    MediaPipe đoán nhãn như thể ảnh CHƯA lật gương. Ảnh của ta đã lật nên phải đổi Left <-> Right
    (đo trên máy thật: tay phải ở bên phải ảnh được gắn nhãn "Left"). Nếu thấy hai tay mà nhãn đã
    đổi vẫn luôn mâu thuẫn với vị trí thì tự đổi lại quy ước.
    """

    STICKY_PX = 150     # tay di chuyển ít hơn mức này giữa 2 khung thì coi là cùng một tay
    VOTE_FRAMES = 10

    def __init__(self, labels_flipped=True):
        self.flipped = labels_flipped
        self._last = {}                   # side -> vị trí cổ tay khung trước
        self._by_position = False         # khung trước gán vai theo vị trí (2 tay) hay theo nhãn
        self._votes = deque(maxlen=self.VOTE_FRAMES)
        self._calib = 0.0

    def _label_side(self, label):
        side = label.lower()
        if self.flipped:
            side = "left" if side == "right" else "right"
        return side

    def _calibrate(self, left_in_image, right_in_image):
        """Hai tay có nhãn khác nhau: nhãn (sau khi đổi) có khớp vị trí không?"""
        if left_in_image.label == right_in_image.label:
            return
        agree = self._label_side(left_in_image.label) == "left"
        self._calib = 0.95 * self._calib + 0.05 * (1.0 if agree else -1.0)
        if self._calib < -0.6:  # nhiều lần liên tiếp mâu thuẫn: quy ước đang sai
            self.flipped = not self.flipped
            self._calib = 0.0

    def assign(self, hands):
        if len(hands) >= 2:
            a, b = sorted(hands, key=lambda h: h.pts[WRIST][0])[:2]
            a.side, b.side = "left", "right"
            self._calibrate(a, b)
            hands = [a, b]
            self._by_position = True
            self._votes.clear()
        elif len(hands) == 1:
            h = hands[0]
            wrist = h.pts[WRIST]
            near = [(math.dist(p, wrist), side) for side, p in self._last.items()
                    if math.dist(p, wrist) < self.STICKY_PX]
            if not near:
                self._votes.clear()                       # tay mới xuất hiện
            elif self._by_position:                       # vừa tách ra từ khung 2 tay: giữ vai theo vị trí
                self._votes.extend([min(near)[1]] * self.VOTE_FRAMES)
            self._by_position = False
            self._votes.append(self._label_side(h.label))
            lefts = sum(v == "left" for v in self._votes)
            if lefts * 2 == len(self._votes):             # hòa: theo phiếu mới nhất
                h.side = self._votes[-1]
            else:
                h.side = "left" if lefts * 2 > len(self._votes) else "right"
        else:
            self._votes.clear()
            self._by_position = False
        self._last = {h.side: h.pts[WRIST] for h in hands}
        return hands


def split_roles(hands, dominant="right", drive_active=True):
    """-> (tay giao diện, tay lái): tay thuận điều khiển giao diện, tay còn lại lái robot (có thể None).

    drive_active=False (chế độ Thủ công, robot không lái bằng cử chỉ): không có tay lái. Tay nào đang
    thấy cũng là tay giao diện (ưu tiên tay thuận), nên chỉ cần một tay, không phụ thuộc đoán trái/phải."""
    ui = next((h for h in hands if h.side == dominant), None)
    drive = next((h for h in hands if h.side != dominant), None)
    if not drive_active:
        return (ui or drive), None
    return ui, drive


# ---------- hình học ngón tay ----------
def extended_fingers(pts):
    """Ngón duỗi = đầu ngón xa cổ tay hơn khớp giữa. Đúng với mọi góc xoay của bàn tay."""
    wrist = pts[WRIST]
    return {name for name, (tip, pip) in FINGERS.items()
            if math.dist(pts[tip], wrist) > math.dist(pts[pip], wrist) * 1.15}


# ---------- vẽ ----------
ROLE_COLORS = {"ui": (255, 190, 0), "drive": (80, 220, 120)}  # BGR


def draw_hand(frame, hand, role, label="", k=1.0):
    """Vẽ khung xương một bàn tay lên frame (sửa trực tiếp), màu theo vai trò."""
    color = ROLE_COLORS.get(role, (255, 255, 255))
    k = max(1.0, k)  # k > 1: khung lớn hơn 640 px, vẽ nét và chữ to lên cho cân
    for a, b in CONNECTIONS:
        cv2.line(frame, tuple(map(int, hand.pts[a])), tuple(map(int, hand.pts[b])), color, round(2 * k))
    for p in hand.pts:
        cv2.circle(frame, tuple(map(int, p)), round(4 * k), (0, 200, 255), -1)
    if label:
        x, y = map(int, hand.pts[WRIST])
        cv2.putText(frame, label, (x - round(40 * k), y + round(28 * k)), cv2.FONT_HERSHEY_SIMPLEX, 0.7 * k, (0, 0, 0), round(4 * k))
        cv2.putText(frame, label, (x - round(40 * k), y + round(28 * k)), cv2.FONT_HERSHEY_SIMPLEX, 0.7 * k, color, round(2 * k))
    return frame
