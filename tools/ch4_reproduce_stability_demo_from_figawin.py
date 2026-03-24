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
DATA_ROOT = Path(r"D:\xidian_Master\研究生论文\毕业论文\实验数据\第四章\ch4_matlab_pybest_global_oneclick\data")
ZHENZHI_DIR = DATA_ROOT / "zhenzhi"
GT_CSV = ZHENZHI_DIR / "parking_groundtruth_filled_cleaned.csv"
WIN_CSV = ROOT / "绘图" / "第四章" / "0304" / "_work_ch4" / "ch4_onekey_pack" / "run" / "fig_a_win.csv"
VERIFY_PY = ROOT / "绘图" / "第四章" / "0304" / "_work_ch4" / "ch4_onekey_pack" / "python" / "ch4_verify_python.py"

OUT_DIR = ROOT / "绘图" / "图片新修" / "第四章"
PNG_OUT = OUT_DIR / "ch4_stability_demo_from_figawin_preview.png"
SVG_OUT = OUT_DIR / "ch4_stability_demo_from_figawin_preview.svg"
META_OUT = OUT_DIR / "ch4_stability_demo_from_figawin_preview_meta.json"


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


def style_axis(ax: plt.Axes, tick_size: float = 11.0) -> None:
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


def find_sheet2_clean_csv() -> Path:
    cands = sorted(ZHENZHI_DIR.glob("*sheet2_clean.csv"))
    if not cands:
        raise RuntimeError(f"在 {ZHENZHI_DIR} 下没有找到 *sheet2_clean.csv")
    return cands[0]


def compute_stability_full(B: np.ndarray, cfg: dict) -> dict[str, np.ndarray]:
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


