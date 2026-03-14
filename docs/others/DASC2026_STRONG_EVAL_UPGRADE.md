# AeroGuardian DASC 2026 Strong Evaluation Upgrade

Date: 2026-03-12

Status note (2026-03-13): Phase 6 validation and URS enhancement are complete; terminology below is aligned to current implementation (CCR, BRR, AGI, URS, EES).

## 1) End-to-End Purpose and Pipeline (Confirmed)

Primary mission:
- Convert difficult FAA UAS sighting narratives into robust, evidence-backed analysis that is faster and clearer than manual-only processing.

Primary beneficiary:
- FAA sighting report analysts and safety investigators.

Secondary beneficiary (after analyst review/approval):
- UAV operators who receive targeted mitigation guidance on what to check, what to redesign, and what operational constraints to apply to prevent recurrence.

Operational value proposition:
- Reduce analyst burden on unstructured reports.
- Improve consistency and traceability of safety interpretation.
- Produce actionable advisories that can support post-analysis communication to operators.

Primary defended output focus:
- The strongest defended output is not decision label alone.
- The strongest defended output is high-quality Section 2 content:
  1. aircraft system design constraints
  2. mitigation recommendations with actor and measurable condition
  3. evidence linkage to anomalies/telemetry

AeroGuardian is a two-LLM plus physics validation pipeline:

1. LLM1 translates FAA narrative text into executable PX4 scenario configuration.
2. PX4 SITL executes that scenario and produces telemetry.
3. Deterministic evaluator (no LLM) checks telemetry behavior against explicit thresholds.
4. LLM2 writes a pre-flight safety report with three required sections:
   - Safety level and cause
   - Design constraints and recommendations
   - Evidence-based explanation
5. Evaluator scores consistency across stages.

Current implementation is aligned to CCR, BRR, AGI, URS, and EES (with ESRI retained only for legacy comparison). The remaining publication risk is not core architecture but closure quality: reviewer-facing clarity and explicit uncertainty reporting.

Important context rule for LLM2:
- LLM2 input must always include BOTH the raw FAA narrative and the validated telemetry summary (including anomaly evidence). The narrative provides operational context; telemetry provides evidence constraints.

## 2) Why Fixed Thresholds Like 5 m Are Not Enough

Fixed values (for example altitude deviation > 5 m) are useful as conservative defaults but weak for publication-grade claims across heterogeneous scenarios.

Main weakness:
- A single fixed threshold does not adapt to platform class, environment, mission phase, or baseline noise.

Upgrade policy:
- Keep fixed thresholds as fallback safety guardrails.
- Primary decision threshold should be data-driven from baseline flights:
  - threshold(channel, class, phase) = mu + k * sigma
- Use class-specific k values and report them explicitly.

Example:
- Propulsion detection can use vel_z and gyro channels with k = 3.0 from normal-flight baseline.
- Navigation drift under high wind may need k = 3.5 for lower false positives.

This answers the question "why not threshold?" with: yes, thresholding is correct, but it must be adaptive and traceable, not a single global constant.

## 3) Strong Upgrade for LLM1 Evaluation (Narrative -> Config)

Replace keyword-heavy SFS emphasis with a primary metric:

Constraint Correctness Rate (CCR)

Definition:
- Extract a canonical constraint set from each narrative:
  - altitude, airspace relation, location, weather, timing, fault/event cues, vehicle type, mission intent
- Compare with generated config values.

Per-constraint score:
- exact match, numeric tolerance match, semantic equivalent match, missing, contradiction

Final metrics:
- CCR_exact
- CCR_tolerant
- Contradiction rate
- Missing-critical-field rate

Ambiguity handling (critical for reviewer 1):
- For each narrative, enumerate top-N feasible configs (N-best set) rather than one forced config.
- Execute all N and compute:
  - Feasibility Coverage: fraction executable
  - Behavioral Spread: trajectory divergence across N
  - Robustness-to-Ambiguity: whether safety conclusion is stable across N

