#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chapter 4 one-click: generate thesis tables & key figures (minimal set).

This script is a Python port of the MATLAB one-key pipeline in
`ch4_onekey_pack/run/run_ch4_onekey_global.m`, and aligns outputs to the
Chapter 4 LaTeX placeholders under the *no-appendix* writing policy.

It writes (relative to --out_dir):

  tables/
    - ch4_dataset_rows.tex            (dataset counts; sample-size only)
    - ch4_bycase_compare_rows.tex     (baseline comparison: P/R/F1 for A/B/C/D/ALL)
    - ch4_timing_global_rows.tex      (brief timing stats on TP samples)
    - ch4_ablation_global_rows.tex    (ablation F1 summary) [skipped if --no_ablation]

  images/
    - ch4_baseline_cmp_f1.pdf         (main result figure: $F_1$ comparison across A/B/C/D)
    - ch4_C_seek_ratio.pdf            (C-group stable-found ratio & degrade usage)

Optional figures (parameter evidence, sensitivity, distribution plots, etc.)
can be generated with --optional_figs, but are not required for the minimal
thesis version.

By default it:
  - treats all samples as evaluation samples (includes synth_out if --use_synth=1)
  - runs OURS, LWC+ and ADTA-FSM baselines
  - runs ablation unless --no_ablation is set

Usage example:
  python ch4_oneclick_make_tables_figs_minimal.py \
    --data_zip data.zip \
    --pack_zip ch4_onekey_pack_nodata.zip \
    --out_dir  <YOUR_LATEX_ROOT> \
    --work_dir _work_ch4
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _decode_hashu(s: str) -> str:
    """Decode '#U4E2D' style escapes into unicode chars."""

    def repl(m: re.Match) -> str:
        return chr(int(m.group(1), 16))

    return re.sub(r"#U([0-9A-Fa-f]{4})", repl, s)


def _encode_hashu(s: str) -> str:
    """Encode non-ascii chars into '#UXXXX' (UTF-16 BMP style, as used in your data)."""
    out: List[str] = []
    for ch in s:
        code = ord(ch)
        if code > 127:
            out.append(f"#U{code:04X}")
        else:
            out.append(ch)
    return "".join(out)


