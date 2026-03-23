from pathlib import Path
import json
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "绘图" / "第四章" / "0304" / "ch4_param_scan_out" / "csv" / "ch4_tseek_scan.csv"
SUMMARY_PATH = ROOT / "绘图" / "第四章" / "0304" / "ch4_param_scan_out" / "summary.json"
OUT_PATH = ROOT / "images" / "ch4_param_scan_tseek.png"


def configure_style() -> None:
    plt.rcParams["font.family"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK JP",
        "PingFang SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def main() -> None:
    configure_style()
    df = pd.read_csv(CSV_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    tuned_value = float(summary["selected_value"])

    matlab_blue = (0.0, 0.447, 0.741)
    matlab_orange = (0.85, 0.325, 0.098)
    matlab_yellow = (0.929, 0.694, 0.125)

    fig = plt.figure(figsize=(14.0, 5.25), facecolor="white")
    gs = fig.add_gridspec(1, 4, width_ratios=[3.40, 5.35, 1.20, 2.15], wspace=0.0)
    ax_pad = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax_gap = fig.add_subplot(gs[0, 2])
    ax_leg = fig.add_subplot(gs[0, 3])
    ax_pad.axis("off")
    ax_gap.axis("off")
    ax_leg.axis("off")

    x = df["T_seek_sec"].to_numpy(dtype=float)

    ax1.plot(
        x,
        df["F1_ALL"],
        color=matlab_blue,
        marker="o",
        markersize=4.4,
        linewidth=1.4,
        label="全体样本 $F_1$",
    )
    ax1.plot(
        x,
        df["F1_C"],
        color=matlab_orange,
        marker="s",
        markersize=4.4,
        linewidth=1.4,
        label="C类工况 $F_1$",
    )
    ax1.axvline(
        tuned_value,
        color=matlab_blue,
        linestyle="--",
        linewidth=1.0,
        label="选定值",
    )

    ax1.set_ylim(0.0, 1.0)
    ax1.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax1.set_xlabel(r"$T_{seek}$ / s", fontsize=18)
    ax1.set_ylabel(r"$F_1$", fontsize=20)
    ax1.tick_params(axis="both", labelsize=17)
    ax1.grid(True, linestyle="--", linewidth=0.8, alpha=0.30)

    ax2 = ax1.twinx()
    ax2.plot(
        x,
        df["tau_in_C_median"],
        color=matlab_yellow,
        marker="^",
        markersize=4.6,
        linewidth=1.2,
        linestyle=":",
        label="C类确认时差中位数",
    )
    ax2.set_ylabel("")
    ax2.tick_params(axis="y", labelsize=17)

    ax_gap.text(
        0.68,
        0.50,
        "确认时差 / s",
        rotation=90,
        va="center",
        ha="center",
        fontsize=18,
    )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    legend = ax_leg.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        bbox_to_anchor=(-0.12, 0.95),
        fontsize=15,
        frameon=True,
        borderpad=0.42,
        handlelength=1.6,
        handletextpad=0.50,
        labelspacing=0.28,
    )
    legend.get_frame().set_alpha(0.92)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.02, right=0.985, bottom=0.17, top=0.97)
    fig.savefig(OUT_PATH, dpi=240, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
