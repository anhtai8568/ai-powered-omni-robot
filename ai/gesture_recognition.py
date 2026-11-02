"""
Nhận diện cử chỉ bàn tay bằng MediaPipe Hand Landmarker.

MediaPipe trả về 21 điểm khớp trên bàn tay (tọa độ chuẩn hóa 0..1):

        8   12  16  20        đầu ngón (TIP)
        7   11  15  19
        6   10  14  18        khớp giữa (PIP)
    4   5    9  13  17        gốc ngón (MCP)
    3
    2            0            0 = cổ tay
    1

Từ các điểm này ta tự phân loại cử chỉ bằng luật hình học (không cần train).

Xem thử:  python ai/gesture_recognition.py   (bấm q để thoát)
"""
import math
import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/latest/hand_landmarker.task")

WRIST = 0
# (đầu ngón, khớp giữa) của trỏ, giữa, áp út, út. Bỏ ngón cái vì khó đo ổn định.
FINGERS = {"index": (8, 6), "middle": (12, 10), "ring": (16, 14), "pinky": (20, 18)}
INDEX_MCP, INDEX_TIP = 5, 8
MIDDLE_MCP, MIDDLE_TIP = 9, 12

CONNECTIONS = [(c.start, c.end) for c in vision.HandLandmarksConnections.HAND_CONNECTIONS]


def ensure_model() -> Path:
    """Tải model về lần đầu chạy (~8 MB), các lần sau dùng file có sẵn."""
    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Đang tải model nhận diện tay về {MODEL_PATH} ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


class HandTracker:
    """Tìm 1 bàn tay trong ảnh, trả về 21 điểm theo pixel [(x, y), ...] hoặc None."""

    def __init__(self, min_confidence=0.6):
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ensure_model())),
            running_mode=vision.RunningMode.VIDEO,  # dùng thông tin khung trước để bám tay nhanh hơn
            num_hands=1,
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
        if not result.hand_landmarks:
            return None
        return [(p.x * w, p.y * h) for p in result.hand_landmarks[0]]

    def close(self):
        self._landmarker.close()


# ---------- phân loại cử chỉ ----------
def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def extended_fingers(pts):
    """Ngón duỗi = đầu ngón xa cổ tay hơn khớp giữa. Đúng với mọi góc xoay của bàn tay."""
    wrist = pts[WRIST]
    return {name for name, (tip, pip) in FINGERS.items()
            if _dist(pts[tip], wrist) > _dist(pts[pip], wrist) * 1.15}


def direction(base, tip):
    """Hướng của vector base -> tip trên màn hình: 'up' | 'down' | 'left' | 'right'."""
    dx, dy = tip[0] - base[0], tip[1] - base[1]
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"   # trục y của ảnh hướng xuống


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
        return "point_" + direction(pts[INDEX_MCP], pts[INDEX_TIP])
    if up == {"index", "middle"}:
        d = direction(pts[INDEX_MCP], pts[INDEX_TIP])
        if d in ("left", "right") and d == direction(pts[MIDDLE_MCP], pts[MIDDLE_TIP]):
            return "v_" + d
    return None


# ---------- vẽ ----------
def draw(frame, pts, label=None):
    """Vẽ khung xương bàn tay và tên cử chỉ lên frame (sửa trực tiếp)."""
    if pts is not None:
        for a, b in CONNECTIONS:
            cv2.line(frame, tuple(map(int, pts[a])), tuple(map(int, pts[b])), (255, 255, 255), 2)
        for p in pts:
            cv2.circle(frame, tuple(map(int, p)), 4, (0, 200, 255), -1)
    if label:
        cv2.putText(frame, label, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(frame, label, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 120), 2)
    return frame


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ai.camera import Camera

    cam = Camera().start()
    tracker = HandTracker()
    last, n, t0, fps = -1, 0, time.time(), 0.0
    try:
        while True:
            last, frame = cam.read(last)
            if frame is None:
                continue
            pts = tracker.detect(frame)
            draw(frame, pts, f"{classify(pts) or '-'}  {fps:.0f} fps")
            n += 1
            if time.time() - t0 >= 1:
                fps, n, t0 = n / (time.time() - t0), 0, time.time()
            cv2.imshow("Gesture", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        tracker.close()
        cam.stop()
        cv2.destroyAllWindows()
