#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "images" / "fig_p_car_example.png"
DEFAULT_OUT_DIR = REPO_ROOT / "绘图" / "图片新修" / "第二章" / "fig_p_car_example_rebuild"

# Fixed bounds reverse-engineered from the current thesis PNG.
# Each tuple is (x0, y0, x1, y1) in pixel coordinates of images/fig_p_car_example.png.
TOP_PLOT_BOUNDS = (135, 46, 1952, 526)
BOTTOM_PLOT_BOUNDS = (135, 615, 1952, 1094)

X_RANGE = (324.5, 326.5)
TOP_Y_RANGE = (-15.0, 15.0)
BOTTOM_Y_RANGE = (0.0, 1.0)
TEXT_FONT_FAMILIES = ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"]

MATLAB_RGB = {
    "X轴差分": np.array([0.0, 114.0, 189.0]),
    "Y轴差分": np.array([217.0, 83.0, 25.0]),
    "Z轴差分": np.array([237.0, 177.0, 32.0]),
}
MATLAB_HEX = {
    "X轴差分": "#0072BD",
    "Y轴差分": "#D95319",
    "Z轴差分": "#EDB120",
}
BOTTOM_BLUE_RGB = np.array([0.0, 114.0, 189.0])


@dataclass
class CurveTrace:
    x_px: np.ndarray
    y_px: np.ndarray
    x_data: np.ndarray
    y_data: np.ndarray
    valid_ratio: float


def configure_fonts() -> None:
    plt.rcParams["font.family"] = TEXT_FONT_FAMILIES
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = "Times New Roman"
    plt.rcParams["mathtext.it"] = "Times New Roman:italic"
    plt.rcParams["mathtext.bf"] = "Times New Roman:bold"
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"


def mixed_font(size: float | None = None) -> fm.FontProperties:
    props = fm.FontProperties(family=TEXT_FONT_FAMILIES)
    if size is not None:
        props.set_size(size)
    return props


