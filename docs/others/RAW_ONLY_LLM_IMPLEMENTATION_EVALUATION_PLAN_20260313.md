# AeroGuardian Raw-Only LLM Input Plan (Implementation + Evaluation)

Date: 2026-03-14
Owner: AeroGuardian Team
Status: Active execution plan

## 1. Purpose

This plan enforces a strict raw-only policy for LLM #1 scenario generation.
Only original FAA source evidence is allowed into prompt construction.

Primary goals:
1. Eliminate heuristic-label leakage into LLM inference.
2. Preserve end-to-end traceability from raw FAA source fields.
3. Keep evaluation reproducible and scientifically auditable.
4. Maintain publication-grade reporting quality under one canonical mode.

## 2. Core Policy

Single-mode policy:
1. Use only `raw_only` behavior for LLM #1.
2. Do not use or report hinted-mode comparisons in the primary workflow.
3. Treat derived labels as downstream analytics only, not LLM prompt inputs.

## 3. Raw Input Contract for LLM #1

Allowed fields:
1. `description` (original narrative text)
2. `date`
3. `city`
4. `state`
5. `report_id`

Disallowed fields:
1. `fault_type`
2. `hazard_category`
3. `classification`
4. `classification_confidence`
5. any heuristic or derived hint field

Prompt serialization shape:
1. Narrative block
2. Original metadata block (`report_id`, `date`, `city`, `state`)

## 4. Implementation Scope

In scope:
1. Enforce raw-only prompt construction in `src/llm/client.py`.
2. Keep deterministic post-parse validation in scenario generation.
3. Use one canonical raw-only runner for reproducible evaluation.
4. Produce standardized per-case and aggregate metric artifacts.

Out of scope:
1. Re-introducing dual-mode ablation in production workflow.
2. Using LLM-as-judge as primary truth.

## 5. Canonical Execution Flow

Step A: Build case list
1. Freeze a fixed case file or use predefined demo cases.
2. Record case IDs in output metadata.

Step B: Generate in raw-only mode
1. Run the canonical runner:
2. `python scripts/run_raw_only_evaluation.py --headless --data-source sightings`

Step C: Validate outputs
1. Confirm output artifacts exist in `outputs/verification/`.
2. Confirm report contains per-case metrics and mean metrics.
3. Confirm run metadata includes command settings and timestamp.

Step D: Quality gates
1. CCR, BRR, AGI, URS, EES must all be present.
2. Contradiction count must stay under configured threshold.
3. Schema validity must pass for all generated cases.

Step E: Remediation loop
1. If quality gates fail, adjust prompt/schema constraints only.
2. Re-run raw-only evaluation.
3. Stop after 3 failed remediation cycles and issue HOLD note.

## 6. Evaluation Matrix (Raw-Only)

Report the following per case and mean:
1. CCR
2. BRR
3. AGI
4. URS
5. EES
6. contradiction_count
7. better_specificity_count

Statistical reporting:
1. Include confidence intervals where feasible.
2. Use bootstrap summaries for aggregate metrics when sample size permits.

## 7. Risk Controls

1. Never inject derived hints into LLM #1 prompt text.
2. Keep case set fixed between repeated runs.
3. Preserve source traceability fields in generated artifacts.
4. Record all run parameters for reproducibility.

## 8. Deliverables

1. Raw-only code enforcement in LLM client.
2. Canonical runner: `scripts/run_raw_only_evaluation.py`.
3. Raw-only evaluation artifacts in `outputs/verification/`.
4. Reviewer-ready summary with metrics and methodology notes.

## 9. Immediate Checklist

1. Verify no residual compare/hinted references in active scripts.
2. Execute `run_raw_only_evaluation.py` smoke run.
3. Confirm artifact naming and storage are standardized.
4. Document any HOLD risks and mitigation steps.
