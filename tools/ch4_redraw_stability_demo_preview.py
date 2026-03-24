from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "绘图" / "图片新修" / "第四章"
PNG_PATH = OUT_DIR / "ch4_stability_demo_preview.png"
SVG_PATH = OUT_DIR / "ch4_stability_demo_preview.svg"
META_PATH = OUT_DIR / "ch4_stability_demo_preview_meta.json"

SOURCE_CSV = ROOT / "绘图" / "第四章" / "0304" / "_work_ch4" / "data" / "zhenzhi" / "20240723_停车检测_sheet2_clean.csv"
GT_CSV = ROOT / "绘图" / "第四章" / "0304" / "_work_ch4" / "data" / "zhenzhi" / "parking_groundtruth_filled_cleaned.csv"
VERIFY_PY = ROOT / "绘图" / "第四章" / "0304" / "_work_ch4" / "ch4_onekey_pack" / "python" / "ch4_verify_python.py"


def configure_style() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = "Times New Roman"
    plt.rcParams["mathtext.it"] = "Times New Roman:italic"
    plt.rcParams["mathtext.bf"] = "Times New Roman:bold"
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"


def set_cn_font(text_obj, size: float) -> None:
    text_obj.set_fontfamily("SimSun")
    text_obj.set_fontsize(size)


def style_axis(ax: plt.Axes, tick_size: float = 12.0) -> None:
    ax.grid(True, linestyle="--", linewidth=0.75, color="#d7dde7", alpha=0.72)
    ax.tick_params(axis="both", labelsize=tick_size, pad=2.5)
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontfamily("Times New Roman")
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


def load_verify_module():
    spec = importlib.util.spec_from_file_location("ch4_verify_python", VERIFY_PY)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 ch4_verify_python.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def match_events_to_gt(events: list[dict], gt_idx: np.ndarray, tol_k: int) -> tuple[list[int], list[int]]:
    if len(events) == 0 or gt_idx.size == 0:
        return [], []
    kout = np.asarray([int(e["k_out"]) for e in events], dtype=int)
    arr_idx: list[int] = []
    leave_idx: list[int] = []
    for j in range(int(gt_idx.shape[0])):
        kin = int(gt_idx[j, 0])
        kout_gt = int(gt_idx[j, 1])

        d1 = int(np.min(np.abs(kout - kin)))
        i1 = int(np.argmin(np.abs(kout - kin)))
        if d1 <= tol_k:
            arr_idx.append(i1)

        d2 = int(np.min(np.abs(kout - kout_gt)))
        i2 = int(np.argmin(np.abs(kout - kout_gt)))
        if d2 <= tol_k:
            leave_idx.append(i2)

    return sorted(set(arr_idx)), sorted(set(leave_idx))


def compute_stability(B: np.ndarray, cfg: dict) -> dict[str, np.ndarray]:
    n = B.shape[0]
    L = int(cfg["st"]["L"])
    s = int(cfg["st"]["s"])
    fs = int(cfg["fs"])
    n0 = min(n, fs * 10)
    sig = np.std(B[:n0, :], axis=0, ddof=1)
    w = np.array([sig[1] * sig[2], sig[0] * sig[2], sig[0] * sig[1]], dtype=float)
    if float(w.sum()) == 0.0:
        w = np.array([1.0, 1.0, 1.0], dtype=float)
    w = w / w.sum()

    mean_vec = np.full((n, 3), np.nan)
    R = np.full(n, np.nan)
    M = np.full(n, np.nan)

    for k in range(L, n + 1):
        win = B[k - L : k, :]
        mean_vec[k - 1, :] = win.mean(axis=0)
        rvec = win.max(axis=0) - win.min(axis=0)
        R[k - 1] = float(w.dot(rvec))
        if (k - s) >= L:
            M[k - 1] = float(w.dot(np.abs(mean_vec[k - 1, :] - mean_vec[k - s - 1, :])))

    stable0 = (R <= cfg["st"]["R_th"]) & (M <= cfg["st"]["M_th"])
    stable_state = np.zeros(n, dtype=bool)
    cnt = 0
    Nst = int(cfg["st"]["N_stable"])
    for i in range(n):
        if stable0[i] and np.isfinite(R[i]) and np.isfinite(M[i]):
            cnt = min(cnt + 1, Nst)
        else:
            cnt = 0
        stable_state[i] = cnt == Nst

    return {
        "meanVec": mean_vec,
        "R": R,
        "M": M,
        "stable0": stable0,
        "stableState": stable_state,
        "w": w,
    }


