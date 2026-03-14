# AeroGuardian Detailed Step-by-Step Implementation Protocol

Date: 2026-03-14
Owner: AeroGuardian Team
Purpose: Highest-quality, low-rework implementation protocol aligned with upgrading-plan strategy

## 1. Scientific Operating Principles

1. Trust before convenience: every generated claim must be traceable to source evidence, deterministic checks, or validated telemetry.
2. Raw-only LLM #1 policy: no derived hint labels in scenario prompt construction.
3. Deterministic guardrails first, LLM inference second.
4. Reproducibility at each phase gate: fixed inputs, fixed command manifests, fixed output schema.
5. Fail fast, repair locally: if a phase gate fails, do not proceed to next phase.

## 2. Non-Negotiable Data Paths

1. FAA raw source: C:/VIRAK/Python Code/aero-guardian/data/raw/faa
2. RFlyMAD raw source: C:/VIRAK/Python Code/aero-guardian-full-version-including-dl&ml/data/raw/rflymad
3. New dataset output only: C:/VIRAK/Python Code/aero-guardian/data/new_data

## 3. Master Phase Roadmap

1. Phase 0: Baseline governance and reproducibility envelope
2. Phase 1: FAA raw ingestion and schema integrity
3. Phase 2: Physics-informed extraction and FAA regulatory flagging
4. Phase 3: Raw-only LLM #1 contract hardening
5. Phase 4: Scenario-to-simulation consistency and fault-injection semantics
6. Phase 5: RFlyMAD-grounded telemetry validation
7. Phase 6: LLM #2 report evidence quality and regulatory traceability
8. Phase 7: Evaluation framework hardening and publication-ready evidence package

## 4. Detailed Execution Plan

### Phase 0. Baseline Governance and Reproducibility Envelope

Goals:
1. Freeze the execution environment and establish one canonical run manifest format.
2. Ensure all outputs are attributable to exact code+command states.

Actions:
1. Define a run manifest template with fields:
- run_id
- timestamp
- code_revision
- dataset_paths
- runner_command
- case_selection_source
- metric_schema_version
2. Establish canonical raw-only runner for longitudinal comparability:
- scripts/run_raw_only_evaluation.py
3. Add pre-run and post-run checksum logging for input case files.

Gate criteria:
1. Two consecutive dry runs with same manifest produce same selected case IDs.
2. Artifact package includes manifest and metrics summary.

Risk controls:
1. No ad-hoc manual edits to generated artifacts.
2. If manifest missing, run is invalid.

---

### Phase 1. FAA Raw Ingestion and Schema Integrity

Goals:
1. Preserve source fidelity from FAA Excel to structured records.
2. Remove phantom-column and malformed-schema failure modes.

Target code areas:
1. scripts/process_faa_data.py
2. src/faa/sighting_filter.py

Actions:
1. Build deterministic column-selection map for required FAA fields with robust fallback names.
2. Preserve provenance keys in each record:
- source_file
- source_row_index
- source_quarter
- report_id
3. Add schema scanner:
- detects empty-wide columns
- logs unknown columns
- records per-file parsing warnings
4. Write upgraded FAA dataset snapshots to:
- data/new_data/faa/

Gate criteria:
1. 100 percent of processed rows retain source provenance keys.
2. No row silently dropped without explicit reason log.
3. Sampling audit confirms round-trip mapping from output row to original Excel row.

Risk controls:
1. On schema drift, run enters HOLD with diagnostic report instead of partial silent success.

---

### Phase 2. Physics-Informed Extraction and FAA Regulatory Flagging

Goals:
1. Convert narrative ambiguity into deterministic engineering context.
2. Explicitly encode applicable FAA rule checks.

Target logic:
1. Altitude extraction and unit normalization
2. UAS descriptor extraction (type, shape, size if present)
3. Proximity and evasive-action extraction
4. Regulatory flags

Actions:
1. Altitude parser:
- parse feet and AGL mentions
- emit altitude_m and extraction_confidence
2. Regulatory checks:
- Part 107.51 altitude limit flag
- close-approach hazard flag for manned-aircraft proximity contexts
- VLOS indicator flags from narrative cues
3. Confidence strategy:
- separate extraction confidence from fault interpretation confidence
4. Persist outputs in dataset records under deterministic fields:
- physics_flags
- regulatory_flags

Gate criteria:
1. Altitude extraction precision/recall benchmark on annotated sample meets target.
2. Regulatory flags are deterministic and reproducible on rerun.
3. No derived fault label is required to compute physics/regulatory outputs.

Risk controls:
1. Ambiguous extractions are tagged as uncertain, never auto-promoted to failure facts.

---

### Phase 3. Raw-Only LLM #1 Contract Hardening

Goals:
1. Ensure LLM #1 uses only source narrative plus raw metadata context.
2. Eliminate all legacy hinted comparisons from active path.

Target code areas:
1. src/llm/client.py
2. src/llm/signatures.py
3. src/llm/scenario_generator.py

