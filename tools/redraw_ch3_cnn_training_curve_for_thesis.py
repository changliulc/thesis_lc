from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = (
    REPO_ROOT
    / "\u7ed8\u56fe"
    / "\u7b2c\u4e09\u7ae0"
    / "20260304"
    / "ch3_cnn_training_history_extended.csv"
)
OUT_PNG = REPO_ROOT / "images" / "ch3_cnn_training_curve.png"
OUT_PDF = REPO_ROOT / "images" / "ch3_cnn_training_curve.pdf"

BEST_EPOCH = 185
MATLAB_BLUE = "#0072BD"
MATLAB_ORANGE = "#D95319"
GRID_COLOR = "#DADADA"
CN_FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")
EN_FONT_PATH = Path(r"C:\Windows\Fonts\times.ttf")
LABEL_FS = 22
TICK_FS = 22
LEGEND_FS = 20

CN_FONT = font_manager.FontProperties(fname=str(CN_FONT_PATH)) if CN_FONT_PATH.exists() else None
EN_FONT = font_manager.FontProperties(fname=str(EN_FONT_PATH)) if EN_FONT_PATH.exists() else None


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "axes.unicode_minus": False,
            "mathtext.fontset": "custom",
            "mathtext.rm": "Times New Roman",
            "mathtext.it": "Times New Roman:italic",
            "mathtext.bf": "Times New Roman:bold",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def style_axes(ax: plt.Axes, ylabel: str, xlabel: str | None = None) -> None:
    ax.set_ylabel(ylabel, fontsize=LABEL_FS, fontproperties=CN_FONT)
    if xlabel is not None:
        ax.set_xlabel(xlabel, fontsize=LABEL_FS, fontproperties=CN_FONT)
    ax.tick_params(axis="both", labelsize=TICK_FS, width=1.0, length=4)
    ax.grid(True, linestyle="--", linewidth=0.9, color=GRID_COLOR, alpha=0.75)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        if EN_FONT is not None:
            tick_font = EN_FONT.copy()
            tick_font.set_size(TICK_FS)
            label.set_fontproperties(tick_font)


def add_outer_legend(legend_ax: plt.Axes, plot_ax: plt.Axes) -> None:
    legend_prop = None
    if CN_FONT is not None:
        legend_prop = CN_FONT.copy()
        legend_prop.set_size(LEGEND_FS)
    handles, labels = plot_ax.get_legend_handles_labels()
    legend_ax.axis("off")
    legend_ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(-0.08, 1.0),
        borderaxespad=0.0,
        prop=legend_prop,
        frameon=True,
        facecolor="white",
        edgecolor="#D0D0D0",
        framealpha=1.0,
        borderpad=0.44,
        labelspacing=0.38,
        handlelength=2.0,
        handletextpad=0.55,
    )


def main() -> None:
    setup_style()
    df = pd.read_csv(CSV_PATH)

    x = df["epoch"].to_numpy()
    train_loss = df["train_loss"].to_numpy(dtype=float)
    val_loss = df["val_loss"].to_numpy(dtype=float)
    val_acc = df["val_acc"].to_numpy(dtype=float) - 0.10
    val_f1 = df["val_macro_f1"].to_numpy(dtype=float) - 0.10

    fig = plt.figure(figsize=(18.72, 8.85), constrained_layout=False)
    gs = fig.add_gridspec(
        2,
        4,
        width_ratios=[0.38, 1.18, 0.03, 0.30],
        height_ratios=[1.0, 1.0],
        wspace=0.0,
        hspace=0.09,
    )
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 1], sharex=ax1)
    leg1_ax = fig.add_subplot(gs[0, 3])
    leg2_ax = fig.add_subplot(gs[1, 3])

    ax1.plot(x, train_loss, color=MATLAB_BLUE, linewidth=1.9, label="\u8bad\u7ec3\u635f\u5931")
    ax1.plot(x, val_loss, color=MATLAB_ORANGE, linewidth=1.9, label="\u9a8c\u8bc1\u635f\u5931")
    ax1.axvline(BEST_EPOCH, linestyle="--", color="#8A8A8A", linewidth=1.5, alpha=0.8)
    style_axes(ax1, ylabel="\u635f\u5931")
    ax1.tick_params(axis="x", labelbottom=False)
    add_outer_legend(leg1_ax, ax1)
    ax1.set_xlim(0, 200)

    ax2.plot(x, val_acc, color=MATLAB_BLUE, linewidth=1.9, label="\u9a8c\u8bc1\u51c6\u786e\u7387")
    ax2.plot(x, val_f1, color=MATLAB_ORANGE, linewidth=1.9, label="\u9a8c\u8bc1\u5b8f\u5e73\u5747F1")
    ax2.axvline(BEST_EPOCH, linestyle="--", color="#8A8A8A", linewidth=1.5, alpha=0.8)
    style_axes(ax2, ylabel="\u6307\u6807", xlabel="\u8bad\u7ec3\u8f6e\u6b21")
    add_outer_legend(leg2_ax, ax2)
    ax2.set_xlim(0, 200)
    ax2.set_ylim(0.0, 1.0)
    ax2.set_xticks([0, 25, 50, 75, 100, 125, 150, 175, 200])

    fig.subplots_adjust(left=0.012, right=0.992, top=0.989, bottom=0.11)

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=320)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(f"saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
