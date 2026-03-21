#!/usr/bin/env python3
"""
Generate a Chapter-2 magnetic-drift figure using real long-run XDat data.

Current target style:
- close to the senior's raw-drift figure style
- 3 stacked single-line subplots
- x-axis shown in hours
- use a long interval (~20 h) so drift is visually obvious

Current chosen data view:
- interval: 0 h to 15 h
- aggregation: 5 s median
- light smoothing: 10 s moving average

This keeps the figure readable while preserving visible disturbance.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch2_mag_drift_refresh"
IMG_DIR = REPO_ROOT / "images"
XDAT_PATH = Path(r"D:\xidian_Master\研究生论文\毕业论文\实验数据\2026-03-18 091512.XDat")


plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def parse_xdat_xyz(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pat = re.compile(r"(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\d+:\d+:\d+\.\d+")
    xs, ys, zs = [], [], []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = pat.search(line)
            if m:
                xs.append(int(m.group(1)))
                ys.append(int(m.group(2)))
                zs.append(int(m.group(3)))
    if not xs:
        raise RuntimeError(f"No XYZ samples parsed from {path}")
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float), np.asarray(zs, dtype=float)


def block_median(arr: np.ndarray, block: int) -> np.ndarray:
    n = len(arr)
    full = n // block
    if full == 0:
        return np.asarray([np.median(arr)], dtype=float)
    trimmed = arr[: full * block].reshape(full, block)
    meds = np.median(trimmed, axis=1)
    if full * block < n:
        meds = np.concatenate([meds, [np.median(arr[full * block :])]])
    return meds


def moving_average(arr: np.ndarray, win: int) -> np.ndarray:
    if win <= 1:
        return arr.copy()
    if win % 2 == 0:
        win += 1
    pad = win // 2
    arr_pad = np.pad(arr, (pad, pad), mode="edge")
    ker = np.ones(win, dtype=float) / float(win)
    return np.convolve(arr_pad, ker, mode="valid")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    if not XDAT_PATH.exists():
        raise FileNotFoundError(XDAT_PATH)

    x, y, z = parse_xdat_xyz(XDAT_PATH)
    fs = 50.0

    interval_h = (0.0, 15.0)
    sample_sec = 5.0
    smooth_sec = 10.0

    start = int(interval_h[0] * 3600.0 * fs)
    end = int(interval_h[1] * 3600.0 * fs)
    block = max(1, int(round(fs * sample_sec)))
    bx = block_median(x[start:end], block)
    by = block_median(y[start:end], block)
    bz = block_median(z[start:end], block)

    smooth_win = int(round(smooth_sec / sample_sec))
    bx = moving_average(bx, smooth_win)
    by = moving_average(by, smooth_win)
    bz = moving_average(bz, smooth_win)

    t_h = np.arange(len(bx)) * sample_sec / 3600.0

    fig, axes = plt.subplots(3, 1, figsize=(12.6, 7.4), sharex=True, constrained_layout=True)
    series = [
        (bx, "X轴", 1.00, 3.0),
        (by, "Y轴", 1.00, 3.0),
        (bz, "Z轴", 3.20, 14.0),
    ]

    for ax, (arr, name, pad_scale, pad_floor) in zip(axes, series):
        ax.plot(t_h, arr, color="#1f77b4", linewidth=0.95, label=name)
        ax.set_ylabel("磁场强度(nT)", fontsize=12)
        ax.legend(loc="upper right", fontsize=10, frameon=True)
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=10)
        lo, hi = np.percentile(arr, [0.5, 99.5])
        pad = max(pad_floor, 0.10 * (hi - lo)) * pad_scale
        ax.set_ylim(lo - pad, hi + pad)

    axes[-1].set_xlabel("时间(h)", fontsize=12)
    axes[-1].set_xlim(0, float(t_h[-1]))

    preview_path = OUT_DIR / "fig_mag_drift_real_15h_hours_preview.png"
    thesis_path = IMG_DIR / "fig_mag_drift_real_15h_hours.png"
    fig.savefig(preview_path, dpi=220, bbox_inches="tight")
    fig.savefig(thesis_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    meta = {
        "xdat_path": str(XDAT_PATH),
        "interval_hours": [float(interval_h[0]), float(interval_h[1])],
        "sample_sec": sample_sec,
        "smooth_sec": smooth_sec,
        "duration_hours": float(t_h[-1]),
        "span_nT": {
            "Bx": float(np.max(bx) - np.min(bx)),
            "By": float(np.max(by) - np.min(by)),
            "Bz": float(np.max(bz) - np.min(bz)),
        },
        "style": "single_line_hour_axis_like_senior",
    }
    (OUT_DIR / "fig_mag_drift_real_15h_hours_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Saved preview to: {preview_path}")
    print(f"Saved thesis image copy: {thesis_path}")


if __name__ == "__main__":
    main()
