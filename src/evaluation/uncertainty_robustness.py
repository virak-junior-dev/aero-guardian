"""
Uncertainty Robustness Score (URS)
==================================
Author: AeroGuardian Team
Date: 2026-03-12
Updated: 2026-03-13

Enhanced metric for ambiguity robustness under narrative uncertainty.

URS is designed to address the concern about many possible trajectories
for a single natural-language incident narrative.

**ENHANCEMENTS (2026-03-13):**
- Behavioral divergence metrics from telemetry data (position spread, velocity)
- Trajectory-based spread calculation using actual simulated paths
- Integration with N-best configuration generation
- Verdict stability from full evaluation reports (not just config metadata)
- Confidence estimation based on sample size and metric reliability
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class URSResult:
    """Result of uncertainty robustness evaluation."""

    score: float = 0.0
    alternative_count: int = 0
    verdict_stability: float = 0.0
    trajectory_spread: float = 1.0
    behavioral_divergence: float = 0.0  # NEW: Telemetry-based divergence
    position_spread_m: float = 0.0      # NEW: Max position deviation
    velocity_divergence: float = 0.0    # NEW: Velocity spread
    confidence: str = "LOW"
    fallback_reason: Optional[str] = None
    diagnostics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "URS": round(self.score, 3),
            "alternative_count": self.alternative_count,
            "verdict_stability": round(self.verdict_stability, 3),
            "trajectory_spread": round(self.trajectory_spread, 3),
            "behavioral_divergence": round(self.behavioral_divergence, 3),
            "position_spread_m": round(self.position_spread_m, 1),
            "velocity_divergence": round(self.velocity_divergence, 3),
            "confidence": self.confidence,
            "fallback_reason": self.fallback_reason,
            "diagnostics": self.diagnostics,
        }


class UncertaintyRobustnessEvaluator:
    """
    Evaluate verdict stability under top-N feasible alternative configurations.

    **ENHANCED IMPLEMENTATION (2026-03-13):**
    - Uses actual telemetry data for trajectory divergence
    - Computes behavioral spread metrics (position, velocity, altitude)
    - Extracts verdicts from full evaluation reports (not just config)
    - Returns detailed diagnostics for debugging and visualization
    
    **Input Modes:**
    1. **Config-Only Mode** (legacy): Only configs provided → signature-based spread
    2. **Telemetry Mode** (enhanced): Configs + telemetry → behavioral divergence
    3. **Full Evaluation Mode** (optimal): Configs + telemetry + reports → verdict stability
    """

    def evaluate(
        self,
        primary_config: Dict,
        alternative_configs: Optional[List[Dict]] = None,
        primary_telemetry: Optional[List[Dict]] = None,
        alternative_telemetries: Optional[List[List[Dict]]] = None,
        primary_report: Optional[Dict] = None,
        alternative_reports: Optional[List[Dict]] = None,
        base_verdict: Optional[str] = None,
    ) -> URSResult:
        """
        Evaluate uncertainty robustness with optional telemetry and reports.
        
        Args:
            primary_config: Primary LLM-generated configuration
            alternative_configs: N-1 alternative configs from generate_n_best()
            primary_telemetry: Telemetry from primary config simulation
            alternative_telemetries: Telemetries from alternative config simulations
            primary_report: Evaluation report for primary config
            alternative_reports: Evaluation reports for alternative configs
            base_verdict: Fallback verdict if not in reports
            
        Returns:
            URSResult with score, stability, spread, and diagnostics
        """
        alternatives = alternative_configs or []
        
        # FALLBACK MODE: No alternatives available
        if not alternatives:
            return URSResult(
                score=0.5,
                alternative_count=0,
                verdict_stability=0.5,
                trajectory_spread=0.5,
                behavioral_divergence=0.0,
                confidence="LOW",
                fallback_reason=(
                    "Top-N alternative feasible configurations are not available; "
                    "returning neutral scaffold score."
                ),
                diagnostics={
                    "mode": "fallback",
                    "base_verdict": (base_verdict or "UNKNOWN"),
                },
            )

        all_configs = [primary_config] + alternatives
        n_configs = len(all_configs)
        
        # Determine evaluation mode
        has_telemetry = (
            primary_telemetry is not None and 
            alternative_telemetries is not None and
            len(alternative_telemetries) == len(alternatives)
        )
        has_reports = (
            primary_report is not None and
            alternative_reports is not None and
            len(alternative_reports) == len(alternatives)
        )
        
        mode = "config_only"
        if has_telemetry and has_reports:
            mode = "full_evaluation"
        elif has_telemetry:
            mode = "telemetry"
        
        # =====================================================================
        # VERDICT STABILITY: Agreement rate across alternatives
        # =====================================================================
        if has_reports:
            all_reports = [primary_report] + alternative_reports
            verdicts = [self._extract_verdict_from_report(r, base_verdict) for r in all_reports]
        else:
            verdicts = [self._extract_verdict(c, base_verdict) for c in all_configs]
        
        primary_verdict = verdicts[0]
        same_verdict = sum(1 for v in verdicts if v == primary_verdict)
        verdict_stability = same_verdict / len(verdicts)
        
        # =====================================================================
        # TRAJECTORY SPREAD: Diversity in configuration parameters
        # =====================================================================
        signatures = [self._config_signature(c) for c in all_configs]
        config_spread = self._normalized_spread(signatures)
        
        # =====================================================================
        # BEHAVIORAL DIVERGENCE: Telemetry-based trajectory analysis (NEW)
        # =====================================================================
        behavioral_divergence = 0.0
        position_spread_m = 0.0
        velocity_divergence = 0.0
        
        if has_telemetry:
            all_telemetries = [primary_telemetry] + alternative_telemetries
            (
                behavioral_divergence,
                position_spread_m,
                velocity_divergence,
            ) = self._compute_behavioral_divergence(all_telemetries)
        
        # =====================================================================
        # URS SCORE COMPUTATION
        # =====================================================================
        if mode == "full_evaluation":
            # Optimal: verdict stability (50%) + behavioral divergence (30%) + config spread (20%)
            score = (
                0.50 * verdict_stability +
                0.30 * (1.0 - behavioral_divergence) +  # Invert: low divergence = high robustness
                0.20 * (1.0 - config_spread)
            )
        elif mode == "telemetry":
            # Good: behavioral divergence (60%) + config spread (40%)
            score = (
                0.60 * (1.0 - behavioral_divergence) +
                0.40 * (1.0 - config_spread)
            )
        else:
            # Legacy: config spread only (verdict stability from configs)
            score = (
                0.65 * verdict_stability +
                0.35 * (1.0 - config_spread)
            )
        
        # Confidence assessment
        if mode == "full_evaluation" and n_configs >= 5:
            confidence = "HIGH"
        elif mode in ["full_evaluation", "telemetry"] and n_configs >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return URSResult(
            score=max(0.0, min(score, 1.0)),
            alternative_count=len(alternatives),
            verdict_stability=verdict_stability,
            trajectory_spread=config_spread,
            behavioral_divergence=behavioral_divergence,
            position_spread_m=position_spread_m,
            velocity_divergence=velocity_divergence,
            confidence=confidence,
            diagnostics={
                "mode": mode,
                "n_configs": n_configs,
                "primary_verdict": primary_verdict,
                "verdicts": verdicts,
                "verdict_distribution": self._verdict_distribution(verdicts),
                "signatures": signatures,
                "has_telemetry": has_telemetry,
                "has_reports": has_reports,
            },
        )
    
    def _compute_behavioral_divergence(
        self, 
        telemetries: List[List[Dict]]
    ) -> Tuple[float, float, float]:
        """
        Compute behavioral divergence from telemetry trajectories.
        
        Returns:
            Tuple of (normalized_divergence, max_position_spread_m, velocity_divergence)
        """
        if not telemetries or len(telemetries) < 2:
            return 0.0, 0.0, 0.0
        
        # Extract positions and velocities at matched timestamps
        # Strategy: for each timestamp in primary, find nearest in alternatives
        primary = telemetries[0]
        alternatives = telemetries[1:]
        
        if not primary:
            return 0.0, 0.0, 0.0
        
        position_spreads = []
        velocity_spreads = []
        
        # Sample every 10th point to avoid excessive computation
        sample_indices = range(0, len(primary), max(1, len(primary) // 20))
        
        for i in sample_indices:
            primary_point = primary[i]
            primary_pos = self._extract_position(primary_point)
            
            if primary_pos is None:
                continue
            
            # Compute primary velocity from position delta if not available
            primary_vel = self._extract_velocity(primary_point)
            if primary_vel is None and i > 0:
                prev_point = primary[i-1]
                prev_pos = self._extract_position(prev_point)
                dt = primary_point.get("timestamp", i) - prev_point.get("timestamp", i-1)
                if prev_pos and dt > 0:
                    primary_vel = (
                        (primary_pos[0] - prev_pos[0]) / dt,
                        (primary_pos[1] - prev_pos[1]) / dt,
                        (primary_pos[2] - prev_pos[2]) / dt,
                    )
            
            # Find corresponding points in alternatives (nearest timestamp)
            alt_positions = []
            alt_velocities = []
            
            for alt_telem in alternatives:
                alt_point = self._find_nearest_timestamp(alt_telem, primary_point.get("timestamp", i))
                if alt_point:
                    alt_pos = self._extract_position(alt_point)
                    if alt_pos:
                        alt_positions.append(alt_pos)
                        
                        # Compute alt velocity from position delta if not available
                        alt_vel = self._extract_velocity(alt_point)
                        if alt_vel is None:
                            # Find previous point in alternative telemetry
                            alt_idx = alt_telem.index(alt_point)
                            if alt_idx > 0:
                                prev_alt_point = alt_telem[alt_idx - 1]
                                prev_alt_pos = self._extract_position(prev_alt_point)
                                dt_alt = alt_point.get("timestamp", alt_idx) - prev_alt_point.get("timestamp", alt_idx-1)
                                if prev_alt_pos and dt_alt > 0:
                                    alt_vel = (
                                        (alt_pos[0] - prev_alt_pos[0]) / dt_alt,
                                        (alt_pos[1] - prev_alt_pos[1]) / dt_alt,
                                        (alt_pos[2] - prev_alt_pos[2]) / dt_alt,
                                    )
                        
                        if alt_vel:
                            alt_velocities.append(alt_vel)
            
            if alt_positions:
                # Compute max distance from primary position
                distances = [self._euclidean_distance_3d(primary_pos, alt_pos) for alt_pos in alt_positions]
                position_spreads.append(max(distances))
            
            if alt_velocities and primary_vel:
                # Compute velocity magnitude differences
                vel_diffs = [abs(self._velocity_magnitude(alt_vel) - self._velocity_magnitude(primary_vel)) 
                             for alt_vel in alt_velocities]
                velocity_spreads.append(max(vel_diffs))
        
        # Aggregate metrics
        max_position_spread_m = max(position_spreads) if position_spreads else 0.0
        mean_position_spread_m = sum(position_spreads) / len(position_spreads) if position_spreads else 0.0
        mean_velocity_divergence = sum(velocity_spreads) / len(velocity_spreads) if velocity_spreads else 0.0
        
        # Normalize spread to [0, 1] range
        # Assumption: 500m position spread = very high divergence (1.0)
        # Assumption: 10 m/s velocity divergence = very high divergence (1.0)
        normalized_position = min(mean_position_spread_m / 500.0, 1.0)
        normalized_velocity = min(mean_velocity_divergence / 10.0, 1.0)
        
        # Combined divergence (60% position, 40% velocity if available, else 100% position)
        if velocity_spreads:
            behavioral_divergence = 0.60 * normalized_position + 0.40 * normalized_velocity
        else:
            behavioral_divergence = normalized_position
        
        return behavioral_divergence, max_position_spread_m, mean_velocity_divergence
    
    def _extract_position(self, point: Dict) -> Optional[Tuple[float, float, float]]:
        """Extract (x, y, z) position from telemetry point.
        
        Handles multiple formats:
        - Local Cartesian: x, y, z or pos_x, pos_y, pos_z
        - GPS: lat, lon, alt (returned directly for spread calculation)
        """
        try:
            # Try local Cartesian first
            x = point.get("x") or point.get("local_x") or point.get("pos_x")
            y = point.get("y") or point.get("local_y") or point.get("pos_y")
            z = point.get("z") or point.get("local_z") or point.get("pos_z") or point.get("altitude")
            
            if x is not None and y is not None and z is not None:
                return (float(x), float(y), float(z))
            
            # Fall back to GPS coordinates (lat, lon, alt)
            # Note: For spread calculation, we treat these as approximate positions
            # (Not geometrically accurate but sufficient for divergence detection)
            lat = point.get("lat")
            lon = point.get("lon")
            alt = point.get("alt") or point.get("relative_alt")
            
            if lat is not None and lon is not None and alt is not None:
                # Convert to approximate local coordinates (1 deg lat ≈ 111km, 1 deg lon ≈ 85km at 40°N)
                # This is rough but sufficient for spread detection
                x_approx = float(lon) * 85000.0  # meters
                y_approx = float(lat) * 111000.0  # meters
                z_approx = float(alt)
                return (x_approx, y_approx, z_approx)
        except (TypeError, ValueError):
            pass
        return None
    
    def _extract_velocity(self, point: Dict) -> Optional[Tuple[float, float, float]]:
        """Extract (vx, vy, vz) velocity from telemetry point.
        
        If velocity not present, returns None (will be computed from position deltas).
        """
        try:
            vx = point.get("vx") or point.get("vel_x")
            vy = point.get("vy") or point.get("vel_y")
            vz = point.get("vz") or point.get("vel_z")
            
            if vx is not None and vy is not None and vz is not None:
                return (float(vx), float(vy), float(vz))
        except (TypeError, ValueError):
            pass
        return None
    
    def _find_nearest_timestamp(self, telemetry: List[Dict], target_time: float) -> Optional[Dict]:
        """Find telemetry point with nearest timestamp to target."""
        if not telemetry:
            return None
        
        best_point = None
        min_diff = float('inf')
        
        for point in telemetry:
            time = point.get("timestamp", point.get("time", 0))
            diff = abs(time - target_time)
            if diff < min_diff:
                min_diff = diff
                best_point = point
        
        return best_point
    
    def _euclidean_distance_3d(self, pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]) -> float:
        """Compute 3D Euclidean distance between two positions."""
        return math.sqrt(
            (pos1[0] - pos2[0])**2 +
            (pos1[1] - pos2[1])**2 +
            (pos1[2] - pos2[2])**2
        )
    
    def _velocity_magnitude(self, vel: Tuple[float, float, float]) -> float:
        """Compute velocity magnitude (speed)."""
        return math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2)
    
    def _extract_verdict_from_report(self, report: Dict, fallback: Optional[str]) -> str:
        """Extract verdict from full evaluation report."""
        # Try multiple possible locations
        verdict = (
            report.get("hazard_level") or
            report.get("safety_level") or
            report.get("risk_level") or
            report.get("severity") or
            fallback or
            "UNKNOWN"
        )
        return str(verdict).upper().strip()
    
    def _verdict_distribution(self, verdicts: List[str]) -> Dict[str, int]:
        """Compute verdict distribution for diagnostics."""
        dist = {}
        for v in verdicts:
            dist[v] = dist.get(v, 0) + 1
        return dist

    def _extract_verdict(self, config: Dict, fallback: Optional[str]) -> str:
        verdict = (
            config.get("safety_level")
            or config.get("hazard_level")
            or config.get("risk_level")
            or fallback
            or "UNKNOWN"
        )
        return str(verdict).upper().strip()

    def _config_signature(self, config: Dict) -> Dict:
        fault = (config.get("fault_injection") or {}).get("fault_type", "unknown")
        timing = (config.get("fault_injection") or {}).get("onset_sec")
        altitude = (config.get("flight_envelope") or {}).get("altitude_m")

        onset_bucket = self._bucket_numeric(timing, [15, 30, 60, 120])
        altitude_bucket = self._bucket_numeric(altitude, [20, 50, 100, 200])

        return {
            "fault_type": str(fault).lower(),
            "onset_bucket": onset_bucket,
            "altitude_bucket": altitude_bucket,
        }

    def _bucket_numeric(self, value, boundaries: List[float]) -> str:
        if value is None:
            return "unknown"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "unknown"

        for boundary in boundaries:
            if numeric <= boundary:
                return f"<= {boundary}"
        return f"> {boundaries[-1]}"

    def _normalized_spread(self, signatures: List[Dict]) -> float:
        if len(signatures) <= 1:
            return 0.0

        unique_fault = len({s["fault_type"] for s in signatures})
        unique_onset = len({s["onset_bucket"] for s in signatures})
        unique_alt = len({s["altitude_bucket"] for s in signatures})

        # Normalize each dimension by sample count.
        n = len(signatures)
        fault_spread = (unique_fault - 1) / max(1, (n - 1))
        onset_spread = (unique_onset - 1) / max(1, (n - 1))
        alt_spread = (unique_alt - 1) / max(1, (n - 1))

        return max(0.0, min((0.5 * fault_spread) + (0.25 * onset_spread) + (0.25 * alt_spread), 1.0))