This converts the "many possible trajectories" criticism into a measurable uncertainty analysis.

### Fairness Guardrail: LLM Better Than Hardcode

Your concern is correct: a deterministic parser must NOT be treated as absolute ground truth.

Use a reference-based adjudication policy:

- Deterministic extractor is a baseline reference, not oracle truth.
- For each field, assign one of: exact_match, equivalent_match, better_specificity, contradiction, missing.
- If LLM output is more specific and still physically/regulatorily valid, score it as better_specificity (not an error).
- Only penalize hard contradictions, physically impossible values, or unverifiable invented details.

Practical scoring example:
- Hardcode extracts generic "multirotor", LLM outputs "iris + motor_failure + onset=45s" with supporting evidence and executable behavior.
- This should increase score under better_specificity, not reduce it.

## 4) Strong Upgrade for LLM2 Evaluation (Telemetry -> Safety Report)

Current ECC is helpful but still allows generic recommendations to score too high.

Introduce Actionability and Grounding Index (AGI):

AGI requires all of the following per recommendation/constraint claim:
1. Subsystem specificity: recommendation names affected subsystem.
2. Parameter specificity: includes measurable parameter(s) and threshold(s).
3. Causal grounding: references anomaly supported by telemetry.
4. Verifiability: recommendation can be tested in simulation or checklist.

Suggested component scores:
- G1 Subsystem grounding
- G2 Numeric actionability
- G3 Telemetry causal link
- G4 Testability

AGI = weighted sum of G1..G4 with hard zero if contradiction exists.

Also score report structure completeness:
- Section completeness score for all three required report sections.
- Penalize vague language without target system, parameter, or criterion.

### Why LLM + Deterministic Validation (Not Hardcode Only)

This is a critical architecture question and the answer should be explicit in the paper:

- Hardcode-only is strong for checking known numeric rules but weak for parsing ambiguous natural language FAA narratives.
- LLM-only is strong for semantic interpretation but weak on deterministic trust.
- The strongest design is hybrid:
  - LLM handles semantic extraction and structured generation from unstructured text.
  - Deterministic validators independently verify consistency, physical plausibility, and evidence grounding.

So this is not redundant. It is defense-in-depth with clear division of responsibility.

### Strong Report Evaluation Rubric (for real operational usefulness)

To ensure reports are useful for FAA analysts and UAV operators, evaluate report quality with four explicit sub-scores:

- SCC (Section Completeness and Clarity)
  - Verifies all required sections exist and are clear: safety level/cause, design constraints/recommendations, evidence explanation.

- OAS (Operator Actionability Score)
  - Rewards specific operator actions with measurable conditions (what to check, when to stop flight, what threshold triggers action).
  - Penalizes generic recommendations that cannot be operationalized.

- DTS (Design Traceability Score)
  - Requires each design recommendation to name subsystem, parameter, and intended mitigation mechanism.
  - Example: not just "improve reliability"; must state what system and which measurable change.

- ETS (Evidence Traceability Score)
  - Requires every key claim/recommendation to map to telemetry anomalies and timeline.
  - Contradictions or unsupported claims receive hard penalties.

Composite report quality:

RQS = SCC * OAS * DTS * ETS

This can be combined with AGI, or AGI can be redefined as the strict grounding core and RQS used as a broader usability score.

### Design Constraint / Recommendation Quality Gate (Reviewer-Critical)

For acceptance-strength reporting, each key recommendation should answer:
1. Design of what subsystem/envelope?
2. Recommendation for whom (operator, engineering, regulator, analyst)?
3. Under what measurable trigger/threshold?
4. Supported by which telemetry anomaly/evidence?

If a recommendation fails one or more items, it must be marked weaker and not used as flagship evidence.

## 5) Upgraded Composite Index (Meaningful Abbreviations)

Current ESRI is useful for consistency but should be expanded with full-meaning abbreviations:

