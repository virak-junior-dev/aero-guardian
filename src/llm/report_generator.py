"""
Report Generator for AeroGuardian
==================================
Author: AeroGuardian Member
Date: 2026-01-30

Generates pre-flight safety reports from simulation telemetry.
Uses GeneratePreFlightReport DSPy signature.

USAGE:
    from src.llm import ReportGenerator
    
    generator = ReportGenerator()
    report = generator.generate(incident_info, telemetry_summary)
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

import dspy

from .signatures import GeneratePreFlightReport
from .llm_logger import LLMInteractionLogger, get_dspy_history, clear_dspy_history

logger = logging.getLogger("AeroGuardian.ReportGenerator")


# =============================================================================
# Data Classes
# =============================================================================

class ReportGenerationError(Exception):
    """Raised when report generation fails."""


@dataclass
class SafetyReport:
    """Pre-flight safety report - all values from LLM."""
    
    report_id: str
    incident_location: str
    fault_type: str
    expected_outcome: str
    
    # Section 1: Safety Level & Cause
    safety_level: str
    primary_hazard: str
    observed_effect: str
    
    # Section 2: Design Constraints & Recommendations
    design_constraints: list
    recommendations: list
    
    # Section 3: Explanation
    explanation: str
    
    # Final Verdict
    verdict: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Report Generator
# =============================================================================

class ReportGenerator:
    """
    Generate pre-flight safety reports from simulation telemetry.
    
    Uses GeneratePreFlightReport DSPy signature.
    
    USAGE:
        generator = ReportGenerator()
        report = generator.generate(
            incident_description="...",
            incident_id="FAA_xxx",
            incident_location="City, State",
            fault_type="motor_failure",
            expected_outcome="crash",
            telemetry_summary="duration: 120s, max_alt: 50m, ..."
        )
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize report generator with optional output logging."""
        self.is_ready = False
        self._generator = None
        self._output_dir = output_dir
        self._llm_logger: Optional[LLMInteractionLogger] = None
        self._configure()
    
    def _configure(self):
        """Configure DSPy with Universal LLM Factory + model-specific enhancer."""
        try:
            from .llm_setup import get_dspy_lm
            self.lm = get_dspy_lm()
            
            # Use local context instead of global dspy.configure
            self._generator = dspy.ChainOfThought(GeneratePreFlightReport)
            
            # Load model-specific prompt enhancer (Strategy Pattern)
            from .prompt_enhancers import get_enhancer
            self._enhancer = get_enhancer()
            
            # Load few-shot examples
            try:
                from .dspy_fewshot import get_preflight_report_examples
                examples = get_preflight_report_examples()
                if examples:
                    self._generator.demos = examples[:2]
                    logger.info(f"Loaded {len(examples)} few-shot examples")
            except ImportError:
                logger.debug("Few-shot examples not available")
            
            self.is_ready = True
            logger.info(
                f">>>>> ReportGenerator ready | "
                f"Enhancer: {self._enhancer}"
            )
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to initialize LLM: {e}")
    
    def generate(
        self,
        incident_description: str,
        report_id: str,
        incident_location: str,
        fault_type: str,
        expected_outcome: str,
        telemetry_summary: str,
    ) -> SafetyReport:
        """
        Generate pre-flight safety report.
        
        Args:
            incident_description: Original FAA incident narrative
            report_id: FAA report ID
            incident_location: City, State
            fault_type: MOTOR_FAILURE, GPS_LOSS, etc.
            expected_outcome: crash, controlled_landing, flyaway
            telemetry_summary: Telemetry analysis metrics
            
        Returns:
            SafetyReport with all sections
            
        Raises:
            ReportGenerationError on failure
        """
        if not self.is_ready:
            raise ReportGenerationError("Generator not initialized")
        
        if not incident_description:
            raise ReportGenerationError("incident_description required")
        
        logger.info(f"Generating safety report: {report_id}")
        
        # Initialize LLM logger for this request
        if self._output_dir:
            from pathlib import Path
            self._llm_logger = LLMInteractionLogger(
                output_dir=Path(self._output_dir),
                phase=2,
                report_id=report_id
            )
        
        try:
            # Log request start
            input_fields = {
                "incident_description": incident_description,
                "incident_location": incident_location,
                "fault_type": fault_type,
                "expected_outcome": expected_outcome,
                "telemetry_summary": telemetry_summary,
            }
            if self._llm_logger:
                clear_dspy_history(self.lm)  # Clear previous history
                self._llm_logger.log_request_start(
                    "GeneratePreFlightReport",
                    input_fields,
                    model_name=str(getattr(self.lm, "model", "unknown")),
                )

            # Apply model-specific prompt enhancement (additive, DSPy still executes)
            enhanced_telemetry = self._enhancer.enhance_report_prompt(telemetry_summary)

            try:
                with dspy.context(lm=self.lm):
                    result = self._generator(
                        incident_description=incident_description,
                        incident_location=incident_location,
                        fault_type=fault_type,
                        expected_outcome=expected_outcome,
                        telemetry_summary=enhanced_telemetry,
                    )
            except Exception as first_error:
                # Provider/model-specific fallback: Anthropic model may be unavailable
                # in some accounts/regions. Retry once with OpenAI if key is present.
                err_text = str(first_error).lower()
                current_model = str(getattr(self.lm, "model", ""))
                can_retry_openai = bool(os.getenv("OPENAI_API_KEY"))

                if (
                    "not_found_error" in err_text
                    and current_model.startswith("anthropic/")
                    and can_retry_openai
                ):
                    logger.warning(
                        ">>>>> Anthropic model unavailable (%s). Retrying once with OpenAI provider.",
                        current_model,
                    )
                    from .llm_setup import get_dspy_lm_for_provider

                    self.lm = get_dspy_lm_for_provider("openai")
                    with dspy.context(lm=self.lm):
                        result = self._generator(
                            incident_description=incident_description,
                            incident_location=incident_location,
                            fault_type=fault_type,
                            expected_outcome=expected_outcome,
                            telemetry_summary=enhanced_telemetry,
                        )
                else:
                    raise first_error

            # Log response with DSPy history
            if self._llm_logger:
                self._llm_logger.log_response(result, get_dspy_history(self.lm))

            # Parse constraints and recommendations
            constraints = [c.strip() for c in str(result.design_constraints).split("|") if c.strip()]
            recommendations = [r.strip() for r in str(result.recommendations).split("|") if r.strip()]

            report = SafetyReport(
                report_id=report_id,
                incident_location=incident_location,
                fault_type=fault_type,
                expected_outcome=expected_outcome,

                safety_level=str(result.safety_level),
                primary_hazard=str(result.primary_hazard),
                observed_effect=str(result.observed_effect),

                design_constraints=constraints,
                recommendations=recommendations,

                explanation=str(result.explanation),
                verdict=str(result.verdict),
            )

            logger.info(f">>>>> Generated report: {report.safety_level} / {report.verdict}")
            return report

        except ReportGenerationError:
            raise
        except Exception as e:
            raise ReportGenerationError(f"LLM generation failed: {e}")


# =============================================================================
# Singleton Access
# =============================================================================

_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Get report generator singleton. Raises if not available."""
    global _generator
    if _generator is None:
        _generator = ReportGenerator()
    return _generator


__all__ = [
    "ReportGenerator",
    "SafetyReport",
    "ReportGenerationError",
    "get_report_generator",
]
