# AI-Powered Omni Robot

Robot omni 4 bánh (bánh chéo 45°) điều khiển bằng cử chỉ tay qua camera laptop.

```
Camera ──► AI cử chỉ ──► Server ──WiFi──► ESP32 ──► PID ──► 4 motor
                           └──► Dashboard web
```

## Cài đặt

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Firmware dùng [PlatformIO](https://platformio.org/). Nạp firmware chính (cắm ESP32 qua USB):

```bash
cd firmware
pio run -t upload
```

## Chạy

1. Bật robot, laptop bắt WiFi **omni-robot** (mật khẩu `omnirobot`). Không cần Internet.
2. `python web/server.py`, mở http://127.0.0.1:8000/. Ô "Robot" xanh là đã kết nối.

## Cử chỉ

Bật bằng nút **Cử chỉ tay**. Ảnh đã lật gương: "trái" là bên trái của bạn.

| Cử chỉ | Robot |
|---|---|
| Ngón trỏ chỉ 8 hướng | Đi theo hướng chỉ |
| Chữ V chỉ trái / phải | Xoay trái / phải |
| Nắm tay, xòe tay, không thấy tay | Dừng |

Nút **Dừng khẩn cấp** (phím Space) luôn dừng ngay. ESP32 tự dừng nếu mất lệnh quá 0.3 s.

## Công cụ kiểm tra

Kê robot lên (bánh không chạm đất) trước khi chạy motor.

| Lệnh | Việc |
|---|---|
| `pio run -e motor_test -t upload -t monitor` | Gõ `1`-`4` chạy từng bánh, `t` đo tốc độ tối đa và vùng chết |
| `pio run -t upload -t monitor` | Firmware chính. Gõ `s` chạy kịch bản thử, `g kp ki ff` đổi hệ số PID |
| `pio device monitor` | Chỉ xem Serial, không nạp lại |
| `python ai/gesture_recognition.py` | Xem AI nhận diện tay |
| `python communication/robot_link.py` | Gửi lệnh thử tới ESP32 (khi không chạy server) |

Lệnh `pio` chạy trong thư mục `firmware/`. Thoát bằng Ctrl+C.

## Phần cứng

ESP32 DevKit V1, 2 driver L298N, 4 motor GM25-370 (1:78, encoder 8112 xung/vòng bánh, cấp 3.3 V), nguồn 12 V.

![Sơ đồ chân](docs/pinout.png)

| Bánh | PWM | IN1 | IN2 | Encoder A | Encoder B |
|---|---|---|---|---|---|
| Trước trái | 25 | 26 | 27 | 36 | 39 |
| Trước phải | 13 | 23 | 22 | 34 | 35 |
| Sau trái | 21 | 19 | 18 | 32 | 33 |
| Sau phải | 17 | 16 | 4 | 14 | 5 |

## Thư mục

| | |
|---|---|
| `ai/` | camera, nhận diện cử chỉ |
| `web/` | server và dashboard |
| `communication/` | gửi lệnh tới ESP32 qua UDP |
| `firmware/` | ESP32: WiFi, động học omni, PID |
| `tests/` | đo FPS camera |
