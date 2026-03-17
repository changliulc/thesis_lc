from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dipole_fit_experiment import load_vehicle_waveform, preprocess_waveform


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
OUTPUT_DIR = ROOT / "tmp" / "speed_latent_reblur_demo"


@dataclass
class AxisDeblurResult:
    axis: str
    lambda_reg: float
    gcv: float
    ref_rmse: float


def build_lowpass_matrix(length: int, a: float) -> np.ndarray:
    matrix = np.zeros((length, length), dtype=np.float64)
    matrix[0, 0] = 1.0
    for row in range(1, length):
        matrix[row, 0] = a**row
        for col in range(1, row + 1):
            matrix[row, col] = (1.0 - a) * (a ** (row - col))
    return matrix


def apply_lowpass(signal: np.ndarray, a: float) -> np.ndarray:
    output = np.empty_like(signal)
    output[0] = signal[0]
    for idx in range(1, signal.shape[0]):
        output[idx] = a * output[idx - 1] + (1.0 - a) * signal[idx]
    return output


def build_second_difference(length: int) -> np.ndarray:
    if length < 3:
        return np.zeros((0, length), dtype=np.float64)
    matrix = np.zeros((length - 2, length), dtype=np.float64)
    for idx in range(length - 2):
        matrix[idx, idx : idx + 3] = [1.0, -2.0, 1.0]
    return matrix


def solve_tikhonov_gcv(
    observed: np.ndarray,
    lowpass_matrix: np.ndarray,
    diff_matrix: np.ndarray,
    lambdas: np.ndarray,
) -> tuple[np.ndarray, AxisDeblurResult]:
    length = observed.shape[0]
    hth = lowpass_matrix.T @ lowpass_matrix
    dtd = diff_matrix.T @ diff_matrix if diff_matrix.size else np.zeros((length, length), dtype=np.float64)
    hty = lowpass_matrix.T @ observed

    best_gcv = math.inf
    best_lambda = float(lambdas[0])
    best_latent = observed.copy()
    best_reproj = observed.copy()

    for lambda_reg in lambdas:
        system = hth + float(lambda_reg) * dtd
        try:
            latent = np.linalg.solve(system, hty)
        except np.linalg.LinAlgError:
            latent = np.linalg.lstsq(system, hty, rcond=None)[0]
        reproj = lowpass_matrix @ latent
        residual = observed - reproj

        try:
            influence = lowpass_matrix @ np.linalg.solve(system, lowpass_matrix.T)
        except np.linalg.LinAlgError:
            influence = lowpass_matrix @ np.linalg.lstsq(system, lowpass_matrix.T, rcond=None)[0]
        dof = float(np.trace(influence))
        denom = max((1.0 - dof / length) ** 2, 1e-9)
        gcv = float(np.mean(residual**2) / denom)

        if gcv < best_gcv:
            best_gcv = gcv
            best_lambda = float(lambda_reg)
            best_latent = latent
            best_reproj = reproj

    result = AxisDeblurResult(
        axis="",
        lambda_reg=best_lambda,
        gcv=best_gcv,
        ref_rmse=float(np.sqrt(np.mean((observed - best_reproj) ** 2))),
    )
    return best_latent, result


def interpolate_latent(x_ref: np.ndarray, latent_ref: np.ndarray, x_target: np.ndarray) -> np.ndarray:
    interpolated = np.zeros((x_target.shape[0], latent_ref.shape[1]), dtype=np.float64)
    for axis in range(latent_ref.shape[1]):
        interpolated[:, axis] = np.interp(
            x_target,
            x_ref,
            latent_ref[:, axis],
            left=float(latent_ref[0, axis]),
            right=float(latent_ref[-1, axis]),
        )
    return interpolated


