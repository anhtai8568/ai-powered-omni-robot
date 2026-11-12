"""
Server điều khiển robot: camera -> hai bàn tay -> (tay không thuận) lệnh robot, (tay thuận) con trỏ giao diện.

Chạy: python web/server.py, mở http://127.0.0.1:8000/ (hoặc giơ tay trước camera 2 giây, trình duyệt tự mở)
Biến môi trường: CAMERA_INDEX (mặc định 0), HOST (0.0.0.0 để máy khác truy cập), PORT (8000),
                 HAND_OPEN=0 để tắt việc tự mở trình duyệt khi giơ tay

Lệnh (vx, vy, w) theo chuẩn ROS, trong -1..1: vx > 0 tiến, vy > 0 sang trái, w > 0 xoay trái.
"""
import asyncio
import csv
import json
import os
import socket
import sys
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parent))  # để import được ai/ và communication/
from ai.camera import Camera  # noqa: E402
from ai.drive.command import GestureFilter, to_command  # noqa: E402
from ai.drive.gestures import classify  # noqa: E402
from ai.hands import Hand, HandTracker, RoleAssigner, draw_hand, split_roles  # noqa: E402
from ai.ui.cursor import Cursor  # noqa: E402
from communication.robot_link import RobotLink  # noqa: E402
from web.runlog import RunLog  # noqa: E402

STATIC = BASE / "static"
LOGS = BASE.parent / "logs"

# Nhật ký cả lần chạy (logs/run_*.log + logs/ai_*.csv). Chỉ bật khi chạy trực tiếp `python web/server.py`,
# bật trước mọi thứ khác để bắt luôn cảnh báo của MediaPipe/OpenCV lúc nạp.
runlog = RunLog(LOGS, BASE.parent)
if __name__ == "__main__":
    runlog.start()

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
# Hình hiển thị lấy 1280x720 cho nét (640x480 bị phóng ~2 lần lên cửa sổ nên mờ); AI vẫn chạy trên bản thu về
# DETECT_WIDTH px để ngưỡng và tốc độ không đổi. Camera không có chế độ này thì OpenCV tự chọn chế độ gần nhất.
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", "1280"))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", "720"))
DETECT_WIDTH = 640
HAND_OPEN = os.environ.get("HAND_OPEN", "1") != "0"
OPEN_HOLD = 2.0       # giây giơ tay liên tục thì tự mở trình duyệt
OPEN_COOLDOWN = 30.0  # giây tối thiểu giữa hai lần tự mở

CONTROL_HZ = 20       # tần số vòng điều khiển gửi lệnh ra robot
CMD_TIMEOUT = 0.4     # giây; quá thời gian này không có lệnh mới -> dừng robot
JPEG_QUALITY = 85
MAX_ACCEL = 2.0       # tăng tốc tối đa, đơn vị lệnh/giây (0 -> 1 mất 0.5 s)
MAX_DECEL = 4.0       # giảm tốc tối đa (1 -> 0 mất 0.25 s), nhanh hơn tăng tốc để dừng kịp


def ramp(cur: float, target: float, dt: float) -> float:
    """Đưa `cur` tiến dần về `target`, không đổi quá nhanh (giới hạn gia tốc).

    Tốc độ nhảy bậc làm 4 motor không giảm/tăng đều nhau -> robot omni bị xoay
    lệch, con lăn trượt, dòng điện motor tăng vọt khi đảo chiều. Khi đổi chiều
    (tiến -> lùi) thì phanh về 0 trước rồi mới tăng tốc theo chiều mới.
    """
    if cur * target < 0:                  # đổi chiều: phanh về 0 trước
        goal, rate = 0.0, MAX_DECEL
    elif abs(target) < abs(cur):          # chậm lại
        goal, rate = target, MAX_DECEL
    else:                                 # nhanh lên
        goal, rate = target, MAX_ACCEL
    step = rate * dt
    return cur + max(-step, min(step, goal - cur))


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
        self.speed = 0.5                     # tốc độ tối đa (0.1..1), chỉnh bằng thanh trên dashboard
        self.gesture = None                  # tên cử chỉ đã lọc nhiễu (tay lái)
        self.dominant = "right"              # tay thuận: điều khiển giao diện; tay còn lại lái robot
        self.region = 1.0                    # vùng tay hoạt động (phần khung camera ứng với cả màn hình); 1.0 = con trỏ đúng đầu ngón tay
        self.video = True                    # false: không gửi hình lên dashboard (camera vẫn nhận tay)
        self.cursor = {"pose": "none", "x": 0.5, "y": 0.5, "ax": 0.5, "ay": 0.5}
        self.hands = {"ui": False, "drive": False}
        self.gesture_cmd = (0.0, 0.0, 0.0)
        self.gesture_ts = 0.0
        self.frame_count = 0
        self.fps = 0.0
        self.out = {"vx": 0.0, "vy": 0.0, "w": 0.0}


