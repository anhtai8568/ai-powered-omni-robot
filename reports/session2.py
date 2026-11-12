"""
Số liệu và hình của phiên chạy thứ hai (logs thật do server.py ghi, đã chép vào docs/data/v2/session2/).

    .venv/bin/python reports/session2.py

Đầu ra: reports/figures/fig_sess2_<en|vi>.{pdf,png} và reports/figures/stats_session2.json.
Bốn phiên: A, B chạy mã c6df4be (camera 640x480, con trỏ 1:1), C chạy 08d3d43 và D chạy 3484375
(camera 1280x720, con trỏ kéo giãn gần mép; C đường gãy, D đường mượt). A, B có robot; C, D chỉ thử con trỏ.
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from analyze_run import latency  # noqa: E402

D = ROOT / "docs/data/v2/session2"
OUT = ROOT / "reports" / "figures"
W = ["tt", "tp", "st", "sp"]
SESS = {  # id: (ai csv, drive csv hoặc None, mã, camera, con trỏ)
    "A": ("ai_20261112_185804", "drive_20261112_185814", "c6df4be", "640x480", "1:1"),
    "B": ("ai_20261112_193058", "drive_20261112_193058", "c6df4be", "640x480", "1:1"),
    "C": ("ai_20261112_203603", None, "08d3d43", "1280x720", "stretch"),
    "D": ("ai_20261112_204209", None, "3484375", "1280x720", "smooth"),
}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
                     "axes.grid": True, "grid.linestyle": ":", "grid.alpha": 0.5, "pdf.fonttype": 42, "savefig.dpi": 300})


def rd(p):
    return list(csv.DictReader(open(p)))


def pct(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))]


def tracking(dr):
    out = {}
    for mode in ("manual", "gesture"):
        e, sat, n = [], 0, 0
        for i in range(6, len(dr)):
            if dr[i]["mode"] != mode:
                continue
            for w in W:
                T = float(dr[i][f"{w}_muon"])
                if abs(T) >= 0.1 and all(abs(float(dr[j][f"{w}_muon"]) - T) < 0.01 for j in range(i - 6, i)):
                    e.append(abs(float(dr[i][f"{w}_do"]) - T))
                    sat += abs(float(dr[i][f"{w}_pwm"])) >= 0.95
                    n += 1
        if n:
            out[mode] = {"n": n, "mean_pct": 100 * st.mean(e), "p95_pct": 100 * pct(e, .95), "sat_pct": 100 * sat / n}
    return out


def ui_segments(ai):
    """Đoạn liên tiếp có tay giao diện (>0.3 s); đếm số đoạn kết thúc khi con trỏ sát mép (<2% màn hình)."""
    segs, cur, last = [], None, None
    for x in ai:
        t = float(x["t"])
        if x["ui_pose"] != "none":
            cur = [t, t] if cur is None else cur
            cur[1], last = t, x
        elif cur is not None:
            segs.append((cur[1] - cur[0], last))
            cur = None
    if cur:
        segs.append((cur[1] - cur[0], last))
    edge = lambda x: min(float(x["cx"]), 1 - float(x["cx"]), float(x["cy"]), 1 - float(x["cy"])) < 0.02
    seg = [s for s in segs if s[0] > 0.3]
    act = [x for x in ai if x["ui_pose"] != "none"]
    return {"segments": len(seg), "ended_at_edge": sum(edge(s[1]) for s in seg),
            "active_frames": len(act), "edge_frames": sum(edge(x) for x in act),
            "click_frames": sum(x["ui_pose"] == "click" for x in ai)}


def main():
    stats, infer_all = {}, {}
    for k, (a, d, code, cam, cur) in SESS.items():
        ai = rd(D / f"{a}.csv")
        t = [float(x["t"]) for x in ai]
        span = t[-1] - t[0]
        s = {"code": code, "camera": cam, "cursor": cur, "frames": len(ai), "seconds": span, "fps": len(ai) / span,
             "gap_p95_ms": 1000 * pct([b - c for c, b in zip(t, t[1:])], .95), "infer": {}, "ui": ui_segments(ai)}
        infer_all[k] = {}
        for n in "012":
            x = [float(r["infer_ms"]) for r in ai if r["n_hands"] == n]
            infer_all[k][n] = x
            if x:
                s["infer"][n] = {"n": len(x), "mean": st.mean(x), "median": st.median(x), "p95": pct(x, .95)}
        if d:
            dr = rd(D / f"{d}.csv")
            lat, lat_cmd, tg = latency(ai, dr)
            rtt = [float(r["rtt_ms"]) for r in dr]
            s["drive"] = {"rows": len(dr), "seconds": float(dr[-1]["t"]) - float(dr[0]["t"]),
                          "rtt_median": st.median(rtt), "rtt_p95": pct(rtt, .95), "rtt_max": max(rtt),
                          "tracking": tracking(dr)}
            if lat:
                s["latency"] = {"n": len(lat), "median": st.median(lat), "min": min(lat), "max": max(lat),
                                "p95": pct(lat, .95), "to_cmd_median": st.median(lat_cmd) if lat_cmd else None,
                                "target_median": st.median(tg), "values": lat}
        stats[k] = s
    json.dump(stats, open(OUT / "stats_session2.json", "w"), indent=1, default=float)

    T = {"en": ("Hand-landmark inference time (ms)", "No hand", "One hand", "Two hands",
                "Camera frame to 50% wheel speed (ms)", "Gesture events", "Session"),
         "vi": ("Thời gian suy luận tay (ms)", "Không tay", "Một tay", "Hai tay",
                "Từ khung camera đến bánh đạt 50% (ms)", "Các lần cử chỉ", "Phiên")}
    A = stats["A"].get("latency", {}).get("values", [])
    for lang, (yl, n0, n1, n2, xl, tl, sl) in T.items():
        fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.5), gridspec_kw={"width_ratios": [1.7, 1]})
        pos, data, labs = [], [], []
        for i, k in enumerate(SESS):
            for j, n in enumerate("012"):
                if infer_all[k][n]:
                    pos.append(i * 4 + j)
                    data.append(infer_all[k][n])
        bp = ax[0].boxplot(data, positions=pos, widths=0.8, showfliers=False, patch_artist=True)
        for p, ps in zip(bp["boxes"], pos):
            p.set_facecolor(["#9ecae1", "#fdae6b", "#a1d99b"][ps % 4])
        ax[0].set_xticks([i * 4 + 1 for i in range(4)])
        ax[0].set_xticklabels([f"{sl} {k}\n{SESS[k][3]}" for k in SESS])
        ax[0].set_ylabel(yl)
        ax[0].legend([bp["boxes"][0], bp["boxes"][1], bp["boxes"][2]], [n0, n1, n2], loc="upper left", ncol=3, fontsize=6)
        ax[0].set_ylim(0, 95)
        ax[0].set_title("(a)")
        ax[1].hist(A, bins=12, color="#6baed6", edgecolor="white")
        ax[1].axvline(st.median(A), color="#d62728", ls="--", lw=1)
        ax[1].set_xlabel(xl)
        ax[1].set_ylabel(tl)
        ax[1].set_title("(b)")
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(OUT / f"fig_sess2_{lang}.{ext}", bbox_inches="tight", pad_inches=0.03)
        plt.close(fig)
    print(json.dumps({k: {x: v for x, v in s.items() if x not in ("latency",)} | ({"latency": {y: z for y, z in s["latency"].items() if y != "values"}} if "latency" in s else {}) for k, s in stats.items()}, indent=1, default=float))


if __name__ == "__main__":
    main()
