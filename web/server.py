"""
Máy chủ web điều khiển robot omni 4 bánh (camera laptop).

Chạy (từ thư mục web/):   python server.py
Mở dashboard:             http://127.0.0.1:8000/

Biến môi trường (tùy chọn):
  CAMERA_INDEX=1   chọn camera khác (mặc định 0)
  HOST=0.0.0.0     cho máy khác trong mạng (vd iPhone) mở dashboard để điều khiển
  PORT=8000

Quy ước lệnh (theo chuẩn ROS), mỗi giá trị nằm trong -1..1:
  vx > 0  tiến        vy > 0  đi ngang sang trái        w > 0  xoay ngược chiều kim đồng hồ
"""
import asyncio
import json
import os
import socket
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parent))  # để import được ai/camera.py
from ai.camera import Camera  # noqa: E402

STATIC = BASE / "static"

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))

CONTROL_HZ = 20       # tần số vòng điều khiển gửi lệnh ra robot
CMD_TIMEOUT = 0.4     # giây; quá thời gian này không có lệnh mới -> dừng robot
JPEG_QUALITY = 70


def clamp(v, lo=-1.0, hi=1.0) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(lo, min(hi, v))


class State:
    def __init__(self):
        self.dashboards: set[WebSocket] = set()
        self.mode = "manual"          # "manual" | "gesture"
        self.estop = False
        self.manual_cmd = (0.0, 0.0, 0.0)
        self.manual_ts = 0.0
        self.gesture_cmd = (0.0, 0.0, 0.0)   # AI sẽ ghi vào đây
        self.gesture_ts = 0.0
        self.frame_count = 0
        self.fps = 0.0
        self.out = {"vx": 0.0, "vy": 0.0, "w": 0.0}


state = State()
cam = Camera(index=CAMERA_INDEX, width=640, height=480, fps=30, mirror=True)


class RobotLink:
    """Cầu nối tới ESP32. Hiện chỉ là bản giả (in ra console).

    TODO: gửi lệnh qua WiFi (UDP hoặc WebSocket) tới ESP32, rồi chuyển
    class này sang thư mục communication/.
    """

    connected = False

    def __init__(self):
        self._last_log = 0.0

    async def send(self, cmd: dict):
        now = time.time()
        moving = any(cmd[k] for k in ("vx", "vy", "w"))
        if moving and now - self._last_log > 0.5:
            print(f"[robot] vx={cmd['vx']:.2f} vy={cmd['vy']:.2f} w={cmd['w']:.2f}")
            self._last_log = now


robot = RobotLink()


def process_frame(frame):
    """Chỗ cắm AI (chạy trong thread riêng, không chặn vòng điều khiển).

    `frame` là ảnh BGR (numpy). Sau này:
      - gọi gesture_recognition rồi gesture_to_command
      - ghi kết quả:  state.gesture_cmd = (vx, vy, w);  state.gesture_ts = time.time()
      - muốn vẽ khung xương bàn tay lên hình dashboard thì vẽ lên `frame`
        rồi return nó; return None nếu không vẽ gì.
    """
    return None


def encode_frame(frame, want_jpeg: bool):
    out = process_frame(frame)
    if out is not None:
        frame = out
    if not want_jpeg:
        return None
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes() if ok else None


def status_msg() -> dict:
    return {
        "type": "status",
        "camera": cam.opened,
        "robot": robot.connected,
        "mode": state.mode,
        "estop": state.estop,
        "fps": round(state.fps, 1),
        "out": state.out,
    }


async def broadcast_status():
    msg = json.dumps(status_msg())
    for ws in list(state.dashboards):
        try:
            await ws.send_text(msg)
        except Exception:
            state.dashboards.discard(ws)


async def broadcast_frame(data: bytes):
    for ws in list(state.dashboards):
        try:
            await ws.send_bytes(data)
        except Exception:
            state.dashboards.discard(ws)


async def video_loop():
    """Lấy khung mới nhất từ camera -> AI -> gửi JPEG cho dashboard."""
    last = -1
    while True:
        seq, frame = await asyncio.to_thread(cam.read, last, 1.0)
        if frame is None:
            continue
        last = seq
        state.frame_count += 1
        jpeg = await asyncio.to_thread(encode_frame, frame, bool(state.dashboards))
        if jpeg:
            await broadcast_frame(jpeg)


async def control_loop():
    """Mỗi 1/CONTROL_HZ giây chọn lệnh đầu ra và gửi cho robot.

    Không có lệnh mới trong CMD_TIMEOUT giây (mất kết nối, treo trình duyệt,
    AI không thấy tay...) thì đầu ra tự về 0.
    """
    period = 1.0 / CONTROL_HZ
    tick = 0
    fps_t0 = time.time()
    while True:
        now = time.time()
        vx = vy = w = 0.0
        if not state.estop:
            if state.mode == "manual" and now - state.manual_ts < CMD_TIMEOUT:
                vx, vy, w = state.manual_cmd
            elif state.mode == "gesture" and now - state.gesture_ts < CMD_TIMEOUT:
                vx, vy, w = state.gesture_cmd
        state.out = {"vx": vx, "vy": vy, "w": w}
        await robot.send(state.out)

        tick += 1
        if tick % (CONTROL_HZ // 2) == 0:  # 2 lần/giây
            dt = now - fps_t0
            state.fps = state.frame_count / dt if dt > 0 else 0.0
            state.frame_count = 0
            fps_t0 = now
            await broadcast_status()

        await asyncio.sleep(period)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cam.start()
    tasks = [asyncio.create_task(control_loop()), asyncio.create_task(video_loop())]
    yield
    for t in tasks:
        t.cancel()
    cam.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


async def handle_dashboard_message(d: dict):
    kind = d.get("type")
    if kind == "cmd":
        state.manual_cmd = (clamp(d.get("vx")), clamp(d.get("vy")), clamp(d.get("w")))
        state.manual_ts = time.time()
    elif kind == "estop":
        state.estop = bool(d.get("on"))
        await broadcast_status()
    elif kind == "mode" and d.get("mode") in ("manual", "gesture"):
        state.mode = d["mode"]
        await broadcast_status()


@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    state.dashboards.add(ws)
    await ws.send_text(json.dumps(status_msg()))
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            text = msg.get("text")
            if not text:
                continue
            try:
                data = json.loads(text)
            except ValueError:
                continue
            if isinstance(data, dict):
                await handle_dashboard_message(data)
    finally:
        state.dashboards.discard(ws)
        state.manual_ts = 0.0  # dashboard đóng -> dừng robot


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # UDP: không gửi gói tin nào, chỉ để chọn card mạng
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    print(f"Dashboard: http://127.0.0.1:{PORT}/")
    if HOST != "127.0.0.1":
        print(f"Từ máy khác trong mạng: http://{lan_ip()}:{PORT}/  (ai cũng điều khiển được, chỉ dùng mạng tin cậy)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")