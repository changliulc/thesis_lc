from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dipole_fit_experiment import load_vehicle_waveform


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
FIT_RESULTS_PATH = ROOT / "tmp" / "dipole_fit_fixed_50hz_6dipole" / "fit_results.json"
OUTPUT_DIR = ROOT / "tmp" / "dipole_speed_morphology_demo"
MU0_OVER_4PI_NT = 100.0


@dataclass
class MorphologyParams:
    tau_s: float
    y_shift_m: float
    z_shift_m: float
    phase_shift_samples: float
    gain_slope: float
    y_axis_gain_slope: float
    x_axis_gain_slope: float
    z_axis_gain_slope: float
    y_pos_gain_slope: float
    y_neg_gain_slope: float


def configure_plot_style() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "font.family": ["Times New Roman", "SimSun", "DejaVu Sans"],
            "font.size": 13,
            "axes.labelsize": 17,
            "axes.titlesize": 16,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
            "legend.fontsize": 13,
            "axes.unicode_minus": False,
        }
    )


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


def rc_lowpass(signal: np.ndarray, sample_rate_hz: float, tau_s: float) -> np.ndarray:
    if tau_s <= 1e-9:
        return signal.copy()
    dt = 1.0 / sample_rate_hz
    alpha = dt / (tau_s + dt)
    out = np.empty_like(signal)
    out[0] = signal[0]
    for i in range(1, signal.shape[0]):
        out[i] = out[i - 1] + alpha * (signal[i] - out[i - 1])
    return out


def simulate_waveform(
    model: dict[str, object],
    x_track: np.ndarray,
    y_shift_m: float,
    z_shift_m: float,
    gain: float,
) -> np.ndarray:
    x_offsets_xyz = np.asarray(model["x_offsets_m"], dtype=np.float64)
    moments = np.asarray(model["moments_Am2"], dtype=np.float64)
    bias_nT = np.asarray(model["bias_nT"], dtype=np.float64)
    y0_m = float(model["y0_m"]) + y_shift_m
    z0_m = float(model["z0_m"]) + z_shift_m

    prediction = np.zeros((x_track.shape[0], 3), dtype=np.float64)
    for idx in range(moments.shape[0]):
        position = np.column_stack(
            [
                x_track + x_offsets_xyz[idx, 0],
                np.full(x_track.shape[0], y0_m + x_offsets_xyz[idx, 1], dtype=np.float64),
                np.full(x_track.shape[0], z0_m + x_offsets_xyz[idx, 2], dtype=np.float64),
            ]
        )
        prediction += dipole_field((gain * moments[idx])[None, :], position)
    prediction += bias_nT[None, :]
    return prediction


def crop_effective_segment(
    waveform: np.ndarray,
    threshold_ratio: float,
    margin_samples: int,
) -> tuple[np.ndarray, int, int]:
    magnitude = np.linalg.norm(waveform, axis=1)
    peak = float(np.max(magnitude))
    idx = np.flatnonzero(magnitude >= peak * threshold_ratio)
    if idx.size == 0:
        return waveform.copy(), 0, waveform.shape[0] - 1
    start = max(0, int(idx[0]) - margin_samples)
    end = min(waveform.shape[0] - 1, int(idx[-1]) + margin_samples)
    return waveform[start : end + 1], start, end


def resample_to_length(x: np.ndarray, target_len: int) -> np.ndarray:
    old_idx = np.linspace(0.0, 1.0, x.shape[0])
    new_idx = np.linspace(0.0, 1.0, target_len)
    return np.interp(new_idx, old_idx, x)


def normalized_corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - np.mean(a)
    b = b - np.mean(b)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 1.0
    return float(np.dot(a, b) / denom)


