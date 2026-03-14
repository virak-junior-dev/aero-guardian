"""
FAA Raw Data Processor (Rebuilt from Zero)
==========================================
Date: 2026-03-14

Purpose:
1. Read raw FAA Excel reports from data/raw/faa.
2. Build provenance-preserving incident records.
3. Add deterministic physics/regulatory flags.
4. Export upgraded datasets to data/new_data/faa.

Primary outputs:
- faa_reports.json
- faa_simulatable.json
- faa_schema_diagnostics.json
- faa_actual_failures.json
- faa_high_risk_sightings.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logger = logging.getLogger("AeroGuardian.FAAProcessor")


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


# -----------------------------------------------------------------------------
# Config and Constants
# -----------------------------------------------------------------------------


@dataclass
class FAAConfig:
    raw_data_dir: Path = field(default_factory=lambda: Path("data/raw/faa"))
    output_dir: Path = field(default_factory=lambda: Path("data/new_data/faa"))
    include_high_risk: bool = True
    verbose: bool = False


TARGET_INPUT_COLUMNS = {
    "summary",
    "description",
    "narrative",
    "date",
    "day of sighting",
    "date of sighting",
    "date of sighitng",
    "city",
    "state",
}

SUMMARY_CANDIDATES = [
    "summary",
    "description",
    "narrative",
    "eventdescription",
    "event description",
]

DATE_CANDIDATES = [
    "date",
    "day of sighting",
    "date of sighting",
    "date of sighitng",
    "eventdate",
    "event date",
]

CITY_CANDIDATES = ["city", "eventcity", "event city"]
STATE_CANDIDATES = ["state", "eventstate", "event state"]

FAULT_META = {
    "gps_loss": {
        "hazard_category": "NAVIGATION",
        "hazard_description": "GPS signal loss or position-hold degradation",
    },
    "motor_failure": {
        "hazard_category": "PROPULSION",
        "hazard_description": "Motor/propeller thrust asymmetry or loss",
    },
    "battery_failure": {
        "hazard_category": "POWER",
        "hazard_description": "Battery/voltage related power degradation",
    },
    "control_loss": {
        "hazard_category": "CONTROL",
        "hazard_description": "Control link or command instability",
    },
    "sensor_fault": {
        "hazard_category": "SENSOR",
        "hazard_description": "Sensor reliability or calibration failure",
    },
}


# -----------------------------------------------------------------------------
# Classifier + deterministic extractors
# -----------------------------------------------------------------------------


class FAAClassifier:
    UAS_SIZE_TERMS = ["small", "medium", "large", "micro", "mini"]
    UAS_SHAPE_TERMS = ["quadcopter", "hexacopter", "fixed-wing", "fixed wing", "helicopter", "balloon", "multirotor"]
    UAS_COLOR_TERMS = ["black", "white", "red", "blue", "green", "gray", "grey", "silver", "yellow", "orange"]

    ACTUAL_FAILURE_KEYWORDS = [
        "operator stated",
        "operator reported",
        "malfunction",
        "crash",
        "crashed",
        "lost control",
        "out of control",
        "flyaway",
        "flew away",
        "runaway",
        "parachute",
        "chute deployed",
        "lost power",
        "motor failed",
        "unresponsive",
    ]

    HIGH_RISK_KEYWORDS = [
        "evasive action",
        "near miss",
        "nmac",
        "runway",
        "final approach",
        "departure",
        "same altitude",
        "within 50 feet",
        "within 100 feet",
    ]

    def classify(self, narrative: str) -> Tuple[str, str, float]:
        text = (narrative or "").lower()

        if any(k in text for k in self.ACTUAL_FAILURE_KEYWORDS):
            return "ACTUAL_FAILURE", self.detect_fault_type(narrative), 0.90

        altitude_m = self.parse_altitude_m(narrative)
        if altitude_m is not None and altitude_m > 457.2:  # 1500 ft
            return "HIGH_RISK_SIGHTING", self.detect_fault_type(narrative), 0.80

        if any(k in text for k in self.HIGH_RISK_KEYWORDS):
            return "HIGH_RISK_SIGHTING", self.detect_fault_type(narrative), 0.70

        return "NORMAL_SIGHTING", "none", 0.50

    def detect_fault_type(self, narrative: str) -> str:
        text = (narrative or "").lower()

        if any(k in text for k in ["gps", "navigation", "drift", "position"]):
            return "gps_loss"
        if any(k in text for k in ["motor", "propeller", "thrust", "esc"]):
            return "motor_failure"
        if any(k in text for k in ["battery", "voltage", "power"]):
            return "battery_failure"
        if any(k in text for k in ["control", "link", "signal", "rc"]):
            return "control_loss"
        if any(k in text for k in ["sensor", "imu", "gyro", "compass", "barometer"]):
            return "sensor_fault"

        altitude_m = self.parse_altitude_m(narrative)
        if altitude_m is not None and altitude_m > 300.0:
            return "gps_loss"

        return "gps_loss"

    def parse_altitude_m(self, narrative: str) -> Optional[float]:
        if not narrative:
            return None

        text = narrative.upper()

        # FL210 -> 21,000 ft
        fl_match = re.search(r"\bFL\s*(\d{2,3})\b", text)
        if fl_match:
            feet = int(fl_match.group(1)) * 100
            return round(feet * 0.3048, 3)

        patterns = [
            r"\bAT\s+([\d,]+)\s*(?:FEET|FT)\b",
            r"\b([\d,]+)\s*(?:FEET|FT)\b",
            r"\bALTITUDE\s+(?:OF\s+)?([\d,]+)\b",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            try:
                feet = int(m.group(1).replace(",", ""))
                return round(feet * 0.3048, 3)
            except ValueError:
                continue

        return None

    def parse_proximity_ft(self, narrative: str) -> Optional[float]:
        text = (narrative or "").upper()
        patterns = [
            r"\bWITHIN\s+([\d,]+)\s*(?:FEET|FT)\b",
            r"\b([\d,]+)\s*(?:FEET|FT)\s*(?:AWAY|FROM|BELOW|ABOVE)\b",
        ]

        distances: List[float] = []
        for pat in patterns:
            for m in re.finditer(pat, text):
                try:
                    distances.append(float(m.group(1).replace(",", "")))
                except ValueError:
                    continue

        return min(distances) if distances else None

    def build_regulatory_flags(self, narrative: str, altitude_m: Optional[float]) -> Dict[str, Any]:
        text = (narrative or "").lower()
        proximity_ft = self.parse_proximity_ft(narrative)
        altitude_violation = bool(altitude_m is not None and altitude_m > 121.92)
        high_certainty_altitude_violation = bool(altitude_m is not None and altitude_m > 152.4)  # 500 ft

        return {
            "part_107_51_altitude_violation": altitude_violation,
            "part_107_51_high_certainty_violation": high_certainty_altitude_violation,
            "part_107_31_vlos_indicator": any(k in text for k in ["lost sight", "out of sight", "beyond visual", "visual line"]),
            "part_89_remote_id_indicator": any(k in text for k in ["remote id", "unidentified", "no id", "identification"]),
            "close_approach_flag": bool(
                (proximity_ft is not None and proximity_ft <= 500.0)
                or ("near miss" in text)
                or ("nmac" in text)
                or ("evasive action" in text)
            ),
            "closest_proximity_ft": proximity_ft,
        }

    def extract_uas_descriptors(self, narrative: str) -> Dict[str, List[str]]:
        """Extract deterministic UAS descriptors (size/shape/color) from narrative text."""
        text = (narrative or "").lower()

        sizes = sorted({term for term in self.UAS_SIZE_TERMS if term in text})
        shapes = sorted({term for term in self.UAS_SHAPE_TERMS if term in text})
        colors = sorted({term for term in self.UAS_COLOR_TERMS if term in text})

        return {
            "sizes": sizes,
            "shapes": shapes,
            "colors": colors,
        }

    def build_physics_flags(self, narrative: str, altitude_m: Optional[float]) -> Dict[str, Any]:
        text = (narrative or "").lower()
        high_alt_proxy_required = bool(altitude_m is not None and altitude_m > 3048.0)  # 10,000 ft
        small_uas_descriptor = any(k in text for k in ["small", "toy", "quadcopter", "drone", "uas"])
        descriptors = self.extract_uas_descriptors(narrative)

        summary_parts: List[str] = []
        if descriptors["sizes"]:
            summary_parts.append("size=" + ",".join(descriptors["sizes"]))
        if descriptors["shapes"]:
            summary_parts.append("shape=" + ",".join(descriptors["shapes"]))
        if descriptors["colors"]:
            summary_parts.append("color=" + ",".join(descriptors["colors"]))
        physical_description_summary = "; ".join(summary_parts) if summary_parts else "unspecified"

        if high_alt_proxy_required and small_uas_descriptor:
            confidence = "LOW"
        elif high_alt_proxy_required:
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"

        return {
            "high_altitude_proxy_required": high_alt_proxy_required,
            "observation_confidence_score": confidence,
            "uas_descriptors": descriptors,
            "physical_description_summary": physical_description_summary,
        }


# -----------------------------------------------------------------------------
# Processor
# -----------------------------------------------------------------------------


class FAAProcessor:
    def __init__(self, config: FAAConfig):
        self.config = config
        self.classifier = FAAClassifier()
        self.schema_diagnostics: List[Dict[str, Any]] = []
        self.stats = {
            "total_raw": 0,
            "ACTUAL_FAILURE": 0,
            "HIGH_RISK_SIGHTING": 0,
            "NORMAL_SIGHTING": 0,
            "by_fault_type": Counter(),
            "by_file": Counter(),
        }

    def run(self) -> List[Dict[str, Any]]:
        logger.info("=" * 60)
        logger.info("FAA DATA PROCESSING PIPELINE")
        logger.info("=" * 60)

        excel_files = sorted([p for p in self.config.raw_data_dir.glob("*.xlsx") if not p.name.startswith("~$")])
        logger.info("Found %d Excel files in %s", len(excel_files), self.config.raw_data_dir)

        incidents: List[Dict[str, Any]] = []
        for file_path in excel_files:
            incidents.extend(self._process_file(file_path))

        incidents.sort(key=lambda x: (0 if x["classification"] == "ACTUAL_FAILURE" else 1, x["report_id"]))
        self._save_outputs(incidents)
        self._print_summary(incidents)
        return incidents

    def _scan_schema(self, file_path: Path) -> None:
        try:
            header_df = pd.read_excel(file_path, nrows=0)
            normalized = [str(c).strip().lower() for c in header_df.columns]
            target = set(TARGET_INPUT_COLUMNS)
            missing = sorted(target - set(normalized))
            unexpected = sorted(set(normalized) - target)
            phantom = [c for c in header_df.columns if re.match(r"^Column\d+$", str(c).strip(), re.IGNORECASE)]

            self.schema_diagnostics.append(
                {
                    "source_file": file_path.name,
                    "column_count": len(header_df.columns),
                    "missing_target_columns": missing,
                    "unexpected_columns_count": len(unexpected),
                    "phantom_columns_count": len(phantom),
                }
            )
        except Exception as exc:
            self.schema_diagnostics.append(
                {
                    "source_file": file_path.name,
                    "schema_scan_error": str(exc),
                }
            )

    def _find_col(self, columns: List[str], candidates: List[str]) -> Optional[str]:
        lowered = {c.lower(): c for c in columns}
        for candidate in candidates:
            if candidate in lowered:
                return lowered[candidate]
        return None

    def _process_file(self, file_path: Path) -> List[Dict[str, Any]]:
        logger.info("Processing: %s", file_path.name)
        self._scan_schema(file_path)

        try:
            df = pd.read_excel(
                file_path,
                usecols=lambda c: str(c).strip().lower() in TARGET_INPUT_COLUMNS,
            )
        except Exception as exc:
            logger.error("  ERROR reading %s: %s", file_path.name, exc)
            return []

        df.columns = [str(c).strip() for c in df.columns]
        summary_col = self._find_col(list(df.columns), SUMMARY_CANDIDATES)
        date_col = self._find_col(list(df.columns), DATE_CANDIDATES)
        city_col = self._find_col(list(df.columns), CITY_CANDIDATES)
        state_col = self._find_col(list(df.columns), STATE_CANDIDATES)

        if not summary_col:
            logger.warning("  No summary-like column found in %s", file_path.name)
            return []

        out: List[Dict[str, Any]] = []
        quarter = file_path.stem.replace("FAA_", "")

        for idx, row in df.iterrows():
            self.stats["total_raw"] += 1

            narrative = str(row.get(summary_col, "") or "").strip()
            if len(narrative) < 10:
                continue

            classification, fault_type, conf = self.classifier.classify(narrative)
            self.stats[classification] += 1
            if classification == "NORMAL_SIGHTING":
                continue
            if classification == "HIGH_RISK_SIGHTING" and not self.config.include_high_risk:
                continue

            date_str = self._format_date(row.get(date_col, "") if date_col else "")
            city = str(row.get(city_col, "") or "").strip().upper() if city_col else ""
            state = str(row.get(state_col, "") or "").strip().upper() if state_col else ""

            altitude_m = self.classifier.parse_altitude_m(narrative)
            regulatory_flags = self.classifier.build_regulatory_flags(narrative, altitude_m)
            physics_flags = self.classifier.build_physics_flags(narrative, altitude_m)

            fault_meta = FAULT_META.get(fault_type, FAULT_META["gps_loss"])

            report_id = f"{file_path.stem}_{idx + 1}"
            is_observational = classification == "HIGH_RISK_SIGHTING"

            rec = {
                "report_id": report_id,
                "source_file": file_path.name,
                "source_row_index": int(idx + 1),
                "source_quarter": quarter,
                "date": date_str,
                "city": city,
                "state": state,
                "description": narrative,
                "classification": classification,
                "fault_type": fault_type,
                "classification_confidence": float(conf),
                "fault_label_trust": "LOW" if is_observational else "HIGH",
                "fault_label_source": "heuristic_observation" if is_observational else "heuristic_failure_evidence",
                "llm_fault_hint_allowed": classification == "ACTUAL_FAILURE",
                "altitude_m": altitude_m,
                "hazard_category": fault_meta["hazard_category"],
                "hazard_description": fault_meta["hazard_description"],
                "regulatory_flags": regulatory_flags,
                "physics_flags": physics_flags,
            }

            out.append(rec)
            self.stats["by_fault_type"][fault_type] += 1
            self.stats["by_file"][file_path.name] += 1

        logger.info("  -> Extracted %d simulatable incidents", len(out))
        return out

    def _format_date(self, value: Any) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _save_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _save_outputs(self, incidents: List[Dict[str, Any]]) -> None:
        logger.info("")
        logger.info("=" * 60)
        logger.info("GENERATING OUTPUT FILES")
        logger.info("=" * 60)

        now = datetime.now().isoformat()

        full = {
            "version": "2.0",
            "generated_at": now,
            "description": "FAA incidents processed from raw Excel with deterministic physics/regulatory flags",
            "source_root": str(self.config.raw_data_dir.resolve()),
            "statistics": {
                "total_raw_records": self.stats["total_raw"],
                "simulatable_total": len(incidents),
            },
            "incidents": incidents,
        }
        self._save_json(self.config.output_dir / "faa_reports.json", full)

        simulatable = {
            "version": "2.0",
            "generated_at": now,
            "description": "PX4-simulatable FAA incidents",
            "original_total": self.stats["total_raw"],
            "simulatable_total": len(incidents),
            "filter_rate": f"{len(incidents) / max(self.stats['total_raw'], 1) * 100:.1f}%",
            "incidents": incidents,
        }
        self._save_json(self.config.output_dir / "faa_simulatable.json", simulatable)

        schema = {
            "generated_at": now,
            "source_root": str(self.config.raw_data_dir.resolve()),
            "target_columns": sorted(TARGET_INPUT_COLUMNS),
            "files": self.schema_diagnostics,
        }
        self._save_json(self.config.output_dir / "faa_schema_diagnostics.json", schema)

        actual = [r for r in incidents if r.get("classification") == "ACTUAL_FAILURE"]
        actual_payload = {
            "version": "2.0",
            "generated_at": now,
            "description": "Confirmed/strongly-indicated FAA failure incidents",
            "total_failures": len(actual),
            "incidents": actual,
        }
        self._save_json(self.config.output_dir / "faa_actual_failures.json", actual_payload)

        high_risk = [r for r in incidents if r.get("classification") == "HIGH_RISK_SIGHTING"]
        high_risk_payload = {
            "version": "2.0",
            "generated_at": now,
            "description": "High-risk observational sightings",
            "total_sightings": len(high_risk),
            "incidents": high_risk,
        }
        self._save_json(self.config.output_dir / "faa_high_risk_sightings.json", high_risk_payload)

        logger.info(">>>>>  Saved: %s (%d incidents)", self.config.output_dir / "faa_reports.json", len(incidents))
        logger.info(">>>>>  Saved: %s (%d incidents)", self.config.output_dir / "faa_simulatable.json", len(incidents))
        logger.info(">>>>>  Saved: %s (%d files scanned)", self.config.output_dir / "faa_schema_diagnostics.json", len(self.schema_diagnostics))
        logger.info(">>>>>  Saved: %s (%d ACTUAL_FAILURE incidents)", self.config.output_dir / "faa_actual_failures.json", len(actual))
        logger.info(">>>>>  Saved: %s (%d HIGH_RISK_SIGHTING incidents)", self.config.output_dir / "faa_high_risk_sightings.json", len(high_risk))

    def _print_summary(self, incidents: List[Dict[str, Any]]) -> None:
        logger.info("")
        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info("Total raw records: %d", self.stats["total_raw"])
        logger.info("ACTUAL_FAILURE: %d", self.stats["ACTUAL_FAILURE"])
        logger.info("HIGH_RISK_SIGHTING: %d", self.stats["HIGH_RISK_SIGHTING"])
        logger.info("NORMAL_SIGHTING: %d", self.stats["NORMAL_SIGHTING"])
        logger.info("Simulatable total: %d", len(incidents))
        logger.info("By fault type (internal classification):")
        for ftype, count in self.stats["by_fault_type"].most_common():
            logger.info("  %s: %d", ftype, count)
        logger.info(">>>>>  Data ready for AeroGuardian pipeline!")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process raw FAA Excel files into AeroGuardian upgraded datasets")
    parser.add_argument("--input", "-i", type=Path, default=Path("data/raw/faa"))
    parser.add_argument("--output", "-o", type=Path, default=Path("data/new_data/faa"))
    parser.add_argument("--exclude-high-risk", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    config = FAAConfig(
        raw_data_dir=args.input,
        output_dir=args.output,
        include_high_risk=not args.exclude_high_risk,
        verbose=args.verbose,
    )

    try:
        FAAProcessor(config).run()
        return 0
    except Exception as exc:
        logger.exception("Processing failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