def mask_segments(mask: np.ndarray, min_points: int = 1) -> list[tuple[int, int]]:
    vec = np.asarray(mask, dtype=bool)
    d = np.diff(np.r_[False, vec, False].astype(int))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0] - 1
    segs: list[tuple[int, int]] = []
    for s, e in zip(starts, ends):
        if e - s + 1 >= min_points:
            segs.append((int(s), int(e)))
    return segs


def merge_segments(
    segs: list[tuple[int, int]],
    x: np.ndarray,
    max_gap_sec: float,
    min_len_sec: float,
) -> list[tuple[int, int]]:
    if not segs:
        return []
    merged: list[list[int]] = [[segs[0][0], segs[0][1]]]
    for s, e in segs[1:]:
        prev = merged[-1]
        gap = float(x[s] - x[prev[1]])
        if gap <= max_gap_sec:
            prev[1] = e
        else:
            merged.append([s, e])
    out: list[tuple[int, int]] = []
    for s, e in merged:
        if float(x[e] - x[s]) >= min_len_sec:
            out.append((s, e))
    return out


def add_top_shading(ax: plt.Axes, x: np.ndarray, stable0_mask: np.ndarray, warmup_sec: float) -> list[tuple[int, int]]:
    shade_color = "#e7eaef"
    if warmup_sec > 0:
        ax.axvspan(float(x[0]), min(float(x[-1]), warmup_sec), color=shade_color, alpha=0.55, zorder=0)
    merged = merge_segments(mask_segments(stable0_mask, min_points=6), x, max_gap_sec=1.20, min_len_sec=0.80)
    for s, e in merged:
        x0 = max(float(x[0]), float(x[s]) - 0.35)
        x1 = min(float(x[-1]), float(x[e]) + 0.55)
        ax.axvspan(x0, x1, color=shade_color, alpha=0.55, zorder=0)
    return merged


def choose_event_and_window(
    t: np.ndarray,
    B: np.ndarray,
    st: dict[str, np.ndarray],
    verify_mod,
    cfg: dict,
    gt_idx: np.ndarray,
) -> dict[str, float]:
    b_xy, b_z = verify_mod.design_fir(cfg)
    pr = verify_mod.pr_vehicle(B, cfg, b_xy, b_z)
    events = verify_mod.detect_events(pr, cfg)
    if not events:
        raise RuntimeError("原始 sheet2_clean 数据中未检测到停车事件")

    arr_idx, leave_idx = match_events_to_gt(events, gt_idx, int(round(2.0 * cfg["fs"])))
    if not arr_idx:
        raise RuntimeError("未能按 MATLAB 逻辑匹配到 A 类停车到达事件")

    park_m = int(arr_idx[0])
    ev = events[park_m]
    k_out = int(ev["k_out"])
    found = np.where(st["stableState"][k_out - 1 :])[0]
    if found.size == 0:
        raise RuntimeError("所选事件后未找到连续门控稳定窗")
    k_st = k_out + int(found[0])

    crop_len = 12.0
    crop_start = max(0.0, float(t[k_out - 1]) - 5.55)

    return {
        "event_index": park_m + 1,
        "leave_match_index": int(leave_idx[0] + 1) if leave_idx else -1,
        "k_in": int(ev["k_in"]),
        "k_out": k_out,
        "k_st": k_st,
        "t_in": float(t[int(ev["k_in"]) - 1]),
        "t_out": float(t[k_out - 1]),
        "t_st": float(t[k_st - 1]),
        "crop_start": crop_start,
        "crop_end": crop_start + crop_len,
    }


