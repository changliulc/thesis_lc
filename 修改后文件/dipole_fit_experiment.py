from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import differential_evolution, least_squares
from scipy.signal import savgol_filter


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
OUTPUT_DIR = ROOT / "tmp" / "dipole_fit"
XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
MU0_OVER_4PI_NT = 100.0


@dataclass
class VehicleWaveform:
    raw_xyz: np.ndarray
    delta_xyz: np.ndarray
    baseline_xyz: np.ndarray
    speed_kmh: float
    status: np.ndarray
    metadata: np.ndarray


@dataclass
class FitSummary:
    dipoles: int
    objective: float
    weighted_rmse: float
    raw_vector_rmse: float
    per_axis_rmse: list[float]
    per_axis_r2: list[float]
    bic: float
    sample_spacing_m: float
    inferred_sample_rate_hz: float
    center_sample: float
    y0_m: float
    z0_m: float
    x_offsets_m: list[list[float]]
    moments_Am2: list[list[float]]
    optimization: dict[str, float | int | str]


def parse_xlsx_numeric(path: Path) -> np.ndarray:
    with zipfile.ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        relationships = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", XLSX_NS):
                texts = [node.text or "" for node in si.iterfind(".//a:t", XLSX_NS)]
                shared_strings.append("".join(texts))

        first_sheet = workbook.find("a:sheets", XLSX_NS)[0]
        rel_id = first_sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        sheet_target = rel_map[rel_id].replace("\\", "/")
        sheet_xml = ET.fromstring(zf.read(f"xl/{sheet_target}"))

        rows: list[list[str]] = []
        for row in sheet_xml.findall(".//a:sheetData/a:row", XLSX_NS):
            values: dict[int, str] = {}
            for cell in row.findall("a:c", XLSX_NS):
                ref = cell.attrib["r"]
                match = re.match(r"([A-Z]+)(\d+)", ref)
                if match is None:
                    continue
                col_idx = 0
                for ch in match.group(1):
                    col_idx = col_idx * 26 + (ord(ch) - 64)
                col_idx -= 1
                value_node = cell.find("a:v", XLSX_NS)
                value = "" if value_node is None else (value_node.text or "")
                if cell.attrib.get("t") == "s" and value:
                    value = shared_strings[int(value)]
                values[col_idx] = value
            max_col = max(values) if values else -1
            rows.append([values.get(i, "") for i in range(max_col + 1)])

    numeric_rows = []
    for row in rows:
        numeric_rows.append([float(item) if item != "" else math.nan for item in row])
    return np.asarray(numeric_rows, dtype=float)


def load_vehicle_waveform(path: Path) -> VehicleWaveform:
    workbook = parse_xlsx_numeric(path)
    if workbook.shape[1] < 10:
        raise ValueError(f"unexpected worksheet shape: {workbook.shape}")

    metadata = workbook[0]
    data = workbook[1:]
    return VehicleWaveform(
        raw_xyz=data[:, 0:3],
        delta_xyz=data[:, 3:6],
        baseline_xyz=data[:, 7:10],
        speed_kmh=float(metadata[7]),
        status=data[:, 6].astype(int),
        metadata=metadata,
    )


def smooth_signal(x: np.ndarray, window: int, polyorder: int = 2) -> np.ndarray:
    if window <= 2:
        return x.copy()
    window = min(window, x.shape[0] - (1 - x.shape[0] % 2))
    if window % 2 == 0:
        window -= 1
    if window < polyorder + 2:
        return x.copy()
    return savgol_filter(x, window_length=window, polyorder=polyorder, axis=0, mode="interp")


