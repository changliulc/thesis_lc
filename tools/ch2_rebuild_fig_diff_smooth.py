#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.dom import minidom

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm


AXES_LAYOUT = [
    ("axes_1", "matplotlib.axis_2", r"$B$", "三轴原始磁场"),
    ("axes_2", "matplotlib.axis_4", r"$D$", "一阶差分"),
    ("axes_3", "matplotlib.axis_6", r"$\overline{D}$", "平滑差分"),
]
LINE_LABELS = ["X轴", "Y轴", "Z轴"]
LINE_COLORS = ["#1f77b4", "#d95319", "#edb120"]
TEXT_FONT_FAMILIES = ["Times New Roman", "SimSun", "STSong", "DejaVu Serif"]
AXES_WIDTH_SHRINK = 0.80
PANEL_TITLE_FONTSIZE = 13
AXIS_LABEL_FONTSIZE = 13
TICK_LABEL_FONTSIZE = 11
LEGEND_FONTSIZE = 12
LINE_WIDTH_SCALE = 1.35
SAVE_PAD_INCHES = 0.02


@dataclass
class Tick:
    pos_px: float
    value: float


@dataclass
class LineTrace:
    line_id: str
    x_px: np.ndarray
    y_px: np.ndarray
    color: str
    linewidth: float


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_reference_svg_candidates() -> list[Path]:
    root = repo_root()
    return [
        root.parent / "图片" / "第二章" / "图2-3.svg",
        root / "tmp" / "fig2_3_ref.svg",
    ]


def default_output_dir() -> Path:
    return repo_root() / "绘图" / "图片新修" / "第二章" / "fig_diff_smooth_rebuild"


def resolve_reference_svg(explicit: Path | None) -> Path:
    if explicit is not None:
        if explicit.exists():
            return explicit
        raise FileNotFoundError(f"Reference SVG not found: {explicit}")
    for path in default_reference_svg_candidates():
        if path.exists():
            return path
    checked = "\n".join(str(p) for p in default_reference_svg_candidates())
    raise FileNotFoundError(f"Could not find 图2-3.svg.\nChecked:\n{checked}")


def find_g_by_id(doc: minidom.Document, gid: str):
    for node in doc.getElementsByTagName("g"):
        if node.getAttribute("id") == gid:
            return node
    raise KeyError(gid)


def child_elements(node, tag_name: str | None = None) -> Iterable:
    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE and (tag_name is None or child.tagName == tag_name):
            yield child


def first_child_with_prefix(node, prefix: str):
    for child in child_elements(node, "g"):
        if child.getAttribute("id").startswith(prefix):
            return child
    return None


def first_path_d(node) -> str:
    for path in node.getElementsByTagName("path"):
        return path.getAttribute("d")
    raise ValueError("No <path> found")


def parse_path_points(path_d: str) -> tuple[np.ndarray, np.ndarray]:
    values = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+", path_d)]
    if len(values) < 4 or len(values) % 2 != 0:
        raise ValueError(f"Unsupported path data: {path_d[:80]}")
    arr = np.asarray(values, dtype=np.float64)
    return arr[0::2], arr[1::2]


def parse_patch_bounds(axes_node) -> tuple[float, float, float, float]:
    patch_node = first_child_with_prefix(axes_node, "patch_")
    if patch_node is None:
        raise ValueError(f"No patch node found under {axes_node.getAttribute('id')}")
    x, y = parse_path_points(first_path_d(patch_node))
    return float(x.min()), float(x.max()), float(y.min()), float(y.max())


def first_comment_text(node) -> str | None:
    for child in node.childNodes:
        if child.nodeType == child.COMMENT_NODE:
            text = child.data.strip()
            if text:
                return text
        if child.nodeType == child.ELEMENT_NODE:
            text = first_comment_text(child)
            if text:
                return text
    return None


