"""
FAA UAS Sighting Report — Deep Analysis Script
================================================
Author: AeroGuardian Team
Date: 2026-03-11
Purpose: DASC 2026 Conference Paper — Data Analysis Phase

Reads the ORIGINAL FAA Excel quarterly files directly (not pre-processed JSON)
and performs a comprehensive, publication-quality analysis including:
  1. Column schema discovery and data profiling
  2. Temporal distribution (reports per quarter, per year)
  3. Altitude extraction and distribution (Watters 2023 comparison)
  4. UAV type identification from narrative text
  5. Close-approach / evasive-action extraction
  6. Fault/incident keyword detection
  7. PX4 Gazebo simulatability assessment
  8. Scenario generation for each simulatable report
  9. Summary statistics (CSV + JSON output)

Reference: Watters (2023), "Preliminary Analysis of FAA UAS Sighting Reports",
           AIAA, 1,317 reports from Jul 2020 – Mar 2021.

Usage:
    python src/analysis/faa_analysis.py
    python src/analysis/faa_analysis.py --output-dir outputs/faa_analysis
    python src/analysis/faa_analysis.py --verbose
"""

import os
import re
import sys
import json
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("AeroGuardian.FAAAnalysis")

# ---------------------------------------------------------------------------
# Constants — keyword dictionaries for narrative text mining
# ---------------------------------------------------------------------------

# UAV model patterns (case-insensitive regex)
UAV_MODEL_PATTERNS = {
    # DJI consumer/prosumer
    "DJI Phantom":    re.compile(r"\b(DJI\s*)?PHANTOM\s*\d?\b", re.IGNORECASE),
    "DJI Mavic":      re.compile(r"\b(DJI\s*)?MAVIC\s*\w*\b", re.IGNORECASE),
    "DJI Inspire":    re.compile(r"\b(DJI\s*)?INSPIRE\s*\d?\b", re.IGNORECASE),
    "DJI Matrice":    re.compile(r"\b(DJI\s*)?MATRICE\s*\w*\b", re.IGNORECASE),
    "DJI Mini":       re.compile(r"\b(DJI\s*)?MINI\s*\d?\b", re.IGNORECASE),
    "DJI Air":        re.compile(r"\b(DJI\s*)?AIR\s*\d?S?\b", re.IGNORECASE),
    # Enterprise
    "Skydio":         re.compile(r"\bSKYDIO\s*\w*\b", re.IGNORECASE),
    "Autel":          re.compile(r"\bAUTEL\s*\w*\b", re.IGNORECASE),
    "Parrot":         re.compile(r"\bPARROT\s*\w*\b", re.IGNORECASE),
    # Commercial delivery
    "Amazon MK30":    re.compile(r"\b(AMAZON|MK\s*30)\b", re.IGNORECASE),
    "Wing":           re.compile(r"\bWING\s*(DELIVERY|DRONE)?\b", re.IGNORECASE),
    # Military
    "RQ-7B Shadow":   re.compile(r"\bRQ[\-\s]?7\w?\b", re.IGNORECASE),
    "MQ-9 Reaper":    re.compile(r"\bMQ[\-\s]?9\b", re.IGNORECASE),
    "MQ-1C Gray Eagle": re.compile(r"\bMQ[\-\s]?1\w?\b", re.IGNORECASE),
    "RQ-4 Global Hawk": re.compile(r"\bRQ[\-\s]?4\b", re.IGNORECASE),
    "ScanEagle":      re.compile(r"\bSCAN\s*EAGLE\b", re.IGNORECASE),
}

# Airframe type patterns
AIRFRAME_PATTERNS = {
    "quadcopter":  re.compile(r"\b(QUAD[\-\s]?COPTER|QUAD[\-\s]?ROTOR|4[\-\s]?ROTOR)\b", re.IGNORECASE),
    "hexacopter":  re.compile(r"\b(HEX[\-\s]?COPTER|HEX[\-\s]?ROTOR|6[\-\s]?ROTOR)\b", re.IGNORECASE),
    "octocopter":  re.compile(r"\b(OCTO[\-\s]?COPTER|OCTO[\-\s]?ROTOR|8[\-\s]?ROTOR)\b", re.IGNORECASE),
    "fixed_wing":  re.compile(r"\bFIXED[\-\s]?WING\b", re.IGNORECASE),
    "helicopter_style": re.compile(r"\bHELI(COPTER)?[\-\s]?STYLE\b", re.IGNORECASE),
    "multirotor":  re.compile(r"\bMULTI[\-\s]?ROTOR\b", re.IGNORECASE),
    "balloon":     re.compile(r"\bBALLOON\b", re.IGNORECASE),
}

