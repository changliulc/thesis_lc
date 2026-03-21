#!/usr/bin/env python3
"""
Build a real-data inspired segmented D-case single-axis preview:
- left: parking entry from the new D event source
- middle: 7 h occupied-platform drift from long-run background trend
- right: vehicle exit from the same new D event source

This is a display-oriented layout preview for the revised Chapter 4 figure.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch4_wave_refresh"
IMG_DIR = REPO_ROOT / "images"

SRC_DIR = Path(r"D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi")
SRC_CSV = SRC_DIR / "20240723_停车检测_sheet1_clean.csv"
GT_CSV = SRC_DIR / "parking_groundtruth_filled_cleaned.csv"
OLD_D_CSV = REPO_ROOT / "tmp" / "ch4_wave_refresh" / "fig_d_win_new.csv"

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def moving_average(arr: np.ndarray, win: int) -> np.ndarray:
    if win <= 1:
        return arr.copy()
    if win % 2 == 0:
        win += 1
    pad = win // 2
    arr_pad = np.pad(arr, (pad, pad), mode="edge")
    ker = np.ones(win, dtype=float) / float(win)
    return np.convolve(arr_pad, ker, mode="valid")


def load_new_d_event() -> tuple[pd.DataFrame, float, float]:
    df = pd.read_csv(SRC_CSV)
    gt = pd.read_csv(GT_CSV)

    # D events for 20240723 sheet1 are rows 4:7; event 3 is the cleanest.
    row = gt.iloc[6]
    start_t = float(row["t_star_in_sec"])
    end_t = float(row["t_star_out_sec"])

    pre = 7.0
    post = 8.0
    mask = (df["t"] >= start_t - pre) & (df["t"] <= end_t + post)
    out = df.loc[mask, ["t", "x"]].copy()
    return out.reset_index(drop=True), start_t, end_t


def add_break_marks(ax_left, ax_right, size: float = 0.015) -> None:
    kwargs = dict(transform=ax_left.transAxes, color="0.35", clip_on=False, linewidth=1.0)
    ax_left.plot((1 - size, 1 + size), (-size, +size), **kwargs)
    ax_left.plot((1 - size, 1 + size), (1 - size, 1 + size), **kwargs)
    kwargs = dict(transform=ax_right.transAxes, color="0.35", clip_on=False, linewidth=1.0)
    ax_right.plot((-size, +size), (-size, +size), **kwargs)
    ax_right.plot((-size, +size), (1 - size, 1 + size), **kwargs)


def safe_pick(arr_t: np.ndarray, arr_y: np.ndarray, t_query: float) -> tuple[float, float]:
    idx = int(np.searchsorted(arr_t, t_query))
    idx = max(0, min(idx, len(arr_t) - 1))
    return float(arr_t[idx]), float(arr_y[idx])


def build_middle_platform_from_old_preview() -> tuple[np.ndarray, np.ndarray, float]:
    """
    Reuse the occupied X-axis drift shape from the earlier 7 h D preview.
    This preserves the old drift amount the user preferred.
    """
    df = pd.read_csv(OLD_D_CSV)
    # These are the same settings used in the old 7 h synthesized D figure.
    pre_h = 0.45
    entry_h = 25.0 / 3600.0
    occ_h = 6.086111111111111
    occ_start = pre_h + entry_h
    occ_end = occ_start + occ_h
    mask = (df["t"] >= occ_start) & (df["t"] <= occ_end)
    occ = df.loc[mask, ["t", "x"]].copy()
    if len(occ) < 10:
        raise RuntimeError("Old D preview occupied segment too short")

    t_src = occ["t"].to_numpy(dtype=float) - float(occ["t"].iloc[0])
    y_src = occ["x"].to_numpy(dtype=float)
    t_h = np.linspace(0.0, 7.0, 420)
    y = np.interp(t_h, np.linspace(0.0, 7.0, len(y_src)), y_src)
    ref = float(df["x"].iloc[0])
    return t_h, y, ref


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    event_df, occ_start, occ_end = load_new_d_event()
    t = event_df["t"].to_numpy(dtype=float)
    x = event_df["x"].to_numpy(dtype=float)
    ref = float(x[0])

    # Use narrower real second-level windows and keep their original local time.
    left_mask = (t >= occ_start - 4.2) & (t <= occ_start + 2.1)
    right_mask = (t >= occ_end - 2.8) & (t <= occ_end + 4.8)

    t_left = t[left_mask]
    x_left = x[left_mask]

    t_right = t[right_mask]
    x_right = x[right_mask]

    t_mid_h, x_mid, old_ref = build_middle_platform_from_old_preview()
    ref = old_ref

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(8.8, 4.7),
        gridspec_kw={"width_ratios": [0.92, 2.05, 0.92], "wspace": 0.08},
        constrained_layout=True,
    )
    ax1, ax2, ax3 = axes

    y_all = np.concatenate([x_left, x_mid, x_right, np.asarray([ref])])
    y_pad = 0.06 * float(np.max(y_all) - np.min(y_all))
    y_min = float(np.min(y_all) - y_pad)
    y_max = float(np.max(y_all) + y_pad)

    for ax in axes:
        ax.axhline(ref, color="#d62728", linestyle="--", linewidth=1.15, alpha=0.92)
        ax.grid(True, alpha=0.18)
        ax.tick_params(labelsize=9)
        ax.set_ylim(y_min, y_max)

    # Left entry segment
    ax1.axvspan(occ_start, t_left[-1], color="0.93", alpha=0.95, zorder=0)
    ax1.plot(t_left, x_left, color="#1f77b4", linewidth=1.8)
    ax1.set_ylabel(r"$B_x$", fontsize=14)
    ax1.set_xlabel("Time / s", fontsize=10)
    ax1.set_title("D类慢漂移背景场景（X轴，分段展示）", fontsize=13, pad=6)
    entry_tx, entry_ty = safe_pick(t_left, x_left, occ_start + 1.0)
    ax1.annotate(
        "进入",
        xy=(entry_tx, entry_ty),
        xytext=(max(0.8, occ_start - 4.0), ref + 95),
        arrowprops=dict(arrowstyle="->", lw=0.9, color="0.25"),
        fontsize=9,
        color="0.25",
    )

    # Middle 7 h drift segment
    ax2.axvspan(0.0, 7.0, color="0.93", alpha=0.95, zorder=0)
    ax2.plot(t_mid_h, x_mid, color="#1f77b4", linewidth=1.8)
    ax2.set_xlabel("Time / h", fontsize=10)
    ax2.text(
        0.5,
        0.08,
        "停车占用平台\n缓慢漂移",
        transform=ax2.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        color="0.30",
    )

    # Right exit segment
    exit_occ_end = max(0.0, occ_end - t[right_mask][0])
    ax3.axvspan(t_right[0], t_right[0] + exit_occ_end, color="0.93", alpha=0.95, zorder=0)
    ax3.plot(t_right, x_right, color="#1f77b4", linewidth=1.8)
    ax3.set_xlabel("Time / s", fontsize=10)
    exit_xy_t = min(t_right[-1], t_right[0] + exit_occ_end + 0.55)
    exit_tx, exit_ty = safe_pick(t_right, x_right, exit_xy_t)
    ax3.annotate(
        "驶离",
        xy=(exit_tx, exit_ty),
        xytext=(min(t_right[-1] - 1.2, t_right[0] + exit_occ_end + 2.0), ref + 88),
        arrowprops=dict(arrowstyle="->", lw=0.9, color="0.25"),
        fontsize=9,
        color="0.25",
    )

    # Reduce clutter on the middle / right panels.
    for ax in [ax2, ax3]:
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelleft=False)

    # Omission markers and break marks.
    ax1.text(1.02, 0.5, "...", transform=ax1.transAxes, fontsize=16, color="0.4", va="center")
    ax2.text(1.02, 0.5, "...", transform=ax2.transAxes, fontsize=16, color="0.4", va="center")
    add_break_marks(ax1, ax2)
    add_break_marks(ax2, ax3)

    preview = OUT_DIR / "ch4_wave_D_single_axis_segmented_real.png"
    img = IMG_DIR / "ch4_wave_D_single_axis_segmented_real.png"
    fig.savefig(preview, dpi=220, bbox_inches="tight")
    fig.savefig(img, dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved preview to: {preview}")
    print(f"Saved image copy to: {img}")


if __name__ == "__main__":
    main()
