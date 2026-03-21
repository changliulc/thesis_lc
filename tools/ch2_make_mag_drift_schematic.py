#!/usr/bin/env python3
"""
Create a schematic Chapter-2 magnetic drift figure that visually follows
the senior's long-run raw drift style.

Important:
- This is a style mockup /示意版, not a measured-data figure.
- Keep it separate from the real-data figure until explicitly approved.
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(20260320)

    total_h = 15.0
    dt_sec = 5.0
    n = int(round(total_h * 3600.0 / dt_sec))
    t_h = np.arange(n) * dt_sec / 3600.0

    # X axis: early decay, mid stable segment, small hump around 11 h, late mild recovery
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

    # Y axis: gentle rise first, long downward drift, dip at ~11.2 h, then partial recovery
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

    # Z axis: noisy band, early drop, mild upward drift, strong bump around 11 h, then decay
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

    fig, axes = plt.subplots(3, 1, figsize=(11.8, 7.2), sharex=True, constrained_layout=True)
    labels = ["X轴", "Y轴", "Z轴"]
    arrays = [x, y, z]

    for ax, arr, lab in zip(axes, arrays, labels):
        ax.plot(t_h, arr, color="#1f77b4", linewidth=0.95, label=lab)
        ax.set_ylabel("磁场强度(nT)", fontsize=12)
        ax.legend(loc="upper right", fontsize=10, frameon=True)
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=10)
        lo, hi = np.percentile(arr, [0.3, 99.7])
        pad = max(2.0, 0.08 * (hi - lo))
        ax.set_ylim(lo - pad, hi + pad)

    axes[-1].set_xlabel("时间(h)", fontsize=12)
    axes[-1].set_xlim(0, total_h)

    preview = OUT_DIR / "fig_mag_drift_schematic_15h_preview.png"
    thesis = IMG_DIR / "fig_mag_drift_schematic_15h.png"
    fig.savefig(preview, dpi=220, bbox_inches="tight")
    fig.savefig(thesis, dpi=220, bbox_inches="tight")
    plt.close(fig)

    meta = {
        "type": "schematic",
        "duration_hours": total_h,
        "dt_sec": dt_sec,
        "span_nT": {
            "Bx": float(np.max(x) - np.min(x)),
            "By": float(np.max(y) - np.min(y)),
            "Bz": float(np.max(z) - np.min(z)),
        },
        "note": "Style mockup following senior's long-run drift figure; not measured data.",
    }
    (OUT_DIR / "fig_mag_drift_schematic_15h_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Saved preview to: {preview}")
    print(f"Saved thesis image copy to: {thesis}")


if __name__ == "__main__":
    main()