state = State()
cam = Camera(index=CAMERA_INDEX, width=CAMERA_WIDTH, height=CAMERA_HEIGHT, fps=30, mirror=True)
tracker = HandTracker()
roles = RoleAssigner()
cursor = Cursor()
gesture_filter = GestureFilter(hold=4, stop_hold=6)  # số khung cần giữ: di chuyển / dừng


robot = RobotLink()  # gửi lệnh tới ESP32 qua UDP (communication/robot_link.py)


class DriveLog:
    """Ghi mỗi tick điều khiển 1 dòng vào logs/drive_<ngày giờ>.csv, chỉ khi robot đang kết nối.

    Mỗi dòng: thời gian, chế độ, cử chỉ, lệnh gửi robot, độ trễ, và số liệu 4 bánh ESP32 gửi về
    (tốc độ muốn, tốc độ đo, PWM; đơn vị chuẩn hóa, 1.0 = tốc độ tối đa).
    """

    WHEELS = ("tt", "tp", "st", "sp")  # trước trái, trước phải, sau trái, sau phải

    def __init__(self):
        self._file = None
        self._writer = None

    def write(self):
        if not robot.connected or robot.wheels is None:
            return
        if self._file is None:
            LOGS.mkdir(exist_ok=True)
            path = LOGS / time.strftime("drive_%Y%m%d_%H%M%S.csv")
            self._file = open(path, "w", newline="")
            self._writer = csv.writer(self._file)
            self._writer.writerow(["t", "mode", "estop", "gesture", "vx", "vy", "w", "rtt_ms"]
                                  + [f"{w}_{k}" for w in self.WHEELS for k in ("muon", "do", "pwm")])
            print(f"Ghi log: {path}")
        o = state.out
        self._writer.writerow([f"{time.time():.3f}", state.mode, int(state.estop), state.gesture or "",
                               f"{o['vx']:.3f}", f"{o['vy']:.3f}", f"{o['w']:.3f}",
                               f"{robot.rtt_ms:.1f}"] + robot.wheels)

    def flush(self):
        if self._file:
            self._file.flush()

    def close(self):
        if self._file:
            self._file.close()


drive_log = DriveLog()


def process_frame(frame, t_frame=None):
    """AI hai bàn tay (chạy trong thread riêng, không chặn vòng điều khiển). Vẽ khung xương lên frame.

    Tay thuận -> con trỏ giao diện. Tay không thuận -> cử chỉ lái robot (như bản 1).
    Luôn chạy, kể cả ở chế độ thủ công, để người dùng thấy AI nhận ra gì trước khi bật chế độ cử chỉ.
    Nếu AI bị treo, gesture_ts không được cập nhật và control_loop tự dừng robot sau CMD_TIMEOUT.
    """
    t_start = time.perf_counter()
    fh, fw = frame.shape[:2]
    if fw > DETECT_WIDTH:
        small = cv2.resize(frame, (DETECT_WIDTH, round(fh * DETECT_WIDTH / fw)), interpolation=cv2.INTER_AREA)
    else:
        small = frame
    h, w = small.shape[:2]
    k = fw / w  # hệ số phóng từ ảnh nhận diện lên ảnh hiển thị
    detected = tracker.detect(small)
    t_infer = time.perf_counter()
    hands = roles.assign(detected)
    # Thủ công: robot không lái bằng cử chỉ, nên chỉ cần một tay (tay nào cũng là tay giao diện)
    ui_hand, drive_hand = split_roles(hands, state.dominant, drive_active=state.mode == "gesture")

    state.gesture = gesture_filter.update(classify(drive_hand.pts if drive_hand else None))
    state.gesture_cmd = to_command(state.gesture, state.speed)
    state.gesture_ts = time.time()

    cursor.region = state.region
    state.cursor = cursor.update(ui_hand.pts if ui_hand else None, w, h, time.monotonic())
    state.hands = {"ui": ui_hand is not None, "drive": drive_hand is not None}

    runlog.ai_row(t_frame if t_frame is not None else time.time(), (t_infer - t_start) * 1000,
                  (time.perf_counter() - t_start) * 1000, len(hands), state.cursor["pose"], state.gesture,
                  state.gesture_cmd, state.cursor)

    scaled = lambda hd: hd if k == 1 else Hand(pts=[(x * k, y * k) for x, y in hd.pts], label=hd.label, side=hd.side)
    if ui_hand:
        draw_hand(frame, scaled(ui_hand), "ui", f"UI {state.cursor['pose']}", k)
    if drive_hand:
        draw_hand(frame, scaled(drive_hand), "drive", f"DRIVE {state.gesture or '-'}", k)
    return frame


