#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate the single Chapter-4 parameter-scan figure recommended in the thesis
revision notes, by reusing the logic in your provided
`ch4_oneclick_make_tables_figs_minimal_fixed.py`.

Default target:
  退化分支搜索窗 T_seek_sec

Figure design:
  - left axis: ALL F1 and C-group F1
  - right axis: C-group median confirmation delay tau_in

Why this script exists:
  - it does not replace your Chapter-4 one-click evaluator;
  - it only extracts the minimal parameter-scan evidence needed for the thesis.

Requirements:
  1) your data zip (the same `data.zip` you uploaded)
  2) either:
       - `--pack_zip ch4_onekey_pack_nodata.zip`, or
       - `--ch4_py <path/to/ch4_verify_python.py>`
  3) your base script `ch4_oneclick_make_tables_figs_minimal_fixed.py`

Usage example:
  python make_ch4_param_scan_tseek.py \
    --data_zip data.zip \
    --pack_zip ch4_onekey_pack_nodata.zip \
    --base_script ch4_oneclick_make_tables_figs_minimal_fixed.py \
    --out_dir ch4_tseek_scan_out
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


def ensure_plot_style(lang: str = "zh"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK JP",
        "PingFang SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    return plt


def save_pdf_png(fig, out_no_ext: str) -> None:
    out_no_ext = str(out_no_ext)
    os.makedirs(os.path.dirname(out_no_ext), exist_ok=True)
    fig.savefig(out_no_ext + ".pdf", bbox_inches="tight")
    fig.savefig(out_no_ext + ".png", dpi=220, bbox_inches="tight")


def import_module_from_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def locate_ch4_py(work_dir: Path, ch4_py_arg: str | None) -> Path:
    if ch4_py_arg:
        p = Path(ch4_py_arg).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"--ch4_py not found: {p}")
        return p

    candidates = [
        work_dir / "ch4_onekey_pack" / "python" / "ch4_verify_python.py",
        work_dir / "python" / "ch4_verify_python.py",
    ]
    for p in candidates:
        if p.exists():
            return p

    all_found = list(work_dir.rglob("ch4_verify_python.py"))
    if all_found:
        return all_found[0]
    raise FileNotFoundError(
        "Cannot locate ch4_verify_python.py. Provide --pack_zip or --ch4_py explicitly."
    )


def parse_grid(s: str) -> List[float]:
    vals = [float(x.strip()) for x in s.split(",") if x.strip()]
    if not vals:
        raise ValueError("Empty scan grid.")
    return vals


def apply_tuned_overrides(cfg: dict) -> dict:
    """Apply the same tuned Chapter-4 parameter overrides as the one-click base script.

    This helper keeps the scan script aligned with
    `ch4_oneclick_make_tables_figs_minimal_fixed.py`, which is the script used
    to generate the main Chapter-4 results.
    """
    cfg["pk"]["D_th"] = 36.0
    cfg["pk"]["T_seek_sec"] = 3.0
    cfg["pk"]["D_free"] = 30.0
    cfg["pk"]["dist_th"] = 20.1886907302364
    cfg["ref"]["D_upd"] = 30.0
    return cfg


