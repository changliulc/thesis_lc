import argparse
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")
plt.rcParams["font.sans-serif"] = [
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    "Arial",
]
plt.rcParams["axes.unicode_minus"] = False


def plot_baseline_cmp(csv_path: str, output_dir: str) -> None:
    df = pd.read_csv(csv_path)
    groups = ["A", "B", "C", "D"]
    methods = ["Ours", "LWC", "ADTA-FSM"]
    method_labels = {"Ours": "本文方法", "LWC": "基线一", "ADTA-FSM": "基线二"}
    colors = ["#2E86AB", "#D95F02", "#E6AB02"]

    M = np.zeros((len(groups), len(methods)))
    for gi, g in enumerate(groups):
        for mi, m in enumerate(methods):
            M[gi, mi] = float(df[(df.method == m) & (df.group == g)].F1.iloc[0])

    fig, ax = plt.subplots(figsize=(6.25, 3.75))
    ax.grid(True, axis="y", linestyle="--", alpha=0.7)
    x = np.arange(len(groups))
    w = 0.25

    for mi, m in enumerate(methods):
        ax.bar(
            x + (mi - 1) * w,
            M[:, mi],
            width=w,
            label=method_labels[m],
            color=colors[mi],
            edgecolor="black",
            linewidth=0.5,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    # Keep symmetric side margins so an in-axes legend can sit on the right
    # without occluding bars/labels.
    ax.set_xlim(-1.4, 4.4)
    ax.set_ylim(0.0, 1.12)
    ax.set_ylabel(r"$F_1$", fontsize=12)
    ax.set_xlabel("工况", fontsize=12)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(3.48, 1.11),
        bbox_transform=ax.transData,
        ncol=1,
        fontsize=10,
        frameon=True,
        framealpha=0.95,
        borderpad=0.3,
        labelspacing=0.3,
    )
    ax.set_title(r"不同方法在各工况上的 $F_1$ 对比（IoU$\geq$0.5）", fontsize=13)

    for gi in range(len(groups)):
        for mi in range(len(methods)):
            ax.text(
                gi + (mi - 1) * w,
                M[gi, mi] + 0.02,
                f"{M[gi, mi]:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    plt.tight_layout()
    out_png = os.path.join(output_dir, "ch4_baseline_cmp_f1.png")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")


def plot_c_seek_ratio(output_dir: str, r_found: float = 0.34, r_deg: float = 0.66) -> None:
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    ax.grid(True, axis="y", linestyle="--", alpha=0.7)
    vals = [r_found, r_deg]
    ax.bar(
        [0, 1],
        vals,
        color=["#2E86AB", "#2E86AB"],
        edgecolor="black",
        linewidth=0.5,
    )
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["稳定点可得率", "退化触发率"], fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("比例", fontsize=12)
    ax.set_title("C 类数据稳定点可得率与退化分支使用率统计", fontsize=13)

    for i, v in enumerate(vals):
        # Force a compact decimal label (e.g., 0.66 instead of 0. 66)
        txt = f"{float(v):.2f}".replace(". ", ".").replace(" .", ".")
        ax.text(
            i,
            v + 0.03,
            txt,
            ha="center",
            va="bottom",
            fontsize=12,
            fontfamily="DejaVu Sans",
        )

    plt.tight_layout()
    out_png = os.path.join(output_dir, "ch4_C_seek_ratio.png")
    fig.savefig(out_png, dpi=125, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_png}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--baseline_csv",
        default="绘图/第四章/0304/out_ch4_thesis/csv/E1_baseline_cmp_by_group.csv",
        help="Path to E1_baseline_cmp_by_group.csv",
    )
    ap.add_argument(
        "--output_dir",
        default="images",
        help="Output figure directory",
    )
    ap.add_argument("--r_found", type=float, default=0.34, help="C 类稳定点可得率")
    ap.add_argument("--r_deg", type=float, default=0.66, help="C 类退化触发率")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    plot_baseline_cmp(args.baseline_csv, args.output_dir)
    plot_c_seek_ratio(args.output_dir, r_found=args.r_found, r_deg=args.r_deg)
    print("Done.")


if __name__ == "__main__":
    main()