def parse_tick_groups(axis_node, tick_prefix: str) -> list[Tick]:
    ticks: list[Tick] = []
    for tick_node in child_elements(axis_node, "g"):
        if not tick_node.getAttribute("id").startswith(tick_prefix):
            continue

        path_d = None
        for line_node in child_elements(tick_node, "g"):
            if line_node.getAttribute("id").startswith("line2d_"):
                try:
                    path_d = first_path_d(line_node)
                    break
                except ValueError:
                    continue
        if path_d is None:
            continue

        x, y = parse_path_points(path_d)
        pos = float(x[0] if tick_prefix == "xtick_" else y[0])

        label = None
        for text_node in child_elements(tick_node, "g"):
            if text_node.getAttribute("id").startswith("text_"):
                label = first_comment_text(text_node)
                break
        if label is None:
            continue
        ticks.append(Tick(pos_px=pos, value=float(label)))
    return ticks


def parse_direct_line_traces(axes_node) -> list[LineTrace]:
    traces: list[LineTrace] = []
    for child in child_elements(axes_node, "g"):
        line_id = child.getAttribute("id")
        if not line_id.startswith("line2d_"):
            continue
        path_nodes = child.getElementsByTagName("path")
        if not path_nodes:
            continue
        path_node = path_nodes[0]
        x_px, y_px = parse_path_points(path_node.getAttribute("d"))
        style = path_node.getAttribute("style")
        color_match = re.search(r"stroke:\s*([^;]+)", style)
        lw_match = re.search(r"stroke-width:\s*([^;]+)", style)
        traces.append(
            LineTrace(
                line_id=line_id,
                x_px=x_px,
                y_px=y_px,
                color=color_match.group(1) if color_match else "#1f77b4",
                linewidth=float(lw_match.group(1)) if lw_match else 1.2,
            )
        )
    traces.sort(key=lambda item: int(item.line_id.split("_")[1]))
    return traces


def linear_map_from_ticks(ticks: list[Tick]) -> np.poly1d:
    if len(ticks) < 2:
        raise ValueError("Need at least two tick labels to recover a linear mapping")
    px = np.asarray([tick.pos_px for tick in ticks], dtype=np.float64)
    values = np.asarray([tick.value for tick in ticks], dtype=np.float64)
    return np.poly1d(np.polyfit(px, values, deg=1))


def configure_matplotlib_fonts() -> None:
    plt.style.use("default")
    plt.rcParams["font.family"] = TEXT_FONT_FAMILIES
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = "Times New Roman"
    plt.rcParams["mathtext.it"] = "Times New Roman:italic"
    plt.rcParams["mathtext.bf"] = "Times New Roman:bold"
    plt.rcParams["axes.linewidth"] = 0.95
    plt.rcParams["xtick.direction"] = "out"
    plt.rcParams["ytick.direction"] = "out"


def mixed_font(size: float | None = None) -> fm.FontProperties:
    props = fm.FontProperties(family=TEXT_FONT_FAMILIES)
    if size is not None:
        props.set_size(size)
    return props


def parse_svg_canvas_size(doc: minidom.Document) -> tuple[float, float]:
    svg = doc.documentElement
    width_pt = float(svg.getAttribute("width").replace("pt", ""))
    height_pt = float(svg.getAttribute("height").replace("pt", ""))
    return width_pt, height_pt


