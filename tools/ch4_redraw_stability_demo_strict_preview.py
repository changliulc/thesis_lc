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
PNG_PATH = OUT_DIR / "ch4_stability_demo_strict_preview.png"
SVG_PATH = OUT_DIR / "ch4_stability_demo_strict_preview.svg"
META_PATH = OUT_DIR / "ch4_stability_demo_strict_preview_meta.json"


def find_one(pattern: str, must_contain: str | None = None) -> Path:
    hits = sorted(ROOT.rglob(pattern))
    if must_contain is not None:
        hits = [p for p in hits if must_contain.replace("\\", "/") in str(p).replace("\\", "/")]
    if not hits:
        raise FileNotFoundError(f"Could not find {pattern!r}")
    return hits[0]


VERIFY_PY = find_one("ch4_verify_python.py", "ch4_onekey_pack/python")
FIG_A_CSV = find_one("fig_a_win.csv", "ch4_onekey_pack/run")
SOURCE_CSV = find_one("20240723_停车检测_sheet2_clean.csv", "_work_ch4/data/zhenzhi")


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


def style_axis(ax: plt.Axes, tick_size: float = 11.5) -> None:
    ax.grid(True, linestyle="--", linewidth=0.75, color="#d7dde7", alpha=0.72)
    ax.tick_params(axis="both", labelsize=tick_size, pad=2.5)
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontfamily("Times New Roman")
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


def set_cn_font(text_obj, size: float) -> None:
    text_obj.set_fontfamily("SimSun")
    text_obj.set_fontsize(size)


def load_verify_module():
    spec = importlib.util.spec_from_file_location("ch4_verify_python", VERIFY_PY)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load ch4_verify_python.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def compute_stability_with_fixed_weights(B: np.ndarray, cfg: dict, w: np.ndarray) -> dict[str, np.ndarray]:
    n = B.shape[0]
    L = int(cfg["st"]["L"])
    s = int(cfg["st"]["s"])

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


def choose_arrival_event(
    t: np.ndarray,
    B: np.ndarray,
    events: list[dict],
    st: dict[str, np.ndarray],
) -> dict[str, float]:
    rows: list[dict[str, float | int]] = []
    for idx, ev in enumerate(events, 1):
        kout = int(ev["k_out"])
        kin = int(ev["k_in"])
        found = np.where(st["stableState"][kout - 1 :])[0]
        if found.size == 0:
            continue
        kst = kout + int(found[0])

        crop_start = max(float(t[0]), float(t[kout - 1]) - 5.55)
        crop_end = min(float(t[-1]), crop_start + 12.0)
        mask = (t >= crop_start) & (t <= crop_end)
        x = t[mask] - crop_start
        bz = B[mask, 2]

        pre = bz[x < 4.5]
        post = bz[x > 7.5]
        tail = bz[x > 10.0]
        if pre.size == 0 or post.size == 0 or tail.size == 0:
            continue

        step = float(np.mean(post) - np.mean(pre))
        flat = float(np.std(tail))

        rows.append(
            {
                "event_index": idx,
                "kin": kin,
                "kout": kout,
                "kst": kst,
                "step": step,
                "flat": flat,
            }
        )

    pos = [r for r in rows if float(r["step"]) > 20.0]
    if not pos:
        raise RuntimeError("No arrival-like event found in fig_a_win.csv")
    pos.sort(key=lambda r: (float(r["flat"]), -float(r["step"]), int(r["event_index"])))
    best = pos[0]
    return {
        "event_index": int(best["event_index"]),
        "k_in": int(best["kin"]),
        "k_out": int(best["kout"]),
        "k_st": int(best["kst"]),
    }


def add_top_shading(ax: plt.Axes, x: np.ndarray, stable0_mask: np.ndarray, warmup_sec: float) -> list[tuple[float, float]]:
    shade_color = "#e7eaef"
    if warmup_sec > 0:
        ax.axvspan(float(x[0]), min(float(x[-1]), warmup_sec), color=shade_color, alpha=0.55, zorder=0)

    merged = merge_segments(mask_segments(stable0_mask, min_points=6), x, max_gap_sec=1.20, min_len_sec=0.40)
    out: list[tuple[float, float]] = []
    for s, e in merged:
        left = max(float(x[0]), float(x[s]) + 0.10)
        right_pad = 1.30 if float(x[s]) < 5.55 else 1.85
        right = min(float(x[-1]), float(x[e]) + right_pad)
        ax.axvspan(left, right, color=shade_color, alpha=0.55, zorder=0)
        out.append((left, right))
    return out


def pick_display_t_st(x: np.ndarray, stable_state_mask: np.ndarray, t_out_rel: float, raw_t_st: float) -> float:
    segs = mask_segments(stable_state_mask, min_points=1)
    after = [(s, e) for s, e in segs if float(x[s]) >= raw_t_st - 1e-9]
    sustained = [(s, e) for s, e in after if float(x[e] - x[s]) >= 0.80]
    if sustained:
        return float(x[sustained[0][0]])
    return raw_t_st


