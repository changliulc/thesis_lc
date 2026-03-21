#!/usr/bin/env python3
"""
Create a cropped schematic drift figure for Chapter 2.

Design goals from discussion:
- follow the senior's clean long-run raw-drift style
- crop from the Z-axis peak / Y-axis trough region
- show about 2.5 h after that point
- keep Chinese labels rendered correctly
- make the visible drift a bit stronger (roughly around 30 nT order)

This is still a schematic / style mockup, not measured data.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch2_mag_drift_refresh"
IMG_DIR = REPO_ROOT / "images"

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


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

    # Compress Z slightly so its span is about 10 nT smaller.
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    t_h, x, y, z = build_full_series()
    t_rel, x_tail, y_tail, z_tail, meta = crop_and_strengthen(t_h, x, y, z)

    fig, axes = plt.subplots(3, 1, figsize=(11.8, 7.0), sharex=True, constrained_layout=True)
    series = [
        (x_tail, "X轴", 1.0),
        (y_tail, "Y轴", 1.0),
        (z_tail, "Z轴", 1.45),
    ]

    for ax, (arr, label, pad_scale) in zip(axes, series):
        ax.plot(t_rel, arr, color="#1f77b4", linewidth=0.95, label=label)
        ax.set_ylabel("磁场强度(nT)", fontsize=12)
        ax.legend(loc="upper right", fontsize=10, frameon=True)
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=10)
        lo, hi = np.percentile(arr, [0.3, 99.7])
        pad = max(2.0, 0.08 * (hi - lo)) * pad_scale
        ax.set_ylim(lo - pad, hi + pad)

    axes[-1].set_xlabel("时间(h)", fontsize=12)
    axes[-1].set_xlim(0, float(t_rel[-1]))

    preview = OUT_DIR / "fig_mag_drift_schematic_tail_preview.png"
    thesis = IMG_DIR / "fig_mag_drift_schematic_tail.png"
    fig.savefig(preview, dpi=220, bbox_inches="tight")
    fig.savefig(thesis, dpi=220, bbox_inches="tight")
    plt.close(fig)

    info = {
        "type": "schematic_tail",
        **meta,
        "note": "Cropped from Z-peak region, 2.5 h shown, labels fixed in UTF-8.",
    }
    (OUT_DIR / "fig_mag_drift_schematic_tail_meta.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Saved preview to: {preview}")
    print(f"Saved thesis image copy to: {thesis}")
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
