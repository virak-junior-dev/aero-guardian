# Evaluation Framework Publication Standard

Date: 2026-03-13  
Status: Active Standard

## 1. Purpose
Define the canonical, publication-defensible standard for AeroGuardian evaluation terminology, formulas, evidence traceability, and acceptance gates.

## 2. Canonical Vocabulary
- CCR: Constraint Correctness Rate
- BRR: Behavior Reproduction Rate
- AGI: Actionability and Grounding Index
- URS: Uncertainty Robustness Score
- EES: End-to-End Evaluation Score
- ESRI: Legacy comparison-only baseline

Legacy aliases (SFS, ECC, CSR, BRS) may appear only as historical references.

## 3. Canonical Composite Formula
EES = CCR * BRR * AGI * URS

Interpretation:
- Higher score means stronger end-to-end internal consistency under validated evidence.
- EES is a trust-oriented internal metric, not certification evidence by itself.

## 4. Component Standards

### 4.1 CCR Standard
- Must use field-level adjudication with statuses:
  - exact_match, equivalent_match, better_specificity, contradiction, missing
- Fairness guardrail is mandatory:
  - better_specificity is not penalized when physically/regulatorily valid.

### 4.2 BRR Standard
- Deterministic telemetry evaluation only.
- Threshold rationale must be explicit and data-driven where possible (mu + k*sigma) with fallback defaults documented.

### 4.3 AGI Standard
Each recommendation should be judged on:
- subsystem specificity
- numeric actionability
- causal telemetry grounding
- verifiability

Generic recommendations without measurable criteria must be penalized.

### 4.4 URS Standard
- Support mode-aware reporting:
  - config-only
  - telemetry
  - full evaluation
- If alternatives are unavailable, fallback reason must be explicit.
- Ambiguity discussion must include trajectory spread/divergence evidence.

## 5. Traceability Standard
Every defended manuscript claim must include:
1. one primary evidence artifact path
2. one verification note describing why the artifact supports the claim
3. caveat text if the claim depends on approximations or deferred validation

## 6. Statistical and Reporting Standard
- Report both aggregate and per-case metrics.
- Preserve at least one before/after bugfix delta in Results.
- Keep contradiction and non-contradiction accounting explicit.

## 7. Reproducibility Standard
- Include executable command set and expected artifact outputs in reviewer-facing docs.
- Keep environment and dependency limitations explicit.
- Any deferred tests must be clearly labeled as non-blocking with rationale.

## 8. Publication Gate (Pass/Fail)
A release is publication-ready only if all are true:
1. Metric terminology is canonical across docs markdown files.
2. EES formula and component definitions are consistent across plan, methods, and traceability docs.
3. Reviewer concern mapping and claim-evidence mapping are complete.
4. Known limitations and mitigations are declared.
5. Validation evidence artifacts are linked and reproducible.

## 9. Source Documents
- docs/IMPLEMENTATION_STEP_PLAN_LATEST.md
- docs/DASC2026_STRONG_EVAL_UPGRADE.md
- docs/PHASE7_MANUSCRIPT_FINALIZATION_PLAN.md
- docs/REVIEWER_RESPONSE_MATRIX_20260313.md
- docs/MANUSCRIPT_CLAIM_EVIDENCE_TRACEABILITY_20260313.md