def main() -> None:
    configure_style()
    verify_mod = load_verify_module()
    cfg = verify_mod.cfg_global_v2()
    cfg["pk"]["D_th"] = 36.0
    cfg["pk"]["dist_th"] = 4.0
    cfg["ref"]["D_upd"] = 30.0

    full_df = pd.read_csv(SOURCE_CSV)
    win_df = pd.read_csv(FIG_A_CSV)

    t_full = full_df["t"].to_numpy(float)
    B_full = full_df[["x", "y", "z"]].to_numpy(float)
    t_win = win_df["t"].to_numpy(float)
    B_win = win_df[["x", "y", "z"]].to_numpy(float)

    n0 = min(len(B_full), int(cfg["fs"] * 10))
    sig = np.std(B_full[:n0, :], axis=0, ddof=1)
    w = np.array([sig[1] * sig[2], sig[0] * sig[2], sig[0] * sig[1]], dtype=float)
    if float(w.sum()) == 0.0:
        w = np.array([1.0, 1.0, 1.0], dtype=float)
    w = w / w.sum()

    st = compute_stability_with_fixed_weights(B_win, cfg, w)
    b_xy, b_z = verify_mod.design_fir(cfg)
    pr = verify_mod.pr_vehicle(B_win, cfg, b_xy, b_z)
    events = verify_mod.detect_events(pr, cfg)
    selected = choose_arrival_event(t_win, B_win, events, st)

    k_in = selected["k_in"]
    k_out = selected["k_out"]
    k_st = selected["k_st"]

    crop_start = max(float(t_win[0]), float(t_win[k_out - 1]) - 5.55)
    crop_end = min(float(t_win[-1]), crop_start + 12.0)
    mask = (t_win >= crop_start) & (t_win <= crop_end)

    x = t_win[mask] - crop_start
    Bz = B_win[mask, 2]
    R = np.where(np.isfinite(st["R"][mask]), st["R"][mask], 0.0)
    M = np.where(np.isfinite(st["M"][mask]), st["M"][mask], 0.0)
    stable0 = st["stable0"][mask]
    stable_state = st["stableState"][mask]

    t_out_rel = float(t_win[k_out - 1] - crop_start)
    raw_t_st = float(t_win[k_st - 1] - crop_start)
    display_t_st = pick_display_t_st(x, stable_state, t_out_rel, raw_t_st)
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

    shade_top = add_top_shading(ax1, x, stable0, warmup_sec)
    ax2.axvspan(float(x[0]), min(float(x[-1]), warmup_sec), color="#e7eaef", alpha=0.55, zorder=0)
    ax3.axvspan(float(x[0]), min(float(x[-1]), warmup_sec), color="#e7eaef", alpha=0.55, zorder=0)

    ax1.plot(x, Bz, color=matlab_blue, linewidth=1.75)
    ax1.axvline(t_out_rel, color=thr_color, linewidth=1.0, linestyle=(0, (4, 4)))
    ax1.axvline(display_t_st, color=thr_color, linewidth=1.0)
    title = ax1.set_title("稳定窗双判据示意（通道=Bz）", pad=4)
    set_cn_font(title, 12.4)
    ylabel1 = ax1.set_ylabel(r"$\bar{B}_z$ / nT", fontsize=13.0)
    ylabel1.set_fontfamily("Times New Roman")
    ax1.text(t_out_rel - 0.12, float(np.nanpercentile(Bz, 33)), r"$t_{out}$", ha="right", va="center", fontsize=12.0)
    ax1.text(display_t_st + 0.10, float(np.nanpercentile(Bz, 33)), r"$t_{st}$", ha="left", va="center", fontsize=12.0)

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

    ax4.step(x, stable0.astype(float), where="post", color=matlab_blue, linewidth=1.65, label="双判据成立")
    ax4.step(x, stable_state.astype(float), where="post", color=matlab_orange, linewidth=1.45, label="连续门控后")
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
    ax2.set_ylim(-1.0, max(100.0, float(np.nanmax(R) * 1.05)))
    ax3.set_ylim(-1.0, max(60.0, float(np.nanmax(M) * 1.05)))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_PATH, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(SVG_PATH, facecolor="white", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    meta = {
        "source_window_csv": str(FIG_A_CSV),
        "source_full_csv": str(SOURCE_CSV),
        "config": "cfg_global_v2 + thesis global overrides",
        "weight_sigma_source": "full source first 10 seconds",
        "weights": [float(v) for v in w],
        "selected_event_index_in_window": int(selected["event_index"]),
        "event_k_in": int(k_in),
        "event_k_out": int(k_out),
        "event_k_st_raw": int(k_st),
        "display_t_out_s": round(t_out_rel, 4),
        "display_t_st_raw_s": round(raw_t_st, 4),
        "display_t_st_s": round(display_t_st, 4),
        "crop_start_abs_s": round(crop_start, 4),
        "crop_end_abs_s": round(crop_end, 4),
        "R_max": round(float(np.nanmax(R)), 4),
        "M_max": round(float(np.nanmax(M)), 4),
        "shade_top_segments_s": [[round(a, 4), round(b, 4)] for a, b in shade_top],
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