def preprocess_waveform(
    waveform: VehicleWaveform,
    smooth_window: int,
    tail_len: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    signal = waveform.delta_xyz.astype(np.float64)
    tail_len = min(tail_len, signal.shape[0] // 4)
    edge = np.vstack([signal[:tail_len], signal[-tail_len:]])
    bias = np.median(edge, axis=0, keepdims=True)
    centered = signal - bias
    smoothed = smooth_signal(centered, smooth_window)

    axis_scale = np.maximum(np.sqrt(np.mean(smoothed**2, axis=0)), 10.0)
    mag = np.linalg.norm(smoothed, axis=1)
    mag_scale = float(np.max(mag)) + 1e-9
    sample_weight = 0.35 + 0.65 * (mag / mag_scale)
    return centered, smoothed, sample_weight


def unpack_theta(
    theta: np.ndarray,
    dipoles: int,
) -> tuple[float, float, float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    theta = np.asarray(theta, dtype=np.float64)
    gap_count = max(0, dipoles - 1)
    sample_spacing = theta[0]
    center_sample = theta[1]
    y0 = theta[2]
    z0 = theta[3]
    x_gaps = theta[4 : 4 + gap_count]
    y_rel = theta[4 + gap_count : 4 + 2 * gap_count]
    z_rel = theta[4 + 2 * gap_count : 4 + 3 * gap_count]
    moments = theta[4 + 3 * gap_count :].reshape(dipoles, 3)

    if gap_count == 0:
        x_offsets = np.zeros(1, dtype=np.float64)
        y_offsets = np.zeros(1, dtype=np.float64)
        z_offsets = np.zeros(1, dtype=np.float64)
    else:
        x_offsets = np.concatenate([[0.0], np.cumsum(x_gaps)])
        x_offsets -= np.mean(x_offsets)
        y_offsets = np.concatenate([[0.0], y_rel])
        y_offsets -= np.mean(y_offsets)
        z_offsets = np.concatenate([[0.0], z_rel])
        z_offsets -= np.mean(z_offsets)
    return sample_spacing, center_sample, y0, z0, x_offsets, y_offsets, z_offsets, moments


def dipole_field_nT(moment: np.ndarray, position: np.ndarray) -> np.ndarray:
    r2 = np.sum(position**2, axis=-1, keepdims=True)
    r = np.sqrt(np.maximum(r2, 1e-12))
    m_dot_r = np.sum(moment * position, axis=-1, keepdims=True)
    return MU0_OVER_4PI_NT * ((3.0 * position * m_dot_r) / np.maximum(r, 1e-12) ** 5 - moment / np.maximum(r, 1e-12) ** 3)


def simulate_multidipole(theta: np.ndarray, length: int, dipoles: int) -> np.ndarray:
    sample_spacing, center_sample, y0, z0, x_offsets, y_offsets, z_offsets, moments = unpack_theta(theta, dipoles)

    x_track = sample_spacing * (np.arange(length, dtype=np.float64) - center_sample)
    prediction = np.zeros((length, 3), dtype=np.float64)
    for idx in range(dipoles):
        position = np.column_stack(
            [
                x_track + x_offsets[idx],
                np.full(length, y0 + y_offsets[idx], dtype=np.float64),
                np.full(length, z0 + z_offsets[idx], dtype=np.float64),
            ]
        )
        prediction += dipole_field_nT(moments[idx][None, :], position)
    return prediction


def build_bounds(dipoles: int) -> tuple[np.ndarray, np.ndarray]:
    return build_bounds_config(dipoles)


def build_bounds_config(
    dipoles: int,
    spacing_bounds: tuple[float, float] = (0.08, 0.35),
    center_bounds: tuple[float, float] = (15.0, 85.0),
    y0_bounds: tuple[float, float] = (0.8, 4.5),
    z0_bounds: tuple[float, float] = (0.1, 2.8),
    x_gap_bounds: tuple[float, float] = (0.25, 6.0),
    yz_offset_bound: float = 2.5,
    moment_bound: float = 400.0,
) -> tuple[np.ndarray, np.ndarray]:
    gap_count = max(0, dipoles - 1)
    lower = [spacing_bounds[0], center_bounds[0], y0_bounds[0], z0_bounds[0]]
    upper = [spacing_bounds[1], center_bounds[1], y0_bounds[1], z0_bounds[1]]
    lower.extend([x_gap_bounds[0]] * gap_count)
    upper.extend([x_gap_bounds[1]] * gap_count)
    lower.extend([-yz_offset_bound] * gap_count)
    upper.extend([yz_offset_bound] * gap_count)
    lower.extend([-yz_offset_bound] * gap_count)
    upper.extend([yz_offset_bound] * gap_count)
    lower.extend([-moment_bound] * (3 * dipoles))
    upper.extend([moment_bound] * (3 * dipoles))
    return np.asarray(lower, dtype=np.float64), np.asarray(upper, dtype=np.float64)


class DipoleFitter:
    def __init__(
        self,
        observed: np.ndarray,
        sample_weight: np.ndarray,
        nominal_spacing_m: float | None = None,
        spacing_sigma_m: float = 0.04,
        vehicle_length_prior_m: float | None = None,
        vehicle_length_sigma_m: float = 1.0,
    ):
        self.observed = observed
        self.length = observed.shape[0]
        self.axis_scale = np.maximum(np.sqrt(np.mean(observed**2, axis=0)), 10.0)
        self.sample_weight = np.asarray(sample_weight, dtype=np.float64)
        self.nominal_spacing_m = nominal_spacing_m
        self.spacing_sigma_m = spacing_sigma_m
        self.vehicle_length_prior_m = vehicle_length_prior_m
        self.vehicle_length_sigma_m = vehicle_length_sigma_m

    def residual_vector(self, theta: np.ndarray, dipoles: int) -> np.ndarray:
        prediction = simulate_multidipole(theta, self.length, dipoles)
        residual = (prediction - self.observed) / self.axis_scale
        residual *= np.sqrt(self.sample_weight)[:, None]

        sample_spacing, _, _, _, x_offsets, y_offsets, z_offsets, moments = unpack_theta(theta, dipoles)
        total_length = float(x_offsets.max() - x_offsets.min()) if dipoles > 1 else 0.0
        reg_terms = [
            5e-3 * moments.reshape(-1) / 120.0,
            5e-3 * y_offsets.reshape(-1) / 0.6,
            5e-3 * z_offsets.reshape(-1) / 0.6,
            np.asarray([5e-3 * max(0.0, total_length - 10.0)]),
        ]
        if self.nominal_spacing_m is not None:
            reg_terms.append(
                np.asarray([2.0 * (sample_spacing - self.nominal_spacing_m) / max(self.spacing_sigma_m, 1e-6)])
            )
        if self.vehicle_length_prior_m is not None and dipoles > 1:
            reg_terms.append(
                np.asarray([(total_length - self.vehicle_length_prior_m) / max(self.vehicle_length_sigma_m, 1e-6)])
            )
        reg = np.concatenate(reg_terms)
        return np.concatenate([residual.reshape(-1), reg])

    def objective(self, theta: np.ndarray, dipoles: int) -> float:
        res = self.residual_vector(theta, dipoles)
        return float(np.mean(res**2))


def fit_single_model(
    fitter: DipoleFitter,
    observed_raw: np.ndarray,
    speed_kmh: float,
    dipoles: int,
    de_maxiter: int,
    de_popsize: int,
    ls_max_nfev: int,
    seed: int,
    restarts: int = 1,
    spacing_bounds: tuple[float, float] = (0.08, 0.35),
    center_bounds: tuple[float, float] = (15.0, 85.0),
    y0_bounds: tuple[float, float] = (0.8, 4.5),
    z0_bounds: tuple[float, float] = (0.1, 2.8),
    x_gap_bounds: tuple[float, float] = (0.25, 6.0),
    yz_offset_bound: float = 2.5,
    moment_bound: float = 400.0,
) -> tuple[FitSummary, np.ndarray]:
    lower, upper = build_bounds_config(
        dipoles=dipoles,
        spacing_bounds=spacing_bounds,
        center_bounds=center_bounds,
        y0_bounds=y0_bounds,
        z0_bounds=z0_bounds,
        x_gap_bounds=x_gap_bounds,
        yz_offset_bound=yz_offset_bound,
        moment_bound=moment_bound,
    )
    bounds = list(zip(lower, upper))

    best_de_result = None
    best_ls_result = None
    best_objective = math.inf
    for restart_idx in range(restarts):
        de_result = differential_evolution(
            lambda x: fitter.objective(x, dipoles),
            bounds=bounds,
            strategy="best1bin",
            maxiter=de_maxiter,
            popsize=de_popsize,
            tol=1e-4,
            mutation=(0.5, 1.0),
            recombination=0.7,
            polish=False,
            seed=seed + 1009 * restart_idx,
            init="latinhypercube",
            updating="deferred",
            workers=1,
        )

        ls_result = least_squares(
            lambda x: fitter.residual_vector(x, dipoles),
            x0=de_result.x,
            bounds=(lower, upper),
            method="trf",
            loss="soft_l1",
            f_scale=0.5,
            max_nfev=ls_max_nfev,
            xtol=1e-8,
            ftol=1e-8,
            gtol=1e-8,
        )
        objective = float(ls_result.cost * 2.0 / len(fitter.residual_vector(ls_result.x, dipoles)))
        if objective < best_objective:
            best_objective = objective
            best_de_result = de_result
            best_ls_result = ls_result

    de_result = best_de_result
    ls_result = best_ls_result

    prediction = simulate_multidipole(ls_result.x, fitter.length, dipoles)
    raw_residual = observed_raw - prediction
    weighted_residual = fitter.residual_vector(ls_result.x, dipoles)
    fit_residual = weighted_residual[: fitter.length * 3]
    per_axis_rmse = np.sqrt(np.mean(raw_residual**2, axis=0))
    total_rmse = float(np.sqrt(np.mean(np.sum(raw_residual**2, axis=1))))

    per_axis_r2 = []
    for axis in range(3):
        ss_res = float(np.sum(raw_residual[:, axis] ** 2))
        centered = observed_raw[:, axis] - float(np.mean(observed_raw[:, axis]))
        ss_tot = float(np.sum(centered**2))
        per_axis_r2.append(1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0)

    n_obs = observed_raw.size
    rss = float(np.sum(raw_residual**2))
    param_count = len(ls_result.x)
    bic = n_obs * math.log(max(rss / n_obs, 1e-12)) + param_count * math.log(n_obs)

    sample_spacing, center_sample, y0, z0, x_offsets, y_offsets, z_offsets, moments = unpack_theta(ls_result.x, dipoles)
    speed_mps = speed_kmh / 3.6
    sample_rate = (observed_raw.shape[0] and (fitter.length > 0) and (speed_mps / sample_spacing)) or math.nan

    summary = FitSummary(
        dipoles=dipoles,
        objective=float(ls_result.cost * 2.0 / len(weighted_residual)),
        weighted_rmse=float(np.sqrt(np.mean(fit_residual**2))),
        raw_vector_rmse=total_rmse,
        per_axis_rmse=[float(x) for x in per_axis_rmse],
        per_axis_r2=[float(x) for x in per_axis_r2],
        bic=float(bic),
        sample_spacing_m=float(sample_spacing),
        inferred_sample_rate_hz=float(sample_rate),
        center_sample=float(center_sample),
        y0_m=float(y0),
        z0_m=float(z0),
        x_offsets_m=[[float(x), float(y), float(z)] for x, y, z in zip(x_offsets, y_offsets, z_offsets)],
        moments_Am2=[[float(v) for v in row] for row in moments],
        optimization={
            "de_fun": float(de_result.fun),
            "de_nit": int(de_result.nit),
            "de_nfev": int(de_result.nfev),
            "ls_cost": float(ls_result.cost),
            "ls_nfev": int(ls_result.nfev),
            "ls_status": int(ls_result.status),
            "ls_message": ls_result.message,
            "restarts": int(restarts),
        },
    )
    return summary, prediction


def plot_observed_signal(observed_raw: np.ndarray, observed_fit: np.ndarray, output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9, 6), sharex=True)
    labels = ["X", "Y", "Z"]
    for idx, ax in enumerate(axes):
        ax.plot(observed_raw[:, idx], color="#4c78a8", linewidth=1.4, label="raw delta")
        ax.plot(observed_fit[:, idx], color="#f58518", linewidth=1.8, label="smoothed fit target")
        ax.set_ylabel(f"{labels[idx]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("sample")
    fig.tight_layout()
    fig.savefig(output_dir / "observed_waveform.png", dpi=220)
    plt.close(fig)


def plot_fit_comparison(
    observed_raw: np.ndarray,
    predictions: dict[int, np.ndarray],
    summaries: dict[int, FitSummary],
    output_dir: Path,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    labels = ["X", "Y", "Z"]
    colors = {1: "#e45756", 2: "#4c78a8", 3: "#54a24b", 4: "#b279a2", 5: "#9d755d"}
    for axis, ax in enumerate(axes):
        ax.plot(observed_raw[:, axis], color="black", linewidth=1.8, label="observed")
        for dipoles, prediction in predictions.items():
            summary = summaries[dipoles]
            ax.plot(
                prediction[:, axis],
                linewidth=1.4,
                color=colors.get(dipoles, None),
                label=f"{dipoles} dipoles (RMSE={summary.per_axis_rmse[axis]:.1f})",
            )
        ax.set_ylabel(f"{labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("sample")
    fig.tight_layout()
    fig.savefig(output_dir / "fit_comparison.png", dpi=220)
    plt.close(fig)


def plot_best_fit(
    observed_raw: np.ndarray,
    best_prediction: np.ndarray,
    summary: FitSummary,
    output_dir: Path,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9, 6), sharex=True)
    labels = ["X", "Y", "Z"]
    for axis, ax in enumerate(axes):
        ax.plot(observed_raw[:, axis], color="black", linewidth=1.8, label="observed")
        ax.plot(best_prediction[:, axis], color="#4c78a8", linewidth=1.8, label="best fit")
        ax.set_ylabel(f"{labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right")
    axes[0].set_title(
        f"Best fit: {summary.dipoles} dipoles, vector RMSE={summary.raw_vector_rmse:.2f} nT, "
        f"BIC={summary.bic:.1f}"
    )
    axes[-1].set_xlabel("sample")
    fig.tight_layout()
    fig.savefig(output_dir / "best_fit.png", dpi=220)
    plt.close(fig)


def save_results(
    summaries: dict[int, FitSummary],
    predictions: dict[int, np.ndarray],
    observed_raw: np.ndarray,
    observed_fit: np.ndarray,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_observed_signal(observed_raw, observed_fit, output_dir)
    plot_fit_comparison(observed_raw, predictions, summaries, output_dir)

    best = min(summaries.values(), key=lambda item: item.bic)
    plot_best_fit(observed_raw, predictions[best.dipoles], best, output_dir)

    result_payload = {
        "best_by_bic": best.dipoles,
        "models": {str(k): asdict(v) for k, v in summaries.items()},
    }
    (output_dir / "fit_results.json").write_text(json.dumps(result_payload, indent=2), encoding="utf-8")

    lines = [
        "dipoles,objective,weighted_rmse,raw_vector_rmse,bic,sample_spacing_m,inferred_sample_rate_hz,"
        "center_sample,y0_m,z0_m,rmse_x,rmse_y,rmse_z,r2_x,r2_y,r2_z"
    ]
    for k in sorted(summaries):
        item = summaries[k]
        lines.append(
            ",".join(
                [
                    str(item.dipoles),
                    f"{item.objective:.8f}",
                    f"{item.weighted_rmse:.8f}",
                    f"{item.raw_vector_rmse:.8f}",
                    f"{item.bic:.8f}",
                    f"{item.sample_spacing_m:.8f}",
                    f"{item.inferred_sample_rate_hz:.8f}",
                    f"{item.center_sample:.8f}",
                    f"{item.y0_m:.8f}",
                    f"{item.z0_m:.8f}",
                    *(f"{x:.8f}" for x in item.per_axis_rmse),
                    *(f"{x:.8f}" for x in item.per_axis_r2),
                ]
            )
        )
    (output_dir / "fit_summary.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit a moving multi-dipole model to the provided vehicle waveform.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--dipoles", type=int, nargs="+", default=[1, 2, 3, 4], help="dipole counts to evaluate")
    parser.add_argument("--smooth-window", type=int, default=7, help="Savitzky-Golay window for the fit target")
    parser.add_argument("--de-maxiter", type=int, default=90, help="differential evolution generations")
    parser.add_argument("--de-popsize", type=int, default=18, help="differential evolution population scale")
    parser.add_argument("--ls-max-nfev", type=int, default=4000, help="least-squares max evaluations")
    parser.add_argument("--restarts", type=int, default=1, help="number of DE+LS restarts per dipole count")
    parser.add_argument(
        "--nominal-sample-period",
        type=float,
        default=0.02,
        help="soft prior on the sample period in seconds; use 0 to disable",
    )
    parser.add_argument(
        "--spacing-prior-sigma",
        type=float,
        default=0.04,
        help="standard deviation for the sample-spacing prior in meters",
    )
    parser.add_argument(
        "--vehicle-length-prior",
        type=float,
        default=0.0,
        help="soft prior on total dipole x-span in meters; use 0 to disable",
    )
    parser.add_argument(
        "--vehicle-length-sigma",
        type=float,
        default=1.2,
        help="standard deviation for the vehicle-length prior in meters",
    )
    parser.add_argument("--x-gap-max", type=float, default=6.0, help="upper bound for x-gap between dipoles (m)")
    parser.add_argument("--yz-offset-bound", type=float, default=2.5, help="absolute bound for relative y/z offsets (m)")
    parser.add_argument("--moment-bound", type=float, default=400.0, help="absolute bound for each moment component (Am^2)")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for plots and metrics")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    observed_raw, observed_fit, sample_weight = preprocess_waveform(waveform, smooth_window=args.smooth_window)
    nominal_spacing = None
    if args.nominal_sample_period > 0:
        nominal_spacing = (waveform.speed_kmh / 3.6) * args.nominal_sample_period
    vehicle_length_prior = args.vehicle_length_prior if args.vehicle_length_prior > 0 else None
    fitter = DipoleFitter(
        observed_fit,
        sample_weight,
        nominal_spacing_m=nominal_spacing,
        spacing_sigma_m=args.spacing_prior_sigma,
        vehicle_length_prior_m=vehicle_length_prior,
        vehicle_length_sigma_m=args.vehicle_length_sigma,
    )

    summaries: dict[int, FitSummary] = {}
    predictions: dict[int, np.ndarray] = {}
    for dipoles in args.dipoles:
        summary, prediction = fit_single_model(
            fitter=fitter,
            observed_raw=observed_raw,
            speed_kmh=waveform.speed_kmh,
            dipoles=dipoles,
            de_maxiter=args.de_maxiter,
            de_popsize=args.de_popsize,
            ls_max_nfev=args.ls_max_nfev,
            seed=args.seed + dipoles,
            restarts=args.restarts,
            x_gap_bounds=(0.25, args.x_gap_max),
            yz_offset_bound=args.yz_offset_bound,
            moment_bound=args.moment_bound,
        )
        summaries[dipoles] = summary
        predictions[dipoles] = prediction
        print(
            f"[dipoles={dipoles}] vector_rmse={summary.raw_vector_rmse:.3f} nT, "
            f"bic={summary.bic:.2f}, spacing={summary.sample_spacing_m:.3f} m/sample, "
            f"fs≈{summary.inferred_sample_rate_hz:.1f} Hz"
        )

    save_results(summaries, predictions, observed_raw, observed_fit, args.output_dir)
    best = min(summaries.values(), key=lambda item: item.bic)
    print(f"Best model by BIC: {best.dipoles} dipoles")
    print(f"Artifacts written to: {args.output_dir}")


if __name__ == "__main__":
    main()
