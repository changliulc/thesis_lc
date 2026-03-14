from pathlib import Path
import sys
import types

import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio

try:
    import coverage

    if not hasattr(coverage, "types"):
        coverage.types = types.SimpleNamespace()
    for _name in [
        "Tracer",
        "TTraceData",
        "TTraceFn",
        "TShouldTraceFn",
        "TShouldStartContextFn",
        "TWarnFn",
        "TFileDisposition",
    ]:
        if not hasattr(coverage.types, _name):
            setattr(coverage.types, _name, object)
except Exception:
    coverage = types.ModuleType("coverage")
    coverage.types = types.SimpleNamespace()
    for _name in [
        "Tracer",
        "TTraceData",
        "TTraceFn",
        "TShouldTraceFn",
        "TShouldStartContextFn",
        "TWarnFn",
        "TFileDisposition",
    ]:
        setattr(coverage.types, _name, object)
    sys.modules["coverage"] = coverage


ROOT = Path(__file__).resolve().parents[3]
DATA_MAT = Path(__file__).resolve().parent / "processedVehicleData_3class_REAL (2).mat"
REVISION_V9 = Path(__file__).resolve().parent / "out_ch3_revision_pkg_20260314_seed42_v9" / "images"
IMG_ROOT = ROOT / "images"

DTW_CODE_DIR = Path(__file__).resolve().parent / "dtw_cnn_handoff" / "code"
if str(DTW_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(DTW_CODE_DIR))

import run_dtw_clsmin_sweep as C  # noqa: E402


def ensure_plot_style():
    plt.style.use("default")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Microsoft YaHei",
                "SimHei",
                "SimSun",
                "Arial Unicode MS",
                "DejaVu Sans",
            ],
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.unicode_minus": False,
        }
    )


def load_raw_y_tlen(mat_path: Path):
    mat = sio.loadmat(mat_path)
    pd_cell = mat["ProcessedData"]
    tl_cell = mat["targetLength"]
    raw_list, y_list, tlen_list = [], [], []
    for c in range(3):
        cell = pd_cell[0, c]
        tl = tl_cell[0, c].reshape(-1)
        for i in range(cell.shape[1]):
            arr = np.array(cell[0, i], dtype=np.float32)
            t = int(np.array(tl[i]).squeeze())
            raw_list.append(arr)
            y_list.append(c)
            tlen_list.append(t)
    return raw_list, np.array(y_list, dtype=np.int64), np.array(tlen_list, dtype=np.int64)


def extract_event(raw_pad: np.ndarray, n: int, fs: float, n0: int = 10):
    n = int(n)
    raw = np.asarray(raw_pad[:n, :], dtype=np.float32)
    n0 = min(int(n0), n)
    b0 = raw[:n0].mean(axis=0, keepdims=True)
    d_b = raw - b0
    b_mag = np.sqrt(np.sum(d_b**2, axis=1)).astype(np.float32)
    t = np.arange(n, dtype=np.float32) / fs
    return raw, d_b, b_mag, t


def estimate_event_onset(signal: np.ndarray, frac: float = 0.08) -> int:
    signal = np.asarray(signal, dtype=np.float32).reshape(-1)
    if signal.size == 0:
        return 0
    n0 = max(5, min(signal.size, int(round(0.1 * signal.size))))
    baseline = float(np.median(signal[:n0]))
    dev = np.abs(signal - baseline)
    if signal.size >= 5:
        kernel = np.ones(5, dtype=np.float32) / 5.0
        dev = np.convolve(dev, kernel, mode="same")
    peak = float(dev.max())
    if peak <= 1e-6:
        return 0
    idx = np.where(dev >= frac * peak)[0]
    return int(idx[0]) if idx.size else 0


def pick_pair(y: np.ndarray, tlen: np.ndarray, target_class=1, short_len=92, long_len=176):
    idx_cls = np.where(y == target_class)[0]
    if idx_cls.size == 0:
        raise RuntimeError(f"class {target_class} has no samples")
    len_cls = tlen[idx_cls]
    idx_short = idx_cls[len_cls == short_len]
    idx_long = idx_cls[len_cls == long_len]
    if idx_short.size and idx_long.size:
        return int(idx_short[0]), int(idx_long[0])
    i_short = int(idx_cls[np.argmin(np.abs(len_cls - short_len))])
    i_long = int(idx_cls[np.argmin(np.abs(len_cls - long_len))])
    return i_short, i_long


