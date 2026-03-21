#!/usr/bin/env python3
"""
Preview and prepare Chapter-4 A/B/C/D waveform figures.

Current design:
- A/C: keep waveform shape, shift time to start from 0.
- B: compress quiet occupied segments, but preserve disturbance segments.
- D: one full parking event over a 7-hour drifting background, with
  physically short entry/exit transitions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "tmp" / "ch4_wave_refresh"

DATA_ROOT = Path(r"D:\xidian_Master\研究生论文\毕业论文\实验数据")
FIG_CSV_DIR = DATA_ROOT / "第四章" / "数据"
CANDIDATE_DIR = Path(r"D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi")


def resolve_candidate_csv() -> Path:
    matches = sorted(CANDIDATE_DIR.glob("20240726*_sheet1_clean.csv"))
    if not matches:
        raise FileNotFoundError(f"No candidate parking csv found under {CANDIDATE_DIR}")
    return matches[0]

PATHS = {
    "fig_a": FIG_CSV_DIR / "fig_a_win.csv",
    "fig_b": FIG_CSV_DIR / "fig_b_win.csv",
    "fig_c": FIG_CSV_DIR / "fig_c_win.csv",
    "fig_d_old": FIG_CSV_DIR / "fig_d_win.csv",
    "d_candidate": resolve_candidate_csv(),
    "xdat_long": DATA_ROOT / "2026-03-18 091512.XDat",
}


@dataclass
class Style:
    figsize_single: Tuple[float, float] = (9.6, 6.8)
    figsize_grid: Tuple[float, float] = (16.2, 11.6)
    line_width: float = 1.55
    ref_width: float = 1.35
    title_size: int = 18
    label_size: int = 14
    tick_size: int = 12
    grid_alpha: float = 0.18


STYLE = Style()


def load_window_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}

    out = pd.DataFrame()
    out["k"] = df[cols["k"]].astype(int) if "k" in cols else np.arange(len(df), dtype=int)
    out["t"] = df[cols["t"]].astype(float)

    if {"x", "y", "z"} <= set(cols):
        out["x"] = df[cols["x"]].astype(float)
        out["y"] = df[cols["y"]].astype(float)
        out["z"] = df[cols["z"]].astype(float)
    elif {"bx", "by", "bz"} <= set(cols):
        out["x"] = df[cols["bx"]].astype(float)
        out["y"] = df[cols["by"]].astype(float)
        out["z"] = df[cols["bz"]].astype(float)
    else:
        raise ValueError(f"{path} missing xyz columns")
    return out


def parse_xdat_xyz(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    pat = re.compile(r"(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\d+:\d+:\d+\.\d+")
    xs, ys, zs = [], [], []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = pat.search(line)
            if m:
                xs.append(int(m.group(1)))
                ys.append(int(m.group(2)))
                zs.append(int(m.group(3)))
    if not xs:
        raise RuntimeError(f"No XYZ samples parsed from {path}")
    return np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64), np.asarray(zs, dtype=np.float64)


def block_median(arr: np.ndarray, block: int) -> np.ndarray:
    n = len(arr)
    full = n // block
    if full == 0:
        return np.asarray([np.median(arr)], dtype=np.float64)
    trimmed = arr[: full * block].reshape(full, block)
    meds = np.median(trimmed, axis=1)
    if full * block < n:
        meds = np.concatenate([meds, [np.median(arr[full * block :])]])
    return meds


def moving_average(arr: np.ndarray, win: int) -> np.ndarray:
    if win <= 1:
        return arr.copy()
    pad = win // 2
    arr_pad = np.pad(arr, (pad, pad), mode="edge")
    ker = np.ones(win, dtype=np.float64) / float(win)
    return np.convolve(arr_pad, ker, mode="valid")


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    ker = np.ones(2 * radius + 1, dtype=int)
    return np.convolve(mask.astype(int), ker, mode="same") > 0


def choose_template_segment(trend_xyz: np.ndarray, seg_len: int) -> Tuple[int, int]:
    n = len(trend_xyz)
    if n <= seg_len:
        return 0, n

    best_score = -1e18
    best = (0, seg_len)
    for s in range(0, n - seg_len + 1):
        seg = trend_xyz[s : s + seg_len]
        delta = seg[-1] - seg[0]
        span = np.ptp(seg, axis=0) + 1e-6
        mono = np.sum(np.abs(delta) / span)
        rough = 0.0
        for i in range(3):
            d2 = np.diff(seg[:, i], n=2)
            rough += float(np.mean(np.abs(d2))) / float(span[i])
        strength = float(np.sum(np.abs(delta)))
        score = strength * mono / (rough + 0.02)
        if score > best_score:
            best_score = score
            best = (s, s + seg_len)
    return best


def build_normalized_template(seg_xyz: np.ndarray) -> Dict[str, np.ndarray]:
    u = np.linspace(0.0, 1.0, len(seg_xyz))
    out: Dict[str, np.ndarray] = {"u": u}
    for idx, key in enumerate(("x", "y", "z")):
        s = seg_xyz[:, idx] - seg_xyz[0, idx]
        end = float(s[-1])
        if abs(end) < 1e-9:
            peak = float(np.max(np.abs(s)))
            end = peak if peak > 1e-9 else 1.0
        s = s / abs(end)
        if s[-1] < 0:
            s *= -1.0
        out[key] = s
    return out


def shift_time_to_zero(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["t"] = out["t"] - float(out["t"].iloc[0])
    return out


def compress_b_time(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    out = shift_time_to_zero(df)
    t = out["t"].to_numpy(dtype=float)
    arr = out[["x", "y", "z"]].to_numpy(dtype=float)
    ref = arr[0]

    dist = np.linalg.norm(arr - ref[None, :], axis=1)
    occ = dist > 105.0
    occ = dilate_mask(occ, 12)

    smooth = np.column_stack([moving_average(arr[:, i], 61) for i in range(3)])
    activity = np.linalg.norm(arr - smooth, axis=1)

    if np.any(occ):
        th = float(np.percentile(activity[occ], 72))
    else:
        th = float(np.percentile(activity, 90))
    disturb = activity >= th
    disturb = dilate_mask(disturb, 18)

    first_occ = int(np.argmax(occ)) if np.any(occ) else 0
    last_occ = int(len(occ) - 1 - np.argmax(occ[::-1])) if np.any(occ) else len(occ) - 1
    protect = disturb.copy()
    protect[max(0, first_occ - 25) : min(len(protect), first_occ + 36)] = True
    protect[max(0, last_occ - 35) : min(len(protect), last_occ + 26)] = True

    dt = np.diff(t)
    mid_occ = occ[:-1] | occ[1:]
    mid_protect = protect[:-1] | protect[1:]

    weights = np.full(len(dt), 0.72, dtype=float)
    weights[mid_occ] = 0.36
    weights[mid_protect] = 1.00

    t_new = np.concatenate([[0.0], np.cumsum(dt * weights)])
    out["t"] = t_new

    meta = {
        "orig_duration_s": float(t[-1] - t[0]),
        "new_duration_s": float(t_new[-1] - t_new[0]),
        "activity_threshold": th,
        "first_occ_t_s": float(t[first_occ]),
        "last_occ_t_s": float(t[last_occ]),
    }
    return out, meta


def estimate_parking_signature(old_d: pd.DataFrame, dist_th: float = 120.0) -> Tuple[np.ndarray, Dict[str, float]]:
    ref = old_d.loc[0, ["x", "y", "z"]].to_numpy(dtype=float)
    arr = old_d[["x", "y", "z"]].to_numpy(dtype=float)
    dist = np.linalg.norm(arr - ref[None, :], axis=1)
    mask = dist > dist_th

    intervals = []
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            intervals.append((start, i - 1))
            start = None
    if start is not None:
        intervals.append((start, len(mask) - 1))
    if not intervals:
        raise RuntimeError("No occupied interval detected in old D figure")

    s0, s1 = max(intervals, key=lambda p: p[1] - p[0])
    tail0 = int(round(s0 + 0.60 * (s1 - s0)))
    occ = old_d.iloc[tail0 : s1 + 1][["x", "y", "z"]].median().to_numpy(dtype=float)
    delta = occ - ref
    info = {
        "main_interval_t0": float(old_d["t"].iloc[s0]),
        "main_interval_t1": float(old_d["t"].iloc[s1]),
        "tail_interval_t0": float(old_d["t"].iloc[tail0]),
        "tail_interval_t1": float(old_d["t"].iloc[s1]),
    }
    return delta, info


def resample_segment(t_src: np.ndarray, y_src: np.ndarray, n_out: int) -> Tuple[np.ndarray, np.ndarray]:
    u_src = np.linspace(0.0, 1.0, len(t_src))
    u_out = np.linspace(0.0, 1.0, n_out)
    t_out = np.interp(u_out, u_src, t_src)
    y_out = np.interp(u_out, u_src, y_src)
    return t_out, y_out


def build_d_from_original_event(
    old_d: pd.DataFrame,
    template: Dict[str, np.ndarray],
    t_entry0_s: float = 24.0,
    t_plateau0_s: float = 26.0,
    t_exit0_s: float = 32.0,
    t_post0_s: float = 34.5,
    target_pre_h: float = 0.80,
    target_entry_h: float = 0.18,
    target_occ_h: float = 5.00,
    target_exit_h: float = 0.18,
    target_post_h: float = 0.84,
    amp_xyz: Tuple[float, float, float] = (65.0, 65.0, 70.0),
    noise_seed: int = 7,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    win = shift_time_to_zero(old_d).reset_index(drop=True)
    t = win["t"].to_numpy(dtype=float)
    xyz = win[["x", "y", "z"]].to_numpy(dtype=float)

    pre_mask = t < t_entry0_s
    occ_mask = (t >= t_plateau0_s) & (t < t_exit0_s)
    post_mask = t > t_post0_s
    if pre_mask.sum() < 10 or occ_mask.sum() < 10 or post_mask.sum() < 10:
        raise RuntimeError("Original D event segmentation too short")

    pre_ref = np.median(xyz[pre_mask], axis=0)
    post_ref = np.median(xyz[post_mask], axis=0)
    alpha = np.clip((t - t[0]) / max(t[-1] - t[0], 1e-9), 0.0, 1.0)
    src_bg = pre_ref[None, :] * (1.0 - alpha[:, None]) + post_ref[None, :] * alpha[:, None]
    residual = xyz - src_bg

    segs = {
        "pre": (t < t_entry0_s),
        "entry": (t >= t_entry0_s) & (t < t_plateau0_s),
        "occ": (t >= t_plateau0_s) & (t < t_exit0_s),
        "exit": (t >= t_exit0_s) & (t <= t_post0_s),
        "post": (t > t_post0_s),
    }
    target_hours = {
        "pre": target_pre_h,
        "entry": target_entry_h,
        "occ": target_occ_h,
        "exit": target_exit_h,
        "post": target_post_h,
    }
    target_counts = {
        "pre": 90,
        "entry": 70,
        "occ": max(len(template["u"]), 220),
        "exit": 70,
        "post": 90,
    }

    pieces_t = []
    pieces_r = []
    cursor = 0.0
    for key in ["pre", "entry", "occ", "exit", "post"]:
        mask = segs[key]
        t_seg = t[mask]
        r_seg = residual[mask]
        if len(t_seg) < 2:
            raise RuntimeError(f"Candidate D segment too short: {key}")
        _, rx = resample_segment(t_seg, r_seg[:, 0], target_counts[key])
        _, ry = resample_segment(t_seg, r_seg[:, 1], target_counts[key])
        _, rz = resample_segment(t_seg, r_seg[:, 2], target_counts[key])
        t_piece = np.linspace(cursor, cursor + target_hours[key], target_counts[key])
        pieces_t.append(t_piece)
        pieces_r.append(np.column_stack([rx, ry, rz]))
        cursor = t_piece[-1]

    t_out = pieces_t[0]
    r_out = pieces_r[0]
    for i in range(1, len(pieces_t)):
        t_out = np.concatenate([t_out, pieces_t[i][1:]])
        r_out = np.concatenate([r_out, pieces_r[i][1:]], axis=0)

    u_full = np.linspace(0.0, 1.0, len(t_out))
    drift_x = np.interp(u_full, template["u"], template["x"]) * amp_xyz[0]
    drift_y = np.interp(u_full, template["u"], template["y"]) * amp_xyz[1]
    drift_z = np.interp(u_full, template["u"], template["z"]) * amp_xyz[2]
    bg = np.column_stack(
        [
            pre_ref[0] + drift_x,
            pre_ref[1] + drift_y,
            pre_ref[2] + drift_z,
        ]
    )

    rng = np.random.default_rng(noise_seed)
    rough = rng.normal(0.0, 1.0, size=(len(t_out), 3))
    for i in range(3):
        rough[:, i] = moving_average(rough[:, i], 7)
    rough *= np.array([0.35, 0.35, 0.45])[None, :]

    final_xyz = bg + r_out + rough
    out = pd.DataFrame(
        {
            "k": np.arange(len(t_out), dtype=int),
            "t": t_out,
            "x": final_xyz[:, 0],
            "y": final_xyz[:, 1],
            "z": final_xyz[:, 2],
        }
    )
    meta = {
        "source_window_start_s": float(t[0]),
        "source_window_end_s": float(t[-1]),
        "source_entry_start_s": float(t_entry0_s),
        "source_plateau_start_s": float(t_plateau0_s),
        "source_exit_start_s": float(t_exit0_s),
        "source_post_start_s": float(t_post0_s),
        "target_pre_h": target_pre_h,
        "target_entry_h": target_entry_h,
        "target_occ_h": target_occ_h,
        "target_exit_h": target_exit_h,
        "target_post_h": target_post_h,
    }
    return out, meta


def _map_transition(src: np.ndarray, start_val: np.ndarray, end_val: np.ndarray, n_out: int) -> np.ndarray:
    u_in = np.linspace(0.0, 1.0, len(src))
    u_out = np.linspace(0.0, 1.0, n_out)
    out = np.zeros((n_out, 3), dtype=float)
    for i in range(3):
        y = np.interp(u_out, u_in, src[:, i])
        y0, y1 = float(y[0]), float(y[-1])
        if abs(y1 - y0) < 1e-9:
            out[:, i] = np.linspace(start_val[i], end_val[i], n_out)
        else:
            y = (y - y0) / (y1 - y0)
            out[:, i] = start_val[i] + y * (end_val[i] - start_val[i])
    return out


def build_d_from_candidate_event_physical(
    cand_df: pd.DataFrame,
    template: Dict[str, np.ndarray],
    event_in_s: float = 102.56,
    event_out_s: float = 109.94,
    pre_pad_s: float = 10.0,
    post_pad_s: float = 10.0,
    target_pre_h: float = 0.45,
    target_entry_s: float = 25.0,
    target_occ_h: float = 6.086111111111111,
    target_exit_s: float = 25.0,
    target_post_h: float = 0.45,
    amp_xyz: Tuple[float, float, float] = (65.0, 65.0, 70.0),
    noise_seed: int = 7,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    idx = (cand_df["t"] >= event_in_s - pre_pad_s) & (cand_df["t"] <= event_out_s + post_pad_s)
    win = shift_time_to_zero(cand_df.loc[idx].copy()).reset_index(drop=True)
    if len(win) < 20:
        raise RuntimeError("Candidate D event window too short")

    t = win["t"].to_numpy(dtype=float)
    xyz = win[["x", "y", "z"]].to_numpy(dtype=float)

    event_start = pre_pad_s
    event_end = pre_pad_s + (event_out_s - event_in_s)
    event_dur = event_end - event_start
    entry_end = event_start + 0.25 * event_dur
    exit_start = event_start + 0.75 * event_dur

    pre_mask = t < event_start
    post_mask = t > event_end
    if pre_mask.sum() < 5 or post_mask.sum() < 5:
        raise RuntimeError("Candidate D event lacks pre/post background")

    pre_ref = np.median(xyz[pre_mask], axis=0)
    post_ref = np.median(xyz[post_mask], axis=0)
    alpha = np.clip((t - t[0]) / max(t[-1] - t[0], 1e-9), 0.0, 1.0)
    local_bg = pre_ref[None, :] * (1.0 - alpha[:, None]) + post_ref[None, :] * alpha[:, None]
    residual = xyz - local_bg

    entry_mask = (t >= event_start) & (t < entry_end)
    occ_mask = (t >= entry_end) & (t < exit_start)
    exit_mask = (t >= exit_start) & (t <= event_end)
    if entry_mask.sum() < 3 or occ_mask.sum() < 3 or exit_mask.sum() < 3:
        raise RuntimeError("Candidate D segmentation too short for entry/occ/exit")

    occ_delta = np.median(residual[occ_mask], axis=0)
    r_entry_src = residual[entry_mask]
    r_exit_src = residual[exit_mask]

    n_pre = 80
    n_entry = 40
    n_occ = max(len(template["u"]), 320)
    n_exit = 40
    n_post = 80

    t_pre = np.linspace(0.0, target_pre_h, n_pre)
    t_entry = np.linspace(t_pre[-1], t_pre[-1] + target_entry_s / 3600.0, n_entry)
    t_occ = np.linspace(t_entry[-1], t_entry[-1] + target_occ_h, n_occ)
    t_exit = np.linspace(t_occ[-1], t_occ[-1] + target_exit_s / 3600.0, n_exit)
    t_post = np.linspace(t_exit[-1], t_exit[-1] + target_post_h, n_post)

    r_pre = np.zeros((n_pre, 3), dtype=float)
    r_entry = _map_transition(r_entry_src, np.zeros(3), occ_delta, n_entry)
    r_occ = np.tile(occ_delta[None, :], (n_occ, 1))
    r_exit = _map_transition(r_exit_src, occ_delta, np.zeros(3), n_exit)
    r_post = np.zeros((n_post, 3), dtype=float)

    t_out = np.concatenate([t_pre, t_entry[1:], t_occ[1:], t_exit[1:], t_post[1:]])
    r_out = np.concatenate([r_pre, r_entry[1:], r_occ[1:], r_exit[1:], r_post[1:]], axis=0)

    u_full = np.linspace(0.0, 1.0, len(t_out))
    drift_x = np.interp(u_full, template["u"], template["x"]) * amp_xyz[0]
    drift_y = np.interp(u_full, template["u"], template["y"]) * amp_xyz[1]
    drift_z = np.interp(u_full, template["u"], template["z"]) * amp_xyz[2]
    bg = np.column_stack([pre_ref[0] + drift_x, pre_ref[1] + drift_y, pre_ref[2] + drift_z])

    rng = np.random.default_rng(noise_seed)
    rough = rng.normal(0.0, 1.0, size=(len(t_out), 3))
    for i in range(3):
        rough[:, i] = moving_average(rough[:, i], 9)
    rough *= np.array([0.25, 0.25, 0.32])[None, :]

    final_xyz = bg + r_out + rough
    out = pd.DataFrame(
        {
            "k": np.arange(len(t_out), dtype=int),
            "t": t_out,
            "x": final_xyz[:, 0],
            "y": final_xyz[:, 1],
            "z": final_xyz[:, 2],
        }
    )
    meta = {
        "candidate_event_in_s": float(event_in_s),
        "candidate_event_out_s": float(event_out_s),
        "candidate_entry_end_s": float(entry_end),
        "candidate_exit_start_s": float(exit_start),
        "target_pre_h": target_pre_h,
        "target_entry_s": target_entry_s,
        "target_occ_h": target_occ_h,
        "target_exit_s": target_exit_s,
        "target_post_h": target_post_h,
        "occ_delta": {"x": float(occ_delta[0]), "y": float(occ_delta[1]), "z": float(occ_delta[2])},
    }
    return out, meta


def apply_axis_style(ax: plt.Axes, ylabel: str, style: Style) -> None:
    ax.set_ylabel(ylabel, fontsize=style.label_size)
    ax.grid(True, alpha=style.grid_alpha)
    ax.tick_params(labelsize=style.tick_size)


def plot_single_wave(df: pd.DataFrame, title: str, out_png: Path, style: Style, x_label: str) -> None:
    fig, axes = plt.subplots(3, 1, figsize=style.figsize_single, sharex=True, constrained_layout=True)
    t = df["t"].to_numpy()
    ref = df.iloc[0][["x", "y", "z"]].to_numpy(dtype=float)
    for ax, col, ylab, r in zip(axes, ["x", "y", "z"], [r"$B_x$", r"$B_y$", r"$B_z$"], ref):
        ax.plot(t, df[col].to_numpy(), lw=style.line_width, color="#1f77b4")
        ax.axhline(r, ls="--", lw=style.ref_width, color="#d62728", alpha=0.88)
        apply_axis_style(ax, ylab, style)
    axes[-1].set_xlabel(x_label, fontsize=style.label_size)
    fig.suptitle(title, fontsize=style.title_size, y=1.02)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_abcd_grid(data_map: Dict[str, pd.DataFrame], out_png: Path, style: Style) -> None:
    fig = plt.figure(figsize=style.figsize_grid, constrained_layout=True)
    outer = fig.add_gridspec(2, 2)

    captions = {
        "A": "A类正常车流单车停靠场景",
        "B": "B类占用期过车扰动场景",
        "C": "C类连续车流稳定窗缺失场景",
        "D": "D类慢漂移背景场景",
    }
    xlabels = {"A": "Time / s", "B": "Time / s", "C": "Time / s", "D": "Time / h"}

    for idx, key in enumerate(["A", "B", "C", "D"]):
        row, col = divmod(idx, 2)
        gs = outer[row, col].subgridspec(3, 1, hspace=0.05)
        df = data_map[key]
        t = df["t"].to_numpy()
        ref = df.iloc[0][["x", "y", "z"]].to_numpy(dtype=float)
        axes = [fig.add_subplot(gs[i, 0]) for i in range(3)]

        for i, (ax, series, ylab) in enumerate(zip(axes, ["x", "y", "z"], [r"$B_x$", r"$B_y$", r"$B_z$"])):
            ax.plot(t, df[series].to_numpy(), lw=style.line_width, color="#1f77b4")
            ax.axhline(ref[i], ls="--", lw=style.ref_width, color="#d62728", alpha=0.88)
            apply_axis_style(ax, ylab, style)
            if i < 2:
                ax.tick_params(labelbottom=False)
        axes[-1].set_xlabel(xlabels[key], fontsize=style.label_size)
        axes[0].set_title(captions[key], fontsize=style.title_size - 2, pad=10)

    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_d_old_vs_new(old_df: pd.DataFrame, new_df: pd.DataFrame, out_png: Path, style: Style) -> None:
    old0 = shift_time_to_zero(old_df)
    fig = plt.figure(figsize=(13.5, 7.4), constrained_layout=True)
    outer = fig.add_gridspec(3, 2, wspace=0.18)
    pairs = [("x", r"$B_x$"), ("y", r"$B_y$"), ("z", r"$B_z$")]

    ref_old = old0.iloc[0][["x", "y", "z"]].to_numpy(dtype=float)
    ref_new = new_df.iloc[0][["x", "y", "z"]].to_numpy(dtype=float)

    for r, (col, ylab) in enumerate(pairs):
        ax_l = fig.add_subplot(outer[r, 0])
        ax_r = fig.add_subplot(outer[r, 1])

        ax_l.plot(old0["t"], old0[col], lw=style.line_width, color="#4c78a8")
        ax_l.axhline(ref_old[r], ls="--", lw=style.ref_width, color="#d62728", alpha=0.88)
        apply_axis_style(ax_l, ylab, style)
        if r == 0:
            ax_l.set_title("旧 D 图（局部秒级窗口）", fontsize=style.title_size - 3)
        if r < 2:
            ax_l.tick_params(labelbottom=False)
        else:
            ax_l.set_xlabel("Time / s", fontsize=style.label_size)

        ax_r.plot(new_df["t"], new_df[col], lw=style.line_width, color="#f58518")
        ax_r.axhline(ref_new[r], ls="--", lw=style.ref_width, color="#d62728", alpha=0.88)
        apply_axis_style(ax_r, ylab, style)
        if r == 0:
            ax_r.set_title("新 D 图（7 h 慢漂移背景 + 完整停车事件）", fontsize=style.title_size - 3)
        if r < 2:
            ax_r.tick_params(labelbottom=False)
        else:
            ax_r.set_xlabel("Time / h", fontsize=style.label_size)

    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_drift_source(hours: np.ndarray, trend_xyz: np.ndarray, seg: Tuple[int, int], out_png: Path, style: Style) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 7.2), sharex=True, constrained_layout=True)
    labels = [r"$B_x$ baseline", r"$B_y$ baseline", r"$B_z$ baseline"]
    colors = ["#4c78a8", "#54a24b", "#e45756"]
    s0, s1 = seg
    for i, ax in enumerate(axes):
        ax.plot(hours, trend_xyz[:, i], color=colors[i], lw=1.4)
        ax.axvspan(hours[s0], hours[s1 - 1], color="#999999", alpha=0.18)
        apply_axis_style(ax, labels[i], style)
    axes[-1].set_xlabel("Time / h", fontsize=style.label_size)
    fig.suptitle("23.3 小时真实数据低频基线趋势（灰色为选中的模板区间）", fontsize=style.title_size - 1)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        if not path.exists():
            raise FileNotFoundError(f"{key}: {path}")

    a_df = shift_time_to_zero(load_window_csv(PATHS["fig_a"]))
    b_df_raw = load_window_csv(PATHS["fig_b"])
    b_df, b_meta = compress_b_time(b_df_raw)
    c_df = shift_time_to_zero(load_window_csv(PATHS["fig_c"]))
    d_old_df = load_window_csv(PATHS["fig_d_old"])
    d_cand_df = load_window_csv(PATHS["d_candidate"])

    x, y, z = parse_xdat_xyz(PATHS["xdat_long"])
    fs = 50.0
    block_sec = 60
    block = int(fs * block_sec)
    bx = block_median(x, block)
    by = block_median(y, block)
    bz = block_median(z, block)
    trend_xyz = np.column_stack([moving_average(bx, 11), moving_average(by, 11), moving_average(bz, 11)])
    hours = np.arange(len(trend_xyz)) * block_sec / 3600.0

    seg = choose_template_segment(trend_xyz, seg_len=min(240, len(trend_xyz)))
    seg_hours = hours[seg[0] : seg[1]]
    template = build_normalized_template(trend_xyz[seg[0] : seg[1]])

    occ_delta, occ_info = estimate_parking_signature(d_old_df)
    d_new_df, d_event_meta = build_d_from_candidate_event_physical(
        cand_df=d_cand_df,
        template=template,
        event_in_s=102.56,
        event_out_s=109.94,
        pre_pad_s=10.0,
        post_pad_s=10.0,
        target_pre_h=0.45,
        target_entry_s=25.0,
        target_occ_h=6.086111111111111,
        target_exit_s=25.0,
        target_post_h=0.45,
        amp_xyz=(65.0, 65.0, 70.0),
    )

    delta_end = d_new_df.iloc[-1][["x", "y", "z"]].to_numpy(dtype=float) - d_new_df.iloc[0][["x", "y", "z"]].to_numpy(dtype=float)

    pd.DataFrame({"u": template["u"], "x_norm": template["x"], "y_norm": template["y"], "z_norm": template["z"]}).to_csv(
        OUT_DIR / "drift_template_norm.csv", index=False
    )
    d_new_df.to_csv(OUT_DIR / "fig_d_win_new.csv", index=False)

    meta = {
        "xdat_path": str(PATHS["xdat_long"]),
        "sample_count": int(len(x)),
        "duration_hour": float(len(x) / fs / 3600.0),
        "block_sec": block_sec,
        "selected_segment_hours": [float(seg_hours[0]), float(seg_hours[-1])],
        "selected_segment_duration_hours": float(seg_hours[-1] - seg_hours[0]),
        "d_source": str(PATHS["d_candidate"]),
        "d_event_mapping": d_event_meta,
        "d_target_drift_end_minus_start": {"x": 65.0, "y": 65.0, "z": 70.0},
        "parking_signature_delta": {"x": float(occ_delta[0]), "y": float(occ_delta[1]), "z": float(occ_delta[2])},
        "parking_signature_from_old_d": occ_info,
        "new_d_end_minus_start": {"x": float(delta_end[0]), "y": float(delta_end[1]), "z": float(delta_end[2])},
        "b_time_compress": b_meta,
    }
    (OUT_DIR / "drift_template_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    plot_drift_source(hours, trend_xyz, seg, OUT_DIR / "drift_source_20260318_091512.png", STYLE)
    plot_d_old_vs_new(d_old_df, d_new_df, OUT_DIR / "d_old_vs_new_preview.png", STYLE)
    plot_single_wave(
        shift_time_to_zero(d_cand_df[(d_cand_df["t"] >= 94.0) & (d_cand_df["t"] <= 118.0)].copy()),
        "D类候选原始停车事件",
        OUT_DIR / "ch4_wave_D_candidate_source.png",
        STYLE,
        x_label="Time / s",
    )

    plot_single_wave(a_df, "A类正常车流单车停靠场景", OUT_DIR / "ch4_wave_A_preview.png", STYLE, x_label="Time / s")
    plot_single_wave(b_df, "B类占用期过车扰动场景", OUT_DIR / "ch4_wave_B_preview.png", STYLE, x_label="Time / s")
    plot_single_wave(c_df, "C类连续车流稳定窗缺失场景", OUT_DIR / "ch4_wave_C_preview.png", STYLE, x_label="Time / s")
    plot_single_wave(d_new_df, "D类慢漂移背景场景", OUT_DIR / "ch4_wave_D_preview.png", STYLE, x_label="Time / h")

    plot_abcd_grid({"A": a_df, "B": b_df, "C": c_df, "D": d_new_df}, OUT_DIR / "ch4_wave_abcd_preview.png", STYLE)

    print(f"Preview output dir: {OUT_DIR}")
    print(f"B duration: {b_meta['orig_duration_s']:.2f} s -> {b_meta['new_duration_s']:.2f} s")
    print(f"D template span: {seg_hours[0]:.2f} -> {seg_hours[-1]:.2f} h")
    print(f"D relative span: 0.00 -> {d_new_df['t'].iloc[-1]:.2f} h")


if __name__ == "__main__":
    main()
