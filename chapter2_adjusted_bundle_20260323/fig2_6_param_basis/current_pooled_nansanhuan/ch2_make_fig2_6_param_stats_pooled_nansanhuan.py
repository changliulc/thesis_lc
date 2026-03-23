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


def plot_panel_a(base, ax: plt.Axes, p_env: np.ndarray, p_veh: np.ndarray) -> dict[str, float]:
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
        linewidth=0.9,
        label="无车段",
    )
    _, _, car_patches = ax.hist(
        p_veh,
        bins=edges,
        density=True,
        alpha=0.55,
        color=base.COLOR_CAR,
        edgecolor="#8F5A3B",
        linewidth=0.9,
        label="有车段",
    )

    ax.axvline(base.THETA_LEA, color=base.COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    ax.axvline(base.THETA_ARR, color=base.COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    y_top = ax.get_ylim()[1]
    ax.text(base.THETA_LEA + 0.012, y_top * 0.92, "θlea", rotation=90, fontsize=base.FS_TXT, color="#444444", va="bottom")
    ax.text(base.THETA_ARR + 0.012, y_top * 0.92, "θarr", rotation=90, fontsize=base.FS_TXT, color="#444444", va="bottom")

    ax.set_title("(a) Pcar(k) 分布对比", fontsize=base.FS_TTL, pad=10, fontproperties=base.mixed_font(base.FS_TTL))
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
    txt = (
        f"无车: P99.9={q_env[2]:.3f}, P99={q_env[1]:.3f}\n"
        f"有车: P1={q_veh[0]:.3f}, P5={q_veh[1]:.3f}"
    )
    ax.text(
        0.02,
        0.98,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=base.FS_TXT,
        fontproperties=base.mixed_font(base.FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.20"),
    )
    base.add_common_axis_style(ax)

    return {
        "p_env_p99_9": float(q_env[2]),
        "p_env_p99": float(q_env[1]),
        "p_veh_p1": float(q_veh[0]),
        "p_veh_p5": float(q_veh[1]),
    }


def plot_panel_b(base, ax: plt.Axes, false_lens: np.ndarray) -> dict[str, float]:
    edges = np.arange(0.5, float(false_lens.max()) + 1.6, 1.0)
    ax.hist(
        false_lens,
        bins=edges,
        color=base.COLOR_BAR,
        edgecolor="#1F587F",
        linewidth=0.9,
        alpha=0.96,
        rwidth=0.82,
    )
    ax.axvline(base.NARR, color=base.COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    y_top = ax.get_ylim()[1]
    ax.text(base.NARR + 0.10, y_top * 0.90, f"Narr={base.NARR}", rotation=90, fontsize=base.FS_TXT, color="#444444", va="bottom")

    p95, p99 = base.percentile(false_lens, [95.0, 99.0])
    cov = float(np.mean(false_lens < base.NARR) * 100.0)
    txt = f"覆盖率(<Narr)={cov:.1f}%\nmax={int(false_lens.max())}, P95={p95:.1f}, P99={p99:.1f}"
    ax.text(
        0.02,
        0.98,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=base.FS_TXT,
        fontproperties=base.mixed_font(base.FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.20"),
    )

    ax.set_title("(b) 无车连续触发长度统计", fontsize=base.FS_TTL, pad=10, fontproperties=base.mixed_font(base.FS_TTL))
    ax.set_xlabel("连续点数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_ylabel("次数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    base.add_common_axis_style(ax)

    return {"coverage_lt_narr": cov, "p95": float(p95), "p99": float(p99)}


def plot_panel_c(base, ax: plt.Axes, drop_lens: np.ndarray) -> dict[str, float]:
    edges = np.arange(0.5, float(drop_lens.max()) + 1.6, 1.0)
    ax.hist(
        drop_lens,
        bins=edges,
        color=base.COLOR_BAR,
        edgecolor="#1F587F",
        linewidth=0.9,
        alpha=0.96,
        rwidth=0.74,
    )
    ax.axvline(base.TD, color=base.COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    y_top = ax.get_ylim()[1]
    ax.text(base.TD + 0.10, y_top * 0.90, f"Td={base.TD}", rotation=90, fontsize=base.FS_TXT, color="#444444", va="bottom")

    p95, p99 = base.percentile(drop_lens, [95.0, 99.0])
    cov = float(np.mean(drop_lens <= base.TD) * 100.0)
    txt = f"n={drop_lens.size}, 覆盖率(<=Td)={cov:.1f}%\nmax={int(drop_lens.max())}, P95={p95:.1f}, P99={p99:.1f}"
    ax.text(
        0.02,
        0.98,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=base.FS_TXT,
        fontproperties=base.mixed_font(base.FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.20"),
    )

    ax.set_title("(c) 到达确认后短时回落长度统计", fontsize=base.FS_TTL, pad=10, fontproperties=base.mixed_font(base.FS_TTL))
    ax.set_xlabel("连续点数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    ax.set_ylabel("次数", fontsize=base.FS_AX, fontproperties=base.mixed_font(base.FS_AX))
    base.add_common_axis_style(ax)

    return {"coverage_le_td": cov, "p95": float(p95), "p99": float(p99), "n": int(drop_lens.size)}


def build_preview() -> dict[str, Path]:
    base = load_base_module()
    base.configure_matplotlib()
    base.FS_AX = 18.0
    base.FS_TTL = 19.5
    base.FS_TXT = 16.2
    base.FS_LEG = 17.0
    plt.rcParams["font.size"] = 17
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    analyses = [analyze_one(base, path) for path in INPUT_FILES]

    p_env = np.concatenate([item["p_env"] for item in analyses], axis=0)
    p_veh = np.concatenate([item["p_veh"] for item in analyses], axis=0)
    false_lens = np.concatenate([item["false_lens"] for item in analyses], axis=0)
    drop_lens = np.concatenate([item["drop_lens"] for item in analyses], axis=0)
    total_events = int(sum(int(item["event_count"]) for item in analyses))

    fig, axes = plt.subplots(1, 3, figsize=(17.6, 5.8), dpi=220)
    plt.subplots_adjust(left=0.045, right=0.992, bottom=0.20, top=0.89, wspace=0.24)

    panel_a_stats = plot_panel_a(base, axes[0], p_env, p_veh)
    panel_b_stats = plot_panel_b(base, axes[1], false_lens)
    panel_c_stats = plot_panel_c(base, axes[2], drop_lens)

    png_path = OUT_DIR / "fig_param_basis_pooled_nansanhuan_preview.png"
    svg_path = OUT_DIR / "fig_param_basis_pooled_nansanhuan_preview.svg"
    meta_path = OUT_DIR / "fig_param_basis_pooled_nansanhuan_preview_meta.json"

    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    meta = {
        "source_files": [str(path) for path in INPUT_FILES],
        "total_rows": int(sum(int(item["rows"]) for item in analyses)),
        "event_count": total_events,
        "false_lens_count": int(false_lens.size),
        "drop_lens_count": int(drop_lens.size),
        "panel_a": panel_a_stats,
        "panel_b": panel_b_stats,
        "panel_c": panel_c_stats,
        "per_file": [
            {
                "file": item["file"],
                "rows": int(item["rows"]),
                "event_count": int(item["event_count"]),
                "false_lens_count": int(item["false_lens"].size),
                "drop_lens_count": int(item["drop_lens"].size),
            }
            for item in analyses
        ],
        "note": "Preview only. Current thesis image was not overwritten.",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"png": png_path, "svg": svg_path, "meta": meta_path}


def main() -> None:
    outputs = build_preview()
    print(f"Preview PNG: {outputs['png']}")
    print(f"Preview SVG: {outputs['svg']}")
    print(f"Preview META: {outputs['meta']}")


if __name__ == "__main__":
    main()
