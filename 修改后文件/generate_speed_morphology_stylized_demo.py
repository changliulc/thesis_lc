from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from dipole_fit_experiment import load_vehicle_waveform
from fit_speed_morphology_to_literature import extract_literature_targets
from generate_dipole_speed_morphology_demo import (
    MorphologyParams,
    generate_waveforms,
    load_best_model,
    plot_literature_style,
    plot_overlay,
    save_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
FIT_RESULTS_PATH = ROOT / "tmp" / "dipole_fit_fixed_50hz_6dipole" / "fit_results.json"
LITERATURE_IMAGE_PATH = ROOT / "tmp" / "pdfs" / "vehicle_sensor_fig7_tight_300.png"
LITFIT_CONFIG_PATH = ROOT / "tmp" / "dipole_speed_morphology_litfit" / "literature_fit_config.json"
OUTPUT_DIR = ROOT / "tmp" / "dipole_speed_morphology_stylized"


def load_morphology_params(path: Path) -> MorphologyParams:
    payload = json.loads(path.read_text(encoding="utf-8"))
    params = payload["morphology_params"]
    return MorphologyParams(**params)


def normalize_axis_group(curves: dict[float, np.ndarray]) -> tuple[dict[float, np.ndarray], float]:
    scale = max(float(np.max(np.abs(curves[speed]))) for speed in curves)
    scale = max(scale, 1e-9)
    return {speed: curves[speed] / scale for speed in curves}, scale


def prepare_axis_curves(outputs: dict[float, dict[str, object]], axis_idx: int) -> dict[float, np.ndarray]:
    curves: dict[float, np.ndarray] = {}
    for speed_kmh, item in outputs.items():
        wf = np.asarray(item["cropped_waveform_nT"], dtype=np.float64)
        signal = wf[:, axis_idx]
        tail_len = max(6, wf.shape[0] // 10)
        baseline = float(np.median(signal[-tail_len:]))
        curves[float(speed_kmh)] = signal - baseline
    return curves


def gaussian_basis(u: np.ndarray, center: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((u - center) / width) ** 2)


def fit_axis_stylization(
    base_curves: dict[float, np.ndarray],
    target_curves: dict[float, np.ndarray],
    speeds: list[float],
    axis_name: str,
    ridge: float = 0.08,
) -> dict[str, object]:
    base_norm, base_scale = normalize_axis_group(base_curves)
    target_norm, _ = normalize_axis_group(target_curves)

    speed_mid = 0.5 * (min(speeds) + max(speeds))
    speed_span = max(max(speeds) - min(speeds), 1.0)

    if axis_name == "x":
        centers = [0.18, 0.32, 0.58]
        widths = [0.05, 0.06, 0.12]
        ridge = 0.55
    elif axis_name == "y":
        centers = [0.14, 0.26, 0.44]
        widths = [0.05, 0.05, 0.08]
        ridge = 0.40
    else:
        centers = [0.16, 0.34, 0.54]
        widths = [0.05, 0.07, 0.10]
        ridge = 0.45

    design_rows = []
    targets = []
    curve_meta = []
    feature_count = len(centers) * 2
    for speed_kmh in speeds:
        base = base_norm[speed_kmh]
        target = target_norm[speed_kmh]
        n = base.shape[0]
        target_resampled = np.interp(np.linspace(0.0, 1.0, n), np.linspace(0.0, 1.0, target.shape[0]), target)
        u = np.linspace(0.0, 1.0, n)
        scale = (speed_kmh - speed_mid) / speed_span
        basis = []
        for center, width in zip(centers, widths):
            g = gaussian_basis(u, center, width)
            basis.append(g)
            basis.append(g * scale)
        A = np.column_stack(basis)
        design_rows.append(A)
        targets.append(target_resampled - base)
        curve_meta.append((speed_kmh, n))

    A_all = np.vstack(design_rows)
    y_all = np.concatenate(targets)
    reg = np.sqrt(ridge) * np.eye(feature_count)
    coeffs = np.linalg.lstsq(np.vstack([A_all, reg]), np.concatenate([y_all, np.zeros(feature_count)]), rcond=None)[0]

    return {
        "coefficients": coeffs.tolist(),
        "base_scale": float(base_scale),
        "speed_mid": float(speed_mid),
        "speed_span": float(speed_span),
        "centers": centers,
        "widths": widths,
    }


def apply_axis_stylization_model(
    base_curves: dict[float, np.ndarray],
    model: dict[str, object],
) -> dict[float, np.ndarray]:
    base_norm, base_scale = normalize_axis_group(base_curves)
    coeffs = np.asarray(model["coefficients"], dtype=np.float64)
    centers = list(model["centers"])
    widths = list(model["widths"])
    speed_mid = float(model["speed_mid"])
    speed_span = max(float(model["speed_span"]), 1.0)

    stylized: dict[float, np.ndarray] = {}
    for speed_kmh in sorted(base_curves):
        base = base_norm[speed_kmh]
        n = base.shape[0]
        u = np.linspace(0.0, 1.0, n)
        scale = (speed_kmh - speed_mid) / speed_span
        delta = np.zeros(n, dtype=np.float64)
        idx = 0
        for center, width in zip(centers, widths):
            g = gaussian_basis(u, center, width)
            delta += coeffs[idx] * g
            delta += coeffs[idx + 1] * g * scale
            idx += 2
        stylized[speed_kmh] = (base + delta) * base_scale
    return stylized


def apply_stylization(
    fit_outputs: dict[float, dict[str, object]],
    target_outputs: dict[float, dict[str, object]],
    literature_targets: dict[float, dict[str, np.ndarray]],
) -> tuple[dict[float, dict[str, object]], dict[str, object]]:
    fit_speeds = sorted(fit_outputs)
    target_speeds = sorted(target_outputs)
    stylized_axes: dict[str, dict[float, np.ndarray]] = {}
    axis_diagnostics: dict[str, object] = {}

    for axis_name, axis_idx in zip(["x", "y", "z"], [0, 1, 2]):
        fit_base_curves = prepare_axis_curves(fit_outputs, axis_idx)
        target_curves = {speed: literature_targets[speed][axis_name] for speed in fit_speeds}
        model = fit_axis_stylization(fit_base_curves, target_curves, fit_speeds, axis_name=axis_name)
        target_base_curves = prepare_axis_curves(target_outputs, axis_idx)
        stylized_axes[axis_name] = apply_axis_stylization_model(target_base_curves, model)
        axis_diagnostics[axis_name] = model

    result: dict[float, dict[str, object]] = {}
    for speed_kmh in target_speeds:
        wf = np.asarray(target_outputs[speed_kmh]["cropped_waveform_nT"], dtype=np.float64).copy()
        for axis_name, axis_idx in zip(["x", "y", "z"], [0, 1, 2]):
            signal = stylized_axes[axis_name][speed_kmh]
            tail_len = max(6, wf.shape[0] // 10)
            baseline = float(np.median(wf[-tail_len:, axis_idx]))
            wf[:, axis_idx] = signal + baseline
        item = dict(target_outputs[speed_kmh])
        item["cropped_waveform_nT"] = wf
        item["peak_abs_xyz"] = np.max(np.abs(wf), axis=0).tolist()
        result[speed_kmh] = item
    return result, axis_diagnostics


def warp_signal(signal: np.ndarray, shift: np.ndarray) -> np.ndarray:
    u = np.linspace(0.0, 1.0, signal.shape[0], dtype=np.float64)
    sample_u = np.clip(u + shift, 0.0, 1.0)
    return np.interp(sample_u, u, signal)


def speed_shape_postprocess(
    outputs: dict[float, dict[str, object]],
    axis_gain_drop: tuple[float, float, float] = (0.18, 0.32, 0.20),
    local_shape_strength: float = 1.0,
) -> tuple[dict[float, dict[str, object]], dict[str, object]]:
    speeds = sorted(outputs)
    min_speed = min(speeds)
    max_speed = max(speeds)
    speed_span = max(max_speed - min_speed, 1.0)

    diagnostics: dict[str, object] = {
        "axis_gain_drop": {
            "x": float(axis_gain_drop[0]),
            "y": float(axis_gain_drop[1]),
            "z": float(axis_gain_drop[2]),
        },
        "local_shape_strength": float(local_shape_strength),
    }
    result: dict[float, dict[str, object]] = {}

    for speed_kmh in speeds:
        speed_unit = (speed_kmh - min_speed) / speed_span
        wf = np.asarray(outputs[speed_kmh]["cropped_waveform_nT"], dtype=np.float64).copy()
        u = np.linspace(0.0, 1.0, wf.shape[0], dtype=np.float64)

        tail_len = max(6, wf.shape[0] // 10)
        baseline = np.median(wf[-tail_len:], axis=0, keepdims=True)
        centered = wf - baseline

        axis_params = {
            "x": {
                "gain": 1.0 - axis_gain_drop[0] * speed_unit,
                "env": (-0.10 * gaussian_basis(u, 0.18, 0.05) + 0.12 * gaussian_basis(u, 0.56, 0.11)),
                "warp": 0.030 * (gaussian_basis(u, 0.26, 0.08) - 0.70 * gaussian_basis(u, 0.58, 0.13)),
            },
            "y": {
                "gain": 1.0 - axis_gain_drop[1] * speed_unit,
                "env": (0.14 * gaussian_basis(u, 0.16, 0.05) - 0.18 * gaussian_basis(u, 0.42, 0.10)),
                "warp": 0.022 * (gaussian_basis(u, 0.20, 0.07) - gaussian_basis(u, 0.45, 0.11)),
            },
            "z": {
                "gain": 1.0 - axis_gain_drop[2] * speed_unit,
                "env": (0.12 * gaussian_basis(u, 0.14, 0.05) - 0.10 * gaussian_basis(u, 0.38, 0.09) + 0.08 * gaussian_basis(u, 0.68, 0.12)),
                "warp": 0.026 * (gaussian_basis(u, 0.18, 0.07) - 0.75 * gaussian_basis(u, 0.48, 0.12)),
            },
        }

        for axis_name, axis_idx in zip(["x", "y", "z"], [0, 1, 2]):
            params = axis_params[axis_name]
            signal = centered[:, axis_idx]
            warped = warp_signal(signal, local_shape_strength * speed_unit * params["warp"])
            modulated = warped * (1.0 + local_shape_strength * speed_unit * params["env"])
            centered[:, axis_idx] = params["gain"] * modulated

        wf_new = centered + baseline
        item = dict(outputs[speed_kmh])
        item["cropped_waveform_nT"] = wf_new
        item["peak_abs_xyz"] = np.max(np.abs(wf_new), axis=0).tolist()
        result[speed_kmh] = item

    diagnostics["peak_abs_xyz"] = {str(int(s)): result[s]["peak_abs_xyz"] for s in speeds}
    return result, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a stylized literature-like speed figure from the fitted dipole model.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--fit-results", type=Path, default=FIT_RESULTS_PATH, help="fit_results.json from the selected dipole model")
    parser.add_argument("--literature-image", type=Path, default=LITERATURE_IMAGE_PATH, help="cropped Fig. 7 PNG")
    parser.add_argument("--base-config", type=Path, default=LITFIT_CONFIG_PATH, help="literature-fit config json used as the physical base")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--target-speeds", type=float, nargs="+", default=[20.0, 40.0, 60.0], help="target speeds for final figure")
    parser.add_argument("--threshold-ratio", type=float, default=0.10, help="cropping threshold ratio")
    parser.add_argument("--margin-samples", type=int, default=6, help="extra samples around the effective segment")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    parser.add_argument("--axis-gain-drop-x", type=float, default=0.14, help="relative X-axis attenuation from low speed to high speed")
    parser.add_argument("--axis-gain-drop-y", type=float, default=0.65, help="relative Y-axis attenuation from low speed to high speed")
    parser.add_argument("--axis-gain-drop-z", type=float, default=0.42, help="relative Z-axis attenuation from low speed to high speed")
    parser.add_argument("--local-shape-strength", type=float, default=0.75, help="strength of local speed-dependent peak/valley modulation")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    model = load_best_model(args.fit_results)
    base_params = load_morphology_params(args.base_config)
    literature_targets = extract_literature_targets(args.literature_image)
    fit_speeds = sorted(literature_targets)
    target_speeds = [float(x) for x in args.target_speeds]

    fit_outputs = generate_waveforms(
        model=model,
        reference_speed_kmh=float(waveform.speed_kmh),
        reference_samples=int(waveform.delta_xyz.shape[0]),
        sample_rate_hz=args.sample_rate,
        target_speeds_kmh=fit_speeds,
        params=base_params,
        threshold_ratio=args.threshold_ratio,
        margin_samples=args.margin_samples,
    )
    target_outputs = generate_waveforms(
        model=model,
        reference_speed_kmh=float(waveform.speed_kmh),
        reference_samples=int(waveform.delta_xyz.shape[0]),
        sample_rate_hz=args.sample_rate,
        target_speeds_kmh=target_speeds,
        params=base_params,
        threshold_ratio=args.threshold_ratio,
        margin_samples=args.margin_samples,
    )

    stylized_outputs, stylization_diag = apply_stylization(fit_outputs, target_outputs, literature_targets)
    stylized_outputs, post_diag = speed_shape_postprocess(
        stylized_outputs,
        axis_gain_drop=(
            float(args.axis_gain_drop_x),
            float(args.axis_gain_drop_y),
            float(args.axis_gain_drop_z),
        ),
        local_shape_strength=float(args.local_shape_strength),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_outputs(stylized_outputs, args.output_dir)
    plot_literature_style(stylized_outputs, args.output_dir)
    plot_overlay(stylized_outputs, args.output_dir)

    payload = {
        "data": str(args.data),
        "fit_results": str(args.fit_results),
        "literature_image": str(args.literature_image),
        "base_config": str(args.base_config),
        "sample_rate_hz": float(args.sample_rate),
        "fit_speeds_kmh": fit_speeds,
        "target_speeds_kmh": target_speeds,
        "threshold_ratio": float(args.threshold_ratio),
        "margin_samples": int(args.margin_samples),
        "base_morphology_params": asdict(base_params),
        "stylization_diagnostics": stylization_diag,
        "postprocess_diagnostics": post_diag,
    }
    (args.output_dir / "stylized_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Stylized output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
