#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.signal import firwin, lfilter
from scipy.special import erf

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "绘图" / "图片新修" / "第二章" / "fig_param_basis_from_data"

FILE = Path(r"G:\地磁组路段数据\路段统计\20240506南三环\20240506南三环.xlsx")
SHEET = 1

FS = 50.0
SIGMA0 = np.array([1.0235, 1.0176, 0.8763], dtype=np.float64)
P_VEH = 0.25
P_ENV = 1.0 - P_VEH

THETA_ARR = 0.90
THETA_LEA = 0.50
NARR = 10
NLEA = 10
TD = 8

FIR_ORDER = 11
KAISER_BETA = 0.5
FC_XY = 5.0
FC_Z = 6.0

FONT_FAMILIES = ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"]
COLOR_ENV = "#5B9BD5"
COLOR_CAR = "#E6A57E"
COLOR_BAR = "#2F80B9"
COLOR_THRESH = "#6A6A6A"

FS_AX = 13.5
FS_TTL = 14.5
FS_TXT = 11.5
FS_LEG = 12.5


def configure_matplotlib() -> None:
    plt.rcParams["font.family"] = FONT_FAMILIES
    plt.rcParams["font.size"] = 13
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.linewidth"] = 1.1
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"
    plt.rcParams["mathtext.fontset"] = "stix"


def mixed_font(size: float | None = None, weight: str | None = None) -> fm.FontProperties:
    props = fm.FontProperties(family=FONT_FAMILIES)
    if size is not None:
        props.set_size(size)
    if weight is not None:
        props.set_weight(weight)
    return props


def read_b() -> np.ndarray:
    if not FILE.exists():
        raise FileNotFoundError(f"未找到原始数据文件: {FILE}")

    df = pd.read_excel(FILE, sheet_name=SHEET - 1, engine="openpyxl")
    if df.shape[1] < 3:
        raise ValueError("Excel 数据列数不足 3 列，无法提取 Bx/By/Bz。")

    b = df.iloc[:, :3].to_numpy(dtype=np.float64, copy=True)
    b = b[np.all(np.isfinite(b), axis=1)]

    if b.shape[0] < 2000:
        raise RuntimeError(f"数据点太少（{b.shape[0]}），不适合做统计图。")

    return b


def legacy_fir_response(cutoff_hz: float) -> np.ndarray:
    # MATLAB: fir1(N, Wn, kaiser(N+1, beta)) with N=11 -> 12 taps
    return firwin(
        numtaps=FIR_ORDER + 1,
        cutoff=cutoff_hz,
        fs=FS,
        window=("kaiser", KAISER_BETA),
        pass_zero="lowpass",
        scale=True,
    )


def compute_dbar(b: np.ndarray) -> np.ndarray:
    dx = np.diff(b[:, 0])
    dy = np.diff(b[:, 1])
    dz = np.diff(b[:, 2])

    b5 = legacy_fir_response(FC_XY)
    b6 = legacy_fir_response(FC_Z)
    dx_bar = lfilter(b5, [1.0], dx)
    dy_bar = lfilter(b5, [1.0], dy)
    dz_bar = lfilter(b6, [1.0], dz)

    return np.column_stack([dx_bar, dy_bar, dz_bar]).astype(np.float64, copy=False)


def phi(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + erf(z / np.sqrt(2.0)))


def compute_pcar(dbar: np.ndarray) -> np.ndarray:
    zx = np.abs(dbar[:, 0]) / SIGMA0[0]
    zy = np.abs(dbar[:, 1]) / SIGMA0[1]
    zz = np.abs(dbar[:, 2]) / SIGMA0[2]

    x1 = 2.0 * phi(zx) - 1.0
    y1 = 2.0 * phi(zy) - 1.0
    z1 = 2.0 * phi(zz) - 1.0

    x0 = 1.0 - x1
    y0 = 1.0 - y1
    z0 = 1.0 - z1

    pr_env = (x0 * y0 * z0) / (P_ENV * P_ENV)
    pr_veh = (x1 * y1 * z1) / (P_VEH * P_VEH)
    return pr_veh / (pr_env + pr_veh + 1e-12)


def detect_events(pcar: np.ndarray) -> np.ndarray:
    s1, s2, s3, s4, s5 = 1, 2, 3, 4, 5
    state = s1
    n_arr = 0
    n_lea = 0
    td = 0
    tin = None
    events: list[tuple[int, int]] = []

    for k, p in enumerate(pcar):
        if state == s1:
            if p >= THETA_ARR:
                state = s2
                n_arr = 1

        elif state == s2:
            if p >= THETA_ARR:
                n_arr += 1
                if n_arr >= NARR:
                    tin = k - NARR + 1
                    state = s3
                    td = 0
            else:
                state = s1
                n_arr = 0

        elif state == s3:
            td += 1
            if td >= TD:
                state = s4

        elif state == s4:
            if p <= THETA_LEA:
                state = s5
                n_lea = 1

        elif state == s5:
            if p <= THETA_LEA:
                n_lea += 1
                if n_lea >= NLEA:
                    tout = k - NLEA + 1
                    if tin is not None and tout > tin:
                        events.append((tin, tout))
                    state = s1
                    n_arr = 0
                    n_lea = 0
                    td = 0
                    tin = None
            else:
                state = s4
                n_lea = 0

    return np.asarray(events, dtype=np.int64)