Actions:
1. Enforce prompt payload contract fields only:
- report_id
- date
- city
- state
- description
2. Add prompt-audit hook that writes effective prompt payload schema checks to log.
3. Keep strict output schema checks:
- enum validation
- waypoint JSON structure
- mission-bound plausibility
4. Reject non-conforming output with deterministic retry or failure mark.

Gate criteria:
1. Prompt audit confirms zero derived hint fields injected.
2. No invalid enum value in smoke set.
3. No malformed waypoint payload in smoke set.

Risk controls:
1. If any derived field appears in prompt body, immediate gate fail.

---

### Phase 4. Scenario-to-Simulation Consistency and Fault Semantics

Goals:
1. Ensure generated scenario semantics align with runtime fault injection capabilities.
2. Avoid text-command coupling errors.

Target code areas:
1. src/llm/scenario_generator.py
2. scripts/run_automated_pipeline.py
3. src/reporting/unified_reporter.py

Actions:
1. Use deterministic fault_injection_supported logic from fault type category.
2. Keep runtime marker semantics explicit:
- mavsdk_emulation
- behavioral_only
3. Remove or prohibit command-string as support decision source.
4. Add cross-check in report generation:
- unsupported fault type must be transparently labeled behavioral-only.

Gate criteria:
1. No runtime branch depends on generated command text.
2. Fault support flags are consistent from scenario generation to report output.

Risk controls:
1. If mismatch detected between fault type and support flag, run marked invalid.

---

### Phase 5. RFlyMAD-Grounded Telemetry Validation

Goals:
1. Validate telemetry analysis against real fault behavior prior to FAA generalized deployment.
2. Quantify detection quality and attribution reliability.

Target code areas:
1. src/evaluation/ground_truth_benchmark.py
2. src/evaluation/behavior_validation.py
3. src/analysis/telemetry_analyzer.py

Actions:
1. Create explicit mapping file for RFlyMAD fault taxonomy to internal fault taxonomy.
2. Run benchmark suite by mapped fault class.
3. Compute and store:
- BRR by class
- false positive behavior on nominal segments
- mean onset delay
- subsystem attribution accuracy
4. Save dataset-level transformed outputs only under:
- data/new_data/rflymad/

Gate criteria:
1. Mapping is complete for target RFlyMAD classes used in benchmark.
2. Benchmark report generated with per-class and aggregate sections.
3. Onset delay and attribution metrics included.

Risk controls:
1. If mapping ambiguity unresolved for a class, exclude class with explicit rationale, do not silently merge.

---

### Phase 6. LLM #2 Report Evidence Quality and Regulatory Traceability

Goals:
1. Ensure safety report claims are evidence-grounded, actionable, and regulation-aware.
2. Prevent generic recommendation drift.

Target code areas:
1. src/llm/signatures.py
2. src/llm/report_generator.py
3. src/reporting/unified_reporter.py

Actions:
1. Input contract to LLM #2 includes validated telemetry summary and violation context.
2. Output contract enforces:
- explicit safety level
- regulatory_violation_summary
- evidence-linked recommendation text
3. Add post-generation quality checks:
- no generic non-numeric recommendations
- contradiction check against telemetry summary

Gate criteria:
1. Recommendations contain measurable criteria where applicable.
2. Regulatory summary aligns with deterministic regulatory flags.
3. Unsupported causal claims count below threshold.

Risk controls:
1. If report fails evidence checks, tag as non-publishable artifact.

---

### Phase 7. Evaluation Hardening and Publication-Ready Package

Goals:
1. Produce a reproducible, reviewer-robust evidence package.
2. Keep naming and schema stable for iterative reruns.

Actions:
1. Canonical outputs include:
- run manifest
- per-case metrics
- aggregate metrics
- gate status
2. Track established metrics consistently:
- CCR
- BRR
- AGI
- URS
- EES
- contradiction_count
- better_specificity_count
3. Add confidence interval reporting where statistically valid.
4. Assemble final reviewer package under outputs/verification with a stable schema version.

Gate criteria:
1. End-to-end raw-only run completes with manifest and full metric payload.
2. All prior phase gates marked pass.
3. Reviewer package regenerated from scratch with fixed inputs.

Risk controls:
1. No publication claim from runs missing manifest, gate states, or schema version.

## 5. Cross-Phase Quality Assurance Matrix

1. Data lineage QA:
- source_file/source_row_index always present
- trace checks performed on sampled records
2. Prompt policy QA:
- raw-only payload audit attached to run artifact
3. Simulation QA:
- fault support semantics consistent end-to-end
4. Telemetry QA:
- benchmark evidence attached for mapped fault classes
5. Report QA:
- recommendation evidence traceability passes

## 6. Stop and HOLD Conditions

1. Any source-to-output traceability break.
2. Any derived hint leakage into LLM #1 prompt.
3. Any schema instability in canonical evaluation outputs.
4. Any unresolved taxonomy mismatch in RFlyMAD mapping for included classes.

## 7. Immediate Next Implementation Slice

1. Implement Phase 0 manifest template and integrate into raw-only runner.
2. Implement Phase 1 schema scanner and provenance-preserving exporter to data/new_data/faa.
3. Execute first audited FAA raw processing run and store gate report.
