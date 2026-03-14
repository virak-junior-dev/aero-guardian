# AeroGuardian Implementation Step Plan (Latest Agreement)

Date: 2026-03-13

## Plan Dashboard (Operational)

### Completed
- Phase 1: CCR evaluator integrated with fairness guardrail.
- Phase 2: AGI grounding strictness integrated.
- Phase 3: URS implemented with config-only/telemetry/full modes.
- Phase 4: EES exported with ESRI retained as legacy baseline.
- Phase 5: report section intent clarified for analyst and operator audiences.
- Phase 6: multi-case validation and reviewer evidence package completed.

### Updated This Cycle
- Canonical metric terminology standardized across active docs: CCR, BRR, AGI, URS, EES.
- Phase 7 artifacts integrated into verification list and execution path.
- Publication-gate and traceability requirements linked into planning flow.

### In Progress
- Phase 7 manuscript/rebuttal hardening and final consistency checks.

### Next Actions (Priority Order)
1. Close Phase 7 WP1-WP4 acceptance checks against existing evidence artifacts.
2. Verify AGI evidence includes one strong and one penalized recommendation example.
3. Final terminology drift scan across docs markdown and fix only active-plan wording.
4. Mark Phase 7 complete once all completion checks pass.

### Known Blockers / Risks
- N-best standalone test dependency issue remains non-blocking for documentation claims.
- Full real-data end-to-end N-best simulation batch is deferred; must stay explicit in limitations.

## Terminology Alignment
- Primary metric names used in current code and validation artifacts:
   - CCR: Constraint Correctness Rate
   - BRR: Behavior Reproduction Rate
   - AGI: Actionability and Grounding Index
   - URS: Uncertainty Robustness Score
   - EES: End-to-End Evaluation Score
- Note: Older references to CSR/BRS are legacy wording and map to CCR/BRR.

## Goal
Implement the agreed evaluation and reporting upgrades so AeroGuardian is robust for FAA analyst workflow and operator advisory support after analyst confirmation.

## Primary Publication Focus

- Reviewer-facing core value is not verdict wording (GO/CAUTION/NO-GO) alone.
- Core defended contribution is high-quality analysis that produces:
   1. aircraft system design constraints (design of what)
   2. mitigation recommendations (recommend what, for whom, under what measurable condition)
   3. evidence traceability from narrative and telemetry to each constraint/recommendation

Priority rule for manuscript and rebuttal:
- If trade-off is needed, prioritize Section 2 quality (constraints/recommendations) and Section 3 traceability over decision-label emphasis.

## Governance Rule: Reviewer Feedback Handling
- Reviewer comments are used to guide research framing, validation design, and documentation quality.
- Do not insert reviewer commentary text into source code comments.
- Keep reviewer-oriented discussion in docs/rebuttal artifacts and keep source code comments technical and implementation-focused.

## Phase 0: Baseline Lock and Verification
1. Freeze baseline outputs for reference:
   - Keep one representative output set in outputs for before/after comparison.
2. Confirm pipeline entry and report generation paths:
   - scripts/run_automated_pipeline.py
   - src/reporting/unified_reporter.py
   - src/core/pdf_report_generator.py
3. Acceptance:
   - Baseline artifacts are reproducible before migration changes.

## Phase 1: Narrative->Config Evaluation Upgrade (CCR)
1. Add primary metric module:
   - src/evaluation/constraint_correctness.py
2. Use reference-based adjudication statuses:
   - exact_match, equivalent_match, better_specificity, contradiction, missing
3. Enforce fairness guardrail:
   - deterministic parser is baseline reference, not oracle truth
   - better valid specificity receives benefit, not penalty
4. Integrate CCR into case evaluator:
   - src/evaluation/evaluate_case.py
   - keep legacy alias mapping documented for backward compatibility
5. Acceptance:
   - evaluation JSON contains CCR and assessment list
   - no regression in existing ESRI output fields

## Phase 2: Report Grounding Upgrade (AGI Strictness)
1. Tighten recommendation verification in:
   - src/evaluation/evidence_consistency.py
2. Add hard penalties for:
   - generic non-actionable recommendations
   - claims without telemetry traceability
3. Add positive checks for:
   - subsystem specificity
   - measurable threshold/action criterion
   - timeline linkage to anomalies
4. Acceptance:
   - previous generic recommendations no longer score as fully supported
   - AGI evaluation details explicitly show penalties and reasons

## Phase 3: Ambiguity Robustness (URS)
1. Add URS evaluation module:
   - src/evaluation/uncertainty_robustness.py