def generate_waveforms(
    model: dict[str, object],
    reference_speed_kmh: float,
    reference_samples: int,
    sample_rate_hz: float,
    target_speeds_kmh: list[float],
    params: MorphologyParams,
    threshold_ratio: float,
    margin_samples: int,
) -> dict[float, dict[str, object]]:
    sample_spacing_ref = (reference_speed_kmh / 3.6) / sample_rate_hz
    base_center = float(model["center_sample"])
    x_min = sample_spacing_ref * (0.0 - base_center)
    x_max = sample_spacing_ref * ((reference_samples - 1) - base_center)
    speed_mid = 0.5 * (min(target_speeds_kmh) + max(target_speeds_kmh))
    speed_span = max(max(target_speeds_kmh) - min(target_speeds_kmh), 1.0)

    outputs: dict[float, dict[str, object]] = {}
    for speed_kmh in target_speeds_kmh:
        scale = (speed_kmh - speed_mid) / speed_span
        phase = params.phase_shift_samples * scale
        spacing = (speed_kmh / 3.6) / sample_rate_hz
        n_samples = int(math.ceil((x_max - x_min) / spacing)) + 1
        x_track = x_min + spacing * (np.arange(n_samples, dtype=np.float64) - phase)
        waveform = simulate_waveform(
            model=model,
            x_track=x_track,
            y_shift_m=params.y_shift_m * scale,
            z_shift_m=params.z_shift_m * scale,
            gain=1.0 + params.gain_slope * scale,
        )
        waveform = rc_lowpass(waveform, sample_rate_hz=sample_rate_hz, tau_s=params.tau_s)
        waveform[:, 0] *= 1.0 + params.x_axis_gain_slope * scale
        waveform[:, 2] *= 1.0 + params.z_axis_gain_slope * scale
        y_axis = waveform[:, 1] * (1.0 + params.y_axis_gain_slope * scale)
        y_pos = np.clip(y_axis, 0.0, None) * (1.0 + params.y_pos_gain_slope * scale)
        y_neg = np.clip(y_axis, None, 0.0) * (1.0 + params.y_neg_gain_slope * scale)
        waveform[:, 1] = y_pos + y_neg
        cropped, start, end = crop_effective_segment(
            waveform=waveform,
            threshold_ratio=threshold_ratio,
            margin_samples=margin_samples,
        )
        outputs[float(speed_kmh)] = {
            "speed_kmh": float(speed_kmh),
            "sample_spacing_m": float(spacing),
            "sample_rate_hz": float(sample_rate_hz),
            "full_waveform_nT": waveform,
            "cropped_waveform_nT": cropped,
            "crop_start": int(start),
            "crop_end": int(end),
            "full_samples": int(waveform.shape[0]),
            "cropped_samples": int(cropped.shape[0]),
            "peak_abs_xyz": np.max(np.abs(cropped), axis=0).tolist(),
        }
    return outputs


