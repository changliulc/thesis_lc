#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter
from scipy.signal import filtfilt, firwin
from scipy.stats import norm

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "绘图" / "图片新修" / "第二章" / "fig_p_car_example_from_data"

FILE = Path(r"G:\地磁组路段数据\路段统计\20240730白沙路数据采集\20240730白沙路车型分类数据采集.xlsx")
SHEET = 2
ROW_START = 1
ROW_END = 32740

FS = 50.0
NTAP = 11
BETA = 5.0
FC_XY = 5.0
FC_Z = 6.0

P_VEH = 0.25
BG_QUANTILE = 0.30
KAPPA = 3.0
SIGMA_FLOOR = np.array([0.8, 0.8, 0.8], dtype=np.float64)

TL = 324.0
TR = 327.0
X1 = 324.5
X2 = 326.5

FONT_FAMILIES = ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"]
COLOR_X = "#0072BD"
COLOR_Y = "#D95319"
COLOR_Z = "#EDB120"


def configure_fonts() -> None:
    plt.rcParams["font.family"] = FONT_FAMILIES
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"
    plt.rcParams["mathtext.fontset"] = "stix"


def mixed_font(size: float | None = None) -> fm.FontProperties:
    props = fm.FontProperties(family=FONT_FAMILIES)
    if size is not None:
        props.set_size(size)
    return props


def tick_formatter(x: float, _pos: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x))}"
    return f"{x:.1f}"


def read_b() -> np.ndarray:
    if not FILE.exists():
        raise FileNotFoundError(f"未找到原始数据文件: {FILE}")

    nrows = ROW_END - ROW_START + 1
    df = pd.read_excel(
        FILE,
        sheet_name=SHEET - 1,
        usecols="A:C",
        skiprows=ROW_START - 1,
        nrows=nrows,
        engine="openpyxl",
    )
    b = df.to_numpy(dtype=np.float64)
    if np.isnan(b).any():
        raise ValueError("原始 B 数据中存在 NaN，请检查 Excel 区间或空行。")
    return b


def smooth_diff(b: np.ndarray) -> np.ndarray:
    d = np.diff(b, axis=0)
    h_xy = firwin(NTAP, FC_XY, fs=FS, window=("kaiser", BETA), pass_zero="lowpass", scale=True)
    h_z = firwin(NTAP, FC_Z, fs=FS, window=("kaiser", BETA), pass_zero="lowpass", scale=True)

    dbar = np.zeros_like(d)
    dbar[:, 0] = filtfilt(h_xy, [1.0], d[:, 0])
    dbar[:, 1] = filtfilt(h_xy, [1.0], d[:, 1])
    dbar[:, 2] = filtfilt(h_z, [1.0], d[:, 2])
    return dbar


def detect_main_event_window(dbar: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, int]:
    e = np.linalg.norm(dbar, axis=1)
    thr = np.median(e) + 3.0 * 1.4826 * np.median(np.abs(e - np.median(e)))
    idx_evt = np.flatnonzero(e > thr)

    if idx_evt.size == 0:
        return dbar, e, 0, len(dbar) - 1

    pad_l = round(0.4 * FS)
    pad_r = round(0.6 * FS)
    k1 = max(0, int(idx_evt[0]) - pad_l)
    k2 = min(len(dbar) - 1, int(idx_evt[-1]) + pad_r)
    return dbar[k1 : k2 + 1], e[k1 : k2 + 1], k1, k2


