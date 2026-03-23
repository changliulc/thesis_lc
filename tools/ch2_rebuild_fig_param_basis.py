#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "绘图" / "图片新修" / "第二章" / "fig_param_basis_rebuild"
TEXT_FONT_FAMILIES = ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"]


def configure_fonts() -> None:
    plt.rcParams["font.family"] = TEXT_FONT_FAMILIES
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"


def mixed_font(size: float | None = None) -> fm.FontProperties:
    props = fm.FontProperties(family=TEXT_FONT_FAMILIES)
    if size is not None:
        props.set_size(size)
    return props


def build_piecewise_quantile_samples(
    probs: np.ndarray,
    values: np.ndarray,
    n: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    u = np.sort(rng.uniform(0.0, 1.0, size=n))
    return np.interp(u, probs, values)


def synthetic_panel_a_data() -> tuple[np.ndarray, np.ndarray]:
    # Construct empirical samples that match the annotated quantiles in the thesis figure.
    no_car = build_piecewise_quantile_samples(
        probs=np.array([0.0, 0.80, 0.95, 0.99, 0.999, 1.0]),
        values=np.array([0.0, 0.01, 0.18, 0.939, 0.996, 1.0]),
        n=24000,
        seed=20260208,
    )
    car = build_piecewise_quantile_samples(
        probs=np.array([0.0, 0.01, 0.05, 0.20, 0.60, 0.95, 1.0]),
        values=np.array([0.0, 0.052, 0.442, 0.92, 0.985, 0.999, 1.0]),
        n=18000,
        seed=20260209,
    )
    return no_car, car


def synthetic_panel_b_data() -> np.ndarray:
    counts = {
        1: 28,
        2: 17,
        3: 17,
        4: 9,
        5: 15,
        6: 9,
        7: 5,
        8: 7,
        9: 7,
    }
    return np.concatenate([np.full(c, k, dtype=int) for k, c in counts.items()])


def synthetic_panel_c_data() -> np.ndarray:
    return np.array([1, 1, 1, 2, 11], dtype=int)


def panel_a(ax: plt.Axes) -> None:
    no_car, car = synthetic_panel_a_data()
    bins = np.linspace(0.0, 1.0, 41)
    ax.hist(
        no_car,
        bins=bins,
        density=True,
        alpha=0.62,
        color="#5DA5DA",
        edgecolor="#2B5876",
        linewidth=0.85,
        label="无车段",
    )
    ax.hist(
        car,
        bins=bins,
        density=True,
        alpha=0.78,
        color="#E6956B",
        edgecolor="#8A4F2A",
        linewidth=0.85,
        label="有车段",
    )
    ax.axvline(0.50, color="#8F8F8F", linestyle="--", linewidth=0.9, dashes=(5, 4))
    ax.axvline(0.90, color="#8F8F8F", linestyle="--", linewidth=0.9, dashes=(5, 4))
    ax.text(
        0.515,
        0.55,
        r"$\theta_{\mathrm{lea}}$",
        rotation=90,
        fontsize=11.5,
        color="#444444",
        ha="left",
        va="bottom",
    )
    ax.text(
        0.915,
        0.55,
        r"$\theta_{\mathrm{arr}}$",
        rotation=90,
        fontsize=11.5,
        color="#444444",
        ha="left",
        va="bottom",
    )
    ax.text(
        0.02,
        0.98,
        "无车:  P99.9=0.996, P99=0.939\n有车:  P1=0.052, P5=0.442",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11.5,
        fontproperties=mixed_font(11.5),
    )
    ax.set_title("(a) P_car(k) 分布对比", fontsize=16, pad=12, fontproperties=mixed_font(16))
    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(0.0, 35.0)
    ax.set_xlabel("P_car", fontsize=15, fontproperties=mixed_font(15))
    ax.set_ylabel("概率密度", fontsize=15, fontproperties=mixed_font(15))
    ax.tick_params(labelsize=13.5, length=5.5, width=1.0, top=True, right=True)
    ax.grid(True, color="#B0B0B0", alpha=0.35, linewidth=0.8)
    leg = ax.legend(
        loc="upper right",
        fontsize=12.5,
        prop=mixed_font(12.5),
        frameon=True,
        framealpha=0.96,
        fancybox=False,
        borderpad=0.45,
        handlelength=1.7,
        handletextpad=0.4,
    )
    leg.get_frame().set_edgecolor("#444444")


def panel_b(ax: plt.Axes) -> None:
    data = synthetic_panel_b_data()
    bins = np.arange(0.5, 10.5, 1.0)
    ax.hist(
        data,
        bins=bins,
        color="#2E86C1",
        edgecolor="#1B4F72",
        linewidth=0.85,
        alpha=0.98,
    )
    ax.axvline(10.0, color="#8F8F8F", linestyle="--", linewidth=0.9, dashes=(5, 4))
    ax.text(
        10.08,
        0.4,
        "N_arr=10",
        rotation=90,
        fontsize=11.5,
        color="#444444",
        ha="left",
        va="bottom",
    )
    ax.text(
        0.02,
        0.98,
        "max=9, P95=9.0, P99=9.0",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11.5,
        fontproperties=mixed_font(11.5),
    )
    ax.set_title("(b) 无车连续触发长度统计", fontsize=16, pad=12, fontproperties=mixed_font(16))
    ax.set_xlim(0.0, 10.9)
    ax.set_ylim(0.0, 30.0)
    ax.set_xlabel("连续点数", fontsize=15, fontproperties=mixed_font(15))
    ax.set_ylabel("次数", fontsize=15, fontproperties=mixed_font(15))
    ax.tick_params(labelsize=13.5, length=5.5, width=1.0, top=True, right=True)
    ax.grid(True, color="#B0B0B0", alpha=0.35, linewidth=0.8)


def panel_c(ax: plt.Axes) -> None:
    data = synthetic_panel_c_data()
    bins = np.arange(0.5, 12.5, 1.0)
    ax.hist(
        data,
        bins=bins,
        color="#2E86C1",
        edgecolor="#1B4F72",
        linewidth=0.85,
        alpha=0.98,
    )
    ax.axvline(8.0, color="#8F8F8F", linestyle="--", linewidth=0.9, dashes=(5, 4))
    ax.text(
        8.08,
        0.08,
        "T_d=8",
        rotation=90,
        fontsize=11.5,
        color="#444444",
        ha="left",
        va="bottom",
    )
    ax.text(
        0.02,
        0.98,
        "n=5, 覆盖率(<=T_d)=80.0%\nmax=11, P95=11.0, P99=11.0",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11.5,
        fontproperties=mixed_font(11.5),
    )
    ax.set_title(
        "(c) 到达确认后短时间回落长度统计",
        fontsize=16,
        pad=12,
        fontproperties=mixed_font(16),
    )
    ax.set_xlim(0.0, 13.0)
    ax.set_ylim(0.0, 3.0)
    ax.set_xlabel("连续点数", fontsize=15, fontproperties=mixed_font(15))
    ax.set_ylabel("次数", fontsize=15, fontproperties=mixed_font(15))
    ax.tick_params(labelsize=13.5, length=5.5, width=1.0, top=True, right=True)
    ax.grid(True, color="#B0B0B0", alpha=0.35, linewidth=0.8)


def build_preview(out_dir: Path, dpi: int) -> dict[str, Path]:
    configure_fonts()
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15.8, 7.1), dpi=dpi, constrained_layout=True)
    panel_a(axes[0])
    panel_b(axes[1])
    panel_c(axes[2])

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)

    png_path = out_dir / "fig_param_basis_preview.png"
    svg_path = out_dir / "fig_param_basis_preview.svg"
    meta_path = out_dir / "fig_param_basis_preview_meta.json"

    fig.savefig(png_path, dpi=dpi, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    meta = {
        "type": "semantic_rebuild_preview_only",
        "notes": [
            "Original plotting code for Fig. 2.6 was not found in the current thesis workspace.",
            "This preview was rebuilt from the visible chart structure and the parameter-selection text in Chapter 2.",
            "The current thesis image images/fig_param_basis.png was not overwritten.",
        ],
        "panel_a_target_stats": {
            "no_car": {"P99.9": 0.996, "P99": 0.939},
            "car": {"P1": 0.052, "P5": 0.442},
        },
        "panel_b_target_stats": {"max": 9, "P95": 9.0, "P99": 9.0, "N_arr": 10},
        "panel_c_target_stats": {
            "n": 5,
            "coverage_le_Td": 0.80,
            "max": 11,
            "P95": 11.0,
            "P99": 11.0,
            "T_d": 8,
        },
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"png": png_path, "svg": svg_path, "meta": meta_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild Fig. 2.6 preview from semantic cues.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dpi", type=int, default=220)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = build_preview(args.out_dir, args.dpi)
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
