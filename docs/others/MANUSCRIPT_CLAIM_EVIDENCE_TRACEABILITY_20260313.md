# Manuscript Claim-to-Evidence Traceability (2026-03-13)

## Purpose
Map each core manuscript claim to concrete repository artifacts for defensible review and rebuttal.

## Traceability Table

| Manuscript Claim | Evidence Type | Primary Artifact(s) | Verification Note |
|---|---|---|---|
| The framework provides end-to-end narrative-to-safety evaluation, not isolated NLP classification. | Architecture/process | docs/AEROGUARDIAN_END_TO_END_MERMAID.md; docs/DASC2026_STRONG_EVAL_UPGRADE.md | Confirms LLM1 -> PX4 -> deterministic analysis -> LLM2 -> scoring chain. |
| LLM1 evaluation is fairness-aware and avoids penalizing valid specificity. | Metric implementation + case evidence | src/evaluation/constraint_correctness.py; outputs/verification/PHASE6_EVIDENCE_TABLE.md | better_specificity adjudication demonstrated across cases. |
| Critical altitude-evaluation bugs were fixed and materially improved reliability. | Bugfix + before/after metrics | BUGFIX_REPORT_20260313.md; outputs/verification/PHASE6_EVIDENCE_TABLE.md | Case 103 CCR increased 0.485 -> 0.955 after fixes. |
| Cross-case validation supports consistency claims. | Aggregate validation results | outputs/verification/validation_results.json; outputs/verification/COMPREHENSIVE_VALIDATION_SUMMARY.md | 4-case metrics and summary statistics documented. |
| The method addresses narrative ambiguity with N-best alternatives and URS. | Method implementation + test evidence | src/llm/scenario_generator.py; src/evaluation/uncertainty_robustness.py; outputs/verification/URS_ENHANCEMENT_SUMMARY.md | URS behavioral divergence and three-mode evaluation documented. |
| Recommendation quality is evaluated for grounding and actionability, not only style. | Evaluation policy + code | docs/DASC2026_STRONG_EVAL_UPGRADE.md; src/evaluation/evidence_consistency.py | AGI strictness criteria define subsystem/parameter/evidence checks. |
| Composite trust uses canonical upgraded metrics while preserving legacy comparability. | Scoring policy docs | docs/IMPLEMENTATION_STEP_PLAN_LATEST.md; docs/DASC2026_STRONG_EVAL_UPGRADE.md | EES uses CCR, BRR, AGI, URS; ESRI retained as legacy comparison baseline. |
| Compared with prior FAA sighting descriptive analyses, this framework adds executable reconstruction and simulation-validated safety intelligence. | Prior-work delta + architecture evidence | docs/DASC2026_STRONG_EVAL_UPGRADE.md; docs/AEROGUARDIAN_END_TO_END_MERMAID.md; outputs/verification/COMPREHENSIVE_VALIDATION_SUMMARY.md | Prior work is descriptive; this work adds generation -> simulation -> telemetry-grounded recommendations. |

## Claim Strength Levels

Use these levels in manuscript/rebuttal drafting:
- Level A (Direct Measured): Numerical result appears directly in a generated artifact (tables/json/reports).
- Level B (Code-Backed Method): Claim is methodological and directly linked to implementation files.
- Level C (Interpretive): Claim is reasoned from evidence and must include explicit caveat text.

Suggested assignments:
1. Mean CCR, non-contradiction rate, Case 103 delta -> Level A
2. URS three-mode design, N-best generation process -> Level B
3. Generalization and deployment implications -> Level C
4. Prior-work advancement framing (descriptive -> executable validation) -> Level B/C depending on claim strength

## Limitation-to-Claim Mapping

| Limitation | Affected Claim(s) | Required Caveat Language |
|---|---|---|
| N-best standalone test dependency issue | Ambiguity robustness end-to-end completeness | N-best generation is implemented; full real-data E2E validation is partially deferred due to dependency compatibility. |
| Approximate GPS-to-local conversion | Absolute geometric precision claims | Behavioral divergence is valid for comparative spread detection, not geodetic-precision distance estimation. |
| Small validation sample (4 cases) | Broad external generalization claims | Current results demonstrate internal consistency across diverse cases; larger cohort validation is future work. |

## Publication Standard Checklist (Traceability File)

- Every Results number appears in at least one artifact path.
- Every Methods claim has at least one code artifact and one process/policy artifact.
- Every Discussion limitation has an explicit artifact-backed caveat.
- Every rebuttal point can be answered by one row in this file or reviewer matrix.
- Prior-work positioning claims include clear boundary language (complementary advancement, not unsupported superiority).

## Real-World Impact Claim Guidance

Use these impact claims with evidence discipline:
1. Analyst-efficiency potential claim -> phrase as operational motivation unless measured study is provided.
2. Government/operator alerting utility claim -> phrase as downstream applicability contingent on trust and policy adoption.
3. Pre-flight safety intelligence claim -> support with report structure evidence and telemetry-grounding criteria.

## Quantitative Anchors for Results Section

1. Mean CCR across 4 cases: 0.734
2. Non-contradiction rate: 85%
3. Case 103 CCR improvement: 0.485 -> 0.955
4. URS enhanced test: behavioral divergence detected, 4/5 checks passed

Artifacts:
- outputs/verification/COMPREHENSIVE_VALIDATION_SUMMARY.md
- outputs/verification/PHASE6_EVIDENCE_TABLE.md
- outputs/verification/URS_ENHANCEMENT_SUMMARY.md

## Rebuttal Usage Pattern

1. Copy reviewer concern text.
2. Cite one claim row from this table.
3. Reference corresponding artifact paths directly.
4. Include one quantitative anchor when available.

This ensures each rebuttal answer is concrete, reproducible, and evidence-first.
