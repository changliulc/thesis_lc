#!/usr/bin/env python3
"""
Create a schematic D-case figure:
- local second-level main plot (Bx/By/Bz)
- one small 7 h long-run overview inset on the first axis

This is intentionally synthetic and only used to preview the visual layout.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


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


def build_local_main() -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float], tuple[float, float]]:
    t = np.linspace(0.0, 60.0, 1201)
    occ_start = 13.0
    occ_end = 46.0

    up = smooth_step(t, occ_start, 0.85)
    down = smooth_step(t, occ_end, 0.95)
    occ = up - down

    # Background drift visible before, during and after occupancy.
    bg_x = -738.0 + 0.14 * t - 4.5 * np.sin(2 * np.pi * t / 85.0)
    bg_y = -2128.0 - 0.22 * t + 3.5 * np.sin(2 * np.pi * (t + 7.0) / 92.0)
    bg_z = -1689.0 + 0.18 * t + 3.0 * np.sin(2 * np.pi * (t - 5.0) / 78.0)

    # Parking occupancy offsets for each axis.
    occ_x = 265.0 * occ - 10.0 * occ * (t - occ_start) / max(occ_end - occ_start, 1.0)
    occ_y = -42.0 * occ + 6.0 * occ * (t - occ_start) / max(occ_end - occ_start, 1.0)
    occ_z = 58.0 * occ + 4.0 * occ * (t - occ_start) / max(occ_end - occ_start, 1.0)

    # Entry / exit transients so the local event still looks like a real parking waveform.
    entry_x = 28.0 * np.exp(-0.5 * ((t - (occ_start + 2.0)) / 0.55) ** 2)
    exit_x = -36.0 * np.exp(-0.5 * ((t - (occ_end + 0.9)) / 0.55) ** 2)

    entry_y = -18.0 * np.exp(-0.5 * ((t - (occ_start - 0.8)) / 0.5) ** 2)
    exit_y = 42.0 * np.exp(-0.5 * ((t - (occ_end - 0.2)) / 0.65) ** 2)

    entry_z = 20.0 * np.exp(-0.5 * ((t - (occ_start + 1.5)) / 0.7) ** 2)
    exit_z = -24.0 * np.exp(-0.5 * ((t - (occ_end + 0.1)) / 0.75) ** 2)

    ripple = 0.9 * np.sin(2 * np.pi * t / 1.15) + 0.35 * np.sin(2 * np.pi * t / 0.43)

    x = bg_x + occ_x + entry_x + exit_x + 0.85 * ripple
    y = bg_y + occ_y + entry_y + exit_y + 0.75 * ripple
    z = bg_z + occ_z + entry_z + exit_z + 0.65 * ripple

    series = {"x": x, "y": y, "z": z}
    refs = {"x": bg_x[0], "y": bg_y[0], "z": bg_z[0]}
    return t, series, refs, (occ_start, occ_end)


def build_overview() -> tuple[np.ndarray, np.ndarray, tuple[float, float], tuple[float, float]]:
    th = np.linspace(0.0, 7.0, 1401)

    park_start = 1.15
    park_end = 5.85
    up = smooth_step(th, park_start, 0.16)
    down = smooth_step(th, park_end, 0.18)
    occ = up - down

    # Representative long-run background drift (schematic).
    bg = 590.0 - 11.5 * np.log1p(2.4 * th) - 2.4 * np.sin(2 * np.pi * th / 3.1)
    occ_shift = 13.5 * occ + 3.0 * occ * (th - park_start) / max(park_end - park_start, 1.0)
    shoulder = 2.4 * np.exp(-0.5 * ((th - 2.1) / 0.25) ** 2) - 2.0 * np.exp(-0.5 * ((th - 5.2) / 0.3) ** 2)
    ripple = 0.55 * np.sin(2 * np.pi * th / 0.18) + 0.18 * np.sin(2 * np.pi * th / 0.07)
    bz = bg + occ_shift + shoulder + ripple

    # A slightly exaggerated "local window" highlight so it is visible in the inset.
    local_window = (3.15, 3.55)
    return th, bz, (park_start, park_end), local_window


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    t, series, refs, occ_win = build_local_main()
    th, bz_overview, park_win, local_window = build_overview()

    fig, axes = plt.subplots(3, 1, figsize=(10.8, 7.7), sharex=True, constrained_layout=True)
    labels = [("x", r"$B_x$"), ("y", r"$B_y$"), ("z", r"$B_z$")]

    for ax, (key, ylabel) in zip(axes, labels):
        ax.axvspan(occ_win[0], occ_win[1], color="0.92", alpha=0.95, zorder=0)
        ax.plot(t, series[key], color="#1f77b4", linewidth=1.7, zorder=2)
        ax.axhline(refs[key], color="#d62728", linestyle="--", linewidth=1.15, alpha=0.9, zorder=1)
        ax.set_ylabel(ylabel, fontsize=14)
        ax.grid(True, alpha=0.18)
        ax.tick_params(labelsize=11)

    axes[0].annotate("进入", xy=(occ_win[0] + 0.8, series["x"][np.searchsorted(t, occ_win[0] + 0.8)]),
                     xytext=(occ_win[0] - 4.2, refs["x"] + 58),
                     arrowprops=dict(arrowstyle="->", lw=1.0, color="0.25"),
                     fontsize=10, color="0.25")
    axes[0].annotate("驶离", xy=(occ_win[1] - 0.5, series["x"][np.searchsorted(t, occ_win[1] - 0.5)]),
                     xytext=(occ_win[1] + 1.8, refs["x"] + 65),
                     arrowprops=dict(arrowstyle="->", lw=1.0, color="0.25"),
                     fontsize=10, color="0.25")

    axes[-1].set_xlabel("Time / s", fontsize=14)
    axes[0].set_title("D类慢漂移背景场景（示意）", fontsize=16, pad=8)

    axin = inset_axes(axes[0], width="30%", height="34%", loc="upper right", borderpad=1.05)
    axin.axvspan(park_win[0], park_win[1], color="0.93", alpha=1.0, zorder=0)
    axin.plot(th, bz_overview, color="#707070", linewidth=1.35, zorder=2)
    rect = Rectangle((local_window[0], np.min(bz_overview) - 1.5),
                     local_window[1] - local_window[0],
                     (np.max(bz_overview) - np.min(bz_overview)) + 3.0,
                     fill=False, linewidth=1.0, linestyle="-", edgecolor="#4c4c4c")
    axin.add_patch(rect)
    axin.set_title("7 h 长时背景总览", fontsize=8.5, pad=2)
    axin.set_xlabel("时间 / h", fontsize=7)
    axin.grid(True, alpha=0.12)
    axin.tick_params(labelsize=6.5, pad=1)
    for spine in axin.spines.values():
        spine.set_linewidth(0.85)

    preview = OUT_DIR / "ch4_wave_D_inset_schematic.png"
    img_copy = IMG_DIR / "ch4_wave_D_inset_schematic.png"
    fig.savefig(preview, dpi=220, bbox_inches="tight")
    fig.savefig(img_copy, dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved preview to: {preview}")
    print(f"Saved image copy to: {img_copy}")


if __name__ == "__main__":
    main()
