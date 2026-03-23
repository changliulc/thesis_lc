from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import ScalarFormatter


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "tmp" / "ch4_d_discussion_pkg_20260319_235420" / "data" / "fig_d_win_new.csv"
IMG_OUT = ROOT / "images" / "ch4_wave_d_python_matlab.png"
PREVIEW_OUT = ROOT / "tmp" / "ch4_wave_refresh" / "ch4_wave_d_python_matlab.png"


plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["mathtext.fontset"] = "stix"


SIG_COLOR = (0.0, 0.4470, 0.7410)
BASE_COLOR = (0.8500, 0.3250, 0.0980)
DRIFT_COLOR = (0.55, 0.55, 0.55)


def add_break_marks(ax_left, ax_right, size: float = 0.014) -> None:
    kwargs_l = dict(transform=ax_left.transAxes, color="0.35", clip_on=False, linewidth=1.0)
    ax_left.plot((1 - size, 1 + size), (-size, +size), **kwargs_l)
    ax_left.plot((1 - size, 1 + size), (1 - size, 1 + size), **kwargs_l)
    kwargs_r = dict(transform=ax_right.transAxes, color="0.35", clip_on=False, linewidth=1.0)
    ax_right.plot((-size, +size), (-size, +size), **kwargs_r)
    ax_right.plot((-size, +size), (1 - size, 1 + size), **kwargs_r)


def matlab_power_formatter() -> ScalarFormatter:
    fmt = ScalarFormatter(useMathText=True)
    fmt.set_powerlimits((4, 4))
    return fmt


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    t = df["t"].to_numpy(float)
    y = df["x"].to_numpy(float)

    left_mask = t <= 0.62
    mid_mask = (t >= 1.00) & (t <= 3.00)
    right_mask = t >= 6.45

    y_left = y[left_mask]
    y_mid = y[mid_mask]
    y_right = y[right_mask]

    x_left = np.linspace(0, 700, len(y_left))
    x_mid = np.linspace(200000, 500000, len(y_mid))
    x_right = np.linspace(1260350, 1261000, len(y_right))

    baseline = float(np.median(y[:40]))
    drift_ref = float(np.median(y_right[-25:]))

    y_all = np.concatenate([y_left, y_mid, y_right, np.array([baseline, drift_ref])])
    y_pad = 0.07 * float(np.max(y_all) - np.min(y_all))
    y_min = float(np.min(y_all) - y_pad)
    y_max = float(np.max(y_all) + y_pad)
    y_ticks = np.arange(50 * np.floor(y_min / 50), 50 * np.ceil(y_max / 50) + 1, 50)

    fig = plt.figure(figsize=(8.6, 4.5), dpi=220)
    gs = fig.add_gridspec(1, 3, width_ratios=[2.2, 1.15, 2.2], wspace=0.16)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])

    axes = [ax1, ax2, ax3]
    for i, ax in enumerate(axes):
        ax.grid(True, alpha=0.18, linewidth=0.8)
        ax.tick_params(labelsize=12, length=3.5, width=0.8)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
            spine.set_color("0.35")
        ax.set_ylim(y_ticks[0], y_ticks[-1])
        ax.set_yticks(y_ticks)
        ax.axhline(baseline, color=BASE_COLOR, linestyle="--", linewidth=1.0, alpha=0.55)
        if i == 2:
            ax.axhline(drift_ref, color=DRIFT_COLOR, linestyle="--", linewidth=1.0, alpha=0.8)
        if i > 0:
            ax.tick_params(axis="y", labelleft=False)

    ax1.plot(x_left, y_left, color=SIG_COLOR, linewidth=1.7)
    ax1.set_xlim(0, 700)
    ax1.set_xticks([0, 200, 400, 600])
    ax1.set_xlabel("点数", fontsize=15)
    ax1.set_ylabel(r"$B_x$", fontsize=17)
    ax1.set_title("进入局部", fontsize=15, pad=4)

    ax2.plot(x_mid, y_mid, color=SIG_COLOR, linewidth=1.7)
    ax2.set_xlim(200000, 500000)
    ax2.set_xticks([200000, 300000, 400000, 500000])
    ax2.xaxis.set_major_formatter(matlab_power_formatter())
    ax2.set_xlabel("点数", fontsize=15)
    ax2.set_title("占用中段漂移", fontsize=15, pad=4)
    ax2.text(
        350000,
        np.percentile(y_mid, 60),
        "停车占用波形\n缓慢漂移",
        ha="center",
        va="center",
        fontsize=14,
        color="0.35",
    )

    ax3.plot(x_right, y_right, color=SIG_COLOR, linewidth=1.7)
    ax3.set_xlim(1260350, 1261000)
    ax3.set_xticks([1260400, 1260600, 1260800, 1261000])
    ax3.xaxis.set_major_formatter(matlab_power_formatter())
    ax3.set_xlabel("点数", fontsize=15)
    ax3.set_title("驶离局部", fontsize=15, pad=4)

    add_break_marks(ax1, ax2)
    add_break_marks(ax2, ax3)
    ax1.text(1.02, 0.50, "...", transform=ax1.transAxes, fontsize=18, color="0.40", va="center")
    ax2.text(1.02, 0.50, "...", transform=ax2.transAxes, fontsize=18, color="0.40", va="center")

    x0 = ax1.get_position().x0
    x1 = ax3.get_position().x1
    y_top = max(ax.get_position().y1 for ax in axes)
    fig.text((x0 + x1) / 2, y_top + 0.04, "D类慢漂移背景场景", ha="center", va="bottom", fontsize=18)

    PREVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
    IMG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PREVIEW_OUT, dpi=220, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(IMG_OUT, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print(f"saved -> {PREVIEW_OUT}")
    print(f"saved -> {IMG_OUT}")


if __name__ == "__main__":
    main()
