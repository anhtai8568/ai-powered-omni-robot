"""
Kiểm tra logic tay bằng bàn tay giả (21 điểm dựng bằng toán, không cần camera):
phân loại cử chỉ lái, gán vai trò hai tay, con trỏ (tư thế, lọc mượt, chống lệch khi click).

    python tests/test_hands_logic.py
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai.drive.gestures import classify  # noqa: E402
from ai.hands import FINGERS, Hand, RoleAssigner, split_roles  # noqa: E402
from ai.ui.cursor import Cursor, OneEuro, ui_pose  # noqa: E402

W, H = 640, 480
FINGER_DIR = {"index": -0.15, "middle": 0.0, "ring": 0.15, "pinky": 0.3}  # lệch góc quạt các ngón


def make_hand(extended, wrist=(320, 400), tip_dx=0.0, tip_dy=0.0, point_angle=90.0):
    """Bàn tay giả: cổ tay ở `wrist`, các ngón trong `extended` duỗi theo hướng point_angle (độ, 90 = lên),
    ngón còn lại gập. Đầu ngón trỏ dịch thêm (tip_dx, tip_dy) pixel."""
    pts = [wrist] * 21
    base = math.radians(point_angle)
    for name, (tip, pip) in FINGERS.items():
        a = base + FINGER_DIR[name]
        ux, uy = math.cos(a), -math.sin(a)
        mcp = tip - 3
        pts[mcp] = (wrist[0] + ux * 60, wrist[1] + uy * 60)
        pts[pip] = (wrist[0] + ux * 100, wrist[1] + uy * 100)
        far = 160 if name in extended else 70   # duỗi: đầu ngón xa cổ tay hơn khớp giữa; gập: gần hơn
        pts[tip] = (wrist[0] + ux * far, wrist[1] + uy * far)
    pts[8] = (pts[8][0] + tip_dx, pts[8][1] + tip_dy)
    return pts


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        check.failed += 1


check.failed = 0

# ---- 1. Cử chỉ lái (bản 1) vẫn đúng sau khi tách thư mục ----
check("nắm tay -> fist", classify(make_hand(set())) == "fist")
check("xòe tay -> palm", classify(make_hand(set(FINGERS))) == "palm")
for ang, want in ((90, "point_up"), (0, "point_right"), (180, "point_left"), (270, "point_down"),
                  (45, "point_up_right"), (135, "point_up_left")):
    check(f"chỉ {ang} độ -> {want}", classify(make_hand({"index"}, point_angle=ang)) == want)
check("chữ V sang phải -> v_right", classify(make_hand({"index", "middle"}, point_angle=0)) == "v_right")
check("không có tay -> None", classify(None) is None)

# ---- 2. Tư thế của tay giao diện ----
check("trỏ -> point", ui_pose(make_hand({"index"})) == "point")
check("trỏ + giữa -> click", ui_pose(make_hand({"index", "middle"})) == "click")
check("xòe -> idle", ui_pose(make_hand(set(FINGERS))) == "idle")
check("nắm -> idle", ui_pose(make_hand(set())) == "idle")
check("trỏ + giữa + áp út -> idle", ui_pose(make_hand({"index", "middle", "ring"})) == "idle")

# ---- 3. Vai trò hai tay ----
ra = RoleAssigner()
left_on_screen, right_on_screen = make_hand({"index"}, wrist=(180, 400)), make_hand({"index"}, wrist=(460, 400))
hands = ra.assign([Hand(right_on_screen, "Left"), Hand(left_on_screen, "Left")])  # nhãn MediaPipe cố tình sai
check("2 tay: tay bên trái ảnh = left, bên phải = right (bỏ qua nhãn sai)",
      {h.side for h in hands} == {"left", "right"} and min(hands, key=lambda h: h.pts[0][0]).side == "left")
ui, drive = split_roles(hands, "right")
check("tay thuận phải -> giao diện là tay bên phải ảnh", ui.pts[0][0] > 320 and drive.pts[0][0] < 320)
ui, drive = split_roles(hands, "left")
check("đổi tay thuận trái -> hai vai trò đổi chỗ", ui.pts[0][0] < 320 and drive.pts[0][0] > 320)
only_right = ra.assign([Hand(make_hand({"index"}, wrist=(465, 400)), "Right")])  # nhãn "ngược", nhưng ở gần tay phải vừa thấy
check("2 tay -> còn 1 tay ở gần chỗ cũ: giữ vai trò theo vị trí, không theo nhãn", only_right[0].side == "right")
fresh = RoleAssigner().assign([Hand(make_hand({"index"}), "Left")])
check('1 tay, chưa có lịch sử: nhãn MediaPipe "Left" nghĩa là tay PHẢI (ảnh đã lật)', fresh[0].side == "right")
fresh = RoleAssigner().assign([Hand(make_hand({"index"}), "Right")])
check('1 tay, nhãn MediaPipe "Right" nghĩa là tay TRÁI', fresh[0].side == "left")

# đo trên máy thật: chỉ giơ tay phải thì MediaPipe gắn nhãn "Left" 251/253 khung, 2 khung đầu gắn nhãn "Right"
rb = RoleAssigner()
seq = ["Right", "Right"] + ["Left"] * 30
sides = [rb.assign([Hand(make_hand({"index"}, wrist=(460, 400)), lab)])[0].side for lab in seq]
check("nhãn nhầm ở 2 khung đầu: cuối cùng vẫn đúng là tay phải", sides[-1] == "right")
check("nhãn nhầm thoáng qua giữa chừng không đổi vai", all(s == "right" for s in sides[4:]))
rb = RoleAssigner()
seq = ["Left"] * 20 + ["Right"] * 2 + ["Left"] * 10
sides = [rb.assign([Hand(make_hand({"index"}, wrist=(460, 400)), lab)])[0].side for lab in seq]
check("tay phải đang ổn định, 2 khung nhãn sai: không bị đổi sang tay lái", all(s == "right" for s in sides))
rb = RoleAssigner()
rb.assign([])
sides = [rb.assign([Hand(make_hand({"index"}, wrist=(180, 400)), "Right")])[0].side for _ in range(5)]
check("tay trái (nhãn Right) xuất hiện riêng: vai tay trái", all(s == "left" for s in sides))
# hạ tay rồi giơ tay kia vào đúng chỗ cũ: không được kế thừa vai cũ
rb = RoleAssigner()
for _ in range(15): rb.assign([Hand(make_hand({"index"}, wrist=(460, 400)), "Left")])
rb.assign([])
sides = [rb.assign([Hand(make_hand({"index"}, wrist=(460, 400)), "Right")])[0].side for _ in range(5)]
check("hạ tay phải, giơ tay trái vào cùng chỗ: nhận là tay trái", sides[-1] == "left")

# tự hiệu chỉnh: hai tay nhưng nhãn khớp vị trí kiểu KHÔNG đổi (Left bên trái ảnh) liên tục -> đổi quy ước
rc = RoleAssigner()
for _ in range(60):
    rc.assign([Hand(make_hand({"index"}, wrist=(180, 400)), "Left"), Hand(make_hand({"index"}, wrist=(460, 400)), "Right")])
check("nhãn mâu thuẫn quy ước hiện tại nhiều lần: tự đổi quy ước", rc.flipped is False)
rc.assign([])
check("sau khi tự đổi: 1 tay nhãn Left -> tay trái", rc.assign([Hand(make_hand({"index"}, wrist=(180, 400)), "Left")])[0].side == "left")
rd = RoleAssigner()
for _ in range(60):
    rd.assign([Hand(make_hand({"index"}, wrist=(180, 400)), "Right"), Hand(make_hand({"index"}, wrist=(460, 400)), "Left")])
check("nhãn khớp quy ước hiện tại: giữ nguyên quy ước", rd.flipped is True)

# Chế độ Thủ công: không có tay lái, tay nào đang thấy cũng là tay giao diện
only_one = [Hand(make_hand({"index"}, wrist=(180, 400)), "Right", side="left")]   # chỉ tay trái, kể cả khi bị đoán là tay lái
ui, drive = split_roles(only_one, "right", drive_active=True)
check("Cử chỉ: chỉ tay trái -> là tay lái, không có tay giao diện", ui is None and drive is only_one[0])
ui, drive = split_roles(only_one, "right", drive_active=False)
check("Thủ công: chỉ một tay (dù bị đoán là tay lái) -> là tay giao diện", ui is only_one[0] and drive is None)
both = [Hand(make_hand({"index"}, wrist=(180, 400)), "Right", side="left"), Hand(make_hand({"index"}, wrist=(460, 400)), "Left", side="right")]
ui, drive = split_roles(both, "right", drive_active=False)
check("Thủ công: có cả hai tay -> tay thuận làm giao diện, không có tay lái", ui.side == "right" and drive is None)
ui, drive = split_roles([], "right", drive_active=False)
check("Thủ công: không thấy tay -> không có gì", ui is None and drive is None)

# ---- 4. Con trỏ ----
random.seed(1)


def run(cursor, frames, t0=0.0, fps=30):
    out = []
    for i, pts in enumerate(frames):
        out.append(cursor.update(pts, W, H, t0 + i / fps))
    return out


c = Cursor(region=0.65)
out = run(c, [make_hand({"index"}) for _ in range(10)])
check("tay trỏ xuất hiện: sau 3 khung tư thế là point", out[1]["pose"] == "none" and out[3]["pose"] == "point")
check("không thấy tay: sau thời gian ân hạn thì none",
      run(c, [None] * 12, t0=1.0)[-1]["pose"] == "none")

# lọc mượt: tay đứng yên + nhiễu 2 px -> con trỏ rung ít hơn nhiều so với không lọc
c = Cursor(region=0.65)
raw_xs, out_xs = [], []
for i in range(90):
    jx, jy = random.gauss(0, 2), random.gauss(0, 2)
    o = c.update(make_hand({"index"}, tip_dx=jx, tip_dy=jy), W, H, i / 30)
    if i > 30:
        out_xs.append(o["x"])
        raw_xs.append(0.5 + (320 + jx - 320) / W / 0.65)  # vị trí không lọc (chuẩn hóa, cùng cách ánh xạ)
sd = lambda v: math.sqrt(sum((a - sum(v) / len(v)) ** 2 for a in v) / len(v))
check(f"lọc mượt: độ rung giảm (không lọc {sd(raw_xs):.4f} -> có lọc {sd(out_xs):.4f})", sd(out_xs) < 0.6 * sd(raw_xs))

# tay di nhanh: không trễ quá nhiều
c = Cursor(region=0.65)
xs = []
for i in range(60):
    o = c.update(make_hand({"index"}, tip_dx=min(i, 30) * 6), W, H, i / 30)  # tay đi 180 px trong 1 s rồi dừng
    xs.append(o["x"])
target = (make_hand({"index"}, tip_dx=180)[8][0] / W - 0.5) / 0.65 + 0.5
check(f"tay đi nhanh rồi dừng: sau 0.2 s con trỏ cách đích {abs(xs[36] - target) * W * 0.65:.1f} px", abs(xs[36] - target) * W * 0.65 < 3)

# mặc định (region 1.0): con trỏ trùng đúng đầu ngón trỏ trong khung camera
c = Cursor()
for i in range(40):
    o = c.update(make_hand({"index"}, tip_dx=60, tip_dy=-40), W, H, i / 30)
tip = make_hand({"index"}, tip_dx=60, tip_dy=-40)[8]
check(f"con trỏ trùng đầu ngón trỏ: lệch {abs(o['x'] - tip[0] / W) * W:.2f} px ngang, {abs(o['y'] - tip[1] / H) * H:.2f} px dọc",
      abs(o["x"] - tip[0] / W) * W < 1 and abs(o["y"] - tip[1] / H) * H < 1)
check("chỉ trỏ: điểm tác động trùng con trỏ", o["ax"] == o["x"] and o["ay"] == o["y"])

# chống lệch khi click: duỗi ngón giữa làm đầu ngón trỏ xê dịch 25 px -> ĐIỂM TÁC ĐỘNG không được nhảy,
# còn con trỏ hiển thị vẫn bám đầu ngón tay
c = Cursor(region=0.65)
frames = [make_hand({"index"}) for _ in range(30)]                                        # trỏ yên 1 s
frames += [make_hand({"index", "middle"}, tip_dx=25, tip_dy=-15) for _ in range(15)]      # duỗi giữa: đầu trỏ xê dịch
out = run(c, frames)
before = out[29]
during = out[-1]
shift = math.hypot(during["ax"] - before["ax"], during["ay"] - before["ay"])
shown = math.hypot(during["x"] - before["x"], during["y"] - before["y"])
unfixed = math.hypot(25 / W / 0.65, 15 / H / 0.65)
check("duỗi ngón giữa: tư thế -> click", during["pose"] == "click")
check(f"chống lệch: điểm tác động lệch {shift:.4f} (không chống: {unfixed:.4f})", shift < 0.25 * unfixed)
check(f"con trỏ hiển thị vẫn bám đầu ngón tay: dịch {shown:.4f} (đầu ngón dịch {unfixed:.4f})", abs(shown - unfixed) < 0.1 * unfixed)

# kéo: trong lúc click, tay di 60 px thì con trỏ đi theo
frames2 = [make_hand({"index", "middle"}, tip_dx=25 + i * 4, tip_dy=-15) for i in range(15)]
out2 = run(c, frames2, t0=1.0)
moved = out2[-1]["ax"] - during["ax"]
check(f"kéo khi click: tay đi 56 px, điểm tác động đi {moved * W * 0.65:.0f} px", 40 < moved * W * 0.65 < 70)

# nhả click: con trỏ không giật
frames3 = [make_hand({"index"}, tip_dx=25 + 56, tip_dy=0) for _ in range(20)]
out3 = run(c, frames3, t0=2.0)
step = max(abs(b["ax"] - a["ax"]) for a, b in zip(out3, out3[1:]))
check(f"nhả click: điểm tác động không nhảy (bước lớn nhất {step:.4f})", step < 0.03)

# tư thế thoáng qua (1 khung) không làm đổi tư thế
c = Cursor(region=0.65)
frames = [make_hand({"index"}) for _ in range(10)] + [make_hand({"index", "middle"})] + [make_hand({"index"}) for _ in range(5)]
out = run(c, frames)
check("1 khung 'click' thoáng qua không làm bấm nhầm", all(o["pose"] != "click" for o in out))

# OneEuro cơ bản
f = OneEuro()
check("OneEuro: giá trị đầu giữ nguyên", f(0.3, 0.0) == 0.3)

print(f"\n{'TẤT CẢ ĐỀU ĐẠT' if check.failed == 0 else str(check.failed) + ' BÀI KHÔNG ĐẠT'}")
sys.exit(1 if check.failed else 0)
