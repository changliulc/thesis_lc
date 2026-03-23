from __future__ import annotations

import argparse
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scipy.signal import filtfilt, firwin
except Exception:
    filtfilt = None
    firwin = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = Path(r"G:\地磁组\lab_office\路段统计\20240723校园测试数据\校园测试20240723.xlsx")
DEFAULT_OUT = ROOT / "images" / "ch4_pass_vs_park_python_matlab.png"


def configure_style() -> None:
    plt.rcParams["font.family"] = ["Times New Roman", "SimSun", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["mathtext.fontset"] = "stix"


def clamp(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


def _xlsx_col_to_index(col_ref: str) -> int:
    idx = 0
    for ch in col_ref:
        if "A" <= ch <= "Z":
            idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        with zf.open("xl/sharedStrings.xml") as f:
            root = ET.parse(f).getroot()
    except KeyError:
        return []
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    vals: list[str] = []
    for si in root.findall("m:si", ns):
        vals.append("".join(t.text or "" for t in si.findall(".//m:t", ns)))
    return vals


def _xlsx_sheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    ns_main = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    ns_rel = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zf.open("xl/workbook.xml") as f:
        wb_root = ET.parse(f).getroot()
    rel_id = None
    for sheet in wb_root.findall("m:sheets/m:sheet", ns_main):
        if sheet.attrib.get("name") == sheet_name:
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            break
    if rel_id is None:
        available = [s.attrib.get("name", "") for s in wb_root.findall("m:sheets/m:sheet", ns_main)]
        raise ValueError(f"Excel 中未找到工作表 {sheet_name}，可用工作表: {available}")
    with zf.open("xl/_rels/workbook.xml.rels") as f:
        rel_root = ET.parse(f).getroot()
    target = None
    for rel in rel_root.findall("r:Relationship", ns_rel):
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib.get("Target")
            break
    if not target:
        raise ValueError(f"工作表 {sheet_name} 的关系目标未找到")
    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target
    return target


def _read_xyz_from_xlsx_fallback(xlsx_path: Path, sheet_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cell_ref_pat = re.compile(r"([A-Z]+)")
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = _xlsx_shared_strings(zf)
        sheet_path = _xlsx_sheet_path(zf, sheet_name)
        with zf.open(sheet_path) as f:
            root = ET.parse(f).getroot()
    rows: list[list[float]] = []
    for row in root.findall(".//m:sheetData/m:row", ns):
        vals: dict[int, float] = {}
        for cell in row.findall("m:c", ns):
            ref = cell.attrib.get("r", "")
            m = cell_ref_pat.match(ref)
            if not m:
                continue
            col_idx = _xlsx_col_to_index(m.group(1))
            if col_idx > 2:
                continue
            v = cell.find("m:v", ns)
            if v is None or v.text is None:
                continue
            raw = v.text.strip()
            cell_type = cell.attrib.get("t", "")
            try:
                vals[col_idx] = float(shared[int(raw)]) if cell_type == "s" else float(raw)
            except Exception:
                continue
        if all(i in vals for i in (0, 1, 2)):
            rows.append([vals[0], vals[1], vals[2]])
    if not rows:
        raise ValueError("Excel 回退读取未能提取到前三列三轴数值")
    arr = np.asarray(rows, dtype=float)
    return arr[:, 0], arr[:, 1], arr[:, 2]


def read_xyz(xlsx_path: Path, sheet_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, usecols=[0, 1, 2])
        df = df.apply(pd.to_numeric, errors="coerce").dropna(how="any")
        if not df.empty:
            arr = df.to_numpy(dtype=float)
            return arr[:, 0], arr[:, 1], arr[:, 2]
    except Exception:
        pass
    return _read_xyz_from_xlsx_fallback(xlsx_path, sheet_name)


def moving_average(x: np.ndarray, win: int) -> np.ndarray:
    if win <= 1:
        return x.copy()
    kernel = np.ones(win, dtype=float) / float(win)
    pad = win // 2
    xp = np.pad(x, (pad, pad), mode="edge")
    y = np.convolve(xp, kernel, mode="same")
    return y[pad : pad + len(x)]


def lowpass_or_smooth(x: np.ndarray, fs: float, fc: float, order: int = 11) -> np.ndarray:
    if firwin is not None and filtfilt is not None:
        try:
            b = firwin(order + 1, fc / (fs / 2.0), window=("kaiser", 0.5), pass_zero="lowpass")
            return filtfilt(b, [1.0], x)
        except Exception:
            pass
    win = max(5, round(0.20 * fs))
    if win % 2 == 0:
        win += 1
    return moving_average(x, win)


def sec2idx(time_win: tuple[float, float], fs: float, n: int) -> tuple[int, int]:
    k1 = max(0, int(np.floor(time_win[0] * fs)))
    k2 = min(n - 1, int(np.floor(time_win[1] * fs)))
    return k1, k2


def pick_two_peaks(sig: np.ndarray, fs: float) -> tuple[int, int]:
    smooth = moving_average(sig, max(3, round(0.20 * fs)))
    order = np.argsort(smooth)[::-1]
    idx1 = int(order[0])
    min_gap = max(1, round(2.0 * fs))
    idx2 = idx1
    for idx in order[1:]:
        if abs(int(idx) - idx1) >= min_gap:
            idx2 = int(idx)
            break
    return min(idx1, idx2), max(idx1, idx2)


def build_windows(
    bx: np.ndarray,
    by: np.ndarray,
    bz: np.ndarray,
    fs: float,
    pass_win_sec: tuple[float, float],
    park_win_sec: tuple[float, float],
    pre_sec: float,
    pass_show_sec: float,
    park_show_sec: float,
    depart_target_sec: float,
) -> dict[str, np.ndarray]:
    n = len(bx)
    t = np.arange(n, dtype=float) / fs
    bx_f = lowpass_or_smooth(bx, fs, 5)
    by_f = lowpass_or_smooth(by, fs, 5)
    bz_f = lowpass_or_smooth(bz, fs, 6)
    b_f = np.column_stack([bx_f, by_f, bz_f])
    d_b = np.r_[0.0, np.sqrt(np.sum(np.diff(b_f, axis=0) ** 2, axis=1))]

    k1p, k2p = sec2idx(pass_win_sec, fs, n)
    k1k, k2k = sec2idx(park_win_sec, fs, n)
    pre_n = max(1, round(pre_sec * fs))
    b0p = np.mean(b_f[k1p : min(n, k1p + pre_n)], axis=0)
    b0k = np.mean(b_f[k1k : min(n, k1k + pre_n)], axis=0)

    bp = b_f[k1p : k2p + 1] - b0p
    bk = b_f[k1k : k2k + 1] - b0k
    tp = t[k1p : k2p + 1] - t[k1p]
    tk = t[k1k : k2k + 1] - t[k1k]
    dp = d_b[k1p : k2p + 1]
    dk = d_b[k1k : k2k + 1]

    i_peak_p = int(np.argmax(dp))
    t_peak_p = tp[i_peak_p]
    t0p = clamp(t_peak_p - 0.5 * pass_show_sec, 0.0, max(0.0, tp[-1] - pass_show_sec))
    sel_p = (tp >= t0p) & (tp <= t0p + pass_show_sec)

    _, idx_depart = pick_two_peaks(dk, fs)
    t_depart = tk[idx_depart]
    t0k = clamp(t_depart - depart_target_sec, 0.0, max(0.0, tk[-1] - park_show_sec))
    sel_k = (tk >= t0k) & (tk <= t0k + park_show_sec)

    return {
        "tp": tp[sel_p] - t0p,
        "bp": bp[sel_p],
        "dp": dp[sel_p],
        "tk": tk[sel_k] - t0k,
        "bk": bk[sel_k],
        "dk": dk[sel_k],
        "pass_show_sec": np.array([pass_show_sec], dtype=float),
        "park_show_sec": np.array([park_show_sec], dtype=float),
    }


def draw_figure(data: dict[str, np.ndarray], out_path: Path) -> None:
    matlab_colors = np.array([
        [0.0, 0.4470, 0.7410],
        [0.8500, 0.3250, 0.0980],
        [0.9290, 0.6940, 0.1250],
    ])
    fig, axs = plt.subplots(2, 2, figsize=(20 / 2.54, 11.5 / 2.54), facecolor="white")
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.11, top=0.90, wspace=0.18, hspace=0.24)

    fs_ax = 12
    fs_lab = 14
    fs_title = 15

    top_all = np.r_[data["bp"].reshape(-1), data["bk"].reshape(-1)]
    y_top_min, y_top_max = np.min(top_all), np.max(top_all)
    pad_top = 0.06 * max(1.0, y_top_max - y_top_min)

    bot_all = np.r_[data["dp"], data["dk"]]
    y_bot_max = np.max(bot_all)
    pad_bot = 0.06 * max(1.0, y_bot_max)

    for ax in axs.reshape(-1):
        ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.30)
        ax.set_facecolor("white")
        for s in ax.spines.values():
            s.set_linewidth(0.8)
            s.set_color((0.25, 0.25, 0.25))
        ax.tick_params(labelsize=fs_ax)

    for i in range(3):
        axs[0, 0].plot(data["tp"], data["bp"][:, i], linewidth=1.2, color=matlab_colors[i])
    axs[0, 0].axhline(0.0, linestyle="--", linewidth=0.9, color=(0.6, 0.6, 0.6))
    axs[0, 0].set_xlim(0, float(data["pass_show_sec"][0]))
    axs[0, 0].set_ylim(y_top_min - pad_top, y_top_max + pad_top)
    axs[0, 0].set_title("通过事件：三轴磁场扰动", fontsize=fs_title, fontweight="normal")
    axs[0, 0].set_ylabel("磁场扰动 / nT", fontsize=fs_lab)
    axs[0, 0].legend(["X轴", "Y轴", "Z轴"], loc="upper left", fontsize=fs_ax, frameon=True)

    for i in range(3):
        axs[0, 1].plot(data["tk"], data["bk"][:, i], linewidth=1.2, color=matlab_colors[i])
    axs[0, 1].axhline(0.0, linestyle="--", linewidth=0.9, color=(0.6, 0.6, 0.6))
    axs[0, 1].set_xlim(0, float(data["park_show_sec"][0]))
    axs[0, 1].set_ylim(y_top_min - pad_top, y_top_max + pad_top)
    axs[0, 1].set_title("停车到达事件：三轴磁场扰动", fontsize=fs_title, fontweight="normal")
    axs[0, 1].set_ylabel("")

    axs[1, 0].plot(data["tp"], data["dp"], linewidth=1.2, color=matlab_colors[0])
    axs[1, 0].set_xlim(0, float(data["pass_show_sec"][0]))
    axs[1, 0].set_ylim(0, y_bot_max + pad_bot)
    axs[1, 0].set_xlabel("时间 / s", fontsize=fs_lab)
    axs[1, 0].set_ylabel("一阶差分幅值 ||ΔB||₂", fontsize=fs_lab)

    axs[1, 1].plot(data["tk"], data["dk"], linewidth=1.2, color=matlab_colors[0])
    axs[1, 1].set_xlim(0, float(data["park_show_sec"][0]))
    axs[1, 1].set_ylim(0, y_bot_max + pad_bot)
    axs[1, 1].set_xlabel("时间 / s", fontsize=fs_lab)
    axs[1, 1].set_ylabel("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, facecolor="white")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python + MATLAB 风格重画图4.2（通过/停车对比图）")
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX, help="原始三轴数据 Excel 路径")
    parser.add_argument("--sheet", type=str, default="下午", help="Excel 工作表名称")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="输出 PNG 路径")
    parser.add_argument("--fs", type=float, default=50.0, help="采样频率")
    parser.add_argument("--pass-win", nargs=2, type=float, default=(406.0, 443.0), metavar=("START", "END"))
    parser.add_argument("--park-win", nargs=2, type=float, default=(70.0, 115.0), metavar=("START", "END"))
    parser.add_argument("--pre-sec", type=float, default=1.0)
    parser.add_argument("--pass-show", type=float, default=10.0)
    parser.add_argument("--park-show", type=float, default=25.0)
    parser.add_argument("--depart-target", type=float, default=20.0)
    return parser.parse_args()


def main() -> None:
    configure_style()
    args = parse_args()
    if not args.xlsx.exists():
        raise FileNotFoundError(f"未找到原始 Excel：{args.xlsx}")
    bx, by, bz = read_xyz(args.xlsx, args.sheet)
    data = build_windows(
        bx=bx,
        by=by,
        bz=bz,
        fs=args.fs,
        pass_win_sec=tuple(args.pass_win),
        park_win_sec=tuple(args.park_win),
        pre_sec=args.pre_sec,
        pass_show_sec=args.pass_show,
        park_show_sec=args.park_show,
        depart_target_sec=args.depart_target,
    )
    draw_figure(data, args.out)
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
