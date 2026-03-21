#!/usr/bin/env python3
"""
Build a display-oriented D-case preview:
- main plot: a cleaner local D-case parking event from the original D source file
- inset: a 7 h long-run background overview

This keeps the main plot readable and lets us tune the visual effect before
deciding whether to integrate it into the thesis figure.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch4_wave_refresh"
IMG_DIR = REPO_ROOT / "images"
SRC_DIR = Path(r"D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi")
SRC_CSV = SRC_DIR / "20240723_停车检测_sheet1_clean.csv"
GT_CSV = SRC_DIR / "parking_groundtruth_filled_cleaned.csv"
LONG_XDAT = Path(r"D:\xidian_Master\研究生论文\毕业论文\实验数据\2026-03-18 091512.XDat")


plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def parse_xdat_z(path: Path) -> np.ndarray:
    pat = re.compile(r"(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\d+:\d+:\d+\.\d+")
    zs: list[int] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = pat.search(line)
            if m:
                zs.append(int(m.group(3)))
    if not zs:
        raise RuntimeError(f"No Z samples parsed from {path}")
    return np.asarray(zs, dtype=float)


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


def load_cleaner_d_event() -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(SRC_CSV)
    gt = pd.read_csv(GT_CSV)

    # The D events for 20240723 sheet1 are rows 4:7 in this cleaned GT table.
    # Event 3 is visually the cleanest among the three D events.
    row = gt.iloc[6]
    start_t = float(row["t_star_in_sec"])
    end_t = float(row["t_star_out_sec"])

    pre = 7.0
    post = 8.0
    mask = (df["t"] >= start_t - pre) & (df["t"] <= end_t + post)
    out = df.loc[mask, ["t", "x", "y", "z"]].copy()
    out["t"] = out["t"] - float(out["t"].iloc[0])
    ref = out.loc[out.index[0], ["x", "y", "z"]].to_numpy(dtype=float)
    return out.reset_index(drop=True), ref


def build_inset_series() -> tuple[np.ndarray, np.ndarray]:
    z = parse_xdat_z(LONG_XDAT)
    fs = 50.0
    start_h = 11.0
    duration_h = 7.0
    start = int(round(start_h * 3600.0 * fs))
    end = int(round((start_h + duration_h) * 3600.0 * fs))
    block_sec = 15.0
    block = int(round(fs * block_sec))

    bz = block_median(z[start:end], block)
    bz = moving_average(bz, 9)
    t_h = np.arange(len(bz)) * block_sec / 3600.0
    return t_h, bz


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    loc, ref = load_cleaner_d_event()
    t_bg_h, bz_bg = build_inset_series()

    fig, axes = plt.subplots(3, 1, figsize=(9.6, 7.2), sharex=True, constrained_layout=True)
    names = [("x", r"$B_x$"), ("y", r"$B_y$"), ("z", r"$B_z$")]

    for ax, (col, label), ref_val in zip(axes, names, ref):
        ax.plot(loc["t"], loc[col], color="#1f77b4", linewidth=1.55)
        ax.axhline(ref_val, color="#d62728", linestyle="--", linewidth=1.15, alpha=0.9)
        ax.set_ylabel(label, fontsize=14)
        ax.grid(True, alpha=0.18)
        ax.tick_params(labelsize=11)

    axes[-1].set_xlabel("Time / s", fontsize=14)

    axin = inset_axes(axes[0], width="29%", height="31%", loc="upper right", borderpad=1.15)
    axin.plot(t_bg_h, bz_bg, color="#707070", linewidth=1.25)
    axin.set_title("Long-run background", fontsize=8.2, pad=2)
    axin.set_xlabel("Time / h", fontsize=7)
    axin.grid(True, alpha=0.10)
    axin.tick_params(labelsize=6.5, pad=1)
    for spine in axin.spines.values():
        spine.set_linewidth(0.85)
    axin.set_facecolor("white")

    preview = OUT_DIR / "ch4_wave_D_inset_preview_v2.png"
    thesis = IMG_DIR / "ch4_wave_D_inset_preview_v2.png"
    fig.savefig(preview, dpi=220, bbox_inches="tight")
    fig.savefig(thesis, dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved preview to: {preview}")
    print(f"Saved image copy to: {thesis}")


if __name__ == "__main__":
    main()
