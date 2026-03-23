#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新生成第三章图 3.6：
把原先“每类 1 个代表样本的 1x3 子图”改成“每类 3 个样本的分组对比图”。

设计目标：
1. 让小型车 / 中型车 / 大型车的差异更直观。
2. 仍然只基于现有 .mat 数据文件，不改论文中的图片路径。
3. 输出到：
   - figures/ch3_waveform_by_class.png
   - images/ch3_waveform_by_class.png
"""

from __future__ import annotations

import argparse
from pathlib import Path
import itertools
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle
import numpy as np
import scipy.io as sio


FS = 50
N0 = 10
L_REF = 176
CLASS_NAMES = ["小型车", "中型车", "大型车"]
AXIS_LABELS = ["X轴", "Y轴", "Z轴"]
AXIS_COLORS = ["#0072BD", "#D95319", "#EDB120"]


def pick_font() -> None:
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def extract_event(bpad: np.ndarray, n: int, fs: int = FS, n0: int = N0):
    b = np.asarray(bpad[: int(n), :], dtype=float)
    base_len = min(int(n0), len(b))
    b0 = b[:base_len].mean(axis=0)
    db = b - b0
    mag = np.sqrt(np.sum(db**2, axis=1))
    t = np.arange(len(b), dtype=float) / fs
    return b, db, mag, t


def crop_by_mag(mag: np.ndarray, frac: float = 0.10, margin: int = 5) -> np.ndarray:
    mag = np.asarray(mag, dtype=float).reshape(-1)
    if mag.size == 0:
        return np.array([], dtype=int)
    thr = frac * np.max(mag)
    pos = np.flatnonzero(mag >= thr)
    if pos.size == 0:
        return np.arange(mag.size, dtype=int)
    start = max(0, int(pos[0]) - margin)
    end = min(mag.size, int(pos[-1]) + margin + 1)
    return np.arange(start, end, dtype=int)


def resample_linear(x: np.ndarray, out_len: int) -> np.ndarray:
    x = np.asarray(x, dtype=float).reshape(-1)
    if x.size == out_len:
        return x.copy()
    xp = np.linspace(0.0, 1.0, x.size)
    xq = np.linspace(0.0, 1.0, out_len)
    return np.interp(xq, xp, x)


def pct(x: np.ndarray, p: float) -> float:
    return float(np.percentile(np.asarray(x, dtype=float), p))


def scale01(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo = np.min(x)
    hi = np.max(x)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-12:
        return np.full_like(x, 0.5, dtype=float)
    return (x - lo) / (hi - lo)


def find_repo_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "xdupgthesis_template_lc.tex").exists():
            return cand
    raise FileNotFoundError("未找到仓库根目录（缺少 xdupgthesis_template_lc.tex）")


def find_default_mat_path(script_dir: Path, repo_root: Path) -> Path:
    candidates = [
        script_dir / "processedVehicleData_3class_REAL (2).mat",
        repo_root / "绘图" / "第三章" / "20260304" / "processedVehicleData_3class_REAL (2).mat",
        repo_root / "绘图" / "第三章" / "20260304" / "ch3_assets_plus_matlab" / "processedVehicleData_3class_REAL (2).mat",
    ]
    for cand in candidates:
        if cand.exists():
            return cand

    matches = sorted(repo_root.rglob("processedVehicleData_3class_REAL (2).mat"))
    if matches:
        return matches[0]
    raise FileNotFoundError("未找到 processedVehicleData_3class_REAL (2).mat 数据文件")


def load_processed_data(mat_path: Path):
    mat = sio.loadmat(mat_path)
    return mat["ProcessedData"], mat["targetLength"]


def corr_score(a: np.ndarray, b: np.ndarray) -> float:
    c = np.corrcoef(a, b)[0, 1]
    if not np.isfinite(c):
        return 0.0
    return float(c)


def choose_diverse_trio(
    candidate_ids: np.ndarray,
    feat: np.ndarray,
    amp: np.ndarray,
    rough: np.ndarray,
    curv: np.ndarray,
    turns: np.ndarray,
    dur: np.ndarray,
    target_amp: float,
    weights: Dict[str, float],
) -> Tuple[np.ndarray, float]:
    if candidate_ids.size < 3:
        raise ValueError("候选样本不足 3 个，无法执行三元组组合搜索")

    best_ids = None
    best_score = -np.inf
    for trio in itertools.combinations(candidate_ids.tolist(), 3):
        trio = np.asarray(trio, dtype=int)
        sims = []
        for ia, ib in itertools.combinations(trio.tolist(), 2):
            sims.append(corr_score(feat[ia], feat[ib]))
        diversity = sum(1.0 - s for s in sims)
        q = -np.sum(rough[trio] + 0.9 * curv[trio] + 0.01 * turns[trio])
        amp_term = -np.sum(np.abs(amp[trio] - target_amp)) / max(target_amp, 1.0)
        dur_term = np.std(dur[trio]) / 20.0
        turn_term = np.std(turns[trio]) / 5.0
        score = (
            weights["diversity"] * diversity
            + weights["quality"] * q
            + weights["amp"] * amp_term
            + weights["dur"] * dur_term
            + weights["turn"] * turn_term
        )
        if score > best_score:
            best_score = float(score)
            best_ids = trio

    return best_ids, best_score


def select_grouped_samples(processed_data, target_length, fs: int = FS, n0: int = N0, l_ref: int = L_REF):
    n_class = processed_data.shape[1]
    feat_cell: List[np.ndarray] = []
    energy_cell: List[np.ndarray] = []
    amp_cell: List[np.ndarray] = []
    len_cell: List[np.ndarray] = []
    rough_cell: List[np.ndarray] = []
    curv_cell: List[np.ndarray] = []
    turns_cell: List[np.ndarray] = []
    tmpl = np.zeros((n_class, 3 * l_ref), dtype=float)

    for c in range(n_class):
        len_vec = np.asarray(target_length[0, c]).ravel().astype(float)
        class_cell = processed_data[0, c]
        n_samp = len_vec.size

        feat = np.zeros((n_samp, 3 * l_ref), dtype=float)
        energy = np.zeros(n_samp, dtype=float)
        amp = np.zeros(n_samp, dtype=float)
        rough = np.zeros(n_samp, dtype=float)
        curv = np.zeros(n_samp, dtype=float)
        turns = np.zeros(n_samp, dtype=float)

        for i in range(n_samp):
            _, db, mag, _ = extract_event(class_cell[0, i], len_vec[i], fs, n0)
            use = crop_by_mag(mag, 0.10, 5)
            db_use = db[use, :]
            energy[i] = np.sum(mag**2)
            amp[i] = np.max(np.abs(db_use))
            rough[i] = np.mean(np.abs(np.diff(db_use, axis=0))) / (amp[i] + np.finfo(float).eps)
            if db_use.shape[0] > 2:
                curv[i] = np.mean(np.abs(np.diff(db_use, n=2, axis=0))) / (amp[i] + np.finfo(float).eps)
            dx = np.diff(db_use[:, 0])
            if dx.size > 1:
                turns[i] = np.sum(np.sign(dx[:-1]) * np.sign(dx[1:]) < 0)

            x_ref = np.zeros((l_ref, 3), dtype=float)
            for k in range(3):
                xk = resample_linear(db[:, k], l_ref)
                xk = (xk - xk.mean()) / (xk.std() + np.finfo(float).eps)
                x_ref[:, k] = xk
            feat[i, :] = x_ref.reshape(-1)

        feat_cell.append(feat)
        energy_cell.append(energy)
        amp_cell.append(amp)
        len_cell.append(len_vec)
        rough_cell.append(rough)
        curv_cell.append(curv)
        turns_cell.append(turns)

        tmp = feat.mean(axis=0)
        tmpl[c, :] = (tmp - tmp.mean()) / (tmp.std() + np.finfo(float).eps)

    class_cfg = [
        {
            "q_list": [35, 50, 70],
            "amp_lo_q": 45,
            "amp_hi_q": 68,
            "energy_lo_q": 35,
            "rough_hi_q": 75,
            "curv_hi_q": 85,
            "own_w": 1.15,
            "margin_w": 1.55,
            "energy_w": 0.22,
            "amp_w": 0.05,
            "rough_w": 0.75,
            "curv_w": 0.45,
            "len_w": 0.25,
        },
        {
            "q_list": [35, 55, 75],
            "amp_lo_q": 40,
            "amp_hi_q": 72,
            "energy_lo_q": 40,
            "rough_hi_q": 75,
            "curv_hi_q": 80,
            "own_w": 1.15,
            "margin_w": 1.45,
            "energy_w": 0.26,
            "amp_w": 0.18,
            "rough_w": 0.90,
            "curv_w": 0.55,
            "len_w": 0.26,
        },
        {
            "q_list": [30, 50, 70],
            "amp_lo_q": 45,
            "amp_hi_q": 80,
            "energy_lo_q": 45,
            "rough_hi_q": 60,
            "curv_hi_q": 70,
            "own_w": 1.10,
            "margin_w": 1.35,
            "energy_w": 0.28,
            "amp_w": 0.24,
            "rough_w": 1.25,
            "curv_w": 0.95,
            "len_w": 0.28,
        },
    ]
    rep_idx = np.zeros((n_class, 3), dtype=int)
    rep_len = np.zeros((n_class, 3), dtype=int)
    rep_score = np.zeros((n_class, 3), dtype=float)
    rep_amp = np.zeros((n_class, 3), dtype=float)
    chosen_amp_by_class: List[List[float]] = [[] for _ in range(n_class)]

    for c in range(n_class):
        cfg = class_cfg[c]
        feat = feat_cell[c]
        energy = energy_cell[c]
        amp = amp_cell[c]
        len_vec = len_cell[c]
        rough = rough_cell[c]
        curv = curv_cell[c]
        turns = turns_cell[c]

        own = feat @ tmpl[c, :].T / (3 * l_ref)
        other = np.full(feat.shape[0], -np.inf)
        for oc in range(n_class):
            if oc == c:
                continue
            oc_score = feat @ tmpl[oc, :].T / (3 * l_ref)
            other = np.maximum(other, oc_score)

        margin = own - other
        base = (
            cfg["own_w"] * scale01(own)
            + cfg["margin_w"] * scale01(margin)
            + cfg["energy_w"] * scale01(np.log(energy + 1))
            + cfg["amp_w"] * scale01(amp)
            - cfg["rough_w"] * scale01(rough)
            - cfg["curv_w"] * scale01(curv)
        )

        mask = (
            (amp >= pct(amp, cfg["amp_lo_q"]))
            & (amp <= pct(amp, cfg["amp_hi_q"]))
            & (energy >= pct(energy, cfg["energy_lo_q"]))
            & (rough <= pct(rough, cfg["rough_hi_q"]))
            & (curv <= pct(curv, cfg["curv_hi_q"]))
        )

        if c == 0:
            # 小型车整体幅值必须明显低于中型车，避免视觉上“比中型车更大”。
            med_amp_q25 = pct(amp_cell[1], 25)
            mask &= amp <= 0.90 * med_amp_q25
        elif c == 1 and chosen_amp_by_class[0]:
            # 中型车必须整体强于已经选出的三条小型车。
            small_max = max(chosen_amp_by_class[0])
            mask &= amp >= 1.15 * small_max
        elif c == 2 and chosen_amp_by_class[1]:
            # 大型车在幅值上继续拉开，同时更偏向平滑、规整的波形。
            med_max = max(chosen_amp_by_class[1])
            mask &= amp >= 1.20 * med_max

        if mask.sum() < 15:
            mask = (
                (energy >= pct(energy, cfg["energy_lo_q"]))
                & (rough <= pct(rough, 85))
            )
            if c == 0:
                med_amp_q25 = pct(amp_cell[1], 25)
                mask &= amp <= 0.92 * med_amp_q25
            elif c == 1 and chosen_amp_by_class[0]:
                small_max = max(chosen_amp_by_class[0])
                mask &= amp >= max(pct(amp, 35), 1.12 * small_max)
            elif c == 2 and chosen_amp_by_class[1]:
                med_max = max(chosen_amp_by_class[1])
                mask &= amp >= max(pct(amp, 45), 1.15 * med_max)

        if mask.sum() < 8:
            mask = np.ones_like(mask, dtype=bool)

        len_std = np.std(len_vec) + np.finfo(float).eps
        candidate_ids = np.flatnonzero(mask)

        if c == 0:
            # 小型车：优先选组内差异更大的三个样本，但幅值仍控制在中型车之下。
            candidate_ids = candidate_ids[
                (amp[candidate_ids] >= 120)
                & (amp[candidate_ids] <= 180)
                & (rough[candidate_ids] <= 0.040)
                & (curv[candidate_ids] <= 0.022)
                & (turns[candidate_ids] <= 12)
            ]
            if candidate_ids.size >= 3:
                trio, trio_score = choose_diverse_trio(
                    candidate_ids,
                    feat,
                    amp,
                    rough,
                    curv,
                    turns,
                    len_vec,
                    target_amp=145.0,
                    weights={"diversity": 2.1, "quality": 1.0, "amp": 0.9, "dur": 0.45, "turn": 0.35},
                )
                order = np.argsort(len_vec[trio])
                trio = trio[order]
                for j, best_idx in enumerate(trio):
                    rep_idx[c, j] = int(best_idx)
                    rep_len[c, j] = int(len_vec[best_idx])
                    rep_score[c, j] = float(trio_score)
                    rep_amp[c, j] = float(amp[best_idx])
                    chosen_amp_by_class[c].append(float(amp[best_idx]))
                continue

        if c == 2:
            # 大型车：优先选更平滑、转折更少、同时组内不要太像的三条波形。
            candidate_ids = candidate_ids[
                (amp[candidate_ids] >= 550)
                & (rough[candidate_ids] <= 0.022)
                & (curv[candidate_ids] <= 0.009)
                & (turns[candidate_ids] <= 2)
            ]
            if candidate_ids.size >= 3:
                trio, trio_score = choose_diverse_trio(
                    candidate_ids,
                    feat,
                    amp,
                    rough,
                    curv,
                    turns,
                    len_vec,
                    target_amp=720.0,
                    weights={"diversity": 2.0, "quality": 1.15, "amp": 0.35, "dur": 0.35, "turn": 0.15},
                )
                order = np.argsort(len_vec[trio])
                trio = trio[order]
                for j, best_idx in enumerate(trio):
                    rep_idx[c, j] = int(best_idx)
                    rep_len[c, j] = int(len_vec[best_idx])
                    rep_score[c, j] = float(trio_score)
                    rep_amp[c, j] = float(amp[best_idx])
                    chosen_amp_by_class[c].append(float(amp[best_idx]))
                continue

        used = np.zeros(feat.shape[0], dtype=bool)
        for j, q in enumerate(cfg["q_list"]):
            len_target = pct(len_vec, q)
            len_score = -np.abs(len_vec - len_target) / len_std
            total = base + cfg["len_w"] * scale01(len_score)
            total[~mask] = -np.inf
            total[used] = -np.inf

            best_idx = int(np.argmax(total))
            best_score = total[best_idx]
            if not np.isfinite(best_score):
                total = base + 0.10 * scale01(len_score)
                total[used] = -np.inf
                best_idx = int(np.argmax(total))
                best_score = total[best_idx]

            used[best_idx] = True
            rep_idx[c, j] = best_idx
            rep_len[c, j] = int(len_vec[best_idx])
            rep_score[c, j] = float(best_score)
            rep_amp[c, j] = float(amp[best_idx])
            chosen_amp_by_class[c].append(float(amp[best_idx]))

    return rep_idx, rep_len, rep_score


def draw_grouped_waveform(processed_data, rep_idx, rep_len, out_png: Path, export_dir: Path) -> List[Dict[str, float]]:
    fig, ax = plt.subplots(figsize=(13.2, 6.8), dpi=300)
    ax.grid(True, alpha=0.35)
    ax.set_xlabel("时间 / s", fontsize=17, labelpad=8)
    ax.set_ylabel("磁场扰动 / nT", fontsize=17, labelpad=10)
    ax.tick_params(axis="both", labelsize=15)

    waveform_examples: List[Dict[str, float]] = []
    t_cursor = 0.0
    gap_event = 0.18
    gap_group = 0.70
    evt_no = 0
    y_min_all, y_max_all = np.inf, -np.inf
    group_info = []

    for c in range(3):
        group_start = t_cursor
        group_y_min, group_y_max = np.inf, -np.inf
        class_cell = processed_data[0, c]

        for j in range(3):
            evt_no += 1
            idx = int(rep_idx[c, j])
            n = int(rep_len[c, j])

            _, db, mag, t = extract_event(class_cell[0, idx], n)
            use = crop_by_mag(mag, 0.10, 5)
            t_use = t[use] - t[use[0]]
            db_use = db[use, :]
            mag_use = mag[use]
            t_plot = t_cursor + t_use

            for k in range(3):
                ax.plot(
                    t_plot,
                    db_use[:, k],
                    color=AXIS_COLORS[k],
                    linewidth=2.0,
                    label=AXIS_LABELS[k] if evt_no == 1 else None,
                )

            export_data = np.column_stack([t_use, t_plot, db_use, mag_use])
            header = "t_local_s,t_plot_s,dBx_nT,dBy_nT,dBz_nT,b_nT"
            np.savetxt(
                export_dir / f"waveform_group_class{c+1}_evt{evt_no}_idx{idx+1}.csv",
                export_data,
                delimiter=",",
                header=header,
                comments="",
            )

            local_top = float(np.max(db_use))
            local_bot = float(np.min(db_use))
            local_x = float((t_plot[0] + t_plot[-1]) / 2)
            y_min_all = min(y_min_all, local_bot)
            y_max_all = max(y_max_all, local_top)
            group_y_min = min(group_y_min, local_bot)
            group_y_max = max(group_y_max, local_top)

            waveform_examples.append(
                {
                    "event_id": evt_no,
                    "class_id": c + 1,
                    "class_name": CLASS_NAMES[c],
                    "sample_index_1based": idx + 1,
                    "length": n,
                    "label_x": local_x,
                    "label_y": local_top,
                }
            )
            t_cursor = float(t_plot[-1]) + gap_event

        group_end = t_cursor - gap_event
        group_info.append((group_start, group_end, group_y_min, group_y_max, CLASS_NAMES[c]))
        t_cursor = group_end + gap_group

    y_range = y_max_all - y_min_all
    if y_range < 1e-9:
        y_range = max(1.0, abs(y_max_all))
    y_pad = 0.18 * y_range
    y_box_pad = 0.08 * y_range
    y_low = y_min_all - y_pad
    y_high = y_max_all + y_pad
    ax.set_xlim(0, t_cursor - gap_group + 0.25)
    ax.set_ylim(y_low, y_high)
    top_number_y = y_high - 0.055 * y_range

    for x0, x1, y0, y1, name in group_info:
        rect = Rectangle(
            (x0 - 0.08, y0 - y_box_pad),
            (x1 - x0) + 0.16,
            (y1 - y0) + 2 * y_box_pad,
            fill=False,
            linestyle=":",
            linewidth=1.45,
            edgecolor=(0.35, 0.35, 0.35),
        )
        ax.add_patch(rect)
        label_y = max(y_low + 0.045 * y_range, (y0 - y_box_pad) - 0.085 * y_range)
        ax.text((x0 + x1) / 2, label_y, name, ha="center", va="center", fontsize=17)

    for item in waveform_examples:
        ax.text(
            item["label_x"],
            top_number_y,
            str(item["event_id"]),
            ha="center",
            va="center",
            fontsize=16,
            fontweight="bold",
        )

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 0.92),
        frameon=False,
        fontsize=17,
        ncol=1,
        handlelength=1.0,
        handletextpad=0.6,
        borderaxespad=0.0,
    )

    fig.subplots_adjust(left=0.08, right=0.88, bottom=0.16, top=0.86)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return waveform_examples


def main() -> None:
    parser = argparse.ArgumentParser(description="重绘第三章三类车辆分组对比波形图")
    parser.add_argument("--mat", type=Path, default=None, help="processedVehicleData_3class_REAL (2).mat 路径")
    parser.add_argument("--out-dir", type=Path, default=None, help="输出目录，默认脚本同级 figures/")
    parser.add_argument("--copy-to-images", action="store_true", help="同时复制到论文 images/ 目录")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = find_repo_root(script_dir)
    mat_path = args.mat or find_default_mat_path(script_dir, repo_root)
    out_dir = args.out_dir or (script_dir / "figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = repo_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if not mat_path.exists():
        raise FileNotFoundError(f"未找到数据文件: {mat_path}")

    pick_font()
    processed_data, target_length = load_processed_data(mat_path)
    rep_idx, rep_len, rep_score = select_grouped_samples(processed_data, target_length)
    out_png = out_dir / "ch3_waveform_by_class.png"
    waveform_examples = draw_grouped_waveform(processed_data, rep_idx, rep_len, out_png, out_dir)

    np.savez(
        out_dir / "ch3_waveform_examples_grouped.npz",
        rep_idx=rep_idx,
        rep_len=rep_len,
        rep_score=rep_score,
    )

    if args.copy_to_images:
        (images_dir / "ch3_waveform_by_class.png").write_bytes(out_png.read_bytes())

    print("selected sample indices (1-based):")
    print(rep_idx + 1)
    print("selected lengths:")
    print(rep_len)
    print(f"saved figure: {out_png}")
    if args.copy_to_images:
        print(f"copied figure: {images_dir / 'ch3_waveform_by_class.png'}")
    print(f"saved grouped metadata: {out_dir / 'ch3_waveform_examples_grouped.npz'}")
    print(f"saved {len(waveform_examples)} grouped waveform csv files to: {out_dir}")


if __name__ == "__main__":
    main()
