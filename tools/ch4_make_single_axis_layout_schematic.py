#!/usr/bin/env python3
"""
Schematic preview for the proposed Chapter 4 figure layout:
- A/B/C: single-axis (X-axis only) local windows
- D: single-axis segmented display (entry / long dwell drift / exit)

This is intentionally synthetic and only used to confirm layout understanding.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch4_wave_refresh"
IMG_DIR = REPO_ROOT / "images"


plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def smooth_step(x: np.ndarray, center: float, width: float) -> np.ndarray:
    return 0.5 * (1.0 + np.tanh((x - center) / width))


def make_case_a():
    t = np.linspace(0, 32, 500)
    base = -895 + 2.0 * np.sin(2 * np.pi * t / 22)
    occ = 240 * (smooth_step(t, 9.2, 0.35) - smooth_step(t, 19.6, 0.5))
    leave = -40 * np.exp(-0.5 * ((t - 20.8) / 0.6) ** 2)
    y = base + occ + leave + 1.3 * np.sin(2 * np.pi * t / 0.5)
    return t, y, float(base[0])


def make_case_b():
    t = np.linspace(0, 36, 600)
    base = -900 + 1.2 * np.sin(2 * np.pi * t / 16)
    occ = 255 * (smooth_step(t, 6.8, 0.28) - smooth_step(t, 30.8, 0.55))
    interference = (
        26 * np.exp(-0.5 * ((t - 14.2) / 0.22) ** 2)
        - 32 * np.exp(-0.5 * ((t - 16.1) / 0.24) ** 2)
        + 38 * np.exp(-0.5 * ((t - 18.7) / 0.26) ** 2)
        - 24 * np.exp(-0.5 * ((t - 22.3) / 0.20) ** 2)
        + 19 * np.exp(-0.5 * ((t - 24.9) / 0.22) ** 2)
    )
    y = base + occ + interference + 1.1 * np.sin(2 * np.pi * t / 0.45)
    return t, y, float(base[0])


def make_case_c():
    t = np.linspace(0, 68, 800)
    base = -898 + 1.5 * np.sin(2 * np.pi * t / 28)
    long_occ = 275 * (smooth_step(t, 18.0, 0.42) - smooth_step(t, 50.5, 0.6))
    busy = (
        24 * np.sin(2 * np.pi * t / 2.4) * ((t > 12) & (t < 56)).astype(float)
        + 18 * np.sin(2 * np.pi * t / 1.2) * ((t > 14) & (t < 55)).astype(float)
    )
    y = base + long_occ + busy
    return t, y, float(base[0])


def make_case_d_segments():
    # Left: parking entry
    t1 = np.linspace(0, 16, 260)
    ref = -740.0
    base1 = ref + 1.8 * np.sin(2 * np.pi * t1 / 10)
    seg1 = base1 + 245 * smooth_step(t1, 10.6, 0.65) + 10 * np.exp(-0.5 * ((t1 - 12.8) / 0.5) ** 2)

    # Middle: long dwell with slow drift
    t2 = np.linspace(0, 7, 420)
    seg2 = -492 + 18 * t2 / 7 + 8 * np.sin(2 * np.pi * t2 / 3.8) - 6 * np.exp(-0.5 * ((t2 - 4.9) / 0.38) ** 2)

    # Right: vehicle exit
    t3 = np.linspace(0, 16, 260)
    base3 = -720 + 9 * t3 / 16 + 2.0 * np.sin(2 * np.pi * t3 / 9)
    seg3 = base3 - 245 * smooth_step(t3, 4.8, 0.72) - 12 * np.exp(-0.5 * ((t3 - 6.0) / 0.55) ** 2)
    return (t1, seg1), (t2, seg2), (t3, seg3), ref


def add_break_marks(ax_left, ax_right, size=0.015):
    kwargs = dict(transform=ax_left.transAxes, color="0.35", clip_on=False, linewidth=1.0)
    ax_left.plot((1 - size, 1 + size), (-size, +size), **kwargs)
    ax_left.plot((1 - size, 1 + size), (1 - size, 1 + size), **kwargs)
    kwargs = dict(transform=ax_right.transAxes, color="0.35", clip_on=False, linewidth=1.0)
    ax_right.plot((-size, +size), (-size, +size), **kwargs)
    ax_right.plot((-size, +size), (1 - size, 1 + size), **kwargs)


def style_single_axis(ax, t, y, ref, title, xlabel="Time / s", occupancy=None):
    if occupancy is not None:
        ax.axvspan(*occupancy, color="0.93", alpha=0.95, zorder=0)
    ax.plot(t, y, color="#1f77b4", linewidth=1.7)
    ax.axhline(ref, color="#d62728", linestyle="--", linewidth=1.15, alpha=0.92)
    ax.set_title(title, fontsize=13, pad=6)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(r"$B_x$", fontsize=14)
    ax.grid(True, alpha=0.18)
    ax.tick_params(labelsize=10)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(12.8, 8.6), constrained_layout=True)
    outer = GridSpec(2, 2, figure=fig)

    # A
    axA = fig.add_subplot(outer[0, 0])
    t, y, ref = make_case_a()
    style_single_axis(axA, t, y, ref, "(a) A类正常车流单车停车场景（X轴）", occupancy=(9.2, 19.6))

    # B
    axB = fig.add_subplot(outer[0, 1])
    t, y, ref = make_case_b()
    style_single_axis(axB, t, y, ref, "(b) B类占用期过车干扰场景（X轴）", occupancy=(6.8, 30.8))

    # C
    axC = fig.add_subplot(outer[1, 0])
    t, y, ref = make_case_c()
    style_single_axis(axC, t, y, ref, "(c) C类连续车流稳定窗缺失场景（X轴）", occupancy=(18.0, 50.5))

    # D segmented
    sub = outer[1, 1].subgridspec(1, 3, width_ratios=[1.25, 1.75, 1.25], wspace=0.08)
    axD1 = fig.add_subplot(sub[0, 0])
    axD2 = fig.add_subplot(sub[0, 1])
    axD3 = fig.add_subplot(sub[0, 2])

    (t1, y1), (t2, y2), (t3, y3), ref = make_case_d_segments()

    for ax in [axD1, axD2, axD3]:
        ax.axhline(ref, color="#d62728", linestyle="--", linewidth=1.15, alpha=0.92)
        ax.plot([], [])  # keep axes initialized the same way
        ax.grid(True, alpha=0.18)
        ax.tick_params(labelsize=9)
        ax.set_ylabel(r"$B_x$", fontsize=14)

    axD1.plot(t1, y1, color="#1f77b4", linewidth=1.7)
    axD1.axvspan(10.6, 16.0, color="0.93", alpha=0.95)
    axD1.set_title("(d) D类慢漂移背景场景（X轴，分段展示）", fontsize=13, pad=6)
    axD1.set_xlabel("Time / s", fontsize=10)
    axD1.annotate("进入", xy=(10.9, -520), xytext=(7.3, -655),
                  arrowprops=dict(arrowstyle="->", lw=0.9, color="0.25"),
                  fontsize=9, color="0.25")

    axD2.plot(t2, y2, color="#1f77b4", linewidth=1.7)
    axD2.axvspan(0.0, 7.0, color="0.93", alpha=0.95)
    axD2.set_xlabel("Time / h", fontsize=10)
    axD2.text(0.5, 0.08, "停车占用平台\n缓慢漂移", transform=axD2.transAxes,
              ha="center", va="bottom", fontsize=9, color="0.30")

    axD3.plot(t3, y3, color="#1f77b4", linewidth=1.7)
    axD3.set_xlabel("Time / s", fontsize=10)
    axD3.annotate("驶离", xy=(5.1, -525), xytext=(8.3, -655),
                  arrowprops=dict(arrowstyle="->", lw=0.9, color="0.25"),
                  fontsize=9, color="0.25")

    # make only left-most D axis show y tick labels to reduce clutter
    for ax in [axD2, axD3]:
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelleft=False)

    # Ellipsis between D segments
    axD1.text(1.02, 0.5, "...", transform=axD1.transAxes, fontsize=16, color="0.4", va="center")
    axD2.text(1.02, 0.5, "...", transform=axD2.transAxes, fontsize=16, color="0.4", va="center")
    add_break_marks(axD1, axD2)
    add_break_marks(axD2, axD3)

    fig.suptitle("图 4.8 重绘思路示意：A/B/C 单轴，D 分段展示", fontsize=16)

    out = OUT_DIR / "ch4_single_axis_layout_schematic.png"
    img = IMG_DIR / "ch4_single_axis_layout_schematic.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    fig.savefig(img, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved preview to: {out}")
    print(f"Saved image copy to: {img}")


if __name__ == "__main__":
    main()
