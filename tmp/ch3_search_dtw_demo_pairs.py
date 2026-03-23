from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "绘图" / "第三章" / "20260304" / "redraw_ch3_motivation_figures.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ch3_motivation", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main():
    M = load_module()
    raw_list, y, tlen = M.load_raw_y_tlen(M.DATA_MAT)
    fs = 50.0

    cls = 1
    idx_all = np.where(y == cls)[0].tolist()
    print(f"class={cls}, total={len(idx_all)}")

    coarse = []
    for i in range(len(idx_all)):
        idx_a = int(idx_all[i])
        len_a = int(tlen[idx_a])
        if len_a < 85 or len_a > 140:
            continue
        _, d_b_a, mag_a, _ = M.extract_event(raw_list[idx_a], len_a, fs)
        z_a = d_b_a[:, 2]
        peak_a = float(np.max(np.abs(z_a)) + 1e-6)
        energy_a = float(np.sum(z_a**2) + 1e-6)

        for j in range(i + 1, len(idx_all)):
            idx_b = int(idx_all[j])
            len_b = int(tlen[idx_b])
            if len_b <= len_a:
                continue
            if len_b < 100 or len_b > 190:
                continue

            ratio = len_b / max(1.0, len_a)
            if ratio < 1.22 or ratio > 1.65:
                continue

            _, d_b_b, mag_b, _ = M.extract_event(raw_list[idx_b], len_b, fs)
            z_b = d_b_b[:, 2]
            peak_b = float(np.max(np.abs(z_b)) + 1e-6)
            peak_ratio = peak_a / peak_b
            if peak_ratio < 0.78 or peak_ratio > 1.28:
                continue

            energy_b = float(np.sum(z_b**2) + 1e-6)
            energy_ratio = energy_a / energy_b
            if energy_ratio < 0.55 or energy_ratio > 1.80:
                continue

            common = max(len_a, len_b)
            z_a_r = M.resample_linear(z_a, common)
            z_b_r = M.resample_linear(z_b, common)
            pre_corr = M.safe_corr(z_a_r, z_b_r)
            if pre_corr < 0.28 or pre_corr > 0.82:
                continue

            mag_a_r = M.resample_linear(mag_a, common)
            mag_b_r = M.resample_linear(mag_b, common)
            mag_corr = M.safe_corr(mag_a_r, mag_b_r)
            if mag_corr < 0.55:
                continue

            coarse_score = (
                1.15 * mag_corr
                + 0.45 * pre_corr
                - 0.30 * abs(np.log(ratio / 1.38))
                - 0.22 * abs(np.log(peak_ratio))
            )
            coarse.append((coarse_score, idx_a, idx_b, len_a, len_b, ratio, pre_corr, mag_corr))

    coarse.sort(reverse=True)
    shortlist = coarse[:40]
    print(f"coarse shortlist={len(shortlist)}")

    final_rows = []
    for coarse_score, idx_a, idx_b, len_a, len_b, ratio, pre_corr, mag_corr in shortlist:
        metrics = M.alignment_demo_metrics(raw_list, tlen, idx_a, idx_b, fs)
        post_corr = float(metrics["post_corr"])
        peak_ratio = float(metrics["peak_ratio"])
        if post_corr < 0.965:
            continue
        score = (
            1.55 * post_corr
            - 0.55 * abs(pre_corr - 0.58)
            + 0.18 * mag_corr
            - 0.18 * abs(np.log(ratio / 1.38))
            - 0.15 * abs(np.log(peak_ratio))
        )
        final_rows.append(
            (
                score,
                idx_a,
                idx_b,
                len_a,
                len_b,
                ratio,
                pre_corr,
                post_corr,
                mag_corr,
                peak_ratio,
            )
        )

    final_rows.sort(reverse=True)
    for row in final_rows[:15]:
        print(
            "score={:.4f} pair=({}, {}) len=({}, {}) ratio={:.3f} pre={:.4f} post={:.4f} "
            "mag={:.4f} peak_ratio={:.3f}".format(*row)
        )

    if not final_rows:
        raise SystemExit("no suitable pair found")

    out_dir = ROOT / "tmp" / "ch3_dtw_pair_candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    for rank, row in enumerate(final_rows[:6], start=1):
        _, idx_a, idx_b, len_a, len_b, ratio, pre_corr, post_corr, mag_corr, peak_ratio = row
        raw_a = raw_list[idx_a]
        raw_b = raw_list[idx_b]
        tag = f"cand{rank}_{idx_a}_{idx_b}"
        M.plot_dtw_alignment_matlab_style(raw_a, len_a, raw_b, len_b, fs, tag=tag)
        src = ROOT / "images" / f"fig_motivation_dtw_align_z_{tag}.png"
        dst = out_dir / f"{rank:02d}_{idx_a}_{idx_b}_r{ratio:.3f}_pre{pre_corr:.3f}_post{post_corr:.3f}.png"
        src.replace(dst)
        print(f"saved {dst.name}")


if __name__ == "__main__":
    main()