# Fault / failure keyword patterns
FAULT_KEYWORDS = {
    "motor_failure": re.compile(
        r"\b(ENGINE\s+FAIL|MOTOR\s+FAIL|PROPELLER\s+(FAIL|BROKE|LOST)|PROP\s+FAIL|"
        r"THRUST\s+LOSS|ROTOR\s+FAIL|ESC\s+FAIL|LOST\s+PROPULSION)\b", re.IGNORECASE),
    "control_loss": re.compile(
        r"\b(LOST?\s+CONTROL|UNCONTROLLED|FLYAWAY|FLY[\-\s]?AWAY|RUNAWAY|"
        r"NOT\s+RESPOND|UNABLE\s+TO\s+(MAINTAIN\s+)?CONTROL|ERRATIC|"
        r"RC\s+FAIL|CONTROL\s+LINK\s+LOST?)\b", re.IGNORECASE),
    "gps_loss": re.compile(
        r"\b(GPS\s+(FAIL|LOST?|ERROR|DENIED|SPOOF)|POSITION\s+HOLD\s+FAIL|"
        r"NAVIGATION\s+FAIL|DRIFTED?|GEOFENCE\s+BREACH)\b", re.IGNORECASE),
    "battery_failure": re.compile(
        r"\b(BATTERY\s+(FAIL|LOW|DEAD|DEPLETED)|LOW\s+VOLTAGE|POWER\s+LOSS|"
        r"LOST?\s+POWER|POWER\s+FAIL|LIPO\s+FAIL)\b", re.IGNORECASE),
    "crash": re.compile(
        r"\b(CRASH(ED|ING)?|STRUCK|HIT\s+(A\s+)?|COLLID(ED|SION)|IMPACT(ED)?|"
        r"WENT\s+DOWN|FELL|DROPPED|DESTROYED)\b", re.IGNORECASE),
    "parachute_deployed": re.compile(
        r"\b(PARACHUTE\s+(DEPLOY|ACTIVAT)|CHUTE\s+DEPLOY)\b", re.IGNORECASE),
    "fire": re.compile(
        r"\b(CAUGHT?\s+FIRE|POST[\-\s]?CRASH\s+FIRE|BURN(ED|ING)?|FIRE)\b", re.IGNORECASE),
}

# Close approach / evasive action patterns
CLOSE_APPROACH_PATTERN = re.compile(
    r"\b(\d+)\s*(FEET|FT|FOOT)\s*(OF|FROM|AWAY|BELOW|ABOVE)?\b", re.IGNORECASE)
EVASIVE_ACTION_PATTERN = re.compile(
    r"\b(EVASIVE\s+(ACTION|MANEUVER)|TOOK\s+EVASIVE|NMAC|NEAR[\-\s]?MISS|"
    r"TCAS\s+RA|DEVIATED|AVOIDED)\b", re.IGNORECASE)

# Altitude extraction pattern (from narrative text)
ALTITUDE_PATTERN = re.compile(
    r"(?:AT|ALTITUDE|ALT|LEVEL|OPERATING\s+AT|OBSERVED\s+AT|FLYING\s+AT|"
    r"REPORTED\s+(?:A\s+)?(?:UAS\s+)?(?:AT\s+)?|WHILE\s+\w+\s+BOUND\s+AT\s+)"
    r"\s*(\d[\d,]*)\s*(FEET|FT|FOOT)\b", re.IGNORECASE)

# PX4 vehicle model mapping
PX4_MODEL_MAP = {
    "quadcopter":   {"px4_model": "iris",          "simulatable": True,  "notes": "Default PX4 quad, close to DJI consumer drones"},
    "hexacopter":   {"px4_model": "typhoon_h480",  "simulatable": True,  "notes": "Yuneec Typhoon H480 hex model in PX4"},
    "octocopter":   {"px4_model": "iris",          "simulatable": True,  "notes": "Approximated with iris (parameter-tuned for heavier craft)"},
    "multirotor":   {"px4_model": "iris",          "simulatable": True,  "notes": "Default multirotor assumed quadcopter"},
    "fixed_wing":   {"px4_model": "plane",         "simulatable": True,  "notes": "PX4 fixed-wing standard plane model"},
    "military_large": {"px4_model": None,          "simulatable": False, "notes": "Military MALE/HALE UAV, not simulatable with PX4 consumer stack"},
    "balloon":      {"px4_model": None,            "simulatable": False, "notes": "Balloon/lighter-than-air, not a UAV"},
    "unknown":      {"px4_model": "iris",          "simulatable": True,  "notes": "Type unknown — default to quadcopter (most common in FAA data per Watters 2023)"},
}


# ---------------------------------------------------------------------------
# Core Analysis Functions
# ---------------------------------------------------------------------------

