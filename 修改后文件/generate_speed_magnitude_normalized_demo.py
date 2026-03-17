from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from generate_speed_latent_reblur_demo import crop_effective_segment
from generate_speed_latent_reblur_medium_demo import build_outputs, preprocess_delta_signal
from medium_segment_utils import MEDIUM_DATA_PATH, SPEED_EST_PATH, get_medium_segment


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "tmp" / "speed_magnitude_normalized_demo"


def save_summary(
    magnitudes: dict[float, np.ndarray],
    cropped_waveforms: dict[float, np.ndarray],
    output_dir: Path,
) -> None:
    lines = ["speed_kmh,samples,max_magnitude_nT"]
    for speed_kmh in sorted(magnitudes):
        mag = magnitudes[speed_kmh]
        wave = cropped_waveforms[speed_kmh]
        lines.append(f"{speed_kmh:.1f},{wave.shape[0]},{float(np.max(np.linalg.norm(wave, axis=1))):.8f}")
    (output_dir / "magnitude_summary.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_curves(
    magnitudes: dict[float, np.ndarray],
    cropped_waveforms: dict[float, np.ndarray],
    output_dir: Path,
) -> None:
    for speed_kmh in sorted(magnitudes):
        mag = magnitudes[speed_kmh]
        wave = cropped_waveforms[speed_kmh]
        rows = ["local_sample,normalized_magnitude,x_nT,y_nT,z_nT"]
        for idx in range(mag.shape[0]):
            rows.append(
                f"{idx},{mag[idx]:.8f},{wave[idx,0]:.8f},{wave[idx,1]:.8f},{wave[idx,2]:.8f}"
            )
        (output_dir / f"normalized_magnitude_{int(round(speed_kmh))}kmh.csv").write_text(
            "\n".join(rows) + "\n",
            encoding="utf-8",
        )


def plot_overlay(magnitudes: dict[float, np.ndarray], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    colors = ["#2ca02c", "#1f77b4", "#d627cf", "#ff7f0e", "#17becf"]
    for idx, speed_kmh in enumerate(sorted(magnitudes)):
        mag = magnitudes[speed_kmh]
        ax.plot(
            np.arange(mag.shape[0], dtype=np.float64),
            mag,
            lw=2.3,
            color=colors[idx % len(colors)],
            label=f"{int(round(speed_kmh))} km/h",
        )

    base_y = 0.10
    for idx, speed_kmh in enumerate(sorted(magnitudes)):
        mag = magnitudes[speed_kmh]
        y = base_y - 0.03 * idx
        ax.hlines(y, 0, mag.shape[0], color="#555555", lw=1.2)
        ax.text(
            mag.shape[0] + 2,
            y,
            f"length at {int(round(speed_kmh))} km/h",
            va="center",
            ha="left",
            fontsize=9,
            color="#444444",
        )

    ax.set_xlim(0, max(m.shape[0] for m in magnitudes.values()) + 40)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("samples")
    ax.set_ylabel("Normalized magnitude of magnetic field")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_dir / "normalized_magnitude_overlay.png", dpi=220)
    plt.close(fig)


