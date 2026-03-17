from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image

from dipole_fit_experiment import load_vehicle_waveform
from generate_dipole_speed_morphology_demo import (
    MorphologyParams,
    generate_waveforms,
    load_best_model,
    plot_literature_style,
    plot_overlay,
    save_outputs,
    score_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
FIT_RESULTS_PATH = ROOT / "tmp" / "dipole_fit_fixed_50hz_6dipole" / "fit_results.json"
LITERATURE_IMAGE_PATH = ROOT / "tmp" / "pdfs" / "vehicle_sensor_fig7_tight_300.png"
OUTPUT_DIR = ROOT / "tmp" / "dipole_speed_morphology_litfit"


PANEL_BOUNDS = {
    20.0: (105, 305),
    30.0: (365, 505),
    40.0: (535, 650),
    50.0: (675, 760),
}
PLOT_TOP = 112
PLOT_BOTTOM = 738
COLOR_MASKS = {
    "x": lambda a: (a[:, :, 0] > 160) & (a[:, :, 1] < 145) & (a[:, :, 2] < 145),
    "y": lambda a: (a[:, :, 1] > 115) & (a[:, :, 0] < 180) & (a[:, :, 2] < 180),
    "z": lambda a: (a[:, :, 2] > 115) & (a[:, :, 0] < 180) & (a[:, :, 1] < 180),
}


def extract_literature_targets(image_path: Path) -> dict[float, dict[str, np.ndarray]]:
    image = Image.open(image_path).convert("RGB")
    arr = np.asarray(image)
    targets: dict[float, dict[str, np.ndarray]] = {}

    for speed_kmh, (x0, x1) in PANEL_BOUNDS.items():
        panel_targets: dict[str, np.ndarray] = {}
        panel_width = x1 - x0 + 1
        for axis_name, mask_fn in COLOR_MASKS.items():
            mask = mask_fn(arr)
            xs = []
            ys = []
            for x in range(x0, x1 + 1):
                yy = np.flatnonzero(mask[PLOT_TOP : PLOT_BOTTOM + 1, x])
                if yy.size:
                    xs.append(x - x0)
                    ys.append(float(np.median(yy)))

            if not xs:
                raise RuntimeError(f"failed to extract {axis_name} curve for {speed_kmh} km/h")

            xs_arr = np.asarray(xs, dtype=np.float64)
            ys_arr = np.asarray(ys, dtype=np.float64)
            full_x = np.arange(panel_width, dtype=np.float64)
            interp_y = np.interp(full_x, xs_arr, ys_arr)
            tail_len = max(6, panel_width // 10)
            tail_baseline = float(np.median(interp_y[-tail_len:]))
            signal = tail_baseline - interp_y
            panel_targets[axis_name] = signal.astype(np.float64)
        targets[float(speed_kmh)] = panel_targets
    return targets


def normalize_axis_group(curves: dict[float, np.ndarray]) -> dict[float, np.ndarray]:
    scale = max(float(np.max(np.abs(curves[speed]))) for speed in curves)
    scale = max(scale, 1e-9)
    return {speed: curves[speed] / scale for speed in curves}


def prepare_generated_targets(outputs: dict[float, dict[str, object]]) -> dict[float, dict[str, np.ndarray]]:
    prepared: dict[float, dict[str, np.ndarray]] = {}
    for speed_kmh, item in outputs.items():
        wf = np.asarray(item["cropped_waveform_nT"], dtype=np.float64)
        panel: dict[str, np.ndarray] = {}
        for axis_idx, axis_name in enumerate(["x", "y", "z"]):
            axis_signal = wf[:, axis_idx]
            tail_len = max(6, wf.shape[0] // 10)
            tail_baseline = float(np.median(axis_signal[-tail_len:]))
            panel[axis_name] = axis_signal - tail_baseline
        prepared[float(speed_kmh)] = panel
    return prepared


def resample_curve(curve: np.ndarray, target_len: int = 160) -> np.ndarray:
    old_x = np.linspace(0.0, 1.0, curve.shape[0])
    new_x = np.linspace(0.0, 1.0, target_len)
    return np.interp(new_x, old_x, curve)


def literature_shape_score(
    outputs: dict[float, dict[str, object]],
    literature_targets: dict[float, dict[str, np.ndarray]],
) -> tuple[float, dict[str, float]]:
    generated = prepare_generated_targets(outputs)

    total_mse = 0.0
    total_count = 0
    per_axis_mse: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}

    for axis_name in ["x", "y", "z"]:
        lit_axis = normalize_axis_group({speed: literature_targets[speed][axis_name] for speed in literature_targets})
        gen_axis = normalize_axis_group({speed: generated[speed][axis_name] for speed in generated})
        for speed in sorted(lit_axis):
            lit = resample_curve(lit_axis[speed], 180)
            gen = resample_curve(gen_axis[speed], 180)
            mse = float(np.mean((lit - gen) ** 2))
            total_mse += mse
            per_axis_mse[axis_name] += mse
            total_count += 1

    heuristic_score, heuristic_diag = score_outputs(outputs)
    total_score = total_mse / max(total_count, 1) + 0.18 * heuristic_score
    diagnostics = {
        "shape_mse_mean": total_mse / max(total_count, 1),
        "shape_mse_x": per_axis_mse["x"] / 4.0,
        "shape_mse_y": per_axis_mse["y"] / 4.0,
        "shape_mse_z": per_axis_mse["z"] / 4.0,
        **heuristic_diag,
    }
    return total_score, diagnostics


def search_best_params(
    model: dict[str, object],
    waveform_speed_kmh: float,
    reference_samples: int,
    sample_rate_hz: float,
    literature_targets: dict[float, dict[str, np.ndarray]],
    threshold_ratio: float,
    margin_samples: int,
) -> tuple[MorphologyParams, dict[float, dict[str, object]], dict[str, float]]:
    best_score = math.inf
    best_params = None
    best_outputs = None
    best_diag = None

    tau_candidates = [0.010]
    y_candidates = [0.08, 0.10, 0.12]
    z_candidates = [0.12, 0.14, 0.16]
    phase_candidates = [-0.35, -0.30, -0.25, -0.20]
    gain_candidates = [0.0]
    y_axis_gain_candidates = [-0.34, -0.30, -0.26]
    x_axis_gain_candidates = [-0.16, -0.10, -0.04]
    z_axis_gain_candidates = [-0.08, -0.04, 0.0]
    y_pos_gain_candidates = [-0.30, -0.20, -0.10]
    y_neg_gain_candidates = [0.0, 0.08, 0.15]

    speeds = sorted(literature_targets)
    for tau_s in tau_candidates:
        for y_shift_m in y_candidates:
            for z_shift_m in z_candidates:
                for phase_shift_samples in phase_candidates:
                    for gain_slope in gain_candidates:
                        for y_axis_gain_slope in y_axis_gain_candidates:
                            for x_axis_gain_slope in x_axis_gain_candidates:
                                for z_axis_gain_slope in z_axis_gain_candidates:
                                    for y_pos_gain_slope in y_pos_gain_candidates:
                                        for y_neg_gain_slope in y_neg_gain_candidates:
                                            params = MorphologyParams(
                                                tau_s=tau_s,
                                                y_shift_m=y_shift_m,
                                                z_shift_m=z_shift_m,
                                                phase_shift_samples=phase_shift_samples,
                                                gain_slope=gain_slope,
                                                y_axis_gain_slope=y_axis_gain_slope,
                                                x_axis_gain_slope=x_axis_gain_slope,
                                                z_axis_gain_slope=z_axis_gain_slope,
                                                y_pos_gain_slope=y_pos_gain_slope,
                                                y_neg_gain_slope=y_neg_gain_slope,
                                            )
                                            outputs = generate_waveforms(
                                                model=model,
                                                reference_speed_kmh=waveform_speed_kmh,
                                                reference_samples=reference_samples,
                                                sample_rate_hz=sample_rate_hz,
                                                target_speeds_kmh=speeds,
                                                params=params,
                                                threshold_ratio=threshold_ratio,
                                                margin_samples=margin_samples,
                                            )
                                            score, diag = literature_shape_score(outputs, literature_targets)
                                            if score < best_score:
                                                best_score = score
                                                best_params = params
                                                best_outputs = outputs
                                                best_diag = diag

    assert best_params is not None and best_outputs is not None and best_diag is not None
    return best_params, best_outputs, best_diag


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune morphology parameters against the literature Fig. 7 curves.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--fit-results", type=Path, default=FIT_RESULTS_PATH, help="fit_results.json from the selected dipole model")
    parser.add_argument("--literature-image", type=Path, default=LITERATURE_IMAGE_PATH, help="cropped Fig. 7 PNG")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--threshold-ratio", type=float, default=0.10, help="cropping threshold ratio")
    parser.add_argument("--margin-samples", type=int, default=6, help="extra samples around the effective segment")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    model = load_best_model(args.fit_results)
    literature_targets = extract_literature_targets(args.literature_image)
    params, outputs, diagnostics = search_best_params(
        model=model,
        waveform_speed_kmh=float(waveform.speed_kmh),
        reference_samples=int(waveform.delta_xyz.shape[0]),
        sample_rate_hz=args.sample_rate,
        literature_targets=literature_targets,
        threshold_ratio=args.threshold_ratio,
        margin_samples=args.margin_samples,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_outputs(outputs, args.output_dir)
    plot_literature_style(outputs, args.output_dir)
    plot_overlay(outputs, args.output_dir)

    payload = {
        "data": str(args.data),
        "fit_results": str(args.fit_results),
        "literature_image": str(args.literature_image),
        "sample_rate_hz": float(args.sample_rate),
        "target_speeds_kmh": sorted(literature_targets),
        "threshold_ratio": float(args.threshold_ratio),
        "margin_samples": int(args.margin_samples),
        "selected_model": {
            "dipoles": int(model["dipoles"]),
            "raw_vector_rmse": float(model["raw_vector_rmse"]),
            "bic": float(model["bic"]),
        },
        "morphology_params": asdict(params),
        "diagnostics": diagnostics,
    }
    (args.output_dir / "literature_fit_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Best params:", json.dumps(payload["morphology_params"], ensure_ascii=False))
    print("Diagnostics:", json.dumps(payload["diagnostics"], ensure_ascii=False))
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
