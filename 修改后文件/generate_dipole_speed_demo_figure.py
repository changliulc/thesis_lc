from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dipole_fit_experiment import load_vehicle_waveform


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
FIT_RESULTS_PATH = ROOT / "tmp" / "dipole_fit_fixed_50hz_6dipole" / "fit_results.json"
OUTPUT_DIR = ROOT / "tmp" / "dipole_speed_effect_demo"
MU0_OVER_4PI_NT = 100.0


def load_best_model(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    best_key = str(payload["best_by_bic"])
    return payload["models"][best_key]


def dipole_field(moment: np.ndarray, position: np.ndarray) -> np.ndarray:
    r2 = np.sum(position**2, axis=-1, keepdims=True)
    r = np.sqrt(np.maximum(r2, 1e-12))
    m_dot_r = np.sum(moment * position, axis=-1, keepdims=True)
    return MU0_OVER_4PI_NT * (
        (3.0 * position * m_dot_r) / np.maximum(r, 1e-12) ** 5 - moment / np.maximum(r, 1e-12) ** 3
    )


def simulate_waveform(
    x_track: np.ndarray,
    x_offsets_xyz: np.ndarray,
    moments: np.ndarray,
    bias_nT: np.ndarray,
    y0_m: float,
    z0_m: float,
) -> np.ndarray:
    prediction = np.zeros((x_track.shape[0], 3), dtype=np.float64)
    for idx in range(moments.shape[0]):
        position = np.column_stack(
            [
                x_track + x_offsets_xyz[idx, 0],
                np.full(x_track.shape[0], y0_m + x_offsets_xyz[idx, 1], dtype=np.float64),
                np.full(x_track.shape[0], z0_m + x_offsets_xyz[idx, 2], dtype=np.float64),
            ]
        )
        prediction += dipole_field(moments[idx][None, :], position)
    prediction += bias_nT[None, :]
    return prediction


def generate_full_waveforms(
    model: dict[str, object],
    sample_rate_hz: float,
    reference_speed_kmh: float,
    reference_samples: int,
    target_speeds_kmh: list[float],
) -> dict[float, dict[str, np.ndarray | float | int]]:
    sample_spacing_ref = (reference_speed_kmh / 3.6) / sample_rate_hz
    center_sample = float(model["center_sample"])
    x_min = sample_spacing_ref * (0.0 - center_sample)
    x_max = sample_spacing_ref * ((reference_samples - 1) - center_sample)

    x_offsets_xyz = np.asarray(model["x_offsets_m"], dtype=np.float64)
    moments = np.asarray(model["moments_Am2"], dtype=np.float64)
    bias_nT = np.asarray(model["bias_nT"], dtype=np.float64)
    y0_m = float(model["y0_m"])
    z0_m = float(model["z0_m"])

    outputs: dict[float, dict[str, np.ndarray | float | int]] = {}
    for speed_kmh in target_speeds_kmh:
        spacing = (speed_kmh / 3.6) / sample_rate_hz
        n_samples = int(math.ceil((x_max - x_min) / spacing)) + 1
        x_track = x_min + spacing * np.arange(n_samples, dtype=np.float64)
        waveform = simulate_waveform(
            x_track=x_track,
            x_offsets_xyz=x_offsets_xyz,
            moments=moments,
            bias_nT=bias_nT,
            y0_m=y0_m,
            z0_m=z0_m,
        )
        outputs[float(speed_kmh)] = {
            "speed_kmh": float(speed_kmh),
            "sample_spacing_m": float(spacing),
            "sample_rate_hz": float(sample_rate_hz),
            "time_s": np.arange(n_samples, dtype=np.float64) / sample_rate_hz,
            "waveform_nT": waveform,
            "magnitude_nT": np.linalg.norm(waveform, axis=1),
        }
    return outputs


def crop_effective_segment(
    waveform: np.ndarray,
    magnitude: np.ndarray,
    threshold_ratio: float,
    margin_samples: int,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    peak = float(np.max(magnitude))
    idx = np.flatnonzero(magnitude >= peak * threshold_ratio)
    if idx.size == 0:
        start = 0
        end = waveform.shape[0] - 1
    else:
        start = max(0, int(idx[0]) - margin_samples)
        end = min(waveform.shape[0] - 1, int(idx[-1]) + margin_samples)
    return waveform[start : end + 1], magnitude[start : end + 1], start, end


def save_outputs(
    outputs: dict[float, dict[str, np.ndarray | float | int]],
    cropped: dict[float, dict[str, np.ndarray | float | int]],
    output_dir: Path,
) -> None:
    summary_lines = [
        "speed_kmh,full_samples,cropped_samples,duration_s,threshold_ratio,crop_start,crop_end,sample_spacing_m"
    ]
    combined_lines = ["speed_kmh,sample_local,Bx_nT,By_nT,Bz_nT,mag_nT"]

    for speed_kmh in sorted(outputs):
        item = outputs[speed_kmh]
        cropped_item = cropped[speed_kmh]
        waveform = np.asarray(cropped_item["waveform_nT"], dtype=np.float64)
        magnitude = np.asarray(cropped_item["magnitude_nT"], dtype=np.float64)

        summary_lines.append(
            ",".join(
                [
                    f"{speed_kmh:.0f}",
                    str(np.asarray(item["waveform_nT"]).shape[0]),
                    str(waveform.shape[0]),
                    f"{float(waveform.shape[0] - 1) / float(item['sample_rate_hz']):.8f}",
                    f"{float(cropped_item['threshold_ratio']):.4f}",
                    str(int(cropped_item["crop_start"])),
                    str(int(cropped_item["crop_end"])),
                    f"{float(item['sample_spacing_m']):.8f}",
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

        (output_dir / f"cropped_waveform_{int(speed_kmh)}kmh.csv").write_text(
            "\n".join(csv_lines) + "\n", encoding="utf-8"
        )

    (output_dir / "cropped_speed_summary.csv").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (output_dir / "cropped_speed_combined.csv").write_text("\n".join(combined_lines) + "\n", encoding="utf-8")


def plot_literature_style(cropped: dict[float, dict[str, np.ndarray | float | int]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    colors = {"x": "#e45756", "y": "#54a24b", "z": "#4c78a8"}
    gap = 16
    cursor = 0

    all_values = np.vstack([np.asarray(cropped[s]["waveform_nT"], dtype=np.float64) for s in sorted(cropped)])
    y_min = float(np.min(all_values))
    y_max = float(np.max(all_values))
    y_span = max(y_max - y_min, 1.0)

    for idx, speed_kmh in enumerate(sorted(cropped)):
        item = cropped[speed_kmh]
        waveform = np.asarray(item["waveform_nT"], dtype=np.float64)
        local_x = cursor + np.arange(waveform.shape[0], dtype=np.float64)

        ax.plot(local_x, waveform[:, 0], color=colors["x"], linewidth=1.8, label="x" if idx == 0 else None)
        ax.plot(local_x, waveform[:, 1], color=colors["y"], linewidth=1.8, label="y" if idx == 0 else None)
        ax.plot(local_x, waveform[:, 2], color=colors["z"], linewidth=1.8, label="z" if idx == 0 else None)

        z_peak_idx = int(np.argmax(waveform[:, 2]))
        peak_x = float(local_x[z_peak_idx])
        peak_y = float(waveform[z_peak_idx, 2])
        label_y = y_max + 0.11 * y_span
        ax.annotate(
            f"{int(speed_kmh)} km/h",
            xy=(peak_x, peak_y + 0.02 * y_span),
            xytext=(peak_x, label_y),
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            arrowprops={"arrowstyle": "->", "linewidth": 1.0, "color": "#222222"},
        )

        length_text_y = y_min - 0.08 * y_span
        ax.text(
            cursor + (waveform.shape[0] - 1) / 2.0,
            length_text_y,
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


def plot_overlay(cropped: dict[float, dict[str, np.ndarray | float | int]], output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=False)
    axis_labels = ["X", "Y", "Z"]
    speed_colors = {20.0: "#4c78a8", 30.0: "#72b7b2", 40.0: "#54a24b", 50.0: "#e45756", 60.0: "#f58518"}
    for axis, ax in enumerate(axes):
        for speed_kmh in sorted(cropped):
            waveform = np.asarray(cropped[speed_kmh]["waveform_nT"], dtype=np.float64)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a clearer literature-style speed-effect figure from the dipole model.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--fit-results", type=Path, default=FIT_RESULTS_PATH, help="fit_results.json from the selected dipole model")
    parser.add_argument("--speeds", type=float, nargs="+", default=[20.0, 30.0, 40.0, 50.0], help="target speeds in km/h")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--threshold-ratio", type=float, default=0.10, help="magnitude threshold ratio used to crop the effective disturbance segment")
    parser.add_argument("--margin-samples", type=int, default=6, help="extra samples kept before and after the effective segment")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    model = load_best_model(args.fit_results)
    outputs = generate_full_waveforms(
        model=model,
        sample_rate_hz=args.sample_rate,
        reference_speed_kmh=float(waveform.speed_kmh),
        reference_samples=int(waveform.delta_xyz.shape[0]),
        target_speeds_kmh=[float(x) for x in args.speeds],
    )

    cropped: dict[float, dict[str, np.ndarray | float | int]] = {}
    for speed_kmh, item in outputs.items():
        waveform_arr = np.asarray(item["waveform_nT"], dtype=np.float64)
        magnitude = np.asarray(item["magnitude_nT"], dtype=np.float64)
        cropped_waveform, cropped_magnitude, start, end = crop_effective_segment(
            waveform_arr,
            magnitude,
            threshold_ratio=args.threshold_ratio,
            margin_samples=args.margin_samples,
        )
        cropped[speed_kmh] = {
            **item,
            "waveform_nT": cropped_waveform,
            "magnitude_nT": cropped_magnitude,
            "crop_start": start,
            "crop_end": end,
            "threshold_ratio": float(args.threshold_ratio),
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_outputs(outputs, cropped, args.output_dir)
    plot_literature_style(cropped, args.output_dir)
    plot_overlay(cropped, args.output_dir)

    metadata = {
        "data": str(args.data),
        "fit_results": str(args.fit_results),
        "sample_rate_hz": float(args.sample_rate),
        "reference_speed_kmh": float(waveform.speed_kmh),
        "reference_samples": int(waveform.delta_xyz.shape[0]),
        "target_speeds_kmh": [float(x) for x in args.speeds],
        "threshold_ratio": float(args.threshold_ratio),
        "margin_samples": int(args.margin_samples),
        "selected_model": {
            "dipoles": int(model["dipoles"]),
            "raw_vector_rmse": float(model["raw_vector_rmse"]),
            "bic": float(model["bic"]),
        },
    }
    (args.output_dir / "generation_config.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Generated literature-style demo for speeds: {', '.join(str(int(x)) for x in args.speeds)} km/h")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