def score_outputs(outputs: dict[float, dict[str, object]]) -> tuple[float, dict[str, float]]:
    speeds = sorted(outputs)
    corrs = []
    peak_ratios = []
    lengths = [int(outputs[s]["cropped_samples"]) for s in speeds]
    z_peaks = []
    x_peaks = []
    y_peaks = []
    x_pos_peaks = []
    x_neg_peaks = []
    z_pos_peaks = []
    y_pos_peaks = []
    for s in speeds:
        wf = np.asarray(outputs[s]["cropped_waveform_nT"], dtype=np.float64)
        z_peaks.append(float(np.max(np.abs(wf[:, 2]))))
        x_peaks.append(float(np.max(np.abs(wf[:, 0]))))
        y_peaks.append(float(np.max(np.abs(wf[:, 1]))))
        x_pos_peaks.append(float(np.max(wf[:, 0])))
        x_neg_peaks.append(float(-np.min(wf[:, 0])))
        z_pos_peaks.append(float(np.max(wf[:, 2])))
        y_pos_peaks.append(float(np.max(wf[:, 1])))
    for a, b in zip(speeds[:-1], speeds[1:]):
        wa = np.asarray(outputs[a]["cropped_waveform_nT"], dtype=np.float64)
        wb = np.asarray(outputs[b]["cropped_waveform_nT"], dtype=np.float64)
        za = resample_to_length(wa[:, 2], 160)
        zb = resample_to_length(wb[:, 2], 160)
        xa = resample_to_length(wa[:, 0], 160)
        xb = resample_to_length(wb[:, 0], 160)
        ya = resample_to_length(wa[:, 1], 160)
        yb = resample_to_length(wb[:, 1], 160)
        corrs.append(
            0.35 * normalized_corr(za, zb) + 0.25 * normalized_corr(xa, xb) + 0.40 * normalized_corr(ya, yb)
        )
    peak_ratios.extend([max(z_peaks) / max(min(z_peaks), 1e-9), max(x_peaks) / max(min(x_peaks), 1e-9)])

    avg_corr = float(np.mean(corrs))
    max_peak_ratio = float(np.max(peak_ratios))
    monotonic_penalty = 0.0 if all(lengths[i] > lengths[i + 1] for i in range(len(lengths) - 1)) else 1.0
    y_monotonic_penalty = 0.0 if all(y_peaks[i] > y_peaks[i + 1] for i in range(len(y_peaks) - 1)) else 1.0
    y_pos_monotonic_penalty = 0.0 if all(y_pos_peaks[i] > y_pos_peaks[i + 1] for i in range(len(y_pos_peaks) - 1)) else 1.0
    x_pos_monotonic_penalty = 0.0 if all(x_pos_peaks[i] >= x_pos_peaks[i + 1] - 1.0 for i in range(len(x_pos_peaks) - 1)) else 1.0
    x_neg_monotonic_penalty = 0.0 if all(x_neg_peaks[i] > x_neg_peaks[i + 1] for i in range(len(x_neg_peaks) - 1)) else 1.0
    z_pos_monotonic_penalty = 0.0 if all(z_pos_peaks[i] >= z_pos_peaks[i + 1] - 2.0 for i in range(len(z_pos_peaks) - 1)) else 1.0
    y_ratio = max(y_peaks) / max(min(y_peaks), 1e-9)
    x_pos_ratio = max(x_pos_peaks) / max(min(x_pos_peaks), 1e-9)
    x_neg_ratio = max(x_neg_peaks) / max(min(x_neg_peaks), 1e-9)
    z_pos_ratio = max(z_pos_peaks) / max(min(z_pos_peaks), 1e-9)
    corr_penalty = abs(avg_corr - 0.920)
    peak_penalty = max(0.0, max_peak_ratio - 1.28) + max(0.0, 0.88 - min(peak_ratios))
    y_ratio_penalty = max(0.0, 1.25 - y_ratio) + max(0.0, y_ratio - 1.85)
    x_pos_ratio_penalty = max(0.0, 1.05 - x_pos_ratio) + max(0.0, x_pos_ratio - 1.35)
    x_neg_ratio_penalty = max(0.0, 1.08 - x_neg_ratio) + max(0.0, x_neg_ratio - 1.35)
    z_pos_ratio_penalty = max(0.0, 1.08 - z_pos_ratio) + max(0.0, z_pos_ratio - 1.35)
    score = (
        corr_penalty
        + 0.45 * peak_penalty
        + 0.80 * y_ratio_penalty
        + 0.55 * x_pos_ratio_penalty
        + 0.35 * x_neg_ratio_penalty
        + 0.35 * z_pos_ratio_penalty
        + 1.5 * monotonic_penalty
        + 2.0 * y_monotonic_penalty
        + 2.2 * y_pos_monotonic_penalty
        + 0.8 * x_pos_monotonic_penalty
        + 0.8 * x_neg_monotonic_penalty
        + 0.4 * z_pos_monotonic_penalty
    )
    diagnostics = {
        "avg_adjacent_corr": avg_corr,
        "max_peak_ratio": max_peak_ratio,
        "lengths_ok": float(1.0 - monotonic_penalty),
        "y_lengths_ok": float(1.0 - y_monotonic_penalty),
        "y_peak_ratio": float(y_ratio),
        "y_pos_lengths_ok": float(1.0 - y_pos_monotonic_penalty),
        "x_pos_lengths_ok": float(1.0 - x_pos_monotonic_penalty),
        "x_neg_lengths_ok": float(1.0 - x_neg_monotonic_penalty),
        "z_pos_lengths_ok": float(1.0 - z_pos_monotonic_penalty),
        "x_pos_ratio": float(x_pos_ratio),
        "x_neg_ratio": float(x_neg_ratio),
        "z_pos_ratio": float(z_pos_ratio),
    }
    return score, diagnostics