def prepare_runtime(args) -> Dict:
    work_dir = Path(args.work_dir).resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    data_zip = Path(args.data_zip).expanduser().resolve()
    if not data_zip.exists():
        raise FileNotFoundError(f"data_zip not found: {data_zip}")
    with zipfile.ZipFile(data_zip, "r") as zf:
        zf.extractall(work_dir)

    if args.pack_zip:
        pack_zip = Path(args.pack_zip).expanduser().resolve()
        if not pack_zip.exists():
            raise FileNotFoundError(f"pack_zip not found: {pack_zip}")
        with zipfile.ZipFile(pack_zip, "r") as zf:
            zf.extractall(work_dir)

    base_script = Path(args.base_script).expanduser().resolve()
    if not base_script.exists():
        raise FileNotFoundError(f"base_script not found: {base_script}")

    base_mod = import_module_from_path("ch4_oneclick_user_base", str(base_script))
    ch4_py = locate_ch4_py(work_dir, args.ch4_py)
    ch4 = import_module_from_path("ch4_verify_runtime", str(ch4_py))

    cfg = ch4.cfg_global_v2()
    if args.tuned:
        cfg = apply_tuned_overrides(cfg)

    b_xy, b_z = ch4.design_fir(cfg)

    data_dir = work_dir / "data" / "zhenzhi"
    synth_dir = work_dir / "data" / "synth_out"
    gt_path = data_dir / "parking_groundtruth_filled_cleaned.csv"
    if not gt_path.exists():
        raise FileNotFoundError(f"GT not found: {gt_path}")

    gt_base = pd.read_csv(gt_path)
    gt_all = gt_base.copy()
    if int(args.use_synth) == 1:
        gt_all = ch4.append_synth_gt_all_events(gt_base, str(synth_dir))

    files = sorted(pd.unique(gt_all["file"]))
    cache: Dict[str, dict] = {}
    for file_name in files:
        csv_path = base_mod._find_csv(file_name, str(data_dir), str(synth_dir))
        if csv_path is None:
            print(f"[WARN] missing CSV for {file_name}")
            continue
        k, t, B = ch4.load_csv(csv_path, cfg["fs"])
        k0 = int(k[0])
        gt_f = gt_all[gt_all["file"] == file_name]
        group = str(gt_f["scenario_group"].iloc[0])
        gt_idx = np.column_stack(
            [
                gt_f["k_star_in"].to_numpy(dtype=int) - k0 + 1,
                gt_f["k_star_out"].to_numpy(dtype=int) - k0 + 1,
            ]
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
        raise RuntimeError("No valid files in cache.")

    return {
        "work_dir": work_dir,
        "base_mod": base_mod,
        "ch4": ch4,
        "cfg_base": cfg,
        "b_xy": b_xy,
        "b_z": b_z,
        "cache": cache,
        "fs": float(cfg["fs"]),
    }


def summarize_one_cfg(runtime: Dict, cfg_v: dict, args) -> Dict[str, float]:
    base_mod = runtime["base_mod"]
    ch4 = runtime["ch4"]
    b_xy = runtime["b_xy"]
    b_z = runtime["b_z"]
    fs = runtime["fs"]

    rows_file = []
    tim_rows = []
    C_stable_found = []
    C_used_degrade = []

    for file_name, item in runtime["cache"].items():
        B = item["B"]
        gt_idx = item["gt_idx"]
        group = item["group"]
        events = item["events"]
        st = item["st"]

        pred, conf, _, dbg = base_mod.run_parking_with_dbg(
            ch4,
            B,
            cfg_v,
            b_xy,
            b_z,
            events=events,
            st=st,
        )
        pred_pp, conf_pp = base_mod.postprocess_pred_conf(
            pred,
            conf,
            fs,
            float(args.Tmin),
            float(args.gap_merge),
        )
        tp, fp, fn, p, r, f1, match = base_mod.eval_iou_with_match(
            pred_pp,
            gt_idx,
            float(args.iou_th),
        )
        rows_file.append(
            {
                "file": file_name,
                "group": group,
                "TP": tp,
                "FP": fp,
                "FN": fn,
                "P": p,
                "R": r,
                "F1": f1,
                "pred": int(pred_pp.shape[0]),
                "gt": int(gt_idx.shape[0]),
            }
        )

        for ip, ig, iou in match:
            pseg = pred_pp[ip]
            cseg = conf_pp[ip]
            gseg = gt_idx[ig]
            tim_rows.append(
                {
                    "file": file_name,
                    "group": group,
                    "dt_in": float((pseg[0] - gseg[0]) / fs),
                    "dt_out": float((pseg[1] - gseg[1]) / fs),
                    "tau_in": float((cseg[0] - gseg[0]) / fs),
                    "tau_out": float((cseg[1] - gseg[1]) / fs),
                    "iou": float(iou),
                }
            )

        if group == "C":
            C_stable_found.extend([bool(d.stable_found) for d in dbg])
            C_used_degrade.extend([bool(d.used_degrade) for d in dbg])

    T_file = pd.DataFrame(rows_file)
    T_group = base_mod.summarize_by_group(T_file)
    tim_df = pd.DataFrame(tim_rows)

    def _f1_of(group_name: str) -> float:
        row = T_group[T_group["group"] == group_name]
        return float(row["F1"].iloc[0]) if not row.empty else float("nan")

    def _tau_in_med(group_name: str) -> float:
        if tim_df.empty:
            return float("nan")
        row = tim_df[tim_df["group"] == group_name]
        return float(np.median(row["tau_in"])) if not row.empty else float("nan")

    return {
        "F1_A": _f1_of("A"),
        "F1_B": _f1_of("B"),
        "F1_C": _f1_of("C"),
        "F1_D": _f1_of("D"),
        "F1_ALL": _f1_of("ALL"),
        "tau_in_C_median": _tau_in_med("C"),
        "stable_found_ratio_C": float(np.mean(np.asarray(C_stable_found, dtype=float))) if C_stable_found else float("nan"),
        "degrade_ratio_C": float(np.mean(np.asarray(C_used_degrade, dtype=float))) if C_used_degrade else float("nan"),
    }


def plot_scan(df_scan: pd.DataFrame, tuned_value: float, out_no_ext: str, lang: str = "zh") -> None:
    plt = ensure_plot_style(lang)
    fig, ax1 = plt.subplots(figsize=(7.2, 4.6))

    x = df_scan["T_seek_sec"].to_numpy(dtype=float)
    ax1.plot(x, df_scan["F1_ALL"], marker="o", label="全体样本 $F_1$" if lang == "zh" else "ALL $F_1$")
    ax1.plot(x, df_scan["F1_C"], marker="s", label="C类工况 $F_1$" if lang == "zh" else "Group-C $F_1$")
    ax1.axvline(float(tuned_value), linestyle="--", linewidth=1.2, label="选定值" if lang == "zh" else "Selected")
    ax1.set_ylim(0.0, 1.2)
    ax1.set_xlabel(r"$T_{seek}$ / s")
    ax1.set_ylabel(r"$F_1$")
    ax1.grid(True, linestyle="--", alpha=0.35)

    ax2 = ax1.twinx()
    ax2.plot(
        x,
        df_scan["tau_in_C_median"],
        marker="^",
        linestyle=":",
        label="C类确认时差中位数" if lang == "zh" else "Group-C median $\\tau_{in}$",
    )
    ax2.set_ylabel("确认时差 / s" if lang == "zh" else "Confirmation delay / s")

    if lang == "zh":
        ax1.set_title(r"退化分支搜索窗 $T_{seek}$ 参数扫描结果")
    else:
        ax1.set_title(r"Parameter scan of degrade-branch search window $T_{seek}$")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", bbox_to_anchor=(0.98, 0.98))

    fig.tight_layout()
    save_pdf_png(fig, out_no_ext)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_zip", required=True)
    ap.add_argument("--pack_zip", default=None, help="Path to ch4_onekey_pack_nodata.zip")
    ap.add_argument("--ch4_py", default=None, help="Direct path to ch4_verify_python.py if no pack zip is used")
    ap.add_argument(
        "--base_script",
        default=str(Path(__file__).with_name("ch4_oneclick_make_tables_figs_minimal_fixed.py")),
        help="Path to your provided Chapter-4 one-click Python script",
    )
    ap.add_argument("--work_dir", default="_work_ch4_param_scan")
    ap.add_argument("--out_dir", default="ch4_param_scan_out")
    ap.add_argument("--use_synth", type=int, default=1)
    ap.add_argument("--tuned", type=int, default=1)
    ap.add_argument("--Tmin", type=float, default=4.0)
    ap.add_argument("--gap_merge", type=float, default=0.0)
    ap.add_argument("--iou_th", type=float, default=0.5)
    ap.add_argument("--scan_grid", default="1.0,1.5,2.0,2.5,3.0,3.5,4.0")
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    fig_dir = out_dir / "figures"
    csv_dir = out_dir / "csv"
    fig_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    runtime = prepare_runtime(args)
    grid = parse_grid(args.scan_grid)
    tuned_value = float(runtime["cfg_base"]["pk"]["T_seek_sec"])

    scan_rows = []
    for v in grid:
        print(f"[INFO] scanning T_seek_sec={v:.3f}")
        cfg_v = copy.deepcopy(runtime["cfg_base"])
        cfg_v["pk"]["T_seek_sec"] = float(v)
        row = summarize_one_cfg(runtime, cfg_v, args)
        row["T_seek_sec"] = float(v)
        scan_rows.append(row)

    df_scan = pd.DataFrame(scan_rows).sort_values("T_seek_sec").reset_index(drop=True)
    df_scan.to_csv(csv_dir / "ch4_tseek_scan.csv", index=False, encoding="utf-8-sig")
    plot_scan(df_scan, tuned_value=tuned_value, out_no_ext=str(fig_dir / "ch4_param_scan_tseek"), lang=args.lang)

    summary = {
        "scan_grid": grid,
        "selected_value": tuned_value,
        "best_by_all_f1": float(df_scan.loc[df_scan["F1_ALL"].idxmax(), "T_seek_sec"]),
        "best_all_f1": float(df_scan["F1_ALL"].max()),
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("[INFO] parameter baseline used for scan:")
    print(json.dumps({
        "T_seek_sec_default": runtime["cfg_base"]["pk"]["T_seek_sec"],
        "D_th": runtime["cfg_base"]["pk"]["D_th"],
        "D_free": runtime["cfg_base"]["pk"]["D_free"],
        "dist_th": runtime["cfg_base"]["pk"]["dist_th"],
        "D_upd": runtime["cfg_base"]["ref"]["D_upd"],
        "Tmin": args.Tmin,
        "gap_merge": args.gap_merge,
        "iou_th": args.iou_th,
    }, ensure_ascii=False, indent=2))

    print(f"[OK] Figure written to: {fig_dir}")
    print(f"[OK] CSV written to: {csv_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