def plot_literature_style(magnitudes: dict[float, np.ndarray], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    colors = ["#2ca02c", "#1f77b4", "#d627cf", "#ff7f0e", "#17becf"]
    linestyles = ["--", "-.", ":", "-"]

    for idx, speed_kmh in enumerate(sorted(magnitudes)):
        mag = magnitudes[speed_kmh]
        ax.plot(
            np.arange(mag.shape[0], dtype=np.float64),
            mag,
            lw=2.4,
            color=colors[idx % len(colors)],
            linestyle=linestyles[idx % len(linestyles)],
            label=f"{int(round(speed_kmh))} km/h",
        )

    ordered = sorted(magnitudes)
    base_y = 0.11
    for idx, speed_kmh in enumerate(ordered):
        mag = magnitudes[speed_kmh]
        y = base_y - 0.035 * idx
        ax.annotate(
            "",
            xy=(mag.shape[0], y),
            xytext=(0, y),
            arrowprops=dict(arrowstyle="-|>", color="#666666", lw=1.0),
        )
        ax.text(
            max(2, mag.shape[0] * 0.04),
            y + 0.012,
            f"length at {int(round(speed_kmh))} km/h",
            fontsize=9,
            color="#444444",
        )

    ax.set_xlim(0, max(m.shape[0] for m in magnitudes.values()) + 45)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("samples")
    ax.set_ylabel("Normalized magnitude of magnetic field")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_dir / "normalized_magnitude_literature_style.png", dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate same-vehicle speed-effect curves in normalized magnitude form.")
    parser.add_argument("--medium-data", type=Path, default=MEDIUM_DATA_PATH, help="path to 中型车数据.xlsx")
    parser.add_argument("--speed-est", type=Path, default=SPEED_EST_PATH, help="path to 估计速度.xlsx")
    parser.add_argument("--segment-index", type=int, default=1, help="1-based segment index inside the medium-vehicle workbook")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--tau-ms", type=float, default=20.0, help="low-pass time constant in ms")
    parser.add_argument("--speeds", type=float, nargs="+", default=[30.0, 50.0, 70.0], help="target speeds in km/h")
    parser.add_argument("--tail-len", type=int, default=12, help="edge length for bias removal")
    parser.add_argument("--crop-threshold-ratio", type=float, default=0.10, help="magnitude threshold ratio")
    parser.add_argument("--crop-margin-samples", type=int, default=6, help="extra samples around the effective segment")
    parser.add_argument("--lambda-min-exp", type=float, default=-3.0, help="minimum log10(lambda) for deblur search")
    parser.add_argument("--lambda-max-exp", type=float, default=2.0, help="maximum log10(lambda) for deblur search")
    parser.add_argument("--lambda-steps", type=int, default=80, help="number of lambda candidates")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    args = parser.parse_args()

    segment = get_medium_segment(
        segment_index=int(args.segment_index),
        data_path=args.medium_data,
        speed_path=args.speed_est,
    )
    observed = preprocess_delta_signal(segment.delta_xyz, tail_len=int(args.tail_len))
    _, _, axis_results, full_outputs, meta = build_outputs(
        observed=observed,
        reference_speed_kmh=float(segment.speed_kmh),
        sample_rate_hz=float(args.sample_rate),
        tau_ms=float(args.tau_ms),
        speeds=[float(x) for x in args.speeds],
        lambda_min_exp=float(args.lambda_min_exp),
        lambda_max_exp=float(args.lambda_max_exp),
        lambda_steps=int(args.lambda_steps),
    )

    cropped_waveforms: dict[float, np.ndarray] = {}
    normalized_magnitudes: dict[float, np.ndarray] = {}
    for speed_kmh, item in full_outputs.items():
        cropped_waveform, _, _, _ = crop_effective_segment(
            np.asarray(item["waveform_nT"], dtype=np.float64),
            threshold_ratio=float(args.crop_threshold_ratio),
            margin_samples=int(args.crop_margin_samples),
        )
        mag = np.linalg.norm(cropped_waveform, axis=1)
        mag = mag / max(float(np.max(mag)), 1e-9)
        cropped_waveforms[speed_kmh] = cropped_waveform
        normalized_magnitudes[speed_kmh] = mag

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_summary(normalized_magnitudes, cropped_waveforms, args.output_dir)
    save_curves(normalized_magnitudes, cropped_waveforms, args.output_dir)
    plot_overlay(normalized_magnitudes, args.output_dir)
    plot_literature_style(normalized_magnitudes, args.output_dir)

    payload = {
        "medium_data": str(args.medium_data),
        "speed_est": str(args.speed_est),
        "segment_index": int(segment.index),
        "segment_name": segment.name,
        "segment_description": segment.description,
        "reference_speed_kmh": float(segment.speed_kmh),
        "sample_rate_hz": float(args.sample_rate),
        "tau_ms": float(args.tau_ms),
        "target_speeds_kmh": [float(x) for x in args.speeds],
        "crop_threshold_ratio": float(args.crop_threshold_ratio),
        "crop_margin_samples": int(args.crop_margin_samples),
        "axis_deblur": [asdict(item) for item in axis_results],
        "latent_meta": meta,
    }
    (args.output_dir / "generation_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Segment: {segment.name} ({segment.description})")
    print(f"Reference speed: {segment.speed_kmh:.4f} km/h")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    from dataclasses import asdict

    main()
