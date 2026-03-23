from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    values = [0.34, 0.66]
    labels = ["\u7a33\u5b9a\u70b9\u53ef\u5f97\u7387", "\u9000\u5316\u89e6\u53d1\u7387"]

    matlab_blue = (0.0000, 0.4470, 0.7410)

    fig, ax = plt.subplots(figsize=(6.2, 4.4), facecolor="white")
    x = np.arange(len(values))
    bars = ax.bar(
        x,
        values,
        width=0.62,
        color=[matlab_blue, matlab_blue],
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_ylim(0.0, 1.10)
    ax.set_ylabel("\u6bd4\u4f8b", fontsize=18)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=17)
    ax.tick_params(axis="y", labelsize=16)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8, alpha=0.45)

    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 0.03,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=18,
        )

    fig.tight_layout()

    out_path = Path("images/ch4_C_seek_ratio.png")
    fig.savefig(out_path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(out_path)


if __name__ == "__main__":
    main()