def auto_select_params(
    model: dict[str, object],
    reference_speed_kmh: float,
    reference_samples: int,
    sample_rate_hz: float,
    target_speeds_kmh: list[float],
    threshold_ratio: float,
    margin_samples: int,
) -> tuple[MorphologyParams, dict[float, dict[str, object]], dict[str, float]]:
    best_score = math.inf
    best_params = None
    best_outputs = None
    best_diag = None

    tau_candidates = [0.010]
    y_candidates = [0.08, 0.10, 0.12]
    z_candidates = [0.10, 0.12, 0.14]
    phase_candidates = [-0.35, -0.30, -0.25]
    gain_candidates = [0.0]
    y_axis_gain_candidates = [-0.34, -0.30, -0.26]
    x_axis_gain_candidates = [-0.16, -0.10, 0.0]
    z_axis_gain_candidates = [-0.12, -0.06, 0.0]
    y_pos_gain_candidates = [-0.20, -0.10, 0.0]
    y_neg_gain_candidates = [0.0, 0.08, 0.15]

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
                                                reference_speed_kmh=reference_speed_kmh,
                                                reference_samples=reference_samples,
                                                sample_rate_hz=sample_rate_hz,
                                                target_speeds_kmh=target_speeds_kmh,
                                                params=params,
                                                threshold_ratio=threshold_ratio,
                                                margin_samples=margin_samples,
                                            )
                                            score, diag = score_outputs(outputs)
                                            if score < best_score:
                                                best_score = score
                                                best_params = params
                                                best_outputs = outputs
                                                best_diag = diag

    assert best_params is not None and best_outputs is not None and best_diag is not None
    return best_params, best_outputs, best_diag


