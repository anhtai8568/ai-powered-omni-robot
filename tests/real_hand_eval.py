"""
Đo con trỏ trên bàn tay THẬT qua camera (các số trong bài báo hiện chỉ đo trên bàn tay mô phỏng).

    python tests/real_hand_eval.py                 # 8 lần click
    python tests/real_hand_eval.py --trials 12 --label ban_ngay
    CAMERA_INDEX=1 python tests/real_hand_eval.py

Tắt server.py trước (camera chỉ mở được bởi một chương trình). Ngồi cách camera như lúc dùng thật, một bàn tay
trong khung (bàn tay nào cũng được). Chương trình in hướng dẫn từng bước; không cần chuột hay bàn phím.

Phần A (rung): giữ yên ngón trỏ 8 giây. So độ lệch chuẩn của đầu ngón trỏ thô (MediaPipe) và của con trỏ đã lọc One-Euro.
Phần B (lệch khi click): chỉ ngón trỏ GIỮ THẬT YÊN (chương trình kiểm tra đầu ngón đứng yên trong 3 px suốt 1 giây mới cho duỗi ngón giữa; lần nào tay còn trôi thì bị loại), rồi duỗi ngón giữa. Đo đầu ngón trỏ thô dịch bao nhiêu pixel,
con trỏ hiển thị dịch bao nhiêu, và điểm tác động (FREEZE_BACK) dịch bao nhiêu.

Kết quả in ra và lưu logs/real_hand_eval_<nhãn>_<giờ>.csv (mỗi lần click một dòng).
"""
import argparse
import csv
import math
import os
import statistics as st
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ai.camera import Camera  # noqa: E402
from ai.hands import HandTracker  # noqa: E402
from ai.ui.cursor import Cursor  # noqa: E402

TIP = 8  # đầu ngón trỏ
STILL_PX = 3.0   # đầu ngón trỏ thô phải nằm trong vòng này (quanh vị trí trung bình) suốt 1 giây trước khi duỗi ngón giữa
STILL_S = 1.0


def say(msg):
    print(msg, flush=True)


def sd(v):
    return st.pstdev(v) if len(v) > 1 else float("nan")


class Rig:
    """Đọc camera, dò tay, chạy Cursor thật; mỗi bước trả về một dòng dữ liệu."""

    def __init__(self):
        self.cam = Camera().start()
        self.tr = HandTracker()
        self.cur = Cursor(region=1.0)  # region 1.0: con trỏ trùng đầu ngón tay, đơn vị = pixel khung camera
        self.last = -1
        self.t0 = time.monotonic()

    def step(self):
        self.last, frame = self.cam.read(self.last, 1.0)
        if frame is None:
            return None
        t = time.monotonic() - self.t0
        h, w = frame.shape[:2]
        hands = self.tr.detect(frame)
        pts = hands[0].pts if hands else None
        s = self.cur.update(pts, w, h, t)
        row = {"t": t, "pose": s["pose"], "hand": pts is not None,
               "raw": pts[TIP] if pts else None,
               "x": s["x"] * w, "y": s["y"] * h, "ax": s["ax"] * w, "ay": s["ay"] * h}
        return row

    def close(self):
        self.cam.stop()
        self.tr.close()


def mean_xy(rows, key_x, key_y):
    xs = [r[key_x] for r in rows]
    ys = [r[key_y] for r in rows]
    return st.mean(xs), st.mean(ys)