def resample_linear(x: np.ndarray, out_len: int):
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) == out_len:
        return x.copy()
    xp = np.linspace(0.0, 1.0, len(x), dtype=np.float32)
    xq = np.linspace(0.0, 1.0, out_len, dtype=np.float32)
    return np.interp(xq, xp, x).astype(np.float32)


def pick_best_exact_length_pair(
    raw_list,
    y: np.ndarray,
    tlen: np.ndarray,
    fs: float,
    target_class: int = 1,
    short_len: int = 92,
    long_len: int = 176,
    n0: int = 10,
):
    idx_cls = np.where(y == target_class)[0]
    idx_short = idx_cls[tlen[idx_cls] == short_len]
    idx_long = idx_cls[tlen[idx_cls] == long_len]
    if idx_short.size == 0 or idx_long.size == 0:
        return None

    best_pair = None
    best_score = -1e18
    for i in idx_short:
        _, d_b_s, b_s, _ = extract_event(raw_list[int(i)], short_len, fs, n0)
        z_s = d_b_s[:, 2]
        b_s_r = resample_linear(b_s, long_len)
        z_s_r = resample_linear(z_s, long_len)
        for j in idx_long:
            _, d_b_l, b_l, _ = extract_event(raw_list[int(j)], long_len, fs, n0)
            z_l = d_b_l[:, 2]
            corr_b = float(np.corrcoef(b_s_r, b_l)[0, 1])
            corr_z = float(np.corrcoef(z_s_r, z_l)[0, 1])
            amp_ratio = float((b_s.max() + 1e-6) / (b_l.max() + 1e-6))
            score = 0.65 * corr_b + 0.35 * corr_z - 0.15 * abs(np.log(amp_ratio))
            if score > best_score:
                best_score = score
                best_pair = (int(i), int(j))
    return best_pair


def pick_max_energy(raw_list, tlen: np.ndarray, candidate_idx: np.ndarray, fs: float, n0: int = 10):
    best_idx = int(candidate_idx[0])
    best_energy = -1.0
    for idx in candidate_idx:
        _, _, b_mag, _ = extract_event(raw_list[int(idx)], int(tlen[int(idx)]), fs, n0)
        energy = float(np.sum(b_mag**2))
        if energy > best_energy:
            best_energy = energy
            best_idx = int(idx)
    return best_idx


def pick_percentile_speed_pair(
    raw_list,
    y: np.ndarray,
    tlen: np.ndarray,
    fs: float,
    target_class: int = 1,
    q: float = 0.15,
    n0: int = 10,
):
    idx_cls = np.where(y == target_class)[0]
    len_cls = tlen[idx_cls]
    order = np.argsort(len_cls)
    idx_sorted = idx_cls[order]
    n_all = len(idx_sorted)
    n_q = max(1, int(round(q * n_all)))
    short_pool = idx_sorted[:n_q]
    long_pool = idx_sorted[max(0, n_all - n_q) :]
    idx_short = pick_max_energy(raw_list, tlen, short_pool, fs, n0)
    idx_long = pick_max_energy(raw_list, tlen, long_pool, fs, n0)
    return idx_short, idx_long


def save_both(fig, filename: str):
    for out_dir in [IMG_ROOT, REVISION_V9]:
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / filename, dpi=240, bbox_inches="tight")


def plot_speed_stretch(raw_short: np.ndarray, len_short: int, raw_long: np.ndarray, len_long: int, fs: float):
    _, _, mag_short, _ = extract_event(raw_short, len_short, fs)
    _, _, mag_long, _ = extract_event(raw_long, len_long, fs)

    onset_short = estimate_event_onset(mag_short)
    onset_long = estimate_event_onset(mag_long)
    t_short = (np.arange(len(mag_short), dtype=np.float32) - onset_short) / fs
    t_long = (np.arange(len(mag_long), dtype=np.float32) - onset_long) / fs

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    ax.plot(
        t_short,
        mag_short,
        linewidth=1.9,
        color="#1f77b4",
        label=f"短时长样本（{len(mag_short)}点，{len(mag_short) / fs:.2f} s）",
    )
    ax.plot(
        t_long,
        mag_long,
        linewidth=1.9,
        color="#ff7f0e",
        label=f"长时长样本（{len(mag_long)}点，{len(mag_long) / fs:.2f} s）",
    )
    ax.axvline(0.0, color="0.55", linestyle="--", linewidth=1.0)
    ax.set_xlabel("相对时间 / s")
    ax.set_ylabel(r"模值序列 $|b[n]|$ / nT")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(frameon=True, edgecolor="black", fancybox=False, loc="upper right")
    fig.tight_layout()
    save_both(fig, "fig_motivation_speed.png")
    plt.close(fig)


