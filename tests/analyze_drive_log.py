"""
Phân tích log chạy thật (server ghi vào logs/, dữ liệu bản 1 ở docs/data/v1/).

    python tests/analyze_drive_log.py docs/data/v1/drive_gesture.csv

In ra: độ trễ WiFi, sai số bám tốc độ từng bánh, chuyển động robot suy ra từ 4 bánh so với
lệnh (động học thuận), và với chế độ cử chỉ: độ ổn định nhận diện, độ trễ cử chỉ -> bánh.
Tốc độ chuẩn hóa: 1.0 = 4300 xung/giây (xem firmware/src/robot_config.h).
"""
import csv
import statistics as st
import sys
from collections import Counter

W = ["tt", "tp", "st", "sp"]  # trước trái, trước phải, sau trái, sau phải
SETTLE = 6                    # số tick (0.3 s) lệnh phải giữ nguyên mới tính là ổn định


def f(r, k):
    return float(r[k])


def motor_unpowered(r):
    # Cả 4 bánh đứng yên dù PWM cao: nguồn motor đang tắt, không phải lỗi điều khiển
    return all(f(r, f"{w}_do") == 0 and abs(f(r, f"{w}_pwm")) > 0.9 for w in W)


def pct(xs, p):
    return sorted(xs)[int(p * (len(xs) - 1))]


def settled(rows, i, key):
    return all(abs(f(rows[j], key) - f(rows[i], key)) < 0.01 for j in range(i - SETTLE, i))


def main(path):
    rows = list(csv.DictReader(open(path)))
    bad = sum(motor_unpowered(r) for r in rows)
    rows = [r for r in rows if not motor_unpowered(r)]
    dur = f(rows[-1], "t") - f(rows[0], "t")
    print(f"{path}: {len(rows)} dòng, {dur:.0f} s (bỏ {bad} dòng lúc nguồn motor tắt)")
    print("Chế độ:", dict(Counter(r["mode"] for r in rows)))
    rtt = [f(r, "rtt_ms") for r in rows]
    print(f"Độ trễ WiFi: trung vị {st.median(rtt):.1f} ms, 95% {pct(rtt, .95):.1f} ms, max {max(rtt):.0f} ms")

    print("\nBám tốc độ khi lệnh ổn định (|lệnh| >= 0.1):")
    for w in W:
        err, pwm = [], []
        for i in range(SETTLE, len(rows)):
            T = f(rows[i], f"{w}_muon")
            if abs(T) >= 0.1 and settled(rows, i, f"{w}_muon"):
                err.append(abs(f(rows[i], f"{w}_do") - T))
                pwm.append(abs(f(rows[i], f"{w}_pwm")))
        print(f"  {w}: sai số TB {st.mean(err):.3f}, 95% {pct(err, .95):.3f} | PWM TB {st.mean(pwm):.2f}, max {max(pwm):.2f}")

    # Động học thuận (nghịch đảo của firmware/src/kinematics.h)
    def fk(v):
        return ((v[0] + v[1] + v[2] + v[3]) / 4, (-v[0] + v[1] + v[2] - v[3]) / 4, (-v[0] + v[1] - v[2] + v[3]) / 4)

    def motion(r):
        vx, vy, w = f(r, "vx"), f(r, "vy"), f(r, "w")
        names = [n for n, v, d in (("tiến", vx, 1), ("lùi", vx, -1), ("trái", vy, 1), ("phải", vy, -1),
                                   ("xoay trái", w, 1), ("xoay phải", w, -1)) if v * d >= 0.05]
        return "+".join(names) or "dừng"

    print("\nChuyển động: lệnh (vx vy w) | suy ra từ tốc độ đo 4 bánh")
    groups = {}
    for i in range(SETTLE, len(rows)):
        m = motion(rows[i])
        if m != "dừng" and all(motion(rows[j]) == m for j in range(i - SETTLE, i)):
            cmd = fk([f(rows[i], f"{w}_muon") for w in W])
            got = fk([f(rows[i], f"{w}_do") for w in W])
            groups.setdefault(m, []).append((cmd, got))
    for m, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        c = [st.mean(x[0][k] for x in v) for k in range(3)]
        g = [st.mean(x[1][k] for x in v) for k in range(3)]
        print(f"  {m:10} {c[0]:+.3f} {c[1]:+.3f} {c[2]:+.3f} | {g[0]:+.3f} {g[1]:+.3f} {g[2]:+.3f}  ({len(v)} mẫu)")

    gest = [r for r in rows if r["mode"] == "gesture"]
    if not gest:
        return
    segs, cur = [], [gest[0]]
    for r in gest[1:]:
        if r["gesture"] != cur[-1]["gesture"]:
            segs.append(cur)
            cur = [r]
        else:
            cur.append(r)
    segs.append(cur)
    length = lambda s: f(s[-1], "t") - f(s[0], "t") + 0.05
    moving = lambda g: g.startswith(("point", "v_"))
    short = Counter(s[0]["gesture"] or "không tay" for s in segs if length(s) < 0.3)
    print(f"\nCử chỉ: {len(segs)} lần đổi; kéo dài < 0.3 s (chập chờn): {sum(short.values())} {dict(short)}")
    print("Thời gian mỗi cử chỉ (s):", {g or "không tay": round(n / 20, 1) for g, n in Counter(r["gesture"] for r in gest).most_common()})

    # Độ trễ: AI chốt cử chỉ di chuyển -> bánh có lệnh lớn nhất đạt 50% tốc độ mới
    lat = []
    pos = {id(r): i for i, r in enumerate(gest)}
    for s in segs:
        if not moving(s[0]["gesture"]) or length(s) < 0.8:
            continue
        i0 = pos[id(s[0])]
        T = [f(s[-1], f"{w}_muon") for w in W]
        k = max(range(4), key=lambda j: abs(T[j]))
        s0 = f(gest[i0], f"{W[k]}_do")
        if abs(T[k] - s0) < 0.1:
            continue
        for r in gest[i0:i0 + 40]:
            if (f(r, f"{W[k]}_do") - s0) / (T[k] - s0) >= 0.5:
                lat.append((f(r, "t") - f(gest[i0], "t")) * 1000)
                break
    if lat:
        print(f"Cử chỉ được chốt -> bánh đạt 50% tốc độ mới: trung vị {st.median(lat):.0f} ms "
              f"({min(lat):.0f}-{max(lat):.0f} ms, {len(lat)} lần)")


if __name__ == "__main__":
    main(sys.argv[1])