def part_a(rig, seconds=8.0):
    say("\n=== PHẦN A: rung khi giữ yên ===")
    say("Chỉ ngón trỏ (các ngón khác gập), giữ yên thật yên, khi thấy 'BẮT ĐẦU'. Chờ thấy tay...")
    ok_since = None
    while True:  # chờ tư thế point ổn định 1 giây
        r = rig.step()
        if r is None:
            continue
        if r["pose"] == "point":
            ok_since = ok_since or r["t"]
            if r["t"] - ok_since > 1.0:
                break
        else:
            ok_since = None
    say("BẮT ĐẦU: giữ yên ngón trỏ %.0f giây..." % seconds)
    rows, t_end = [], time.monotonic() + seconds
    while time.monotonic() < t_end:
        r = rig.step()
        if r and r["hand"] and r["pose"] == "point":
            rows.append(r)
    rows = [r for r in rows if r["t"] - rows[0]["t"] > 1.0]  # bỏ 1 giây đầu cho bộ lọc ổn định
    if len(rows) < 30:
        say("Không đủ dữ liệu (tay mất khỏi khung hoặc không còn tư thế trỏ).")
        return None
    raw_x, raw_y = [r["raw"][0] for r in rows], [r["raw"][1] for r in rows]
    out = {"frames": len(rows), "raw_sd_x": sd(raw_x), "raw_sd_y": sd(raw_y),
           "filt_sd_x": sd([r["x"] for r in rows]), "filt_sd_y": sd([r["y"] for r in rows])}
    raw = math.hypot(out["raw_sd_x"], out["raw_sd_y"])
    filt = math.hypot(out["filt_sd_x"], out["filt_sd_y"])
    out["reduction"] = 1 - filt / raw if raw else float("nan")
    say("Rung (độ lệch chuẩn, pixel): thô x %.2f y %.2f | sau lọc x %.2f y %.2f | giảm %.0f%%" % (
        out["raw_sd_x"], out["raw_sd_y"], out["filt_sd_x"], out["filt_sd_y"], 100 * out["reduction"]))
    return out


