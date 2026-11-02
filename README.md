# AI-Powered Omni Robot

Robot omni 4 bánh điều khiển bằng **cử chỉ tay** qua camera laptop, kèm dashboard web để giám sát và điều khiển thủ công.

```
Camera laptop ──► AI nhận diện cử chỉ ──► Server (FastAPI) ──WiFi──► ESP32 ──► 4 motor + encoder
                                              │
                                              └──► Dashboard web (video + điều khiển)
```

## Tính năng

- [x] Đọc camera độ trễ thấp (thread riêng, chỉ giữ khung mới nhất, tự mở lại khi mất camera)
- [x] Dashboard web: video trực tiếp, cần điều khiển, phím W/A/S/D/Q/E, dừng khẩn cấp
- [x] Vòng điều khiển 20 Hz, tự dừng robot khi mất lệnh quá 0.4 s
- [ ] Tối ưu tốc độ khung hình stream
- [ ] Nhận diện cử chỉ tay (MediaPipe Hands) và chuyển thành lệnh di chuyển
- [ ] Giao diện web mới, có hiệu ứng
- [ ] Firmware ESP32: điều khiển motor, đọc encoder, PID tốc độ, nhận lệnh qua WiFi

## Phần cứng

| Linh kiện | Số lượng |
|---|---|
| ESP32 DevKit V1 | 1 |
| Driver L298N | 2 (một cho 2 bánh trước, một cho 2 bánh sau) |
| Motor DC có encoder + bánh omni | 4 |
| Laptop có webcam | 1 |

### Sơ đồ chân ESP32

![Sơ đồ chân](docs/pinout.png)

| Bánh | PWM | IN1 / IN3 | IN2 / IN4 | Encoder A | Encoder B |
|---|---|---|---|---|---|
| Trước trái | 25 | 26 | 27 | 36 | 39 |
| Trước phải | 13 | 23 | 22 | 34 | 35 |
| Sau trái | 21 | 19 | 18 | 32 | 33 |
| Sau phải | 17 | 16 | 4 | 14 | 5 |

> GPIO 34, 35, 36, 39 chỉ là chân input và không có điện trở kéo lên trong. Nếu encoder là loại open-collector thì cần gắn điện trở kéo lên ngoài (10 kΩ lên 3.3 V).

## Cấu trúc thư mục

```
ai/         camera.py: đọc camera laptop (sẽ thêm module nhận diện cử chỉ)
web/        server.py: FastAPI + WebSocket; static/: giao diện dashboard
firmware/   (sắp có) chương trình ESP32
tests/      camera_fps_test.py: đo FPS qua từng khâu xử lý
docs/       sơ đồ chân
```

## Cài đặt và chạy

```bash
git clone git@github.com:anhtai8568/ai-powered-omni-robot.git
cd ai-powered-omni-robot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Chạy dashboard:

```bash
python web/server.py
# mở http://127.0.0.1:8000/
```

Tùy chọn qua biến môi trường: `CAMERA_INDEX=1` (chọn camera khác), `HOST=0.0.0.0` (cho thiết bị khác trong mạng truy cập), `PORT=8000`.

Công cụ khác:

```bash
python ai/camera.py              # xem thử camera, bấm q để thoát
python tests/camera_fps_test.py  # đo FPS (tắt server trước)
```

## Quy ước lệnh điều khiển

Theo chuẩn ROS, mỗi giá trị nằm trong khoảng `-1..1`:

| Lệnh | Ý nghĩa |
|---|---|
| `vx > 0` | tiến |
| `vy > 0` | đi ngang sang trái |
| `w > 0` | xoay ngược chiều kim đồng hồ |
