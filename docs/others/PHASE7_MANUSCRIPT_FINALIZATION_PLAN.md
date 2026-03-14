# Phase 7 Manuscript Finalization Plan

Date: 2026-03-13  
Status: IN PROGRESS

## Status Snapshot

### Already Completed
- Reviewer response matrix drafted and linked to evidence artifacts.
- Claim-to-evidence traceability drafted with quantitative anchors.
- Canonical metric vocabulary standardized in active plan documents.

### Remaining to Close Phase 7
- Final acceptance check for WP1-WP4 against current artifacts.
- Confirm AGI documentation includes both positive and penalized recommendation examples.
- Perform final docs-only terminology drift scan and resolve any active-wording mismatch.
- Reviewer closure wording lock for DASC comments:
	- explicitly state what is simulated (UAS flight dynamics/controller/sensor response in PX4 SITL)
	- explicitly state scenario scope (reconstructed mission and fault scenarios)
	- explicitly state design scope (aircraft system design constraints + operator mitigation recommendations)
- Integrate refreshed validation evidence summary (CCR mean 0.734, EES mean 0.1846, AGI active across all four cases).

## Objective
Convert validated Phase 6 technical outcomes into submission-ready manuscript and rebuttal materials with strict terminology consistency and evidence traceability.

## Purpose-First Framing (Research-Question Agnostic)

Primary real-world problem:
- FAA UAS sighting reports are unstructured, ambiguous, and time-consuming to analyze at scale.

Primary project purpose:
- Convert difficult narrative reports into executable simulation evidence and standardized pre-flight safety intelligence that helps FAA analysts work faster and with better traceability.

Operational beneficiaries:
- Direct: FAA sighting report analysts and safety investigators.
- Downstream (if trust and policy allow): government/operator alerting with evidence-backed design constraints and mitigation recommendations.

Writing rule:
- Manuscript claims must stay purpose-first and evidence-first, not tied to fixed wording of current research questions.

## FAA Analyst Workflow Alignment (Manual -> Framework)

Current manual analyst tasks (problem reality):
1. Read long unstructured narratives and infer key operational facts.
2. Resolve ambiguity (what happened vs. what was observed).
3. Judge risk severity with limited aircraft-state evidence.
4. Decide whether recommendations are operationally actionable.
5. Produce traceable summary outputs under time pressure.

Observed gaps in manual process:
- high time cost per case
- inconsistent interpretation across analysts
- weak reproducibility of reasoning chain
- limited dynamic feasibility checking from text alone
- difficult transition from observation to actionable pre-flight constraints

How AeroGuardian addresses these gaps:
1. Structured extraction from narrative -> executable scenario configuration.
2. PX4 SITL telemetry evidence for dynamic plausibility checks.
3. Causal structuring in report output (root cause subsystem, causal chain, primary hazard).
4. Grounded recommendation scoring (AGI) for actionability and traceability.
5. Standardized report sections for consistent analyst-facing outputs.

Trust argument to include:
- Not a replacement for analyst judgment; a decision-support accelerator with explicit evidence links and documented limitations.

## Inputs (Authoritative Evidence)
- outputs/verification/COMPREHENSIVE_VALIDATION_SUMMARY.md
- outputs/verification/PHASE6_EVIDENCE_TABLE.md
- outputs/verification/URS_ENHANCEMENT_SUMMARY.md
- outputs/verification/validation_results.json
- BUGFIX_REPORT_20260313.md
- docs/DASC2026_STRONG_EVAL_UPGRADE.md
- docs/AEROGUARDIAN_END_TO_END_MERMAID.md

## Canonical Metric Vocabulary
- CCR: Constraint Correctness Rate
- BRR: Behavior Reproduction Rate
- AGI: Actionability and Grounding Index
- URS: Uncertainty Robustness Score
- EES: End-to-End Evaluation Score
- ESRI: Legacy comparison baseline only

## Work Packages

### Priority Declaration
- Primary defended novelty in final narrative is Section 2 quality:
	- aircraft system design constraints
	- mitigation recommendations
	- evidence linkage and actionability
- Decision labels (GO/CAUTION/NO-GO) are secondary summaries, not primary contribution.

### WP1: Abstract + Contributions Alignment
Acceptance criteria:
1. Abstract includes N-best ambiguity handling and URS behavioral divergence.
2. Contributions explicitly separate LLM semantic extraction from deterministic telemetry validation.
3. Terms use CCR/BRR/AGI/URS/EES consistently.
4. Abstract explicitly states what is simulated: reconstructed UAS mission/fault scenarios in PX4 SITL (flight dynamics, controller behavior, sensor/telemetry response).
5. Abstract explicitly states design scope: aircraft system design constraints and operator mitigation recommendations.

