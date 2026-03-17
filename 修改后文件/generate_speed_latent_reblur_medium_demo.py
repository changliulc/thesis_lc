from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from generate_speed_latent_reblur_demo import (
    AxisDeblurResult,
    apply_lowpass,
    build_lowpass_matrix,
    build_second_difference,
    crop_effective_segment,
    interpolate_latent,
    plot_latent_template,
    plot_literature_style,
    plot_overlay,
    plot_reference_fit,
    save_latent_template,
    save_waveforms,
    solve_tikhonov_gcv,
)
from medium_segment_utils import (
    MEDIUM_DATA_PATH,
    SPEED_EST_PATH,
    get_medium_segment,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "tmp" / "speed_latent_reblur_medium_segment1_demo"


def preprocess_delta_signal(
    delta_xyz: np.ndarray,
    tail_len: int,
    anchor_ends: bool = True,
    pad_samples: int = 10,
) -> np.ndarray:
    signal = np.asarray(delta_xyz, dtype=np.float64)
    tail_len = min(tail_len, max(1, signal.shape[0] // 4))
    if anchor_ends:
        start_level = np.median(signal[:tail_len], axis=0)
        end_level = np.median(signal[-tail_len:], axis=0)
        t = np.linspace(0.0, 1.0, signal.shape[0], dtype=np.float64)[:, None]
        baseline = (1.0 - t) * start_level[None, :] + t * end_level[None, :]
        signal = signal - baseline
    else:
        edge = np.vstack([signal[:tail_len], signal[-tail_len:]])
        bias = np.median(edge, axis=0, keepdims=True)
        signal = signal - bias

    if pad_samples > 0:
        pad = np.zeros((pad_samples, signal.shape[1]), dtype=np.float64)
        signal = np.vstack([pad, signal, pad])
    return signal


def build_outputs(
    observed: np.ndarray,
    reference_speed_kmh: float,
    sample_rate_hz: float,
    tau_ms: float,
    speeds: list[float],
    lambda_min_exp: float,
    lambda_max_exp: float,
    lambda_steps: int,
) -> tuple[np.ndarray, np.ndarray, list[AxisDeblurResult], dict[float, dict[str, object]], dict[str, float]]:
    dt_s = 1.0 / sample_rate_hz
    tau_s = tau_ms / 1000.0
    a = float(np.exp(-dt_s / tau_s))
    dx_ref = (reference_speed_kmh / 3.6) / sample_rate_hz

    mag = np.linalg.norm(observed, axis=1)
    center_sample = float(np.sum(np.arange(observed.shape[0], dtype=np.float64) * mag) / np.sum(mag))
    x_ref = (np.arange(observed.shape[0], dtype=np.float64) - center_sample) * dx_ref

    lowpass_ref = build_lowpass_matrix(observed.shape[0], a)
    diff_matrix = build_second_difference(observed.shape[0])
    lambdas = np.logspace(lambda_min_exp, lambda_max_exp, lambda_steps)

    latent = np.zeros_like(observed)
    reproj = np.zeros_like(observed)
    axis_results: list[AxisDeblurResult] = []
    for axis_idx, axis_name in enumerate(["X", "Y", "Z"]):
        latent_axis, axis_result = solve_tikhonov_gcv(
            observed=observed[:, axis_idx],
            lowpass_matrix=lowpass_ref,
            diff_matrix=diff_matrix,
            lambdas=lambdas,
        )
        latent[:, axis_idx] = latent_axis
        reproj[:, axis_idx] = lowpass_ref @ latent_axis
        axis_result.axis = axis_name
        axis_result.ref_rmse = float(np.sqrt(np.mean((observed[:, axis_idx] - reproj[:, axis_idx]) ** 2)))
        axis_results.append(axis_result)

    x_min = float(x_ref[0])
    x_max = float(x_ref[-1])
    outputs: dict[float, dict[str, object]] = {}
    for speed_kmh in speeds:
        dx_target = (speed_kmh / 3.6) / sample_rate_hz
        sample_count = int(np.ceil((x_max - x_min) / dx_target)) + 1
        x_target = x_min + dx_target * np.arange(sample_count, dtype=np.float64)
        latent_target = interpolate_latent(x_ref, latent, x_target)
        waveform_target = np.zeros_like(latent_target)
        for axis_idx in range(3):
            waveform_target[:, axis_idx] = apply_lowpass(latent_target[:, axis_idx], a)
        outputs[float(speed_kmh)] = {
            "speed_kmh": float(speed_kmh),
            "sample_spacing_m": float(dx_target),
            "sample_rate_hz": float(sample_rate_hz),
            "samples": int(sample_count),
            "waveform_nT": waveform_target,
            "x_m": x_target,
        }

    meta = {
        "dt_s": dt_s,
        "tau_s": tau_s,
        "alpha_exact": float(1.0 - a),
        "pole_a": a,
        "reference_speed_kmh": float(reference_speed_kmh),
        "reference_spacing_m": float(dx_ref),
        "reference_center_sample": float(center_sample),
    }
    return latent, reproj, axis_results, outputs, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate speed-effect figure from one segment in the medium-vehicle workbook.")
    parser.add_argument("--medium-data", type=Path, default=MEDIUM_DATA_PATH, help="path to 中型车数据.xlsx")
    parser.add_argument("--speed-est", type=Path, default=SPEED_EST_PATH, help="path to 估计速度.xlsx")
    parser.add_argument("--segment-index", type=int, default=1, help="1-based segment index inside the medium-vehicle workbook")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--tau-ms", type=float, default=20.0, help="low-pass time constant in ms")
    parser.add_argument("--speeds", type=float, nargs="+", default=[20.0, 30.0, 40.0, 50.0], help="target speeds in km/h")
    parser.add_argument("--tail-len", type=int, default=12, help="edge length for bias removal")
    parser.add_argument("--anchor-ends", action="store_true", default=True, help="force the first and last edge levels toward zero with an affine baseline")
    parser.add_argument("--no-anchor-ends", dest="anchor_ends", action="store_false", help="disable endpoint anchoring")
    parser.add_argument("--pad-samples", type=int, default=10, help="number of zero samples padded at both ends")
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
    observed = preprocess_delta_signal(
        segment.delta_xyz,
        tail_len=int(args.tail_len),
        anchor_ends=bool(args.anchor_ends),
        pad_samples=int(args.pad_samples),
    )
    latent, reproj, axis_results, full_outputs, meta = build_outputs(
        observed=observed,
        reference_speed_kmh=float(segment.speed_kmh),
        sample_rate_hz=float(args.sample_rate),
        tau_ms=float(args.tau_ms),
        speeds=[float(x) for x in args.speeds],
        lambda_min_exp=float(args.lambda_min_exp),
        lambda_max_exp=float(args.lambda_max_exp),
        lambda_steps=int(args.lambda_steps),
    )

    cropped_outputs: dict[float, dict[str, object]] = {}
    for speed_kmh, item in full_outputs.items():
        cropped_waveform, cropped_magnitude, start, end = crop_effective_segment(
            np.asarray(item["waveform_nT"], dtype=np.float64),
            threshold_ratio=float(args.crop_threshold_ratio),
            margin_samples=int(args.crop_margin_samples),
        )
        cropped_outputs[speed_kmh] = {
            "speed_kmh": float(speed_kmh),
            "sample_spacing_m": item["sample_spacing_m"],
            "sample_rate_hz": item["sample_rate_hz"],
            "waveform_nT": cropped_waveform,
            "magnitude_nT": cropped_magnitude,
            "crop_start": int(start),
            "crop_end": int(end),
            "threshold_ratio": float(args.crop_threshold_ratio),
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_waveforms(full_outputs, cropped_outputs, args.output_dir)
    x_ref = meta["reference_spacing_m"] * (np.arange(observed.shape[0]) - meta["reference_center_sample"])
    save_latent_template(x_ref, latent, reproj, observed, args.output_dir)
    plot_reference_fit(observed, reproj, latent, args.output_dir)
    plot_latent_template(x_ref, latent, args.output_dir)
    plot_literature_style(cropped_outputs, args.output_dir)
    plot_overlay(cropped_outputs, args.output_dir)

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
        "anchor_ends": bool(args.anchor_ends),
        "pad_samples": int(args.pad_samples),
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
    main()
