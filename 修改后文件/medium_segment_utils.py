from __future__ import annotations

import math
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np


XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

MEDIUM_DATA_PATH = Path(__file__).resolve().with_name("中型车数据.xlsx")
SPEED_EST_PATH = Path(__file__).resolve().with_name("估计速度.xlsx")
NUMERIC_RE = re.compile(r"-?\d+(\.\d+)?([Ee][+-]?\d+)?")


@dataclass
class MediumSegmentRecord:
    index: int
    name: str
    description: str
    speed_kmh: float
    raw_xyz: np.ndarray
    delta_xyz: np.ndarray
    baseline_xyz: np.ndarray
    status: np.ndarray


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    shared_strings: list[str] = []
    if "xl/sharedStrings.xml" not in zf.namelist():
        return shared_strings

    sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    for si in sst.findall("a:si", XLSX_NS):
        texts = [node.text or "" for node in si.iterfind(".//a:t", XLSX_NS)]
        shared_strings.append("".join(texts))
    return shared_strings


def _read_sheet_rows(
    zf: zipfile.ZipFile,
    sheet_target: str,
    shared_strings: list[str],
) -> list[list[str]]:
    sheet_xml = ET.fromstring(zf.read(f"xl/{sheet_target}"))
    rows: list[list[str]] = []

    for row in sheet_xml.findall(".//a:sheetData/a:row", XLSX_NS):
        values: dict[int, str] = {}
        for cell in row.findall("a:c", XLSX_NS):
            ref = cell.attrib["r"]
            match = re.match(r"([A-Z]+)(\d+)", ref)
            if match is None:
                continue
            col_idx = 0
            for ch in match.group(1):
                col_idx = col_idx * 26 + (ord(ch) - 64)
            col_idx -= 1
            value_node = cell.find("a:v", XLSX_NS)
            value = "" if value_node is None else (value_node.text or "")
            if cell.attrib.get("t") == "s" and value:
                value = shared_strings[int(value)]
            values[col_idx] = value
        max_col = max(values) if values else -1
        rows.append([values.get(i, "") for i in range(max_col + 1)])
    return rows


def load_xlsx_sheets(path: Path) -> dict[str, list[list[str]]]:
    with zipfile.ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        relationships = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
        shared_strings = _read_shared_strings(zf)

        sheets: dict[str, list[list[str]]] = {}
        for sheet in workbook.find("a:sheets", XLSX_NS):
            rel_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = rel_map[rel_id].replace("\\", "/")
            sheets[sheet.attrib["name"]] = _read_sheet_rows(zf, target, shared_strings)
    return sheets


def _to_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return math.nan


def _is_numeric(value: str) -> bool:
    return bool(value) and bool(NUMERIC_RE.fullmatch(value))


def load_medium_segments(
    data_path: Path = MEDIUM_DATA_PATH,
    speed_path: Path = SPEED_EST_PATH,
    sheet_name: str = "Sheet1",
) -> list[MediumSegmentRecord]:
    medium_rows = load_xlsx_sheets(data_path)[sheet_name]
    speed_rows = load_xlsx_sheets(speed_path)[sheet_name]
    speed_map = {
        row[0]: float(row[5])
        for row in speed_rows[1:]
        if len(row) >= 6 and row[0] and _is_numeric(row[5])
    }

    header_rows: list[int] = []
    for idx, row in enumerate(medium_rows):
        first = row[0] if row else ""
        if first and not _is_numeric(first):
            header_rows.append(idx)
    header_rows.append(len(medium_rows))

    segments: list[MediumSegmentRecord] = []
    for segment_idx in range(len(header_rows) - 1):
        header_idx = header_rows[segment_idx]
        next_idx = header_rows[segment_idx + 1]
        header = medium_rows[header_idx]
        data_rows = medium_rows[header_idx + 1 : next_idx]
        if not data_rows:
            continue

        data = np.full((len(data_rows), 10), np.nan, dtype=np.float64)
        for row_idx, row in enumerate(data_rows):
            for col_idx, value in enumerate(row[:10]):
                data[row_idx, col_idx] = _to_float(value)

        segments.append(
            MediumSegmentRecord(
                index=segment_idx + 1,
                name=header[0],
                description=header[3] if len(header) > 3 else "",
                speed_kmh=float(speed_map.get(header[0], math.nan)),
                raw_xyz=data[:, 0:3],
                delta_xyz=data[:, 3:6],
                status=np.nan_to_num(data[:, 6], nan=-1).astype(int),
                baseline_xyz=data[:, 7:10],
            )
        )
    return segments


def get_medium_segment(
    segment_index: int,
    data_path: Path = MEDIUM_DATA_PATH,
    speed_path: Path = SPEED_EST_PATH,
    sheet_name: str = "Sheet1",
) -> MediumSegmentRecord:
    segments = load_medium_segments(data_path=data_path, speed_path=speed_path, sheet_name=sheet_name)
    if segment_index < 1 or segment_index > len(segments):
        raise IndexError(f"segment_index must be in [1, {len(segments)}], got {segment_index}")
    return segments[segment_index - 1]