def main() -> None:
    configure_style()
    verify_mod = load_verify_module()
    cfg = verify_mod.cfg_global_v2()

    df = pd.read_csv(SOURCE_CSV)
    gt = pd.read_csv(GT_CSV)
    gt_f = gt[gt["file"].astype(str) == SOURCE_CSV.name].copy()
    if gt_f.empty:
        raise RuntimeError("GT 中未找到 sheet2_clean 对应的 A 类标注")

    t_full = df["t"].to_numpy(float) - float(df["t"].iloc[0])
    B_full = df[["x", "y", "z"]].to_numpy(float)
    k0 = int(df["k"].iloc[0])
    gt_idx = np.column_stack(
        [
            gt_f["k_star_in"].to_numpy(dtype=float) - k0 + 1,
            gt_f["k_star_out"].to_numpy(dtype=float) - k0 + 1,
        ]
    ).astype(int)

    st_full = compute_stability(B_full, cfg)
    selected = choose_event_and_window(t_full, B_full, st_full, verify_mod, cfg, gt_idx)

    crop_mask = (t_full >= selected["crop_start"]) & (t_full <= selected["crop_end"])
    x = t_full[crop_mask] - selected["crop_start"]
    Bz = B_full[crop_mask, 2]
    R = np.where(np.isfinite(st_full["R"][crop_mask]), st_full["R"][crop_mask], 0.0)
    M = np.where(np.isfinite(st_full["M"][crop_mask]), st_full["M"][crop_mask], 0.0)
    stable0 = st_full["stable0"][crop_mask].astype(float)
    stable_state = st_full["stableState"][crop_mask].astype(float)
    stable0_mask = st_full["stable0"][crop_mask]

    t_out_rel = selected["t_out"] - selected["crop_start"]
    t_st_rel = selected["t_st"] - selected["crop_start"]
    warmup_sec = max(cfg["st"]["L"], cfg["st"]["s"]) / cfg["fs"]

    matlab_blue = (0.0, 0.447, 0.741)
    matlab_orange = (0.85, 0.325, 0.098)
    thr_color = "#7f7f7f"

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(9.2, 6.6),
        dpi=220,
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.0, 1.0, 0.95], "hspace": 0.08},
    )
    ax1, ax2, ax3, ax4 = axes

    shade_segments = add_top_shading(ax1, x, stable0_mask, warmup_sec)
    ax2.axvspan(float(x[0]), min(float(x[-1]), warmup_sec), color="#e7eaef", alpha=0.55, zorder=0)
    ax3.axvspan(float(x[0]), min(float(x[-1]), warmup_sec), color="#e7eaef", alpha=0.55, zorder=0)

    ax1.plot(x, Bz, color=matlab_blue, linewidth=1.75)
    ax1.axvline(t_out_rel, color=thr_color, linewidth=1.0, linestyle=(0, (4, 4)))
    ax1.axvline(t_st_rel, color=thr_color, linewidth=1.0)
    title = ax1.set_title("稳定窗双判据示意（通道=Bz）", pad=4)
    set_cn_font(title, 12.4)
    ylabel1 = ax1.set_ylabel(r"$\bar{B}_z$ / nT", fontsize=13.0)
    ylabel1.set_fontfamily("Times New Roman")
    ax1.text(t_out_rel - 0.12, float(np.nanpercentile(Bz, 33)), r"$t_{out}$", ha="right", va="center", fontsize=12.0)
    ax1.text(t_st_rel + 0.10, float(np.nanpercentile(Bz, 33)), r"$t_{st}$", ha="left", va="center", fontsize=12.0)

    ax2.plot(x, R, color=matlab_blue, linewidth=1.45)
    ax2.axhline(cfg["st"]["R_th"], color=thr_color, linewidth=0.95, linestyle=(0, (4, 4)))
    ax2.text(float(x[-1]) - 0.06, float(cfg["st"]["R_th"]) + 1.0, r"$R_{th}$", ha="right", va="bottom", fontsize=12.0)
    ylabel2 = ax2.set_ylabel(r"$R(k)$", fontsize=13.0)
    ylabel2.set_fontfamily("Times New Roman")

    ax3.plot(x, M, color=matlab_blue, linewidth=1.45)
    ax3.axhline(cfg["st"]["M_th"], color=thr_color, linewidth=0.95, linestyle=(0, (4, 4)))
    ax3.text(float(x[-1]) - 0.06, float(cfg["st"]["M_th"]) + 0.8, r"$M_{th}$", ha="right", va="bottom", fontsize=12.0)
    ylabel3 = ax3.set_ylabel(r"$M(k)$", fontsize=13.0)
    ylabel3.set_fontfamily("Times New Roman")

    ax4.step(x, stable0, where="post", color=matlab_blue, linewidth=1.65, label="双判据成立")
    ax4.step(x, stable_state, where="post", color=matlab_orange, linewidth=1.45, label="连续门控后")
    ax4.set_ylim(-0.05, 1.08)
    ax4.set_yticks([0.0, 0.5, 1.0])
    ylabel4 = ax4.set_ylabel("stable", fontsize=13.0)
    ylabel4.set_fontfamily("Times New Roman")
    xlabel = ax4.set_xlabel("时间 / s", fontsize=13.2)
    set_cn_font(xlabel, 13.2)
    legend = ax4.legend(
        loc="center right",
        frameon=True,
        fontsize=11.0,
        borderpad=0.32,
        labelspacing=0.30,
        handlelength=1.9,
    )
    legend.get_frame().set_alpha(0.94)
    legend.get_frame().set_edgecolor("#bfc7d2")
    for text in legend.get_texts():
        set_cn_font(text, 11.0)

    for ax in axes:
        ax.set_xlim(0.0, 12.0)
        style_axis(ax)

    ax1.set_ylim(float(np.floor((np.nanmin(Bz) - 8) / 10) * 10), float(np.ceil((np.nanmax(Bz) + 8) / 10) * 10))
    ax2.set_ylim(-1.0, max(85.0, float(np.nanmax(R) * 1.05)))
    ax3.set_ylim(-1.0, max(80.0, float(np.nanmax(M) * 1.05)))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_PATH, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(SVG_PATH, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    stable0_segments = merge_segments(mask_segments(stable0.astype(bool), min_points=1), x, max_gap_sec=0.20, min_len_sec=0.0)
    stable_segments = merge_segments(mask_segments(stable_state.astype(bool), min_points=1), x, max_gap_sec=0.20, min_len_sec=0.0)

    meta = {
        "source_csv": str(SOURCE_CSV),
        "gt_csv": str(GT_CSV),
        "config": "cfg_global_v2",
        "selected_event_index": int(selected["event_index"]),
        "leave_match_index": int(selected["leave_match_index"]),
        "event_k_in": int(selected["k_in"]),
        "event_k_out": int(selected["k_out"]),
        "event_k_st": int(selected["k_st"]),
        "event_t_in_rel_s": round(float(selected["t_in"]), 4),
        "event_t_out_rel_s": round(float(selected["t_out"]), 4),
        "event_t_st_rel_s": round(float(selected["t_st"]), 4),
        "crop_start_s": round(float(selected["crop_start"]), 4),
        "crop_end_s": round(float(selected["crop_end"]), 4),
        "display_t_out_s": round(float(t_out_rel), 4),
        "display_t_st_s": round(float(t_st_rel), 4),
        "display_segments": {
            "shade_top": [[round(float(x[s]), 4), round(float(x[e]), 4)] for s, e in shade_segments],
            "stable0": [[round(float(x[s]), 4), round(float(x[e]), 4)] for s, e in stable0_segments],
            "stableState": [[round(float(x[s]), 4), round(float(x[e]), 4)] for s, e in stable_segments],
        },
        "cfg_st": {
            "L": int(cfg["st"]["L"]),
            "s": int(cfg["st"]["s"]),
            "N_stable": int(cfg["st"]["N_stable"]),
            "R_th": float(cfg["st"]["R_th"]),
            "M_th": float(cfg["st"]["M_th"]),
        },
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