- CCR = Constraint Correctness Rate (LLM1, from CCR_tolerant)
- BRR = Behavior Reproduction Rate (deterministic telemetry checks)
- AGI = Actionability and Grounding Index (LLM2 recommendation grounding)
- URS = Uncertainty Robustness Score (N-best narrative ambiguity stability)
- EES = End-to-End Evaluation Score

Formula:

EES = CCR * BRR * AGI * URS

Where:
- CCR maps to LLM1 extraction correctness
- BRR maps to deterministic behavior score
- AGI maps to recommendation grounding/actionability score
- URS maps to ambiguity robustness across feasible trajectories

Keep existing confidence ceilings and explicitly state that index is an internal consistency metric, not certification evidence.

### ESRI Policy During Submission Transition

- ESRI is retained only as a legacy comparison baseline.
- ESRI must NOT be presented as the primary defended metric in the revised paper narrative.
- Primary defended framework for updated research questions should be based on:
  - CCR (narrative-to-config correctness)
  - BRR (behavior reproduction validity)
  - AGI/RQS (report grounding and actionability)
  - URS (ambiguity robustness)

Recommended statement for manuscript and rebuttal:
- "We retain ESRI only for historical comparability with prior internal experiments; primary claims are based on the upgraded metric framework designed to address ambiguity and actionability concerns raised by reviewers."

### Reviewer-Driven Positioning for Updated Research Questions

- Reviewer concern on trajectory degrees of freedom:
  - answer with URS and N-best scenario stability analysis.
- Reviewer concern on unclear simulation/scenario meaning:
  - explicitly state we simulate UAS flight dynamics, controller response, and telemetry under reconstructed mission/fault hypotheses in PX4 SITL.
- Reviewer concern on "design of what":
  - explicitly define "aircraft system design constraints" and "operator mitigation recommendations" in the report structure.

## Reviewer Closure Status (R1-R3)

### Review 1: Trajectory degrees-of-freedom and unclear accuracy
- Concern:
  - many trajectories can fit one report; accuracy measurement unclear.
- Implemented response:
  - N-best generation and URS ambiguity evaluation modes (config-only, telemetry, full).
  - CCR adjudication with fairness guardrail and multi-case evidence table.
- Residual gap to close in narrative:
  - explicitly state uncertainty treatment in abstract/results and cite URS evidence artifacts.
- Status:
  - Substantially addressed; final manuscript wording alignment pending.

### Review 2: Useful formalization tool
- Concern:
  - no major technical blockers raised.
- Implemented response:
  - reinforced traceability, deterministic validation, and evidence-backed recommendations.
- Residual gap to close in narrative:
  - keep concise value proposition and avoid over-claiming external generalization.
- Status:
  - Addressed.

### Review 3: "What is being simulated?" "Scenarios of what?" "Design of what?"
- Concern:
  - missing contextual specificity in abstract wording.
- Implemented response:
  - standardized wording around "reconstructed UAS mission/fault scenarios in PX4 SITL" and "aircraft system design constraints".
- Residual gap to close in narrative:
  - ensure those exact terms appear in abstract and first-paragraph method summary.
- Status:
  - Technically addressed; manuscript phrasing lock pending.

## Robustness Verdict (Current)

- Technical framework robustness: STRONG
  - Evidence: CCR/AGI/URS implementation, bugfix deltas, multi-case validation artifacts.
- Defensibility for publication: STRONG WITH MINOR WORDING RISK
  - Remaining risk is reviewer-facing phrasing clarity, not missing evaluation capability.
- Immediate path to full closure:
  1. Lock abstract/method wording with explicit simulation subject and ambiguity treatment.
  2. Ensure every key claim cites one artifact in rebuttal and manuscript traceability sections.
  3. Keep limitations explicit (dependency issue, deferred full real N-best batch, GPS approximation caveat).

## 6) Reviewer-Concern-to-Action Mapping