def estimate_background_sigma(dbar_use: np.ndarray, e_use: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    q = np.quantile(e_use, BG_QUANTILE)
    bg_mask = e_use <= q
    mu0 = np.zeros(3, dtype=np.float64)
    sigma0 = dbar_use[bg_mask].std(axis=0, ddof=0)
    sigma0 = np.maximum(sigma0, SIGMA_FLOOR)
    sigma0 = KAPPA * sigma0
    return mu0, sigma0


def pget_merge(dbar_use: np.ndarray, mu0: np.ndarray, sigma0: np.ndarray) -> np.ndarray:
    x1 = 1.0 - (1.0 - norm.cdf(np.abs(dbar_use[:, 0]), loc=mu0[0], scale=sigma0[0])) * 2.0
    y1 = 1.0 - (1.0 - norm.cdf(np.abs(dbar_use[:, 1]), loc=mu0[1], scale=sigma0[1])) * 2.0
    z1 = 1.0 - (1.0 - norm.cdf(np.abs(dbar_use[:, 2]), loc=mu0[2], scale=sigma0[2])) * 2.0
    x0 = 1.0 - x1
    y0 = 1.0 - y1
    z0 = 1.0 - z1
    p_env = 1.0 - P_VEH
    pr_env = (x0 * y0 * z0) / (p_env * p_env)
    pr_veh = (x1 * y1 * z1) / (P_VEH * P_VEH)
    return pr_veh / (pr_env + pr_veh)


def build_absolute_time(k1: int, k2: int) -> np.ndarray:
    idx_use = np.arange(k1, k2 + 1, dtype=np.int64)
    n_abs = ROW_START + idx_use + 1
    return (n_abs - 1) / FS


def plot_preview(t_plot: np.ndarray, dbar_plot: np.ndarray, pcar_plot: np.ndarray) -> dict[str, Path]:
    configure_fonts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(7.25, 4.20), dpi=240)
    gs = fig.add_gridspec(
        2,
        1,
        height_ratios=[1.0, 1.0],
        left=0.11,
        right=0.985,
        bottom=0.12,
        top=0.985,
        hspace=0.16,
    )
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

    ax1.plot(t_plot, dbar_plot[:, 0], color=COLOR_X, linewidth=2.0, label="X轴差分")
    ax1.plot(t_plot, dbar_plot[:, 1], color=COLOR_Y, linewidth=2.0, label="Y轴差分")
    ax1.plot(t_plot, dbar_plot[:, 2], color=COLOR_Z, linewidth=2.0, label="Z轴差分")
    ax1.set_xlim(X1, X2)
    ax1.set_ylim(-15.0, 20.0)
    ax1.set_yticks(np.arange(-15.0, 20.1, 5.0))
    ax1.grid(True, color="#B0B0B0", alpha=0.35, linewidth=0.8)
    ax1.tick_params(labelsize=11, length=5, width=1.0, top=True, right=True)
    ax1.set_ylabel("磁场差分值 (nT)", fontsize=13, fontproperties=mixed_font(13))
    ax1.xaxis.set_major_formatter(FuncFormatter(tick_formatter))
    ax1.yaxis.set_major_formatter(FuncFormatter(tick_formatter))
    leg = ax1.legend(
        loc="upper right",
        bbox_to_anchor=(0.985, 1.015),
        fontsize=9.8,
        prop=mixed_font(9.8),
        frameon=True,
        framealpha=0.95,
        fancybox=False,
        borderpad=0.30,
        handlelength=2.2,
        handletextpad=0.42,
    )
    leg.get_frame().set_edgecolor("#444444")

    ax2.plot(t_plot, pcar_plot, color=COLOR_X, linewidth=2.2)
    ax2.set_xlim(X1, X2)
    ax2.set_ylim(-0.02, 1.02)
    ax2.set_yticks(np.linspace(0.0, 1.0, 6))
    ax2.grid(True, color="#B0B0B0", alpha=0.35, linewidth=0.8)
    ax2.tick_params(labelsize=11, length=5, width=1.0, top=True, right=True)
    ax2.set_ylabel("有车概率 Pcar(k)", fontsize=13, fontproperties=mixed_font(13))
    ax2.set_xlabel("时间 (s)", fontsize=13, fontproperties=mixed_font(13))
    ax2.xaxis.set_major_formatter(FuncFormatter(tick_formatter))

    xticks = [324.5, 325.0, 325.5, 326.0, 326.5]
    ax1.set_xticks(xticks)
    ax2.set_xticks(xticks)

    for ax in (ax1, ax2):
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)

    png_path = OUT_DIR / "fig_p_car_example_from_data_preview.png"
    svg_path = OUT_DIR / "fig_p_car_example_from_data_preview.svg"
    meta_path = OUT_DIR / "fig_p_car_example_from_data_preview_meta.json"

    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    meta = {
        "source_excel": str(FILE),
        "sheet": SHEET,
        "row_start": ROW_START,
        "row_end": ROW_END,
        "window_seconds": [X1, X2],
        "style_note": "Reference-like layout, no threshold dashed lines, reduced legend occlusion.",
        "note": "Preview only. Current thesis image was not overwritten.",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"png": png_path, "svg": svg_path, "meta": meta_path}


def main() -> None:
    b = read_b()
    dbar = smooth_diff(b)
    dbar_use, e_use, k1, k2 = detect_main_event_window(dbar)
    mu0, sigma0 = estimate_background_sigma(dbar_use, e_use)
    pcar = pget_merge(dbar_use, mu0, sigma0)
    t_abs = build_absolute_time(k1, k2)

    win = (t_abs >= TL) & (t_abs <= TR)
    if not np.any(win):
        raise RuntimeError(
            f"窗口 [{TL:.2f}, {TR:.2f}] s 内没有数据。当前 t_abs 范围=[{t_abs.min():.2f}, {t_abs.max():.2f}] s。"
        )

    outputs = plot_preview(t_abs[win], dbar_use[win], pcar[win])
    print(f"Preview PNG: {outputs['png']}")
    print(f"Preview SVG: {outputs['svg']}")
    print(f"Preview META: {outputs['meta']}")


if __name__ == "__main__":
    main()
