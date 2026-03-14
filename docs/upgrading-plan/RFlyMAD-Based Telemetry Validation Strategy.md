# RFlyMAD-Based Telemetry Validation Strategy (Strong Plan-Aligned Upgrade)

## 1. Scope Lock (Important)

This document upgrades validation methodology only.
It does not require immediate disruptive changes to the whole evaluation pipeline.

Execution rule:
- Phase by phase.
- Every phase must preserve current runnable flow unless explicitly approved for replacement.

## 2. Objective

Strengthen RFlyMAD validation so reviewer questions are answered with deterministic, traceable evidence.

Core position:
- No black-box ML for benchmark scoring.
- Physics-informed and rule-based validation with reproducible artifacts.

## 3. Current Baseline and Pain Points

Current strict RFlyMAD-only baseline:
- Precision: 0.739
- Recall: 0.675
- F1: 0.706

Weak point:
- Wind class dominates metrics.
- Motor and sensor recall are too low for strong reviewer confidence.

Main causes:
1. One-size-fits-all thresholds.
2. Weak class-specific evidence rules for motor and sensor faults.
3. Aggregate metrics hide class imbalance risk.

## 4. Non-ML Validation Principles (Mandatory)

1. Deterministic rules only in scoring.
2. Physics-grounded signatures for each fault class.
3. Full traceability from metric to source rows and thresholds.
4. Reproducible runs with fixed manifest and versioned settings.
5. Conservative claims with explicit uncertainty bounds.

## 5. Strongest Practical Upgrade Path (Non-Disruptive)

### Phase V1 (Additive, no pipeline break)

Goal:
- Improve metrics transparency immediately without changing core detector behavior.

Actions:
1. Keep current detector.
2. Expand reporting to include macro/micro/weighted F1 and per-class support.
3. Export per-class confusion components (tp, tn, fp, fn) and onset delay quantiles.

Outputs:
- detailed metrics CSV,
- confusion matrix CSV/image,
- onset-delay distribution CSV.

Exit gate:
- Full per-class + overall metric package exists for every run.

### Phase V2 (Class-aware detection upgrade)

Goal:
- Raise motor and sensor recall while controlling false positives.

Actions:
1. Add class-conditional threshold profiles:
	- motor profile,
	- sensor profile,
	- wind profile.
2. Add temporal persistence and hysteresis.
3. Add unknown class fallback when evidence is conflicting.

Exit gate:
- motor recall and sensor recall each improve by >= 0.20 absolute from baseline.
- precision drop per class is <= 0.10 absolute.

### Phase V3 (Reviewer-grade statistical validation)

Goal:
- Prove improvements are statistically credible.

Actions:
1. Bootstrap 95% CI for precision/recall/F1 per class and overall.
2. Paired significance test (McNemar at flight level) baseline vs upgraded rules.
3. Report effect sizes and confidence bounds.

Exit gate:
- CI and significance outputs included in artifact bundle for each benchmark run.

### Phase V4 (Robustness and stress validation)

Goal:
- Demonstrate reliability under realistic data imperfections.

Actions:
1. Missing-channel stress test.
2. Noise perturbation test.
3. Timestamp jitter test.

Exit gate:
- No catastrophic collapse in class metrics.
- robustness report with delta metrics per stress condition.

## 6. Metric Contract (Must Always Be Reported)

For each class and overall:
- accuracy,
- precision,
- recall,
- F1,
- support,
- tp, tn, fp, fn,
- mean/median/P90/P95 onset delay.

Required averages:
- macro F1,
- micro F1,
- weighted F1.

Required confusion outputs:
- sample-level confusion matrix,
- flight-level confusion matrix.

## 7. Reproducibility Contract

Every validation run must save:
1. run manifest (command, code version, dataset path, timestamp),
2. metrics CSV (overall + per class),
3. confusion matrix CSV + image,
4. per-flight prediction trace CSV,
5. CI/significance JSON (from Phase V3 onward).

## 8. Acceptance Targets for Paper Claims

Minimum claimable target:
1. Macro-F1 >= 0.65.
2. Overall F1 >= 0.75.
3. Motor recall >= 0.45.
4. Sensor recall >= 0.45.
5. P95 onset delay <= 5.0s.

If these are not met:
- claims must be bounded,
- limitations must be explicit,
- per-class failure analysis must be included.

## 9. Reviewer Defense Pack (Ready Answers)

Q: Why no ML black-box?
- A: Deterministic safety validation is auditable. Every decision maps to interpretable physics-based rules.

Q: How do you prove it is rigorous?
- A: Per-class metrics, confidence intervals, significance tests, and reproducible run artifacts.

Q: How do you avoid inflated aggregate metrics from class imbalance?
- A: Macro-F1 and class-level confusion are mandatory, not optional.

Q: Is the method good enough for claims?
- A: Claims are gated by explicit acceptance targets and confidence bounds.

## 10. Integration with Entire AeroGuardian Plan

This validation strategy is the evidence backbone for later phases:
1. Validate telemetry detector on RFlyMAD.
2. Lock validated detector profile.
3. Use validated outputs as LLM #2 evidence input.
4. Keep report statements traceable to deterministic telemetry evidence.

This keeps AeroGuardian's strongest differentiator intact: explainable safety intelligence without black-box dependency.
