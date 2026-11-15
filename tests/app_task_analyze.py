"""
Phân tích thí nghiệm ứng dụng (docs/app_task_protocol.md).

Ghép tệp mốc của người phụ (logs/task_*.csv, từ tests/app_task_marker.py) với các log server chạy cùng lúc trong
logs/: run_*.log (sự kiện: đổi tốc độ, dừng khẩn cấp, đổi chế độ), ai_*.csv (từng khung camera) và drive_*.csv
(4 bánh, 20 Hz). Tất cả dùng chung đồng hồ time.time() nên chỉ cần cắt theo thời gian.

    python tests/app_task_analyze.py logs/task_20261115.csv
    python tests/app_task_analyze.py logs/task_20261115.csv --logs logs --out docs/data/v2/app_task

Mỗi lượt (theo các mốc s, a, b, f):
    thời gian hoàn thành  từ s (rời ô xuất phát) đến lúc bật dừng khẩn cấp trên dashboard sau f
    thời gian từng đoạn    s->a, a->b, b->f
    lỗi, can thiệp         số lần bấm x, r
    thao tác giao diện     giảm tốc ở A, tăng tốc ở B, dừng khẩn cấp ở đích: bao lâu sau khi robot vào ô
    mất tay                tỉ lệ khung không thấy tay nào; với C1 thêm tỉ lệ khung thiếu một trong hai tay
    dừng giữa đường        số lần robot đứng yên >= 0.5 s giữa s và f
In bảng, ghi <out>/app_task_trials.csv, <out>/app_task_summary.csv và hình <out>/fig_app_task.png.
"""
import argparse
import bisect
import csv
import re
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINE = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\.(\d{3})\] \[SỰ KIỆN\] ([^:]+)(?::\s*(.*))?$")
STAMP = re.compile(r"_(\d{8}_\d{6})\.")
MOVING = 0.05          # |lệnh| trên mức này là đang chạy
STOP_MIN = 0.5         # đứng yên ít nhất chừng này giây mới tính là một lần dừng


def stamp_of(p: Path):
    m = STAMP.search(p.name)
    return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S") if m else None


def read_events(path: Path):
    """Sự kiện trong run_*.log -> [(t, tên, chi tiết)]. Giờ trong log chỉ có HH:MM:SS nên lấy ngày từ tên tệp."""
    day = stamp_of(path)
    if day is None:
        return []
    base = day.replace(hour=0, minute=0, second=0, microsecond=0)
    out, last = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = LINE.match(line.rstrip("\n"))
        if not m:
            continue
        h, mi, s, ms, name, detail = m.groups()
        t = base + timedelta(hours=int(h), minutes=int(mi), seconds=int(s), milliseconds=int(ms))
        if last is not None and t < last - timedelta(hours=1):     # qua nửa đêm
            base += timedelta(days=1)
            t += timedelta(days=1)
        last = t
        out.append((t.timestamp(), name.strip(), (detail or "").strip()))
    return out