def rebuild_from_reference(reference_svg: Path, out_dir: Path, dpi: int) -> dict[str, Path]:
    configure_matplotlib_fonts()
    doc = minidom.parse(str(reference_svg))
    fig_w_pt, fig_h_pt = parse_svg_canvas_size(doc)

    bottom_x_ticks = parse_tick_groups(find_g_by_id(doc, "matplotlib.axis_5"), "xtick_")
    x_map = linear_map_from_ticks(bottom_x_ticks)
    x_tick_values = np.asarray([tick.value for tick in bottom_x_ticks], dtype=np.float64)

    fig = plt.figure(figsize=(fig_w_pt / 72.0, fig_h_pt / 72.0), dpi=dpi)
    legend_handles = None
    top_axis = None

    for idx, (axes_id, y_axis_id, ylabel, title) in enumerate(AXES_LAYOUT):
        axes_node = find_g_by_id(doc, axes_id)
        x0, x1, y0, y1 = parse_patch_bounds(axes_node)
        width = (x1 - x0) / fig_w_pt
        rect = [
            x0 / fig_w_pt,
            1.0 - y1 / fig_h_pt,
            width * AXES_WIDTH_SHRINK,
            (y1 - y0) / fig_h_pt,
        ]
        ax = fig.add_axes(rect)

        y_ticks = parse_tick_groups(find_g_by_id(doc, y_axis_id), "ytick_")
        y_map = linear_map_from_ticks(y_ticks)
        y_tick_values = np.asarray([tick.value for tick in y_ticks], dtype=np.float64)

        traces = parse_direct_line_traces(axes_node)
        handles = []
        for color, label, trace in zip(LINE_COLORS, LINE_LABELS, traces, strict=True):
            x_data = x_map(trace.x_px)
            y_data = y_map(trace.y_px)
            handle = ax.plot(
                x_data,
                y_data,
                color=color,
                linewidth=max(trace.linewidth * LINE_WIDTH_SCALE, 1.8),
                label=label,
            )[0]
            handles.append(handle)

        if legend_handles is None:
            legend_handles = handles
        if top_axis is None:
            top_axis = ax

        ax.set_xlim(float(x_tick_values.min()), float(x_tick_values.max()))
        ax.set_xticks(x_tick_values)
        ax.set_yticks(y_tick_values)
        ax.set_title(title, fontsize=PANEL_TITLE_FONTSIZE, pad=6, fontproperties=mixed_font(PANEL_TITLE_FONTSIZE))
        ax.set_ylabel(ylabel, fontsize=AXIS_LABEL_FONTSIZE)
        ax.grid(True, color="#B0B0B0", linewidth=0.8, alpha=0.35)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", labelsize=TICK_LABEL_FONTSIZE, length=4.2, width=0.9)
        for spine in ax.spines.values():
            spine.set_linewidth(0.95)
            spine.set_color("#333333")

        if idx < len(AXES_LAYOUT) - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel("采样点", fontsize=AXIS_LABEL_FONTSIZE, fontproperties=mixed_font(AXIS_LABEL_FONTSIZE))

    if legend_handles is not None and top_axis is not None:
        top_axis.legend(
            legend_handles,
            LINE_LABELS,
            loc="upper left",
            bbox_to_anchor=(1.01, 1.0),
            frameon=True,
            fontsize=LEGEND_FONTSIZE,
            prop=mixed_font(LEGEND_FONTSIZE),
            framealpha=0.95,
            fancybox=False,
            borderpad=0.30,
            labelspacing=0.55,
            handlelength=2.2,
            handletextpad=0.45,
            borderaxespad=0.0,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "fig_diff_smooth_preview.png"
    svg_path = out_dir / "fig_diff_smooth_preview.svg"
    fig.savefig(png_path, dpi=dpi, bbox_inches="tight", pad_inches=SAVE_PAD_INCHES)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=SAVE_PAD_INCHES)
    plt.close(fig)
    return {"png": png_path, "svg": svg_path}


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rebuild chapter-2 figure 2.3 from the surviving Matplotlib SVG reference."
    )
    parser.add_argument(
        "--reference-svg",
        type=Path,
        default=None,
        help="Optional path to 图2-3.svg. If omitted, the script searches the known thesis folders.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=default_output_dir(),
        help="Preview output directory. This script never overwrites images/fig_diff_smooth.png.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=288,
        help="PNG export DPI. 288 keeps the preview close to the current thesis image size.",
    )
    return parser


def main() -> None:
    parser = build_argparser()
    args = parser.parse_args()
    reference_svg = resolve_reference_svg(args.reference_svg)
    outputs = rebuild_from_reference(reference_svg=reference_svg, out_dir=args.out_dir, dpi=args.dpi)
    print(f"Reference SVG: {reference_svg}")
    print(f"Preview PNG:   {outputs['png']}")
    print(f"Preview SVG:   {outputs['svg']}")
    print("No thesis image was replaced.")


if __name__ == "__main__":
    main()
