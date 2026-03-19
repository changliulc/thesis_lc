from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import loadmat


def pick_font() -> list[str]:
    return ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]


def all_zero_crossings(t: np.ndarray, y: np.ndarray) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(len(y) - 1):
        y0 = float(y[i])
        y1 = float(y[i + 1])
        if y0 == 0:
            pts.append((float(t[i]), 0.0))
        elif y0 * y1 < 0:
            ratio = abs(y0) / (abs(y0) + abs(y1))
            x = float(t[i] + (t[i + 1] - t[i]) * ratio)
            pts.append((x, 0.0))
    return pts


def pick_main_zero_crossing(t: np.ndarray, y: np.ndarray, t_left: float, t_right: float) -> tuple[float, float] | None:
    pts = all_zero_crossings(t, y)
    if not pts:
        return None
    in_main = [p for p in pts if t_left <= p[0] <= t_right]
    if in_main:
        center = 0.5 * (t_left + t_right)
        return min(in_main, key=lambda p: abs(p[0] - center))
    center = 0.5 * (t_left + t_right)
    return min(pts, key=lambda p: abs(p[0] - center))


def trim_to_outer_zero_crossings(t: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pts = all_zero_crossings(t, y)
    if len(pts) < 2:
        return t, y

    t_left = float(pts[0][0])
    t_right = float(pts[-1][0])
    if t_right <= t_left:
        return t, y

    keep = (t > t_left) & (t < t_right)
    t_mid = t[keep]
    y_mid = y[keep]

    new_t = np.concatenate(([t_left], t_mid, [t_right]))
    new_y = np.concatenate(([0.0], y_mid, [0.0]))
    return new_t, new_y


def loadmat_safe(mat_path: Path):
    try:
        return loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    except OSError:
        tmp_dir = Path(tempfile.gettempdir()) / "codex_ch3_mat"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / "processedVehicleData_3class_REAL_2.mat"
        shutil.copy2(mat_path, tmp_path)
        return loadmat(tmp_path, squeeze_me=True, struct_as_record=False)


def load_event_from_csv(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    t = df["t_s"].to_numpy(dtype=float)
    dz = df["dBz_nT"].to_numpy(dtype=float)
    return t, dz


def load_full_event_from_mat(mat_path: Path, class_id: int, sample_index: int, fs: float, n0: int) -> tuple[np.ndarray, np.ndarray]:
    mat = loadmat_safe(mat_path)
    processed = np.ravel(mat["ProcessedData"][class_id - 1])
    lengths = np.ravel(mat["targetLength"][class_id - 1]).astype(int)

    bpad = np.array(processed[sample_index - 1], dtype=float)
    n = int(lengths[sample_index - 1])
    b = bpad[:n, :]

    n0 = min(n0, n)
    b0 = np.mean(b[:n0, :], axis=0)
    db = b - b0
    t = np.arange(n, dtype=float) / fs
    dz = db[:, 2]
    return t, dz


def build_figure(t: np.ndarray, dz: np.ndarray, out_path: Path) -> None:
    t_cut = 2.0
    keep = t <= t_cut
    t = t[keep]
    dz = dz[keep]
    t, dz = trim_to_outer_zero_crossings(t, dz)
    t = t - float(t[0])

    t_start = float(t[0])
    t_end = float(t[-1])
    x_pad = max(0.03 * max(t_end - t_start, 1e-6), 0.03)

    z_max_idx = int(np.argmax(dz))
    z_min_idx = int(np.argmin(dz))
    z_max_t = float(t[z_max_idx])
    z_min_t = float(t[z_min_idx])
    z_max = float(dz[z_max_idx])
    z_min = float(dz[z_min_idx])
    zero_cross = pick_main_zero_crossing(t, dz, min(z_max_t, z_min_t), max(z_max_t, z_min_t))

    plt.rcParams["font.sans-serif"] = pick_font()
    plt.rcParams["axes.unicode_minus"] = False
    arrow_color = "#444444"

    fig, ax = plt.subplots(figsize=(7.0, 4.2), facecolor="white")
    ax.grid(True, alpha=0.20, linewidth=0.8)
    ax.set_xlim(0.0, t_end + x_pad)

    y_pad = 0.16 * max(abs(z_max), abs(z_min), 1.0)
    y_top = z_max + y_pad
    y_bottom = min(z_min - y_pad * 1.35, -72.0)

    ax.plot(t, dz, color="#4f81bd", linewidth=2.2, zorder=3)
    ax.axhline(0.0, color="#888888", linewidth=1.0, linestyle="--", zorder=1)
    ax.fill_between(t, 0.0, dz, where=(dz >= 0), color="#f6b26b", alpha=0.28, zorder=2, interpolate=True)
    ax.fill_between(t, 0.0, dz, where=(dz < 0), color="#f6b26b", alpha=0.28, zorder=2, interpolate=True)

    ax.scatter([z_max_t, z_min_t], [z_max, z_min], s=42, color="#d62728", zorder=4)

    ax.annotate(
        r"$z_{\max}$",
        xy=(z_max_t, z_max),
        xytext=(z_max_t - 0.13, z_max + 0.17 * (y_top - y_bottom)),
        fontsize=12,
        arrowprops=dict(arrowstyle="->", lw=1.0, color=arrow_color),
    )
    ax.annotate(
        r"$z_{\min}$",
        xy=(z_min_t, z_min),
        xytext=(z_min_t + 0.16, z_min + 0.12 * (y_top - y_bottom)),
        fontsize=12,
        arrowprops=dict(arrowstyle="->", lw=1.0, color=arrow_color),
    )

    if zero_cross is not None:
        cross_t, cross_y = zero_cross
        ax.scatter([cross_t], [cross_y], s=40, color="#d62728", zorder=4)
        ax.annotate(
            r"$N_{zc}^{(z)}$",
            xy=(cross_t, cross_y),
            xytext=(cross_t + 0.06, 0.12 * (y_top - y_bottom)),
            fontsize=12,
            color="#d62728",
            arrowprops=dict(arrowstyle="->", lw=1.0, color=arrow_color),
        )

    ax.annotate(
        "",
        xy=(t_end, y_bottom + 0.12 * (y_top - y_bottom)),
        xytext=(t_start, y_bottom + 0.12 * (y_top - y_bottom)),
        arrowprops=dict(arrowstyle="<->", lw=1.1, color=arrow_color),
    )
    ax.text(
        t_start + 0.46 * (t_end - t_start),
        y_bottom + 0.145 * (y_top - y_bottom),
        r"$T_{\mathrm{evt}}$",
        ha="center",
        va="bottom",
        fontsize=12,
    )

    ax.text(
        t_start + 0.60 * (t_end - t_start),
        y_top - 0.18 * (y_top - y_bottom),
        r"$A_{z}$",
        color="#8a4b08",
        fontsize=12,
    )
    ax.text(
        t_start + 0.03 * (t_end - t_start),
        0.0 + 0.05 * (y_top - y_bottom),
        "零参考线",
        color="#666666",
        fontsize=11,
    )

    ax.set_xlabel("时间 / s")
    ax.set_ylabel(r"$\Delta B_z[n]$ / nT")
    ax.set_ylim(y_bottom, y_top)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]

    parser = argparse.ArgumentParser(description="Draw a Xiang-style feature explanation figure for Chapter 3.")
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / "processedVehicleData_3class_REAL (2).mat",
        help="Representative waveform source path.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "images" / "ch3_feature_explain.png",
        help="Output image path.",
    )
    parser.add_argument("--source", choices=["mat", "csv"], default="mat", help="Source type.")
    parser.add_argument("--class-id", type=int, default=2, help="1-based class id for MAT source.")
    parser.add_argument("--sample-index", type=int, default=94, help="1-based sample index for MAT source.")
    parser.add_argument("--fs", type=float, default=50.0, help="Sampling rate for MAT source.")
    parser.add_argument("--n0", type=int, default=25, help="Head baseline window size for MAT source.")
    args = parser.parse_args()

    if args.source == "csv":
        t, dz = load_event_from_csv(args.input)
    else:
        t, dz = load_full_event_from_mat(args.input, args.class_id, args.sample_index, args.fs, args.n0)

    build_figure(t, dz, args.out)


if __name__ == "__main__":
    main()