def crop_effective_segment(
    waveform: np.ndarray,
    threshold_ratio: float,
    margin_samples: int,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    magnitude = np.linalg.norm(waveform, axis=1)
    peak = float(np.max(magnitude))
    idx = np.flatnonzero(magnitude >= peak * threshold_ratio)
    if idx.size == 0:
        start = 0
        end = waveform.shape[0] - 1
    else:
        start = max(0, int(idx[0]) - margin_samples)
        end = min(waveform.shape[0] - 1, int(idx[-1]) + margin_samples)
    return waveform[start : end + 1], magnitude[start : end + 1], start, end


def save_waveforms(
    full_outputs: dict[float, dict[str, object]],
    cropped_outputs: dict[float, dict[str, object]],
    output_dir: Path,
) -> None:
    summary_lines = [
        "speed_kmh,full_samples,cropped_samples,duration_s,threshold_ratio,crop_start,crop_end,sample_spacing_m"
    ]
    combined_lines = ["speed_kmh,sample_local,Bx_nT,By_nT,Bz_nT,mag_nT"]

    for speed_kmh in sorted(full_outputs):
        full_item = full_outputs[speed_kmh]
        cropped_item = cropped_outputs[speed_kmh]
        waveform = np.asarray(cropped_item["waveform_nT"], dtype=np.float64)
        magnitude = np.asarray(cropped_item["magnitude_nT"], dtype=np.float64)

        summary_lines.append(
            ",".join(
                [
                    f"{speed_kmh:.0f}",
                    str(int(full_item["samples"])),
                    str(int(waveform.shape[0])),
                    f"{float(waveform.shape[0] - 1) / float(full_item['sample_rate_hz']):.8f}",
                    f"{float(cropped_item['threshold_ratio']):.4f}",
                    str(int(cropped_item["crop_start"])),
                    str(int(cropped_item["crop_end"])),
                    f"{float(full_item['sample_spacing_m']):.8f}",
                ]
            )
        )

        csv_lines = ["sample_local,Bx_nT,By_nT,Bz_nT,mag_nT"]
        for idx in range(waveform.shape[0]):
            csv_lines.append(
                f"{idx},{waveform[idx,0]:.8f},{waveform[idx,1]:.8f},{waveform[idx,2]:.8f},{magnitude[idx]:.8f}"
            )
            combined_lines.append(
                f"{speed_kmh:.0f},{idx},{waveform[idx,0]:.8f},{waveform[idx,1]:.8f},{waveform[idx,2]:.8f},{magnitude[idx]:.8f}"
            )
        (output_dir / f"cropped_waveform_{int(speed_kmh)}kmh.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    (output_dir / "cropped_speed_summary.csv").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (output_dir / "cropped_speed_combined.csv").write_text("\n".join(combined_lines) + "\n", encoding="utf-8")


def plot_reference_fit(observed: np.ndarray, reproj: np.ndarray, latent: np.ndarray, output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    axis_labels = ["X", "Y", "Z"]
    colors = {"obs": "black", "fit": "#4c78a8", "latent": "#f58518"}
    for axis, ax in enumerate(axes):
        ax.plot(observed[:, axis], color=colors["obs"], linewidth=1.8, label="observed 55 km/h")
        ax.plot(reproj[:, axis], color=colors["fit"], linewidth=1.8, label="reblurred latent")
        ax.plot(latent[:, axis], color=colors["latent"], linewidth=1.2, linestyle="--", label="latent template")
        ax.set_ylabel(f"{axis_labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("Reference samples")
    fig.tight_layout()
    fig.savefig(output_dir / "reference_fit.png", dpi=220)
    plt.close(fig)


def plot_latent_template(x_ref: np.ndarray, latent: np.ndarray, output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    axis_labels = ["X", "Y", "Z"]
    colors = ["#e45756", "#54a24b", "#4c78a8"]
    for axis, ax in enumerate(axes):
        ax.plot(x_ref, latent[:, axis], color=colors[axis], linewidth=1.8)
        ax.set_ylabel(f"{axis_labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("Spatial coordinate / m")
    fig.tight_layout()
    fig.savefig(output_dir / "latent_template.png", dpi=220)
    plt.close(fig)


def plot_literature_style(cropped_outputs: dict[float, dict[str, object]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    colors = {"x": "#e45756", "y": "#54a24b", "z": "#4c78a8"}
    gap = 16
    cursor = 0

    all_values = np.vstack([np.asarray(cropped_outputs[s]["waveform_nT"], dtype=np.float64) for s in sorted(cropped_outputs)])
    y_min = float(np.min(all_values))
    y_max = float(np.max(all_values))
    y_span = max(y_max - y_min, 1.0)

    for idx, speed_kmh in enumerate(sorted(cropped_outputs)):
        item = cropped_outputs[speed_kmh]
        waveform = np.asarray(item["waveform_nT"], dtype=np.float64)
        local_x = cursor + np.arange(waveform.shape[0], dtype=np.float64)

        ax.plot(local_x, waveform[:, 0], color=colors["x"], linewidth=1.8, label="x" if idx == 0 else None)
        ax.plot(local_x, waveform[:, 1], color=colors["y"], linewidth=1.8, label="y" if idx == 0 else None)
        ax.plot(local_x, waveform[:, 2], color=colors["z"], linewidth=1.8, label="z" if idx == 0 else None)

        z_peak_idx = int(np.argmax(waveform[:, 2]))
        peak_x = float(local_x[z_peak_idx])
        peak_y = float(waveform[z_peak_idx, 2])
        ax.annotate(
            f"{int(speed_kmh)} km/h",
            xy=(peak_x, peak_y + 0.02 * y_span),
            xytext=(peak_x, y_max + 0.11 * y_span),
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            arrowprops={"arrowstyle": "->", "linewidth": 1.0, "color": "#222222"},
        )
        ax.text(
            cursor + (waveform.shape[0] - 1) / 2.0,
            y_min - 0.08 * y_span,
            f"{waveform.shape[0]} counts",
            ha="center",
            va="top",
            fontsize=10,
        )
        cursor += waveform.shape[0] + gap

    ax.set_xlim(-3, cursor - gap + 3)
    ax.set_ylim(y_min - 0.16 * y_span, y_max + 0.20 * y_span)
    ax.set_xlabel("Counts")
    ax.set_ylabel("Field / nT")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", frameon=True)
    fig.tight_layout()
    fig.savefig(output_dir / "speed_effect_literature_style.png", dpi=220)
    plt.close(fig)


def plot_overlay(cropped_outputs: dict[float, dict[str, object]], output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=False)
    axis_labels = ["X", "Y", "Z"]
    speed_colors = {20.0: "#4c78a8", 30.0: "#72b7b2", 40.0: "#54a24b", 50.0: "#e45756", 60.0: "#f58518"}
    for axis, ax in enumerate(axes):
        for speed_kmh in sorted(cropped_outputs):
            waveform = np.asarray(cropped_outputs[speed_kmh]["waveform_nT"], dtype=np.float64)
            ax.plot(
                np.arange(waveform.shape[0]),
                waveform[:, axis],
                linewidth=1.8,
                color=speed_colors.get(speed_kmh, None),
                label=f"{int(speed_kmh)} km/h ({waveform.shape[0]} counts)",
            )
        ax.set_ylabel(f"{axis_labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("Local counts after cropping")
    fig.tight_layout()
    fig.savefig(output_dir / "speed_effect_overlay.png", dpi=220)
    plt.close(fig)


def save_latent_template(x_ref: np.ndarray, latent: np.ndarray, reproj: np.ndarray, observed: np.ndarray, output_dir: Path) -> None:
    lines = ["x_m,Bx_latent,By_latent,Bz_latent,Bx_reproj,By_reproj,Bz_reproj,Bx_obs,By_obs,Bz_obs"]
    for idx in range(x_ref.shape[0]):
        lines.append(
            ",".join(
                [
                    f"{x_ref[idx]:.8f}",
                    *(f"{latent[idx, axis]:.8f}" for axis in range(3)),
                    *(f"{reproj[idx, axis]:.8f}" for axis in range(3)),
                    *(f"{observed[idx, axis]:.8f}" for axis in range(3)),
                ]
            )
        )
    (output_dir / "latent_template.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate speed-varying tri-axis waveforms via latent deblur and fixed 20 ms reblur.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--tau-ms", type=float, default=20.0, help="time constant of the low-pass measurement chain in ms")
    parser.add_argument("--speeds", type=float, nargs="+", default=[20.0, 30.0, 40.0, 50.0], help="target speeds in km/h")
    parser.add_argument("--tail-len", type=int, default=12, help="edge length used for bias removal")
    parser.add_argument("--crop-threshold-ratio", type=float, default=0.10, help="magnitude threshold ratio for the effective segment")
    parser.add_argument("--crop-margin-samples", type=int, default=6, help="extra samples around the effective segment")
    parser.add_argument("--lambda-min-exp", type=float, default=-3.0, help="minimum log10(lambda) for GCV search")
    parser.add_argument("--lambda-max-exp", type=float, default=2.0, help="maximum log10(lambda) for GCV search")
    parser.add_argument("--lambda-steps", type=int, default=80, help="number of lambda candidates for GCV search")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    observed, _, _ = preprocess_waveform(waveform, smooth_window=0, tail_len=args.tail_len)

    sample_rate_hz = float(args.sample_rate)
    dt_s = 1.0 / sample_rate_hz
    tau_s = float(args.tau_ms) / 1000.0
    if tau_s <= 0:
        raise ValueError("tau must be positive")
    a = math.exp(-dt_s / tau_s)

    speed_ref_mps = float(waveform.speed_kmh) / 3.6
    dx_ref = speed_ref_mps / sample_rate_hz
    magnitude = np.linalg.norm(observed, axis=1)
    center_sample = float(np.sum(np.arange(observed.shape[0], dtype=np.float64) * magnitude) / np.sum(magnitude))
    x_ref = (np.arange(observed.shape[0], dtype=np.float64) - center_sample) * dx_ref

    lowpass_ref = build_lowpass_matrix(observed.shape[0], a)
    diff_matrix = build_second_difference(observed.shape[0])
    lambdas = np.logspace(args.lambda_min_exp, args.lambda_max_exp, args.lambda_steps)

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
    full_outputs: dict[float, dict[str, object]] = {}
    cropped_outputs: dict[float, dict[str, object]] = {}
    for speed_kmh in [float(x) for x in args.speeds]:
        dx_target = (speed_kmh / 3.6) / sample_rate_hz
        sample_count = int(math.ceil((x_max - x_min) / dx_target)) + 1
        x_target = x_min + dx_target * np.arange(sample_count, dtype=np.float64)
        latent_target = interpolate_latent(x_ref, latent, x_target)

        waveform_target = np.zeros_like(latent_target)
        for axis_idx in range(3):
            waveform_target[:, axis_idx] = apply_lowpass(latent_target[:, axis_idx], a)

        full_outputs[speed_kmh] = {
            "speed_kmh": speed_kmh,
            "sample_spacing_m": dx_target,
            "sample_rate_hz": sample_rate_hz,
            "samples": sample_count,
            "waveform_nT": waveform_target,
            "x_m": x_target,
        }

        cropped_waveform, cropped_magnitude, start, end = crop_effective_segment(
            waveform_target,
            threshold_ratio=args.crop_threshold_ratio,
            margin_samples=args.crop_margin_samples,
        )
        cropped_outputs[speed_kmh] = {
            "speed_kmh": speed_kmh,
            "sample_spacing_m": dx_target,
            "sample_rate_hz": sample_rate_hz,
            "waveform_nT": cropped_waveform,
            "magnitude_nT": cropped_magnitude,
            "crop_start": start,
            "crop_end": end,
            "threshold_ratio": float(args.crop_threshold_ratio),
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_waveforms(full_outputs, cropped_outputs, args.output_dir)
    save_latent_template(x_ref, latent, reproj, observed, args.output_dir)
    plot_reference_fit(observed, reproj, latent, args.output_dir)
    plot_latent_template(x_ref, latent, args.output_dir)
    plot_literature_style(cropped_outputs, args.output_dir)
    plot_overlay(cropped_outputs, args.output_dir)

    payload = {
        "data": str(args.data),
        "sample_rate_hz": sample_rate_hz,
        "dt_s": dt_s,
        "tau_s": tau_s,
        "alpha_exact": 1.0 - a,
        "pole_a": a,
        "reference_speed_kmh": float(waveform.speed_kmh),
        "reference_spacing_m": dx_ref,
        "reference_center_sample": center_sample,
        "target_speeds_kmh": [float(x) for x in args.speeds],
        "crop_threshold_ratio": float(args.crop_threshold_ratio),
        "crop_margin_samples": int(args.crop_margin_samples),
        "axis_deblur": [asdict(item) for item in axis_results],
    }
    (args.output_dir / "generation_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Reference spacing: {dx_ref:.8f} m/sample")
    print(f"Low-pass exact alpha: {1.0 - a:.8f}")
    for item in axis_results:
        print(f"[{item.axis}] lambda={item.lambda_reg:.6e}, gcv={item.gcv:.6e}, ref_rmse={item.ref_rmse:.4f}")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
