"""
LLM Configuration Setup
=======================
Author: AeroGuardian Member
Date: 2026-03-12

Flexible strategy pattern for configuring DSPy language models.
Allows seamless switching between Anthropic (Claude) and OpenAI,
optimizing setup parameters based on the provider.
"""

import os
import dspy
import logging
from typing import Dict

logger = logging.getLogger("AeroGuardian.LLMSetup")

class LLMConfigurationError(Exception):
    pass


PROVIDER_ALIASES = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "openai": "openai",
}


ANTHROPIC_MODEL_ALIASES = {
    # Legacy pinned value can be unavailable on some accounts/regions.
    "claude-sonnet-4-5-20250929": "claude-sonnet-4-5-20250929",
}


def normalize_provider(provider: str) -> str:
    """Normalize provider aliases to canonical provider names."""
    return PROVIDER_ALIASES.get((provider or "").strip().lower(), (provider or "").strip().lower())


def get_provider() -> str:
    """Return active provider, defaulting to anthropic for safer cost control."""
    return normalize_provider(os.getenv("LLM_PROVIDER", "anthropic"))


def _provider_key(provider: str) -> str:
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY", "")
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    return ""


def _provider_model(provider: str) -> str:
    if provider == "anthropic":
        raw_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        normalized = ANTHROPIC_MODEL_ALIASES.get(str(raw_model).strip(), str(raw_model).strip())
        if normalized != raw_model:
            logger.warning(
                "Normalizing unsupported Anthropic model '%s' -> '%s'.",
                raw_model,
                normalized,
            )
        return normalized
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o")
    return ""


def _provider_temperature(provider: str, model: str) -> float:
    if provider == "openai":
        is_reasoning = any(x in model.lower() for x in ["o1-", "o3-"])
        return 1.0 if is_reasoning else float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
    return float(os.getenv("ANTHROPIC_TEMPERATURE", "0.1"))


def _provider_max_tokens(provider: str, model: str) -> int:
    if provider == "openai":
        is_reasoning = any(x in model.lower() for x in ["o1-", "o3-"])
        return 16000 if is_reasoning else int(os.getenv("OPENAI_MAX_TOKENS", "4096"))
    return int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))


def get_llm_runtime_config() -> Dict[str, str]:
    """Return resolved provider/model/api-key status used by LLM runtime."""
    provider = get_provider()
    selected_provider = provider
    selected_key = _provider_key(provider)

    # Graceful fallback when current provider is temporarily unavailable.
    if not selected_key:
        fallback = "openai" if provider == "anthropic" else "anthropic"
        fallback_key = _provider_key(fallback)
        if fallback_key:
            logger.warning(
                "Primary provider '%s' has no API key; falling back to '%s'.",
                provider,
                fallback,
            )
            selected_provider = fallback
            selected_key = fallback_key

    model = _provider_model(selected_provider)
    return {
        "requested_provider": provider,
        "provider": selected_provider,
        "model": model,
        "api_key_set": "yes" if bool(selected_key) else "no",
    }

def get_dspy_lm() -> dspy.LM:
    """
    Factory to get the configured DSPy LM instance using the Strategy Pattern.
    Defaults to Anthropic (Claude) but supports OpenAI.
    To switch, set LLM_PROVIDER="openai" or "anthropic" in .env
    """
    requested_provider = get_provider()
    
    try:
        provider = requested_provider
        api_key = _provider_key(provider)
        if not api_key:
            fallback = "openai" if provider == "anthropic" else "anthropic"
            fallback_key = _provider_key(fallback)
            if fallback_key:
                logger.warning(
                    "Requested provider '%s' unavailable (no key). Using '%s' fallback.",
                    provider,
                    fallback,
                )
                provider = fallback
                api_key = fallback_key

        if provider not in {"anthropic", "openai"}:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {requested_provider}. Use 'anthropic', 'claude', or 'openai'."
            )

        if not api_key:
            raise ValueError(
                "No API key available for either ANTHROPIC_API_KEY or OPENAI_API_KEY."
            )

        model = _provider_model(provider)
        temperature = _provider_temperature(provider, model)
        max_tokens = _provider_max_tokens(provider, model)
        logger.info(
            ">>>>> Initializing DSPy connector with provider=%s model=%s max_tokens=%s temp=%.2f",
            provider,
            model,
            max_tokens,
            temperature,
        )

        return dspy.LM(
            model=f"{provider}/{model}",
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
            
    except Exception as e:
        logger.error(f"Failed to initialize LLM connector: {e}")
        raise LLMConfigurationError(f"Connector init failed: {e}")


def get_dspy_lm_for_provider(provider: str) -> dspy.LM:
    """
    Build a DSPy LM for an explicitly requested provider.

    This helper is used for runtime retry/fallback when a provider-specific
    model is unavailable (for example, Anthropic model 404).
    """
    forced_provider = normalize_provider(provider)
    if forced_provider not in {"anthropic", "openai"}:
        raise LLMConfigurationError(
            f"Unknown provider override: {provider}. Use 'anthropic' or 'openai'."
        )

    api_key = _provider_key(forced_provider)
    if not api_key:
        raise LLMConfigurationError(
            f"Provider '{forced_provider}' has no API key configured."
        )

    model = _provider_model(forced_provider)
    temperature = _provider_temperature(forced_provider, model)
    max_tokens = _provider_max_tokens(forced_provider, model)

    logger.info(
        ">>>>> Initializing DSPy connector (forced) provider=%s model=%s max_tokens=%s temp=%.2f",
        forced_provider,
        model,
        max_tokens,
        temperature,
    )
    return dspy.LM(
        model=f"{forced_provider}/{model}",
        api_key=api_key,
        max_tokens=max_tokens,
        temperature=temperature,
    )