### WP2: Methods Strengthening
Acceptance criteria:
1. Method text defines N-best generation (sampling, dedup signature, retry strategy).
2. Method text defines URS three-mode evaluation and formulas.
3. Method text defines fairness guardrail (better_specificity not penalized).
4. Method text explicitly defines how design constraints and recommendations are evaluated for quality (subsystem specificity, measurable parameterization, causal grounding, testability).

### WP3: Results Integration
Acceptance criteria:
1. Multi-case table includes 4-case CCR/BRR/AGI/EES values.
2. Case 103 bugfix before/after (0.485 -> 0.955 CCR) appears explicitly.
3. 85% non-contradiction rate and 7 better_specificity instances are reported.
4. Include one analyst-workflow impact table: manual pain point -> framework support -> evidence artifact.
5. Include stratified reporting split: observational/ambiguous vs confirmed-failure cases.
6. Include a Section 2 quality evidence block with:
	- at least one high-quality constraint/recommendation example
	- at least one penalized/generic recommendation example
	- explicit evidence traceability statements for both

### WP4: Discussion and Limitations
Acceptance criteria:
1. Discussion addresses reviewer concern: many trajectories for one narrative.
2. Limitations include deferred end-to-end real N-best test and dependency note.
3. Future work includes URS calibration and geodetic-accurate distance handling.
4. Discussion positions this work beyond descriptive FAA trend analysis by adding executable scenario reconstruction and simulation-backed recommendations.

### WP5: Rebuttal Support Pack
Acceptance criteria:
1. One reviewer-concern matrix maps concern -> change -> evidence file.
2. One claim-evidence table maps manuscript claims to artifact locations.
3. All links point to existing repository files.
4. Include one explicit prior-work delta statement: descriptive analysis versus simulation-validated safety intelligence.

## Prior-Work Positioning (AIAA FAA Sighting Analysis)

Positioning to include in manuscript/rebuttal:
- Prior FAA sighting studies establish important descriptive risk patterns (altitude, proximity, encounter statistics).
- AeroGuardian extends this by transforming narrative observations into executable PX4 scenarios, validating dynamic feasibility, and producing standardized pre-flight safety outputs.

Required comparison dimensions:
1. Descriptive trend analysis -> executable reconstruction pipeline.
2. Observation-only interpretation -> telemetry-grounded verification.
3. Risk description -> actionable design constraints and mitigation recommendations.
4. Single-interpretation fragility -> N-best uncertainty robustness analysis.

Claim discipline:
- Avoid overclaiming superiority; claim complementary advancement with explicit evidence boundaries.

## Deliverables
1. Reviewer response matrix file.
2. Manuscript claim-to-evidence traceability file.
3. Updated implementation step plan with Phase 7 completion gate.

## Closeout Checklist (Must All Pass)
1. WP1-WP5 acceptance criteria each marked satisfied with artifact references.
2. All manuscript-facing metric names are canonical (CCR, BRR, AGI, URS, EES).
3. Limitations are explicit and consistent across plan/rebuttal/traceability docs.
4. No unresolved docs-level terminology drift remains in active plan files.
5. DASC reviewer closure check:
	- R1 ambiguity/accuracy concern explicitly answered with URS/N-best evidence
	- R3 clarity comments explicitly answered with precise simulation/scenario/design wording
6. Prior-work positioning check:
	- manuscript clearly explains what prior descriptive FAA analyses established
	- manuscript clearly explains what AeroGuardian newly adds (simulation validation + actionable intelligence)
7. Documentation/code-separation check:
	- reviewer commentary remains in docs/rebuttal materials only, not embedded in source code comments
8. Accuracy-and-trust proof check:
	- four-layer accuracy argument is explicit (CCR, BRR, AGI, URS)
	- hallucination controls include at least one penalized and one well-grounded recommendation example
	- claims are explicitly bounded to decision-support scope (not accident-truth reconstruction)
9. Design constraint and recommendation closure check:
	- manuscript clearly answers "design of what" with subsystem/envelope constraints
	- manuscript clearly answers "recommend what" with actor-targeted mitigations
	- recommendation quality is defended with evidence linkage, not only verdict labels

## Submission Readiness Decision Rule

- GO when checklist items 1-9 all pass.
- HOLD if any design-constraint/recommendation closure item is implied but not explicitly stated with evidence support.

Current decision status:
- HOLD (pending final Section 2 flagship evidence block and full checklist closure).

## Completion Gate
Phase 7 is complete when all five work packages pass acceptance checks and all manuscript metrics terminology is canonical.
