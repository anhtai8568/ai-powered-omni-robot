"""
Phân tích một lần chạy server.py: ghép logs/ai_<giờ>.csv (từng khung AI) với logs/drive_<giờ>.csv (4 bánh, 20 Hz).

    python tests/analyze_run.py logs/ai_20261112_185804.csv logs/drive_20261112_185814.csv

Hai tệp dùng chung đồng hồ time.time(). In ra:
  - Tốc độ khung và thời gian suy luận tay, tách theo số tay trong khung (0 / 1 / 2).
  - Độ trễ từ khung camera mà bộ lọc chốt cử chỉ mới đến khi bánh tải nhiều nhất đạt 50% tốc độ mới.
    (Chưa gồm khoảng chốt cử chỉ: GestureFilter cần 4 khung liên tiếp, xem 'chốt' bên dưới.)
  - Sai số bám tốc độ theo chế độ (thủ công / cử chỉ) và số tick PWM chạm trần.
  - Các đoạn RTT lớn.
Phân tích riêng drive_*.csv (động học thuận, ổn định cử chỉ): python tests/analyze_drive_log.py <drive.csv>
"""
import bisect
import csv
import statistics as st
import sys

W = ["tt", "tp", "st", "sp"]


def pct(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))]


def load(path):
    return list(csv.DictReader(open(path)))


def summ(xs, unit=""):
    return f"TB {st.mean(xs):.1f}{unit}, trung vị {st.median(xs):.1f}, P95 {pct(xs, .95):.1f}, lớn nhất {max(xs):.1f}"


def main(ai_path, drive_path):
    ai, dr = load(ai_path), load(drive_path)
    ai_t = [float(r["t"]) for r in ai]
    dr_t = [float(r["t"]) for r in dr]
    span = ai_t[-1] - ai_t[0]
    print(f"AI: {len(ai)} khung trong {span:.0f} s ({len(ai) / span:.1f} khung/giây); drive: {len(dr)} dòng, {dr_t[-1] - dr_t[0]:.0f} s")
    print(f"  khoảng thời gian hai tệp trùng nhau: {max(ai_t[0], dr_t[0]):.1f} .. {min(ai_t[-1], dr_t[-1]):.1f}")

    print("\nSuy luận tay (ms) theo số tay trong khung:")
    for n in ("0", "1", "2"):
        x = [float(r["infer_ms"]) for r in ai if r["n_hands"] == n]
        if x:
            print(f"  {n} tay: {len(x):5d} khung | {summ(x)}")
    tot = [float(r["total_ms"]) for r in ai]
    print(f"  cả bước xử lý khung (gồm suy luận, phân vai, con trỏ): {summ(tot)}")
    gaps = [(b - a) * 1000 for a, b in zip(ai_t, ai_t[1:])]
    print(f"  khoảng cách giữa hai khung liên tiếp: {summ(gaps)}")

    # --- độ trễ từ khung chốt cử chỉ đến bánh
    moving = lambda g: g.startswith(("point", "v_"))
    mode_at = lambda t: dr[max(0, bisect.bisect_right(dr_t, t) - 1)]["mode"]
    segs, cur = [], [ai[0]]
    for r in ai[1:]:
        if r["gesture"] != cur[-1]["gesture"]:
            segs.append(cur)
            cur = [r]
        else:
            cur.append(r)
    segs.append(cur)
    lat, lat_cmd = [], []
    for s in segs:
        g = s[0]["gesture"]
        t0, t1 = float(s[0]["t"]), float(s[-1]["t"])
        if not g or not moving(g) or t1 - t0 < 0.8 or not (dr_t[0] < t0 < dr_t[-1] - 2):
            continue
        if mode_at(t0) != "gesture":
            continue
        i0 = bisect.bisect_left(dr_t, t0)
        i1 = bisect.bisect_left(dr_t, t0 + 0.8)
        T = [float(dr[i1][f"{w}_muon"]) for w in W]
        k = max(range(4), key=lambda j: abs(T[j]))
        s0 = float(dr[max(i0 - 1, 0)][f"{W[k]}_do"])
        if abs(T[k] - s0) < 0.1:
            continue
        for j in range(i0, min(i0 + 60, len(dr))):
            if (float(dr[j][f"{W[k]}_do"]) - s0) / (T[k] - s0) >= 0.5:
                lat.append((dr_t[j] - t0) * 1000)
                break
        for j in range(i0, min(i0 + 60, len(dr))):  # từ khung chốt đến lệnh rời laptop (vx, vy, w khác 0)
            if abs(float(dr[j]["vx"])) + abs(float(dr[j]["vy"])) + abs(float(dr[j]["w"])) > 0.02:
                lat_cmd.append((dr_t[j] - t0) * 1000)
                break
    if lat:
        print(f"\nTừ khung camera mà bộ lọc chốt cử chỉ -> bánh tải nhiều nhất đạt 50% ({len(lat)} lần):")
        print(f"  {summ(lat, ' ms')}")
        if lat_cmd:
            print(f"  từ khung chốt -> lệnh rời laptop khác 0 ({len(lat_cmd)} lần): {summ(lat_cmd, ' ms')}")
        print("  (cộng thêm khoảng chốt: 4 khung liên tiếp, tức khoảng 3 khung trước khung chốt, ~100-150 ms)")

    # --- bám tốc độ theo chế độ
    print("\nBám tốc độ khi lệnh không đổi 0.3 s và |lệnh| >= 0.1 (tỉ lệ tốc độ tối đa):")
    for mode in ("manual", "gesture"):
        errs = {w: [] for w in W}
        sat = tot_n = 0
        for i in range(6, len(dr)):
            if dr[i]["mode"] != mode:
                continue
            for w in W:
                T = float(dr[i][f"{w}_muon"])
                if abs(T) >= 0.1 and all(abs(float(dr[j][f"{w}_muon"]) - T) < 0.01 for j in range(i - 6, i)):
                    errs[w].append(abs(float(dr[i][f"{w}_do"]) - T))
                    tot_n += 1
                    sat += abs(float(dr[i][f"{w}_pwm"])) >= 0.95
        if any(errs.values()):
            print(f"  {mode}: " + " | ".join(f"{w} {100 * st.mean(v):.1f}% (P95 {100 * pct(v, .95):.1f}%)" for w, v in errs.items() if v)
                  + f" | PWM chạm trần: {sat}/{tot_n} mẫu ({100 * sat / max(tot_n, 1):.1f}%)")

    # --- RTT
    rtt = [float(r["rtt_ms"]) for r in dr]
    big = [(dr_t[i] - dr_t[0], rtt[i]) for i in range(len(dr)) if rtt[i] > 50]
    print(f"\nRTT: {summ(rtt, ' ms')}; > 50 ms: {len(big)} dòng" + (f", ở giây {', '.join(f'{a:.0f}' for a, _ in big[:8])}" if big else ""))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
