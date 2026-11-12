"""
Nhật ký một lần chạy server.py, để đọc lại toàn bộ chuyện gì đã xảy ra.

Mỗi lần chạy tạo trong logs/ hai tệp cùng mốc thời gian:

    run_<giờ>.log   Toàn bộ chữ server in ra (cả cảnh báo của MediaPipe/OpenCV/uvicorn), mỗi dòng có giờ,
                    cộng phần đầu (phiên bản mã, thư viện, máy), các sự kiện (đổi chế độ, dừng khẩn cấp, robot
                    nối/mất, dashboard mở/đóng), thống kê mỗi 5 giây và tóm tắt cuối phiên.
    ai_<giờ>.csv    Mỗi khung camera một dòng: giờ đọc khung, thời gian suy luận, số tay, tư thế con trỏ, cử chỉ đã
                    lọc, lệnh cử chỉ, vị trí con trỏ. Cùng đồng hồ time.time() với logs/drive_*.csv (bản ghi 20 Hz
                    số liệu 4 bánh), nên ghép hai tệp lại thì tính được độ trễ từ khung camera đến bánh xe.

Bắt chữ in ra ở mức file descriptor (os.dup2), nên cả chữ do thư viện C in thẳng ra stderr cũng được ghi. Ctrl+C
hoặc tắt server bình thường thì trả terminal về như cũ và ghi tóm tắt.
"""
import atexit
import csv
import os
import platform
import statistics as st
import subprocess
import sys
import threading
import time
from collections import Counter, deque
from pathlib import Path

AI_COLUMNS = ["t", "infer_ms", "total_ms", "n_hands", "ui_pose", "gesture", "gvx", "gvy", "gw",
              "cx", "cy", "ax", "ay"]


def _git(root: Path, *args) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return "?"


