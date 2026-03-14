# AeroGuardian: World-Class RFlyMAD Validation Strategy for DASC 2026

## 1. Scope and Intent

This strategy strengthens RFlyMAD validation only.

Scope constraints:
- Keep the current pipeline runnable.
- Apply upgrades phase by phase.
- Avoid disruptive replacements unless explicitly approved in the checklist.
- Keep benchmark scoring deterministic and non-ML.

## 2. Feedback Review Summary (What Needed Correction)

The previous draft had useful ideas but also critical weaknesses that could reduce reviewer confidence.

Corrected issues:
1. Outdated source references and environment paths:
- Removed stale Linux-style references and aligned to current workspace structure and governed paths.

2. Methodology drift from non-ML core:
- Removed recommendations that could be interpreted as black-box learning in the scoring path.
- Kept the plan strictly deterministic, physics-informed, and auditable.

3. Insufficient phase control:
- Added explicit phase gates and stop/go criteria to prevent uncontrolled changes to the entire evaluation stack.

4. Weak claim governance:
- Added metric contracts, confidence reporting requirements, and claim-bounding rules.

## 3. Current Baseline and Core Risk

Latest strict RFlyMAD-only baseline:
- Precision: 0.739
- Recall: 0.675
- F1: 0.706

Observed risk:
- Wind class performance is strong.
- Motor and sensor recall are weak relative to publication-grade expectations.

Interpretation:
- Aggregate metrics alone are not sufficient.
- Per-class and uncertainty-aware evidence must drive acceptance.

## 4. Validation Principles (Non-Negotiable)

1. Deterministic scoring only.
2. Physics-informed rule sets per class.
3. Traceability from every reported metric to source telemetry and thresholds.
4. Reproducible runs with manifest, version, and fixed configuration.
5. Conservative claims with explicit limitations when thresholds are not met.

## 5. Strong Plan-Aligned Upgrade Roadmap

### Phase V1: Transparency Upgrade (Additive)

Objective:
- Improve evidence quality without changing detector logic.

Required outputs:
- Overall and per-class metrics CSV.
- Confusion matrix CSV and image.
- Per-class support counts.
- Onset delay summary (mean, median, P90, P95).

Exit gate:
- All required artifacts generated for each RFlyMAD-only run.

### Phase V2: Class-Aware Deterministic Rules

Objective:
- Raise motor and sensor recall while containing precision loss.

Required upgrades:
1. Class-conditional threshold profiles:
- motor_fault profile,
- sensor_fault profile,
- wind_fault profile.

2. Temporal logic hardening:
- persistence windows,
- hysteresis,
- phase-aware guards (warm-up, takeoff/landing handling).

3. Abstain fallback:
- support unknown classification when evidence is conflicting.

Exit gate:
- Motor recall and sensor recall each improve by at least +0.20 absolute vs baseline.
- Precision drop per class does not exceed 0.10 absolute.

### Phase V3: Statistical Credibility Package

Objective:
- Prove improvements are statistically meaningful.

Required outputs:
1. Bootstrap 95% CI for precision, recall, and F1 (overall + per class).
2. Paired significance comparison against baseline (flight-level McNemar).
3. Effect-size report for key deltas.

Exit gate:
- CI and significance artifacts attached to benchmark output package.

### Phase V4: Robustness Validation

Objective:
- Demonstrate resilience under realistic telemetry imperfections.

Stress suites:
1. Missing-channel stress.
2. Noise perturbation stress.
3. Timestamp jitter stress.

Exit gate:
- No catastrophic class collapse.
- Delta metrics documented for each stress condition.

## 6. Metric Contract for Reviewer-Facing Reporting

Always report, for each class and overall:
- accuracy,
- precision,
- recall,
- F1,
- support,
- tp, tn, fp, fn,
- onset delay mean, median, P90, P95.

Always include:
- macro-F1,
- micro-F1,
- weighted-F1,
- sample-level confusion matrix,
- flight-level confusion matrix.

## 7. Acceptance Criteria for Paper Claims

Minimum claimable targets:
1. Macro-F1 >= 0.65.
2. Overall F1 >= 0.75.
3. Motor recall >= 0.45.
4. Sensor recall >= 0.45.
5. P95 onset delay <= 5.0 s.

If any target is not met:
- bound claims explicitly,
- include class-specific failure analysis,
- include mitigation roadmap in the limitations section.

## 8. Required Artifact Package Per RFlyMAD Run

1. Run manifest (command, code version, dataset path, timestamp).
2. Detailed metrics CSV (overall + per class).
3. Confusion matrix CSV.
4. Confusion matrix image.
5. Per-flight prediction trace CSV.
6. Onset delay distribution CSV.
7. CI/significance JSON (from Phase V3 onward).
8. Method card documenting thresholds, logic, and known limits.

## 9. Reviewer Defense Notes (Prepared Responses)

Q: Why not use a black-box ML model?
- Safety evidence must be auditable. Deterministic logic provides traceable causal evidence and supports operational trust.

Q: How do you prove the method is rigorous?
- Per-class metrics, confidence intervals, and paired significance tests are mandatory, not optional.

Q: How do you avoid class-imbalance inflation?
- Macro-F1 and class-level confusion reporting are required for all headline claims.

Q: Is performance good enough for strong claims?
- Claims are gated by explicit acceptance targets and confidence bounds.

## 10. Integration with the Full AeroGuardian Plan

This validation strategy is the telemetry evidence backbone for downstream stages:
1. Validate deterministic telemetry logic on RFlyMAD.
2. Lock approved detector profile and thresholds.
3. Use only validated telemetry summaries as evidence inputs for report generation.
4. Keep final report statements linked to deterministic evidence artifacts.

This preserves AeroGuardian's key advantage for DASC 2026: strong safety intelligence without black-box dependency.
