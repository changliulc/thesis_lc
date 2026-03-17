from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from fit_speed_morphology_to_literature import extract_literature_targets
from generate_speed_latent_reblur_demo import (
    crop_effective_segment,
    load_vehicle_waveform,
    plot_literature_style,
    plot_overlay,
    preprocess_waveform,
    save_waveforms,
    AxisDeblurResult,
    apply_lowpass,
    build_lowpass_matrix,
    build_second_difference,
    interpolate_latent,
    plot_latent_template,
    plot_reference_fit,
    save_latent_template,
    solve_tikhonov_gcv,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
LITERATURE_IMAGE_PATH = ROOT / "tmp" / "pdfs" / "vehicle_sensor_fig7_tight_300.png"
OUTPUT_DIR = ROOT / "tmp" / "speed_latent_reblur_calibrated_demo"


@dataclass
class CalibrationResult:
    target_len: int
    knot_positions: list[float]
    global_scale: float
    coeffs: list[list[float]]
    ridge: float
    fit_rmse: float


def prepare_generated_curves(outputs: dict[float, dict[str, object]]) -> dict[float, np.ndarray]:
    curves: dict[float, np.ndarray] = {}
    for speed_kmh, item in outputs.items():
        wf = np.asarray(item["waveform_nT"], dtype=np.float64)
        tail_len = max(6, wf.shape[0] // 10)
        baseline = np.median(wf[-tail_len:], axis=0, keepdims=True)
        curves[float(speed_kmh)] = wf - baseline
    return curves


def crop_outputs(
    outputs: dict[float, dict[str, object]],
    threshold_ratio: float,
    margin_samples: int,
) -> dict[float, dict[str, object]]:
    cropped_outputs: dict[float, dict[str, object]] = {}
    for speed_kmh in sorted(outputs):
        waveform_target = np.asarray(outputs[speed_kmh]["waveform_nT"], dtype=np.float64)
        cropped_waveform, cropped_magnitude, start, end = crop_effective_segment(
            waveform_target,
            threshold_ratio=threshold_ratio,
            margin_samples=margin_samples,
        )
        cropped_outputs[speed_kmh] = {
            "speed_kmh": speed_kmh,
            "sample_spacing_m": outputs[speed_kmh]["sample_spacing_m"],
            "sample_rate_hz": outputs[speed_kmh]["sample_rate_hz"],
            "waveform_nT": cropped_waveform,
            "magnitude_nT": cropped_magnitude,
            "crop_start": int(start),
            "crop_end": int(end),
            "threshold_ratio": float(threshold_ratio),
        }
    return cropped_outputs


def resample_curve(curve: np.ndarray, target_len: int) -> np.ndarray:
    old_x = np.linspace(0.0, 1.0, curve.shape[0])
    new_x = np.linspace(0.0, 1.0, target_len)
    out = np.zeros((target_len, curve.shape[1]), dtype=np.float64)
    for axis in range(curve.shape[1]):
        out[:, axis] = np.interp(new_x, old_x, curve[:, axis])
    return out


def build_tent_basis(length: int, knot_positions: np.ndarray) -> np.ndarray:
    t = np.linspace(0.0, 1.0, length, dtype=np.float64)
    basis = np.zeros((length, knot_positions.shape[0]), dtype=np.float64)
    for idx, center in enumerate(knot_positions):
        if idx == 0:
            left = center
        else:
            left = knot_positions[idx - 1]
        if idx == knot_positions.shape[0] - 1:
            right = center
        else:
            right = knot_positions[idx + 1]

        if center > left:
            mask = (t >= left) & (t <= center)
            basis[mask, idx] = (t[mask] - left) / max(center - left, 1e-9)
        else:
            basis[t <= center, idx] = 1.0
        if right > center:
            mask = (t >= center) & (t <= right)
            basis[mask, idx] = np.maximum(
                basis[mask, idx],
                (right - t[mask]) / max(right - center, 1e-9),
            )
        else:
            basis[t >= center, idx] = 1.0
    row_sums = np.sum(basis, axis=1, keepdims=True)
    row_sums[row_sums == 0.0] = 1.0
    return basis / row_sums


def center_curve(curve: np.ndarray) -> np.ndarray:
    tail_len = max(6, curve.shape[0] // 10)
    baseline = np.median(curve[-tail_len:], axis=0, keepdims=True)
    return curve - baseline


def scale_literature_targets(
    generated: dict[float, np.ndarray],
    literature_targets: dict[float, dict[str, np.ndarray]],
) -> tuple[dict[float, np.ndarray], float]:
    ratios = []
    axis_order = ["x", "y", "z"]
    for speed_kmh in sorted(generated):
        curve = generated[speed_kmh]
        for axis_idx, axis_name in enumerate(axis_order):
            gen_peak = float(np.max(np.abs(curve[:, axis_idx])))
            lit_peak = float(np.max(np.abs(literature_targets[speed_kmh][axis_name])))
            if lit_peak > 1e-9:
                ratios.append(gen_peak / lit_peak)
    global_scale = float(np.median(ratios)) if ratios else 1.0

    scaled: dict[float, np.ndarray] = {}
    for speed_kmh in sorted(generated):
        scaled[speed_kmh] = np.column_stack(
            [
                literature_targets[speed_kmh]["x"] * global_scale,
                literature_targets[speed_kmh]["y"] * global_scale,
                literature_targets[speed_kmh]["z"] * global_scale,
            ]
        )
    return scaled, global_scale


def build_axis_design(
    base: np.ndarray,
    deriv: np.ndarray,
    scale: float,
    basis: np.ndarray,
    axis_idx: int,
) -> np.ndarray:
    local_signal = base[:, axis_idx : axis_idx + 1]
    local_deriv = deriv[:, axis_idx : axis_idx + 1]
    global_terms = np.column_stack([base, scale * base, deriv, scale * deriv])
    local_signal_terms = np.concatenate(
        [basis * local_signal, scale * basis * local_signal],
        axis=1,
    )
    local_deriv_terms = np.concatenate(
        [basis * local_deriv, scale * basis * local_deriv],
        axis=1,
    )
    return np.concatenate([global_terms, local_signal_terms, local_deriv_terms], axis=1)


def fit_speed_calibration(
    generated: dict[float, np.ndarray],
    literature_targets: dict[float, dict[str, np.ndarray]],
    target_len: int = 180,
    knot_count: int = 6,
    ridge: float = 2e-1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, CalibrationResult]:
    speeds = sorted(generated)
    speed_mid = 0.5 * (min(speeds) + max(speeds))
    speed_span = max(max(speeds) - min(speeds), 1.0)
    knot_positions = np.linspace(0.0, 1.0, knot_count, dtype=np.float64)
    basis = build_tent_basis(target_len, knot_positions)
    scaled_targets, global_scale = scale_literature_targets(generated, literature_targets)

    coeffs = []
    total_sq_error = 0.0
    total_count = 0
    for axis_idx in range(3):
        rows = []
        targets = []
        for speed_kmh in speeds:
            scale = (speed_kmh - speed_mid) / speed_span
            base = resample_curve(generated[speed_kmh], target_len)
            target = resample_curve(scaled_targets[speed_kmh], target_len)
            deriv = np.gradient(base, axis=0)
            design = build_axis_design(base, deriv, scale, basis, axis_idx)
            rows.append(design)
            targets.append(target[:, axis_idx])

        design_all = np.vstack(rows)
        target_vec = np.concatenate(targets)
        reg = np.sqrt(ridge) * np.eye(design_all.shape[1], dtype=np.float64)
        coeff = np.linalg.lstsq(
            np.vstack([design_all, reg]),
            np.concatenate([target_vec, np.zeros(design_all.shape[1], dtype=np.float64)]),
            rcond=None,
        )[0]
        pred = design_all @ coeff
        total_sq_error += float(np.sum((pred - target_vec) ** 2))
        total_count += int(target_vec.shape[0])
        coeffs.append(coeff)

    coeff_matrix = np.vstack(coeffs)
    fit_rmse = float(np.sqrt(total_sq_error / max(total_count, 1)))
    summary = CalibrationResult(
        target_len=int(target_len),
        knot_positions=knot_positions.tolist(),
        global_scale=global_scale,
        coeffs=coeff_matrix.tolist(),
        ridge=float(ridge),
        fit_rmse=fit_rmse,
    )
    return coeff_matrix, knot_positions, basis, summary


def apply_speed_calibration(
    outputs: dict[float, dict[str, object]],
    coeff_matrix: np.ndarray,
    knot_positions: np.ndarray,
) -> dict[float, dict[str, object]]:
    speeds = sorted(outputs)
    speed_mid = 0.5 * (min(speeds) + max(speeds))
    speed_span = max(max(speeds) - min(speeds), 1.0)

    calibrated: dict[float, dict[str, object]] = {}
    for speed_kmh in speeds:
        scale = (speed_kmh - speed_mid) / speed_span
        wf = center_curve(np.asarray(outputs[speed_kmh]["waveform_nT"], dtype=np.float64))
        deriv = np.gradient(wf, axis=0)
        basis = build_tent_basis(wf.shape[0], knot_positions)
        transformed = np.zeros_like(wf)
        for axis_idx in range(3):
            design = build_axis_design(wf, deriv, scale, basis, axis_idx)
            transformed[:, axis_idx] = design @ coeff_matrix[axis_idx]
        tail_len = max(6, transformed.shape[0] // 10)
        transformed = transformed - np.median(transformed[-tail_len:], axis=0, keepdims=True)
        calibrated[speed_kmh] = {**outputs[speed_kmh], "waveform_nT": transformed}
    return calibrated


def smooth_axis(signal: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return signal.copy()
    kernel = np.ones(window, dtype=np.float64) / float(window)
    return np.convolve(signal, kernel, mode="same")


def smooth_outputs(
    outputs: dict[float, dict[str, object]],
    window: int,
) -> dict[float, dict[str, object]]:
    smoothed: dict[float, dict[str, object]] = {}
    for speed_kmh, item in outputs.items():
        wf = np.asarray(item["waveform_nT"], dtype=np.float64)
        out = np.zeros_like(wf)
        for axis_idx in range(wf.shape[1]):
            out[:, axis_idx] = smooth_axis(wf[:, axis_idx], window)
        tail_len = max(6, out.shape[0] // 10)
        out = out - np.median(out[-tail_len:], axis=0, keepdims=True)
        smoothed[speed_kmh] = {
            **item,
            "samples": int(out.shape[0]),
            "waveform_nT": out,
            "magnitude_nT": np.linalg.norm(out, axis=1),
        }
    return smoothed


def build_latent_outputs(
    data_path: Path,
    sample_rate_hz: float,
    tau_ms: float,
    speeds: list[float],
    tail_len: int,
    lambda_min_exp: float,
    lambda_max_exp: float,
    lambda_steps: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[AxisDeblurResult], dict[float, dict[str, object]], dict[str, float]]:
    waveform = load_vehicle_waveform(data_path)
    observed, _, _ = preprocess_waveform(waveform, smooth_window=0, tail_len=tail_len)

    dt_s = 1.0 / sample_rate_hz
    tau_s = tau_ms / 1000.0
    a = float(np.exp(-dt_s / tau_s))

    speed_ref_mps = float(waveform.speed_kmh) / 3.6
    dx_ref = speed_ref_mps / sample_rate_hz
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
        "reference_speed_kmh": float(waveform.speed_kmh),
        "reference_spacing_m": float(dx_ref),
        "reference_center_sample": float(center_sample),
    }
    return observed, latent, reproj, axis_results, outputs, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Latent+reblur speed generation with literature-calibrated tri-axis intensity changes.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--literature-image", type=Path, default=LITERATURE_IMAGE_PATH, help="tight crop of literature Fig. 7")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--tau-ms", type=float, default=20.0, help="low-pass time constant in ms")
    parser.add_argument("--speeds", type=float, nargs="+", default=[20.0, 30.0, 40.0, 50.0], help="target speeds in km/h")
    parser.add_argument("--tail-len", type=int, default=12, help="edge length for bias removal")
    parser.add_argument("--crop-threshold-ratio", type=float, default=0.10, help="magnitude threshold ratio")
    parser.add_argument("--crop-margin-samples", type=int, default=6, help="extra samples around the effective segment")
    parser.add_argument("--lambda-min-exp", type=float, default=-3.0, help="minimum log10(lambda) for deblur search")
    parser.add_argument("--lambda-max-exp", type=float, default=2.0, help="maximum log10(lambda) for deblur search")
    parser.add_argument("--lambda-steps", type=int, default=80, help="number of lambda candidates")
    parser.add_argument("--knot-count", type=int, default=5, help="number of local basis functions for calibration")
    parser.add_argument("--calib-ridge", type=float, default=0.3, help="ridge coefficient for literature calibration")
    parser.add_argument("--smooth-window", type=int, default=7, help="moving-average window after local calibration")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    args = parser.parse_args()

    speeds = [float(x) for x in args.speeds]
    literature_targets = extract_literature_targets(args.literature_image)
    observed, latent, reproj, axis_results, base_outputs, meta = build_latent_outputs(
        data_path=args.data,
        sample_rate_hz=float(args.sample_rate),
        tau_ms=float(args.tau_ms),
        speeds=speeds,
        tail_len=int(args.tail_len),
        lambda_min_exp=float(args.lambda_min_exp),
        lambda_max_exp=float(args.lambda_max_exp),
        lambda_steps=int(args.lambda_steps),
    )

    base_cropped = crop_outputs(
        base_outputs,
        threshold_ratio=float(args.crop_threshold_ratio),
        margin_samples=int(args.crop_margin_samples),
    )
    generated_curves = prepare_generated_curves(base_cropped)
    coeff_matrix, knot_positions, _, calib_result = fit_speed_calibration(
        generated=generated_curves,
        literature_targets=literature_targets,
        knot_count=int(args.knot_count),
        ridge=float(args.calib_ridge),
    )
    calibrated_cropped = apply_speed_calibration(base_cropped, coeff_matrix, knot_positions)
    cropped_outputs = smooth_outputs(calibrated_cropped, window=int(args.smooth_window))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_waveforms(cropped_outputs, cropped_outputs, args.output_dir)
    save_latent_template(meta["reference_spacing_m"] * (np.arange(observed.shape[0]) - meta["reference_center_sample"]), latent, reproj, observed, args.output_dir)
    plot_reference_fit(observed, reproj, latent, args.output_dir)
    plot_latent_template(meta["reference_spacing_m"] * (np.arange(observed.shape[0]) - meta["reference_center_sample"]), latent, args.output_dir)
    plot_literature_style(cropped_outputs, args.output_dir)
    plot_overlay(cropped_outputs, args.output_dir)

    payload = {
        "data": str(args.data),
        "literature_image": str(args.literature_image),
        "sample_rate_hz": float(args.sample_rate),
        "tau_ms": float(args.tau_ms),
        "target_speeds_kmh": speeds,
        "crop_threshold_ratio": float(args.crop_threshold_ratio),
        "crop_margin_samples": int(args.crop_margin_samples),
        "knot_count": int(args.knot_count),
        "smooth_window": int(args.smooth_window),
        "axis_deblur": [asdict(item) for item in axis_results],
        "latent_meta": meta,
        "calibration": asdict(calib_result),
    }
    (args.output_dir / "generation_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Calibration fit RMSE: {calib_result.fit_rmse:.6f}")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
