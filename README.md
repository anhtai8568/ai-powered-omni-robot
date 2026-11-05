# AI-Powered Omni Robot

Robot omni 4 bánh (bánh chéo 45°) điều khiển bằng cử chỉ tay qua camera laptop.

**Bản 2 (nhánh `v2`, đang làm):** điều khiển toàn bộ bằng hai tay. Tay không thuận lái robot như bản 1.
Tay thuận điều khiển giao diện: di con trỏ, click, kéo thanh trượt và cần lái, xem thông số, đổi chế độ,
mở cài đặt, ẩn hình camera. Hướng nghiên cứu tiếp theo: `reports/`.

## Phiên bản 1 (`v1.0`): nhận diện ngón tay để điều khiển robot omni

Camera laptop -> MediaPipe (21 điểm bàn tay) -> phân loại cử chỉ bằng luật hình học -> lọc nhiễu,
giới hạn gia tốc -> UDP qua WiFi do ESP32 phát -> động học omni -> PID 4 bánh (encoder 8112 xung/vòng).

Kết quả đo trên robot thật (sàn nhà, tốc độ 22-88%):

| Hạng mục | Kết quả |
|---|---|
| Camera / AI | 30 khung/giây, nhận diện tay 18 ms/khung (CPU) |
| Cử chỉ | 8 hướng chỉ + xoay + dừng; 7 lần chập chờn / 120 lần đổi cử chỉ |
| Độ trễ cử chỉ được chốt -> bánh đạt 50% tốc độ | trung vị 260 ms (204-359 ms) |
| WiFi laptop - ESP32 | trễ khứ hồi trung vị 8 ms, 95% dưới 26 ms |
| Bám tốc độ từng bánh (PID) | sai số trung bình 1.5-3% tốc độ tối đa |
| Chuyển động robot so với lệnh (từ encoder) | lệch 0.5-2.5%, xoay ngoài ý muốn khi đi thẳng < 0.003 |

Dữ liệu gốc: `docs/data/v1/` (log chạy thủ công và bằng cử chỉ). Tính lại các số trên:
`python tests/analyze_drive_log.py docs/data/v1/drive_gesture.csv`. Quay lại bản này: `git checkout v1.0`.


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

```bash
nmcli device wifi connect omni-robot password omnirobot   # bật robot trước, không cần Internet
python web/server.py                                       # mở http://127.0.0.1:8000/
```

Ô "Robot" xanh là đã kết nối. Xong thì nối lại WiFi cũ: `nmcli connection up "<tên WiFi>"`.

## Cử chỉ

Ảnh đã lật gương: "trái" là bên trái của bạn. Hai tay độc lập, dùng cùng lúc được. Mặc định tay phải
điều khiển giao diện, tay trái lái robot (đổi trong Cài đặt).

Chế độ **Thủ công** chỉ cần một tay: tay nào đang thấy cũng điều khiển giao diện, kể cả kéo cần lái.
Chế độ **Cử chỉ tay** mới chia vai theo bên.

**Tay không thuận: lái robot** (bật bằng nút **Cử chỉ tay**)

| Cử chỉ | Robot |
|---|---|
| Ngón trỏ chỉ 8 hướng | Đi theo hướng chỉ |
| Chữ V chỉ trái / phải | Xoay trái / phải |
| Nắm tay, xòe tay, không thấy tay | Dừng |

**Tay thuận: giao diện**

| Cử chỉ | Tác dụng |
|---|---|
| Chỉ ngón trỏ | Di con trỏ |
| Giữ yên con trỏ trên nút (0.8 s, vòng tròn đầy dần) | Click |
| Giữ yên trên thanh trượt | Nắm thanh (viền xanh, giá trị không nhảy). Di ngón tay thì giá trị tăng giảm theo; dừng yên để nhả |
| Duỗi thêm ngón giữa | Bấm nhanh; giữ rồi di chuyển là kéo thanh trượt (cũng tương đối) hoặc cần lái |
| Rê lâu (0.5 s) lên nút hoặc chip trạng thái | Hiện thẻ thông số |
| Tư thế khác (xòe, nắm...) | Con trỏ ẩn, không bấm nhầm |

Nút **Dừng khẩn cấp** (phím Space) luôn dừng ngay. ESP32 tự dừng nếu mất lệnh quá 0.3 s.
Giơ tay trước camera 2 giây khi chưa mở dashboard thì trình duyệt tự mở (tắt: `HAND_OPEN=0`).

## Công cụ kiểm tra

Kê robot lên (bánh không chạm đất) trước khi chạy motor.

| Lệnh | Việc |
|---|---|
| `pio run -e motor_test -t upload -t monitor` | Gõ `1`-`4` chạy từng bánh, `t` đo tốc độ tối đa và vùng chết |
| `pio run -t upload -t monitor` | Firmware chính. Gõ `s` chạy kịch bản thử, `g kp ki ff` đổi hệ số PID |
| `pio device monitor` | Chỉ xem Serial, không nạp lại |
| `python ai/demo.py` | Xem AI nhận hai tay, vai trò và con trỏ (`left` nếu thuận tay trái) |
| `python tests/test_hands_logic.py` | Kiểm tra logic tay bằng bàn tay giả, không cần camera |
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
| `ai/` | `camera.py`, `hands.py` (2 tay, vai trò), `drive/` (cử chỉ lái), `ui/` (con trỏ) |
| `web/` | server và dashboard |
| `communication/` | gửi lệnh tới ESP32 qua UDP |
| `firmware/` | ESP32: WiFi, động học omni, PID |
| `tests/` | đo FPS camera, phân tích log chạy thật |
| `docs/` | sơ đồ chân, dữ liệu đo bản 1 |
