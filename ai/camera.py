"""
Đọc camera laptop với độ trễ thấp.

- Đọc trong thread riêng và chỉ giữ khung MỚI NHẤT (không xếp hàng), nên AI/web
  chậm hơn camera thì khung cũ bị bỏ, hình không bị trễ dần.
- Dùng định dạng MJPG, bộ đệm driver 2 khung. Không dùng 1: khi chương trình
  đang giữ khung duy nhất thì camera không có chỗ ghi khung kế tiếp và bỏ nó,
  FPS rơi đúng một nửa (30 -> 15).
- Camera bị rút/đang bận thì tự thử mở lại mỗi 2 giây.
"""
import sys
import threading
import time

import cv2


class Camera:
    def __init__(self, index=0, width=640, height=480, fps=30, mirror=True):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.mirror = mirror        # lật gương: tay phải của bạn hiện bên phải màn hình
        self.opened = False

        self._cond = threading.Condition()
        self._frame = None
        self._seq = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ---------- vòng đời ----------
    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    # ---------- lấy khung ----------
    def read(self, last_seq=-1, timeout=1.0):
        """Đợi tới khi có khung mới hơn last_seq (tối đa timeout giây).

        Trả về (seq, frame_BGR) hoặc (last_seq, None) nếu hết thời gian.
        """
        with self._cond:
            if self._seq == last_seq:
                self._cond.wait(timeout)
            if self._seq == last_seq or self._frame is None:
                return last_seq, None
            return self._seq, self._frame.copy()

    # ---------- nội bộ ----------
    def _open(self):
        backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.index, backend)
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        return cap

    def _publish(self, frame):
        with self._cond:
            self._frame = frame
            self._seq += 1
            self._cond.notify_all()

    def _run(self):
        while not self._stop.is_set():
            cap = self._open()
            if cap is None:
                self.opened = False
                time.sleep(2)
                continue
            self.opened = True
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                if self.mirror:
                    frame = cv2.flip(frame, 1)
                self._publish(frame)
            cap.release()
            self.opened = False


if __name__ == "__main__":
    # Xem thử camera: python ai/camera.py  (bấm q để thoát)
    cam = Camera().start()
    last = -1
    try:
        while True:
            last, frame = cam.read(last)
            if frame is None:
                continue
            cv2.imshow("Laptop Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        cam.stop()
        cv2.destroyAllWindows()