def read_all_excel_files(data_dir: str) -> Tuple[List[Dict], List[str]]:
    """
    Read all FAA quarterly Excel files from the raw data directory.
    
    Returns:
        Tuple of (list of record dicts, list of column names)
    """
    import pandas as pd
    
    data_path = Path(data_dir)
    excel_files = sorted(data_path.glob("FAA_*.xlsx"))
    
    if not excel_files:
        raise FileNotFoundError(f"No FAA Excel files found in {data_dir}")
    
    all_records = []
    all_columns = set()
    file_stats = []
    
    for fpath in excel_files:
        fname = fpath.name
        logger.info(f"Reading: {fname}")
        
        df = None
        # Try multiple reading strategies for robustness
        for attempt, read_kwargs in enumerate([
            {"engine": "openpyxl"},
            {"engine": "openpyxl", "sheet_name": 0},
            {"engine": "openpyxl", "dtype": str},
        ]):
            try:
                df = pd.read_excel(fpath, **read_kwargs)
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"  All read attempts failed for {fname}: {e}")
                else:
                    logger.warning(f"  Attempt {attempt+1} failed for {fname}, retrying...")
        
        if df is None:
            file_stats.append({
                "filename": fname,
                "quarter": fname.replace("FAA_", "").replace(".xlsx", ""),
                "row_count": 0,
                "columns": [],
                "error": "All read attempts failed",
            })
            continue
        
        try:
            # Prune phantom columns (some FAA files like Apr2025 have 16K+ empty columns)
            real_cols = [c for c in df.columns if not (
                isinstance(c, str) and re.match(r'^Column\d+$', c)
            )]
            if len(real_cols) < len(df.columns):
                dropped = len(df.columns) - len(real_cols)
                logger.warning(f"  Pruned {dropped} phantom columns from {fname}")
                df = df[real_cols]
            # Also drop columns that are entirely NaN
            df = df.dropna(axis=1, how='all')
            
            # Track columns
            cols = list(df.columns)
            all_columns.update(cols)
            
            # Extract quarter info from filename
            # Format: FAA_MonYYYY-MonYYYY.xlsx
            quarter_match = re.match(r"FAA_(\w+\d{4})-(\w+\d{4})\.xlsx", fname)
            quarter_label = fname.replace("FAA_", "").replace(".xlsx", "") if quarter_match else fname
            
            row_count = len(df)
            file_stats.append({
                "filename": fname,
                "quarter": quarter_label,
                "row_count": row_count,
                "columns": cols,
            })
            
            logger.info(f"  -> {row_count} rows, {len(cols)} columns")
            
            # Convert each row to dict
            for idx, row in df.iterrows():
                record = row.to_dict()
                # Add metadata
                record["_source_file"] = fname
                record["_source_quarter"] = quarter_label
                record["_source_row"] = idx
                record["_report_id"] = f"{fname.replace('.xlsx', '')}_{idx}"
                all_records.append(record)
                
        except Exception as e:
            logger.error(f"Failed to process {fname}: {e}")
            file_stats.append({
                "filename": fname,
                "quarter": "ERROR",
                "row_count": 0,
                "columns": [],
                "error": str(e),
            })
    
    logger.info(f"Total files read: {len(excel_files)}")
    logger.info(f"Total records: {len(all_records)}")
    logger.info(f"All columns found: {sorted(all_columns)}")
    
    return all_records, sorted(all_columns), file_stats


def find_description_column(columns: List[str]) -> Optional[str]:
    """Find the narrative description column from the Excel headers."""
    # Common column names used by FAA across different quarterly releases
    candidates = [
        "EventDescription", "Event Description", "DESCRIPTION",
        "Summary", "SUMMARY", "Narrative", "NARRATIVE",
        "Event_Description", "event_description",
        "Comments", "COMMENTS", "Details", "DETAILS",
        "EventSummary", "Event Summary",
    ]
    for c in candidates:
        for col in columns:
            if col and str(col).strip().lower() == c.lower():
                return col
    # Fallback: find any column containing "descr" or "summar" or "narrat"
    for col in columns:
        if col and any(kw in str(col).lower() for kw in ["descr", "summar", "narrat", "comment", "detail"]):
            return col
    return None


def find_date_column(columns: List[str]) -> Optional[str]:
    """Find the date column."""
    candidates = ["EventDate", "Event Date", "DATE", "Date", "event_date",
                   "EventDateTime", "Event Date/Time", "IncidentDate"]
    for c in candidates:
        for col in columns:
            if col and str(col).strip().lower() == c.lower():
                return col
    for col in columns:
        if col and "date" in str(col).lower():
            return col
    return None


def find_city_column(columns: List[str]) -> Optional[str]:
    """Find the city column."""
    for col in columns:
        if col and str(col).strip().lower() in ["city", "eventcity", "event city", "location"]:
            return col
    return None


def find_state_column(columns: List[str]) -> Optional[str]:
    """Find the state column."""
    for col in columns:
        if col and str(col).strip().lower() in ["state", "eventstate", "event state"]:
            return col
    return None


def extract_altitude_from_text(text: str) -> Optional[float]:
    """
    Extract altitude in feet from narrative text.
    Returns altitude in feet (AGL) or None if not found.
    
    Uses the same screening approach as Watters (2023):
    valid altitude, confirmation of UAS AGL.
    """
    if not text or not isinstance(text, str):
        return None
    
    matches = ALTITUDE_PATTERN.findall(text)
    if not matches:
        return None
    
    # Take the first valid altitude
    for num_str, _ in matches:
        try:
            alt_ft = float(num_str.replace(",", ""))
            # Sanity check: reasonable drone altitude range 0 – 60,000 ft
            if 0 < alt_ft <= 60000:
                return alt_ft
        except ValueError:
            continue
    return None