def run_segments(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.asarray(mask, dtype=bool).reshape(-1)
    d = np.diff(np.r_[False, mask, False].astype(np.int8))
    s_idx = np.flatnonzero(d == 1)
    e_idx = np.flatnonzero(d == -1) - 1
    return s_idx, e_idx


def run_lengths(mask: np.ndarray) -> np.ndarray:
    s_idx, e_idx = run_segments(mask)
    return e_idx - s_idx + 1


def compute_statistics(pcar: np.ndarray, events: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    car_mask = np.zeros(pcar.shape[0], dtype=bool)
    for tin, tout in events:
        car_mask[tin : tout + 1] = True
    env_mask = ~car_mask

    iarr_false = (pcar >= THETA_ARR) & env_mask
    false_lens = run_lengths(iarr_false).astype(np.int64)

    drop_lens: list[int] = []
    for tin, tout in events:
        b = tout - 1
        if b <= tin:
            continue

        k_conf = tin + NARR - 1
        k_delay_end = min(k_conf + TD - 1, b)

        seg = pcar[tin : b + 1]
        low_mask = seg <= THETA_LEA
        s_idx, e_idx = run_segments(low_mask)

        for s0, e0 in zip(s_idx, e_idx):
            s_global = tin + s0
            if s_global <= k_delay_end and e0 < len(low_mask) - 1:
                drop_lens.append(int(e0 - s0 + 1))

    return car_mask, env_mask, false_lens, np.asarray(drop_lens, dtype=np.int64)


def percentile(data: np.ndarray, q: list[float]) -> np.ndarray:
    if data.size == 0:
        return np.full(len(q), np.nan)
    return np.percentile(data, q)


def add_common_axis_style(ax: plt.Axes) -> None:
    ax.grid(True, color="#B0B0B0", alpha=0.28, linewidth=0.8)
    ax.tick_params(labelsize=FS_AX, length=5.5, width=1.1, top=True, right=True)
    for spine in ax.spines.values():
        spine.set_linewidth(1.1)


def plot_panel_a(ax: plt.Axes, pcar: np.ndarray, env_mask: np.ndarray, car_mask: np.ndarray) -> dict[str, float]:
    p_env = pcar[env_mask]
    p_veh = pcar[car_mask]
    q_env = percentile(p_env, [95.0, 99.0, 99.9])
    q_veh = percentile(p_veh, [1.0, 5.0, 10.0])

    edges = np.linspace(0.0, 1.0, 41)
    _, _, env_patches = ax.hist(
        p_env,
        bins=edges,
        density=True,
        alpha=0.55,
        color=COLOR_ENV,
        edgecolor="#3E7093",
        linewidth=0.9,
        label="无车段",
    )
    _, _, car_patches = ax.hist(
        p_veh,
        bins=edges,
        density=True,
        alpha=0.55,
        color=COLOR_CAR,
        edgecolor="#8F5A3B",
        linewidth=0.9,
        label="有车段",
    )

    ax.axvline(THETA_LEA, color=COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    ax.axvline(THETA_ARR, color=COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    y_top = ax.get_ylim()[1]
    ax.text(THETA_LEA + 0.012, y_top * 0.92, "θlea", rotation=90, fontsize=FS_TXT, color="#444444", va="bottom")
    ax.text(THETA_ARR + 0.012, y_top * 0.92, "θarr", rotation=90, fontsize=FS_TXT, color="#444444", va="bottom")

    ax.set_title("(a) Pcar(k) 分布对比", fontsize=FS_TTL, pad=10, fontproperties=mixed_font(FS_TTL))
    ax.set_xlabel("Pcar", fontsize=FS_AX, fontproperties=mixed_font(FS_AX))
    ax.set_ylabel("概率密度", fontsize=FS_AX, fontproperties=mixed_font(FS_AX))
    ax.legend(
        handles=[env_patches[0], car_patches[0]],
        labels=["无车段", "有车段"],
        loc="upper right",
        fontsize=FS_LEG,
        prop=mixed_font(FS_LEG),
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
        fontsize=FS_TXT,
        fontproperties=mixed_font(FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.20"),
    )
    add_common_axis_style(ax)

    return {
        "p_env_p99_9": float(q_env[2]),
        "p_env_p99": float(q_env[1]),
        "p_veh_p1": float(q_veh[0]),
        "p_veh_p5": float(q_veh[1]),
    }


def plot_panel_b(ax: plt.Axes, false_lens: np.ndarray) -> dict[str, float]:
    if false_lens.size == 0:
        ax.text(
            0.5,
            0.5,
            "无车误触发为 0\n建议改用更长数据段",
            ha="center",
            va="center",
            fontsize=FS_AX,
            fontproperties=mixed_font(FS_AX),
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        return {"coverage_lt_narr": 100.0}

    edges = np.arange(0.5, float(false_lens.max()) + 1.6, 1.0)
    ax.hist(false_lens, bins=edges, color=COLOR_BAR, edgecolor="#1F587F", linewidth=0.9, alpha=0.96)
    ax.axvline(NARR, color=COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    y_top = ax.get_ylim()[1]
    ax.text(NARR + 0.10, y_top * 0.90, f"Narr={NARR}", rotation=90, fontsize=FS_TXT, color="#444444", va="bottom")

    p95, p99 = percentile(false_lens, [95.0, 99.0])
    cov = float(np.mean(false_lens < NARR) * 100.0)
    txt = f"覆盖率(<Narr)={cov:.1f}%\nmax={int(false_lens.max())}, P95={p95:.1f}, P99={p99:.1f}"

    ax.text(
        0.02,
        0.98,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=FS_TXT,
        fontproperties=mixed_font(FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.20"),
    )
    ax.set_title("(b) 无车连续触发长度统计", fontsize=FS_TTL, pad=10, fontproperties=mixed_font(FS_TTL))
    ax.set_xlabel("连续点数", fontsize=FS_AX, fontproperties=mixed_font(FS_AX))
    ax.set_ylabel("次数", fontsize=FS_AX, fontproperties=mixed_font(FS_AX))
    add_common_axis_style(ax)

    return {"coverage_lt_narr": cov, "p95": float(p95), "p99": float(p99)}


def plot_panel_c(ax: plt.Axes, drop_lens: np.ndarray) -> dict[str, float]:
    if drop_lens.size == 0:
        ax.text(
            0.5,
            0.5,
            "回落统计为空\n事件数少或阈值偏低",
            ha="center",
            va="center",
            fontsize=FS_AX,
            fontproperties=mixed_font(FS_AX),
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        return {"coverage_le_td": 0.0}

    edges = np.arange(0.5, float(drop_lens.max()) + 1.6, 1.0)
    ax.hist(drop_lens, bins=edges, color=COLOR_BAR, edgecolor="#1F587F", linewidth=0.9, alpha=0.96)
    ax.axvline(TD, color=COLOR_THRESH, linestyle="--", linewidth=1.2, dashes=(5, 4))
    y_top = ax.get_ylim()[1]
    ax.text(TD + 0.10, y_top * 0.90, f"Td={TD}", rotation=90, fontsize=FS_TXT, color="#444444", va="bottom")

    p95, p99 = percentile(drop_lens, [95.0, 99.0])
    cov = float(np.mean(drop_lens <= TD) * 100.0)
    txt = f"n={drop_lens.size}, 覆盖率(<=Td)={cov:.1f}%\nmax={int(drop_lens.max())}, P95={p95:.1f}, P99={p99:.1f}"

    ax.text(
        0.02,
        0.98,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=FS_TXT,
        fontproperties=mixed_font(FS_TXT),
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, boxstyle="square,pad=0.20"),
    )
    ax.set_title("(c) 到达确认后短时回落长度统计", fontsize=FS_TTL, pad=10, fontproperties=mixed_font(FS_TTL))
    ax.set_xlabel("连续点数", fontsize=FS_AX, fontproperties=mixed_font(FS_AX))
    ax.set_ylabel("次数", fontsize=FS_AX, fontproperties=mixed_font(FS_AX))
    add_common_axis_style(ax)

    return {"coverage_le_td": cov, "p95": float(p95), "p99": float(p99), "n": int(drop_lens.size)}


def build_preview() -> dict[str, Path]:
    configure_matplotlib()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    b = read_b()
    dbar = compute_dbar(b)
    pcar = compute_pcar(dbar)
    events = detect_events(pcar)
    car_mask, env_mask, false_lens, drop_lens = compute_statistics(pcar, events)

    fig, axes = plt.subplots(1, 3, figsize=(16.2, 4.9), dpi=220)
    plt.subplots_adjust(left=0.045, right=0.988, bottom=0.17, top=0.90, wspace=0.25)

    panel_a_stats = plot_panel_a(axes[0], pcar, env_mask, car_mask)
    panel_b_stats = plot_panel_b(axes[1], false_lens)
    panel_c_stats = plot_panel_c(axes[2], drop_lens)

    png_path = OUT_DIR / "fig_param_basis_from_data_preview.png"
    svg_path = OUT_DIR / "fig_param_basis_from_data_preview.svg"
    meta_path = OUT_DIR / "fig_param_basis_from_data_preview_meta.json"

    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)

    meta = {
        "source_excel": str(FILE),
        "sheet": SHEET,
        "sigma0": SIGMA0.tolist(),
        "theta_arr": THETA_ARR,
        "theta_lea": THETA_LEA,
        "narr": NARR,
        "nlea": NLEA,
        "td": TD,
        "event_count": int(events.shape[0]),
        "false_lens_count": int(false_lens.size),
        "drop_lens_count": int(drop_lens.size),
        "panel_a": panel_a_stats,
        "panel_b": panel_b_stats,
        "panel_c": panel_c_stats,
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
