# AI-Powered Omni Robot

Robot omni 4 bánh (bánh chéo 45°) điều khiển bằng cử chỉ tay qua camera laptop.

```
Camera ──► AI cử chỉ ──► Server ──WiFi──► ESP32 ──► 4 motor
                           └──► Dashboard web
```

**Đã xong:** stream camera 30 FPS, nhận diện cử chỉ, dashboard, truyền lệnh laptop -> ESP32 qua WiFi.
**Đang làm:** firmware ESP32: motor, encoder, PID.

## Chạy

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

1. Nạp firmware (lần đầu): `cd firmware && pio run -t upload`
2. Bật robot, laptop bắt WiFi **omni-robot** (mật khẩu `omnirobot`). Không cần Internet.
3. `python web/server.py`, mở http://127.0.0.1:8000/. Ô "Robot" xanh là đã kết nối.

Tùy chọn: `CAMERA_INDEX=1` chọn camera khác, `HOST=0.0.0.0` cho máy khác trong mạng truy cập.

Công cụ thử riêng từng phần (thoát bằng `q` hoặc Ctrl+C):

```bash
python ai/gesture_recognition.py   # xem AI nhận diện tay
python communication/robot_link.py # gửi lệnh thử tới ESP32 khi không chạy server
python tests/camera_fps_test.py    # đo FPS camera (tắt server trước)
```

## Cử chỉ

Bật bằng nút **Cử chỉ tay** trên dashboard. Ảnh đã lật gương: "trái" là bên trái của bạn.

| Cử chỉ | Robot |
|---|---|
| Ngón trỏ chỉ 8 hướng (lên, xuống, trái, phải, 4 góc chéo) | Đi theo hướng chỉ |
| Chữ V (trỏ + giữa) chỉ trái / phải | Xoay trái / phải |
| Nắm tay, xòe tay, không thấy tay | Dừng |

Chống giật: cử chỉ phải giữ ổn định khoảng 0.15 s mới có hiệu lực, tốc độ tăng giảm dần. Nút **Dừng khẩn cấp** (phím Space) luôn dừng ngay.

Lệnh gửi robot theo chuẩn ROS, mỗi giá trị trong `-1..1`: `vx > 0` tiến, `vy > 0` sang trái, `w > 0` xoay trái.

## Kết nối laptop - ESP32

ESP32 tự phát WiFi, laptop gửi lệnh qua UDP (cổng 4210) 20 lần/giây, độ trễ khoảng 5 ms. ESP32 tự dừng nếu mất lệnh quá 0.3 s, và chỉ nhận lệnh từ một máy tại một thời điểm.

## Phần cứng

ESP32 DevKit V1, 2 driver L298N (trước / sau), 4 motor DC có encoder.

![Sơ đồ chân](docs/pinout.png)

| Bánh | PWM | IN1 / IN3 | IN2 / IN4 | Encoder A | Encoder B |
|---|---|---|---|---|---|
| Trước trái | 25 | 26 | 27 | 36 | 39 |
| Trước phải | 13 | 23 | 22 | 34 | 35 |
| Sau trái | 21 | 19 | 18 | 32 | 33 |
| Sau phải | 17 | 16 | 4 | 14 | 5 |

GPIO 34, 35, 36, 39 không có điện trở kéo lên trong: encoder open-collector cần điện trở 10 kΩ lên 3.3 V.

## Thư mục

| | |
|---|---|
| `ai/` | đọc camera, nhận diện cử chỉ, chuyển cử chỉ thành lệnh |
| `web/` | server FastAPI và giao diện dashboard |
| `communication/` | gửi lệnh tới ESP32 qua UDP |
| `firmware/` | chương trình ESP32 (PlatformIO) |
| `tests/` | đo FPS camera |
| `docs/` | sơ đồ chân |