def identify_uav_model(text: str) -> Dict[str, Any]:
    """
    Identify UAV model from narrative text.
    Returns dict with model name, airframe type, and confidence.
    """
    if not text or not isinstance(text, str):
        return {"model": "unknown", "airframe": "unknown", "confidence": 0.0}
    
    # Check specific models first
    for model_name, pattern in UAV_MODEL_PATTERNS.items():
        if pattern.search(text):
            # Determine if military
            is_military = any(m in model_name for m in ["RQ-", "MQ-", "ScanEagle", "Global Hawk", "Gray Eagle"])
            if is_military:
                airframe = "military_large"
            elif "Phantom" in model_name or "Mavic" in model_name or "Mini" in model_name or "Air" in model_name:
                airframe = "quadcopter"
            elif "Matrice" in model_name:
                airframe = "quadcopter"  # Most Matrice are quads (600/210/30T)
            elif "Inspire" in model_name:
                airframe = "quadcopter"
            elif "Skydio" in model_name:
                airframe = "quadcopter"
            elif "Amazon" in model_name or "MK30" in model_name:
                airframe = "hexacopter"
            else:
                airframe = "unknown"
            return {"model": model_name, "airframe": airframe, "confidence": 0.9}
    
    # Check generic airframe descriptions
    for airframe_name, pattern in AIRFRAME_PATTERNS.items():
        if pattern.search(text):
            return {"model": f"generic_{airframe_name}", "airframe": airframe_name, "confidence": 0.7}
    
    return {"model": "unknown", "airframe": "unknown", "confidence": 0.0}


def detect_faults(text: str) -> Dict[str, bool]:
    """Detect fault/incident keywords in narrative text."""
    if not text or not isinstance(text, str):
        return {k: False for k in FAULT_KEYWORDS}
    
    results = {}
    for fault_name, pattern in FAULT_KEYWORDS.items():
        results[fault_name] = bool(pattern.search(text))
    return results


def classify_incident(text: str, faults: Dict[str, bool]) -> Dict[str, Any]:
    """
    Classify the incident based on detected keywords.
    Returns classification, primary fault type, and confidence.
    """
    if not text or not isinstance(text, str):
        return {"classification": "SIGHTING_ONLY", "primary_fault": None, "confidence": 0.3}
    
    # Priority ordering for fault classification
    fault_priority = ["motor_failure", "battery_failure", "control_loss", "gps_loss"]
    
    detected_faults = [f for f in fault_priority if faults.get(f, False)]
    has_crash = faults.get("crash", False)
    has_parachute = faults.get("parachute_deployed", False)
    has_fire = faults.get("fire", False)
    
    if detected_faults:
        if has_crash or has_fire:
            return {
                "classification": "CONFIRMED_FAILURE",
                "primary_fault": detected_faults[0],
                "confidence": 0.90,
                "all_faults": detected_faults,
            }
        else:
            return {
                "classification": "PROBABLE_FAILURE",
                "primary_fault": detected_faults[0],
                "confidence": 0.75,
                "all_faults": detected_faults,
            }
    elif has_crash:
        return {
            "classification": "CONFIRMED_FAILURE",
            "primary_fault": "control_loss",  # Crash without explicit fault → general control loss
            "confidence": 0.80,
            "all_faults": ["crash"],
        }
    elif has_parachute:
        return {
            "classification": "PROBABLE_FAILURE",
            "primary_fault": "motor_failure",
            "confidence": 0.70,
            "all_faults": ["parachute_deployed"],
        }
    else:
        # No fault keywords — this is a sighting (altitude/proximity) report
        # For AeroGuardian: these are STILL simulatable as "behavioral scenarios"
        return {
            "classification": "BEHAVIORAL_SCENARIO",
            "primary_fault": "behavioral",
            "confidence": 0.60,
            "all_faults": [],
            "note": "No explicit failure — can simulate observed flight behavior for pre-flight risk assessment"
        }


def extract_close_approach(text: str) -> Dict[str, Any]:
    """Extract close-approach distance and evasive action from text."""
    if not text or not isinstance(text, str):
        return {"close_approach": False, "distance_ft": None, "evasive_action": False}
    
    # Check for evasive action
    evasive = bool(EVASIVE_ACTION_PATTERN.search(text))
    
    # Check for distance mentions (within context of proximity to aircraft)
    distances = []
    for match in CLOSE_APPROACH_PATTERN.finditer(text):
        try:
            dist = float(match.group(1).replace(",", ""))
            if 0 < dist <= 5000:  # Reasonable close-approach range
                distances.append(dist)
        except ValueError:
            pass
    
    min_dist = min(distances) if distances else None
    close = min_dist is not None and min_dist <= 500  # FAA close approach = within 500 ft
    
    return {
        "close_approach": close or evasive,
        "distance_ft": min_dist,
        "evasive_action": evasive,
    }


