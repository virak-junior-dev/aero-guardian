"""
Model-Specific DSPy Prompt Enhancers
=====================================
Author: AeroGuardian Member
Date: 2026-03-12

Strategy Pattern implementation for model-specific DSPy prompt optimization.
Injects provider-optimized prompt prefixes INTO DSPy signature calls.
DSPy always remains the execution framework -- enhancers are ADDITIVE.

ARCHITECTURE:
    BasePromptEnhancer (universal fallback)
        |-- AnthropicEnhancer (Claude XML blocks, negative constraints)
        |-- OpenAIEnhancer (JSON schema hints, system-role strictness)

USAGE:
    from src.llm.prompt_enhancers import get_enhancer
    enhancer = get_enhancer("anthropic")
    enhanced_input = enhancer.enhance_scenario_prompt(faa_text)
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("AeroGuardian.PromptEnhancers")


# =============================================================================
# BASE ENHANCER (Universal Fallback)
# =============================================================================

class BasePromptEnhancer(ABC):
    """
    Abstract base class for model-specific prompt enhancement.

    Subclasses inject model-optimized instructions INTO DSPy signature
    inputs. DSPy still handles the API call, response parsing, and
    output schema enforcement.

    The base implementation returns the original text unchanged,
    serving as a safe fallback for unknown or unsupported providers.
    """

    provider_name: str = "universal"

    def enhance_scenario_prompt(self, faa_text: str) -> str:
        """
        Enhance LLM1 (scenario generation) input with model-specific
        prompt prefix.

        Args:
            faa_text: Raw FAA sighting narrative text.

        Returns:
            Enhanced text with model-specific instructions prepended.
        """
        return faa_text

    def enhance_report_prompt(self, telemetry_summary: str) -> str:
        """
        Enhance LLM2 (report generation) input with model-specific
        prompt prefix.

        Args:
            telemetry_summary: Formatted telemetry analysis summary.

        Returns:
            Enhanced text with model-specific instructions prepended.
        """
        return telemetry_summary

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider_name}>"


# =============================================================================
# ANTHROPIC (Claude) ENHANCER
# =============================================================================

class AnthropicEnhancer(BasePromptEnhancer):
    """
    Claude-optimized prompt enhancer.

    Exploits Anthropic's native XML parsing, negative constraint blocks,
    and structured thinking patterns to maximize output quality.

    KEY TECHNIQUES:
        1. <thinking> blocks  -- Claude deeply respects XML-tagged
           reasoning sections, producing more thorough analysis.
        2. <forbidden> blocks -- Explicit prohibition lists that Claude
           treats as hard constraints (stronger than plain-text "do not").
        3. <output_rules> blocks -- ENUM validation and format enforcement
           that Claude parses as structured directives.
    """

    provider_name: str = "anthropic"

    _SCENARIO_PREFIX = (
        "<output_rules>\n"
        "You MUST output exact ENUM string matches for these fields:\n"
        "- failure_mode: ONLY one of [motor_failure, gps_loss, gps_dropout, "
        "battery_failure, battery_depletion, control_loss, control_signal_loss, "
        "sensor_failure, compass_error, geofence_violation, altitude_violation, flyaway]\n"
        "- uav_model: ONLY one of [iris, plane, standard_vtol]\n"
        "- failure_category: ONLY one of [propulsion, navigation, power, control, "
        "environmental, airspace_violation]\n"
        "</output_rules>\n\n"
        "<forbidden>\n"
        "- Do NOT hallucinate coordinates. If you cannot geocode the city, "
        "use approximate US regional coordinates.\n"
        "- Do NOT invent failure modes not listed in the ENUM set above.\n"
        "- Do NOT produce waypoints with altitudes exceeding 120 meters.\n"
        "- Do NOT leave any output field blank or null.\n"
        "</forbidden>\n\n"
        "<thinking>\n"
        "Before generating the output, reason step-by-step:\n"
        "1. What location is described? Extract city, state, approximate lat/lon.\n"
        "2. What behavior is described? Map to the closest failure_mode ENUM.\n"
        "3. What aircraft type is implied? Map to uav_model ENUM.\n"
        "4. Generate waypoints that replicate the described flight path.\n"
        "</thinking>\n\n"
        "FAA SIGHTING REPORT:\n"
    )

    _REPORT_PREFIX = (
        "<output_rules>\n"
        "- safety_level MUST be one of: CRITICAL, HIGH, MEDIUM, LOW\n"
        "- verdict MUST be one of: GO, CAUTION, NO-GO\n"
        "- primary_hazard MUST start with 'Simulated:'\n"
        "- observed_effect MUST start with 'In simulation:'\n"
        "- All design constraints MUST cite specific numbers from the "
        "telemetry data below. Generic advice scores AGI = 0.\n"
        "</output_rules>\n\n"
        "<forbidden>\n"
        "- Do NOT recommend actions for subsystems that showed NO anomalies.\n"
        "- Do NOT claim telemetry showed anomalies if the data is nominal.\n"
        "- Do NOT use vague language like 'ensure safety' without numbers.\n"
        "</forbidden>\n\n"
        "<thinking>\n"
        "Before generating the report:\n"
        "1. Parse every metric in the telemetry summary below.\n"
        "2. Identify which metrics exceed normal operating bounds.\n"
        "3. Trace each recommendation back to a specific anomaly.\n"
        "4. If no anomalies exist, declare GO with justification.\n"
        "</thinking>\n\n"
        "TELEMETRY ANALYSIS:\n"
    )

    def enhance_scenario_prompt(self, faa_text: str) -> str:
        """Prepend Claude XML blocks to FAA text for LLM1."""
        return f"{self._SCENARIO_PREFIX}{faa_text}"

    def enhance_report_prompt(self, telemetry_summary: str) -> str:
        """Prepend Claude XML blocks to telemetry summary for LLM2."""
        return f"{self._REPORT_PREFIX}{telemetry_summary}"


# =============================================================================
# OPENAI (GPT-4 / o1 / o3) ENHANCER
# =============================================================================

class OpenAIEnhancer(BasePromptEnhancer):
    """
    OpenAI-optimized prompt enhancer.

    Exploits GPT-family strengths: strict JSON schema enforcement,
    system-role preamble patterns, and function-call-style output
    formatting for maximum structured output reliability.

    KEY TECHNIQUES:
        1. JSON schema hints -- OpenAI models respond strongly to
           explicit JSON structure definitions in the prompt.
        2. System-role strictness -- Preamble that sets behavioral
           boundaries using OpenAI's preferred instruction style.
        3. Negative examples -- "BAD output" vs "GOOD output" pairs
           that GPT models learn from effectively.
    """

    provider_name: str = "openai"

    _SCENARIO_PREFIX = (
        "STRICT OUTPUT RULES (MANDATORY):\n"
        "=================================\n"
        "You are generating a JSON-compatible structured output. "
        "Every field MUST match the exact schema below.\n\n"
        "ENUM CONSTRAINTS (exact string match required):\n"
        "- failure_mode: [motor_failure | gps_loss | gps_dropout | "
        "battery_failure | battery_depletion | control_loss | "
        "control_signal_loss | sensor_failure | compass_error | "
        "geofence_violation | altitude_violation | flyaway]\n"
        "- uav_model: [iris | plane | standard_vtol]\n"
        "- failure_category: [propulsion | navigation | power | control | "
        "environmental | airspace_violation]\n\n"
        "BAD OUTPUT EXAMPLE (DO NOT DO THIS):\n"
        '  failure_mode: "engine failure"  <-- NOT in ENUM list\n'
        '  uav_model: "quadcopter"  <-- must be "iris"\n\n'
        "GOOD OUTPUT EXAMPLE:\n"
        '  failure_mode: "motor_failure"\n'
        '  uav_model: "iris"\n\n'
        "ANALYZE THIS FAA SIGHTING REPORT:\n"
    )

    _REPORT_PREFIX = (
        "STRICT OUTPUT RULES (MANDATORY):\n"
        "=================================\n"
        "ENUM CONSTRAINTS:\n"
        "- safety_level: [CRITICAL | HIGH | MEDIUM | LOW]\n"
        "- verdict: [GO | CAUTION | NO-GO]\n\n"
        "MATHEMATICAL TRACEABILITY RULE:\n"
        "Every recommendation MUST cite a specific number from the "
        "telemetry data. Generic recommendations without numerical "
        "evidence will be scored AGI = 0 by the evaluation pipeline.\n\n"
        "BAD OUTPUT EXAMPLE:\n"
        '  recommendation: "Check the battery before flight"\n'
        "  (No numbers, no telemetry reference = AGI score 0)\n\n"
        "GOOD OUTPUT EXAMPLE:\n"
        '  recommendation: "Battery voltage dropped 2.1V during flight. '
        'Implement minimum voltage cutoff at 14.2V."\n'
        "  (Cites 2.1V drop, gives specific 14.2V threshold = AGI score 1)\n\n"
        "ANALYZE THIS TELEMETRY DATA:\n"
    )

    def enhance_scenario_prompt(self, faa_text: str) -> str:
        """Prepend OpenAI strictness rules to FAA text for LLM1."""
        return f"{self._SCENARIO_PREFIX}{faa_text}"

    def enhance_report_prompt(self, telemetry_summary: str) -> str:
        """Prepend OpenAI strictness rules to telemetry summary for LLM2."""
        return f"{self._REPORT_PREFIX}{telemetry_summary}"


# =============================================================================
# FACTORY
# =============================================================================

_ENHANCER_REGISTRY = {
    "anthropic": AnthropicEnhancer,
    "openai": OpenAIEnhancer,
}


def get_enhancer(provider: Optional[str] = None) -> BasePromptEnhancer:
    """
    Factory function returning the prompt enhancer for the active provider.

    If no provider is specified, reads from LLM_PROVIDER env var via
    llm_setup.get_provider(). Falls back to BasePromptEnhancer (no-op)
    for unknown providers.

    Args:
        provider: LLM provider name ("anthropic", "openai"), or None
                  to auto-detect from environment.

    Returns:
        Model-specific BasePromptEnhancer subclass instance.
    """
    if provider is None:
        try:
            from .llm_setup import get_provider
            provider = get_provider()
        except ImportError:
            import os
            provider = os.getenv("LLM_PROVIDER", "universal").lower()

    enhancer_cls = _ENHANCER_REGISTRY.get(provider, None)

    if enhancer_cls is None:
        logger.info(
            f">>>>> No model-specific enhancer for provider '{provider}'. "
            f"Using universal (no-op) fallback."
        )
        # Return a concrete no-op instance
        class _UniversalEnhancer(BasePromptEnhancer):
            provider_name = "universal"
        return _UniversalEnhancer()

    enhancer = enhancer_cls()
    logger.info(f">>>>> Loaded {enhancer}")
    return enhancer


__all__ = [
    "BasePromptEnhancer",
    "AnthropicEnhancer",
    "OpenAIEnhancer",
    "get_enhancer",
]