def _find_csv(file_name: str, data_dir: str, synth_dir: str) -> Optional[str]:
    """Find CSV path in data_dir or synth_dir, tolerant to #U-encoding."""
    cand_names = []
    for nm in [file_name, _encode_hashu(file_name), _decode_hashu(file_name)]:
        cand_names.append(nm)

        # common alt name
        if nm.endswith("_clean.csv"):
            cand_names.append(nm.replace("_clean.csv", "_clean_crop.csv"))
        if nm.endswith("_clean_crop.csv"):
            cand_names.append(nm.replace("_clean_crop.csv", "_clean.csv"))

    for nm in cand_names:
        p1 = os.path.join(data_dir, nm)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(synth_dir, nm)
        if os.path.exists(p2):
            return p2
    return None


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _write_text(path: str, text: str) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _load_ch4_module(py_path: str):
    spec = importlib.util.spec_from_file_location("ch4", py_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _calc_prf(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


def eval_iou_with_match(
    pred: Sequence[Sequence[float]],
    gt: Sequence[Sequence[float]],
    iou_th: float,
) -> Tuple[int, int, int, float, float, float, List[Tuple[int, int, float]]]:
    """Greedy one-to-one IoU matching (same strategy as your MATLAB & python verify).

    Returns TP/FP/FN/P/R/F1 and match list: (ip, ig, iou).
    """
    pred = np.asarray(pred, dtype=float).reshape((-1, 2))
    gt = np.asarray(gt, dtype=float).reshape((-1, 2))
    npred = int(pred.shape[0])
    ngt = int(gt.shape[0])

    if npred == 0 and ngt == 0:
        return 0, 0, 0, 0.0, 0.0, 0.0, []
    if npred == 0 and ngt > 0:
        return 0, 0, ngt, 0.0, 0.0, 0.0, []
    if npred > 0 and ngt == 0:
        return 0, npred, 0, 0.0, 0.0, 0.0, []

    iou = np.zeros((npred, ngt), dtype=float)
    for i in range(npred):
        for j in range(ngt):
            inter = max(0.0, min(pred[i, 1], gt[j, 1]) - max(pred[i, 0], gt[j, 0]))
            uni = max(pred[i, 1], gt[j, 1]) - min(pred[i, 0], gt[j, 0])
            if uni > 0:
                iou[i, j] = inter / uni

    pairs: List[Tuple[int, int, float]] = [(i, j, float(iou[i, j])) for i in range(npred) for j in range(ngt)]
    pairs.sort(key=lambda x: -x[2])

    matched_p = np.zeros(npred, dtype=bool)
    matched_g = np.zeros(ngt, dtype=bool)
    match: List[Tuple[int, int, float]] = []
    for i, j, v in pairs:
        if v < iou_th:
            break
        if (not matched_p[i]) and (not matched_g[j]):
            matched_p[i] = True
            matched_g[j] = True
            match.append((i, j, v))

    tp = len(match)
    fp = int(np.sum(~matched_p))
    fn = int(np.sum(~matched_g))
    p, r, f1 = _calc_prf(tp, fp, fn)
    return tp, fp, fn, p, r, f1, match


def postprocess_segments(
    seg: np.ndarray,
    fs: float,
    Tmin_sec: float,
    gap_merge_sec: float,
) -> np.ndarray:
    seg = np.asarray(seg, dtype=float).reshape((-1, 2))
    if seg.size == 0:
        return seg.reshape((0, 2))
    dur = (seg[:, 1] - seg[:, 0]) / fs
    seg = seg[dur >= Tmin_sec]
    if seg.size == 0:
        return seg.reshape((0, 2))

    if gap_merge_sec <= 0:
        seg = seg[np.argsort(seg[:, 0])]
        return seg

    seg = seg[np.argsort(seg[:, 0])]
    gap_k = int(round(gap_merge_sec * fs))
    merged = [seg[0].tolist()]
    for i in range(1, seg.shape[0]):
        if seg[i, 0] - merged[-1][1] <= gap_k:
            merged[-1][1] = max(merged[-1][1], float(seg[i, 1]))
        else:
            merged.append(seg[i].tolist())
    return np.asarray(merged, dtype=float)


def postprocess_pred_conf(
    pred: np.ndarray,
    conf: np.ndarray,
    fs: float,
    Tmin_sec: float,
    gap_merge_sec: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Keep pred/conf aligned under Tmin filtering + gap merging."""
    pred = np.asarray(pred, dtype=float).reshape((-1, 2))
    conf = np.asarray(conf, dtype=float).reshape((-1, 2))
    assert pred.shape[0] == conf.shape[0]
    if pred.size == 0:
        return pred.reshape((0, 2)), conf.reshape((0, 2))

    dur = (pred[:, 1] - pred[:, 0]) / fs
    keep = dur >= Tmin_sec
    pred = pred[keep]
    conf = conf[keep]
    if pred.size == 0:
        return pred.reshape((0, 2)), conf.reshape((0, 2))

    # sort by pred start
    order = np.argsort(pred[:, 0])
    pred = pred[order]
    conf = conf[order]

    if gap_merge_sec <= 0:
        return pred, conf

    gap_k = int(round(gap_merge_sec * fs))
    mp = [pred[0].tolist()]
    mc = [conf[0].tolist()]
    for i in range(1, pred.shape[0]):
        if pred[i, 0] - mp[-1][1] <= gap_k:
            mp[-1][1] = max(mp[-1][1], float(pred[i, 1]))
            mc[-1][1] = max(mc[-1][1], float(conf[i, 1]))
        else:
            mp.append(pred[i].tolist())
            mc.append(conf[i].tolist())
    return np.asarray(mp, dtype=float), np.asarray(mc, dtype=float)


def match_events_to_gt(
    events: Sequence[dict],
    gt_idx: np.ndarray,
    tol_k: int,
) -> Tuple[List[int], List[int]]:
    """Port of MATLAB match_events_to_gt.

    Returns indices (0-based) of events whose k_out is closest to gt_in / gt_out.
    """
    if len(events) == 0 or gt_idx.size == 0:
        return [], []
    kout = np.asarray([int(e["k_out"]) for e in events], dtype=int)

    arr_idx: List[int] = []
    leave_idx: List[int] = []
    for j in range(int(gt_idx.shape[0])):
        kin = int(gt_idx[j, 0])
        kout_gt = int(gt_idx[j, 1])

        d1 = np.min(np.abs(kout - kin))
        i1 = int(np.argmin(np.abs(kout - kin)))
        if d1 <= tol_k:
            arr_idx.append(i1)

        d2 = np.min(np.abs(kout - kout_gt))
        i2 = int(np.argmin(np.abs(kout - kout_gt)))
        if d2 <= tol_k:
            leave_idx.append(i2)

    arr_idx = sorted(set(arr_idx))
    leave_idx = sorted(set(leave_idx))
    return arr_idx, leave_idx


# ------------------------------
# Parking FSM (OURS) with debug
# ------------------------------


@dataclass
class EventDbg:
    k_out: int
    state: str
    stable_found: bool
    used_degrade: bool
    drift_mag: float
    dist: float


def run_parking_with_dbg(
    ch4,
    B: np.ndarray,
    cfg: dict,
    b_xy,
    b_z,
    *,
    events: Optional[List[dict]] = None,
    st: Optional[dict] = None,
) -> Tuple[np.ndarray, np.ndarray, List[dict], List[EventDbg]]:
    """Copy of ch4.run_parking, but returns per-event debug arrays.

    If events/st are provided, they will be reused (to speed up ablations).
    """
    fs = float(cfg["fs"])
    seekN = int(round(cfg["pk"]["T_seek_sec"] * fs))

    if events is None:
        pr = ch4.pr_vehicle(B, cfg, b_xy, b_z)
        events = ch4.detect_events(pr, cfg)
    if st is None:
        st = ch4.stability(B, cfg)

    stableState = np.asarray(st["stableState"], dtype=bool)
    meanVec = np.asarray(st["meanVec"], dtype=float)

    FREE = 1
    OCC = 2
    state = FREE

    # init S_pre from first stable point (fallback to first sample)
    idx0 = np.where(stableState)[0]
    if idx0.size > 0:
        k_first = int(idx0[0]) + 1  # 1-based
        S_pre = meanVec[k_first - 1, :].copy()
    else:
        S_pre = B[0, :].copy()

    S_post = None
    dB = None
    open_k_in = math.nan
    open_k_conf_in = math.nan
    c_park = 0
    c_free = 0

    pred_k: List[List[int]] = []
    conf_k: List[List[int]] = []
    dbg: List[EventDbg] = []

    for ev in events:
        k_out = int(ev["k_out"])  # 1-based
        k_seek_end = min(int(B.shape[0]), k_out + seekN)

        # find stable point within [k_out, k_seek_end]
        slice_st = stableState[k_out - 1 : k_seek_end]
        found = np.where(slice_st)[0]
        stable_found = found.size > 0
        used_degrade = False
        drift_mag = float("nan")
        dist = float("nan")

        if state == FREE:
            # optional reference update (based on last stable before event)
            if cfg["ref"]["enable"]:
                idx = np.where(stableState[:k_out])[0]
                if idx.size > 0:
                    k_last = int(idx[-1]) + 1
                    S_cand = meanVec[k_last - 1, :]
                    alpha = float(cfg["ref"]["alpha_free"])
                    d = S_cand - S_pre
                    nd = float(np.linalg.norm(d))
                    if not cfg["v"]["use_update_gate"]:
                        S_pre = (1 - alpha) * S_pre + alpha * S_cand
                    else:
                        D_upd = float(cfg["ref"]["D_upd"])
                        if nd <= D_upd:
                            S_pre = (1 - alpha) * S_pre + alpha * S_cand
                        else:
                            S_pre = S_pre + alpha * (D_upd / max(nd, 1e-12)) * d

            if stable_found:
                k_st = k_out + int(found[0])
                S_new = meanVec[k_st - 1, :]
                dB_cand = S_new - S_pre
                drift_mag = float(np.linalg.norm(dB_cand))
                if drift_mag > float(cfg["pk"]["D_th"]):
                    state = OCC
                    S_post = S_new.copy()
                    dB = S_post - S_pre
                    open_k_in = k_out
                    open_k_conf_in = k_st
                    c_park = 0
                    c_free = 0
            else:
                if cfg["dg"]["enable"] and cfg["v"]["use_degrade"]:
                    used_degrade = True
                    L_fix = int(cfg["dg"]["L_fix"])
                    if (k_seek_end - L_fix + 1) >= 1:
                        start = k_seek_end - L_fix + 1
                        S_hat = np.mean(B[start - 1 : k_seek_end, :], axis=0)
                    else:
                        S_hat = np.mean(B[:k_seek_end, :], axis=0)
                    dB_hat = S_hat - S_pre
                    drift_mag = float(np.linalg.norm(dB_hat))
                    if drift_mag > float(cfg["pk"]["D_th"]):
                        c_park = min(c_park + 1, int(cfg["dg"]["c_th"]))
                    else:
                        c_park = 0
                    if c_park >= int(cfg["dg"]["c_th"]):
                        state = OCC
                        S_post = S_hat.copy()
                        dB = S_post - S_pre
                        open_k_in = k_out
                        open_k_conf_in = k_seek_end
                        c_park = 0
                        c_free = 0

        else:  # OCC
            if stable_found:
                k_st = k_out + int(found[0])
                S_new = meanVec[k_st - 1, :]
                back2env = float(np.linalg.norm(S_new - S_pre))
                if back2env < float(cfg["pk"]["D_free"]):
                    state = FREE
                    pred_k.append([int(open_k_in), k_out])
                    conf_k.append([int(open_k_conf_in), k_st])
                    S_pre = S_new.copy()
                    open_k_in = math.nan
                    open_k_conf_in = math.nan
                    S_post = None
                    dB = None
                    c_free = 0
                else:
                    if cfg["v"]["use_similarity"] and (dB is not None):
                        dist = float(np.linalg.norm((S_new - S_pre) - dB))
                    if (not math.isnan(dist)) and (dist < float(cfg["pk"]["dist_th"])):
                        lam = float(cfg["pk"]["lambda_occ"])
                        if S_post is None:
                            S_post = S_new.copy()
                        else:
                            S_post = (1 - lam) * S_post + lam * S_new
                        dB = S_post - S_pre
                        c_free = 0
                    else:
                        c_free = min(c_free + 1, int(cfg["dg"]["c_th"]))
                        if c_free >= int(cfg["dg"]["c_th"]):
                            state = FREE
                            pred_k.append([int(open_k_in), k_out])
                            conf_k.append([int(open_k_conf_in), k_st])
                            S_pre = S_new.copy()
                            open_k_in = math.nan
                            open_k_conf_in = math.nan
                            S_post = None
                            dB = None
                            c_free = 0
            else:
                if cfg["dg"]["enable"] and cfg["v"]["use_degrade"]:
                    used_degrade = True
                    L_fix = int(cfg["dg"]["L_fix"])
                    if (k_seek_end - L_fix + 1) >= 1:
                        start = k_seek_end - L_fix + 1
                        S_hat = np.mean(B[start - 1 : k_seek_end, :], axis=0)
                    else:
                        S_hat = np.mean(B[:k_seek_end, :], axis=0)
                    back2env = float(np.linalg.norm(S_hat - S_pre))
                    if back2env < float(cfg["pk"]["D_free"]):
                        c_free = min(c_free + 1, int(cfg["dg"]["c_th"]))
                    else:
                        c_free = 0
                    if c_free >= int(cfg["dg"]["c_th"]):
                        state = FREE
                        pred_k.append([int(open_k_in), k_out])
                        conf_k.append([int(open_k_conf_in), k_seek_end])
                        S_pre = S_hat.copy()
                        open_k_in = math.nan
                        open_k_conf_in = math.nan
                        S_post = None
                        dB = None
                        c_free = 0

        dbg.append(
            EventDbg(
                k_out=k_out,
                state="FREE" if state == FREE else "OCC",  # after update; close enough
                stable_found=stable_found,
                used_degrade=used_degrade,
                drift_mag=drift_mag,
                dist=dist,
            )
        )

    return (
        np.asarray(pred_k, dtype=float).reshape((-1, 2)),
        np.asarray(conf_k, dtype=float).reshape((-1, 2)),
        events,
        dbg,
    )


# ------------------------------
# Baselines
# ------------------------------


@dataclass
class LWCParams:
    theta_park: float = 120.0
    seek_sec: float = 3.0
    c_th: int = 2
    alpha_occ: float = 0.20


def run_lwc_plus_cached(
    B: np.ndarray,
    events: List[dict],
    st: dict,
    cfg: dict,
    params: LWCParams,
) -> np.ndarray:
    """LWC+ baseline (event-driven), cached version.

    Only compares parking detection logic, reusing the same event base.
    """
    fs = float(cfg["fs"])
    seekN = int(round(params.seek_sec * fs))
    stableState = np.asarray(st["stableState"], dtype=bool)
    meanVec = np.asarray(st["meanVec"], dtype=float)

    # init S_prev from first stable point
    idx0 = np.where(stableState)[0]
    if idx0.size > 0:
        k_first = int(idx0[0]) + 1
        S_prev = meanVec[k_first - 1, :].copy()
    else:
        S_prev = B[0, :].copy()

    FREE = 1
    OCC = 2
    state = FREE
    open_in = None
    c_park = 0
    c_free = 0

    out: List[List[int]] = []

    for ev in events:
        k_out = int(ev["k_out"])
        k_seek_end = min(int(B.shape[0]), k_out + seekN)

        slice_st = stableState[k_out - 1 : k_seek_end]
        found = np.where(slice_st)[0]
        if found.size == 0:
            continue
        k_st = k_out + int(found[0])
        S_new = meanVec[k_st - 1, :]

        d = float(np.linalg.norm(S_new - S_prev))

        if state == FREE:
            if d > params.theta_park:
                c_park = min(c_park + 1, params.c_th)
            else:
                c_park = 0
            if c_park >= params.c_th:
                state = OCC
                open_in = k_out
                c_park = 0
                c_free = 0
        else:
            # occupied: maintain via EMA, release when "back to env" long enough
            if d <= params.theta_park:
                c_free = min(c_free + 1, params.c_th)
            else:
                c_free = 0

            S_prev = (1 - params.alpha_occ) * S_prev + params.alpha_occ * S_new

            if c_free >= params.c_th:
                if open_in is not None:
                    out.append([int(open_in), k_out])
                state = FREE
                open_in = None
                c_free = 0

    return np.asarray(out, dtype=float).reshape((-1, 2))


@dataclass
class ADTAParams:
    alpha: float = 0.002
    beta: float = 0.015
    n_on: int = 10
    n_off: int = 10
    Tmin_sec: float = 4.0


def run_adta_fsm(
    B: np.ndarray,
    cfg: dict,
    params: ADTAParams,
) -> np.ndarray:
    """ADTA-FSM baseline (1-based indexing output)."""
    fs = float(cfg["fs"])
    y = np.linalg.norm(B, axis=1)
    n = int(y.size)
    if n == 0:
        return np.zeros((0, 2), dtype=float)

    n_init = int(min(n, max(1, round(fs * 5))))
    F = float(np.mean(y[:n_init]))
    T = float(params.beta * F)

    present = False
    cnt_on = 0
    cnt_off = 0
    occ_active = False
    occ_start: Optional[int] = None
    pred: List[List[int]] = []

    # i in [1..n] (1-based)
    for i in range(1, n + 1):
        dev = abs(float(y[i - 1]) - F)
        if dev < T:
            F = (1 - params.alpha) * F + params.alpha * float(y[i - 1])
        T = params.beta * F
        flag = dev >= T

        if flag:
            cnt_on += 1
            cnt_off = 0
        else:
            cnt_off += 1
            cnt_on = 0

        if (not present) and (cnt_on >= params.n_on):
            present = True
            t0 = i - params.n_on + 1
            if not occ_active:
                occ_active = True
                occ_start = t0
        elif present and (cnt_off >= params.n_off):
            present = False
            t1 = i - params.n_off + 1
            if occ_active and (occ_start is not None):
                dur_sec = (t1 - occ_start) / fs
                if dur_sec >= params.Tmin_sec:
                    pred.append([int(occ_start), int(t1)])
            occ_active = False
            occ_start = None

    # tail
    if occ_active and (occ_start is not None):
        dur_sec = (n - occ_start) / fs
        if dur_sec >= params.Tmin_sec:
            pred.append([int(occ_start), int(n)])
    return np.asarray(pred, dtype=float).reshape((-1, 2))


# ------------------------------
# Summaries + LaTeX row writers
# ------------------------------


def summarize_by_group(T_file: pd.DataFrame) -> pd.DataFrame:
    groups = ["A", "B", "C", "D"]
    rows = []
    for g in groups:
        Tf = T_file[T_file["group"] == g]
        tp = int(Tf["TP"].sum())
        fp = int(Tf["FP"].sum())
        fn = int(Tf["FN"].sum())
        p, r, f1 = _calc_prf(tp, fp, fn)
        ngt = tp + fn
        rf = fp / max(ngt, 1)
        rm = fn / max(ngt, 1)
        rows.append(dict(group=g, TP=tp, FP=fp, FN=fn, P=p, R=r, F1=f1, Rf=rf, Rm=rm))

    tp = int(T_file["TP"].sum())
    fp = int(T_file["FP"].sum())
    fn = int(T_file["FN"].sum())
    p, r, f1 = _calc_prf(tp, fp, fn)
    ngt = tp + fn
    rf = fp / max(ngt, 1)
    rm = fn / max(ngt, 1)
    rows.append(dict(group="ALL", TP=tp, FP=fp, FN=fn, P=p, R=r, F1=f1, Rf=rf, Rm=rm))
    return pd.DataFrame(rows)


def dataset_stats_from_outputs(gt_all: pd.DataFrame, T_file: pd.DataFrame) -> pd.DataFrame:
    groups = ["A", "B", "C", "D"]
    rows = []
    for g in groups:
        files_g = list(pd.unique(gt_all.loc[gt_all["scenario_group"] == g, "file"]))
        Tf = T_file[T_file["group"] == g]
        nFiles = len(files_g)
        Ngt = int(Tf["gt"].sum())
        Nevents = int(Tf["events"].sum())
        Npass = int(max(Nevents - 2 * Ngt, 0))
        rows.append(dict(group=g, num_files=nFiles, num_parking_gt=Ngt, num_vehicle_events=Nevents, num_pass_est=Npass))
    return pd.DataFrame(rows)


def timing_stats_by_group(tim_rows: pd.DataFrame) -> pd.DataFrame:
    """Compute brief timing statistics on matched TP samples (per group).

    Columns:
      - N_TP: number of TP samples (IoU-matched)
      - med_abs_dt_in/out: median absolute boundary error (s)
      - med_tau_in/out: median confirmation delay (s)
    """
    groups = ["A", "B", "C", "D", "ALL"]
    rows = []
    for g in groups:
        Tr = tim_rows if g == "ALL" else tim_rows[tim_rows["group"] == g]
        if Tr.empty:
            rows.append(
                dict(
                    group=g,
                    N_TP=0,
                    med_abs_dt_in=np.nan,
                    med_abs_dt_out=np.nan,
                    med_tau_in=np.nan,
                    med_tau_out=np.nan,
                )
            )
            continue
        rows.append(
            dict(
                group=g,
                N_TP=int(len(Tr)),
                med_abs_dt_in=float(np.median(np.abs(Tr["dt_in"]))),
                med_abs_dt_out=float(np.median(np.abs(Tr["dt_out"]))),
                med_tau_in=float(np.median(Tr["tau_in"])),
                med_tau_out=float(np.median(Tr["tau_out"])),
            )
        )
    return pd.DataFrame(rows)


def write_tex_dataset_rows(T_ds: pd.DataFrame, out_path: str) -> None:
    """Write dataset rows for LaTeX table (sample-size only, no source text)."""
    nFiles = int(T_ds["num_files"].sum())
    Ngt = int(T_ds["num_parking_gt"].sum())
    Npass = int(T_ds["num_pass_est"].sum())

    lines = []
    for _, r in T_ds.iterrows():
        g = str(r.group)
        lines.append(f"{g} & {int(r.num_files)} & {int(r.num_parking_gt)} & {int(r.num_pass_est)} \
")
    lines.append(f"ALL & {nFiles} & {Ngt} & {Npass} \
")
    _write_text(out_path, "".join(lines))


def write_tex_bycase_rows(T_group: pd.DataFrame, out_path: str) -> None:
    lines = []
    for _, r in T_group.iterrows():
        g = str(r.group)
        lines.append(
            f"{g} & {r.P:.3f} & {r.R:.3f} & {r.F1:.3f} & {100*r.Rf:.1f} & {100*r.Rm:.1f} & ({int(r.FP)},{int(r.FN)}) \\\n"
        )
    _write_text(out_path, "".join(lines))


def write_tex_timing_rows(T_timing: pd.DataFrame, out_path: str) -> None:
    """Write brief timing table rows (A/B/C/D/ALL)."""
    lines = []
    for _, r in T_timing.iterrows():
        g = str(r.group)
        lines.append(
            f"{g} & {int(r.N_TP)} & {r.med_abs_dt_in:.2f} & {r.med_abs_dt_out:.2f} & {r.med_tau_in:.2f} & {r.med_tau_out:.2f} \
"
        )
    _write_text(out_path, "".join(lines))


def write_tex_baseline_cmp_rows(summary: pd.DataFrame, out_path: str) -> None:
    """Write baseline comparison rows for `tab:ch4_bycase`.

    Output format (one row per method):
      Method & A(P/R/F1) & B(P/R/F1) & C(P/R/F1) & D(P/R/F1) & ALL(P/R/F1)
    """
    order_g = ["A", "B", "C", "D", "ALL"]

    method_order = [
        ("SP-FSM", "Ours"),
        ("LWC+", "LWC"),
        ("ADTA-FSM", "ADTA-FSM"),
    ]

    lines: List[str] = []
    for disp, key in method_order:
        cells = []
        for g in order_g:
            r = summary[(summary.method == key) & (summary.group == g)].iloc[0]
            cells.append(f"{r.P:.3f} / {r.R:.3f} / {r.F1:.3f}")
        lines.append(f"{disp} & " + " & ".join(cells) + " \
")
    _write_text(out_path, "".join(lines))


def write_tex_ablation_rows(T_ab: pd.DataFrame, out_path: str) -> None:
    def label_and_phen(variant: str) -> Tuple[str, str]:
        if variant == "Ours":
            return "Ours-full", "完整模型"
        if variant == "Abl_noMeanDiff":
            return "Abl-1（去除$M$）", "伪稳态误触发增多，误检上升"
        if variant == "Abl_noSimilarity":
            return "Abl-2（去除$\\mathrm{dist}$）", "占用态过车后误释放或重复占用"
        if variant == "Abl_noDegrade":
            return "Abl-3（去除退化分支）", "拥堵下寻稳失败导致漏检与延迟增大"
        if variant == "Abl_noUpdateGate":
            return "Abl-4（去除更新门控）", "慢漂移背景下参考误更新，产生连锁误判"
        return variant, ""

    lines = []
    for _, r in T_ab.iterrows():
        label, phen = label_and_phen(str(r.variant))
        lines.append(
            f"{label} & {r.F1_all:.3f} & {r.F1_A:.3f} & {r.F1_B:.3f} & {r.F1_C:.3f} & {r.F1_D:.3f} & {phen} \\\n"
        )
    _write_text(out_path, "".join(lines))


# ------------------------------
# Figures
# ------------------------------


def _setup_mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa

    # keep style minimal & thesis-friendly
    return plt


def _save_pdf_png(fig, pdf_path: str) -> None:
    import matplotlib.pyplot as plt

    _ensure_dir(os.path.dirname(pdf_path))
    fig.savefig(pdf_path, bbox_inches="tight")
    png_path = os.path.splitext(pdf_path)[0] + ".png"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_baseline_cmp_f1(summary: pd.DataFrame, out_pdf: str) -> None:
    """Main figure: $F_1$ comparison across A/B/C/D for different methods."""
    plt = _setup_mpl()
    groups = ["A", "B", "C", "D"]
    method_keys = ["Ours", "LWC", "ADTA-FSM"]
    method_labels = {"Ours": "SP-FSM", "LWC": "LWC+", "ADTA-FSM": "ADTA-FSM"}

    M = np.zeros((len(groups), len(method_keys)), dtype=float)
    for gi, g in enumerate(groups):
        for mi, m in enumerate(method_keys):
            M[gi, mi] = float(summary[(summary.method == m) & (summary.group == g)].F1.iloc[0])

    fig = plt.figure(figsize=(10, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True, axis="y")
    x = np.arange(len(groups))
    w = 0.25
    for mi, m in enumerate(method_keys):
        ax.bar(x + (mi - 1) * w, M[:, mi], width=w, label=method_labels.get(m, m))
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylim(0, 1)
    ax.set_ylabel(r"$F_1$")
    ax.legend(loc="upper center", ncol=3)
    _save_pdf_png(fig, out_pdf)


def fig_prf_by_group(T_group: pd.DataFrame, out_pdf: str) -> None:
    plt = _setup_mpl()
    fig = plt.figure(figsize=(10, 4.6))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True, axis="y")

    # keep A-D + ALL
    g = list(T_group.group)
    M = np.stack([T_group.P.to_numpy(), T_group.R.to_numpy(), T_group.F1.to_numpy()], axis=1)
    x = np.arange(len(g))
    offsets = [-0.25, 0.0, 0.25]
    labels = ["P", "R", "F1"]
    for j in range(3):
        ax.bar(x + offsets[j], M[:, j], width=0.22, label=labels[j])
    ax.set_xticks(np.arange(len(g)))
    ax.set_xticklabels(g)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Metric")
    ax.legend(loc="upper center", ncol=3)
    _save_pdf_png(fig, out_pdf)


def fig_errors_by_group(T_group: pd.DataFrame, out_pdf: str) -> None:
    """(MATLAB-style) top: TP/FP/FN; bottom: Rf/Rm."""
    plt = _setup_mpl()
    fig = plt.figure(figsize=(10, 6.8))

    # drop ALL for this plot (more readable)
    Tg = T_group[T_group.group != "ALL"].copy()
    groups = list(Tg.group)
    x = np.arange(len(groups))

    ax1 = fig.add_subplot(2, 1, 1)
    ax1.grid(True, axis="y")
    C = np.stack([Tg.TP.to_numpy(), Tg.FP.to_numpy(), Tg.FN.to_numpy()], axis=1)
    offsets = [-0.25, 0.0, 0.25]
    labels = ["TP", "FP", "FN"]
    for j in range(3):
        ax1.bar(x + offsets[j], C[:, j], width=0.22, label=labels[j])
    ax1.set_xticks(x)
    ax1.set_xticklabels(groups)
    ax1.set_ylabel("Count")
    ax1.legend(loc="upper center", ncol=3)

    ax2 = fig.add_subplot(2, 1, 2)
    ax2.grid(True, axis="y")
    ax2.plot(x, 100 * Tg.Rf.to_numpy(), marker="o", linestyle="-", label="Rf")
    ax2.plot(x, 100 * Tg.Rm.to_numpy(), marker="s", linestyle="--", label="Rm")
    ax2.set_xticks(x)
    ax2.set_xticklabels(groups)
    ax2.set_ylabel("%")
    ax2.legend(loc="upper center", ncol=2)
    _save_pdf_png(fig, out_pdf)


def fig_timing_tau_box(tim_rows: pd.DataFrame, out_pdf: str) -> None:
    plt = _setup_mpl()
    fig = plt.figure(figsize=(10, 6.8))
    Tg = tim_rows[tim_rows.group.isin(["A", "B", "C", "D"])]
    groups = ["A", "B", "C", "D"]

    ax1 = fig.add_subplot(2, 1, 1)
    data1 = [Tg[Tg.group == g].tau_in.to_numpy() for g in groups]
    ax1.boxplot(data1, labels=groups, showfliers=False)
    ax1.grid(True, axis="y")
    ax1.set_ylabel(r"$\tau_{in}$ (s)")

    ax2 = fig.add_subplot(2, 1, 2)
    data2 = [Tg[Tg.group == g].tau_out.to_numpy() for g in groups]
    ax2.boxplot(data2, labels=groups, showfliers=False)
    ax2.grid(True, axis="y")
    ax2.set_ylabel(r"$\tau_{out}$ (s)")
    ax2.set_xlabel("Group")

    _save_pdf_png(fig, out_pdf)


def _plot_ecdf(ax, v: np.ndarray, label: str) -> None:
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return
    v = np.sort(v)
    y = np.arange(1, v.size + 1) / v.size
    ax.plot(v, y, label=label)


def fig_timing_dt_cdf(tim_rows: pd.DataFrame, out_pdf: str) -> None:
    plt = _setup_mpl()
    fig = plt.figure(figsize=(10, 6.8))
    Tg = tim_rows[tim_rows.group.isin(["A", "B", "C", "D"])]
    groups = ["A", "B", "C", "D"]

    ax1 = fig.add_subplot(2, 1, 1)
    ax1.grid(True)
    for g in groups:
        v = np.abs(Tg[Tg.group == g].dt_in.to_numpy())
        _plot_ecdf(ax1, v, g)
    ax1.set_xlabel(r"$|\Delta t_{in}|$ (s)")
    ax1.set_ylabel("CDF")
    ax1.legend(loc="lower right", ncol=4)

    ax2 = fig.add_subplot(2, 1, 2)
    ax2.grid(True)
    for g in groups:
        v = np.abs(Tg[Tg.group == g].dt_out.to_numpy())
        _plot_ecdf(ax2, v, g)
    ax2.set_xlabel(r"$|\Delta t_{out}|$ (s)")
    ax2.set_ylabel("CDF")
    ax2.legend(loc="lower right", ncol=4)

    _save_pdf_png(fig, out_pdf)


def fig_param_scan_Dth(A_drift_mag: np.ndarray, A_is_park: np.ndarray, D_th: float, out_pdf: str) -> None:
    plt = _setup_mpl()
    A_drift_mag = np.asarray(A_drift_mag, dtype=float).reshape((-1,))
    A_is_park = np.asarray(A_is_park, dtype=bool).reshape((-1,))
    mask = np.isfinite(A_drift_mag)
    A_drift_mag = A_drift_mag[mask]
    A_is_park = A_is_park[mask]
    v0 = A_drift_mag[~A_is_park]
    v1 = A_drift_mag[A_is_park]
    if A_drift_mag.size == 0:
        return
    bins = 30
    edges = np.linspace(float(np.min(A_drift_mag)), float(np.max(A_drift_mag)), bins + 1)
    c = (edges[:-1] + edges[1:]) / 2
    p0, _ = np.histogram(v0, bins=edges, density=True)
    p1, _ = np.histogram(v1, bins=edges, density=True)

    fig = plt.figure(figsize=(10, 4.6))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True)
    ax.plot(c, p0, linestyle="-", label="pass/interf")
    ax.plot(c, p1, linestyle="--", label="park-arrive")
    ax.axvline(D_th, linestyle=":", linewidth=1.5)
    ax.set_xlabel(r"$\|\Delta B\|_2$")
    ax.set_ylabel("density")
    ax.legend(loc="best")
    _save_pdf_png(fig, out_pdf)


def fig_param_scan_dist(B_dist: np.ndarray, B_is_leave: np.ndarray, dist_th: float, out_pdf: str) -> None:
    plt = _setup_mpl()
    B_dist = np.asarray(B_dist, dtype=float).reshape((-1,))
    B_is_leave = np.asarray(B_is_leave, dtype=bool).reshape((-1,))
    mask = np.isfinite(B_dist)
    B_dist = B_dist[mask]
    B_is_leave = B_is_leave[mask]

    d_keep = B_dist[~B_is_leave]
    d_leave = B_dist[B_is_leave]
    if d_keep.size == 0:
        return

    bins = 25
    edges = np.linspace(0.0, float(np.max(d_keep)) * 1.05 + 1e-9, bins + 1)
    c = (edges[:-1] + edges[1:]) / 2
    p_keep, _ = np.histogram(d_keep, bins=edges, density=True)

    fig = plt.figure(figsize=(10, 4.6))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True)
    ax.plot(c, p_keep, linestyle="-", label="keep-occ")

    if d_leave.size >= 5:
        p_leave, _ = np.histogram(d_leave, bins=edges, density=True)
        ax.plot(c, p_leave, linestyle="--", label="leave (if dist valid)")
    else:
        ax.text(
            0.02,
            0.10,
            "leave is mostly decided by D_free; dist samples may be few",
            transform=ax.transAxes,
            fontsize=9,
            color=(0.3, 0.3, 0.3),
        )

    ax.axvline(dist_th, linestyle=":", linewidth=1.5)
    acc = float(np.mean(d_keep < dist_th)) if d_keep.size else float("nan")
    ax.text(0.02, 0.90, f"Acc@dist_th={100*acc:.1f}%", transform=ax.transAxes, fontsize=10)
    ax.set_xlabel("dist")
    ax.set_ylabel("density")
    ax.legend(loc="best")
    _save_pdf_png(fig, out_pdf)


def fig_C_seek_ratio(r_found: float, r_deg: float, out_pdf: str) -> None:
    plt = _setup_mpl()
    fig = plt.figure(figsize=(6.0, 4.2))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True, axis="y")
    vals = [r_found, r_deg]
    ax.bar([0, 1], vals)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["stable_found", "use_degrade"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("ratio")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.03, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    _save_pdf_png(fig, out_pdf)


def fig_ablation_by_group(T_ab: pd.DataFrame, out_pdf: str) -> None:
    plt = _setup_mpl()
    fig = plt.figure(figsize=(10, 4.8))
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True, axis="y")
    M = np.stack([T_ab.F1_A.to_numpy(), T_ab.F1_B.to_numpy(), T_ab.F1_C.to_numpy(), T_ab.F1_D.to_numpy()], axis=1)
    x = np.arange(M.shape[0])
    w = 0.18
    labels = ["A", "B", "C", "D"]
    for j in range(4):
        ax.bar(x + (j - 1.5) * w, M[:, j], width=w, label=labels[j])
    ax.set_xticks(x)
    ax.set_xticklabels(list(T_ab.variant))
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1")
    ax.legend(loc="upper center", ncol=4)
    _save_pdf_png(fig, out_pdf)


def fig_sensitivity(A_drift_mag: np.ndarray, A_is_park: np.ndarray, B_dist: np.ndarray, B_is_leave: np.ndarray, D_th: float, dist_th: float, out_pdf: str) -> None:
    plt = _setup_mpl()
    fig = plt.figure(figsize=(10.5, 4.6))

    # (Left) D_th sweep: TPR/FPR (event-level)
    ax1 = fig.add_subplot(1, 2, 1)
    ax1.grid(True)
    x = np.asarray(A_drift_mag, dtype=float).reshape((-1,))
    y = np.asarray(A_is_park, dtype=bool).reshape((-1,))
    mask = np.isfinite(x)
    x = x[mask]
    y = y[mask]
    if x.size:
        grid = np.linspace(float(np.min(x)), float(np.max(x)), 40)
        tpr = []
        fpr = []
        for th in grid:
            yp = x > th
            TP = int(np.sum(yp & y))
            FN = int(np.sum((~yp) & y))
            FP = int(np.sum(yp & (~y)))
            TN = int(np.sum((~yp) & (~y)))
            tpr.append(TP / max(TP + FN, 1))
            fpr.append(FP / max(FP + TN, 1))
        ax1.plot(grid, tpr, label="TPR")
        ax1.plot(grid, fpr, linestyle="--", label="FPR")
        ax1.axvline(D_th, linestyle=":")
        ax1.legend(loc="best")
    ax1.set_xlabel(r"$D_{th}$")
    ax1.set_ylabel("ratio")

    # (Right) dist_th sweep: Acc(d)=P(dist<d) on keep-occ events
    ax2 = fig.add_subplot(1, 2, 2)
    ax2.grid(True)
    dist = np.asarray(B_dist, dtype=float).reshape((-1,))
    is_leave = np.asarray(B_is_leave, dtype=bool).reshape((-1,))
    keep = (~is_leave) & np.isfinite(dist)
    d_keep = dist[keep]
    if d_keep.size:
        grid2 = np.linspace(0.0, float(np.max(d_keep)) * 1.05 + 1e-9, 40)
        acc = [float(np.mean(d_keep < d)) for d in grid2]
        upd = [1 - a for a in acc]
        ax2.plot(grid2, acc, label=r"$Acc(d)$")
        ax2.plot(grid2, upd, linestyle="--", label=r"$1-Acc(d)$")
        ax2.axvline(dist_th, linestyle=":")
        ax2.legend(loc="best")
    ax2.set_xlabel(r"$dist_{th}$")
    ax2.set_ylabel("ratio")

    _save_pdf_png(fig, out_pdf)


# ------------------------------
# Main pipeline
# ------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_zip", default="data.zip")
    ap.add_argument("--pack_zip", default="ch4_onekey_pack_nodata.zip")
    ap.add_argument("--work_dir", default="_work_ch4")
    ap.add_argument("--out_dir", default="out_ch4_thesis")
    ap.add_argument("--use_synth", type=int, default=1)

    ap.add_argument("--tuned", type=int, default=1)
    ap.add_argument("--Tmin", type=float, default=4.0)
    ap.add_argument("--gap_merge", type=float, default=0.0)
    ap.add_argument("--iou_th", type=float, default=0.5)

    ap.add_argument("--no_ablation", action="store_true", help="skip ablation study (faster)")
    ap.add_argument("--optional_figs", action="store_true", help="export optional figures (not needed for minimal thesis)")
    args = ap.parse_args()

    work_dir = os.path.abspath(args.work_dir)
    out_dir = os.path.abspath(args.out_dir)
    data_zip = os.path.abspath(args.data_zip)
    pack_zip = os.path.abspath(args.pack_zip)

    if not os.path.exists(data_zip):
        print(f"[ERR] data_zip not found: {data_zip}", file=sys.stderr)
        return 2
    if not os.path.exists(pack_zip):
        print(f"[ERR] pack_zip not found: {pack_zip}", file=sys.stderr)
        return 2

    # prepare dirs
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    data_root = os.path.join(work_dir, "data")
    pack_root = os.path.join(work_dir, "ch4_onekey_pack")
    os.makedirs(data_root, exist_ok=True)
    os.makedirs(pack_root, exist_ok=True)

    with zipfile.ZipFile(data_zip, "r") as zf:
        zf.extractall(work_dir)
    with zipfile.ZipFile(pack_zip, "r") as zf:
        zf.extractall(work_dir)

    data_dir = os.path.join(work_dir, "data", "zhenzhi")
    synth_dir = os.path.join(work_dir, "data", "synth_out")
    gt_path = os.path.join(data_dir, "parking_groundtruth_filled_cleaned.csv")
    if not os.path.exists(gt_path):
        print(f"[ERR] GT not found: {gt_path}", file=sys.stderr)
        return 2

    ch4_py = os.path.join(pack_root, "python", "ch4_verify_python.py")
    if not os.path.exists(ch4_py):
        # zip root may already be 'ch4_onekey_pack/...'
        ch4_py = os.path.join(work_dir, "ch4_onekey_pack", "python", "ch4_verify_python.py")
    if not os.path.exists(ch4_py):
        print(f"[ERR] cannot locate ch4_verify_python.py under extracted pack", file=sys.stderr)
        return 2
    ch4 = _load_ch4_module(ch4_py)

    cfg = ch4.cfg_global_v2()

    # --- tuned overrides (match your latest baseline comparison run) ---
    if args.tuned:
        cfg["pk"]["D_th"] = 36.0
        cfg["pk"]["T_seek_sec"] = 3.0
        cfg["pk"]["D_free"] = 30.0
        cfg["pk"]["dist_th"] = 20.1886907302364
        cfg["ref"]["D_upd"] = 30.0

    b_xy, b_z = ch4.design_fir(cfg)

    gt_base = pd.read_csv(gt_path)
    gt_all = gt_base.copy()
    if args.use_synth:
        gt_all = ch4.append_synth_gt_all_events(gt_base, synth_dir)

    files = sorted(pd.unique(gt_all["file"]))
    print(f"[INFO] files={len(files)} (use_synth={args.use_synth})")

    # ------------------------------
    # Cache heavy per-file features
    # ------------------------------
    cache: Dict[str, dict] = {}
    for file_name in files:
        csv_path = _find_csv(file_name, data_dir, synth_dir)
        if csv_path is None:
            print(f"[WARN] missing CSV for {file_name}")
            continue
        k, t, B = ch4.load_csv(csv_path, cfg["fs"])
        k0 = int(k[0])
        gt_f = gt_all[gt_all["file"] == file_name]
        group = str(gt_f["scenario_group"].iloc[0])
        gt_idx = np.column_stack(
            [gt_f["k_star_in"].to_numpy(dtype=int) - k0 + 1, gt_f["k_star_out"].to_numpy(dtype=int) - k0 + 1]
        ).astype(float)

        pr = ch4.pr_vehicle(B, cfg, b_xy, b_z)
        events = ch4.detect_events(pr, cfg)
        st = ch4.stability(B, cfg)

        cache[file_name] = {
            "group": group,
            "B": B,
            "gt_idx": gt_idx,
            "events": events,
            "st": st,
        }

    if not cache:
        print("[ERR] no valid files in cache", file=sys.stderr)
        return 2

    fs = float(cfg["fs"])

    # ------------------------------
    # Evaluate OURS (full) with debug
    # ------------------------------
    rows_file = []
    tim_rows = []
    A_drift_mag = []
    A_is_park = []
    B_dist = []
    B_is_leave = []
    C_stable_found = []
    C_used_degrade = []

    for file_name, item in cache.items():
        B = item["B"]
        gt_idx = item["gt_idx"]
        group = item["group"]
        events = item["events"]
        st = item["st"]

        pred, conf, events2, dbg = run_parking_with_dbg(ch4, B, cfg, b_xy, b_z, events=events, st=st)
        pred_pp, conf_pp = postprocess_pred_conf(pred, conf, fs, args.Tmin, args.gap_merge)

        tp, fp, fn, p, r, f1, match = eval_iou_with_match(pred_pp, gt_idx, args.iou_th)
        rows_file.append(
            dict(
                file=file_name,
                group=group,
                TP=tp,
                FP=fp,
                FN=fn,
                P=p,
                R=r,
                F1=f1,
                events=len(events2),
                pred=int(pred_pp.shape[0]),
                gt=int(gt_idx.shape[0]),
            )
        )

        # timing rows on matched TP
        for ip, ig, iou in match:
            pseg = pred_pp[ip]
            cseg = conf_pp[ip]
            gseg = gt_idx[ig]
            tim_rows.append(
                dict(
                    file=file_name,
                    group=group,
                    dt_in=float((pseg[0] - gseg[0]) / fs),
                    dt_out=float((pseg[1] - gseg[1]) / fs),
                    tau_in=float((cseg[0] - gseg[0]) / fs),
                    tau_out=float((cseg[1] - gseg[1]) / fs),
                    iou=float(iou),
                    gt_dur=float((gseg[1] - gseg[0]) / fs),
                )
            )

        # E2 evidence collection
        tol_k = int(round(2.0 * fs))
        arr_idx, leave_idx = match_events_to_gt(events2, gt_idx, tol_k)

        if group == "A":
            for m, d in enumerate(dbg):
                if math.isnan(d.drift_mag):
                    continue
                A_drift_mag.append(d.drift_mag)
                A_is_park.append(m in arr_idx)

        if group == "B":
            for m, d in enumerate(dbg):
                if math.isnan(d.dist):
                    continue
                B_dist.append(d.dist)
                B_is_leave.append(m in leave_idx)

        if group == "C":
            C_stable_found.extend([bool(d.stable_found) for d in dbg])
            C_used_degrade.extend([bool(d.used_degrade) for d in dbg])

    T_file = pd.DataFrame(rows_file)
    T_group = summarize_by_group(T_file)
    T_ds = dataset_stats_from_outputs(gt_all, T_file)
    tim_df = pd.DataFrame(tim_rows)
    T_timing = timing_stats_by_group(tim_df)

    # ------------------------------
    # Baselines: LWC + ADTA-FSM
    # ------------------------------
    lwc_params = LWCParams(theta_park=120.0, seek_sec=3.0, c_th=2, alpha_occ=0.20)
    adta_params = ADTAParams(alpha=0.002, beta=0.015, n_on=10, n_off=10, Tmin_sec=args.Tmin)

    rows_cmp = []
    for method in ["Ours", "LWC", "ADTA-FSM"]:
        for file_name, item in cache.items():
            B = item["B"]
            gt_idx = item["gt_idx"]
            group = item["group"]
            events = item["events"]
            st = item["st"]

            if method == "Ours":
                pred, conf, _, _ = run_parking_with_dbg(ch4, B, cfg, b_xy, b_z, events=events, st=st)
                pred_pp, _ = postprocess_pred_conf(pred, conf, fs, args.Tmin, args.gap_merge)
            elif method == "LWC":
                pred = run_lwc_plus_cached(B, events, st, cfg, lwc_params)
                pred_pp = postprocess_segments(pred, fs, args.Tmin, args.gap_merge)
            else:
                pred = run_adta_fsm(B, cfg, adta_params)
                pred_pp = postprocess_segments(pred, fs, args.Tmin, args.gap_merge)

            tp, fp, fn, p, r, f1, _ = eval_iou_with_match(pred_pp, gt_idx, args.iou_th)
            rows_cmp.append(dict(method=method, file=file_name, group=group, TP=tp, FP=fp, FN=fn, P=p, R=r, F1=f1))

    T_cmp_file = pd.DataFrame(rows_cmp)
    # summarize for baseline table
    sum_rows = []
    for m in ["Ours", "LWC", "ADTA-FSM"]:
        for g in ["A", "B", "C", "D", "ALL"]:
            if g == "ALL":
                Tf = T_cmp_file[T_cmp_file.method == m]
            else:
                Tf = T_cmp_file[(T_cmp_file.method == m) & (T_cmp_file.group == g)]
            tp = int(Tf.TP.sum())
            fp = int(Tf.FP.sum())
            fn = int(Tf.FN.sum())
            p, r, f1 = _calc_prf(tp, fp, fn)
            sum_rows.append(dict(method=m, group=g, TP=tp, FP=fp, FN=fn, P=p, R=r, F1=f1))
    T_cmp = pd.DataFrame(sum_rows)

    # ------------------------------
    # Ablation study (optional)
    # ------------------------------
    T_ab = None
    if not args.no_ablation:
        variants = [
            ("Ours", {}),
            ("Abl_noMeanDiff", {"pk.D_th": 0.0}),
            ("Abl_noSimilarity", {"v.use_similarity": 0}),
            ("Abl_noDegrade", {"v.use_degrade": 0, "dg.enable": 0}),
            ("Abl_noUpdateGate", {"v.use_update_gate": 0}),
        ]

        ab_rows = []
        for vname, patch in variants:
            cfg_v = ch4.cfg_global_v2()
            if args.tuned:
                cfg_v["pk"]["D_th"] = 36.0
                cfg_v["pk"]["T_seek_sec"] = 3.0
                cfg_v["pk"]["D_free"] = 30.0
                cfg_v["pk"]["dist_th"] = 20.1886907302364
                cfg_v["ref"]["D_upd"] = 30.0
            # apply patch
            for k, val in patch.items():
                a, b = k.split(".")
                cfg_v[a][b] = val

            tp_g = {g: 0 for g in ["A", "B", "C", "D"]}
            fp_g = {g: 0 for g in ["A", "B", "C", "D"]}
            fn_g = {g: 0 for g in ["A", "B", "C", "D"]}

            for file_name, item in cache.items():
                B = item["B"]
                gt_idx = item["gt_idx"]
                g = item["group"]
                events = item["events"]
                st = item["st"]

                pred, conf, _, _ = run_parking_with_dbg(ch4, B, cfg_v, b_xy, b_z, events=events, st=st)
                pred_pp, _ = postprocess_pred_conf(pred, conf, fs, args.Tmin, args.gap_merge)
                tp, fp, fn, _, _, _, _ = eval_iou_with_match(pred_pp, gt_idx, args.iou_th)
                tp_g[g] += tp
                fp_g[g] += fp
                fn_g[g] += fn

            # compute F1s
            def f1(tp: int, fp: int, fn: int) -> float:
                return _calc_prf(tp, fp, fn)[2]

            f1A = f1(tp_g["A"], fp_g["A"], fn_g["A"])
            f1B = f1(tp_g["B"], fp_g["B"], fn_g["B"])
            f1C = f1(tp_g["C"], fp_g["C"], fn_g["C"])
            f1D = f1(tp_g["D"], fp_g["D"], fn_g["D"])
            tp_all = sum(tp_g.values())
            fp_all = sum(fp_g.values())
            fn_all = sum(fn_g.values())
            f1All = f1(tp_all, fp_all, fn_all)
            ab_rows.append(dict(variant=vname, F1_all=f1All, F1_A=f1A, F1_B=f1B, F1_C=f1C, F1_D=f1D))

        T_ab = pd.DataFrame(ab_rows)

    # ------------------------------
    # Write LaTeX rows
    # ------------------------------
    tables_dir = os.path.join(out_dir, "tables")
    images_dir = os.path.join(out_dir, "images")
    _ensure_dir(tables_dir)
    _ensure_dir(images_dir)

    write_tex_dataset_rows(T_ds, os.path.join(tables_dir, "ch4_dataset_rows.tex"))
    write_tex_bycase_rows(T_group, os.path.join(tables_dir, "ch4_bycase_global_rows.tex"))
    write_tex_baseline_cmp_rows(T_cmp, os.path.join(tables_dir, "ch4_bycase_compare_rows.tex"))
    write_tex_timing_rows(T_timing, os.path.join(tables_dir, "ch4_timing_global_rows.tex"))
    if T_ab is not None:
        write_tex_ablation_rows(T_ab, os.path.join(tables_dir, "ch4_ablation_global_rows.tex"))

    # ------------------------------
    # Figures
    # ------------------------------
    # Minimal set for thesis main body
    fig_baseline_cmp_f1(T_cmp, os.path.join(images_dir, "ch4_baseline_cmp_f1.pdf"))

    if len(C_stable_found) > 0:
        r_found = float(np.mean(np.asarray(C_stable_found, dtype=float)))
        r_deg = float(np.mean(np.asarray(C_used_degrade, dtype=float)))
        fig_C_seek_ratio(r_found, r_deg, os.path.join(images_dir, "ch4_C_seek_ratio.pdf"))

    # Optional figures (not required for the minimal thesis version)
    if args.optional_figs:
        fig_prf_by_group(T_group, os.path.join(images_dir, "ch4_opt_prf_by_group.pdf"))
        fig_errors_by_group(T_group, os.path.join(images_dir, "ch4_opt_errors_by_group.pdf"))
        fig_timing_tau_box(tim_df, os.path.join(images_dir, "ch4_opt_timing_tau_box.pdf"))
        fig_timing_dt_cdf(tim_df, os.path.join(images_dir, "ch4_opt_timing_dt_cdf.pdf"))

        if len(A_drift_mag) > 0:
            fig_param_scan_Dth(
                np.asarray(A_drift_mag),
                np.asarray(A_is_park),
                float(cfg["pk"]["D_th"]),
                os.path.join(images_dir, "ch4_param_scan_Dth.pdf"),
            )
        if len(B_dist) > 0:
            fig_param_scan_dist(
                np.asarray(B_dist),
                np.asarray(B_is_leave),
                float(cfg["pk"]["dist_th"]),
                os.path.join(images_dir, "ch4_param_scan_dist.pdf"),
            )

        if T_ab is not None:
            fig_ablation_by_group(T_ab, os.path.join(images_dir, "ch4_opt_ablation_by_group.pdf"))

        if (len(A_drift_mag) > 0) and (len(B_dist) > 0):
            fig_sensitivity(
                np.asarray(A_drift_mag),
                np.asarray(A_is_park),
                np.asarray(B_dist),
                np.asarray(B_is_leave),
                float(cfg["pk"]["D_th"]),
                float(cfg["pk"]["dist_th"]),
                os.path.join(images_dir, "ch4_sensitivity.pdf"),
            )

# Save CSV snapshots (optional, helpful for debugging)
    _ensure_dir(os.path.join(out_dir, "csv"))
    T_file.to_csv(os.path.join(out_dir, "csv", "E1_per_file.csv"), index=False, encoding="utf-8-sig")
    T_group.to_csv(os.path.join(out_dir, "csv", "E1_by_group.csv"), index=False, encoding="utf-8-sig")
    T_ds.to_csv(os.path.join(out_dir, "csv", "E0_dataset_stats.csv"), index=False, encoding="utf-8-sig")
    T_timing.to_csv(os.path.join(out_dir, "csv", "E1_timing_by_group.csv"), index=False, encoding="utf-8-sig")
    T_cmp.to_csv(os.path.join(out_dir, "csv", "E1_baseline_cmp_by_group.csv"), index=False, encoding="utf-8-sig")
    if T_ab is not None:
        T_ab.to_csv(os.path.join(out_dir, "csv", "E3_ablation_by_group.csv"), index=False, encoding="utf-8-sig")

    print(f"[OK] LaTeX tables written to: {tables_dir}")
    print(f"[OK] Figures written to: {images_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