def one_click(rig, n, total):
    say(f"\n--- Lần {n}/{total}: chỉ ngón trỏ vào một điểm và GIỮ THẬT YÊN (đừng di tay) ---")
    hist = []
    t_wait = time.monotonic() + 25
    while time.monotonic() < t_wait:  # chờ: tư thế point VÀ đầu ngón đứng yên trong STILL_PX suốt STILL_S giây
        r = rig.step()
        if r is None:
            continue
        hist.append(r)
        if r["pose"] != "point" or not r["raw"]:
            continue
        win = [h for h in hist if r["t"] - STILL_S <= h["t"] <= r["t"]]
        if (win[0]["t"] > r["t"] - STILL_S + 0.15 or any(h["pose"] != "point" or not h["raw"] for h in win)):
            continue
        mx, my = mean_xy([dict(rx=h["raw"][0], ry=h["raw"][1]) for h in win], "rx", "ry")
        if max(math.hypot(h["raw"][0] - mx, h["raw"][1] - my) for h in win) <= STILL_PX:
            break
    else:
        say("  tay không đứng yên đủ lâu, bỏ lần này (đặt khuỷu tay lên bàn cho khỏi rung)")
        return None
    say("  >>> DUỖI NGÓN GIỮA bây giờ, rồi giữ nguyên 1 giây <<<")
    t_click, t_limit = None, time.monotonic() + 6
    while time.monotonic() < t_limit:
        r = rig.step()
        if r is None:
            continue
        hist.append(r)
        if r["pose"] == "click":
            t_click = r["t"]
            break
    if t_click is None:
        say("  không thấy tư thế click, bỏ lần này")
        return None
    t_end = time.monotonic() + 1.0
    while time.monotonic() < t_end:
        r = rig.step()
        if r:
            hist.append(r)
    say("  hạ ngón giữa (co lại), thả lỏng tay...")
    # cửa sổ: trước (ổn định, ngón giữa chưa nhúc nhích) và sau (đang giữ click)
    pre = [r for r in hist if t_click - 0.6 <= r["t"] <= t_click - 0.3 and r["hand"] and r["raw"]]
    post = [r for r in hist if t_click + 0.3 <= r["t"] <= t_click + 0.8 and r["hand"] and r["raw"]]
    mid = [r for r in hist if t_click <= r["t"] <= t_click + 0.5 and r["hand"]]
    if len(pre) < 3 or len(post) < 3:
        say("  tay mất khỏi khung, bỏ lần này")
        return None
    for r in pre + post:
        r["rx"], r["ry"] = r["raw"]
    drift = max(math.hypot(r["rx"] - st.mean(q["rx"] for q in pre), r["ry"] - st.mean(q["ry"] for q in pre)) for r in pre)
    if drift > 2 * STILL_PX:
        say("  tay còn trôi %.1f px trước khi duỗi ngón giữa, bỏ lần này" % drift)
        return None
    px, py = mean_xy(pre, "rx", "ry")
    qx, qy = mean_xy(post, "rx", "ry")
    finger = math.hypot(qx - px, qy - py)
    ax0, ay0 = mean_xy(pre, "ax", "ay")
    ax1, ay1 = mean_xy(post, "ax", "ay")
    cx0, cy0 = mean_xy(pre, "x", "y")
    cx1, cy1 = mean_xy(post, "x", "y")
    action = math.hypot(ax1 - ax0, ay1 - ay0)
    shown = math.hypot(cx1 - cx0, cy1 - cy0)
    transient = max(math.hypot(r["ax"] - ax0, r["ay"] - ay0) for r in mid)
    row = {"finger_px": round(finger, 1), "shown_px": round(shown, 1), "action_px": round(action, 1),
           "action_peak_px": round(transient, 1), "pre_drift_px": round(drift, 1)}
    say("  đầu ngón trỏ dịch %.1f px | con trỏ hiển thị dịch %.1f px | điểm tác động dịch %.1f px (đỉnh %.1f px)" % (
        finger, shown, action, transient))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--label", default="thuc")
    ap.add_argument("--no-jitter", action="store_true", help="bỏ phần A")
    args = ap.parse_args()

    rig = Rig()
    say("Camera mở. Đưa một bàn tay vào khung hình (ngồi như lúc dùng thật).")
    t_open = time.monotonic()
    while rig.step() is None and time.monotonic() - t_open < 10:
        pass
    results, jitter = [], None
    try:
        if not args.no_jitter:
            jitter = part_a(rig)
        say("\n=== PHẦN B: lệch khi click (duỗi ngón giữa) ===")
        for n in range(1, args.trials + 1):
            r = one_click(rig, n, args.trials)
            if r:
                results.append(r)
            time.sleep(1.0)
    except KeyboardInterrupt:
        say("\nDừng sớm, tổng kết các lần đã đo.")
    finally:
        rig.close()

    say("\n===== KẾT QUẢ =====")
    if jitter:
        say("Rung khi giữ yên: thô %.2f px, sau lọc %.2f px, giảm %.0f%% (%d khung)" % (
            math.hypot(jitter["raw_sd_x"], jitter["raw_sd_y"]), math.hypot(jitter["filt_sd_x"], jitter["filt_sd_y"]),
            100 * jitter["reduction"], jitter["frames"]))
    if results:
        f = [r["finger_px"] for r in results]
        a = [r["action_px"] for r in results]
        p = [r["action_peak_px"] for r in results]
        say("Click hợp lệ: %d/%d lần" % (len(results), args.trials))
        say("Đầu ngón trỏ dịch khi duỗi ngón giữa: trung vị %.1f px (khoảng %.1f-%.1f)" % (st.median(f), min(f), max(f)))
        say("Điểm tác động dịch (đã bù FREEZE_BACK): trung vị %.1f px (khoảng %.1f-%.1f); đỉnh thoáng qua trung vị %.1f px" % (
            st.median(a), min(a), max(a), st.median(p)))
        if st.median(f) > 0:
            say("Giảm độ lệch: %.0f%% (so trung vị)" % (100 * (1 - st.median(a) / st.median(f))))
        out = ROOT / "logs"
        out.mkdir(exist_ok=True)
        path = out / time.strftime(f"real_hand_eval_{args.label}_%Y%m%d_%H%M%S.csv")
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(results[0]))
            w.writeheader()
            w.writerows(results)
        say("Đã lưu %s" % path)
    else:
        say("Chưa có lần click hợp lệ nào.")


if __name__ == "__main__":
    main()