def read_csv_window(paths, t0, t1):
    rows = []
    for p in paths:
        with open(p, newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    t = float(r["t"])
                except (KeyError, ValueError):
                    continue
                if t0 <= t <= t1:
                    r["t"] = t
                    rows.append(r)
    rows.sort(key=lambda r: r["t"])
    return rows


def candidates(logs: Path, pattern: str, t0: float, t1: float):
    """Tệp log bắt đầu trước t1 và không quá 12 giờ trước t0 (tránh đọc hết thư mục)."""
    out = []
    for p in sorted(logs.glob(pattern)):
        s = stamp_of(p)
        if s and t0 - 12 * 3600 <= s.timestamp() <= t1:
            out.append(p)
    return out


def load_trials(task_files):
    trials = defaultdict(lambda: {"marks": defaultdict(list)})
    for f in task_files:
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                key = (r["operator"], int(r["trial"]))
                tr = trials[key]
                tr["operator"], tr["trial"], tr["condition"] = r["operator"], int(r["trial"]), r["condition"]
                tr["marks"][r["event"]].append(float(r["t"]))
    return [trials[k] for k in sorted(trials)]


def first_after(events, t, name, pred=lambda d: True, limit=60.0):
    for te, n, d in events:
        if n == name and t <= te <= t + limit and pred(d):
            return te, d
    return None, None


def speed_value(d):
    try:
        return float(d)
    except ValueError:
        return None


def analyse_trial(tr, events, logs: Path):
    m = tr["marks"]
    s = m["start"][0] if m["start"] else None
    a = m["A"][0] if m["A"] else None
    b = m["B"][0] if m["B"] else None
    f = m["finish"][0] if m["finish"] else None
    res = {"operator": tr["operator"], "condition": tr["condition"], "trial": tr["trial"],
           "errors": len(m["error"]), "interventions": len(m["intervene"])}
    if s is None or f is None:
        res["note"] = "thiếu mốc s hoặc f"
        return res
    # mốc kết thúc: dừng khẩn cấp BẬT trên dashboard sau khi vào ô đích
    t_stop, _ = first_after(events, f - 1.0, "dừng khẩn cấp", lambda d: d.upper().startswith("BẬT"), limit=30)
    end = t_stop if t_stop else f
    res["completion_s"] = end - s
    res["seg_SA_s"] = (a - s) if a else None
    res["seg_AB_s"] = (b - a) if a and b else None
    res["seg_BF_s"] = (f - b) if b else None
    res["estop_after_finish_s"] = (t_stop - f) if t_stop else None
    # thao tác giao diện: tốc độ đổi xuống ở A, lên ở B (lấy lần đổi đầu tiên theo đúng chiều)
    if a:
        ta, da = first_after(events, a - 2.0, "tốc độ", lambda d: (speed_value(d) or 1) <= 0.35, limit=30)
        res["gui_slow_at_A_s"] = (ta - a) if ta else None
        res["speed_at_A"] = speed_value(da) if da else None
    if b:
        tb, db = first_after(events, b - 2.0, "tốc độ", lambda d: (speed_value(d) or 0) >= 0.55, limit=30)
        res["gui_fast_at_B_s"] = (tb - b) if tb else None
    res["mode_changes"] = sum(1 for te, n, _ in events if n == "chế độ" and s <= te <= end)
    # khung camera
    ai = read_csv_window(candidates(logs, "ai_*.csv", s, end), s, end)
    if ai:
        nh = [int(r["n_hands"]) for r in ai]
        res["frames"] = len(ai)
        res["fps"] = len(ai) / max(1e-6, ai[-1]["t"] - ai[0]["t"])
        res["no_hand_pct"] = 100 * sum(1 for x in nh if x == 0) / len(nh)
        if tr["condition"] == "C1":
            res["missing_hand_pct"] = 100 * sum(1 for x in nh if x < 2) / len(nh)
        res["infer_ms_mean"] = st.mean(float(r["infer_ms"]) for r in ai)
    # robot
    dr = read_csv_window(candidates(logs, "drive_*.csv", s, end), s, end)
    if dr:
        mag = [max(abs(float(r["vx"])), abs(float(r["vy"])), abs(float(r["w"]))) for r in dr]
        ts = [r["t"] for r in dr]
        stops, still_since, moving_seen = 0, None, False
        for t, v in zip(ts, mag):
            if v > MOVING:
                if still_since is not None and moving_seen and t - still_since >= STOP_MIN:
                    stops += 1
                still_since, moving_seen = None, True
            elif still_since is None:
                still_since = t
        res["stops_midway"] = stops
        res["moving_pct"] = 100 * sum(1 for v in mag if v > MOVING) / len(mag)
        res["rtt_median_ms"] = st.median(float(r["rtt_ms"]) for r in dr)
        res["saturated_pct"] = 100 * sum(1 for r in dr if max(abs(float(r[k])) for k in
                                         ("tt_pwm", "tp_pwm", "st_pwm", "sp_pwm")) >= 0.95) / len(dr)
    return res


COLS = ["operator", "condition", "trial", "completion_s", "seg_SA_s", "seg_AB_s", "seg_BF_s", "errors",
        "interventions", "gui_slow_at_A_s", "speed_at_A", "gui_fast_at_B_s", "estop_after_finish_s", "stops_midway",
        "moving_pct", "no_hand_pct", "missing_hand_pct", "mode_changes", "fps", "infer_ms_mean", "rtt_median_ms",
        "saturated_pct", "frames", "note"]
SUMMARY = ["completion_s", "seg_SA_s", "seg_AB_s", "seg_BF_s", "errors", "interventions", "gui_slow_at_A_s",
           "gui_fast_at_B_s", "estop_after_finish_s", "stops_midway", "no_hand_pct", "missing_hand_pct"]


def fmt(v, nd=2):
    if v is None or v == "":
        return "-"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", nargs="+", type=Path, help="logs/task_*.csv")
    ap.add_argument("--logs", type=Path, default=ROOT / "logs")
    ap.add_argument("--out", type=Path, default=None, help="thư mục ghi kết quả (mặc định cạnh tệp mốc)")
    args = ap.parse_args()

    trials = load_trials(args.task)
    if not trials:
        raise SystemExit("Không có lượt nào trong tệp mốc.")
    t_all = [t for tr in trials for v in tr["marks"].values() for t in v]
    events = []
    for p in candidates(args.logs, "run_*.log", min(t_all), max(t_all)):
        events += read_events(p)
    events.sort()
    rows = [analyse_trial(tr, events, args.logs) for tr in trials]

    out = args.out or args.task[0].parent
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "app_task_trials.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})

    print(f"{'người':8} {'đk':3} {'lượt':>4} {'tổng s':>7} {'S-A':>6} {'A-B':>6} {'B-F':>6} {'lỗi':>4} {'can':>4} "
          f"{'GUI A':>6} {'GUI B':>6} {'Stop':>5} {'dừng':>4} {'0 tay%':>6} {'thiếu%':>6}")
    for r in rows:
        print(f"{r['operator']:8} {r['condition']:3} {r['trial']:>4} {fmt(r.get('completion_s'), 1):>7} "
              f"{fmt(r.get('seg_SA_s'), 1):>6} {fmt(r.get('seg_AB_s'), 1):>6} {fmt(r.get('seg_BF_s'), 1):>6} "
              f"{r['errors']:>4} {r['interventions']:>4} {fmt(r.get('gui_slow_at_A_s'), 1):>6} "
              f"{fmt(r.get('gui_fast_at_B_s'), 1):>6} {fmt(r.get('estop_after_finish_s'), 1):>5} "
              f"{fmt(r.get('stops_midway')):>4} {fmt(r.get('no_hand_pct'), 1):>6} {fmt(r.get('missing_hand_pct'), 1):>6}"
              f"  {r.get('note', '')}")

    # tóm tắt theo điều kiện: trung vị [nhỏ nhất - lớn nhất]
    by = defaultdict(list)
    for r in rows:
        if "completion_s" in r:
            by[r["condition"]].append(r)
    summ = []
    print("\nTheo điều kiện (trung vị [nhỏ nhất - lớn nhất], n = số lượt hoàn thành):")
    for c in sorted(by):
        line = {"condition": c, "n": len(by[c])}
        txt = []
        for k in SUMMARY:
            xs = [r[k] for r in by[c] if r.get(k) is not None]
            if xs:
                line[f"{k}_median"], line[f"{k}_min"], line[f"{k}_max"] = st.median(xs), min(xs), max(xs)
                txt.append(f"{k} {st.median(xs):.1f} [{min(xs):.1f}-{max(xs):.1f}]")
        summ.append(line)
        print(f"  {c} (n={len(by[c])}): " + "; ".join(txt))
    if summ:
        keys = sorted({k for d in summ for k in d}, key=lambda k: (k != "condition", k != "n", k))
        with open(out / "app_task_summary.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for d in summ:
                w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()})

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(không có matplotlib: bỏ qua hình)")
        return
    conds = sorted(by)
    if not conds:
        return
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    for ax, (k, lab) in zip(axes, [("completion_s", "Completion time (s)"), ("errors", "Errors per trial"),
                                   ("gui_slow_at_A_s", "Speed change at A (s)")]):
        data = [[r[k] for r in by[c] if r.get(k) is not None] for c in conds]
        ax.boxplot([d if d else [float("nan")] for d in data], showfliers=False)
        for i, d in enumerate(data, 1):
            ax.plot([i] * len(d), d, "o", alpha=0.6, ms=4)
        ax.set_xticks(range(1, len(conds) + 1), conds)
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "fig_app_task.png", dpi=200)
    print(f"\nĐã ghi {out / 'app_task_trials.csv'}, {out / 'app_task_summary.csv'}, {out / 'fig_app_task.png'}")


if __name__ == "__main__":
    main()
