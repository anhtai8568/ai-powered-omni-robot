"""
Sinh toàn bộ hình và số liệu cho hai bài báo cáo từ dữ liệu thật trong docs/data/ và từ mã nguồn.

    .venv/bin/python reports/make_figures.py

Đầu ra: reports/figures/<tên>_<en|vi>.pdf (+ .png) và reports/figures/stats.json (mọi con số dùng trong bài).
Không có số nào được gõ tay: đổi dữ liệu thì chạy lại là hình và số cùng đổi.
"""
import contextlib
import csv
import importlib.util
import io
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "figures"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))

DATA = {
    "manual": ROOT / "docs/data/v1/drive_manual.csv",
    "gesture": ROOT / "docs/data/v1/drive_gesture.csv",
    "twohand": ROOT / "docs/data/v2/drive_twohand.csv",
}
REAL_CLICK = ROOT / "docs/data/v2/real_hand_click_still.csv"   # tests/real_hand_eval.py, bàn tay thật
W = ["tt", "tp", "st", "sp"]
SETTLE = 6
COL = {"tt": "#1f77b4", "tp": "#d62728", "st": "#2ca02c", "sp": "#7f4fb8"}
FF_OFFSET = [0.076, 0.148, 0.055, 0.060]   # firmware/src/robot_config.h
FF_SLOPE = [0.470, 0.594, 0.453, 0.464]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
                     "legend.fontsize": 6.5, "axes.grid": True, "grid.linestyle": ":", "grid.alpha": 0.5,
                     "pdf.fonttype": 42, "savefig.dpi": 300})

TXT = {
    "en": {
        "wheels": {"tt": "Front-left (FL)", "tp": "Front-right (FR)", "st": "Rear-left (RL)", "sp": "Rear-right (RR)"},
        "time": "Time (s)", "norm": "Wheel speed (1.0 = 4300 cnt/s)",
        "set": "set-point", "meas": "measured",
        "ff_x": "Target speed |r|", "ff_y": "Feed-forward duty", "err_y": "|error| (of max speed)",
        "err_t": "Tracking error, two-hand run", "ff_t": "Dead-zone feed-forward lines",
        "rtt_x": "Round-trip time (ms)", "rtt_y": "Fraction of packets", "rtt_t": "UDP round-trip time",
        "odo_y": "Speed magnitude (normalized)", "odo_t": "Command vs. forward kinematics",
        "cmd": "command", "odo": "from encoders",
        "prim": ["Forward", "Backward", "Left", "Right", "Rotate L", "Rotate R"],
        "click_x": "Time (s)", "click_y": "Horizontal position in camera frame (px)",
        "raw": "raw index fingertip", "shown": "displayed cursor (x, y)", "act": "action point (ax, ay)",
        "click_t": "Middle finger raised at t = 1.0 s (simulated hand)",
        "real_x": "Fingertip displacement (px)", "real_y": "Action-point displacement (px)",
        "real_t": "Real hand: raising the middle finger", "real_eq": "equal", "real_n": "trials",
        "sessions": {"manual": "Manual (v1)", "gesture": "Gesture (v1)", "twohand": "Two-hand (v2)"},
        "trace_t": "Closed-loop speed tracking, two-hand run",
    },
    "vi": {
        "wheels": {"tt": "Trước trái (tt)", "tp": "Trước phải (tp)", "st": "Sau trái (st)", "sp": "Sau phải (sp)"},
        "time": "Thời gian (s)", "norm": "Tốc độ bánh (1,0 = 4300 xung/s)",
        "set": "giá trị đặt", "meas": "giá trị đo",
        "ff_x": "Tốc độ đặt |r|", "ff_y": "PWM feedforward", "err_y": "|sai số| (so với tốc độ tối đa)",
        "err_t": "Sai số bám tốc độ, phiên hai tay", "ff_t": "Đường bù vùng chết feedforward",
        "rtt_x": "Độ trễ khứ hồi (ms)", "rtt_y": "Tỉ lệ gói tin", "rtt_t": "Độ trễ khứ hồi UDP",
        "odo_y": "Độ lớn vận tốc (chuẩn hóa)", "odo_t": "Lệnh so với động học thuận",
        "cmd": "lệnh đặt", "odo": "từ encoder",
        "prim": ["Tiến", "Lùi", "Sang trái", "Sang phải", "Xoay trái", "Xoay phải"],
        "click_x": "Thời gian (s)", "click_y": "Vị trí ngang trong khung camera (px)",
        "raw": "đầu ngón trỏ thô", "shown": "con trỏ hiển thị (x, y)", "act": "điểm tác động (ax, ay)",
        "click_t": "Duỗi ngón giữa tại t = 1,0 s (bàn tay mô phỏng)",
        "real_x": "Đầu ngón trỏ dịch (px)", "real_y": "Điểm tác động dịch (px)",
        "real_t": "Bàn tay thật: duỗi ngón giữa", "real_eq": "bằng nhau", "real_n": "lần",
        "sessions": {"manual": "Thủ công (v1)", "gesture": "Cử chỉ (v1)", "twohand": "Hai tay (v2)"},
        "trace_t": "Bám tốc độ vòng kín, phiên hai tay",
    },
}


