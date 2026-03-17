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
OUTPUT_DIR = ROOT / "tmp" / "dipole_speed_sweep_6dipole"
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


def simulate_on_track(
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


def generate_speed_waveforms(
    model: dict[str, object],
    sample_rate_hz: float,
    reference_speed_kmh: float,
    reference_samples: int,
    target_speeds_kmh: list[float],
) -> tuple[dict[float, dict[str, np.ndarray | float | int]], tuple[float, float]]:
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
        waveform = simulate_on_track(
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
            "samples": int(n_samples),
            "duration_s": float((n_samples - 1) / sample_rate_hz),
            "time_s": np.arange(n_samples, dtype=np.float64) / sample_rate_hz,
            "waveform_nT": waveform,
            "magnitude_nT": np.linalg.norm(waveform, axis=1),
        }
    return outputs, (x_min, x_max)


def save_csvs(outputs: dict[float, dict[str, np.ndarray | float | int]], output_dir: Path) -> None:
    summary_lines = ["speed_kmh,samples,duration_s,sample_spacing_m"]
    combined_lines = ["speed_kmh,sample,time_s,Bx_nT,By_nT,Bz_nT,mag_nT"]

    for speed_kmh in sorted(outputs):
        item = outputs[speed_kmh]
        waveform = np.asarray(item["waveform_nT"], dtype=np.float64)
        magnitude = np.asarray(item["magnitude_nT"], dtype=np.float64)
        time_s = np.asarray(item["time_s"], dtype=np.float64)
        samples = np.arange(waveform.shape[0], dtype=int)

        summary_lines.append(
            f"{speed_kmh:.0f},{int(item['samples'])},{float(item['duration_s']):.8f},{float(item['sample_spacing_m']):.8f}"
        )

        csv_lines = ["sample,time_s,Bx_nT,By_nT,Bz_nT,mag_nT"]
        for idx in range(waveform.shape[0]):
            csv_lines.append(
                f"{idx},{time_s[idx]:.8f},{waveform[idx,0]:.8f},{waveform[idx,1]:.8f},{waveform[idx,2]:.8f},{magnitude[idx]:.8f}"
            )
            combined_lines.append(
                f"{speed_kmh:.0f},{idx},{time_s[idx]:.8f},{waveform[idx,0]:.8f},{waveform[idx,1]:.8f},{waveform[idx,2]:.8f},{magnitude[idx]:.8f}"
            )

        (output_dir / f"waveform_{int(speed_kmh)}kmh.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    (output_dir / "speed_sweep_summary.csv").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    (output_dir / "speed_sweep_combined.csv").write_text("\n".join(combined_lines) + "\n", encoding="utf-8")


def plot_xyz(outputs: dict[float, dict[str, np.ndarray | float | int]], output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=False)
    axis_labels = ["X", "Y", "Z"]
    colors = {20.0: "#4c78a8", 40.0: "#54a24b", 60.0: "#e45756"}
    for axis, ax in enumerate(axes):
        for speed_kmh in sorted(outputs):
            item = outputs[speed_kmh]
            waveform = np.asarray(item["waveform_nT"], dtype=np.float64)
            ax.plot(
                np.arange(waveform.shape[0]),
                waveform[:, axis],
                linewidth=1.8,
                color=colors.get(speed_kmh),
                label=f"{int(speed_kmh)} km/h ({waveform.shape[0]} samples)",
            )
        ax.set_ylabel(f"{axis_labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("sample")
    fig.tight_layout()
    fig.savefig(output_dir / "speed_waveforms_xyz_overlay.png", dpi=220)
    plt.close(fig)


def plot_panel(outputs: dict[float, dict[str, np.ndarray | float | int]], output_dir: Path) -> None:
    fig, axes = plt.subplots(1, len(outputs), figsize=(13, 4.6), sharey=True)
    axis_colors = ["#e45756", "#54a24b", "#4c78a8"]
    speed_list = sorted(outputs)
    for col, speed_kmh in enumerate(speed_list):
        ax = axes[col]
        item = outputs[speed_kmh]
        waveform = np.asarray(item["waveform_nT"], dtype=np.float64)
        x = np.arange(waveform.shape[0])
        ax.plot(x, waveform[:, 0], color=axis_colors[0], linewidth=1.8, label="x")
        ax.plot(x, waveform[:, 1], color=axis_colors[1], linewidth=1.8, label="y")
        ax.plot(x, waveform[:, 2], color=axis_colors[2], linewidth=1.8, label="z")
        ax.set_title(f"{int(speed_kmh)} km/h")
        ax.set_xlabel("Counts")
        ax.grid(True, alpha=0.25)
        if col == 0:
            ax.set_ylabel("Field / nT")
            ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_dir / "speed_waveforms_panel.png", dpi=220)
    plt.close(fig)


def plot_literature_style(outputs: dict[float, dict[str, np.ndarray | float | int]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    axis_colors = {"x": "#e45756", "y": "#54a24b", "z": "#4c78a8"}
    gap = 24
    cursor = 0
    xticks: list[float] = []
    xticklabels: list[str] = []

    all_values = []
    for speed_kmh in sorted(outputs):
        waveform = np.asarray(outputs[speed_kmh]["waveform_nT"], dtype=np.float64)
        all_values.append(waveform)
    all_values_np = np.vstack(all_values)
    y_min = float(np.min(all_values_np))
    y_max = float(np.max(all_values_np))
    y_span = y_max - y_min

    for idx, speed_kmh in enumerate(sorted(outputs)):
        item = outputs[speed_kmh]
        waveform = np.asarray(item["waveform_nT"], dtype=np.float64)
        local_x = cursor + np.arange(waveform.shape[0], dtype=np.float64)

        ax.plot(local_x, waveform[:, 0], color=axis_colors["x"], linewidth=1.8, label="x" if idx == 0 else None)
        ax.plot(local_x, waveform[:, 1], color=axis_colors["y"], linewidth=1.8, label="y" if idx == 0 else None)
        ax.plot(local_x, waveform[:, 2], color=axis_colors["z"], linewidth=1.8, label="z" if idx == 0 else None)

        z_peak_idx = int(np.argmax(waveform[:, 2]))
        peak_x = float(local_x[z_peak_idx])
        peak_y = float(waveform[z_peak_idx, 2])
        label_y = y_max + 0.12 * y_span
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

        xticks.append(cursor + (waveform.shape[0] - 1) / 2.0)
        xticklabels.append(str(int(speed_kmh)))
        cursor += waveform.shape[0] + gap

    ax.set_xlim(-5, cursor - gap + 5)
    ax.set_ylim(y_min - 0.1 * y_span, y_max + 0.22 * y_span)
    ax.set_xlabel("Counts")
    ax.set_ylabel("Field / nT")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", frameon=True)
    fig.tight_layout()
    fig.savefig(output_dir / "speed_waveforms_literature_style.png", dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 20/40/60 km/h waveforms from a fitted fixed-rate dipole model.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--fit-results", type=Path, default=FIT_RESULTS_PATH, help="fit_results.json from the selected dipole model")
    parser.add_argument("--speeds", type=float, nargs="+", default=[20.0, 40.0, 60.0], help="target speeds in km/h")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    model = load_best_model(args.fit_results)
    outputs, x_window = generate_speed_waveforms(
        model=model,
        sample_rate_hz=args.sample_rate,
        reference_speed_kmh=float(waveform.speed_kmh),
        reference_samples=int(waveform.delta_xyz.shape[0]),
        target_speeds_kmh=[float(x) for x in args.speeds],
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_csvs(outputs, args.output_dir)
    plot_xyz(outputs, args.output_dir)
    plot_panel(outputs, args.output_dir)
    plot_literature_style(outputs, args.output_dir)

    metadata = {
        "data": str(args.data),
        "fit_results": str(args.fit_results),
        "sample_rate_hz": float(args.sample_rate),
        "reference_speed_kmh": float(waveform.speed_kmh),
        "reference_samples": int(waveform.delta_xyz.shape[0]),
        "target_speeds_kmh": [float(x) for x in args.speeds],
        "physical_window_m": {"x_min": float(x_window[0]), "x_max": float(x_window[1])},
        "selected_model": {
            "dipoles": int(model["dipoles"]),
            "raw_vector_rmse": float(model["raw_vector_rmse"]),
            "bic": float(model["bic"]),
        },
    }
    (args.output_dir / "generation_config.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Generated waveforms for speeds: {', '.join(str(int(x)) for x in args.speeds)} km/h")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
