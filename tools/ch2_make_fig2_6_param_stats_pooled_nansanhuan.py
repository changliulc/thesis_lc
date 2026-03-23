#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = REPO_ROOT / "tools" / "ch2_make_fig2_6_param_stats_from_excel.py"
OUT_DIR = REPO_ROOT / "绘图" / "图片新修" / "第二章" / "fig_param_basis_from_pooled_nansanhuan"

INPUT_FILES = [
    Path(r"G:\地磁组路段数据\路段统计\20240506南三环\20240506南三环.xlsx"),
    Path(r"G:\地磁组路段数据\路段统计\0511南三环\2024.5.11南三环数据采集.xlsx"),
    Path(r"G:\地磁组路段数据\路段统计\20240522南三环\2024.5.22南三环数据采集.xlsx"),
    Path(r"G:\地磁组路段数据\路段统计\20240528南三环\2024.5.28中型车大型车数据采集.xlsx"),
]

THRESHOLD_PNG = "fig_param_basis_threshold_preview.png"
THRESHOLD_SVG = "fig_param_basis_threshold_preview.svg"
COUNTS_PNG = "fig_param_basis_counts_preview.png"
COUNTS_SVG = "fig_param_basis_counts_preview.svg"
META_JSON = "fig_param_basis_split_preview_meta.json"


def load_base_module():
    spec = importlib.util.spec_from_file_location("fig26_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载基础脚本: {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze_one(base, path: Path) -> dict[str, object]:
    base.FILE = path
    b = base.read_b()
    dbar = base.compute_dbar(b)
    pcar = base.compute_pcar(dbar)
    events = base.detect_events(pcar)
    car_mask, env_mask, false_lens, drop_lens = base.compute_statistics(pcar, events)
    return {
        "file": str(path),
        "rows": int(b.shape[0]),
        "event_count": int(events.shape[0]),
        "p_env": pcar[env_mask],
        "p_veh": pcar[car_mask],
        "false_lens": false_lens.astype(np.int64, copy=False),
        "drop_lens": drop_lens.astype(np.int64, copy=False),
    }


def configure_style(base) -> None:
    base.configure_matplotlib()
    base.FS_AX = 22.0
    base.FS_TXT = 17.2
    base.FS_LEG = 19.2
    base.FS_SUB = 19.4
    plt.rcParams["font.size"] = 20


def collect_pooled_statistics(base) -> dict[str, object]:
    analyses = [analyze_one(base, path) for path in INPUT_FILES]
    return {
        "analyses": analyses,
        "p_env": np.concatenate([item["p_env"] for item in analyses], axis=0),
        "p_veh": np.concatenate([item["p_veh"] for item in analyses], axis=0),
        "false_lens": np.concatenate([item["false_lens"] for item in analyses], axis=0),
        "drop_lens": np.concatenate([item["drop_lens"] for item in analyses], axis=0),
        "total_rows": int(sum(int(item["rows"]) for item in analyses)),
        "total_events": int(sum(int(item["event_count"]) for item in analyses)),
    }


def add_panel_label_below(base, ax: plt.Axes, text: str, y: float = -0.205) -> None:
    ax.text(
        0.5,
        y,
        text,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=base.FS_SUB,
        fontproperties=base.mixed_font(base.FS_SUB),
    )


def add_line_label(base, ax: plt.Axes, x_value: float, text: str, y_axes: float = 0.92) -> None:
    ax.annotate(
        text,
        xy=(x_value, y_axes),
        xycoords=("data", "axes fraction"),
        xytext=(6, 0),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=base.FS_TXT + 0.8,
        color="#444444",
        fontproperties=base.mixed_font(base.FS_TXT + 0.8),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.80, boxstyle="square,pad=0.10"),
        clip_on=False,
    )