def save(fig, name, lang):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}_{lang}.{ext}", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


# ---------------------------------------------------------------- dữ liệu
def load(key):
    rows = list(csv.DictReader(open(DATA[key])))
    out = []
    for r in rows:
        d = {k: (v if k in ("mode", "gesture") else float(v)) for k, v in r.items()}
        out.append(d)
    unpowered = lambda r: all(r[f"{w}_do"] == 0 and abs(r[f"{w}_pwm"]) > 0.9 for w in W)
    n_bad = sum(unpowered(r) for r in out)
    return [r for r in out if not unpowered(r)], n_bad


def pct(xs, p):
    return sorted(xs)[int(p * (len(xs) - 1))]


def settled(rows, i, key):
    return all(abs(rows[j][key] - rows[i][key]) < 0.01 for j in range(i - SETTLE, i))


def wheel_errors(rows):
    res = {}
    for w in W:
        err, pwm = [], []
        for i in range(SETTLE, len(rows)):
            T = rows[i][f"{w}_muon"]
            if abs(T) >= 0.1 and settled(rows, i, f"{w}_muon"):
                err.append(abs(rows[i][f"{w}_do"] - T))
                pwm.append(abs(rows[i][f"{w}_pwm"]))
        res[w] = {"err": err, "pwm": pwm}
    return res


def fk(v):
    return ((v[0] + v[1] + v[2] + v[3]) / 4, (-v[0] + v[1] + v[2] - v[3]) / 4, (-v[0] + v[1] - v[2] + v[3]) / 4)


def motion(r):
    names = [n for n, v, d in (("fwd", r["vx"], 1), ("back", r["vx"], -1), ("left", r["vy"], 1), ("right", r["vy"], -1),
                               ("rotl", r["w"], 1), ("rotr", r["w"], -1)) if v * d >= 0.05]
    return "+".join(names) or "stop"


def primitives(rows):
    g = {}
    for i in range(SETTLE, len(rows)):
        m = motion(rows[i])
        if m != "stop" and all(motion(rows[j]) == m for j in range(i - SETTLE, i)):
            cmd = fk([rows[i][f"{w}_muon"] for w in W])
            got = fk([rows[i][f"{w}_do"] for w in W])
            g.setdefault(m, []).append((cmd, got))
    out = {}
    for m, v in g.items():
        out[m] = {"n": len(v), "cmd": [st.mean(x[0][k] for x in v) for k in range(3)],
                  "odo": [st.mean(x[1][k] for x in v) for k in range(3)]}
    return out


def gesture_stats(rows):
    gest = [r for r in rows if r["mode"] == "gesture"]
    segs, cur = [], [gest[0]]
    for r in gest[1:]:
        if r["gesture"] != cur[-1]["gesture"]:
            segs.append(cur)
            cur = [r]
        else:
            cur.append(r)
    segs.append(cur)
    length = lambda s: s[-1]["t"] - s[0]["t"] + 0.05
    short = sum(1 for s in segs if length(s) < 0.3)
    moving = lambda g: g.startswith(("point", "v_"))
    lat = []
    pos = {id(r): i for i, r in enumerate(gest)}
    for s in segs:
        if not moving(s[0]["gesture"]) or length(s) < 0.8:
            continue
        i0 = pos[id(s[0])]
        T = [s[-1][f"{w}_muon"] for w in W]
        k = max(range(4), key=lambda j: abs(T[j]))
        s0 = gest[i0][f"{W[k]}_do"]
        if abs(T[k] - s0) < 0.1:
            continue
        for r in gest[i0:i0 + 40]:
            if (r[f"{W[k]}_do"] - s0) / (T[k] - s0) >= 0.5:
                lat.append((r["t"] - gest[i0]["t"]) * 1000)
                break
    return {"changes": len(segs), "short": short, "lat_n": len(lat),
            "lat_med": st.median(lat) if lat else None, "lat_min": min(lat) if lat else None,
            "lat_max": max(lat) if lat else None}


