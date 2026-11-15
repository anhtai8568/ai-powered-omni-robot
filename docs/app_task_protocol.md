# Thí nghiệm ứng dụng: vận hành robot không chạm

Mục đích: cho bài báo (mục 3, *Application Scenario*) có số liệu thật cho câu hỏi "người vận hành có lái robot và
dùng dashboard được không, khi không chạm vào thiết bị nào". So sánh ba cách điều khiển trên cùng một đường đi.

| Điều kiện | Lái robot | Dashboard (tốc độ, dừng khẩn cấp) | Chế độ |
|---|---|---|---|
| **C1** không chạm (hệ thống của bài) | tay trái, cử chỉ | tay phải, con trỏ cử chỉ | Cử chỉ |
| **C2** lai | tay trái, cử chỉ | tay phải cầm **chuột** | Cử chỉ |
| **C3** truyền thống | chuột kéo cần lái ảo | chuột | Thủ công |

C1 so với C3 cho biết cái giá (hoặc cái lợi) của việc không chạm. C1 so với C2 tách riêng phần con trỏ cử chỉ.

## 1. Đường đi

Đo **L = kích thước lớn nhất của robot nhìn từ trên xuống** (tính cả bánh). Các bề rộng dưới đây tính theo L.

```
                 phía xa người lái (y)
                        ^
   1.8 m  .  .  .  .  . | .  .  .  .  .  .  .
                        |
            B ┌───┐  cọc   ┌───┐ A
   1.5 m      │ ↻ │ ◦   ◦  │   │        ← đoạn 2: đi NGANG sang trái 1.0 m qua cổng (hai cọc)
              └───┘ cổng   └───┘
               ↙              ║
              ↙  đoạn 3       ║  hành lang L+30 cm
             ↙   chéo 1.2 m   ║  đoạn 1: đi THẲNG 1.5 m
   0.65 m ┌───┐               ║
          │ F │ đích          ║
          └───┘             ┌───┐
   0.0 m                    │ S │ xuất phát (robot quay mặt về phía xa)
                            └───┘
         -1.85 m    -1.0 m  0.0 m  → x
   ─────────────────────────────────────────────
          laptop + webcam, người lái đứng cách camera 1–1.5 m, nhìn thấy cả robot lẫn màn hình
```

| Ô / đoạn | Kích thước | Việc phải làm |
|---|---|---|
| **S** xuất phát | vuông L+10 cm | robot đặt giữa ô, mặt quay về phía xa người lái, tốc độ trên dashboard = 0.50 |
| **Đoạn 1** | thẳng 1.5 m, hành lang rộng L+30 cm (hai vạch băng dính) | đi tới |
| **A** | vuông L+20 cm | dừng trong ô, **giảm tốc độ xuống ≤ 0.30** trên dashboard (vùng chậm trước cổng hẹp) |
| **Đoạn 2** | ngang sang trái 1.0 m, giữa đường có **cổng**: hai cọc (chai nhựa) cách nhau L+15 cm | đi ngang, không xoay thân (đây là khả năng riêng của robot omni) |
| **B** | vuông L+20 cm, vẽ mũi tên chỉ hướng mới | **xoay trái 90°** tại chỗ, rồi **tăng tốc độ lên ≥ 0.60** trên dashboard |
| **Đoạn 3** | chéo khoảng 1.2 m (sau khi xoay, là hướng "tới-trái" của robot) | đi chéo vào ô đích |
| **F** đích | vuông L+10 cm | khi robot nằm gọn trong ô, **bấm dừng khẩn cấp** trên dashboard: lượt kết thúc |

Diện tích cần khoảng **2.5 m × 2.2 m** sàn phẳng (nên dùng lại sàn đã chạy các phiên trước), cộng chỗ đặt laptop.

**Lỗi** (người phụ bấm `x`): robot chạm hoặc vượt vạch hành lang, chạm hoặc làm đổ cọc, rời ô A/B trước khi làm xong
thao tác trên dashboard. **Can thiệp** (`r`): người phụ phải cầm robot đặt lại (đặt về ô vừa qua rồi đi tiếp).