def crop_plot(img: np.ndarray, bounds: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = bounds
    return img[y0 : y1 + 1, x0 : x1 + 1, :]


def build_color_mask(
    crop: np.ndarray,
    target_rgb: np.ndarray,
    *,
    dist_threshold: float,
    chroma_threshold: float,
    ignore_box: tuple[int, int, int, int] | None = None,
) -> np.ndarray:
    rgb = crop.astype(np.float64)
    color_dist = np.linalg.norm(rgb - target_rgb[None, None, :], axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    mask = (color_dist <= dist_threshold) & (chroma >= chroma_threshold)

    if ignore_box is not None:
        x0, y0, x1, y1 = ignore_box
        mask[y0:y1, x0:x1] = False
    return mask


def track_curve_from_mask(
    mask: np.ndarray,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    max_jump: float,
    smooth_sigma: float,
) -> CurveTrace:
    n_rows, n_cols = mask.shape
    x_px = np.arange(n_cols, dtype=np.float64)
    y_track = np.full(n_cols, np.nan, dtype=np.float64)
    prev_y: float | None = None

    for x in range(n_cols):
        ys = np.flatnonzero(mask[:, x])
        if ys.size == 0:
            continue
        if prev_y is None:
            picked = float(np.median(ys))
        else:
            picked = float(ys[np.argmin(np.abs(ys - prev_y))])
            if abs(picked - prev_y) > max_jump:
                picked = float(np.median(ys))
        y_track[x] = picked
        prev_y = picked

    valid = np.isfinite(y_track)
    if valid.sum() < max(20, n_cols // 8):
        raise RuntimeError("Insufficient valid curve pixels extracted")

    y_track[~valid] = np.interp(x_px[~valid], x_px[valid], y_track[valid])
    y_track = gaussian_filter1d(y_track, sigma=smooth_sigma, mode="nearest")

    x_data = np.linspace(x_range[0], x_range[1], n_cols)
    y_data = y_range[1] - (y_track / max(n_rows - 1, 1)) * (y_range[1] - y_range[0])
    return CurveTrace(
        x_px=x_px,
        y_px=y_track,
        x_data=x_data,
        y_data=y_data,
        valid_ratio=float(valid.mean()),
    )


def extract_top_traces(top_crop: np.ndarray) -> dict[str, CurveTrace]:
    traces: dict[str, CurveTrace] = {}
    # Ignore the top-right legend area so it does not pollute the curve tracking.
    ignore_box = (1500, 0, top_crop.shape[1], 150)
    for label, rgb in MATLAB_RGB.items():
        mask = build_color_mask(
            top_crop,
            rgb,
            dist_threshold=95.0,
            chroma_threshold=18.0,
            ignore_box=ignore_box,
        )
        traces[label] = track_curve_from_mask(
            mask,
            X_RANGE,
            TOP_Y_RANGE,
            max_jump=34.0,
            smooth_sigma=1.25,
        )
    return traces


def extract_bottom_trace(bottom_crop: np.ndarray) -> CurveTrace:
    mask = build_color_mask(
        bottom_crop,
        BOTTOM_BLUE_RGB,
        dist_threshold=92.0,
        chroma_threshold=12.0,
    )
    return track_curve_from_mask(
        mask,
        X_RANGE,
        BOTTOM_Y_RANGE,
        max_jump=40.0,
        smooth_sigma=1.4,
    )


def clamp_probability(y: np.ndarray) -> np.ndarray:
    y = np.clip(y, 0.0, 1.0)
    return gaussian_filter1d(y, sigma=0.7, mode="nearest")


def build_preview(input_png: Path, out_dir: Path, dpi: int) -> dict[str, Path]:
    configure_fonts()
    out_dir.mkdir(parents=True, exist_ok=True)

    img = np.asarray(Image.open(input_png).convert("RGB"))
    top_crop = crop_plot(img, TOP_PLOT_BOUNDS)
    bottom_crop = crop_plot(img, BOTTOM_PLOT_BOUNDS)

    top_traces = extract_top_traces(top_crop)
    bottom_trace = extract_bottom_trace(bottom_crop)
    prob = clamp_probability(bottom_trace.y_data)

    fig = plt.figure(figsize=(11.2, 6.6), dpi=dpi)
    gs = fig.add_gridspec(
        2,
        1,
        height_ratios=[1.0, 1.0],
        left=0.095,
        right=0.985,
        bottom=0.11,
        top=0.985,
        hspace=0.18,
    )
    ax_top = fig.add_subplot(gs[0, 0])
    ax_bottom = fig.add_subplot(gs[1, 0], sharex=ax_top)

    for label in ["X轴差分", "Y轴差分", "Z轴差分"]:
        tr = top_traces[label]
        ax_top.plot(
            tr.x_data,
            tr.y_data,
            color=MATLAB_HEX[label],
            linewidth=2.05,
            label=label,
        )

    ax_top.set_ylabel("磁场差分值 (nT)", fontsize=16, fontproperties=mixed_font(16))
    ax_top.set_xlim(*X_RANGE)
    ax_top.set_ylim(*TOP_Y_RANGE)
    ax_top.set_yticks([-15, -10, -5, 0, 5, 10, 15])
    ax_top.set_xticks([324.5, 325.0, 325.5, 326.0, 326.5])
    ax_top.tick_params(labelsize=14, length=6, width=1.0, direction="in", top=True, right=True)
    ax_top.grid(True, color="#b0b0b0", alpha=0.35, linewidth=0.8)
    ax_top.legend(
        loc="upper right",
        fontsize=13,
        prop=mixed_font(13),
        frameon=True,
        framealpha=0.96,
        fancybox=False,
        edgecolor="#4c4c4c",
        borderpad=0.35,
        handlelength=2.4,
        handletextpad=0.4,
        labelspacing=0.35,
    )

    ax_bottom.plot(bottom_trace.x_data, prob, color="#0072BD", linewidth=2.1)
    ax_bottom.set_ylabel("有车概率 Pcar(k)", fontsize=16, fontproperties=mixed_font(16))
    ax_bottom.set_xlabel("时间 (s)", fontsize=16, fontproperties=mixed_font(16))
    ax_bottom.set_ylim(-0.02, 1.02)
    ax_bottom.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax_bottom.set_xticks([324.5, 325.0, 325.5, 326.0, 326.5])
    ax_bottom.tick_params(labelsize=14, length=6, width=1.0, direction="in", top=True, right=True)
    ax_bottom.grid(True, color="#b0b0b0", alpha=0.35, linewidth=0.8)

    for ax in (ax_top, ax_bottom):
        for spine in ax.spines.values():
            spine.set_linewidth(1.0)

    png_path = out_dir / "fig_p_car_example_preview.png"
    svg_path = out_dir / "fig_p_car_example_preview.svg"
    meta_path = out_dir / "fig_p_car_example_preview_meta.json"

    fig.savefig(png_path, dpi=dpi, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    meta = {
        "source_png": str(input_png),
        "type": "curve_preserving_replot_from_png",
        "top_valid_ratio": {k: round(v.valid_ratio, 4) for k, v in top_traces.items()},
        "bottom_valid_ratio": round(bottom_trace.valid_ratio, 4),
        "notes": [
            "Rebuilt from the current thesis PNG because the original plotting code was not found.",
            "Goal: keep curve shape close to the original and only enlarge text for thesis readability.",
            "This script only writes preview files and does not overwrite images/fig_p_car_example.png.",
        ],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"png": png_path, "svg": svg_path, "meta": meta_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild a larger-font preview for Fig. 2.4.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dpi", type=int, default=220)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = build_preview(args.input, args.out_dir, args.dpi)
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