# ---------------------------------------------------------------- mô phỏng con trỏ bằng mã thật
def cursor_sim():
    spec = importlib.util.spec_from_file_location("hands_test", ROOT / "tests" / "test_hands_logic.py")
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            spec.loader.exec_module(mod)
        except SystemExit:  # tests/test_hands_logic.py gọi sys.exit() ở cuối khi nạp
            pass
    make_hand, Cursor, Wd, Hd = mod.make_hand, mod.Cursor, mod.W, mod.H
    REG = 0.65

    def run(c, frames, t0=0.0, fps=30):
        return [c.update(h, Wd, Hd, t0 + i / fps) for i, h in enumerate(frames)]

    # (1) rung khi giữ yên, tay đứng yên + nhiễu Gauss 2 px, 200 lần có hạt giống
    sd = lambda v: math.sqrt(sum((a - sum(v) / len(v)) ** 2 for a in v) / len(v))
    raw_sd, filt_sd = [], []
    for seed in range(200):
        rnd = random.Random(seed)
        c = Cursor(region=REG)
        rx, fx = [], []
        for i in range(90):
            jx, jy = rnd.gauss(0, 2), rnd.gauss(0, 2)
            o = c.update(make_hand({"index"}, tip_dx=jx, tip_dy=jy), Wd, Hd, i / 30)
            if i > 30:
                fx.append(o["x"])
                rx.append(0.5 + jx / Wd / REG)
        raw_sd.append(sd(rx))
        filt_sd.append(sd(fx))
    jitter = {"raw": st.mean(raw_sd), "filt": st.mean(filt_sd), "trials": 200}
    jitter["reduction"] = 1 - jitter["filt"] / jitter["raw"]

    # (2) lệch khi click: đầu ngón trỏ xê dịch (25, -15) px khi duỗi ngón giữa; có / không có FREEZE_BACK
    def click_run(freeze):
        c = Cursor(region=REG)
        if not freeze:
            c.FREEZE_BACK = 0.0
        frames = [make_hand({"index"}) for _ in range(30)] + \
                 [make_hand({"index", "middle"}, tip_dx=25, tip_dy=-15) for _ in range(15)]
        return run(c, frames)

    fixed, unfixed_sim = click_run(True), click_run(False)

    def shift_px(o):
        b = o[29]
        d = o[-1]
        return math.hypot((d["ax"] - b["ax"]) * Wd * REG, (d["ay"] - b["ay"]) * Hd * REG)

    click = {"finger_shift_px": math.hypot(25, 15),
             "action_shift_px_with": shift_px(fixed), "action_shift_px_without": shift_px(unfixed_sim),
             "norm_with": math.hypot(fixed[-1]["ax"] - fixed[29]["ax"], fixed[-1]["ay"] - fixed[29]["ay"]),
             "norm_without": math.hypot(25 / Wd / REG, 15 / Hd / REG)}
    click["reduction"] = 1 - click["norm_with"] / click["norm_without"]

    # (3) quỹ đạo để vẽ: vị trí ngang trong khung camera (px)
    c = Cursor(region=1.0)
    frames = [make_hand({"index"}, tip_dx=0) for _ in range(30)] + \
             [make_hand({"index", "middle"}, tip_dx=25, tip_dy=-15) for _ in range(15)] + \
             [make_hand({"index", "middle"}, tip_dx=25 + 4 * i, tip_dy=-15) for i in range(1, 31)]
    out = run(c, frames)
    t = np.arange(len(frames)) / 30
    raw = np.array([f[8][0] for f in frames])
    shown = np.array([o["x"] * Wd for o in out])
    act = np.array([o["ax"] * Wd for o in out])
    base = act[29]
    click["transient_px"] = float(np.max(np.abs(act[30:45] - base)))
    click["final_px"] = float(abs(act[44] - base))
    click["finger_shift_x_px"] = float(raw[44] - raw[29])
    return jitter, click, (t, raw, shown, act)


# ---------------------------------------------------------------- vẽ
def box(ax, x, y, w, h, text, fc="#ffffff", ec="#2b4c7e", fs=6.2, bold=False, lw=0.9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.12", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal",
            linespacing=1.25)


