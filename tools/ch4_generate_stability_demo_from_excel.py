from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = Path(r"G:\地磁组\lab_office\路段统计\20240723校园测试数据\校园测试20240723.xlsx")
DEFAULT_PNG = ROOT / "images" / "ch4_stability_demo.png"
DEFAULT_PDF = ROOT / "images" / "ch4_stability_demo.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Figure 4.4 from the Excel source.")
    parser.add_argument("--xlsx-file", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--sheet-id", type=int, default=2)
    parser.add_argument("--fs", type=float, default=50.0)
    parser.add_argument("--idx0", type=int, default=25009)
    parser.add_argument("--idx1", type=int, default=25591)
    parser.add_argument("--show-axis", choices=["x", "y", "z", "norm"], default="z")
    parser.add_argument("--L", type=int, default=25)
    parser.add_argument("--s", type=int, default=25)
    parser.add_argument("--N-stable", type=int, default=5, dest="n_stable")
    parser.add_argument("--R-th", type=float, default=5.44, dest="r_th")
    parser.add_argument("--M-th", type=float, default=3.50, dest="m_th")
    parser.add_argument("--x-start", type=float, default=1.0, dest="x_start")
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--out-png", type=Path, default=DEFAULT_PNG)
    parser.add_argument("--out-pdf", type=Path, default=DEFAULT_PDF)
    return parser.parse_args()


def find_font(candidates: list[str]) -> FontProperties:
    available = {entry.name.lower(): entry.fname for entry in fm.fontManager.ttflist}
    for name in candidates:
        key = name.lower()
        if key in available:
            return FontProperties(fname=available[key])
    return FontProperties()


def first_font_name(candidates: list[str], fallback: str) -> str:
    available = {entry.name.lower(): entry.name for entry in fm.fontManager.ttflist}
    for name in candidates:
        key = name.lower()
        if key in available:
            return available[key]
    return fallback


def moving_average(x: np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(x)
    return series.rolling(window, min_periods=1, center=True).mean().to_numpy(float)


def rolling_median(x: np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(x)
    return series.rolling(window, min_periods=1, center=True).median().to_numpy(float)


def maybe_lowpass(x: np.ndarray, fs: float, fc: float, order: int = 11) -> np.ndarray:
    if importlib.util.find_spec("scipy.signal") is None:
        window = max(5, round(0.20 * fs))
        if window % 2 == 0:
            window += 1
        return moving_average(x, int(window))

    from scipy.signal import filtfilt, firwin

    taps = firwin(order + 1, fc / (fs / 2.0), window=("kaiser", 0.5), pass_zero="lowpass", scale=True)
    return filtfilt(taps, [1.0], x)


def trailing_mean(x: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(x).rolling(window, min_periods=window).mean().to_numpy(float)


def trailing_max(x: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(x).rolling(window, min_periods=window).max().to_numpy(float)


def trailing_min(x: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(x).rolling(window, min_periods=window).min().to_numpy(float)


def local_estimate_event_end(x: np.ndarray, k_min: int) -> int:
    dx = np.abs(np.diff(x, prepend=x[0]))
    med = np.median(dx)
    madv = np.median(np.abs(dx - med))
    sigma = 1.4826 * madv
    thr = med + 6.0 * sigma
    if not np.isfinite(thr) or thr <= 0:
        thr = np.percentile(dx, 95)
    idx = np.flatnonzero(dx > thr)
    if idx.size == 0:
        return max(0, k_min)
    return max(int(idx[-1]), int(k_min))


def stable_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    vec = np.asarray(mask, dtype=bool)
    diff = np.diff(np.r_[False, vec, False].astype(int))
    starts = np.flatnonzero(diff == 1)
    ends = np.flatnonzero(diff == -1) - 1
    return [(int(s), int(e)) for s, e in zip(starts, ends)]


def add_shade(ax: plt.Axes, x0: float, x1: float) -> None:
    ax.axvspan(x0, x1, color="black", alpha=0.06, zorder=0)


def add_segment_shades(ax: plt.Axes, t: np.ndarray, mask: np.ndarray) -> None:
    for s, e in stable_segments(mask):
        ax.axvspan(float(t[s]), float(t[e]), color="black", alpha=0.05, zorder=0)


def add_threshold_label(
    ax: plt.Axes,
    y: float,
    label: str,
    font_en: FontProperties,
    fontsize: float,
) -> None:
    ax.axhline(y, color="#7f7f7f", linestyle=(0, (4, 4)), linewidth=1.2, zorder=1)
    x_right = ax.get_xlim()[1]
    ax.text(
        x_right,
        y + 0.02 * (ax.get_ylim()[1] - ax.get_ylim()[0]),
        label,
        fontproperties=font_en,
        fontsize=fontsize,
        ha="right",
        va="bottom",
    )


def main() -> None:
    args = parse_args()
    if not args.xlsx_file.is_file():
        raise FileNotFoundError(f"Excel file not found: {args.xlsx_file}")

    cn_font = find_font(["SimSun", "宋体", "NSimSun", "新宋体", "Microsoft YaHei", "微软雅黑"])
    en_font = find_font(["Times New Roman", "Times", "DejaVu Serif"])
    en_font_name = first_font_name(["Times New Roman", "Times"], "DejaVu Serif")

    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = [en_font_name, "Times", "DejaVu Serif"]
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = en_font_name
    plt.rcParams["mathtext.it"] = f"{en_font_name}:italic"
    plt.rcParams["mathtext.bf"] = f"{en_font_name}:bold"
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"

    df = pd.read_excel(args.xlsx_file, sheet_name=args.sheet_id - 1, header=None)
    df = df.iloc[:, :3].dropna(how="any")
    B = df.to_numpy(dtype=float)

    bx = B[:, 0]
    by = B[:, 1]
    bz = B[:, 2]
    n = len(B)
    if not (1 <= args.idx0 < args.idx1 <= n):
        raise ValueError(f"idx0/idx1 out of range: idx0={args.idx0}, idx1={args.idx1}, n={n}")

    bx_f = maybe_lowpass(bx, args.fs, 5.0)
    by_f = maybe_lowpass(by, args.fs, 5.0)
    bz_f = maybe_lowpass(bz, args.fs, 6.0)

    base_win = max(21, round(10 * args.fs))
    if base_win % 2 == 0:
        base_win += 1
    bx_base = rolling_median(bx_f, int(base_win))
    by_base = rolling_median(by_f, int(base_win))
    bz_base = rolling_median(bz_f, int(base_win))
    norm_sig = np.sqrt((bx_f - bx_base) ** 2 + (by_f - by_base) ** 2 + (bz_f - bz_base) ** 2)

    sl = slice(args.idx0 - 1, args.idx1)
    bx_s = bx_f[sl]
    by_s = by_f[sl]
    bz_s = bz_f[sl]
    norm_s = norm_sig[sl]
    t_s = np.arange(len(bz_s), dtype=float) / args.fs

    ns0 = min(n, max(10, round(5 * args.fs)))
    sgx = float(np.std(bx_f[:ns0], ddof=0))
    sgy = float(np.std(by_f[:ns0], ddof=0))
    sgz = float(np.std(bz_f[:ns0], ddof=0))
    den = sgy * sgz + sgx * sgz + sgx * sgy
    if den < 1e-12:
        w = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=float)
    else:
        w = np.array([sgy * sgz, sgx * sgz, sgx * sgy], dtype=float) / den

    rx = trailing_max(bx_s, args.L) - trailing_min(bx_s, args.L)
    ry = trailing_max(by_s, args.L) - trailing_min(by_s, args.L)
    rz = trailing_max(bz_s, args.L) - trailing_min(bz_s, args.L)
    R = w[0] * rx + w[1] * ry + w[2] * rz

    mux = trailing_mean(bx_s, args.L)
    muy = trailing_mean(by_s, args.L)
    muz = trailing_mean(bz_s, args.L)

    mx = np.full_like(mux, np.nan)
    my = np.full_like(muy, np.nan)
    mz = np.full_like(muz, np.nan)
    mx[args.s :] = mux[args.s :] - mux[:-args.s]
    my[args.s :] = muy[args.s :] - muy[:-args.s]
    mz[args.s :] = muz[args.s :] - muz[:-args.s]
    M = w[0] * np.abs(mx) + w[1] * np.abs(my) + w[2] * np.abs(mz)

    stable_raw = (R <= args.r_th) & (M <= args.m_th)
    stable_gate = pd.Series(stable_raw.astype(float)).rolling(args.n_stable, min_periods=args.n_stable).sum().to_numpy()
    stable_gate = np.nan_to_num(stable_gate) >= args.n_stable

    finite_mask = np.isfinite(R) & np.isfinite(M)
    idx_valid0 = int(np.flatnonzero(finite_mask)[0]) if np.any(finite_mask) else 0
    raw_plot = stable_raw.astype(float)
    gate_plot = stable_gate.astype(float)
    raw_plot[:idx_valid0] = np.nan
    gate_plot[:idx_valid0] = np.nan

    if args.show_axis == "x":
        s_show = bx_s
        ylab = r"$\tilde{B}_x$ / nT"
        tag = "Bx"
    elif args.show_axis == "y":
        s_show = by_s
        ylab = r"$\tilde{B}_y$ / nT"
        tag = "By"
    elif args.show_axis == "z":
        s_show = bz_s
        ylab = r"$\tilde{B}_z$ / nT"
        tag = "Bz"
    else:
        s_show = norm_s
        ylab = r"$\|\Delta \mathbf{B}\|_2$ / nT"
        tag = "norm"

    k_out = local_estimate_event_end(s_show, idx_valid0)
    after_out = np.flatnonzero(stable_gate & (np.arange(len(stable_gate)) >= k_out))
    k_st = int(after_out[0]) if after_out.size else -1

    args.out_png.parent.mkdir(parents=True, exist_ok=True)
    args.out_pdf.parent.mkdir(parents=True, exist_ok=True)

    fs_ax = 19
    fs_lab = 21
    fs_leg = 20
    fs_ann = 28
    lw_main = 1.8
    lw_aux = 1.35

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(11.0, 7.8),
        sharex=True,
        gridspec_kw={"hspace": 0.08},
    )

    for ax in axes:
        ax.grid(True, color="#d7dde7", linestyle="--", linewidth=0.75, alpha=0.72)
        ax.tick_params(axis="both", labelsize=fs_ax, pad=2.5)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(en_font)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)

    ax1, ax2, ax3, ax4 = axes
    ax1.plot(t_s, s_show, linewidth=lw_main, color="#1f77b4")
    ax1.set_ylabel(ylab, fontsize=fs_lab, fontproperties=en_font)
    add_shade(ax1, float(t_s[0]), float(t_s[idx_valid0]))
    add_segment_shades(ax1, t_s, stable_gate)
    ax1.axvline(float(t_s[k_out]), color="black", linestyle=(0, (4, 4)), linewidth=lw_aux)
    if k_st >= 0:
        ax1.axvline(float(t_s[k_st]), color="black", linestyle="-", linewidth=lw_aux)

    yl1 = ax1.get_ylim()
    y_text = yl1[0] + 0.10 * (yl1[1] - yl1[0])
    dx = max(0.05, 0.02 * (float(t_s[-1]) - float(t_s[0])))
    xmin_text = float(t_s[0]) + 0.01 * (float(t_s[-1]) - float(t_s[0]))
    ax1.text(
        max(xmin_text, float(t_s[k_out]) - dx),
        y_text,
        r"$t_{out}$",
        fontsize=fs_ann,
        fontproperties=en_font,
        ha="right",
        va="bottom",
    )
    if k_st >= 0:
        ax1.text(
            max(xmin_text, float(t_s[k_st]) - dx),
            y_text,
            r"$t_{st}$",
            fontsize=fs_ann,
            fontproperties=en_font,
            ha="right",
            va="bottom",
        )

    ax2.plot(t_s, R, linewidth=lw_main, color="#1f77b4")
    ax2.set_ylabel(r"$R(k)$", fontsize=fs_lab, fontproperties=en_font)
    add_shade(ax2, float(t_s[0]), float(t_s[idx_valid0]))
    add_threshold_label(ax2, args.r_th, r"$R_{th}$", en_font, fs_ann)

    ax3.plot(t_s, M, linewidth=lw_main, color="#1f77b4")
    ax3.set_ylabel(r"$M(k)$", fontsize=fs_lab, fontproperties=en_font)
    add_shade(ax3, float(t_s[0]), float(t_s[idx_valid0]))
    add_threshold_label(ax3, args.m_th, r"$M_{th}$", en_font, fs_ann)

    ax4.step(t_s, raw_plot, where="post", linewidth=lw_aux, color="#1f77b4", label="双判据成立")
    ax4.step(t_s, gate_plot, where="post", linewidth=lw_main, color="#ff7f0e", label="连续门控后")
    ax4.set_ylim(-0.1, 1.1)
    ax4.set_ylabel("stable", fontsize=fs_lab, fontproperties=en_font)
    leg = ax4.legend(loc="upper right", prop=cn_font, fontsize=fs_leg, framealpha=1.0)
    for txt in leg.get_texts():
        txt.set_fontproperties(cn_font)

    fig.supxlabel(r"时间 / $s$", fontsize=fs_lab, fontproperties=cn_font, y=0.04)
    x_left = max(float(t_s[0]), float(args.x_start))
    ax4.set_xlim(x_left, float(t_s[-1]))

    fig.savefig(args.out_png, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(args.out_pdf, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"[OK] saved PNG: {args.out_png}")
    print(f"[OK] saved PDF: {args.out_pdf}")


if __name__ == "__main__":
    main()
