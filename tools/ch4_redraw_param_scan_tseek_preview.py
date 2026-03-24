from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "绘图" / "第四章" / "0304" / "ch4_param_scan_out" / "csv" / "ch4_tseek_scan.csv"
SUMMARY_PATH = ROOT / "绘图" / "第四章" / "0304" / "ch4_param_scan_out" / "summary.json"
OUT_DIR = ROOT / "绘图" / "图片新修" / "第四章"
PNG_PATH = OUT_DIR / "ch4_param_scan_tseek_preview.png"
SVG_PATH = OUT_DIR / "ch4_param_scan_tseek_preview.svg"


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
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def set_cn_font(text_obj, size: float) -> None:
    text_obj.set_fontfamily("SimSun")
    text_obj.set_fontsize(size)


def crop_vertical_whitespace(path: Path, pad_px: int = 4) -> None:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    bg = (255, 255, 255)

    rows_with_content: list[int] = []
    for y in range(height):
        row = [image.getpixel((x, y)) for x in range(width)]
        if any(px != bg for px in row):
            rows_with_content.append(y)

    if not rows_with_content:
        return

    top = max(0, rows_with_content[0] - pad_px)
    bottom = min(height, rows_with_content[-1] + pad_px + 1)
    image.crop((0, top, width, bottom)).save(path)


def build_figure() -> plt.Figure:
    configure_style()
    df = pd.read_csv(CSV_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    tuned_value = float(summary["selected_value"])

    matlab_blue = (0.0, 0.447, 0.741)
    matlab_orange = (0.85, 0.325, 0.098)
    matlab_yellow = (0.929, 0.694, 0.125)
    grid_color = "#d9dee7"

    fig = plt.figure(figsize=(11.0, 4.9), facecolor="white")
    gs = fig.add_gridspec(
        1,
        4,
        width_ratios=[0.22, 0.54, 0.04, 0.20],
        left=0.02,
        right=0.98,
        bottom=0.10,
        top=0.97,
        wspace=0.0,
    )
    ax_left = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax_gap = fig.add_subplot(gs[0, 2])
    ax_legend = fig.add_subplot(gs[0, 3])
    ax_left.axis("off")
    ax_gap.axis("off")
    ax_legend.axis("off")
    x = df["T_seek_sec"].to_numpy(dtype=float)

    line_all, = ax1.plot(
        x,
        df["F1_ALL"],
        color=matlab_blue,
        marker="o",
        markersize=5.2,
        linewidth=1.7,
        markeredgewidth=0.55,
        label=r"全体样本 $F_1$",
        zorder=3,
    )
    line_c, = ax1.plot(
        x,
        df["F1_C"],
        color=matlab_orange,
        marker="s",
        markersize=5.0,
        linewidth=1.7,
        markeredgewidth=0.55,
        label=r"C类工况 $F_1$",
        zorder=3,
    )
    line_sel = ax1.axvline(
        tuned_value,
        color=matlab_blue,
        linestyle="--",
        linewidth=1.15,
        alpha=0.95,
        label="选定值",
        zorder=2,
    )

    ax1.set_xlim(float(x.min()) - 0.15, float(x.max()) + 0.15)
    ax1.set_ylim(0.0, 1.0)
    ax1.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax1.set_xticks(x)
    ax1.grid(True, linestyle="--", linewidth=0.8, color=grid_color, alpha=0.72)
    ax1.set_axisbelow(True)
    ax1.tick_params(axis="both", labelsize=12, pad=2)

    xlabel = ax1.set_xlabel(r"$T_{seek}$ / $s$", fontsize=15, labelpad=1)
    ylabel = ax1.set_ylabel(r"$F_1$", fontsize=16)
    xlabel.set_fontfamily("Times New Roman")
    ylabel.set_fontfamily("Times New Roman")

    ax2 = ax1.twinx()
    line_tau, = ax2.plot(
        x,
        df["tau_in_C_median"],
        color=matlab_yellow,
        marker="^",
        markersize=5.2,
        linewidth=1.55,
        linestyle=":",
        markeredgewidth=0.5,
        label="C类确认时差中位数",
        zorder=3,
    )
    ax2.set_ylim(0.65, 2.28)
    ax2.tick_params(axis="y", labelsize=12, pad=2)
    ylabel_r = ax2.set_ylabel("确认时差 / $s$", fontsize=15, labelpad=0)
    set_cn_font(ylabel_r, 15)
    ax2.yaxis.set_label_coords(1.05, 0.5)

    for tick in ax1.get_xticklabels() + ax1.get_yticklabels() + ax2.get_yticklabels():
        tick.set_fontfamily("Times New Roman")

    legend = ax_legend.legend(
        [line_all, line_c, line_sel, line_tau],
        [r"全体样本 $F_1$", r"C类工况 $F_1$", "选定值", "C类确认时差中位数"],
        loc="upper left",
        bbox_to_anchor=(-0.08, 0.96),
        frameon=True,
        fontsize=11.5,
        borderpad=0.4,
        handlelength=1.9,
        handletextpad=0.55,
        labelspacing=0.42,
    )
    legend.get_frame().set_alpha(0.95)
    legend.get_frame().set_edgecolor("#c7cdd7")
    for text in legend.get_texts():
        set_cn_font(text, 11.5)

    return fig


def main() -> None:
    fig = build_figure()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_PATH, dpi=320, facecolor="white")
    fig.savefig(SVG_PATH, facecolor="white")
    plt.close(fig)
    crop_vertical_whitespace(PNG_PATH)


if __name__ == "__main__":
    main()
