# Optimized LLM Signatures for AeroGuardian

## 1. LLM #1: FAA_To_PX4_Complete (Scenario Generator)
*   **Input Fields:**
    *   `raw_faa_report_text`: The original narrative.
    *   `physics_informed_context`: The output from the "Hard-Code + Physics" layer (e.g., `validated_altitude_m`, `uas_type_guess`, `hazard_category`).
    *   `regulatory_violations`: Specific Part 107/89 rules flagged by the pre-processor.
*   **Output Fields (MAVSDK-Compatible):**
    *   `sim_fault_type`: Must match `FailureCategory` (e.g., `motor_failure`, `gps_loss`).
    *   `sim_fault_severity`: Float (0.0-1.0).
    *   `sim_parachute_trigger`: Boolean.
    *   `waypoints_json`: MAVSDK-compatible mission waypoints.
    *   `reasoning`: Justification for the inferred simulation parameters.

## 2. LLM #2: GeneratePreFlightReport (Safety Intelligence)
*   **Input Fields:**
    *   `faa_report_summary`: The original sighting context.
    *   `validated_telemetry_stats`: The output from `TelemetryAnalyzer` (e.g., `max_roll_deg`, `position_drift_m`).
    *   `brr_score`: Behavior Reproduction Rate from `BehaviorValidator`.
    *   `regulatory_violations`: Specific Part 107/89 rules violated during the simulation.
*   **Output Fields (Regulatory-Aware):**
    *   `safety_level`: Risk classification (e.g., CRITICAL, HIGH).
    *   `primary_hazard`: The identified failure or violation.
    *   `regulatory_violation_summary`: Explicit mention of FAA rules (e.g., "Violation of §107.51: Altitude exceeded 400ft AGL").
    *   `causal_chain`: Traceable explanation from FAA report to telemetry anomalies.
    *   `actionable_guidance`: Specific recommendations for operators or investigators.