2. URS inputs and modes:
   - top-N alternative feasible configs
   - verdict stability across N
   - trajectory spread and behavioral divergence across alternatives
   - evaluation modes: config-only, telemetry, full evaluation
3. Integrate URS into case evaluation output (without breaking existing consumers).
4. Acceptance:
   - URS field appears in evaluation output
   - if N-best not available, URS reports explicit fallback reason

## Phase 4: Composite Score Transition (EES)
1. Keep ESRI for backward compatibility and comparison-only usage.
2. Introduce EES in parallel:
   - EES = CCR * BRR * AGI * URS
3. Export both during transition period.
4. Acceptance:
   - evaluation JSON includes both ESRI and EES
   - docs clearly state ESRI comparison-only legacy mode

## Phase 5: Report Component Clarity and Professional Presentation
1. Maintain improved component titles in JSON/PDF.
2. Ensure section intent is explicit:
   - system design constraints
   - operator mitigation recommendations
   - evidence traceability rationale
3. Acceptance:
   - report sections directly answer reviewer concern: "design of what? recommendation for whom?"
4. Design-constraint quality requirements:
   - constraint names target subsystem or operating envelope explicitly
   - each constraint has measurable condition when possible (threshold, bound, trigger)
   - recommendation actor is explicit (analyst, operator, engineering team, regulator)
   - recommendation links to at least one supporting anomaly/evidence statement

## Phase 6: Validation and Demonstration Pack
1. Run representative cases (including DEMO_MOTOR_001).
2. Collect before/after metrics and report excerpts.
3. Build reviewer-facing evidence table:
   - ambiguity handling
   - better_specificity behavior
   - non-generic recommendation enforcement
4. Acceptance:
   - one concise appendix-ready validation summary can be inserted in paper slides/manuscript.

## Phase 7: Manuscript Finalization and Rebuttal Pack
1. Integrate validated findings into manuscript sections:
   - abstract contributions and ambiguity statement
   - methods (N-best generation and URS 3-mode evaluation)
   - results (4-case table, Case 103 bugfix delta, non-contradiction rate)
   - discussion and limitations
2. Build reviewer response matrix:
   - concern -> implemented change -> evidence artifact
3. Build claim-to-evidence traceability package:
   - each manuscript claim mapped to repository artifact
4. Acceptance:
   - submission documents use canonical metric names (CCR, BRR, AGI, URS, EES)
   - every defended claim has artifact traceability
   - Phase 6 evidence is fully represented in manuscript/rebuttal materials
5. Robustness hardening tasks:
   - add publication gate checks (governance, traceability, ambiguity, grounding, reproducibility, statistical integrity)
   - ensure at least one positive and one penalized AGI example are documented
   - ensure all known limitations are explicitly declared with impact and mitigation
6. Completion checks:
   - reviewer response matrix complete and cross-referenced
   - claim-to-evidence traceability complete and cross-referenced
   - no unresolved metric naming drift in docs markdown files

## Execution Order
1. Phase 1 (CCR) -> done first because it is core to fairness concern.
2. Phase 2 (AGI strictness) -> done second because current reports are too lenient.
3. Phase 3 (URS scaffold) -> done third to address multi-trajectory reviewer concern.
4. Phase 4, 5, 6 finalize technical migration and validation package.
5. Phase 7 finalizes manuscript and rebuttal package.

## Current Progress Snapshot
- Phase 1: Completed (CCR integrated with fairness guardrail)
- Phase 2: Completed (AGI strictness applied with recommendation grounding checks)
- Phase 3: Completed (URS enhanced with behavioral divergence and 3 evaluation modes)
- Phase 4: Completed (EES exported with ESRI retained as legacy comparison)
- Phase 5: Completed (report section intent clarified for design and operator guidance)
- Phase 6: Completed (multi-case validation, evidence table, URS summary)
- Phase 7: In progress (manuscript plan, reviewer matrix, and claim-evidence traceability drafted)
- Phase 7 hardening: In progress (publication gates and standardization checks being finalized)
- ESRI policy: Explicitly retained as comparison-only in docs and outputs

## Immediate Execution Queue
1. Validate Phase 7 work package acceptance criteria against current artifacts.
2. Resolve any remaining wording-level inconsistencies in active docs.
3. Freeze Phase 7 status to COMPLETE and lock this plan for submission handoff.

## Where We Are Now (Research Strength Assessment)

- Robustness:
   - STRONG at framework level (CCR/AGI/URS implemented with validation evidence).
- Defensibility:
   - STRONG with minor remaining wording risk (reviewer clarity phrasing and explicit uncertainty statements).
