from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import differential_evolution, least_squares

from dipole_fit_experiment import load_vehicle_waveform, preprocess_waveform


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(__file__).resolve().with_name("单个中型车数据_速度55公里每小时.xlsx")
OUTPUT_DIR = ROOT / "tmp" / "dipole_fit_fixed_50hz"
MU0_OVER_4PI_NT = 100.0


@dataclass
class FitSummary:
    dipoles: int
    objective: float
    raw_vector_rmse: float
    per_axis_rmse: list[float]
    per_axis_r2: list[float]
    bic: float
    sample_spacing_m: float
    sample_rate_hz: float
    center_sample: float
    y0_m: float
    z0_m: float
    x_offsets_m: list[list[float]]
    moments_Am2: list[list[float]]
    bias_nT: list[float]
    optimization: dict[str, float | int | str]


def unpack_q(q: np.ndarray, dipoles: int) -> tuple[float, float, float, np.ndarray, np.ndarray, np.ndarray]:
    q = np.asarray(q, dtype=np.float64)
    gap_count = max(0, dipoles - 1)
    center_sample = q[0]
    y0 = q[1]
    z0 = q[2]
    x_gaps = q[3 : 3 + gap_count]
    y_rel = q[3 + gap_count : 3 + 2 * gap_count]
    z_rel = q[3 + 2 * gap_count :]

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
    return center_sample, y0, z0, x_offsets, y_offsets, z_offsets


def build_bounds(
    dipoles: int,
    center_bounds: tuple[float, float] = (10.0, 90.0),
    y0_bounds: tuple[float, float] = (0.6, 4.5),
    z0_bounds: tuple[float, float] = (0.15, 2.8),
    x_gap_bounds: tuple[float, float] = (0.25, 3.5),
    yz_offset_bound: float = 1.2,
) -> tuple[np.ndarray, np.ndarray]:
    gap_count = max(0, dipoles - 1)
    lower = [center_bounds[0], y0_bounds[0], z0_bounds[0]]
    upper = [center_bounds[1], y0_bounds[1], z0_bounds[1]]
    lower.extend([x_gap_bounds[0]] * gap_count)
    upper.extend([x_gap_bounds[1]] * gap_count)
    lower.extend([-yz_offset_bound] * gap_count)
    upper.extend([yz_offset_bound] * gap_count)
    lower.extend([-yz_offset_bound] * gap_count)
    upper.extend([yz_offset_bound] * gap_count)
    return np.asarray(lower, dtype=np.float64), np.asarray(upper, dtype=np.float64)