Reviewer concern: many trajectories possible for same report, unclear accuracy
Action:
- Add N-best narrative-to-config generation and uncertainty analysis (coverage, spread, conclusion stability).
- Report CCR and ambiguity robustness, not only single-run success rate.

Reviewer concern: design of what? recommend of what?
Action:
- Rename wording to "aircraft system design constraints" and "mitigation design recommendations".
- AGI requires subsystem + parameter + measurable threshold + evidence link.

Reviewer concern: simulation/scenarios not specific enough
Action:
- Always state "PX4 SITL simulates UAS flight dynamics, controller behavior, sensor streams, and fault responses under reconstructed mission and environment conditions."

## 7) Minimal Abstract Wording Upgrade

Use clearer nouns in abstract:
- "design constraints" -> "aircraft system design constraints"
- "design recommendations" -> "mitigation design recommendations for avionics, control, and operations"
- "simulation scenarios" -> "reconstructed UAS mission and fault scenarios in PX4 SITL"

Add one sentence for ambiguity:
- "Because narratives can map to multiple feasible trajectories, we evaluate an N-best scenario set and quantify conclusion stability across feasible reconstructions."

## 8) Implementation Priorities (Code)

Priority 1 (immediate):
- Add CCR evaluator module with canonical constraint extraction and mismatch accounting.
- Add AGI evaluator module with strict telemetry-grounded checks.

Priority 2:
- Add N-best config generation and uncertainty metrics.
- Integrate URS factor into composite score EES.

Priority 3:
- Produce per-case audit file:
  - extracted constraints
  - config mismatches
  - telemetry-linked recommendation evidence
  - uncertainty spread summary

## 9) Publishability Checklist

To claim strong scientific evidence, ensure all are present:
- Explicit definition of what is being simulated.
- Explicit uncertainty treatment for narrative ambiguity.
- Deterministic threshold rationale (mu, sigma, k) with dataset source.
- LLM1 scored on constraint correctness, not only executability.
- LLM2 scored on actionable, telemetry-grounded recommendation quality.
- Full traceability from narrative -> config -> telemetry -> claim.

If all checklist items are satisfied, reviewer concerns become strengths instead of weaknesses.

## 10) Robustness and Defensibility Standard (Publication Gate)

Use this as the mandatory pass/fail standard before submission.

### A. Metric Governance Gate
- Canonical names only in manuscript-facing materials: CCR, BRR, AGI, URS, EES.
- ESRI may appear only as legacy comparison baseline language.
- Any legacy aliases (SFS, ECC, CSR, BRS) must be explicitly marked as historical terms.

### B. Traceability Gate
- Every quantitative claim in Results must map to at least one artifact file.
- Every method claim must map to one code location and one policy document.
- Every rebuttal claim must include concern -> change -> evidence mapping.

### C. Ambiguity Robustness Gate
- URS must be reported with mode context:
  - config-only
  - telemetry
  - full evaluation
- If N-best alternatives are unavailable, the fallback reason must be reported explicitly.
- At least one ambiguity-focused case must be discussed with trajectory divergence evidence.

### D. Recommendation Grounding Gate
- AGI discussion must show subsystem specificity, numeric actionability, causal telemetry link, and testability.
- Generic recommendations without measurable criteria must be scored down and documented.
- At least one positive and one penalized recommendation example should be included in appendix/rebuttal evidence.

### E. Reproducibility Gate
- Validation commands and artifact paths must be listed in a single reviewer-facing section.
- Report all known limitations that affect reproducibility (dependency conflicts, deferred tests, approximations).
- Keep environment statement consistent (Windows + venv workflow).

### F. Statistical Integrity Gate
- Provide both per-case and aggregate metrics.
- Explicitly separate observed evidence from inferred interpretation.
- Preserve before/after bugfix deltas for at least one representative case (Case 103).

Passing all gates indicates the framework is defensible for publication and rebuttal.