def plot_threshold_panel(base, ax: plt.Axes, p_env: np.ndarray, p_veh: np.ndarray) -> dict[str, float]:
    q_env = base.percentile(p_env, [95.0, 99.0, 99.9])
    q_veh = base.percentile(p_veh, [1.0, 5.0, 10.0])

    edges = np.linspace(0.0, 1.0, 41)
    _, _, env_patches = ax.hist(
        p_env,
        bins=edges,
        density=True,
        alpha=0.55,
        color=base.COLOR_ENV,
        edgecolor="#3E7093",
        linewidth=1.0,
        label="无车段",
    )
    _, _, car_patches = ax.hist(
        p_veh,
        bins=edges,
        density=True,
        alpha=0.55,
        color=base.COLOR_CAR,
        edgecolor="#8F5A3B",
        linewidth=1.0,
        label="有车段",
    )

    y_top = ax.get_ylim()[1]
    ax.set_ylim(0.0, y_top * 1.10)
    ax.axvline(base.THETA_LEA, color=base.COLOR_THRESH, linestyle="--", linewidth=1.3, dashes=(5, 4))
    ax.axvline(base.THETA_ARR, color=base.COLOR_THRESH, linestyle="--", linewidth=1.3, dashes=(5, 4))
    add_line_label(base, ax, base.THETA_LEA, r"$\theta_{lea}$", y_axes=0.87)
    add_line_label(base, ax, base.THETA_ARR, r"$\theta_{arr}$", y_axes=0.87)

    ax.set_xlabel("Pcar", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_ylabel("概率密度", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.legend(
        handles=[env_patches[0], car_patches[0]],
        labels=["无车段", "有车段"],
        loc="upper right",
        fontsize=base.FS_LEG,
        prop=base.mixed_font(base.FS_LEG),
        frameon=True,
        framealpha=0.95,
        fancybox=False,
        borderpad=0.35,
        handlelength=1.8,
        handletextpad=0.45,
    )
    txt = f"无车: P99.9={q_env[2]:.3f}, P99={q_env[1]:.3f}\n有车: P1={q_veh[0]:.3f}, P5={q_veh[1]:.3f}"
    ax.text(
        0.02,
        0.95,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=base.FS_TXT,
        fontproperties=base.mixed_font(base.FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.24"),
    )

    base.add_common_axis_style(ax)
    return {
        "p_env_p99_9": float(q_env[2]),
        "p_env_p99": float(q_env[1]),
        "p_veh_p1": float(q_veh[0]),
        "p_veh_p5": float(q_veh[1]),
    }


def plot_narr_panel(base, ax: plt.Axes, false_lens: np.ndarray) -> dict[str, float]:
    edges = np.arange(0.5, float(false_lens.max()) + 1.6, 1.0)
    ax.hist(
        false_lens,
        bins=edges,
        color=base.COLOR_BAR,
        edgecolor="#1F587F",
        linewidth=1.0,
        alpha=0.96,
        rwidth=0.80,
    )
    y_top = ax.get_ylim()[1]
    ax.set_ylim(0.0, y_top * 1.14)
    ax.axvline(base.NARR, color=base.COLOR_THRESH, linestyle="--", linewidth=1.3, dashes=(5, 4))
    add_line_label(base, ax, base.NARR, f"Narr={base.NARR}", y_axes=0.88)

    p95, p99 = base.percentile(false_lens, [95.0, 99.0])
    cov = float(np.mean(false_lens < base.NARR) * 100.0)
    txt = f"覆盖率(<Narr)={cov:.1f}%\nmax={int(false_lens.max())}, P95={p95:.1f}, P99={p99:.1f}"
    ax.text(
        0.02,
        0.95,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=base.FS_TXT,
        fontproperties=base.mixed_font(base.FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.24"),
    )

    ax.set_title("无车连续触发长度统计", pad=8.0, fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_xlabel("连续点数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_ylabel("次数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    base.add_common_axis_style(ax)
    return {"coverage_lt_narr": cov, "p95": float(p95), "p99": float(p99)}


def plot_td_panel(base, ax: plt.Axes, drop_lens: np.ndarray) -> dict[str, float]:
    edges = np.arange(0.5, float(drop_lens.max()) + 1.6, 1.0)
    ax.hist(
        drop_lens,
        bins=edges,
        color=base.COLOR_BAR,
        edgecolor="#1F587F",
        linewidth=1.0,
        alpha=0.96,
        rwidth=0.72,
    )
    y_top = ax.get_ylim()[1]
    ax.set_ylim(0.0, y_top * 1.18)
    ax.axvline(base.TD, color=base.COLOR_THRESH, linestyle="--", linewidth=1.3, dashes=(5, 4))
    add_line_label(base, ax, base.TD, f"Td={base.TD}", y_axes=0.88)

    p95, p99 = base.percentile(drop_lens, [95.0, 99.0])
    cov = float(np.mean(drop_lens <= base.TD) * 100.0)
    txt = f"n={drop_lens.size}, 覆盖率(<=Td)={cov:.1f}%\nmax={int(drop_lens.max())}, P95={p95:.1f}, P99={p99:.1f}"
    ax.text(
        0.02,
        0.95,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=base.FS_TXT,
        fontproperties=base.mixed_font(base.FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.24"),
    )

    ax.set_title("到达确认后短时回落长度统计", pad=8.0, fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_xlabel("连续点数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_ylabel("次数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    base.add_common_axis_style(ax)
    return {"coverage_le_td": cov, "p95": float(p95), "p99": float(p99), "n": int(drop_lens.size)}


def save_threshold_preview(base, pooled: dict[str, object]) -> tuple[Path, Path, dict[str, float]]:
    fig, ax = plt.subplots(figsize=(13.8, 5.7), dpi=260)
    plt.subplots_adjust(left=0.078, right=0.992, bottom=0.205, top=0.93)
    stats = plot_threshold_panel(base, ax, pooled["p_env"], pooled["p_veh"])

    png_path = OUT_DIR / THRESHOLD_PNG
    svg_path = OUT_DIR / THRESHOLD_SVG
    fig.savefig(png_path, dpi=430, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return png_path, svg_path, stats


def save_counts_preview(base, pooled: dict[str, object]) -> tuple[Path, Path, dict[str, float], dict[str, float]]:
    fig, axes = plt.subplots(1, 2, figsize=(16.0, 6.9), dpi=260)
    plt.subplots_adjust(left=0.062, right=0.992, bottom=0.165, top=0.91, wspace=0.20)
    stats_b = plot_narr_panel(base, axes[0], pooled["false_lens"])
    stats_c = plot_td_panel(base, axes[1], pooled["drop_lens"])

    png_path = OUT_DIR / COUNTS_PNG
    svg_path = OUT_DIR / COUNTS_SVG
    fig.savefig(png_path, dpi=430, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return png_path, svg_path, stats_b, stats_c


def build_previews() -> dict[str, Path]:
    base = load_base_module()
    configure_style(base)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pooled = collect_pooled_statistics(base)
    threshold_png, threshold_svg, panel_threshold = save_threshold_preview(base, pooled)
    counts_png, counts_svg, panel_b, panel_c = save_counts_preview(base, pooled)

    meta_path = OUT_DIR / META_JSON
    meta = {
        "source_files": [str(path) for path in INPUT_FILES],
        "total_rows": int(pooled["total_rows"]),
        "event_count": int(pooled["total_events"]),
        "false_lens_count": int(pooled["false_lens"].size),
        "drop_lens_count": int(pooled["drop_lens"].size),
        "panel_threshold": panel_threshold,
        "panel_b": panel_b,
        "panel_c": panel_c,
        "preview_threshold_png": str(threshold_png),
        "preview_counts_png": str(counts_png),
        "per_file": [
            {
                "file": item["file"],
                "rows": int(item["rows"]),
                "event_count": int(item["event_count"]),
                "false_lens_count": int(item["false_lens"].size),
                "drop_lens_count": int(item["drop_lens"].size),
            }
            for item in pooled["analyses"]
        ],
        "note": "Preview only. Split into two main figures for thesis layout.",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "threshold_png": threshold_png,
        "threshold_svg": threshold_svg,
        "counts_png": counts_png,
        "counts_svg": counts_svg,
        "meta": meta_path,
    }


def main() -> None:
    outputs = build_previews()
    print(f"Threshold PNG: {outputs['threshold_png']}")
    print(f"Threshold SVG: {outputs['threshold_svg']}")
    print(f"Counts PNG: {outputs['counts_png']}")
    print(f"Counts SVG: {outputs['counts_svg']}")
    print(f"META JSON: {outputs['meta']}")


if __name__ == "__main__":
    main()