def assess_px4_simulatability(uav_info: Dict, incident_class: Dict,
                               altitude_ft: Optional[float]) -> Dict[str, Any]:
    """
    Assess whether this report is simulatable with PX4 SITL + Gazebo.
    
    A report is fully simulatable if:
      1. The airframe is representable in PX4 (quadcopter, hex, fixed-wing)
      2. The altitude is within PX4 simulation range (< 500m / ~1,640 ft for realism)
      3. A fault scenario can be defined for simulation
    
    Even "sighting-only" reports are simulatable as behavioral scenarios
    (fly the observed behavior and generate telemetry for risk assessment).
    """
    airframe = uav_info.get("airframe", "unknown")
    px4_info = PX4_MODEL_MAP.get(airframe, PX4_MODEL_MAP["unknown"])
    
    # Altitude assessment
    sim_altitude_m = 50.0  # Default if not reported
    if altitude_ft is not None:
        # Use exact reported altitude for realistic safety reporting and telemetry
        sim_altitude_m = float(altitude_ft * 0.3048)
    
    # Overall simulatability
    is_simulatable = px4_info["simulatable"]
    
    # Determine simulation scenario type
    primary_fault = incident_class.get("primary_fault")
    if primary_fault and primary_fault != "behavioral":
        scenario_type = "FAULT_INJECTION"
        px4_fault_cmd = {
            "motor_failure": "commander failure motor_failure",
            "gps_loss": "commander failure gps off",
            "control_loss": "commander failure rc off",
            "battery_failure": "commander failure battery_failure",
        }.get(primary_fault, None)
    else:
        scenario_type = "BEHAVIORAL_FLIGHT"
        px4_fault_cmd = None  # No fault injection — simulate normal flight at observed conditions
    
    return {
        "simulatable": is_simulatable,
        "px4_model": px4_info["px4_model"],
        "px4_notes": px4_info["notes"],
        "scenario_type": scenario_type,
        "px4_fault_cmd": px4_fault_cmd,
        "sim_altitude_m": round(sim_altitude_m, 1),
    }


def build_scenario_config(record: Dict, analysis: Dict) -> Dict:
    """
    Build a PX4 simulation scenario configuration from an analyzed report.
    This can be fed directly to AeroGuardian's batch processing mode.
    """
    sim = analysis["simulatability"]
    if not sim["simulatable"]:
        return None
    
    city = str(analysis.get("city", "Unknown"))
    state = str(analysis.get("state", ""))
    
    return {
        "report_id": analysis["report_id"],
        "source_file": analysis.get("source_file", ""),
        "date": analysis.get("date", ""),
        "city": city,
        "state": state,
        "description": analysis.get("description", "")[:500],
        "incident_type": analysis["classification"]["classification"],
        "fault_type": analysis["classification"].get("primary_fault", "behavioral"),
        "hazard_category": {
            "motor_failure": "PROPULSION",
            "gps_loss": "NAVIGATION",
            "control_loss": "CONTROL",
            "battery_failure": "POWER",
            "behavioral": "BEHAVIORAL",
        }.get(analysis["classification"].get("primary_fault", "behavioral"), "BEHAVIORAL"),
        "simulation_config": {
            "px4_model": sim["px4_model"],
            "altitude_m": sim["sim_altitude_m"],
            "scenario_type": sim["scenario_type"],
            "fault_injection": {
                "fault_type": analysis["classification"].get("primary_fault"),
                "onset_sec": 60,
                "severity": 1.0,
            } if sim["scenario_type"] == "FAULT_INJECTION" else None,
        },
        "uav_model": analysis["uav_identification"]["model"],
        "airframe": analysis["uav_identification"]["airframe"],
        "altitude_ft_reported": analysis.get("altitude_ft"),
        "close_approach": analysis["proximity"]["close_approach"],
        "evasive_action": analysis["proximity"]["evasive_action"],
    }


# ---------------------------------------------------------------------------
# Main Analysis Pipeline
# ---------------------------------------------------------------------------