def encode_jpeg(frame):
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes() if ok else None


class AutoOpen:
    """Giơ tay liên tục OPEN_HOLD giây khi chưa có dashboard nào mở thì tự mở trình duyệt."""

    def __init__(self):
        self._since = None
        self._last = -1e9

    def update(self, hand_visible: bool, dashboard_open: bool, now: float) -> bool:
        if not hand_visible or dashboard_open:
            self._since = None
            return False
        if self._since is None:
            self._since = now
        if now - self._since >= OPEN_HOLD and now - self._last >= OPEN_COOLDOWN:
            self._last = now
            self._since = None
            return True
        return False


auto_open = AutoOpen()


def status_msg() -> dict:
    return {
        "type": "status",
        "camera": cam.opened,
        "robot": robot.connected,
        "rtt": round(robot.rtt_ms, 1) if robot.connected else None,
        "mode": state.mode,
        "estop": state.estop,
        "speed": state.speed,
        "dominant": state.dominant,
        "region": state.region,
        "video": state.video,
        "fps": round(state.fps, 1),
    }


async def broadcast_json(msg: dict):
    if not state.dashboards:
        return
    text = json.dumps(msg)
    for ws in list(state.dashboards):
        try:
            await ws.send_text(text)
        except Exception:
            state.dashboards.discard(ws)


async def broadcast_status():
    await broadcast_json(status_msg())


async def broadcast_frame(data: bytes):
    for ws in list(state.dashboards):
        try:
            await ws.send_bytes(data)
        except Exception:
            state.dashboards.discard(ws)


async def video_loop():
    """Lấy khung mới nhất từ camera -> AI -> gửi con trỏ rồi hình JPEG cho dashboard."""
    last = -1
    while True:
        seq, frame = await asyncio.to_thread(cam.read, last, 1.0)
        if frame is None:
            continue
        last = seq
        state.frame_count += 1
        frame = await asyncio.to_thread(process_frame, frame, time.time())
        # Gửi con trỏ trước khi mã hóa JPEG: con trỏ không phải chờ hình
        await broadcast_json({"type": "cursor", **state.cursor})
        if HAND_OPEN and auto_open.update(any(state.hands.values()), bool(state.dashboards), time.time()):
            print("Thấy tay: mở dashboard trên trình duyệt")
            webbrowser.open(f"http://127.0.0.1:{PORT}/")
        if state.dashboards and state.video:
            jpeg = await asyncio.to_thread(encode_jpeg, frame)
            if jpeg:
                await broadcast_frame(jpeg)