def save_outputs(outputs: dict[float, dict[str, object]], output_dir: Path) -> None:
    summary_lines = [
        "speed_kmh,full_samples,cropped_samples,crop_start,crop_end,sample_spacing_m,peak_abs_x,peak_abs_y,peak_abs_z"
    ]
    for speed_kmh in sorted(outputs):
        item = outputs[speed_kmh]
        peaks = item["peak_abs_xyz"]
        summary_lines.append(
            ",".join(
                [
                    f"{speed_kmh:.0f}",
                    str(item["full_samples"]),
                    str(item["cropped_samples"]),
                    str(item["crop_start"]),
                    str(item["crop_end"]),
                    f"{float(item['sample_spacing_m']):.8f}",
                    f"{float(peaks[0]):.8f}",
                    f"{float(peaks[1]):.8f}",
                    f"{float(peaks[2]):.8f}",
                ]
            )
        )
        wf = np.asarray(item["cropped_waveform_nT"], dtype=np.float64)
        lines = ["sample_local,Bx_nT,By_nT,Bz_nT,mag_nT"]
        mag = np.linalg.norm(wf, axis=1)
        for i in range(wf.shape[0]):
            lines.append(f"{i},{wf[i,0]:.8f},{wf[i,1]:.8f},{wf[i,2]:.8f},{mag[i]:.8f}")
        (output_dir / f"morph_waveform_{int(speed_kmh)}kmh.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "morph_summary.csv").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def plot_literature_style(outputs: dict[float, dict[str, object]], output_dir: Path) -> None:
    configure_plot_style()
    fig, ax = plt.subplots(figsize=(10.8, 6.4))
    colors = {"x": "#e45756", "y": "#54a24b", "z": "#4c78a8"}
    gap = 16
    cursor = 0
    all_values = np.vstack([np.asarray(outputs[s]["cropped_waveform_nT"], dtype=np.float64) for s in sorted(outputs)])
    y_min = float(np.min(all_values))
    y_max = float(np.max(all_values))
    y_span = max(y_max - y_min, 1.0)

    for idx, speed_kmh in enumerate(sorted(outputs)):
        wf = np.asarray(outputs[speed_kmh]["cropped_waveform_nT"], dtype=np.float64)
        x = cursor + np.arange(wf.shape[0], dtype=np.float64)
        ax.plot(x, wf[:, 0], color=colors["x"], linewidth=1.8, label="X轴" if idx == 0 else None)
        ax.plot(x, wf[:, 1], color=colors["y"], linewidth=1.8, label="Y轴" if idx == 0 else None)
        ax.plot(x, wf[:, 2], color=colors["z"], linewidth=1.8, label="Z轴" if idx == 0 else None)

        z_peak_idx = int(np.argmax(wf[:, 2]))
        peak_x = float(x[z_peak_idx])
        peak_y = float(wf[z_peak_idx, 2])
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
            cursor + (wf.shape[0] - 1) / 2.0,
            y_min - 0.08 * y_span,
            f"{wf.shape[0]}点",
            ha="center",
            va="top",
            fontsize=12,
        )
        cursor += wf.shape[0] + gap

    ax.set_xlim(-3, cursor - gap + 3)
    ax.set_ylim(y_min - 0.16 * y_span, y_max + 0.20 * y_span)
    ax.set_xlabel("采样点")
    ax.set_ylabel("磁场扰动 / nT")
    ax.grid(True, alpha=0.25)
    ax.legend(
        loc="lower right",
        bbox_to_anchor=(0.985, 0.14),
        borderaxespad=0.2,
        frameon=True,
    )
    fig.tight_layout()
    fig.savefig(output_dir / "speed_morphology_literature_style.png", dpi=220)
    plt.close(fig)