def arrow(ax, p, q, color="#333333", ls="-", lw=0.9, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=7, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def fig_arch(lang):
    en = lang == "en"
    fig, ax = plt.subplots(figsize=(7.1, 3.7))
    ax.set_xlim(0, 20)
    ax.set_ylim(-1.0, 11.1)
    ax.axis("off")
    ax.grid(False)
    # hai miền
    ax.add_patch(FancyBboxPatch((0.1, 0.1), 9.3, 10.1, boxstyle="round,pad=0,rounding_size=0.3", fc="#f1f5fa", ec="#2b4c7e", lw=1.4))
    ax.add_patch(FancyBboxPatch((10.6, 0.1), 9.3, 10.1, boxstyle="round,pad=0,rounding_size=0.3", fc="#f2f8f3", ec="#2e6b3a", lw=1.4))
    ax.text(4.75, 9.6, "HOST (laptop)" if en else "TRẠM HOST (laptop)", ha="center", fontsize=8, fontweight="bold", color="#1b3556")
    ax.text(15.25, 9.6, "EDGE (ESP32 robot)" if en else "BIÊN EDGE (robot ESP32)", ha="center", fontsize=8, fontweight="bold", color="#1d4a27")
    # host
    box(ax, 0.5, 7.4, 4.1, 1.7, ("Camera (V4L2)\nMJPG 1280×720, 30 fps\nmirrored, 2 buffers" if en else
                                 "Camera (V4L2)\nMJPG 1280×720, 30 fps\nlật gương, đệm 2 khung"))
    box(ax, 4.9, 7.4, 4.1, 1.7, ("MediaPipe Hands\non 640-px-wide copy\n21 landmarks, 2 hands" if en else
                                 "MediaPipe Hands\ntrên bản thu rộng 640 px\n21 điểm mốc, 2 tay"))
    box(ax, 0.5, 5.2, 8.5, 1.5, ("RoleAssigner + split_roles()\nlabel self-calibration, 10-frame vote,\n150 px position stickiness"
                                if en else "RoleAssigner + split_roles()\ntự hiệu chuẩn nhãn, bỏ phiếu 10 khung,\nbám vị trí 150 px"), fc="#e6eefa")
    box(ax, 0.5, 2.9, 4.1, 1.8, ("Dominant hand: GUI\nOne-Euro filter,\nFREEZE_BACK 0.2 s" if en else
                                 "Tay thuận: giao diện\nlọc One-Euro,\nFREEZE_BACK 0,2 s"), fc="#fff7e0", ec="#b07d10")
    box(ax, 4.9, 2.9, 4.1, 1.8, ("Non-dominant hand:\ndrive, 8 directions,\nGestureFilter 4 / 6" if en else
                                 "Tay không thuận: lái\n8 hướng + xoay,\nGestureFilter 4 / 6"), fc="#e6f5ea", ec="#2e6b3a")
    box(ax, 0.5, 0.5, 4.1, 1.8, ("Web dashboard\nFastAPI + WebSocket\nvirtual pad, sliders" if en else
                                 "Web dashboard\nFastAPI + WebSocket\ncần lái ảo, thanh trượt"))
    box(ax, 4.9, 0.5, 4.1, 1.8, ("control_loop() 20 Hz\nramp() 2.0 / 4.0 per s\nRobotLink + CSV log" if en else
                                 "control_loop() 20 Hz\nramp() 2,0 / 4,0 mỗi giây\nRobotLink + log CSV"))
    # edge
    box(ax, 11.0, 7.4, 8.5, 1.7, ("Wi-Fi SoftAP \"omni-robot\" + UDP :4210\nmodem sleep off, 300 ms watchdog,\nsingle-owner lock" if en else
                                  "Wi-Fi SoftAP \"omni-robot\" + UDP :4210\ntắt ngủ modem, watchdog 300 ms,\nkhóa chủ duy nhất"), ec="#2e6b3a")
    box(ax, 11.0, 5.2, 8.5, 1.5, ("Inverse kinematics (X-drive, 45°)\ndirection-preserving desaturation" if en else
                                 "Động học nghịch (cấu hình X, 45°)\nthu nhỏ đồng tỉ lệ khi bão hòa"), ec="#2e6b3a")
    box(ax, 11.0, 2.9, 8.5, 1.8, ("4 × speed controller, 100 Hz\nfeed-forward + PI (Kp 0.8, Ki 6.0)\nanti-windup, stall guard 0.7 s" if en else
                                 "4 bộ điều khiển tốc độ, 100 Hz\nfeedforward + PI (Kp 0,8; Ki 6,0)\nchống bão hòa, bảo vệ kẹt 0,7 s"),
        fc="#e6f5ea", ec="#2e6b3a")
    box(ax, 11.0, 0.5, 4.1, 1.8, ("2 × L298N\nLEDC PWM 1 kHz, 10-bit\n4 × GM25-370" if en else
                                 "2 × L298N\nPWM LEDC 1 kHz, 10-bit\n4 × GM25-370"), ec="#2e6b3a")
    box(ax, 15.4, 0.5, 4.1, 1.8, ("4 × PCNT encoder\n8112 counts/rev\nIIR filter α = 0.3" if en else
                                 "4 × encoder PCNT\n8112 xung/vòng\nlọc IIR α = 0,3"), ec="#2e6b3a")
    # mũi tên trong host
    arrow(ax, (4.6, 8.25), (4.9, 8.25))
    arrow(ax, (6.95, 7.4), (6.95, 6.7))
    arrow(ax, (2.55, 5.2), (2.55, 4.7))
    arrow(ax, (6.95, 5.2), (6.95, 4.7))
    arrow(ax, (2.55, 2.9), (2.55, 2.3))
    arrow(ax, (6.95, 2.9), (6.95, 2.3))
    arrow(ax, (4.6, 1.4), (4.9, 1.4), style="<|-|>")
    # mũi tên trong edge
    arrow(ax, (15.25, 7.4), (15.25, 6.7), color="#2e6b3a")
    arrow(ax, (15.25, 5.2), (15.25, 4.7), color="#2e6b3a")
    arrow(ax, (13.05, 2.9), (13.05, 2.3), color="#2e6b3a")
    arrow(ax, (17.45, 2.3), (17.45, 2.9), color="#2e6b3a")
    # liên kết UDP: hai mũi tên ngang qua khe giữa, nhãn nằm trong khe trống phía trên
    arrow(ax, (9.0, 1.75), (9.9, 1.75), color="#c0392b", lw=1.2)
    arrow(ax, (9.9, 1.75), (9.9, 8.6), color="#c0392b", lw=1.2, style="-")
    arrow(ax, (9.9, 8.6), (11.0, 8.6), color="#c0392b", lw=1.2)
    ax.text(10.0, 10.55, "UDP command  C seq vx vy w  (20 Hz)  →", ha="center", fontsize=6.6,
            color="#c0392b", fontweight="bold")
    arrow(ax, (11.0, 8.0), (10.25, 8.0), color="#2e6b3a", lw=1.2, ls="--")
    arrow(ax, (10.25, 8.0), (10.25, 1.15), color="#2e6b3a", lw=1.2, ls="--", style="-")
    arrow(ax, (10.25, 1.15), (9.0, 1.15), color="#2e6b3a", lw=1.2, ls="--")
    ax.text(10.0, -0.65, "←  ACK  A seq + 12 telemetry values" if en else "←  ACK  A seq + 12 giá trị phản hồi", ha="center", fontsize=6.6,
            color="#2e6b3a", fontweight="bold")
    save(fig, "fig_arch", lang)


def fig_kin(lang):
    en = lang == "en"
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    ax.set_xlim(-2.9, 2.3)
    ax.set_ylim(-2.0, 2.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.grid(False)
    ax.add_patch(Rectangle((-0.9, -0.9), 1.8, 1.8, fc="#eef2f8", ec="#2b4c7e", lw=1.2))
    pos = {"tt": (-0.9, 0.9), "tp": (0.9, 0.9), "st": (-0.9, -0.9), "sp": (0.9, -0.9)}
    # hướng đẩy của mỗi bánh (khi quay tiến): tt, sp: tiến+phải; tp, st: tiến+trái
    push = {"tt": (1, 1), "tp": (-1, 1), "st": (-1, 1), "sp": (1, 1)}
    for w, (x, y) in pos.items():
        px, py = push[w]
        ang = math.degrees(math.atan2(py, px))
        ax.add_patch(Rectangle((x - 0.38, y - 0.12), 0.76, 0.24, angle=ang + 0.0, rotation_point=(x, y), fc="#333333", ec="none",
                               transform=ax.transData))
        n = 0.52 / math.hypot(px, py)
        ax.annotate("", xy=(x + px * n * 1.0, y + py * n * 1.0), xytext=(x, y),
                    arrowprops=dict(arrowstyle="-|>", color=COL[w], lw=1.3))
        ox = -0.2 if x < 0 else 0.2
        oy = 0.3 if y > 0 else -0.3
        ax.text(x + ox * 1.9, y + oy * 1.3, {"tt": "FL", "tp": "FR", "st": "RL", "sp": "RR"}[w] if en else w, color=COL[w], fontsize=7.5, fontweight="bold",
                ha="right" if x < 0 else "left", va="center")
    # trục robot
    ax.annotate("", xy=(-1.9, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color="k", lw=0.8, ls="--"))
    ax.annotate("", xy=(0, 1.95), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color="k", lw=0.8, ls="--"))
    ax.text(-2.0, -0.12, "$Y_R$ " + ("(left)" if en else "(trái)"), fontsize=6.5, va="top", ha="right")
    ax.text(0.08, 2.08, "$X_R$ " + ("(forward)" if en else "(tiến)"), fontsize=6.5)
    ax.text(0, -0.02, "", fontsize=6)
    # w
    th = np.linspace(math.radians(215), math.radians(325), 30)
    ax.plot(0.45 * np.cos(th[:-2]), 0.45 * np.sin(th[:-2]), color="#555", lw=1)
    ax.annotate("", xy=(0.45 * np.cos(th[-1]), 0.45 * np.sin(th[-1])), xytext=(0.45 * np.cos(th[-3]), 0.45 * np.sin(th[-3])),
                arrowprops=dict(arrowstyle="-|>", color="#555", lw=1))
    ax.text(0, -0.72, "$w>0$: " + ("CCW" if en else "xoay trái"), ha="center", fontsize=6.5)
    ax.text(0, 0.05, "", fontsize=6)
    ax.set_title("", fontsize=7)
    save(fig, "fig_kin", lang)


def fig_ctrl(lang):
    en = lang == "en"
    fig, ax = plt.subplots(figsize=(7.1, 2.1))
    ax.set_xlim(0, 20)
    ax.set_ylim(-1.3, 6)
    ax.axis("off")
    ax.grid(False)
    box(ax, 0.2, 2.2, 2.6, 1.6, ("Command\nvx, vy, w" if en else "Lệnh\nvx, vy, w"))
    box(ax, 3.4, 2.2, 2.8, 1.6, ("Inverse\nkinematics" if en else "Động học\nnghịch"))
    box(ax, 6.8, 2.2, 2.6, 1.6, ("Slew limit\n4.0 / s" if en else "Giới hạn\nđộ dốc 4,0/s"))
    box(ax, 10.2, 3.6, 3.2, 1.7, ("Feed-forward\nsgn(r)(a + b|r|)" if en else "Feedforward\nsgn(r)(a + b|r|)"), ec="#b07d10", fc="#fff7e0")
    box(ax, 10.2, 0.7, 3.2, 1.7, ("PI: Kp e + ∫Ki e dt\nfrozen if ramping\nor saturated" if en else "PI: Kp e + ∫Ki e dt\nđóng băng khi tăng\ntốc hoặc bão hòa"), ec="#2e6b3a", fc="#e6f5ea", fs=5.9)
    box(ax, 14.4, 2.2, 1.7, 1.6, "Σ\nclamp ±1", fs=6.3)
    box(ax, 16.8, 2.2, 3.0, 1.6, ("L298N + motor\n+ encoder PCNT" if en else "L298N + động cơ\n+ encoder PCNT"))
    arrow(ax, (2.8, 3.0), (3.4, 3.0))
    arrow(ax, (6.2, 3.0), (6.8, 3.0))
    arrow(ax, (9.4, 3.0), (9.8, 3.0), style="-")
    arrow(ax, (9.8, 3.0), (9.8, 4.45), style="-")
    arrow(ax, (9.8, 4.45), (10.2, 4.45))
    ax.text(9.6, 3.12, "r", fontsize=7, ha="center", va="bottom")
    arrow(ax, (9.8, 3.0), (9.8, 1.55), style="-")
    arrow(ax, (9.8, 1.55), (10.2, 1.55))
    arrow(ax, (13.4, 4.45), (15.25, 4.45), style="-")
    arrow(ax, (15.25, 4.45), (15.25, 3.8))
    arrow(ax, (13.4, 1.55), (15.25, 1.55), style="-")
    arrow(ax, (15.25, 1.55), (15.25, 2.2))
    arrow(ax, (16.1, 3.0), (16.8, 3.0))
    ax.text(16.45, 3.2, "u", fontsize=7, ha="center")
    # phản hồi
    arrow(ax, (18.3, 2.2), (18.3, -0.4), style="-")
    arrow(ax, (18.3, -0.4), (11.8, -0.4), style="-")
    arrow(ax, (11.8, -0.4), (11.8, 0.7))
    ax.text(15.0, -0.25, ("measured speed ω (IIR α = 0.3)   e = r − ω" if en else "tốc độ đo ω (IIR α = 0,3)   e = r − ω"), fontsize=6.4, ha="center", va="bottom")
    save(fig, "fig_ctrl", lang)


def fig_click(lang, sim):
    L = TXT[lang]
    t, raw, shown, act = sim
    fig, ax = plt.subplots(figsize=(3.45, 2.3))
    ax.axvspan(1.0, t[-1], color="#fff2cc", alpha=0.55, lw=0)
    ax.plot(t, raw, color="0.45", ls=":", lw=1.4, label=L["raw"])
    ax.plot(t, shown, color="#1f77b4", ls="--", lw=1.2, label=L["shown"])
    ax.plot(t, act, color="#2e6b3a", lw=1.6, label=L["act"])
    ax.set_xlabel(L["click_x"])
    ax.set_ylabel(L["click_y"])
    ax.set_title(L["click_t"], fontsize=7)
    ax.legend(loc="upper left", frameon=True)
    ax.set_xlim(0, t[-1])
    save(fig, "fig_click", lang)


def fig_wheel(lang, rows, errs):
    L = TXT[lang]
    # cửa sổ 50 s có nhiều thay đổi lệnh nhất
    n = len(rows)
    win = 20 * 50
    best, bi = -1, 0
    for i in range(0, n - win, 20):
        s = sum(abs(rows[j + 1]["tt_muon"] - rows[j]["tt_muon"]) for j in range(i, i + win))
        if s > best:
            best, bi = s, i
    seg = rows[bi:bi + win]
    t = np.array([r["t"] - seg[0]["t"] for r in seg])
    fig, axs = plt.subplots(2, 2, figsize=(7.1, 4.4), gridspec_kw={"hspace": 0.5, "wspace": 0.28})
    for ax, w in ((axs[0, 0], "tt"), (axs[0, 1], "tp")):
        ax.plot(t, [r[f"{w}_muon"] for r in seg], "k--", lw=0.9, label=L["set"])
        ax.plot(t, [r[f"{w}_do"] for r in seg], color=COL[w], lw=0.9, label=L["meas"])
        ax.set_title(f"({'a' if w == 'tt' else 'b'}) {L['wheels'][w]}")
        ax.set_xlabel(L["time"])
        ax.set_ylabel(L["norm"] if w == "tt" else "")
        ax.set_ylim(-1.1, 1.55)
        ax.legend(loc="upper center", ncol=2, frameon=True)
    ax = axs[1, 0]
    xs = np.linspace(0, 1, 50)
    for i, w in enumerate(W):
        ax.plot(xs, FF_OFFSET[i] + FF_SLOPE[i] * xs, color=COL[w], lw=1.4,
                label=f"{L['wheels'][w]}: {FF_OFFSET[i]:.3f} + {FF_SLOPE[i]:.3f}|r|".replace(".", "," if lang == "vi" else "."))
    ax.set_title(f"(c) {L['ff_t']}")
    ax.set_xlabel(L["ff_x"])
    ax.set_ylabel(L["ff_y"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.25)
    ax.legend(loc="upper left", frameon=True)
    ax = axs[1, 1]
    data = [errs[w]["err"] for w in W]
    bp = ax.boxplot(data, tick_labels=[L["wheels"][w].replace(" ", "\n", 1) for w in W], showfliers=False, patch_artist=True,
                    whis=(5, 95), medianprops=dict(color="k", lw=1))
    for p, w in zip(bp["boxes"], W):
        p.set_facecolor(COL[w])
        p.set_alpha(0.45)
    ax.scatter(range(1, 5), [st.mean(d) for d in data], marker="D", s=14, color="k", zorder=5, label="mean" if lang == "en" else "trung bình")
    ax.axhline(0.05, color="#c0392b", ls="--", lw=1, label="5 %")
    ax.set_ylim(0, 0.105)
    ax.set_title(f"(d) {L['err_t']}")
    ax.set_ylabel(L["err_y"])
    ax.legend(loc="upper center", ncol=2, frameon=True)
    ax.tick_params(axis="x", labelsize=6.3)
    save(fig, "fig_wheel", lang)
    return bi, seg[0]["t"] - rows[0]["t"]


def fig_rtt_odo(lang, rtts, prims_for_plot):
    L = TXT[lang]
    fig, axs = plt.subplots(1, 2, figsize=(7.1, 2.5), gridspec_kw={"wspace": 0.28})
    ax = axs[0]
    bins = np.arange(0, 61, 2)
    for key, c in (("manual", "#7f7f7f"), ("gesture", "#1f77b4"), ("twohand", "#2ca02c")):
        v = np.array(rtts[key])
        ax.hist(np.clip(v, 0, 60), bins=bins, weights=np.ones_like(v) / len(v), histtype="step", lw=1.3, color=c,
                label=f"{L['sessions'][key]}, {'median' if lang == 'en' else 'trung vị'} {np.median(v):.1f} ms".replace(".", "," if lang == "vi" else "."))
    ax.set_yscale("log")
    ax.set_xlabel(L["rtt_x"] + (" (>60 ms: last bin)" if lang == "en" else " (>60 ms: cột cuối)"))
    ax.set_ylabel(L["rtt_y"])
    ax.set_title("(a) " + L["rtt_t"])
    ax.legend(loc="upper right", frameon=True)
    ax = axs[1]
    names = L["prim"]
    idx = np.arange(6)
    cmd = [prims_for_plot[k][0] for k in range(6)]
    odo = [prims_for_plot[k][1] for k in range(6)]
    ax.bar(idx - 0.19, cmd, 0.36, color="#3b6a9c", label=L["cmd"])
    ax.bar(idx + 0.19, odo, 0.36, color="#2e7d46", label=L["odo"])
    ax.set_xticks(idx)
    ax.set_xticklabels(names, fontsize=6.3, rotation=25, ha="right")
    ax.set_ylim(0, 0.72)
    ax.set_ylabel(L["odo_y"])
    ax.set_title("(b) " + L["odo_t"])
    ax.legend(loc="upper right", ncol=2, frameon=True)
    save(fig, "fig_rtt_odo", lang)


def real_click():
    rows = list(csv.DictReader(open(REAL_CLICK)))
    f = [float(r["finger_px"]) for r in rows]
    a = [float(r["action_px"]) for r in rows]
    sh = [float(r["shown_px"]) for r in rows]
    pk = [float(r["action_peak_px"]) for r in rows]
    big = [i for i, v in enumerate(f) if v >= 10]
    small = [i for i, v in enumerate(f) if v < 10]
    out = {"n": len(rows), "finger_med": st.median(f), "finger_min": min(f), "finger_max": max(f),
           "action_med": st.median(a), "action_min": min(a), "action_max": max(a),
           "shown_med": st.median(sh), "peak_med": st.median(pk),
           "reduction_med": 1 - st.median(a) / st.median(f),
           "reduction_mean": 1 - st.mean(a) / st.mean(f),
           "action_gt_finger": sum(1 for x, y in zip(f, a) if y > x),
           "n_big": len(big), "big_finger_med": st.median([f[i] for i in big]) if big else None,
           "big_action_med": st.median([a[i] for i in big]) if big else None,
           "n_small": len(small), "small_finger_med": st.median([f[i] for i in small]) if small else None,
           "small_action_med": st.median([a[i] for i in small]) if small else None}
    if big:
        out["big_reduction"] = 1 - out["big_action_med"] / out["big_finger_med"]
    return out, f, a


def fig_real(lang, f, a):
    L = TXT[lang]
    fig, ax = plt.subplots(figsize=(3.3, 2.9))
    m = max(max(f), max(a)) * 1.08
    ax.plot([0, m], [0, m], color="0.5", ls="--", lw=1, label="y = x (" + L["real_eq"] + ")")
    ax.scatter(f, a, s=22, color="#2e6b3a", zorder=3, label=f"{len(f)} {L['real_n']}")
    ax.set_xlim(0, m)
    ax.set_ylim(0, m)
    ax.set_aspect("equal")
    ax.set_xlabel(L["real_x"])
    ax.set_ylabel(L["real_y"])
    ax.set_title(L["real_t"], fontsize=7.5)
    ax.legend(loc="upper left", frameon=True)
    save(fig, "fig_real", lang)


# ---------------------------------------------------------------- chạy
def main():
    stats = {}
    sess = {}
    for k in DATA:
        rows, bad = load(k)
        errs = wheel_errors(rows)
        rtt = [r["rtt_ms"] for r in rows]
        sess[k] = (rows, errs, rtt)
        stats[k] = {
            "rows": len(rows), "dropped_unpowered": bad, "duration_s": rows[-1]["t"] - rows[0]["t"],
            "modes": {m: sum(1 for r in rows if r["mode"] == m) for m in ("manual", "gesture")},
            "rtt_median": st.median(rtt), "rtt_p95": pct(rtt, 0.95), "rtt_max": max(rtt),
            "wheel_mean": {w: st.mean(errs[w]["err"]) for w in W},
            "wheel_p95": {w: pct(errs[w]["err"], 0.95) for w in W},
            "pwm_mean": {w: st.mean(errs[w]["pwm"]) for w in W},
            "pwm_max": {w: max(errs[w]["pwm"]) for w in W},
            "prims": primitives(rows),
        }
        if any(r["mode"] == "gesture" for r in rows):
            stats[k]["gesture"] = gesture_stats(rows)
    stats["total_rows"] = sum(stats[k]["rows"] for k in DATA)
    stats["total_duration_s"] = sum(stats[k]["duration_s"] for k in DATA)

    jitter, click, sim = cursor_sim()
    stats["jitter"], stats["click"] = jitter, click
    stats["real_click"], real_f, real_a = real_click()
    stats["real_jitter"] = json.load(open(ROOT / "docs/data/v2/real_hand_jitter.json"))

    # độ lớn lệnh / odometry cho 6 chuyển động cơ bản: gộp phiên cử chỉ v1 (đủ 6 hướng)
    P = stats["gesture"]["prims"]
    order = [("fwd", 0), ("back", 0), ("left", 1), ("right", 1), ("rotl", 2), ("rotr", 2)]
    plot = [(abs(P[m]["cmd"][a]), abs(P[m]["odo"][a])) for m, a in order]
    stats["prim_table"] = {m: {"n": P[m]["n"], "cmd": P[m]["cmd"], "odo": P[m]["odo"],
                               "err_pct": 100 * (abs(P[m]["odo"][a]) - abs(P[m]["cmd"][a])) / abs(P[m]["cmd"][a]),
                               "cross_max": max(abs(P[m]["odo"][k]) for k in range(3) if k != a)} for m, a in order}
    for m in ("fwd+left", "fwd+right"):
        Q = sess["twohand"][0] and stats["twohand"]["prims"].get(m)
        if Q:
            stats["prim_table"]["twohand_" + m] = {"n": Q["n"], "cmd": Q["cmd"], "odo": Q["odo"]}

    for lang in ("en", "vi"):
        fig_arch(lang)
        fig_real(lang, real_f, real_a)
        fig_kin(lang)
        fig_ctrl(lang)
        fig_click(lang, sim)
        bi, t0 = fig_wheel(lang, sess["twohand"][0], sess["twohand"][1])
        fig_rtt_odo(lang, {k: sess[k][2] for k in DATA}, plot)
    stats["trace_window"] = {"start_s": t0, "length_s": 50}
    json.dump(stats, open(OUT / "stats.json", "w"), indent=1, default=float)
    print("ok ->", OUT)


if __name__ == "__main__":
    main()
