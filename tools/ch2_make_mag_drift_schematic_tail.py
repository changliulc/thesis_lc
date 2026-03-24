#!/usr/bin/env python3
"""
Create a cropped schematic drift figure for Chapter 2.

Design goals from discussion:
- follow the senior's clean long-run raw-drift style
- crop from the Z-axis peak / Y-axis trough region
- show about 2.5 h after that point
- use the thesis font convention: Chinese SimSun, English Times New Roman
- increase label/tick/legend font sizes for thesis readability

This is still a schematic / style mockup, not measured data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch2_mag_drift_refresh"
IMG_DIR = REPO_ROOT / "images"
FONT_FAMILIES = ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"]


def configure_fonts() -> None:
    plt.rcParams["font.family"] = FONT_FAMILIES
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"


def mixed_font(size: float | None = None) -> fm.FontProperties:
    props = fm.FontProperties(family=FONT_FAMILIES)
    if size is not None:
        props.set_size(size)
    return props


def smooth_noise(rng: np.random.Generator, n: int, std: float, win: int) -> np.ndarray:
    x = rng.normal(0.0, std, size=n)
    if win <= 1:
        return x
    if win % 2 == 0:
        win += 1
    ker = np.ones(win, dtype=float) / win
    pad = win // 2
    x_pad = np.pad(x, (pad, pad), mode="edge")
    return np.convolve(x_pad, ker, mode="valid")


def logistic(t: np.ndarray, t0: float, k: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(t - t0) / k))


def gauss(t: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((t - mu) / sigma) ** 2)


def build_full_series() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(20260320)
    total_h = 15.0
    dt_sec = 5.0
    n = int(round(total_h * 3600.0 / dt_sec))
    t_h = np.arange(n) * dt_sec / 3600.0

    x = (
        -396.0
        - 10.0 * (1.0 - np.exp(-t_h / 1.2))
        + 8.5 * logistic(t_h, 4.0, 0.015)
        - 4.8 * (t_h / total_h)
        + 7.2 * gauss(t_h, 11.2, 0.22)
        - 4.0 * logistic(t_h, 12.6, 0.02)
        + 1.4 * logistic(t_h, 13.8, 0.20)
    )
    x += smooth_noise(rng, n, 1.9, 3)
    x += rng.normal(0.0, 0.9, size=n)

    y = (
        -3154.5
        + 11.5 * (1.0 - np.exp(-t_h / 1.4))
        - 4.2 * logistic(t_h, 4.1, 0.02)
        - 6.4 * (t_h / total_h)
        - 11.5 * gauss(t_h, 11.15, 0.20)
        + 4.4 * logistic(t_h, 12.55, 0.05)
        - 1.5 * logistic(t_h, 13.9, 0.18)
    )
    y += smooth_noise(rng, n, 2.2, 3)
    y += rng.normal(0.0, 1.0, size=n)

    z = (
        607.0
        - 33.0 * (1.0 - np.exp(-t_h / 0.95))
        + 4.5 * logistic(t_h, 4.0, 0.02)
        + 8.8 * (t_h / total_h)
        + 34.0 * gauss(t_h, 11.15, 0.24)
        - 9.0 * logistic(t_h, 12.55, 0.03)
        - 2.5 * logistic(t_h, 13.9, 0.18)
    )
    z += smooth_noise(rng, n, 4.4, 3)
    z += rng.normal(0.0, 2.1, size=n)

    return t_h, x, y, z


def crop_and_strengthen(
    t_h: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    start_idx = int(np.argmax(z))
    start_h = float(t_h[start_idx])
    duration_h = 2.5
    end_h = start_h + duration_h
    mask = (t_h >= start_h) & (t_h <= end_h)

    t_rel = t_h[mask] - start_h
    x_tail = x[mask].copy()
    y_tail = y[mask].copy()
    z_tail = z[mask].copy()

    x_tail += -8.0 * logistic(t_rel, 0.35, 0.10) - 6.0 * (t_rel / duration_h)
    y_tail += +7.5 * logistic(t_rel, 0.40, 0.12) + 6.0 * (t_rel / duration_h)
    z_tail += -3.0 * logistic(t_rel, 0.32, 0.10) - 4.5 * (t_rel / duration_h)

    z_anchor = float(z_tail[0])
    z_tail = z_anchor + 0.85 * (z_tail - z_anchor)

    meta = {
        "start_hour_in_full_view": start_h,
        "duration_hours": duration_h,
        "span_nT": {
            "Bx": float(np.max(x_tail) - np.min(x_tail)),
            "By": float(np.max(y_tail) - np.min(y_tail)),
            "Bz": float(np.max(z_tail) - np.min(z_tail)),
        },
    }
    return t_rel, x_tail, y_tail, z_tail, meta


def build_figure(write_thesis: bool) -> dict[str, Path]:
    configure_fonts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    t_h, x, y, z = build_full_series()
    t_rel, x_tail, y_tail, z_tail, meta = crop_and_strengthen(t_h, x, y, z)

    fig, axes = plt.subplots(3, 1, figsize=(12.0, 8.0), sharex=True, constrained_layout=True)
    series = [
        (x_tail, "X轴", 1.0),
        (y_tail, "Y轴", 1.0),
        (z_tail, "Z轴", 1.45),
    ]

    for ax, (arr, label, pad_scale) in zip(axes, series):
        ax.plot(t_rel, arr, color="#1f77b4", linewidth=1.25, label=label)
        ax.set_ylabel("磁场强度 (nT)", fontsize=21, fontproperties=mixed_font(21))
        ax.legend(
            loc="upper right",
            fontsize=18,
            prop=mixed_font(18),
            frameon=True,
            framealpha=0.95,
            borderpad=0.35,
            handlelength=2.0,
            handletextpad=0.45,
        )
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=18, length=5.5, width=1.0)
        lo, hi = np.percentile(arr, [0.3, 99.7])
        pad = max(2.0, 0.08 * (hi - lo)) * pad_scale
        ax.set_ylim(lo - pad, hi + pad)

    axes[-1].set_xlabel("时间 (h)", fontsize=21, fontproperties=mixed_font(21))
    axes[-1].set_xlim(0, float(t_rel[-1]))

    preview = OUT_DIR / "fig_mag_drift_schematic_tail_preview.png"
    thesis = IMG_DIR / "fig_mag_drift_schematic_tail.png"
    meta_path = OUT_DIR / "fig_mag_drift_schematic_tail_meta.json"

    fig.savefig(preview, dpi=240, bbox_inches="tight")
    if write_thesis:
        fig.savefig(thesis, dpi=240, bbox_inches="tight")
    plt.close(fig)

    info = {
        "type": "schematic_tail",
        **meta,
        "font_rule": "Chinese SimSun, English Times New Roman",
        "note": "Preview first. Thesis image overwritten only when --write-thesis is passed.",
    }
    meta_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {"preview": preview, "meta": meta_path}
    if write_thesis:
        outputs["thesis"] = thesis
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chapter 2 drift schematic tail preview.")
    parser.add_argument(
        "--write-thesis",
        action="store_true",
        help="Also overwrite images/fig_mag_drift_schematic_tail.png after preview review.",
    )
    args = parser.parse_args()

    outputs = build_figure(write_thesis=args.write_thesis)
    print(f"Saved preview to: {outputs['preview']}")
    if args.write_thesis:
        print(f"Saved thesis image copy to: {outputs['thesis']}")
    else:
        print("Thesis image was not overwritten. Use --write-thesis after preview review if needed.")
    print(f"Saved meta to: {outputs['meta']}")


if __name__ == "__main__":
    main()