def plot_overlay(outputs: dict[float, dict[str, object]], output_dir: Path) -> None:
    configure_plot_style()
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=False)
    speed_colors = {20.0: "#4c78a8", 30.0: "#72b7b2", 40.0: "#54a24b", 50.0: "#e45756", 60.0: "#f58518"}
    labels = ["X轴", "Y轴", "Z轴"]
    for axis, ax in enumerate(axes):
        for speed_kmh in sorted(outputs):
            wf = np.asarray(outputs[speed_kmh]["cropped_waveform_nT"], dtype=np.float64)
            ax.plot(
                np.arange(wf.shape[0]),
                wf[:, axis],
                linewidth=1.8,
                color=speed_colors.get(speed_kmh, None),
                label=f"{int(speed_kmh)} km/h（{wf.shape[0]}点）",
            )
        ax.set_ylabel(f"{labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("截取后的局部采样点")
    fig.tight_layout()
    fig.savefig(output_dir / "speed_morphology_overlay.png", dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a literature-style figure with both duration and local morphology changes.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--fit-results", type=Path, default=FIT_RESULTS_PATH, help="fit_results.json from the selected dipole model")
    parser.add_argument("--speeds", type=float, nargs="+", default=[20.0, 30.0, 40.0, 50.0], help="target speeds in km/h")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--threshold-ratio", type=float, default=0.10, help="cropping threshold ratio")
    parser.add_argument("--margin-samples", type=int, default=6, help="extra samples around the effective segment")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for generated artifacts")
    parser.add_argument("--tau-s", type=float, default=None, help="override RC time constant in seconds")
    parser.add_argument("--y-shift-m", type=float, default=None, help="override max lateral shift across the speed range")
    parser.add_argument("--z-shift-m", type=float, default=None, help="override max vertical shift across the speed range")
    parser.add_argument("--phase-shift-samples", type=float, default=None, help="override max sampling phase shift across the speed range")
    parser.add_argument("--gain-slope", type=float, default=None, help="override max magnetic moment gain variation across the speed range")
    parser.add_argument("--y-axis-gain-slope", type=float, default=None, help="override extra Y-axis observation gain variation across the speed range")
    parser.add_argument("--x-axis-gain-slope", type=float, default=None, help="override X-axis gain variation across the speed range")
    parser.add_argument("--z-axis-gain-slope", type=float, default=None, help="override Z-axis gain variation across the speed range")
    parser.add_argument("--y-pos-gain-slope", type=float, default=None, help="override positive Y-lobe gain variation across the speed range")
    parser.add_argument("--y-neg-gain-slope", type=float, default=None, help="override negative Y-lobe gain variation across the speed range")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    model = load_best_model(args.fit_results)

    manual_override = any(
        value is not None
        for value in [
            args.tau_s,
            args.y_shift_m,
            args.z_shift_m,
            args.phase_shift_samples,
            args.gain_slope,
            args.y_axis_gain_slope,
            args.x_axis_gain_slope,
            args.z_axis_gain_slope,
            args.y_pos_gain_slope,
            args.y_neg_gain_slope,
        ]
    )

    if manual_override:
        params = MorphologyParams(
            tau_s=0.0 if args.tau_s is None else float(args.tau_s),
            y_shift_m=0.0 if args.y_shift_m is None else float(args.y_shift_m),
            z_shift_m=0.0 if args.z_shift_m is None else float(args.z_shift_m),
            phase_shift_samples=0.0 if args.phase_shift_samples is None else float(args.phase_shift_samples),
            gain_slope=0.0 if args.gain_slope is None else float(args.gain_slope),
            y_axis_gain_slope=0.0 if args.y_axis_gain_slope is None else float(args.y_axis_gain_slope),
            x_axis_gain_slope=0.0 if args.x_axis_gain_slope is None else float(args.x_axis_gain_slope),
            z_axis_gain_slope=0.0 if args.z_axis_gain_slope is None else float(args.z_axis_gain_slope),
            y_pos_gain_slope=0.0 if args.y_pos_gain_slope is None else float(args.y_pos_gain_slope),
            y_neg_gain_slope=0.0 if args.y_neg_gain_slope is None else float(args.y_neg_gain_slope),
        )
        outputs = generate_waveforms(
            model=model,
            reference_speed_kmh=float(waveform.speed_kmh),
            reference_samples=int(waveform.delta_xyz.shape[0]),
            sample_rate_hz=args.sample_rate,
            target_speeds_kmh=[float(x) for x in args.speeds],
            params=params,
            threshold_ratio=args.threshold_ratio,
            margin_samples=args.margin_samples,
        )
        _, diag = score_outputs(outputs)
    else:
        params, outputs, diag = auto_select_params(
            model=model,
            reference_speed_kmh=float(waveform.speed_kmh),
            reference_samples=int(waveform.delta_xyz.shape[0]),
            sample_rate_hz=args.sample_rate,
            target_speeds_kmh=[float(x) for x in args.speeds],
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
        "morphology_params": asdict(params),
        "diagnostics": diag,
    }
    (args.output_dir / "generation_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Generated morphology-aware demo for speeds: {', '.join(str(int(x)) for x in args.speeds)} km/h")
    print(json.dumps(payload["morphology_params"], ensure_ascii=False))
    print(json.dumps(payload["diagnostics"], ensure_ascii=False))
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