def plot_dtw_alignment(
    raw_a: np.ndarray,
    len_a: int,
    raw_b: np.ndarray,
    len_b: int,
    fs: float,
    wR: float = 0.15,
    step: float = 0.05,
):
    _, d_b_a, mag_a, _ = extract_event(raw_a, len_a, fs)
    _, d_b_b, mag_b, _ = extract_event(raw_b, len_b, fs)
    seq_a = np.concatenate([d_b_a, mag_a[:, None]], axis=1)
    seq_b = np.concatenate([d_b_b, mag_b[:, None]], axis=1)

    onset_a = estimate_event_onset(mag_a)
    onset_b = estimate_event_onset(mag_b)
    t_a = (np.arange(len_a, dtype=np.float32) - onset_a) / fs
    t_b = (np.arange(len_b, dtype=np.float32) - onset_b) / fs

    w = max(1, int(round(wR * max(len(seq_a), len(seq_b)))))
    warped_a = C.dtw_warp_mv(seq_a.astype(np.float32), seq_b.astype(np.float32), w, float(step))

    z_a = d_b_a[:, 2]
    z_b = d_b_b[:, 2]
    z_warp = warped_a[:, 2]

    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.4))

    axes[0].plot(
        t_a,
        z_a,
        linewidth=1.8,
        color="#1f77b4",
        label=f"样本A（{len_a}点，{len_a / fs:.2f} s）",
    )
    axes[0].plot(
        t_b,
        z_b,
        linewidth=1.8,
        color="#ff7f0e",
        label=f"样本B（{len_b}点，{len_b / fs:.2f} s）",
    )
    axes[0].axvline(0.0, color="0.55", linestyle="--", linewidth=1.0)
    axes[0].set_title("对齐前（时间伸缩与局部错位）", pad=6)
    axes[0].set_xlabel("相对时间 / s")
    axes[0].set_ylabel(r"$\Delta B_z[n]$ / nT")
    axes[0].grid(True, linestyle="--", alpha=0.35)
    axes[0].legend(frameon=True, edgecolor="black", fancybox=False, loc="upper right")

    axes[1].plot(t_b, z_b, linewidth=1.8, color="#ff7f0e", label="参考样本B")
    axes[1].plot(
        t_b,
        z_warp,
        linewidth=1.8,
        color="#1f77b4",
        linestyle="--",
        label="对齐后的样本A",
    )
    axes[1].set_title("DTW 对齐后（恢复局部结构对应）", pad=6)
    axes[1].set_xlabel("参考时间轴 / s")
    axes[1].set_ylabel(r"$\Delta B_z[n]$ / nT")
    axes[1].grid(True, linestyle="--", alpha=0.35)
    axes[1].legend(frameon=True, edgecolor="black", fancybox=False, loc="upper right")

    fig.tight_layout()
    save_both(fig, "fig_motivation_dtw_align_z.png")
    plt.close(fig)


def main():
    ensure_plot_style()
    raw_list, y, tlen = load_raw_y_tlen(DATA_MAT)
    pair = pick_best_exact_length_pair(
        raw_list,
        y,
        tlen,
        fs=50.0,
        target_class=1,
        short_len=92,
        long_len=176,
    )
    if pair is None:
        i_short, i_long = pick_percentile_speed_pair(raw_list, y, tlen, fs=50.0, target_class=1, q=0.15)
    else:
        i_short, i_long = pair
    raw_short = raw_list[i_short]
    raw_long = raw_list[i_long]
    len_short = int(tlen[i_short])
    len_long = int(tlen[i_long])
    fs = 50.0
    plot_speed_stretch(raw_short, len_short, raw_long, len_long, fs)
    plot_dtw_alignment(raw_short, len_short, raw_long, len_long, fs)
    print(
        f"Rendered motivation figures with class-1 pair: short={len_short}, long={len_long}"
    )


if __name__ == "__main__":
    main()
