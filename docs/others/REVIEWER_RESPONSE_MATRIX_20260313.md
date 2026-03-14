# Reviewer Response Matrix (2026-03-13)

## Purpose
Provide a concise, evidence-backed mapping from reviewer concerns to implemented changes and verifiable artifacts.

## Matrix

| Reviewer Concern | Implemented Change | Evidence Artifact(s) | Status |
|---|---|---|---|
| Many possible trajectories from one FAA narrative; unclear accuracy under ambiguity | Added N-best generation and URS behavioral divergence metrics with 3 evaluation modes | outputs/verification/URS_ENHANCEMENT_SUMMARY.md; src/evaluation/uncertainty_robustness.py; src/llm/scenario_generator.py | Complete |
| LLM1 evaluation is too weak / parser baseline unfair | Added CCR with adjudication statuses and fairness guardrail (better_specificity) | src/evaluation/constraint_correctness.py; outputs/verification/PHASE6_EVIDENCE_TABLE.md | Complete |
| LLM2 recommendations too generic / weak grounding | Tightened AGI strictness with subsystem/parameter/evidence checks and penalties for generic claims | src/evaluation/evidence_consistency.py; docs/DASC2026_STRONG_EVAL_UPGRADE.md | Complete |
| Contradictions in altitude handling reduce trust | Fixed altitude regex comma parsing and added airspace-context logic | BUGFIX_REPORT_20260313.md; outputs/verification/PHASE6_EVIDENCE_TABLE.md | Complete |
| Need stronger cross-case evidence, not single-case claims | Ran multi-case validation and produced evidence package with aggregate metrics | outputs/verification/validation_results.json; outputs/verification/COMPREHENSIVE_VALIDATION_SUMMARY.md | Complete |
| Composite metric interpretability and transition from legacy score | Introduced EES with canonical components; retained ESRI as legacy comparison-only | docs/IMPLEMENTATION_STEP_PLAN_LATEST.md; docs/DASC2026_STRONG_EVAL_UPGRADE.md | Complete |

## Key Quantitative Anchors
- Mean CCR across 4 cases: 0.734
- Non-contradiction rate: 85%
- Case 103 CCR improvement after bugfixes: 0.485 -> 0.955
- URS enhanced test: behavioral divergence computed and validated (4/5 checks)

## Usage Guidance
- Use this file in rebuttal letter drafting to ensure every claim points to a concrete, reproducible artifact.
- Keep terminology canonical: CCR, BRR, AGI, URS, EES.
