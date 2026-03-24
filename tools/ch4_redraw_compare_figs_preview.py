from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "绘图" / "图片新修" / "第四章"


def configure_style() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
    plt.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["mathtext.rm"] = "Times New Roman"
    plt.rcParams["mathtext.it"] = "Times New Roman:italic"
    plt.rcParams["mathtext.bf"] = "Times New Roman:bold"
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"


def set_cn_font(text_obj, size: float) -> None:
    text_obj.set_fontfamily("SimSun")
    text_obj.set_fontsize(size)


def style_axis(ax: plt.Axes, tick_size: float = 12.0) -> None:
    ax.grid(axis="y", linestyle="--", linewidth=0.75, color="#d7dde7", alpha=0.68)
    ax.tick_params(axis="both", labelsize=tick_size, pad=2.5)
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontfamily("Times New Roman")
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


def draw_f1_compare() -> None:
    groups = ["A", "B", "C", "D"]
    ours = np.array([98.2, 96.5, 91.5, 98.9])
    base1 = np.array([92.3, 92.9, 82.6, 96.5])
    base2 = np.array([92.3, 91.1, 82.6, 84.3])

    matlab_blue = (0.0, 0.447, 0.741)
    matlab_orange = (0.85, 0.325, 0.098)
    matlab_yellow = (0.929, 0.694, 0.125)

    x = np.arange(len(groups))
    width = 0.28

    fig = plt.figure(figsize=(8.6, 5.1), dpi=220, facecolor="white")
    gs = fig.add_gridspec(1, 4, width_ratios=[0.04, 0.70, 0.02, 0.24], wspace=0.0)
    ax = fig.add_subplot(gs[0, 1])
    fig.add_subplot(gs[0, 0]).axis("off")
    fig.add_subplot(gs[0, 2]).axis("off")
    ax_legend = fig.add_subplot(gs[0, 3])
    ax_legend.axis("off")

    bars1 = ax.bar(x - width, ours, width, label="本文方法", color=matlab_blue)
    bars2 = ax.bar(x, base1, width, label="基线一", color=matlab_orange)
    bars3 = ax.bar(x + width, base2, width, label="基线二", color=matlab_yellow)

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    xlabel = ax.set_xlabel("工况", fontsize=13.5)
    ylabel = ax.set_ylabel(r"$F_1$ / %", fontsize=15)
    set_cn_font(xlabel, 13.5)
    ylabel.set_fontfamily("Times New Roman")
    ax.set_ylim(0, 110)
    ax.set_yticks(np.arange(0, 111, 20))
    style_axis(ax, tick_size=12.5)

    legend = ax_legend.legend(
        [bars1[0], bars2[0], bars3[0]],
        ["本文方法", "基线一", "基线二"],
        loc="upper left",
        bbox_to_anchor=(0.02, 0.92),
        frameon=True,
        fontsize=12.2,
        borderpad=0.35,
        handlelength=1.4,
        handletextpad=0.6,
        labelspacing=0.42,
    )
    legend.get_frame().set_alpha(0.94)
    legend.get_frame().set_edgecolor("#c7cdd7")
    for text in legend.get_texts():
        set_cn_font(text, 12.2)

    for bars, yoff in ((bars1, 1.5), (bars2, 1.1), (bars3, 0.8)):
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                h + yoff,
                f"{h:.1f}",
                ha="center",
                va="bottom",
                fontsize=11.5,
                fontfamily="Times New Roman",
            )

    png_path = OUT_DIR / "ch4_baseline_cmp_f1_preview.png"
    svg_path = OUT_DIR / "ch4_baseline_cmp_f1_preview.svg"
    fig.savefig(png_path, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(svg_path, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def draw_c_seek_ratio() -> None:
    labels = ["稳定点可得率", "退化触发率"]
    values = np.array([0.34, 0.66])
    colors = [(0.0, 0.447, 0.741), (0.85, 0.325, 0.098)]

    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=220, facecolor="white")
    x = np.arange(len(values))
    bars = ax.bar(x, values, width=0.62, color=colors, edgecolor="#3a3a3a", linewidth=0.45)

    ax.set_ylim(0.0, 1.02)
    ax.set_yticks(np.arange(0.0, 1.01, 0.2))
    ylabel = ax.set_ylabel("比例", fontsize=15)
    set_cn_font(ylabel, 15)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    style_axis(ax, tick_size=12.5)
    for tick in ax.get_xticklabels():
        set_cn_font(tick, 13.2)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=13.5,
            fontfamily="Times New Roman",
        )

    png_path = OUT_DIR / "ch4_C_seek_ratio_preview.png"
    svg_path = OUT_DIR / "ch4_C_seek_ratio_preview.svg"
    fig.savefig(png_path, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(svg_path, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def main() -> None:
    configure_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    draw_f1_compare()
    draw_c_seek_ratio()


if __name__ == "__main__":
    main()
