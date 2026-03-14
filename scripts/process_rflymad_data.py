"""
Deep RFlyMAD raw data extractor and cleaner.

Reads authoritative raw RFlyMAD tree and produces canonical cleaned dataset for
benchmark validation under data/new_data/rflymad.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


AUTHORITATIVE_RFLYMAD_RAW = Path(
    r"C:\VIRAK\Python Code\aero-guardian-full-version-including-dl&ml\data\raw\rflymad"
)

DEFAULT_OUTPUT_DIR = Path("data/new_data/rflymad")

# Folder/category -> benchmark fault label.
FAULT_TYPE_BY_ROOT = {
    "real-motor": "motor_fault",
    "real-sensors": "sensor_fault",
    "hil-wind": "wind_fault",
    "sil-wind": "wind_fault",
    "real-no_fault": "normal",
}


@dataclass
class CaseSummary:
    flight_id: str
    source_root: str
    telemetry_file: str
    testinfo_file: str
    fault_type: str
    fault_injection_time_sec: Optional[float]
    sample_count: int
    usable_count: int
    dropped_count: int


def _normalize_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace({"--.--": np.nan, "": np.nan}), errors="coerce")


def _read_testinfo(testinfo_path: Path) -> Dict[str, str]:
    if testinfo_path.suffix.lower() in {".xlsx", ".xls"}:
        return _read_testinfo_excel(testinfo_path)

    return _read_testinfo_csv(testinfo_path)


def _read_testinfo_csv(testinfo_path: Path) -> Dict[str, str]:
    info: Dict[str, str] = {}
    with open(testinfo_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            key = str(row[0]).strip()
            value = ",".join(row[1:]).strip() if len(row) > 1 else ""
            info[key] = value
    return info


def _read_testinfo_excel(testinfo_path: Path) -> Dict[str, str]:
    info: Dict[str, str] = {}
    df = pd.read_excel(testinfo_path, header=None)
    for _, row in df.iterrows():
        if len(row) == 0:
            continue
        key = str(row.iloc[0]).strip()
        if not key or key.lower() == "nan":
            continue
        values = [str(v).strip() for v in row.iloc[1:].tolist() if str(v).strip() and str(v).lower() != "nan"]
        info[key] = ",".join(values)
    return info


def _parse_fault_injection_time(info: Dict[str, str]) -> Optional[float]:
    raw = str(info.get("Fault injection time", "")).strip()
    if not raw:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    return float(match.group(0))


def _infer_fault_type(telemetry_path: Path) -> str:
    lower_parts = [p.lower() for p in telemetry_path.parts]
    for part in lower_parts:
        if part in FAULT_TYPE_BY_ROOT:
            return FAULT_TYPE_BY_ROOT[part]
    return "unknown"


def _find_case_dir(telemetry_path: Path) -> Optional[Path]:
    for parent in telemetry_path.parents:
        if parent.name.lower().startswith("testcase_"):
            return parent

    for parent in telemetry_path.parents:
        has_testinfo_csv = (parent / "TestInfo.csv").exists()
        has_testinfo_xlsx = any(parent.glob("TestInfo*.xlsx"))
        if has_testinfo_csv or has_testinfo_xlsx:
            return parent

    return None


def _find_testinfo_file(case_dir: Path) -> Optional[Path]:
    candidates = [
        case_dir / "TestInfo.csv",
    ]
    candidates.extend(sorted(case_dir.glob("TestInfo*.xlsx")))
    candidates.extend(sorted(case_dir.glob("TestInfo*.csv")))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _build_flight_id(case_dir: Path, raw_root: Path) -> str:
    try:
        rel = case_dir.relative_to(raw_root)
        raw_id = "_".join(rel.parts)
    except Exception:
        raw_id = case_dir.name

    # Keep IDs stable and filesystem-safe for downstream tools.
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", raw_id).strip("_")
    return f"RFlyMAD_{slug}" if slug else "RFlyMAD_unknown_case"


def _collect_telemetry_files(raw_root: Path) -> Iterable[Path]:
    # RFlyMAD telemetry files are named like "... vehicle1.csv" in TLog folders.
    return raw_root.rglob("*vehicle1.csv")


def _clean_single_case(
    telemetry_path: Path,
    raw_root: Path,
) -> tuple[pd.DataFrame, CaseSummary]:
    case_dir = _find_case_dir(telemetry_path)
    if case_dir is None:
        raise ValueError(f"Cannot determine TestCase directory for {telemetry_path}")

    testinfo_path = _find_testinfo_file(case_dir)
    if testinfo_path is None:
        raise FileNotFoundError(f"Missing TestInfo metadata file for {telemetry_path}")

    info = _read_testinfo(testinfo_path)

    flight_id = _build_flight_id(case_dir, raw_root)

    fault_type = _infer_fault_type(telemetry_path)
    injection_time_sec = _parse_fault_injection_time(info)

    usecols = [
        "Timestamp",
        "rollRate",
        "pitchRate",
        "yawRate",
        "localPosition.x",
        "localPosition.y",
        "localPosition.z",
        "localPosition.vx",
        "localPosition.vy",
        "localPosition.vz",
        "acc_x",
        "acc_y",
        "acc_z",
    ]

    df = pd.read_csv(telemetry_path, low_memory=False)
    # Missing accelerometer columns are expected in some exports.
    for col in usecols:
        if col not in df.columns:
            df[col] = np.nan

    sample_count = len(df)

    ts = pd.to_datetime(df["Timestamp"], errors="coerce")
    if ts.notna().any():
        elapsed = (ts - ts.iloc[0]).dt.total_seconds()
    else:
        freq_raw = str(info.get("Data collected Frequency", "")).strip()
        freq_match = re.search(r"\d+(?:\.\d+)?", freq_raw)
        freq = float(freq_match.group(0)) if freq_match else 50.0
        elapsed = pd.Series(np.arange(len(df), dtype=float) / max(freq, 1.0))

    cleaned = pd.DataFrame(
        {
            "flight_id": [flight_id] * len(df),
            "timestamp": elapsed,
            "fault_type": [fault_type] * len(df),
            "is_fault": 0,
            "pos_x": _normalize_numeric(df["localPosition.x"]),
            "pos_y": _normalize_numeric(df["localPosition.y"]),
            "pos_z": _normalize_numeric(df["localPosition.z"]),
            "vel_x": _normalize_numeric(df["localPosition.vx"]),
            "vel_y": _normalize_numeric(df["localPosition.vy"]),
            "vel_z": _normalize_numeric(df["localPosition.vz"]),
            "gyro_x": _normalize_numeric(df["rollRate"]),
            "gyro_y": _normalize_numeric(df["pitchRate"]),
            "gyro_z": _normalize_numeric(df["yawRate"]),
            "acc_x": _normalize_numeric(df["acc_x"]),
            "acc_y": _normalize_numeric(df["acc_y"]),
            "acc_z": _normalize_numeric(df["acc_z"]),
            "source_case_dir": [str(case_dir)] * len(df),
            "source_file": [str(telemetry_path)] * len(df),
            "fault_injection_time_sec": [injection_time_sec] * len(df),
            "source_root": [str(raw_root)] * len(df),
        }
    )

    if fault_type != "normal" and injection_time_sec is not None:
        cleaned["is_fault"] = (cleaned["timestamp"] >= injection_time_sec).astype(int)

    cleaned = cleaned.dropna(subset=["timestamp"]).reset_index(drop=True)
    usable_count = len(cleaned)
    dropped_count = sample_count - usable_count

    summary = CaseSummary(
        flight_id=flight_id,
        source_root=str(raw_root),
        telemetry_file=str(telemetry_path),
        testinfo_file=str(testinfo_path),
        fault_type=fault_type,
        fault_injection_time_sec=injection_time_sec,
        sample_count=sample_count,
        usable_count=usable_count,
        dropped_count=dropped_count,
    )
    return cleaned, summary


def process_rflymad(raw_root: Path, output_dir: Path) -> Dict[str, object]:
    if not raw_root.exists():
        raise FileNotFoundError(f"RFlyMAD raw root not found: {raw_root}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / "rflymad_cleaned.csv"

    if out_csv.exists():
        out_csv.unlink()

    summaries: List[CaseSummary] = []
    case_count = 0
    total_rows = 0

    for telemetry_path in _collect_telemetry_files(raw_root):
        try:
            cleaned, summary = _clean_single_case(telemetry_path, raw_root)
        except Exception:
            continue

        if len(cleaned) == 0:
            continue

        cleaned.to_csv(out_csv, mode="a", index=False, header=not out_csv.exists(), encoding="utf-8")
        summaries.append(summary)
        case_count += 1
        total_rows += len(cleaned)

    if not out_csv.exists():
        raise RuntimeError("No usable RFlyMAD telemetry files were extracted")

    fault_counts = {}
    for s in summaries:
        fault_counts[s.fault_type] = fault_counts.get(s.fault_type, 0) + 1

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "source_root": str(raw_root),
        "output_csv": str(out_csv),
        "total_cases": case_count,
        "total_rows": total_rows,
        "fault_case_counts": fault_counts,
    }

    (output_dir / "rflymad_extraction_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (output_dir / "rflymad_case_manifest.json").write_text(
        json.dumps([s.__dict__ for s in summaries], indent=2), encoding="utf-8"
    )

    return manifest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and clean RFlyMAD raw telemetry")
    parser.add_argument("--input", type=Path, default=AUTHORITATIVE_RFLYMAD_RAW, help="Authoritative RFlyMAD raw root")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for cleaned dataset")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    manifest = process_rflymad(args.input, args.output)
    print("rflymad_cleaned", manifest["output_csv"])
    print("total_cases", manifest["total_cases"])
    print("total_rows", manifest["total_rows"])
    print("fault_case_counts", manifest["fault_case_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