## 2. Chuẩn bị (trước khi bắt đầu)

- [ ] Sạc **đầy pin** robot (phiên A trước đây bị bão hòa PWM ở tốc độ cao khi pin yếu).
- [ ] Băng dính giấy (hai màu nếu có), 2 chai nhựa làm cọc, thước dây; dán ô và hành lang theo bảng trên.
- [ ] Ánh sáng đủ và đều, không có cửa sổ sáng ngay sau lưng người lái.
- [ ] Điện thoại quay video **toàn bộ đường đi** từ trên cao ở một góc (để đếm lại lỗi, và để có **ảnh robot +
      dashboard cho bài báo**; bài v1 còn thiếu ảnh này).
- [ ] Nếu có: đeo **găng tay** y tế khi chạy C1 (ảnh minh họa đúng kịch bản không chạm).
- [ ] Chạy thử C2 một lần: khi tay phải cầm chuột, chỉ còn một tay trong khung hình; kiểm tra tay trái vẫn được nhận là
      tay lái.

## 3. Chạy

Terminal 1 (server, tự ghi log vào `logs/`):

```bash
source .venv/bin/activate
python web/server.py
```

Terminal 2 (người phụ đánh dấu mốc; **cùng laptop** để chung đồng hồ):

```bash
python tests/app_task_marker.py --operator tai --condition C1
```

Phím: `s` robot rời ô S · `a` vào ô A · `b` vào ô B · `f` vào ô đích · `x` lỗi · `r` can thiệp ·
`u` xóa mốc vừa bấm · `n` lượt mới · `c` đổi điều kiện · `q` thoát.

**Thứ tự** (mỗi người lái):

1. **Tập**: mỗi điều kiện 2 lượt, **không** đánh dấu (hoặc dùng `--operator tai_tap`).
2. **Ghi**: 5 khối, mỗi khối đủ ba điều kiện, đổi thứ tự để công bằng (hiệu ứng quen tay chia đều):

   | Khối | 1 | 2 | 3 | 4 | 5 |
   |---|---|---|---|---|---|
   | Thứ tự | C1 C2 C3 | C2 C3 C1 | C3 C1 C2 | C1 C2 C3 | C2 C3 C1 |

   Tổng 15 lượt, khoảng 1–1.5 phút mỗi lượt, cả buổi khoảng 45–60 phút.
3. Giữa hai lượt: người phụ đặt robot về S, người lái tắt dừng khẩn cấp và đặt tốc độ 0.50 (không tính giờ), người phụ
   bấm `n` (và `c` nếu đổi điều kiện), sau đó mới bắt đầu.

Người lái **không được chạm** vào laptop trong C1; trong C2 chỉ chạm chuột. Nếu có thêm bạn bè, mỗi người chạy cùng
thứ tự (ít nhất 3 lượt mỗi điều kiện) với `--operator <tên>`: nhiều người lái làm kết quả mạnh hơn nhiều so với một người.

## 4. Sau khi chạy

```bash
python tests/app_task_analyze.py logs/task_<ngày>.csv --out docs/data/v2/app_task
```

Script ghép mốc với `run_*.log`, `ai_*.csv`, `drive_*.csv` và cho mỗi lượt: thời gian hoàn thành (từ `s` đến lúc bấm
dừng khẩn cấp), thời gian từng đoạn, số lỗi và can thiệp, thời gian thao tác dashboard ở A, B và ở đích, số lần dừng
giữa đường, tỉ lệ khung mất tay; rồi tóm tắt theo điều kiện và vẽ `fig_app_task.png`.

Chép thêm vào `docs/data/v2/app_task/` các tệp `logs/task_*.csv` và `logs/run_*.log`, `ai_*.csv`, `drive_*.csv` của
buổi chạy, cùng vài ảnh, để số liệu trong bài báo truy lại được.