- Evidence maturity:
   - STRONG for internal consistency and multi-case support.
   - LIMITED for full real-data end-to-end N-best batch validation (explicitly documented limitation).

## Core Reality and Risk (Must Be Explicit)

- FAA sighting reports are primarily observational narratives, not accident investigation records.
- AeroGuardian reconstructs plausible mission/fault scenarios for analysis support; it does not claim historical accident reconstruction truth.
- Therefore, publication acceptance depends on defensible evaluation quality, hallucination control, and transparent uncertainty handling.

## Defensibility Strategy (Accuracy + Trust)

### 1. Case-Type Stratified Evaluation

Use two explicit strata in all key results:
1. Observational/ambiguous cases (majority)
2. Confirmed-failure cases (minority but high diagnostic value)

Why:
- Prevents overclaiming by mixing low-certainty and higher-certainty evidence into one number.

Required reporting:
- CCR/BRR/AGI/URS/EES per stratum
- confidence and limitation notes per stratum

### 2. Four-Layer Accuracy Argument

Define accuracy by layer, not one single metric:
1. Translation Accuracy (CCR): narrative -> structured simulation constraints
2. Dynamic Plausibility (BRR): telemetry consistency with expected anomaly behavior
3. Recommendation Grounding (AGI): subsystem/parameter/testability + telemetry causal link
4. Ambiguity Robustness (URS): conclusion stability across feasible alternatives

Why:
- Directly answers reviewer concern on "how accuracy is measured" under high narrative ambiguity.

### 3. Hallucination Control Argument

Demonstrate anti-hallucination through measurable controls:
1. Structured schema outputs for LLM stages
2. Deterministic post-checking (CCR, BRR, AGI)
3. Penalties for unsupported/generic claims
4. Explicit fallback and uncertainty reporting (URS + confidence levels)

Minimum evidence to show:
- unsupported claim count trend
- contradiction counts and examples
- at least one penalized recommendation example and one well-grounded example

### 4. Trust Calibration and Use Boundaries

Operational trust posture:
1. Analyst-assist decision support (primary use)
2. Not safety certification and not autonomous authority
3. Downstream policy/operator use only after analyst and governance review

Must remain explicit in paper and outputs:
- confidence ceilings
- non-authoritative source caveat
- unresolved limitations and mitigations

## Expected Outcomes (What We Solve)

If framework is used by FAA analysts/researchers, expected outcomes are:
1. Faster triage of large narrative volumes with consistent structure.
2. Better reproducibility of analyst reasoning via narrative -> config -> telemetry -> recommendation trace.
3. More actionable pre-flight outputs than text-only descriptive analysis.
4. Explicit uncertainty-aware decisions instead of single-path overconfidence.

## Acceptance Evidence for Submission (Go/No-Go)

Submission GO requires all of the following:
1. Stratified results reported (observational vs confirmed-failure).
2. Four-layer accuracy argument completed with artifact links.
3. Hallucination controls demonstrated with both positive and penalized examples.
4. Reviewer clarity questions fully closed:
   - what is simulated
   - scenarios of what
   - design of what
5. Claims remain bounded to decision-support scope, not accident-truth reconstruction.

## Trust and Adoption Posture

- Intended role:
   - Decision-support framework for FAA sighting analysts, not autonomous final authority.
- Trust-building mechanisms already in place:
   - explicit disclaimers and confidence ceilings
   - evidence traceability from narrative -> config -> telemetry -> recommendation
   - structured causal reporting (root cause subsystem, causal chain, primary hazard)
- Adoption pathway:
   1. analyst-assist mode (internal triage and consistency support)
   2. supervised recommendation mode (analyst-reviewed outputs)
   3. policy-facing advisory mode only after validation expansion and operational approval

## Next Process (Phase Continuation)

1. Close reviewer wording loop (R1, R3) in manuscript-facing language using existing evidence references.
2. Run final acceptance audit across WP1-WP5 and mark pass/fail per item.
3. Apply GO/HOLD rule:
    - GO: all Phase 7 closeout checks pass.
    - HOLD: any unresolved reviewer clarity or ambiguity-evidence linkage remains.

## Phase-by-Phase Detailed Verification (Purpose and Strength)

Use this detailed audit before submission lock.

### Phase 0: Baseline Integrity
- Check:
   - baseline outputs reproducible
   - entry/report paths stable
- Pass condition:
   - no unexplained baseline drift

### Phase 1: Narrative-to-Config Correctness
- Check:
   - CCR field-level adjudication quality
   - better_specificity used correctly (not penalized)
- Pass condition:
   - contradictions are explainable and not regex/parser artifacts

