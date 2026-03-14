# AeroGuardian Evaluation Upgrades V2 - Task Breakdown

## 1. Claude AI Migration (DSPy)
- [x] Implement flexible LLM connector in `src/llm/llm_setup.py` (Strategy Pattern factory).
- [x] Default to Claude for current testing phase.
- [x] Optimize DSPy Signatures to be universally robust for ALL models.

## 2. Model-Specific DSPy Prompt Enhancers
- [x] Create `src/llm/prompt_enhancers.py` with `BasePromptEnhancer`, `AnthropicEnhancer`, `OpenAIEnhancer`.
- [x] Add `get_provider()` utility to `llm_setup.py`.
- [x] Integrate enhancers into `scenario_generator.py` (LLM1).
- [x] Integrate enhancers into `report_generator.py` (LLM2).

## 3. Dynamic UAV Model Configuration (PX4)
- [x] Update `scenario_generator.py` DSPy signature to extract `uav_model`.
- [x] Update `run_automated_pipeline.py` with `PX4_SYS_AUTOSTART` mapping.

## 4. Architecture Cleanup & Telemetry
- [x] Remove legacy code and emojis from logging.
- [x] Ensure LLM2 receives both FAA narrative and MAVSDK metrics.

## 5. RFlyMAD Validation & Metrics (3-Sigma Upgrade + CSV Report)
- [x] Write `src/evaluation/rflymad_validation.py` with real ALFA data.
- [x] Compute 3-sigma statistical baselines from ALFA normal flights.
- [x] Replace hardcoded thresholds with statistically derived bounds.
- [x] Add per-class F1 bar chart alongside confusion matrix.
- [x] Export detailed CSV report (per-window + summary).
- [x] Fix low F1 by combining Propulsion/Control logic (Quadcopters spin when motors die).

## 6. Final Architecture Documentation
- [x] Generate updated Mermaid diagrams.
