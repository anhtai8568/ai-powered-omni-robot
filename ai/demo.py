"""
Xem thử AI nhận hai tay: python ai/demo.py   (bấm q để thoát)

Tay thuận (mặc định tay phải) màu xanh dương = điều khiển giao diện, hiện tư thế con trỏ.
Tay không thuận màu xanh lá = lái robot, hiện cử chỉ lái. Vòng tròn trắng là vị trí con trỏ.
Thêm tham số left để đổi sang tay thuận trái:  python ai/demo.py left
"""
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai.camera import Camera  # noqa: E402
from ai.drive.command import GestureFilter  # noqa: E402
from ai.drive.gestures import classify  # noqa: E402
from ai.hands import HandTracker, RoleAssigner, draw_hand, split_roles  # noqa: E402
from ai.ui.cursor import Cursor  # noqa: E402

dominant = "left" if "left" in sys.argv[1:] else "right"
cam = Camera().start()
tracker, roles, cursor, gestures = HandTracker(), RoleAssigner(), Cursor(), GestureFilter()
last, n, t0, fps = -1, 0, time.time(), 0.0
try:
    while True:
        last, frame = cam.read(last)
        if frame is None:
            continue
        h, w = frame.shape[:2]
        ui_hand, drive_hand = split_roles(roles.assign(tracker.detect(frame)), dominant)
        gesture = gestures.update(classify(drive_hand.pts if drive_hand else None))
        cur = cursor.update(ui_hand.pts if ui_hand else None, w, h, time.monotonic())
        if ui_hand:
            draw_hand(frame, ui_hand, "ui", f"UI {cur['pose']}")
        if drive_hand:
            draw_hand(frame, drive_hand, "drive", f"DRIVE {gesture or '-'}")
        if cur["pose"] in ("point", "click"):  # vị trí con trỏ chiếu ngược về khung camera
            r = cursor.region
            px = int(((cur["x"] - 0.5) * r + 0.5) * w)
            py = int(((cur["y"] - 0.5) * r + cursor.cy) * h)
            cv2.circle(frame, (px, py), 14 if cur["pose"] == "point" else 8, (255, 255, 255), 3)
        n += 1
        if time.time() - t0 >= 1:
            fps, n, t0 = n / (time.time() - t0), 0, time.time()
        cv2.putText(frame, f"{fps:.0f} fps  tay thuan: {dominant}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Hands", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    tracker.close()
    cam.stop()
    cv2.destroyAllWindows()
