"""
Scenario Generator for AeroGuardian
====================================
Author: AeroGuardian Team (Tiny Coders)
Date: 2026-01-30
Updated: 2026-02-04

Generates PX4 simulation configurations from FAA UAS sighting reports.
Uses FAA_To_PX4_Complete DSPy signature to translate natural language
descriptions of operational anomalies into executable simulation parameters.

OUTPUT: 31-parameter configuration including:
- Fault type, category, and PX4 shell command
- Waypoints with GPS coordinates
- Environmental conditions (wind, weather)
- Mission parameters (altitude, speed, duration)

USAGE:
    from src.llm import ScenarioGenerator
    
    generator = ScenarioGenerator()
    config = generator.generate(faa_report_text, sighting_id)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import dspy

from .signatures import FAA_To_PX4_Complete
from .llm_logger import LLMInteractionLogger, get_dspy_history, clear_dspy_history

logger = logging.getLogger("AeroGuardian.ScenarioGenerator")


# =============================================================================
# Simulation Optimization Constants
# =============================================================================

MAX_UAV_ALTITUDE_M = 5000.0  # Max realistic simulation altitude
DEFAULT_TEST_ALTITUDE_M = 50.0
MAX_MISSION_DURATION_SEC = 120  # 2 minutes max
MIN_MISSION_DURATION_SEC = 60
FAULT_ONSET_RATIO = 0.5

# US Continental bounds for validation
US_LAT_MIN, US_LAT_MAX = 24.0, 50.0
US_LON_MIN, US_LON_MAX = -125.0, -66.0
MAX_GEOCODE_DISTANCE_KM = 100.0  # Max acceptable drift from city center

ALLOWED_UAV_MODELS = {"iris", "plane", "standard_vtol"}
ALLOWED_FAILURE_CATEGORIES = {
    "propulsion",
    "navigation",
    "power",
    "control",
    "environmental",
    "airspace_violation",
}
ALLOWED_FAILURE_COMPONENTS = {"motor", "gps", "battery", "rc_link", "esc", "compass", "baro", "imu", "none"}
ALLOWED_FLIGHT_PHASES = {"takeoff", "climb", "cruise", "hover", "descent", "landing"}
ALLOWED_OUTCOMES = {"unknown", "landed", "crashed", "flew_away", "recovered_by_operator"}
ALLOWED_ENVIRONMENTS = {"urban", "suburban", "rural", "airport_vicinity", "industrial"}
ALLOWED_WAYPOINT_ACTIONS = {"takeoff", "waypoint", "hover", "land"}

FORBIDDEN_DERIVED_HINT_TOKENS = {
    "fault_type:",
    "classification:",
    "hazard_category:",
    "confidence:",
    "incident_type:",
    "predicted_failure:",
}


def validate_geocoding(
    llm_lat: float, 
    llm_lon: float, 
    city: str, 
    state: str
) -> tuple[float, float, bool]:
    """
    Validate LLM-generated lat/lon against expected city location.
    
    If LLM coordinates are invalid or too far from city, falls back to
    geocoder lookup.
    
    Args:
        llm_lat: LLM-generated latitude
        llm_lon: LLM-generated longitude
        city: Expected city name
        state: Expected state name
        
    Returns:
        Tuple of (validated_lat, validated_lon, was_corrected)
    """
    import math
    
    # Check basic US bounds
    if not (US_LAT_MIN <= llm_lat <= US_LAT_MAX and US_LON_MIN <= llm_lon <= US_LON_MAX):
        logger.warning(f">>>>> LLM lat/lon ({llm_lat:.4f}, {llm_lon:.4f}) outside US bounds")
        return _fallback_geocode(city, state, "outside_bounds")
    
    # Try to verify against actual geocoded location
    try:
        from src.core.geocoder import geocode
        actual_lat, actual_lon = geocode(city, state)
        
        # Haversine distance calculation
        R = 6371  # Earth's radius in km
        lat1, lat2 = math.radians(llm_lat), math.radians(actual_lat)
        dlat = math.radians(actual_lat - llm_lat)
        dlon = math.radians(actual_lon - llm_lon)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance_km = R * c
        
        if distance_km > MAX_GEOCODE_DISTANCE_KM:
            logger.warning(
                f">>>>> LLM geocoding drift: {distance_km:.1f}km from {city}, {state} "
                f"(LLM: {llm_lat:.4f}, {llm_lon:.4f} vs Actual: {actual_lat:.4f}, {actual_lon:.4f})"
            )
            return actual_lat, actual_lon, True
        
        # LLM coordinates are acceptable
        logger.debug(f">>>>> LLM geocoding validated: {distance_km:.1f}km from city center")
        return llm_lat, llm_lon, False
        
    except Exception as e:
        logger.debug(f"Geocoding validation skipped (no network?): {e}")
        # Can't verify - accept LLM coordinates if within US bounds
        return llm_lat, llm_lon, False


def _fallback_geocode(city: str, state: str, reason: str) -> tuple[float, float, bool]:
    """Fallback to geocoder when LLM coordinates are invalid."""
    try:
        from src.core.geocoder import geocode
        lat, lon = geocode(city, state)
        logger.info(f">>>>> Geocoding fallback ({reason}): {city}, {state} → ({lat:.4f}, {lon:.4f})")
        return lat, lon, True
    except Exception as e:
        # Ultimate fallback: PX4 default location (Minneapolis)
        logger.warning(f">>>>> Geocoding failed, using PX4 default: {e}")
        return 44.9778, -93.2650, True


def clamp_altitude(altitude_m: float, original_altitude_ft: float = None) -> float:
    """Clamp altitude to UAV-realistic values (max 120m)."""
    if altitude_m is None or altitude_m <= 0:
        logger.info(f">>>>> Altitude missing/invalid, using default {DEFAULT_TEST_ALTITUDE_M}m")
        return DEFAULT_TEST_ALTITUDE_M
    
    if altitude_m > MAX_UAV_ALTITUDE_M:
        original_ft = original_altitude_ft or (altitude_m * 3.28084)
        logger.info(f">>>>> Clamping altitude: {original_ft:.0f}ft ({altitude_m:.0f}m) → {MAX_UAV_ALTITUDE_M}m")
        return MAX_UAV_ALTITUDE_M
    
    return altitude_m


def optimize_fault_timing(llm_onset_sec: int, mission_duration_sec: int = MAX_MISSION_DURATION_SEC) -> int:
    """Optimize fault onset timing for DEMO purposes (fault at T+5s)."""
    DEMO_FAULT_ONSET_SEC = 5
    
    if llm_onset_sec != DEMO_FAULT_ONSET_SEC:
        logger.info(f"Optimizing fault onset: {llm_onset_sec}s → {DEMO_FAULT_ONSET_SEC}s")
    
    return DEMO_FAULT_ONSET_SEC


# =============================================================================
# Data Classes
# =============================================================================

class ScenarioGenerationError(Exception):
    """Raised when scenario generation fails."""


@dataclass
class ScenarioConfig:
    """Complete PX4 config - all values from LLM."""
    
    faa_report_id: str
    faa_report_text: str
    
    city: str
    state: str
    lat: float
    lon: float
    
    altitude_m: float
    speed_ms: float
    flight_phase: str
    uav_model: str
    
    failure_mode: str
    failure_category: str
    failure_component: str
    failure_onset_sec: int
    
    symptoms: List[str]
    outcome: str
    
    weather: str
    wind_speed_ms: float
    wind_direction_deg: float
    environment: str

    waypoints: List[Dict]
    
    reasoning: str
    
    # Uncertainty & evidence tracking
    uncertainty_score: float = 0.5  # 0=certain, 1=highly uncertain
    fault_injection_supported: bool = True  # False for behavior-only scenarios
    
    # Separate narrative facts vs LLM inferences
    narrative_facts: Optional[Dict[str, Any]] = None  # Facts extracted from FAA report
    inferred_parameters: Optional[Dict[str, Any]] = None  # LLM-inferred values
    
    # Proxy simulation tags
    proxy_modeling: Optional[Dict[str, Any]] = None  # Platform substitution info
    
    # Evidence traceability
    evidence_map: Optional[Dict[str, str]] = None  # Parameter → source mapping
    reconstruction_level: str = "proxy_simulation"  # proxy_simulation | partial_match | behavioral_class
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# Scenario Generator
# =============================================================================

class ScenarioGenerator:
    """
    Generate PX4 simulation configurations from FAA UAS sighting reports.
    
    Uses FAA_To_PX4_Complete DSPy signature to translate natural language
    descriptions of operational anomalies into executable simulation configs.
    
    USAGE:
        generator = ScenarioGenerator()
        config = generator.generate(faa_report, sighting_id)
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize scenario generator with optional output logging."""
        self.is_ready = False
        self._translator = None
        self._output_dir = output_dir
        self._llm_logger: Optional[LLMInteractionLogger] = None
        self._configure()
    
    def _configure(self):
        """Configure DSPy with Universal LLM Factory + model-specific enhancer."""
        try:
            from .llm_setup import get_dspy_lm
            self.lm = get_dspy_lm()
            
            # Use local context instead of global dspy.configure to avoid threading issues
            self._translator = dspy.ChainOfThought(FAA_To_PX4_Complete)
            
            # Load model-specific prompt enhancer (Strategy Pattern)
            from .prompt_enhancers import get_enhancer
            self._enhancer = get_enhancer()
            
            # Load few-shot examples
            try:
                from .dspy_fewshot import get_faa_to_px4_examples
                examples = get_faa_to_px4_examples()
                if examples:
                    self._translator.demos = examples[:3]
                    logger.info(f"Loaded {len(examples)} few-shot examples")
            except ImportError:
                logger.debug("Few-shot examples not available")
            
            self.is_ready = True
            logger.info(
                f">>>>> ScenarioGenerator ready | "
                f"Enhancer: {self._enhancer}"
            )
            
        except Exception as e:
            raise ScenarioGenerationError(f"Failed to initialize LLM: {e}")
    
    @staticmethod
    def _normalize_failure_mode(value: str) -> str:
        """Normalize LLM failure_mode into the allowed ontology."""
        allowed = {
            "motor_failure",
            "gps_loss",
            "gps_dropout",
            "battery_failure",
            "battery_depletion",
            "control_loss",
            "control_signal_loss",
            "sensor_failure",
            "compass_error",
            "geofence_violation",
            "altitude_violation",
            "flyaway",
        }

        raw = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
        alias_map = {
            "fly_away": "flyaway",
            "controlsignal_loss": "control_signal_loss",
            "control_signal": "control_signal_loss",
            "rc_loss": "control_signal_loss",
            "rc_link_loss": "control_signal_loss",
            "gps_failure": "gps_loss",
            "battery_low": "battery_depletion",
            "battery_empty": "battery_depletion",
            "geo_fence_violation": "geofence_violation",
        }

        if raw in allowed:
            return raw
        if raw in alias_map:
            return alias_map[raw]

        if "fly" in raw and "away" in raw:
            return "flyaway"
        if "geofence" in raw:
            return "geofence_violation"
        if "altitude" in raw and "violation" in raw:
            return "altitude_violation"
        if "compass" in raw or "mag" in raw:
            return "compass_error"
        if "gps" in raw and "drop" in raw:
            return "gps_dropout"
        if "gps" in raw:
            return "gps_loss"
        if "battery" in raw and ("depletion" in raw or "empty" in raw or "low" in raw):
            return "battery_depletion"
        if "battery" in raw:
            return "battery_failure"
        if "control" in raw and "signal" in raw:
            return "control_signal_loss"
        if "control" in raw:
            return "control_loss"
        if "motor" in raw or "propulsion" in raw or "engine" in raw:
            return "motor_failure"

        return "sensor_failure"

    @staticmethod
    def _is_fault_injection_supported(failure_mode: str) -> bool:
        """Determine injection support in code, independent of LLM command strings."""
        mode = str(failure_mode or "").strip().lower()
        behavior_only = {
            "geofence_violation",
            "altitude_violation",
        }
        if not mode or mode == "unknown":
            return False
        return mode not in behavior_only

    @staticmethod
    def _validate_enum(field_name: str, value: str, allowed: set[str]) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in allowed:
            raise ScenarioGenerationError(
                f"Invalid {field_name}: '{value}'. Allowed values: {sorted(allowed)}"
            )
        return normalized

    @staticmethod
    def _parse_and_validate_waypoints(waypoints_json: str) -> List[Dict[str, Any]]:
        try:
            waypoints = json.loads(waypoints_json)
        except json.JSONDecodeError as e:
            raise ScenarioGenerationError(f"Invalid waypoints JSON: {e}")

        if not isinstance(waypoints, list) or len(waypoints) == 0:
            raise ScenarioGenerationError("Waypoints must be a non-empty JSON array")

        for idx, wp in enumerate(waypoints):
            if not isinstance(wp, dict):
                raise ScenarioGenerationError(f"Waypoint[{idx}] must be an object")

            for key in ["lat", "lon", "alt", "action"]:
                if key not in wp:
                    raise ScenarioGenerationError(f"Waypoint[{idx}] missing required field '{key}'")

            try:
                wp["lat"] = float(wp["lat"])
                wp["lon"] = float(wp["lon"])
                wp["alt"] = float(wp["alt"])
            except (TypeError, ValueError):
                raise ScenarioGenerationError(f"Waypoint[{idx}] lat/lon/alt must be numeric")

            action = str(wp["action"]).strip().lower()
            if action not in ALLOWED_WAYPOINT_ACTIONS:
                raise ScenarioGenerationError(
                    f"Waypoint[{idx}] invalid action '{wp['action']}'. "
                    f"Allowed actions: {sorted(ALLOWED_WAYPOINT_ACTIONS)}"
                )
            wp["action"] = action

        return waypoints

    def _write_prompt_audit(self, report_id: str, audit: Dict[str, Any]) -> None:
        if not self._output_dir:
            return

        safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(report_id))
        out_dir = Path(self._output_dir) / "evaluation"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"phase3_prompt_audit_{safe_id}.json"
        out_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    def _audit_raw_only_prompt_payload(self, faa_report_text: str, report_id: str) -> Dict[str, Any]:
        payload_text = str(faa_report_text or "")
        payload_lower = payload_text.lower()

        required_fields = ["report id:", "date:", "city:", "state:", "description:"]
        missing_required_fields = [fld for fld in required_fields if fld not in payload_lower]
        found_forbidden_tokens = [tok for tok in sorted(FORBIDDEN_DERIVED_HINT_TOKENS) if tok in payload_lower]

        audit = {
            "timestamp": datetime.now().isoformat(),
            "phase": 3,
            "report_id": report_id,
            "required_fields": required_fields,
            "missing_required_fields": missing_required_fields,
            "forbidden_derived_tokens": sorted(FORBIDDEN_DERIVED_HINT_TOKENS),
            "found_forbidden_tokens": found_forbidden_tokens,
            "input_payload_length": len(payload_text),
            "input_preview": payload_text[:800],
            "pass": len(missing_required_fields) == 0 and len(found_forbidden_tokens) == 0,
        }
        return audit
    
    def generate(self, faa_report_text: str, report_id: str) -> ScenarioConfig:
        """
        Generate PX4 config from FAA sighting report.
        
        Args:
            faa_report_text: Complete FAA UAS sighting report text
            report_id: Unique identifier for the report
            
        Returns:
            ScenarioConfig with all simulation parameters
            
        Raises:
            ScenarioGenerationError on failure
        """
        if not self.is_ready:
            raise ScenarioGenerationError("Generator not initialized")
        
        if not faa_report_text or len(faa_report_text.strip()) < 20:
            raise ScenarioGenerationError("FAA report text is empty or too short")
        
        logger.info(f"Generating config: {report_id}")
        
        # Initialize LLM logger for this request
        if self._output_dir:
            from pathlib import Path
            self._llm_logger = LLMInteractionLogger(
                output_dir=Path(self._output_dir),
                phase=1,
                report_id=report_id
            )
        
        try:
            # Log request start
            input_fields = {
                "faa_report_text": faa_report_text,
                "faa_report_id": report_id,
            }
            if self._llm_logger:
                clear_dspy_history(self.lm)  # Clear previous history
                self._llm_logger.log_request_start(
                    "FAA_To_PX4_Complete",
                    input_fields,
                    model_name=str(getattr(self.lm, "model", "unknown")),
                )
            
            # Phase 3 raw-only gate: validate prompt payload contract before LLM call.
            prompt_audit = self._audit_raw_only_prompt_payload(faa_report_text, report_id)
            self._write_prompt_audit(report_id, prompt_audit)
            if not prompt_audit["pass"]:
                raise ScenarioGenerationError(
                    "Raw-only prompt payload audit failed: "
                    f"missing={prompt_audit['missing_required_fields']} "
                    f"forbidden={prompt_audit['found_forbidden_tokens']}"
                )
            
            with dspy.context(lm=self.lm):
                result = self._translator(
                    faa_report_text=faa_report_text,
                    faa_report_id=report_id,
                )
                
            normalized_failure_mode = self._normalize_failure_mode(str(result.failure_mode))
            if normalized_failure_mode != str(result.failure_mode):
                logger.warning(
                    "Normalized unsupported failure_mode '%s' -> '%s'",
                    result.failure_mode,
                    normalized_failure_mode,
                )
            
            # Log response with DSPy history
            if self._llm_logger:
                self._llm_logger.log_response(result, get_dspy_history(self.lm))
            
            # Enforce strict output schema checks.
            uav_model = self._validate_enum("uav_model", result.uav_model, ALLOWED_UAV_MODELS)
            failure_category = self._validate_enum(
                "failure_category", result.failure_category, ALLOWED_FAILURE_CATEGORIES
            )
            failure_component = self._validate_enum(
                "failure_component", result.failure_component, ALLOWED_FAILURE_COMPONENTS
            )
            flight_phase = self._validate_enum("flight_phase", result.flight_phase, ALLOWED_FLIGHT_PHASES)
            outcome = self._validate_enum("outcome", result.outcome, ALLOWED_OUTCOMES)
            environment = self._validate_enum("environment", result.environment, ALLOWED_ENVIRONMENTS)
            waypoints = self._parse_and_validate_waypoints(result.waypoints_json)
            
            # Parse symptoms
            symptoms = [s.strip() for s in str(result.symptoms).split(",") if s.strip()]
            if not symptoms:
                raise ScenarioGenerationError("No symptoms extracted from report")
            
            # Apply simulation optimizations
            raw_altitude_m = float(result.altitude_m)
            raw_altitude_ft = float(result.altitude_ft) if hasattr(result, 'altitude_ft') else raw_altitude_m * 3.28084
            clamped_altitude_m = clamp_altitude(raw_altitude_m, raw_altitude_ft)
            
            for wp in waypoints:
                if 'alt' in wp and wp['alt'] > MAX_UAV_ALTITUDE_M:
                    wp['alt'] = clamped_altitude_m
            
            raw_onset_sec = int(result.failure_onset_sec)
            optimized_onset_sec = optimize_fault_timing(raw_onset_sec, MAX_MISSION_DURATION_SEC)
            
            logger.info(f"Optimizations: Alt {raw_altitude_m:.0f}m→{clamped_altitude_m:.0f}m, Fault {raw_onset_sec}s→{optimized_onset_sec}s")
            
            # Validate LLM geocoding (CRITICAL: Prevents hallucinated coordinates)
            validated_lat, validated_lon, was_corrected = validate_geocoding(
                llm_lat=float(result.lat),
                llm_lon=float(result.lon),
                city=str(result.city),
                state=str(result.state),
            )
            if was_corrected:
                logger.info(f">>>>> Geocoding corrected: LLM ({result.lat:.4f}, {result.lon:.4f}) → ({validated_lat:.4f}, {validated_lon:.4f})")
                # Also update waypoints to use corrected coordinates
                for wp in waypoints:
                    if 'lat' in wp and 'lon' in wp:
                        # Shift waypoints to corrected location (preserve relative positions)
                        lat_offset = validated_lat - float(result.lat)
                        lon_offset = validated_lon - float(result.lon)
                        wp['lat'] = wp['lat'] + lat_offset
                        wp['lon'] = wp['lon'] + lon_offset
            
            # P0: Determine if fault injection is supported (deterministic, code-side)
            fault_injection_supported = self._is_fault_injection_supported(normalized_failure_mode)
            
            # P0: Calculate uncertainty score based on inference confidence
            uncertainty_factors = []
            if str(result.weather) == "not_specified":
                uncertainty_factors.append(0.1)  # Weather unknown
            if not fault_injection_supported:
                uncertainty_factors.append(0.2)  # No direct fault injection
            if was_corrected:
                uncertainty_factors.append(0.1)  # Geocoding corrected
            if raw_altitude_m > MAX_UAV_ALTITUDE_M:
                uncertainty_factors.append(0.1)  # Altitude clamped
            uncertainty_score = min(1.0, 0.3 + sum(uncertainty_factors))  # Base 0.3 for LLM inference
            
            # Separate narrative facts (from FAA report) vs inferred parameters
            narrative_facts = {
                "location_stated": f"{result.city}, {result.state}",
                "malfunction_described": "malfunctioned" in faa_report_text.lower() or "malfunction" in faa_report_text.lower(),
                "parachute_deployed": "chute" in faa_report_text.lower() or "parachute" in faa_report_text.lower(),
                "outcome_stated": "landed" if "landed" in faa_report_text.lower() or "went down" in faa_report_text.lower() else "unknown",
                "aircraft_type_stated": result.uav_model if result.uav_model.lower() not in ["unknown"] else None,
                "altitude_stated": raw_altitude_ft if "ft" in faa_report_text.lower() or "feet" in faa_report_text.lower() else None,
            }
            
            inferred_parameters = {
                "failure_mode": normalized_failure_mode,
                "failure_category": str(result.failure_category),
                "failure_component": failure_component,
                "flight_phase": flight_phase,
                "speed_ms": float(result.speed_ms),
                "wind_speed_ms": float(result.wind_speed_ms),
                "environment_type": environment,
                "inference_reasoning": str(result.reasoning)[:500],
            }
            
            # Dynamic Airframe Modeling
            uav_model_lower = uav_model
            is_fixed_wing = uav_model_lower == "plane"
            is_vtol = uav_model_lower == "standard_vtol"
            
            proxy_modeling = {
                "source_aircraft_class": "fixed_wing" if is_fixed_wing else "vtol" if is_vtol else "multirotor",
                "source_aircraft_type": uav_model,
                "simulation_platform": uav_model, # Dynamically passed to PX4 target
                "platform_substitution": False, # We now support specific airframes dynamically
                "substitution_reason": None,
                "parachute_modeled": narrative_facts["parachute_deployed"],
                "parachute_trigger": "control_loss_recovery" if narrative_facts["parachute_deployed"] else None,
            }
            
            # Evidence traceability map (parameter → source)
            evidence_map = {
                "city": "FAA_NARRATIVE",
                "state": "FAA_NARRATIVE", 
                "lat": "GEOCODER_API" if was_corrected else "LLM_INFERENCE",
                "lon": "GEOCODER_API" if was_corrected else "LLM_INFERENCE",
                "altitude_m": "FAA_NARRATIVE" if narrative_facts["altitude_stated"] else "LLM_DEFAULT",
                "uav_model": "FAA_NARRATIVE" if narrative_facts["aircraft_type_stated"] else "LLM_INFERENCE",
                "failure_mode": "LLM_INFERENCE",
                "failure_category": "LLM_INFERENCE",
                "failure_component": "LLM_INFERENCE",
                "fault_injection_method": "MAVSDK_EMULATION" if fault_injection_supported else "BEHAVIORAL_ONLY",
                "waypoints": "LLM_GENERATED",
                "weather": "FAA_NARRATIVE" if str(result.weather) != "not_specified" else "LLM_DEFAULT",
                "wind_speed_ms": "LLM_DEFAULT",
                "outcome": "FAA_NARRATIVE" if narrative_facts["outcome_stated"] != "unknown" else "LLM_INFERENCE",
            }
            
            # Determine reconstruction level
            if not fault_injection_supported:
                reconstruction_level = "behavioral_class"  # Can only simulate class of behavior
            elif proxy_modeling["platform_substitution"]:
                reconstruction_level = "proxy_simulation"  # Different platform
            else:
                reconstruction_level = "partial_match"  # Same class, some inferences
            
            config = ScenarioConfig(
                faa_report_id=report_id,
                faa_report_text=faa_report_text[:500],
                
                city=str(result.city),
                state=str(result.state),
                lat=validated_lat,
                lon=validated_lon,
                
                altitude_m=clamped_altitude_m,
                speed_ms=float(result.speed_ms),
                flight_phase=flight_phase,
                uav_model=uav_model,
                
                failure_mode=normalized_failure_mode,
                failure_category=failure_category,
                failure_component=failure_component,
                failure_onset_sec=optimized_onset_sec,
                
                symptoms=symptoms,
                outcome=outcome,
                
                weather=str(result.weather),
                wind_speed_ms=float(result.wind_speed_ms),
                wind_direction_deg=float(result.wind_direction_deg),
                environment=environment,

                waypoints=waypoints,
                
                reasoning=str(result.reasoning),
                
                # Uncertainty & evidence tracking
                uncertainty_score=uncertainty_score,
                fault_injection_supported=fault_injection_supported,
                
                # Narrative vs inferred separation
                narrative_facts=narrative_facts,
                inferred_parameters=inferred_parameters,
                
                # Proxy simulation tags
                proxy_modeling=proxy_modeling,
                
                # Evidence traceability
                evidence_map=evidence_map,
                reconstruction_level=reconstruction_level,
            )
            
            logger.info(f">>>>> Generated: {config.failure_mode} at {config.city}, {config.state} (uncertainty: {uncertainty_score:.2f}, level: {reconstruction_level})")
            return config
            
        except ScenarioGenerationError:
            raise
        except Exception as e:
            raise ScenarioGenerationError(f"LLM generation failed: {e}")
    
    def generate_from_dict(self, sighting: Dict) -> ScenarioConfig:
        """
        Generate from FAA sighting dictionary.
        
        Args:
            sighting: Dictionary containing FAA sighting data.
            
        Returns:
            ScenarioConfig with all simulation parameters.
        """
        report_id = sighting.get("report_id", sighting.get("incident_id", "UNKNOWN"))
        description = str(sighting.get("description", sighting.get("summary", "")) or "")
        if not description.strip():
            raise ScenarioGenerationError("Sighting dict missing description/summary")

        payload = "\n".join(
            [
                f"Report ID: {report_id}",
                f"Date: {str(sighting.get('date', '') or '')}",
                f"City: {str(sighting.get('city', '') or '')}",
                f"State: {str(sighting.get('state', '') or '')}",
                f"Description: {description}",
            ]
        )

        return self.generate(
            faa_report_text=payload,
            report_id=report_id,
        )
    
    def generate_n_best(
        self, 
        faa_report_text: str, 
        report_id: str,
        n: int = 3,
        temperature: float = 0.9,
        max_retries: int = 10,
    ) -> List[ScenarioConfig]:
        """
        Generate N alternative interpretations of an ambiguous FAA report.
        
        Uses increased LLM temperature to sample diverse failure mode interpretations,
        altitude inferences, and fault categorizations for ambiguous narratives.
        
        **Use Case:** URS (Uncertainty Robustness Score) evaluation  
        - Compute behavioral divergence across N configs  
        - Assess verdict stability under ambiguity  
        - Identify high-uncertainty narratives requiring human review
        
        Args:
            faa_report_text: Complete FAA UAS sighting report text
            report_id: Unique identifier for the report
            n: Number of alternative configs to generate (default: 3)
            temperature: LLM sampling temperature for diversity (0.7-1.0 recommended)
            max_retries: Maximum attempts to get N unique configs (default: 10)
            
        Returns:
            List[ScenarioConfig]: N alternative configurations (may be < n if duplicates)
            
        Raises:
            ScenarioGenerationError: If generation fails
            
        Example:
            >>> generator = ScenarioGenerator()
            >>> configs = generator.generate_n_best(faa_report, "FAA_123", n=5, temperature=0.9)
            >>> print(f"Generated {len(configs)} unique interpretations")
            >>> failure_modes = [cfg.failure_mode for cfg in configs]
            >>> print(f"Failure mode diversity: {set(failure_modes)}")
        """
        if not self.is_ready:
            raise ScenarioGenerationError("Generator not initialized")
        
        if not faa_report_text or len(faa_report_text.strip()) < 20:
            raise ScenarioGenerationError("FAA report text is empty or too short")
        
        if n < 1:
            raise ValueError("n must be >= 1")
        
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature must be in [0.0, 2.0]")
        
        logger.info(f"Generating N={n} alternative configs for {report_id} (temp={temperature})")
        
        # Store original temperature
        original_temp = getattr(self.lm, 'temperature', None)
        original_top_p = getattr(self.lm, 'top_p', None)
        
        configs: List[ScenarioConfig] = []
        seen_signatures: set = set()  # Track unique configs by key fields
        
        try:
            # Temporarily increase temperature for diversity
            if hasattr(self.lm, 'kwargs'):
                self.lm.kwargs['temperature'] = temperature
                self.lm.kwargs['top_p'] = 0.95  # Nucleus sampling for diversity
            
            attempts = 0
            while len(configs) < n and attempts < max_retries:
                attempts += 1
                
                try:
                    # Generate one config
                    config = self.generate(faa_report_text, f"{report_id}_alt{attempts}")
                    
                    # Create signature for deduplication
                    signature = (
                        config.failure_mode,
                        config.failure_category,
                        round(config.altitude_m, 0),  # Round to avoid float precision diffs
                        config.uav_model,
                        round(config.lat, 3),  # Round coords to ~100m precision
                        round(config.lon, 3),
                    )
                    
                    # Only add if unique
                    if signature not in seen_signatures:
                        configs.append(config)
                        seen_signatures.add(signature)
                        logger.info(
                            f"  Alt {len(configs)}/{n}: {config.failure_mode} @ "
                            f"{config.altitude_m:.0f}m, {config.uav_model}"
                        )
                    else:
                        logger.debug(f"  Duplicate config (attempt {attempts}), retrying...")
                
                except ScenarioGenerationError as e:
                    logger.warning(f"  Generation attempt {attempts} failed: {e}")
                    continue
            
            if len(configs) < n:
                logger.warning(
                    f"Only generated {len(configs)}/{n} unique configs after {attempts} attempts"
                )
            else:
                logger.info(f"Successfully generated {n} diverse configs in {attempts} attempts")
            
            # Compute diversity metrics for logging
            if len(configs) > 1:
                failure_modes = [c.failure_mode for c in configs]
                altitudes = [c.altitude_m for c in configs]
                uav_models = [c.uav_model for c in configs]
                
                logger.info(
                    f"  Diversity: {len(set(failure_modes))} failure modes, "
                    f"{len(set(uav_models))} UAV models, "
                    f"altitude range [{min(altitudes):.0f}m - {max(altitudes):.0f}m]"
                )
            
            return configs
            
        finally:
            # Restore original temperature
            if hasattr(self.lm, 'kwargs'):
                if original_temp is not None:
                    self.lm.kwargs['temperature'] = original_temp
                else:
                    self.lm.kwargs.pop('temperature', None)
                
                if original_top_p is not None:
                    self.lm.kwargs['top_p'] = original_top_p
                else:
                    self.lm.kwargs.pop('top_p', None)


# =============================================================================
# Singleton Access
# =============================================================================

_generator: Optional[ScenarioGenerator] = None


def get_scenario_generator() -> ScenarioGenerator:
    """Get scenario generator singleton. Raises if not available."""
    global _generator
    if _generator is None:
        _generator = ScenarioGenerator()
    return _generator


def generate_scenario(faa_report: str, report_id: str) -> ScenarioConfig:
    """Convenience function to generate scenario config from FAA sighting report."""
    return get_scenario_generator().generate(faa_report, report_id)


__all__ = [
    "ScenarioGenerator",
    "ScenarioConfig",
    "ScenarioGenerationError",
    "get_scenario_generator",
    "generate_scenario",
    "MAX_MISSION_DURATION_SEC",
]
