from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_path = root / "images" / "ch4_baseline_cmp_f1.png"

    groups = ["A", "B", "C", "D"]
    ours = np.array([98.2, 96.5, 91.5, 98.9])
    base1 = np.array([92.3, 92.9, 82.6, 96.5])
    base2 = np.array([92.3, 91.1, 82.6, 84.3])

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 12

    x = np.arange(len(groups))
    width = 0.28

    fig, ax = plt.subplots(figsize=(7.8, 4.8), dpi=180)
    colors = [
        (0.0000, 0.4470, 0.7410),
        (0.8500, 0.3250, 0.0980),
        (0.9290, 0.6940, 0.1250),
    ]

    bars1 = ax.bar(x - width, ours, width, label="本文方法", color=colors[0])
    bars2 = ax.bar(x, base1, width, label="基线一", color=colors[1])
    bars3 = ax.bar(x + width, base2, width, label="基线二", color=colors[2])

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_xlabel("工况", fontsize=13)
    ax.set_ylabel("F1 / %", fontsize=16)
    ax.set_ylim(0, 112)
    ax.grid(axis="y", linestyle=":", linewidth=0.8, alpha=0.35)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 0.98),
        ncol=1,
        frameon=False,
        fontsize=13,
        borderaxespad=0.0,
        handlelength=1.5,
    )
    ax.tick_params(axis="both", labelsize=14)
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

    for bars, yoff, xshift, fsize in (
        (bars1, 1.8, -0.015, 12),
        (bars2, 1.2, 0.000, 12),
        (bars3, 0.8, 0.015, 12),
    ):
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2 + xshift,
                h + yoff,
                f"{h:.1f}",
                ha="center",
                va="bottom",
                fontsize=fsize,
            )

    fig.tight_layout(pad=0.8)
    fig.subplots_adjust(right=0.82)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
