"""
Đo tốc độ khung hình thật của camera, tách từng khâu để biết chỗ nào làm chậm.

Chạy từ thư mục gốc dự án (nhớ tắt server.py trước, vì camera chỉ mở được bởi một chương trình):
    python tests/camera_fps_test.py
    CAMERA_INDEX=1 python tests/camera_fps_test.py     # nếu có nhiều camera
"""
import os
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai.camera import Camera  # noqa: E402

INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
SECONDS = 5


def fourcc_str(v) -> str:
    v = int(v)
    return "".join(chr((v >> (8 * i)) & 0xFF) for i in range(4))


def raw_test(label: str, mjpg: bool):
    backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
    cap = cv2.VideoCapture(INDEX, backend)
    if not cap.isOpened():
        print(f"{label}: không mở được camera (đang bị chương trình khác dùng?)")
        return
    if mjpg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    n, t0 = 0, time.time()
    while time.time() - t0 < SECONDS:
        ok, _ = cap.read()
        if ok:
            n += 1
    dt = time.time() - t0
    print(
        f"{label}: {n / dt:5.1f} khung/giây   "
        f"(driver: {fourcc_str(cap.get(cv2.CAP_PROP_FOURCC))} "
        f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
        f"@ {cap.get(cv2.CAP_PROP_FPS):.0f})"
    )
    cap.release()


def camera_class_test(label: str, encode: bool):
    cam = Camera(index=INDEX).start()
    last, n, t0 = -1, 0, time.time()
    while time.time() - t0 < SECONDS:
        seq, frame = cam.read(last, 1.0)
        if frame is None:
            continue
        last = seq
        if encode:
            cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        n += 1
    dt = time.time() - t0
    cam.stop()
    print(f"{label}: {n / dt:5.1f} khung/giây")


if __name__ == "__main__":
    print(f"Đo {SECONDS} giây mỗi bài, camera index {INDEX}\n")
    raw_test("1. OpenCV thô, định dạng mặc định ", mjpg=False)
    raw_test("2. OpenCV thô, ép MJPG            ", mjpg=True)
    camera_class_test("3. Lớp Camera (ai/camera.py)      ", encode=False)
    camera_class_test("4. Lớp Camera + mã hóa JPEG       ", encode=True)
    print("\nĐọc kết quả: xem hướng dẫn trong tin nhắn.")