class RunLog:
    def __init__(self, logs_dir: Path, root: Path):
        self.dir, self.root = logs_dir, root
        self.stamp = time.strftime("%Y%m%d_%H%M%S")
        self.path = logs_dir / f"run_{self.stamp}.log"
        self.ai_path = logs_dir / f"ai_{self.stamp}.csv"
        self.t0 = time.time()
        self._file = None
        self._ai_file = self._ai_writer = None
        self._ai_rows = 0
        self._ai_t = [None, None]       # giờ khung AI đầu và cuối
        self._tee_thread = None
        self._saved = None
        self._closed = False
        self.active = False
        self.infer = deque(maxlen=300)   # ms gần nhất, để thống kê
        self.total_infer = []            # toàn phiên (nhẹ: một số thực mỗi khung)
        self.events = Counter()

    # ---------------------------------------------------------------- bắt toàn bộ output
    def start(self):
        self.dir.mkdir(exist_ok=True)
        self._file = open(self.path, "w", buffering=1, encoding="utf-8")
        try:
            sys.stdout.reconfigure(line_buffering=True)
            sys.stderr.reconfigure(line_buffering=True)
        except Exception:
            pass
        sys.stdout.flush()
        sys.stderr.flush()
        r, w = os.pipe()
        self._saved = (os.dup(1), os.dup(2))
        os.dup2(w, 1)
        os.dup2(w, 2)
        os.close(w)
        self._tee_thread = threading.Thread(target=self._pump, args=(r,), daemon=True)
        self._tee_thread.start()
        self.active = True
        atexit.register(self.close)
        self._header()

    def _pump(self, r):
        with os.fdopen(r, "rb") as src:
            for raw in src:
                try:
                    os.write(self._saved[0], raw)         # vẫn hiện trên terminal
                except OSError:
                    pass
                text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if text:
                    self._file.write(f"[{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] {text}\n")

    def _header(self):
        cpu = "?"
        try:
            cpu = next(l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
        except Exception:
            pass
        versions = {}
        for mod in ("cv2", "mediapipe", "numpy", "fastapi", "uvicorn"):
            try:
                versions[mod] = __import__(mod).__version__
            except Exception:
                versions[mod] = "?"
        env = {k: os.environ.get(k, "") for k in ("HOST", "PORT", "CAMERA_INDEX", "HAND_OPEN", "ROBOT_HOST", "ROBOT_PORT")}
        dirty = _git(self.root, "status", "--short", "--", "ai", "web", "communication", "firmware")
        print("=" * 70)
        print(f"Phiên chạy server {time.strftime('%Y-%m-%d %H:%M:%S')}  ({self.path.name})")
        print(f"Mã: {_git(self.root, 'rev-parse', '--short', 'HEAD')} nhánh {_git(self.root, 'rev-parse', '--abbrev-ref', 'HEAD')}"
              f"{'  CÓ SỬA CHƯA COMMIT' if dirty else ''}")
        if dirty:
            print("  " + dirty.replace("\n", "\n  "))
        print(f"Máy: {platform.platform()} | {cpu} | Python {platform.python_version()}")
        print("Thư viện: " + ", ".join(f"{k} {v}" for k, v in versions.items()))
        env_txt = ", ".join(f"{k}={v}" for k, v in env.items() if v)
        print("Biến môi trường: " + (env_txt or "(mặc định)"))
        print(f"Tệp phụ: {self.ai_path.name} (từng khung AI), drive_*.csv (4 bánh, 20 Hz, chỉ khi robot nối)")
        print("=" * 70)

    # ---------------------------------------------------------------- sự kiện và thống kê
    def event(self, name: str, detail: str = ""):
        """Ghi một sự kiện, ví dụ event('mode', 'gesture')."""
        self.events[name] += 1
        print(f"[SỰ KIỆN] {name}" + (f": {detail}" if detail else ""))

    def stats_line(self, fps, rtt, connected, mode, estop, hands, clients, cam_ok) -> str:
        x = list(self.infer)
        inf = f"suy luận {st.mean(x):.1f} ms (P95 {sorted(x)[int(.95 * (len(x) - 1))]:.1f})" if x else "suy luận --"
        return (f"[THỐNG KÊ] {fps:.1f} khung/giây, {inf}, camera {'ok' if cam_ok else 'KHÔNG MỞ'}, "
                f"robot {'ok RTT %.1f ms' % rtt if connected else 'CHƯA NỐI'}, chế độ {mode}"
                f"{' DỪNG KHẨN CẤP' if estop else ''}, tay giao diện/lái {int(hands['ui'])}/{int(hands['drive'])}, dashboard {clients}")

    def stats(self, *a):
        print(self.stats_line(*a))

    # ---------------------------------------------------------------- từng khung AI
    def ai_row(self, t, infer_ms, total_ms, n_hands, pose, gesture, cmd, cursor):
        if not self.active:
            return
        self.infer.append(infer_ms)
        self.total_infer.append(infer_ms)
        if self._ai_file is None:
            self._ai_file = open(self.ai_path, "w", newline="", buffering=1 << 16)
            self._ai_writer = csv.writer(self._ai_file)
            self._ai_writer.writerow(AI_COLUMNS)
        self._ai_writer.writerow([f"{t:.3f}", f"{infer_ms:.2f}", f"{total_ms:.2f}", n_hands, pose, gesture or "",
                                  f"{cmd[0]:.3f}", f"{cmd[1]:.3f}", f"{cmd[2]:.3f}",
                                  f"{cursor['x']:.4f}", f"{cursor['y']:.4f}", f"{cursor['ax']:.4f}", f"{cursor['ay']:.4f}"])
        self._ai_rows += 1
        if self._ai_t[0] is None:
            self._ai_t[0] = t
        self._ai_t[1] = t
        if self._ai_rows % 60 == 0:
            self._ai_file.flush()

    # ---------------------------------------------------------------- kết thúc
    def summary(self):
        dur = time.time() - self.t0
        print("-" * 70)
        span = (self._ai_t[1] - self._ai_t[0]) if self._ai_t[0] is not None else 0
        fps = f", {self._ai_rows / span:.1f} khung/giây trong lúc có hình" if span > 1 else ""
        print(f"Tóm tắt: chạy {dur:.0f} s, {self._ai_rows} khung AI{fps}")
        if self.total_infer:
            x = sorted(self.total_infer)
            print(f"  suy luận tay: trung bình {st.mean(x):.1f} ms, trung vị {st.median(x):.1f}, P95 {x[int(.95 * (len(x) - 1))]:.1f}, lớn nhất {x[-1]:.1f}")
        if self.events:
            print("  sự kiện: " + ", ".join(f"{k} x{v}" for k, v in sorted(self.events.items())))
        print(f"  tệp: {self.path.name}, {self.ai_path.name if self._ai_rows else '(không có khung AI)'}")
        print("-" * 70)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.summary()
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        if self._saved:  # trả terminal về như cũ: bản sao đường ống bị đóng nên luồng ghi gặp EOF
            os.dup2(self._saved[0], 1)
            os.dup2(self._saved[1], 2)
            if self._tee_thread:
                self._tee_thread.join(timeout=2)
            os.close(self._saved[0])
            os.close(self._saved[1])
            self._saved = None
        if self._ai_file:
            self._ai_file.close()
        if self._file:
            self._file.close()