def choose_event_in_window(
    t_full: np.ndarray,
    events: list[dict],
    stable_state: np.ndarray,
    gt_idx: np.ndarray,
    fs: float,
    win_t0: float,
    win_t1: float,
    t_seek_sec: float,
) -> dict[str, float]:
    arr_idx, _ = match_events_to_gt(events, gt_idx, int(round(2.0 * fs)))
    if not arr_idx:
        raise RuntimeError("没有匹配到 A 类停车到达事件")

    candidates: list[tuple[float, int, int, int]] = []
    for idx in arr_idx:
        ev = events[idx]
        k_out = int(ev["k_out"])
        t_out = float(t_full[k_out - 1])
        if not (win_t0 - 0.5 <= t_out <= win_t1 + 0.5):
            continue
        k_seek_end = min(len(t_full), k_out + int(round(t_seek_sec * fs)))
        found = np.where(stable_state[k_out - 1 : k_seek_end])[0]
        if found.size == 0:
            continue
        k_st = k_out + int(found[0])
        center_cost = abs(t_out - 0.5 * (win_t0 + win_t1))
        candidates.append((center_cost, idx, k_out, k_st))

    if not candidates:
        raise RuntimeError("窗口范围内没有找到对应的停车事件")

    _, idx, k_out, k_st = sorted(candidates, key=lambda x: x[0])[0]
    ev = events[idx]
    return {
        "event_index": idx + 1,
        "k_in": int(ev["k_in"]),
        "k_out": k_out,
        "k_st": k_st,
        "t_in": float(t_full[int(ev["k_in"]) - 1]),
        "t_out": float(t_full[k_out - 1]),
        "t_st": float(t_full[k_st - 1]),
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


def add_shading(ax: plt.Axes, x: np.ndarray, mask: np.ndarray, color: str = "#e7eaef") -> list[tuple[int, int]]:
    segs = mask_segments(mask, min_points=6)
    for s, e in segs:
        ax.axvspan(float(x[s]), float(x[e]), color=color, alpha=0.55, zorder=0)
    return segs


def main() -> None:
    configure_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    verify_mod = load_verify_module()
    cfg = verify_mod.cfg_global_v2()
    b_xy, b_z = verify_mod.design_fir(cfg)

    source_csv = find_sheet2_clean_csv()

    df_win = pd.read_csv(WIN_CSV)
    win_t0 = float(df_win["t"].iloc[0])
    win_t1 = float(df_win["t"].iloc[-1])

    df_full = pd.read_csv(source_csv)
    gt = pd.read_csv(GT_CSV)
    gt["file"] = gt["file"].astype(str)
    gt["dataset"] = gt["dataset"].astype(str)
    gt["scenario_group"] = gt["scenario_group"].astype(str)
    gt_f = gt[gt["file"] == source_csv.name].copy()
    if gt_f.empty:
        gt_f = gt[
            gt["dataset"].str.contains("sheet2", case=False, na=False)
            & (gt["scenario_group"].str.upper() == "A")
            & (gt["t_star_in_sec"] >= win_t0 - 5.0)
            & (gt["t_star_in_sec"] <= win_t1 + 5.0)
        ].copy()
    if gt_f.empty:
        raise RuntimeError("GT 中仍未匹配到 sheet2 的 A 类停车事件")

    t_full = df_full["t"].to_numpy(float)
    B_full = df_full[["x", "y", "z"]].to_numpy(float)
    k_full = df_full["k"].to_numpy(int)
    k0 = int(k_full[0])

    gt_idx = np.column_stack(
        [
            gt_f["k_star_in"].to_numpy(dtype=float) - k0 + 1,
            gt_f["k_star_out"].to_numpy(dtype=float) - k0 + 1,
        ]
    ).astype(int)

    st_full = compute_stability_full(B_full, cfg)
    _, _, events = verify_mod.run_parking(B_full, k0, cfg, b_xy, b_z)
    selected = choose_event_in_window(
        t_full,
        events,
        st_full["stableState"],
        gt_idx,
        float(cfg["fs"]),
        win_t0,
        win_t1,
        float(cfg["pk"]["T_seek_sec"]),
    )

    mask = (t_full >= win_t0) & (t_full <= win_t1)
    x = t_full[mask] - win_t0
    Bz = B_full[mask, 2]
    R = np.where(np.isfinite(st_full["R"][mask]), st_full["R"][mask], 0.0)
    M = np.where(np.isfinite(st_full["M"][mask]), st_full["M"][mask], 0.0)
    stable0 = st_full["stable0"][mask].astype(float)
    stable_state = st_full["stableState"][mask].astype(float)

    t_out_rel = selected["t_out"] - win_t0
    t_st_rel = selected["t_st"] - win_t0
    matlab_blue = (0.0, 0.447, 0.741)
    matlab_orange = (0.85, 0.325, 0.098)
    thr_color = "#7f7f7f"

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(9.2, 6.9),
        sharex=True,
        gridspec_kw={"hspace": 0.09},
    )

    for ax in axes[:3]:
        add_shading(ax, x, st_full["stableState"][mask])

    ax1, ax2, ax3, ax4 = axes

    ax1.plot(x, Bz, color=matlab_blue, linewidth=1.55)
    ax1.axvline(t_out_rel, color=thr_color, linewidth=1.0, linestyle=(0, (4, 4)))
    ax1.axvline(t_st_rel, color=thr_color, linewidth=1.0)
    title = ax1.set_title("稳定窗双判据示意（通道=Bz）", pad=4)
    set_cn_font(title, 13.0)
    ax1.text(t_out_rel - 0.10, float(np.nanpercentile(Bz, 34)), r"$t_{out}$", ha="right", va="center", fontsize=12.0)
    ax1.text(t_st_rel + 0.08, float(np.nanpercentile(Bz, 34)), r"$t_{st}$", ha="left", va="center", fontsize=12.0)
    ylab = ax1.set_ylabel(r"$B_z$ / nT")
    ylab.set_fontsize(13.0)

    ax2.plot(x, R, color=matlab_blue, linewidth=1.55)
    ax2.axhline(float(cfg["st"]["R_th"]), color=thr_color, linewidth=0.95, linestyle=(0, (4, 4)))
    ax2.text(float(x[-1]) - 0.06, float(cfg["st"]["R_th"]) + 1.0, r"$R_{th}$", ha="right", va="bottom", fontsize=12.0)
    ylab = ax2.set_ylabel(r"$R(k)$")
    ylab.set_fontsize(13.0)

    ax3.plot(x, M, color=matlab_blue, linewidth=1.55)
    ax3.axhline(float(cfg["st"]["M_th"]), color=thr_color, linewidth=0.95, linestyle=(0, (4, 4)))
    ax3.text(float(x[-1]) - 0.06, float(cfg["st"]["M_th"]) + 0.8, r"$M_{th}$", ha="right", va="bottom", fontsize=12.0)
    ylab = ax3.set_ylabel(r"$M(k)$")
    ylab.set_fontsize(13.0)

    ax4.step(x, stable0, where="post", color=matlab_blue, linewidth=1.65, label="双判据成立")
    ax4.step(x, stable_state, where="post", color=matlab_orange, linewidth=1.45, label="连续门控后")
    ax4.set_ylim(-0.05, 1.05)
    ax4.set_yticks([0.0, 0.5, 1.0])
    ylab = ax4.set_ylabel("stable")
    ylab.set_fontsize(13.0)
    xlab = ax4.set_xlabel("时间 / s")
    set_cn_font(xlab, 13.0)
    leg = ax4.legend(loc="center right", frameon=True, fontsize=11.5)
    for txt in leg.get_texts():
        txt.set_fontfamily("SimSun")

    for ax in axes:
        style_axis(ax)
        ax.set_xlim(float(x[0]), float(x[-1]))

    fig.subplots_adjust(left=0.12, right=0.86, top=0.93, bottom=0.10)
    fig.savefig(PNG_OUT, dpi=220, bbox_inches="tight")
    fig.savefig(SVG_OUT, bbox_inches="tight")
    plt.close(fig)

    META_OUT.write_text(
        json.dumps(
            {
                "source_csv": str(source_csv),
                "gt_csv": str(GT_CSV),
                "window_csv": str(WIN_CSV),
                "event_index": selected["event_index"],
                "window_t0_s": round(win_t0, 4),
                "window_t1_s": round(win_t1, 4),
                "t_out_abs_s": round(selected["t_out"], 4),
                "t_st_abs_s": round(selected["t_st"], 4),
                "t_out_rel_s": round(t_out_rel, 4),
                "t_st_rel_s": round(t_st_rel, 4),
                "R_th": float(cfg["st"]["R_th"]),
                "M_th": float(cfg["st"]["M_th"]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