def build_field_matrix(
    q: np.ndarray,
    length: int,
    dipoles: int,
    sample_spacing_m: float,
    include_bias: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    center_sample, y0, z0, x_offsets, y_offsets, z_offsets = unpack_q(q, dipoles)
    x_track = sample_spacing_m * (np.arange(length, dtype=np.float64) - center_sample)

    rows = 3 * length
    cols = 3 * dipoles + (3 if include_bias else 0)
    matrix = np.zeros((rows, cols), dtype=np.float64)

    for idx in range(dipoles):
        x = x_track + x_offsets[idx]
        y = np.full(length, y0 + y_offsets[idx], dtype=np.float64)
        z = np.full(length, z0 + z_offsets[idx], dtype=np.float64)

        r2 = x * x + y * y + z * z
        r = np.sqrt(np.maximum(r2, 1e-12))
        r5 = np.maximum(r2 * r2 * r, 1e-12)

        c11 = MU0_OVER_4PI_NT * (3.0 * x * x - r2) / r5
        c12 = MU0_OVER_4PI_NT * (3.0 * x * y) / r5
        c13 = MU0_OVER_4PI_NT * (3.0 * x * z) / r5
        c21 = MU0_OVER_4PI_NT * (3.0 * x * y) / r5
        c22 = MU0_OVER_4PI_NT * (3.0 * y * y - r2) / r5
        c23 = MU0_OVER_4PI_NT * (3.0 * y * z) / r5
        c31 = MU0_OVER_4PI_NT * (3.0 * x * z) / r5
        c32 = MU0_OVER_4PI_NT * (3.0 * y * z) / r5
        c33 = MU0_OVER_4PI_NT * (3.0 * z * z - r2) / r5

        col = 3 * idx
        matrix[0::3, col + 0] = c11
        matrix[0::3, col + 1] = c12
        matrix[0::3, col + 2] = c13
        matrix[1::3, col + 0] = c21
        matrix[1::3, col + 1] = c22
        matrix[1::3, col + 2] = c23
        matrix[2::3, col + 0] = c31
        matrix[2::3, col + 1] = c32
        matrix[2::3, col + 2] = c33

    if include_bias:
        matrix[0::3, 3 * dipoles + 0] = 1.0
        matrix[1::3, 3 * dipoles + 1] = 1.0
        matrix[2::3, 3 * dipoles + 2] = 1.0

    return matrix, x_offsets, y_offsets, z_offsets


class FixedRateDipoleFitter:
    def __init__(
        self,
        observed_fit: np.ndarray,
        sample_weight: np.ndarray,
        speed_kmh: float,
        sample_rate_hz: float,
        vehicle_length_prior_m: float | None = None,
        vehicle_length_sigma_m: float = 1.0,
        ridge: float = 1e-5,
    ) -> None:
        self.observed = np.asarray(observed_fit, dtype=np.float64)
        self.length = self.observed.shape[0]
        self.axis_scale = np.maximum(np.percentile(np.abs(self.observed), 95, axis=0), 10.0)
        self.sample_weight = np.asarray(sample_weight, dtype=np.float64)
        self.speed_kmh = float(speed_kmh)
        self.sample_rate_hz = float(sample_rate_hz)
        self.sample_spacing_m = (self.speed_kmh / 3.6) / self.sample_rate_hz
        self.vehicle_length_prior_m = vehicle_length_prior_m
        self.vehicle_length_sigma_m = vehicle_length_sigma_m
        self.ridge = ridge
        self.weight_rows = np.repeat(np.sqrt(self.sample_weight), 3) / np.tile(self.axis_scale, self.length)
        self.target_vector = self.observed.reshape(-1)

    def solve_linear(self, q: np.ndarray, dipoles: int, include_bias: bool = True) -> tuple[np.ndarray | None, float, np.ndarray | None]:
        matrix, x_offsets, y_offsets, z_offsets = build_field_matrix(
            q=q,
            length=self.length,
            dipoles=dipoles,
            sample_spacing_m=self.sample_spacing_m,
            include_bias=include_bias,
        )

        center_sample, y0, z0, _, _, _ = unpack_q(q, dipoles)
        x_track = self.sample_spacing_m * (np.arange(self.length, dtype=np.float64) - center_sample)

        y_abs = y0 + y_offsets
        z_abs = z0 + z_offsets
        min_r = math.inf
        for idx in range(dipoles):
            r = np.sqrt((x_track + x_offsets[idx]) ** 2 + y_abs[idx] ** 2 + z_abs[idx] ** 2)
            min_r = min(min_r, float(np.min(r)))

        if (not np.isfinite(min_r)) or min_r < 0.35:
            return None, math.inf, None
        if np.any(y_abs <= 0.15) or np.any(z_abs <= 0.1):
            return None, math.inf, None

        aw = matrix * self.weight_rows[:, None]
        yw = self.target_vector * self.weight_rows
        reg = np.zeros((aw.shape[1], aw.shape[1]), dtype=np.float64)
        reg[: 3 * dipoles, : 3 * dipoles] = np.eye(3 * dipoles) * self.ridge

        ata = aw.T @ aw + reg
        aty = aw.T @ yw
        try:
            beta = np.linalg.solve(ata, aty)
        except np.linalg.LinAlgError:
            beta = np.linalg.lstsq(ata, aty, rcond=None)[0]

        prediction = (matrix @ beta).reshape(self.length, 3)
        residual = ((prediction - self.observed) / self.axis_scale) * np.sqrt(self.sample_weight)[:, None]
        objective = float(np.mean(residual**2))
        return beta, objective, prediction

    def objective_q(self, q: np.ndarray, dipoles: int) -> float:
        beta, objective, prediction = self.solve_linear(q, dipoles)
        if prediction is None:
            return 1e6

        center_sample, y0, z0, x_offsets, y_offsets, z_offsets = unpack_q(q, dipoles)
        del center_sample, y0, z0
        total_length = float(x_offsets.max() - x_offsets.min()) if dipoles > 1 else 0.0
        penalty = 0.0

        if self.vehicle_length_prior_m is not None:
            penalty += 0.03 * ((total_length - self.vehicle_length_prior_m) / self.vehicle_length_sigma_m) ** 2
        penalty += 0.01 * float(np.sum((y_offsets / 0.6) ** 2))
        penalty += 0.01 * float(np.sum((z_offsets / 0.6) ** 2))
        if beta is not None:
            penalty += 5e-4 * float(np.sum((beta[: 3 * dipoles] / 120.0) ** 2))
            if beta.shape[0] >= 3 * dipoles + 3:
                penalty += 5e-4 * float(np.sum((beta[3 * dipoles : 3 * dipoles + 3] / 8.0) ** 2))
        return objective + penalty

    def residuals_for_ls(self, q: np.ndarray, dipoles: int) -> np.ndarray:
        beta, objective, prediction = self.solve_linear(q, dipoles)
        del beta, objective
        if prediction is None:
            return np.full(self.length * 3, 1e3, dtype=np.float64)
        residual = ((prediction - self.observed) / self.axis_scale) * np.sqrt(self.sample_weight)[:, None]
        return residual.reshape(-1)


def fit_single_model(
    fitter: FixedRateDipoleFitter,
    observed_raw: np.ndarray,
    dipoles: int,
    de_maxiter: int,
    de_popsize: int,
    ls_max_nfev: int,
    seed: int,
    restarts: int,
    x_gap_bounds: tuple[float, float],
    yz_offset_bound: float,
) -> tuple[FitSummary, np.ndarray]:
    lower, upper = build_bounds(
        dipoles=dipoles,
        x_gap_bounds=x_gap_bounds,
        yz_offset_bound=yz_offset_bound,
    )

    best_de = None
    best_ls = None
    best_cost = math.inf

    for restart in range(restarts):
        current_seed = seed + 97 * restart
        de_result = differential_evolution(
            func=lambda q: fitter.objective_q(q, dipoles),
            bounds=list(zip(lower, upper)),
            seed=current_seed,
            maxiter=de_maxiter,
            popsize=de_popsize,
            polish=False,
            updating="deferred",
            workers=1,
            tol=0.01,
            mutation=(0.5, 1.0),
            recombination=0.7,
            init="latinhypercube",
        )

        ls_result = least_squares(
            fun=lambda q: fitter.residuals_for_ls(q, dipoles),
            x0=de_result.x,
            bounds=(lower, upper),
            method="trf",
            loss="soft_l1",
            f_scale=1.0,
            max_nfev=ls_max_nfev,
            x_scale="jac",
        )

        beta, objective, prediction = fitter.solve_linear(ls_result.x, dipoles)
        if prediction is None:
            continue
        total_cost = objective + 1e-6 * ls_result.cost
        if total_cost < best_cost:
            best_cost = total_cost
            best_de = de_result
            best_ls = ls_result
            best_beta = beta
            best_prediction = prediction

    if best_ls is None or best_de is None:
        raise RuntimeError(f"no valid solution found for {dipoles} dipoles")

    raw_residual = observed_raw - best_prediction
    per_axis_rmse = np.sqrt(np.mean(raw_residual**2, axis=0))
    total_rmse = float(np.sqrt(np.mean(np.sum(raw_residual**2, axis=1))))
    per_axis_r2: list[float] = []
    for axis in range(3):
        ss_res = float(np.sum(raw_residual[:, axis] ** 2))
        centered = observed_raw[:, axis] - float(np.mean(observed_raw[:, axis]))
        ss_tot = float(np.sum(centered**2))
        per_axis_r2.append(1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0)

    rss = float(np.sum(raw_residual**2))
    n_obs = observed_raw.size
    param_count = len(best_ls.x) + len(best_beta)
    bic = n_obs * math.log(max(rss / n_obs, 1e-12)) + param_count * math.log(n_obs)

    center_sample, y0, z0, x_offsets, y_offsets, z_offsets = unpack_q(best_ls.x, dipoles)
    summary = FitSummary(
        dipoles=dipoles,
        objective=float(best_ls.cost * 2.0 / (fitter.length * 3)),
        raw_vector_rmse=total_rmse,
        per_axis_rmse=[float(x) for x in per_axis_rmse],
        per_axis_r2=[float(x) for x in per_axis_r2],
        bic=float(bic),
        sample_spacing_m=float(fitter.sample_spacing_m),
        sample_rate_hz=float(fitter.sample_rate_hz),
        center_sample=float(center_sample),
        y0_m=float(y0),
        z0_m=float(z0),
        x_offsets_m=[[float(x), float(y), float(z)] for x, y, z in zip(x_offsets, y_offsets, z_offsets)],
        moments_Am2=np.asarray(best_beta[: 3 * dipoles]).reshape(dipoles, 3).tolist(),
        bias_nT=np.asarray(best_beta[3 * dipoles : 3 * dipoles + 3]).tolist(),
        optimization={
            "de_fun": float(best_de.fun),
            "de_nit": int(best_de.nit),
            "de_nfev": int(best_de.nfev),
            "ls_cost": float(best_ls.cost),
            "ls_nfev": int(best_ls.nfev),
            "ls_status": int(best_ls.status),
            "ls_message": best_ls.message,
            "restarts": int(restarts),
        },
    )
    return summary, best_prediction


def plot_fit_comparison(observed_raw: np.ndarray, predictions: dict[int, np.ndarray], summaries: dict[int, FitSummary], output_dir: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    labels = ["X", "Y", "Z"]
    colors = {1: "#e45756", 2: "#4c78a8", 3: "#54a24b", 4: "#b279a2", 5: "#9d755d", 6: "#72b7b2"}
    for axis, ax in enumerate(axes):
        ax.plot(observed_raw[:, axis], color="black", linewidth=1.8, label="observed")
        for dipoles in sorted(predictions):
            summary = summaries[dipoles]
            ax.plot(
                predictions[dipoles][:, axis],
                linewidth=1.4,
                color=colors.get(dipoles),
                label=f"{dipoles} dipoles (RMSE={summary.per_axis_rmse[axis]:.1f})",
            )
        ax.set_ylabel(f"{labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("sample")
    fig.tight_layout()
    fig.savefig(output_dir / "fit_comparison.png", dpi=220)
    plt.close(fig)


def plot_best_fit(observed_raw: np.ndarray, best_prediction: np.ndarray, summary: FitSummary, output_dir: Path) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    labels = ["X", "Y", "Z"]
    for axis, ax in enumerate(axes[:3]):
        ax.plot(observed_raw[:, axis], color="black", linewidth=1.8, label="observed")
        ax.plot(best_prediction[:, axis], color="#4c78a8", linewidth=1.8, label="best fit")
        ax.set_ylabel(f"{labels[axis]} / nT")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper right")

    residual = observed_raw - best_prediction
    axes[3].plot(residual[:, 0], label="Rx", linewidth=1.2)
    axes[3].plot(residual[:, 1], label="Ry", linewidth=1.2)
    axes[3].plot(residual[:, 2], label="Rz", linewidth=1.2)
    axes[3].axhline(0.0, color="black", linewidth=1.0)
    axes[3].set_ylabel("Residual / nT")
    axes[3].set_xlabel("sample")
    axes[3].grid(True, alpha=0.25)
    axes[3].legend(loc="upper right", ncol=3)

    axes[0].set_title(
        f"Best fixed-50Hz fit: {summary.dipoles} dipoles, vector RMSE={summary.raw_vector_rmse:.2f} nT, "
        f"BIC={summary.bic:.1f}"
    )
    fig.tight_layout()
    fig.savefig(output_dir / "best_fit.png", dpi=220)
    plt.close(fig)


def save_results(
    summaries: dict[int, FitSummary],
    predictions: dict[int, np.ndarray],
    observed_raw: np.ndarray,
    output_dir: Path,
    run_config: dict[str, object] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_fit_comparison(observed_raw, predictions, summaries, output_dir)
    best = min(summaries.values(), key=lambda item: item.bic)
    plot_best_fit(observed_raw, predictions[best.dipoles], best, output_dir)

    payload = {"best_by_bic": best.dipoles, "models": {str(k): asdict(v) for k, v in summaries.items()}}
    (output_dir / "fit_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "dipoles,objective,raw_vector_rmse,bic,sample_spacing_m,sample_rate_hz,center_sample,y0_m,z0_m,rmse_x,rmse_y,rmse_z,r2_x,r2_y,r2_z"
    ]
    for dipoles in sorted(summaries):
        item = summaries[dipoles]
        lines.append(
            ",".join(
                [
                    str(item.dipoles),
                    f"{item.objective:.8f}",
                    f"{item.raw_vector_rmse:.8f}",
                    f"{item.bic:.8f}",
                    f"{item.sample_spacing_m:.8f}",
                    f"{item.sample_rate_hz:.8f}",
                    f"{item.center_sample:.8f}",
                    f"{item.y0_m:.8f}",
                    f"{item.z0_m:.8f}",
                    *(f"{x:.8f}" for x in item.per_axis_rmse),
                    *(f"{x:.8f}" for x in item.per_axis_r2),
                ]
            )
        )
    (output_dir / "fit_summary.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if run_config is not None:
        (output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit a moving multi-dipole model with fixed 50 Hz sampling.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="path to the single-vehicle workbook")
    parser.add_argument("--dipoles", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6], help="dipole counts to evaluate")
    parser.add_argument("--sample-rate", type=float, default=50.0, help="fixed sample rate in Hz")
    parser.add_argument("--smooth-window", type=int, default=5, help="Savitzky-Golay window for the fit target")
    parser.add_argument("--de-maxiter", type=int, default=100, help="differential evolution generations")
    parser.add_argument("--de-popsize", type=int, default=18, help="differential evolution population scale")
    parser.add_argument("--ls-max-nfev", type=int, default=5000, help="least-squares max evaluations")
    parser.add_argument("--restarts", type=int, default=2, help="number of DE+LS restarts per dipole count")
    parser.add_argument("--vehicle-length-prior", type=float, default=5.5, help="soft prior on total dipole x-span in meters")
    parser.add_argument("--vehicle-length-sigma", type=float, default=0.9, help="standard deviation for the length prior")
    parser.add_argument("--x-gap-max", type=float, default=3.5, help="upper bound for x-gap between dipoles in meters")
    parser.add_argument("--yz-offset-bound", type=float, default=1.2, help="absolute bound for relative y/z offsets in meters")
    parser.add_argument("--ridge", type=float, default=1e-5, help="ridge coefficient for the linear moment solve")
    parser.add_argument("--seed", type=int, default=2026, help="random seed")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="directory for plots and metrics")
    args = parser.parse_args()

    waveform = load_vehicle_waveform(args.data)
    observed_raw, observed_fit, sample_weight = preprocess_waveform(waveform, smooth_window=args.smooth_window)
    fitter = FixedRateDipoleFitter(
        observed_fit=observed_fit,
        sample_weight=sample_weight,
        speed_kmh=waveform.speed_kmh,
        sample_rate_hz=args.sample_rate,
        vehicle_length_prior_m=args.vehicle_length_prior if args.vehicle_length_prior > 0 else None,
        vehicle_length_sigma_m=args.vehicle_length_sigma,
        ridge=args.ridge,
    )

    summaries: dict[int, FitSummary] = {}
    predictions: dict[int, np.ndarray] = {}
    for dipoles in args.dipoles:
        summary, prediction = fit_single_model(
            fitter=fitter,
            observed_raw=observed_raw,
            dipoles=dipoles,
            de_maxiter=args.de_maxiter,
            de_popsize=args.de_popsize,
            ls_max_nfev=args.ls_max_nfev,
            seed=args.seed + dipoles,
            restarts=args.restarts,
            x_gap_bounds=(0.25, args.x_gap_max),
            yz_offset_bound=args.yz_offset_bound,
        )
        summaries[dipoles] = summary
        predictions[dipoles] = prediction
        print(
            f"[dipoles={dipoles}] vector_rmse={summary.raw_vector_rmse:.3f} nT, "
            f"bic={summary.bic:.2f}, spacing={summary.sample_spacing_m:.3f} m/sample, "
            f"fs={summary.sample_rate_hz:.1f} Hz"
        )

    save_results(
        summaries,
        predictions,
        observed_raw,
        args.output_dir,
        run_config={
            "data": str(args.data),
            "dipoles": args.dipoles,
            "sample_rate": args.sample_rate,
            "smooth_window": args.smooth_window,
            "de_maxiter": args.de_maxiter,
            "de_popsize": args.de_popsize,
            "ls_max_nfev": args.ls_max_nfev,
            "restarts": args.restarts,
            "vehicle_length_prior": args.vehicle_length_prior,
            "vehicle_length_sigma": args.vehicle_length_sigma,
            "x_gap_max": args.x_gap_max,
            "yz_offset_bound": args.yz_offset_bound,
            "ridge": args.ridge,
            "seed": args.seed,
        },
    )
    best = min(summaries.values(), key=lambda item: item.bic)
    print(f"Best model by BIC: {best.dipoles} dipoles")
    print(f"Artifacts written to: {args.output_dir}")


if __name__ == "__main__":
    main()