### Phase 2: Recommendation Grounding
- Check:
   - AGI penalizes generic claims
   - subsystem + parameter + causal link present for strong recommendations
- Pass condition:
   - at least one high-quality grounded recommendation and one penalized generic example documented

### Phase 3: Ambiguity Handling
- Check:
   - URS mode-aware reporting present
   - fallback reason explicit when alternatives missing
- Pass condition:
   - reviewer concern on trajectory multiplicity is directly answered

### Phase 4: Composite Metric Governance
- Check:
   - EES formula and component names consistent
   - ESRI framed as legacy comparison only
- Pass condition:
   - no naming or formula drift in active docs

### Phase 5: Design Constraint and Recommendation Quality (Critical)
- Check:
   - Section 2 content answers "design what" and "recommend what"
   - constraints are actionable and scoped to aircraft system/operations
   - recommendations include actor and condition
- Pass condition:
   - Section 2 stands as primary defended contribution independent of verdict labels

### Phase 6: Multi-Case Validation Evidence
- Check:
   - case table, bugfix deltas, contradiction accounting, non-contradiction rate
- Pass condition:
   - evidence supports robustness claims without overgeneralization

### Phase 7: Manuscript and Rebuttal Closure
- Check:
   - purpose-first framing
   - prior-work delta positioning
   - trust boundaries and limitations explicit
- Pass condition:
   - all checklist gates pass and GO decision is justified

## Deep Audit Iteration 1 (2026-03-13, evidence refresh)

Data source used for this audit:
- outputs/verification/validation_results.json (refreshed run)
- outputs/verification/validation_results_summary.txt
- outputs/verification/PHASE6_EVIDENCE_TABLE.md
- outputs/verification/URS_ENHANCEMENT_SUMMARY.md

Key refreshed metrics:
- CCR mean: 0.734
- EES mean: 0.1846
- Contradictions: 3 total (2/4 cases with zero contradictions)
- Better specificity: 7 total
- AGI now non-zero across cases (0.501 to 0.827), confirming evaluator/report alignment fix

### Phase Status (PASS/HOLD)

1. Phase 0 (Baseline integrity): PASS
- Rationale: artifacts reproducible and available for all 4 selected cases.

2. Phase 1 (Narrative->Config correctness): PASS
- Rationale: CCR mean 0.734 with known contradictions explicit and explainable.
- Strength: better_specificity logic and altitude-context bugfix validated.

3. Phase 2 (Recommendation grounding): PASS-WITH-ACTION
- Rationale: AGI is now active and non-zero; unsupported claims are surfaced.
- Action: keep one strong and one penalized recommendation example as mandatory manuscript evidence.

4. Phase 3 (Ambiguity robustness): HOLD-WITH-BOUNDARY
- Rationale: URS framework and 3-mode logic validated, but multi-case run still uses fallback URS=0.5 (no real N-best alternatives passed in those runs).
- Action: maintain explicit boundary statement and avoid overclaiming full ambiguity closure for all production cases.

5. Phase 4 (Composite governance): PASS
- Rationale: canonical formula and labels now BRR-first in evaluator score policy.
- Action: preserve aliases only for backward compatibility.

6. Phase 5 (Design constraints/recommendations quality): PASS-WITH-ACTION (CRITICAL)
- Rationale: structured Section 2 is in place and evaluator supports recommendation penalties.
- Action: elevate Section 2 evidence block in manuscript (design-of-what, recommend-what, actor, trigger, evidence link).

7. Phase 6 (Validation evidence): PASS
- Rationale: refreshed summary and case-level outputs support robustness claims with explicit limitations.

8. Phase 7 (Submission closure): IN PROGRESS
- Remaining blockers to GO:
   - finalize Section 2 flagship evidence block (positive + penalized examples)
   - lock explicit wording boundaries (decision-support, not accident-truth reconstruction)
   - complete final checklist pass across all Phase 7 gates

## Verification Artifacts (Current)
- outputs/verification/PHASE6_EVIDENCE_TABLE.md
- outputs/verification/URS_ENHANCEMENT_SUMMARY.md
- outputs/verification/COMPREHENSIVE_VALIDATION_SUMMARY.md
- outputs/verification/validation_results.json
- BUGFIX_REPORT_20260313.md
- docs/PHASE7_MANUSCRIPT_FINALIZATION_PLAN.md
- docs/REVIEWER_RESPONSE_MATRIX_20260313.md
- docs/MANUSCRIPT_CLAIM_EVIDENCE_TRACEABILITY_20260313.md
- docs/EVALUATION_FRAMEWORK_PUBLICATION_STANDARD_20260313.md
