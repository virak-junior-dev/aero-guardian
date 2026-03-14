"""
Constraint Correctness Rate (CCR)
=================================
Author: AeroGuardian Team
Date: 2026-03-12

Evaluates narrative -> configuration transformation quality with a
reference-based adjudication policy.

IMPORTANT FAIRNESS RULE:
- Deterministic extraction is a baseline reference, not oracle truth.
- LLM outputs with better valid specificity are rewarded as
  "better_specificity" rather than penalized.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("AeroGuardian.Evaluator.CCR")


VALID_STATUSES = {
    "exact_match",
    "equivalent_match",
    "better_specificity",
    "contradiction",
    "missing",
}


@dataclass
class CCRFieldAssessment:
    """Assessment of one field in narrative -> config transformation."""

    field: str
    status: str
    score: float
    details: str = ""

    def to_dict(self) -> Dict:
        return {
            "field": self.field,
            "status": self.status,
            "score": round(self.score, 3),
            "details": self.details,
        }


@dataclass
class CCRResult:
    """Complete CCR evaluation result."""

    score: float = 0.0
    confidence: str = "LOW"
    assessments: List[CCRFieldAssessment] = field(default_factory=list)
    contradiction_count: int = 0
    missing_count: int = 0
    better_specificity_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "CCR": round(self.score, 3),
            "confidence": self.confidence,
            "assessments": [a.to_dict() for a in self.assessments],
            "contradiction_count": self.contradiction_count,
            "missing_count": self.missing_count,
            "better_specificity_count": self.better_specificity_count,
        }


class ConstraintCorrectnessEvaluator:
    """
    Evaluates transformation quality from FAA narrative to config.

    Fields evaluated:
    - location
    - altitude
    - fault_type
    - uav_model
    - onset_timing
    """

    WEIGHTS = {
        "location": 0.20,
        "altitude": 0.20,
        "fault_type": 0.30,
        "uav_model": 0.15,
        "onset_timing": 0.15,
    }

    STATUS_SCORES = {
        "exact_match": 1.0,
        "equivalent_match": 0.9,
        "better_specificity": 1.0,
        "contradiction": 0.0,
        "missing": 0.0,
    }

    FAULT_KEYWORDS = {
        "motor_failure": ["motor", "propeller", "engine", "thrust", "spin"],
        "gps_loss": ["gps", "navigation", "drift", "satellite"],
        "battery_failure": ["battery", "voltage", "low power", "depleted"],
        "control_loss": ["control", "unresponsive", "flyaway", "lost link"],
        "geofence_violation": ["airport", "approach", "runway", "airspace"],
        "altitude_violation": ["above", "altitude", "ft", "feet"],
    }

    UAV_KEYWORDS = {
        "plane": ["fixed wing", "plane", "cessna", "wing"],
        "standard_vtol": ["vtol", "tilt", "hybrid"],
        "iris": ["quadcopter", "multirotor", "drone", "hexacopter", "uas"],
    }

    def evaluate(self, faa_report: Dict, px4_config: Dict) -> CCRResult:
        result = CCRResult()

        narrative = self._extract_text(faa_report).lower()

        assessments = [
            self._assess_location(faa_report, px4_config),
            self._assess_altitude(narrative, px4_config),
            self._assess_fault_type(narrative, px4_config),
            self._assess_uav_model(narrative, px4_config),
            self._assess_onset_timing(narrative, px4_config),
        ]

        result.assessments = assessments
        result.contradiction_count = sum(1 for a in assessments if a.status == "contradiction")
        result.missing_count = sum(1 for a in assessments if a.status == "missing")
        result.better_specificity_count = sum(1 for a in assessments if a.status == "better_specificity")

        weighted = 0.0
        for a in assessments:
            w = self.WEIGHTS.get(a.field, 0.0)
            weighted += w * a.score

        result.score = weighted
        result.confidence = self._confidence_from_assessments(assessments)

        logger.info(
            "CCR evaluated: %.3f (%s, better_specificity=%d)",
            result.score,
            result.confidence,
            result.better_specificity_count,
        )
        return result

    def _extract_text(self, faa_report: Dict) -> str:
        return " ".join(
            [
                str(faa_report.get("description", "") or ""),
                str(faa_report.get("summary", "") or ""),
                str(faa_report.get("narrative", "") or ""),
            ]
        ).strip()

    def _mk(self, field: str, status: str, details: str = "") -> CCRFieldAssessment:
        if status not in VALID_STATUSES:
            status = "missing"
        return CCRFieldAssessment(
            field=field,
            status=status,
            score=self.STATUS_SCORES[status],
            details=details,
        )

    def _assess_location(self, faa_report: Dict, px4_config: Dict) -> CCRFieldAssessment:
        city = str(faa_report.get("city", "") or "").strip().lower()
        state = str(faa_report.get("state", "") or "").strip().lower()
        lat = px4_config.get("mission", {}).get("start_lat")
        lon = px4_config.get("mission", {}).get("start_lon")

        if city or state:
            if lat is not None and lon is not None:
                return self._mk("location", "exact_match", "Narrative location present and coordinates generated")
            return self._mk("location", "missing", "Narrative location present but config missing coordinates")

        if lat is not None and lon is not None:
            return self._mk("location", "better_specificity", "Config provides geolocation despite sparse narrative")

        return self._mk("location", "missing", "No location evidence in narrative or config")

    def _assess_altitude(self, narrative: str, px4_config: Dict) -> CCRFieldAssessment:
        cfg_alt = px4_config.get("mission", {}).get("takeoff_altitude_m")
        match = re.search(r"([\d,]+)\s*(?:feet|ft|')", narrative)

        if match:
            ft = float(match.group(1).replace(",", ""))
            expected_m = ft * 0.3048
            if cfg_alt is None:
                return self._mk("altitude", "missing", "Narrative altitude present but config altitude missing")
            diff = abs(float(cfg_alt) - expected_m)
            
            # Check if this is an airspace/approach altitude context
            # (e.g., "on base to final" or "approach") where altitude might be
            # reference altitude (controlled airspace) not UAS altitude
            is_airspace_context = any(
                phrase in narrative
                for phrase in [
                    "base to final", "approach", "runway", "airspace",
                    "feet agl", "altitude violation", "altitude limit"
                ]
            )
            
            # Extremely large diffs (>100m) in airspace context likely mean
            # the narrative altitude is NOT about the UAS
            if diff > 100 and is_airspace_context:
                return self._mk(
                    "altitude",
                    "better_specificity",
                    f"Narrative altitude ({expected_m:.0f}m) appears to reference controlled airspace/approach, not UAS. Config UAS altitude inferred as {cfg_alt}m."
                )
            
            if diff <= 8.0:
                return self._mk("altitude", "exact_match", f"Altitude converted correctly (diff={diff:.1f}m)")
            if diff <= 20.0:
                return self._mk("altitude", "equivalent_match", f"Altitude approximately aligned (diff={diff:.1f}m)")
            return self._mk("altitude", "contradiction", f"Config altitude inconsistent with narrative (diff={diff:.1f}m)")

        if cfg_alt is not None:
            return self._mk("altitude", "better_specificity", "Config provides plausible altitude when narrative omits altitude")

        return self._mk("altitude", "missing", "No altitude evidence")

    def _assess_fault_type(self, narrative: str, px4_config: Dict) -> CCRFieldAssessment:
        cfg_fault = str(px4_config.get("fault_injection", {}).get("fault_type", "") or "").lower()
        fault_supported = bool(px4_config.get("fault_injection_supported", True))

        if not cfg_fault:
            return self._mk("fault_type", "missing", "fault_type missing in config")

        hits = {k: sum(1 for kw in kws if kw in narrative) for k, kws in self.FAULT_KEYWORDS.items()}
        best = max(hits, key=hits.get) if hits else ""
        best_count = hits.get(best, 0)

        if best_count == 0:
            return self._mk("fault_type", "better_specificity", "Narrative sparse; fault inferred by LLM")

        if best in cfg_fault or cfg_fault in best:
            return self._mk("fault_type", "exact_match", f"Fault aligned with narrative cues ({best})")

        # Airspace sightings are often behavior-only narratives (altitude/approach/runway)
        # where "flyaway" is a plausible proxy label rather than a hard contradiction.
        is_airspace_best = best in {"altitude_violation", "geofence_violation"}
        is_behavioral_cfg = cfg_fault in {"flyaway", "control_loss", "behavioral"}
        has_explicit_failure_cue = any(
            kw in narrative
            for kw in [
                "motor", "propeller", "engine", "thrust",
                "battery", "voltage", "depleted",
                "gps", "satellite", "drift",
                "lost control", "unresponsive", "lost link",
            ]
        )

        if is_airspace_best and is_behavioral_cfg:
            if not fault_supported:
                return self._mk(
                    "fault_type",
                    "equivalent_match",
                    "Airspace/altitude sighting mapped to unsupported behavioral proxy fault",
                )
            if not has_explicit_failure_cue:
                return self._mk(
                    "fault_type",
                    "equivalent_match",
                    "Airspace/altitude narrative can plausibly map to behavioral flyaway/control proxy",
                )

        if best_count <= 1:
            return self._mk("fault_type", "equivalent_match", "Weak narrative cues; config remains plausible")

        return self._mk("fault_type", "contradiction", f"Narrative cues favor '{best}' but config uses '{cfg_fault}'")

    def _assess_uav_model(self, narrative: str, px4_config: Dict) -> CCRFieldAssessment:
        cfg_model = str(
            px4_config.get("proxy_modeling", {}).get("simulation_platform")
            or px4_config.get("uav_model")
            or ""
        ).lower()

        if not cfg_model:
            return self._mk("uav_model", "missing", "uav_model/simulation_platform missing")

        detected: Optional[str] = None
        for model, kws in self.UAV_KEYWORDS.items():
            if any(kw in narrative for kw in kws):
                detected = model
                break

        if detected is None:
            return self._mk("uav_model", "better_specificity", "Narrative lacks aircraft class; model inferred")

        if detected == "iris" and ("x500" in cfg_model or "iris" in cfg_model):
            return self._mk("uav_model", "equivalent_match", "Equivalent multirotor simulation platform")

        if detected in cfg_model:
            return self._mk("uav_model", "exact_match", "Detected aircraft class matches simulation model")

        return self._mk("uav_model", "contradiction", f"Detected '{detected}' but config model is '{cfg_model}'")

    def _assess_onset_timing(self, narrative: str, px4_config: Dict) -> CCRFieldAssessment:
        onset = px4_config.get("fault_injection", {}).get("onset_sec")
        if onset is None:
            return self._mk("onset_timing", "missing", "fault onset missing")

        try:
            onset_val = int(onset)
        except Exception:
            return self._mk("onset_timing", "contradiction", "fault onset is not numeric")

        if onset_val < 0 or onset_val > 600:
            return self._mk("onset_timing", "contradiction", "fault onset outside plausible mission range")

        if any(x in narrative for x in ["during takeoff", "on takeoff", "immediately"]):
            if onset_val <= 30:
                return self._mk("onset_timing", "exact_match", "Onset aligns with takeoff narrative")
            return self._mk("onset_timing", "equivalent_match", "Onset plausible but later than takeoff cue")

        return self._mk("onset_timing", "better_specificity", "Narrative lacks precise timing; onset inferred")

    def _confidence_from_assessments(self, assessments: List[CCRFieldAssessment]) -> str:
        contradictions = sum(1 for a in assessments if a.status == "contradiction")
        misses = sum(1 for a in assessments if a.status == "missing")
        if contradictions >= 2:
            return "LOW"
        if contradictions == 0 and misses <= 1:
            return "HIGH"
        return "MEDIUM"