def run_analysis(data_dir: str, output_dir: str, verbose: bool = False):
    """
    Main analysis function. Reads all Excel files, analyzes every record,
    and produces JSON + CSV output.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # ===== STEP 1: Read all Excel files =====
    logger.info("=" * 70)
    logger.info("  STEP 1: Reading Raw FAA Excel Files")
    logger.info("=" * 70)
    
    records, columns, file_stats = read_all_excel_files(data_dir)
    
    # Save file statistics
    with open(output_path / "01_file_statistics.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_files": len(file_stats),
            "total_records": len(records),
            "all_columns": columns,
            "files": file_stats,
        }, f, indent=2, default=str)
    
    logger.info(f"  Saved file statistics to 01_file_statistics.json")
    
    # ===== STEP 2: Identify key columns =====
    logger.info("")
    logger.info("=" * 70)
    logger.info("  STEP 2: Column Schema Discovery")
    logger.info("=" * 70)
    
    desc_col = find_description_column(columns)
    date_col = find_date_column(columns)
    city_col = find_city_column(columns)
    state_col = find_state_column(columns)
    
    schema_info = {
        "description_column": desc_col,
        "date_column": date_col,
        "city_column": city_col,
        "state_column": state_col,
        "all_columns": columns,
        "note": "Columns auto-discovered from Excel headers",
    }
    logger.info(f"  Description col: {desc_col}")
    logger.info(f"  Date col: {date_col}")
    logger.info(f"  City col: {city_col}")
    logger.info(f"  State col: {state_col}")
    
    if not desc_col:
        logger.warning("  ⚠ Could not find description column! Trying to use the first text column...")
        # Fallback: find first column with long text
        for col in columns:
            for rec in records[:10]:
                val = rec.get(col)
                if val and isinstance(val, str) and len(val) > 50:
                    desc_col = col
                    schema_info["description_column"] = desc_col
                    schema_info["note"] = f"Description column auto-detected as '{desc_col}' (first long text column)"
                    break
            if desc_col:
                break
    
    with open(output_path / "02_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema_info, f, indent=2, default=str)
    
    # ===== STEP 3: Analyze every record =====
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  STEP 3: Analyzing {len(records)} Records")
    logger.info("=" * 70)
    
    analyzed_records = []
    
    # Counters for summary
    counters = {
        "total": len(records),
        "by_classification": Counter(),
        "by_fault_type": Counter(),
        "by_airframe": Counter(),
        "by_uav_model": Counter(),
        "by_quarter": Counter(),
        "altitude_distribution": {
            "≤400ft (legal)": 0,
            "401-1400ft": 0,
            "1401-4100ft": 0,
            "4101-8200ft": 0,
            ">8200ft": 0,
            "not_reported": 0,
        },
        "close_approaches": 0,
        "evasive_actions": 0,
        "simulatable": 0,
        "fault_injection_scenarios": 0,
        "behavioral_scenarios": 0,
        "not_simulatable": 0,
    }
    
    for i, rec in enumerate(records):
        if verbose and i % 500 == 0:
            logger.info(f"  Processing record {i+1}/{len(records)}...")
        
        # Get text fields
        description = str(rec.get(desc_col, "")) if desc_col else ""
        date_val = rec.get(date_col, "") if date_col else ""
        city_val = str(rec.get(city_col, "")) if city_col else ""
        state_val = str(rec.get(state_col, "")) if state_col else ""
        
        # Clean nan values
        if description == "nan":
            description = ""
        if city_val == "nan":
            city_val = ""
        if state_val == "nan":
            state_val = ""
        
        report_id = rec.get("_report_id", f"UNKNOWN_{i}")
        
        # Analysis pipeline
        altitude_ft = extract_altitude_from_text(description)
        uav_info = identify_uav_model(description)
        faults = detect_faults(description)
        classification = classify_incident(description, faults)
        proximity = extract_close_approach(description)
        simulatability = assess_px4_simulatability(uav_info, classification, altitude_ft)
        
        analysis = {
            "report_id": report_id,
            "source_file": rec.get("_source_file", ""),
            "source_quarter": rec.get("_source_quarter", ""),
            "date": str(date_val) if date_val else "",
            "city": city_val,
            "state": state_val,
            "description": description[:500],
            "altitude_ft": altitude_ft,
            "altitude_m": round(altitude_ft * 0.3048, 1) if altitude_ft else None,
            "uav_identification": uav_info,
            "faults_detected": faults,
            "classification": classification,
            "proximity": proximity,
            "simulatability": simulatability,
        }
        analyzed_records.append(analysis)
        
        # Update counters
        counters["by_classification"][classification["classification"]] += 1
        if classification.get("primary_fault"):
            counters["by_fault_type"][classification["primary_fault"]] += 1
        counters["by_airframe"][uav_info["airframe"]] += 1
        if uav_info["model"] != "unknown":
            counters["by_uav_model"][uav_info["model"]] += 1
        counters["by_quarter"][rec.get("_source_quarter", "UNKNOWN")] += 1
        
        # Altitude distribution (Watters 2023 comparison buckets)
        if altitude_ft is None:
            counters["altitude_distribution"]["not_reported"] += 1
        elif altitude_ft <= 400:
            counters["altitude_distribution"]["≤400ft (legal)"] += 1
        elif altitude_ft <= 1400:
            counters["altitude_distribution"]["401-1400ft"] += 1
        elif altitude_ft <= 4100:
            counters["altitude_distribution"]["1401-4100ft"] += 1
        elif altitude_ft <= 8200:
            counters["altitude_distribution"]["4101-8200ft"] += 1
        else:
            counters["altitude_distribution"][">8200ft"] += 1
        
        # Proximity
        if proximity["close_approach"]:
            counters["close_approaches"] += 1
        if proximity["evasive_action"]:
            counters["evasive_actions"] += 1
        
        # Simulatability
        if simulatability["simulatable"]:
            counters["simulatable"] += 1
            if simulatability["scenario_type"] == "FAULT_INJECTION":
                counters["fault_injection_scenarios"] += 1
            else:
                counters["behavioral_scenarios"] += 1
        else:
            counters["not_simulatable"] += 1
    
    logger.info(f"  Analysis complete: {len(analyzed_records)} records processed")
    
    # ===== STEP 4: Generate scenario configs =====
    logger.info("")
    logger.info("=" * 70)
    logger.info("  STEP 4: Generating PX4 Simulation Scenarios")
    logger.info("=" * 70)
    
    scenarios = []
    for analysis in analyzed_records:
        scenario = build_scenario_config({}, analysis)
        if scenario:
            scenarios.append(scenario)
    
    logger.info(f"  Generated {len(scenarios)} simulatable scenarios")
    logger.info(f"    - Fault injection: {counters['fault_injection_scenarios']}")
    logger.info(f"    - Behavioral flight: {counters['behavioral_scenarios']}")
    logger.info(f"    - Not simulatable: {counters['not_simulatable']}")
    
    # ===== STEP 5: Save all outputs =====
    logger.info("")
    logger.info("=" * 70)
    logger.info("  STEP 5: Saving Analysis Results")
    logger.info("=" * 70)
    
    # 5a. Full analysis JSON
    with open(output_path / "03_full_analysis.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "total_records": len(analyzed_records),
                "data_source": "FAA UAS Sighting Reports (raw Excel files)",
                "data_directory": str(data_dir),
                "reference": "Watters (2023), AIAA — Preliminary Analysis of FAA UAS Sighting Reports",
            },
            "records": analyzed_records,
        }, f, indent=2, default=str)
    logger.info(f"  Saved: 03_full_analysis.json ({len(analyzed_records)} records)")
    
    # 5b. Simulatable scenarios JSON (for batch processing)
    with open(output_path / "04_simulatable_scenarios.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "total_scenarios": len(scenarios),
                "description": "PX4-simulatable scenarios derived from FAA reports — feed to run_automated_pipeline.py --batch",
            },
            "incidents": scenarios,
        }, f, indent=2, default=str)
    logger.info(f"  Saved: 04_simulatable_scenarios.json ({len(scenarios)} scenarios)")
    
    # 5c. Summary statistics JSON
    summary = {
        "dataset_overview": {
            "total_records": counters["total"],
            "total_files": len(file_stats),
            "time_period": f"{file_stats[0]['quarter']} to {file_stats[-1]['quarter']}" if file_stats else "N/A",
            "columns_found": columns,
        },
        "classification_distribution": dict(counters["by_classification"]),
        "fault_type_distribution": dict(counters["by_fault_type"]),
        "airframe_distribution": dict(counters["by_airframe"]),
        "uav_model_identified": dict(counters["by_uav_model"]),
        "altitude_distribution_watters_comparison": counters["altitude_distribution"],
        "proximity_analysis": {
            "close_approaches_within_500ft": counters["close_approaches"],
            "evasive_actions_reported": counters["evasive_actions"],
            "close_approach_rate_pct": round(counters["close_approaches"] / max(counters["total"], 1) * 100, 1),
        },
        "simulatability_assessment": {
            "total_simulatable": counters["simulatable"],
            "fault_injection_scenarios": counters["fault_injection_scenarios"],
            "behavioral_scenarios": counters["behavioral_scenarios"],
            "not_simulatable": counters["not_simulatable"],
            "simulatable_rate_pct": round(counters["simulatable"] / max(counters["total"], 1) * 100, 1),
        },
        "records_per_quarter": dict(counters["by_quarter"]),
    }
    
    with open(output_path / "05_summary_statistics.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"  Saved: 05_summary_statistics.json")
    
    # 5d. CSV summary table (for quick viewing / LaTeX import)
    csv_path = output_path / "06_summary_table.csv"
    total = counters["total"]
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Subcategory", "Count", "Percentage"])
            
            # Classification
            for cls, cnt in sorted(counters["by_classification"].items(), key=lambda x: -x[1]):
                writer.writerow(["Classification", cls, cnt, f"{cnt/total*100:.1f}%"])
            
            # Fault types
            for ft, cnt in sorted(counters["by_fault_type"].items(), key=lambda x: -x[1]):
                writer.writerow(["Fault Type", ft, cnt, f"{cnt/total*100:.1f}%"])
            
            # Airframes
            for af, cnt in sorted(counters["by_airframe"].items(), key=lambda x: -x[1]):
                writer.writerow(["Airframe", af, cnt, f"{cnt/total*100:.1f}%"])
            
            # UAV models identified
            for model, cnt in sorted(counters["by_uav_model"].items(), key=lambda x: -x[1]):
                writer.writerow(["UAV Model", model, cnt, f"{cnt/total*100:.1f}%"])
            
            # Altitude (Watters comparison)
            for band, cnt in counters["altitude_distribution"].items():
                writer.writerow(["Altitude Band", band, cnt, f"{cnt/total*100:.1f}%"])
            
            # Simulatability
            writer.writerow(["Simulatability", "PX4 Simulatable", counters["simulatable"], f"{counters['simulatable']/total*100:.1f}%"])
            writer.writerow(["Simulatability", "Fault Injection", counters["fault_injection_scenarios"], f"{counters['fault_injection_scenarios']/total*100:.1f}%"])
            writer.writerow(["Simulatability", "Behavioral Flight", counters["behavioral_scenarios"], f"{counters['behavioral_scenarios']/total*100:.1f}%"])
            writer.writerow(["Simulatability", "Not Simulatable", counters["not_simulatable"], f"{counters['not_simulatable']/total*100:.1f}%"])
            
            # Proximity
            writer.writerow(["Proximity", "Close Approaches (≤500ft)", counters["close_approaches"], f"{counters['close_approaches']/total*100:.1f}%"])
            writer.writerow(["Proximity", "Evasive Actions", counters["evasive_actions"], f"{counters['evasive_actions']/total*100:.1f}%"])
        
        logger.info(f"  Saved: 06_summary_table.csv")
    except PermissionError:
        logger.warning(f"  ⚠ Could not save 06_summary_table.csv (Permission denied - file may be open in Excel)")
    
    # 5e. Confirmed failures only (highest-value subset)
    confirmed = [a for a in analyzed_records if a["classification"]["classification"] == "CONFIRMED_FAILURE"]
    with open(output_path / "07_confirmed_failures.json", "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "description": "Records with explicit crash/failure evidence from FAA narratives",
                "total_confirmed": len(confirmed),
            },
            "records": confirmed,
        }, f, indent=2, default=str)
    logger.info(f"  Saved: 07_confirmed_failures.json ({len(confirmed)} records)")
    
    # ===== Print Summary =====
    logger.info("")
    logger.info("=" * 70)
    logger.info("  ANALYSIS COMPLETE — SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total records analyzed:        {total}")
    logger.info(f"  Confirmed failures:            {counters['by_classification'].get('CONFIRMED_FAILURE', 0)}")
    logger.info(f"  Probable failures:             {counters['by_classification'].get('PROBABLE_FAILURE', 0)}")
    logger.info(f"  Behavioral scenarios:          {counters['by_classification'].get('BEHAVIORAL_SCENARIO', 0)}")
    logger.info(f"  ---")
    logger.info(f"  PX4 Simulatable:               {counters['simulatable']} ({counters['simulatable']/total*100:.1f}%)")
    logger.info(f"    -> Fault injection:           {counters['fault_injection_scenarios']}")
    logger.info(f"    -> Behavioral flight:         {counters['behavioral_scenarios']}")
    logger.info(f"  Not simulatable:               {counters['not_simulatable']}")
    logger.info(f"  ---")
    logger.info(f"  UAV models identified:         {sum(counters['by_uav_model'].values())}")
    logger.info(f"  Close approaches:              {counters['close_approaches']} ({counters['close_approaches']/total*100:.1f}%)")
    logger.info(f"  Evasive actions:               {counters['evasive_actions']}")
    logger.info(f"  ---")
    logger.info(f"  Output directory:              {output_path}")
    logger.info("=" * 70)
    
    return summary


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FAA UAS Sighting Report Deep Analysis — AeroGuardian DASC 2026",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python src/analysis/faa_analysis.py
    python src/analysis/faa_analysis.py --output-dir outputs/faa_analysis
    python src/analysis/faa_analysis.py --verbose
    
Output files:
    01_file_statistics.json    - File-level stats (rows, columns per Excel file)
    02_schema.json             - Discovered column schema
    03_full_analysis.json      - Complete analysis of every record
    04_simulatable_scenarios.json - PX4-ready scenario configs (batch mode input)
    05_summary_statistics.json - Summary statistics (for paper tables)
    06_summary_table.csv       - CSV summary (for LaTeX/Excel import)
    07_confirmed_failures.json - Confirmed failure subset only
        """
    )
    parser.add_argument("--data-dir", type=str,
                        default=str(PROJECT_ROOT / "data" / "raw" / "faa"),
                        help="Path to raw FAA Excel files")
    parser.add_argument("--output-dir", type=str,
                        default=str(PROJECT_ROOT / "outputs" / "faa_analysis"),
                        help="Output directory for analysis results")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose progress logging")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    logger.info("AeroGuardian — FAA UAS Sighting Report Deep Analysis")
    logger.info(f"Data directory: {args.data_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info("")
    
    try:
        summary = run_analysis(args.data_dir, args.output_dir, args.verbose)
        logger.info("Analysis completed successfully!")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