async def control_loop():
    """Mỗi 1/CONTROL_HZ giây chọn lệnh đầu ra, gửi cho robot và cho dashboard.

    Không có lệnh mới trong CMD_TIMEOUT giây (mất kết nối, treo trình duyệt,
    AI không thấy tay...) thì đầu ra tự về 0 (qua bộ giới hạn gia tốc).
    Dừng khẩn cấp thì về 0 ngay lập tức, không đi qua bộ giới hạn.
    """
    period = 1.0 / CONTROL_HZ
    tick = 0
    fps_t0 = time.time()
    was_connected, was_camera = None, None
    while True:
        now = time.time()
        vx = vy = w = 0.0
        if not state.estop:
            if state.mode == "manual" and now - state.manual_ts < CMD_TIMEOUT:
                vx, vy, w = state.manual_cmd
            elif state.mode == "gesture" and now - state.gesture_ts < CMD_TIMEOUT:
                vx, vy, w = state.gesture_cmd
        if state.estop:
            state.out = {"vx": 0.0, "vy": 0.0, "w": 0.0}
        else:
            state.out = {k: ramp(state.out[k], v, period)
                         for k, v in (("vx", vx), ("vy", vy), ("w", w))}
        await robot.send(state.out)
        drive_log.write()
        if robot.connected != was_connected:
            runlog.event("robot", "đã kết nối" if robot.connected else "mất kết nối / chưa kết nối")
            was_connected = robot.connected
        if cam.opened != was_camera:
            runlog.event("camera", "mở được" if cam.opened else "không mở được")
            was_camera = cam.opened
        # Lệnh thật gửi cho robot + cử chỉ, mỗi tick (20 lần/giây) để web hiển thị tức thì
        await broadcast_json({"type": "telemetry", "out": state.out, "gesture": state.gesture,
                              "hands": state.hands})

        tick += 1
        if tick % (CONTROL_HZ // 2) == 0:  # 2 lần/giây
            dt = now - fps_t0
            state.fps = state.frame_count / dt if dt > 0 else 0.0
            state.frame_count = 0
            fps_t0 = now
            await broadcast_status()
            drive_log.flush()
        if tick % (CONTROL_HZ * 5) == 0:  # 5 giây một dòng thống kê vào nhật ký
            runlog.stats(state.fps, robot.rtt_ms, robot.connected, state.mode, state.estop, state.hands,
                         len(state.dashboards), cam.opened)

        await asyncio.sleep(period)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cam.start()
    await robot.start()
    tasks = [asyncio.create_task(control_loop()), asyncio.create_task(video_loop())]
    yield
    for t in tasks:
        t.cancel()
    cam.stop()
    tracker.close()
    robot.close()
    drive_log.close()
    runlog.close()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def no_cache(request, call_next):
    # Bắt trình duyệt hỏi lại server mỗi lần tải (file không đổi thì chỉ trả 304),
    # để sửa HTML/JS/CSS xong là thấy ngay, không bị dính bản cũ trong cache.
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


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
        if bool(d.get("on")) != state.estop:
            runlog.event("dừng khẩn cấp", "BẬT" if d.get("on") else "tắt")
        state.estop = bool(d.get("on"))
        await broadcast_status()
    elif kind == "speed":
        try:
            v = float(d.get("value"))
        except (TypeError, ValueError):
            return  # giá trị rác: giữ nguyên tốc độ cũ (không để thành 0)
        if v == v:  # bỏ NaN
            new = max(0.1, min(1.0, v))
            if abs(new - state.speed) >= 0.05:  # thanh trượt gửi liên tục: chỉ ghi khi đổi đáng kể
                runlog.event("tốc độ", f"{new:.2f}")
            state.speed = new
            await broadcast_status()
    elif kind == "mode" and d.get("mode") in ("manual", "gesture"):
        if d["mode"] != state.mode:
            runlog.event("chế độ", d["mode"])
        state.mode = d["mode"]
        await broadcast_status()
    elif kind == "video":
        state.video = bool(d.get("on"))
        await broadcast_status()
    elif kind == "settings":
        if d.get("dominant") in ("left", "right"):
            state.dominant = d["dominant"]
        if "region" in d:
            try:
                r = float(d["region"])
            except (TypeError, ValueError):
                r = None
            if r is not None and r == r:
                state.region = max(0.4, min(1.0, r))
        await broadcast_status()


@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    state.dashboards.add(ws)
    runlog.event("dashboard", f"mở ({len(state.dashboards)} đang mở)")
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
        runlog.event("dashboard", f"đóng ({len(state.dashboards)} còn lại)")
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