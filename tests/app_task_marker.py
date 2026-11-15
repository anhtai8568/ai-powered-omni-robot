"""
Đánh dấu mốc cho thí nghiệm ứng dụng (lái robot qua đường đi, xem docs/app_task_protocol.md).

Người phụ chạy script này trên CÙNG laptop với server (để dùng chung đồng hồ time.time() với logs/run_*.log,
logs/ai_*.csv, logs/drive_*.csv) và bấm một phím mỗi khi robot qua một mốc. Người lái không chạm vào gì.

    python tests/app_task_marker.py --operator tai --condition C1

Phím (không cần Enter):
    s  bắt đầu lượt (robot rời ô xuất phát)        a  robot vào ô A        b  robot vào ô B
    f  robot vào ô đích                             x  lỗi: chạm vạch / chạm cọc / ra khỏi ô
    r  phải can thiệp (đặt lại robot, người phụ giúp)
    u  xóa mốc vừa bấm       n  sang lượt tiếp theo       c  đổi điều kiện (C1 -> C2 -> C3)       q  thoát

Mỗi lần bấm ghi một dòng vào logs/task_<ngày>.csv: t, operator, condition, trial, event.
"""
import argparse
import csv
import sys
import termios
import time
import tty
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = {"s": "start", "a": "A", "b": "B", "f": "finish", "x": "error", "r": "intervene"}
CONDITIONS = ["C1", "C2", "C3"]
NAMES = {"C1": "cử chỉ hai tay (không chạm)", "C2": "tay trái cử chỉ + tay phải chuột", "C3": "chỉ chuột"}


def getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd, termios.TCSANOW)   # TCSANOW: không xóa phím đã gõ mà chưa kịp đọc
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--operator", required=True, help="tên người lái, ví dụ tai")
    ap.add_argument("--condition", default="C1", choices=CONDITIONS)
    ap.add_argument("--trial", type=int, default=None, help="số lượt bắt đầu (mặc định: tiếp theo lượt cuối trong tệp)")
    ap.add_argument("--out", type=Path, default=ROOT / "logs" / f"task_{time.strftime('%Y%m%d')}.csv")
    args = ap.parse_args()

    args.out.parent.mkdir(exist_ok=True)
    new = not args.out.exists()
    trial = args.trial
    if trial is None:
        trial = 1
        if not new:
            with open(args.out) as fh:
                rows = [r for r in csv.DictReader(fh) if r["operator"] == args.operator]
            if rows:
                trial = max(int(r["trial"]) for r in rows) + 1
    cond = args.condition
    fh = open(args.out, "a", newline="", buffering=1)
    w = csv.writer(fh)
    if new:
        w.writerow(["t", "operator", "condition", "trial", "event"])

    written = []          # (dòng đã ghi, nhãn) để xóa được dòng vừa ghi
    t_start = None
    print(f"Tệp: {args.out}\nNgười lái {args.operator}, điều kiện {cond} ({NAMES[cond]}), lượt {trial}")
    print("s bắt đầu | a ô A | b ô B | f đích | x lỗi | r can thiệp | u xóa | n lượt mới | c đổi điều kiện | q thoát")
    while True:
        k = getch().lower()
        now = time.time()
        if k in ("q", "\x03"):
            break
        if k == "n":
            trial += 1
            t_start = None
            print(f"\r\n--- lượt {trial} ({cond}) ---")
            continue
        if k == "c":
            cond = CONDITIONS[(CONDITIONS.index(cond) + 1) % len(CONDITIONS)]
            print(f"\r\nđiều kiện -> {cond} ({NAMES[cond]})")
            continue
        if k == "u":
            if written:
                line, label = written.pop()
                fh.flush()
                lines = open(args.out, newline="").read().splitlines(keepends=True)
                for i in range(len(lines) - 1, -1, -1):      # bỏ đúng dòng vừa ghi, từ cuối lên
                    if lines[i].rstrip("\r\n") == line:
                        del lines[i]
                        break
                with open(args.out, "w", newline="") as g:
                    g.writelines(lines)
                print(f"\r\nđã xóa: {label}")
            continue
        if k not in EVENTS:
            continue
        ev = EVENTS[k]
        if ev == "start":
            t_start = now
        row = [f"{now:.3f}", args.operator, cond, trial, ev]
        w.writerow(row)
        fh.flush()
        written.append((",".join(map(str, row)), f"{ev} (lượt {trial})"))
        el = f"  +{now - t_start:.1f} s" if t_start else ""
        print(f"\r\n{time.strftime('%H:%M:%S')}  lượt {trial} {cond}: {ev}{el}")
    fh.close()
    print("\r\nĐã lưu.")


if __name__ == "__main__":
    main()
