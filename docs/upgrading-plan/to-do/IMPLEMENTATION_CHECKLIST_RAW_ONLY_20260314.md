# AeroGuardian Upgrade Implementation Checklist (Raw-Only)

Date: 2026-03-14
Scope Source: docs/upgrading-plan/* (read one-by-one)
Execution Policy: Raw-only LLM #1 input, physics/regulatory grounding, RFlyMAD-validated telemetry pipeline

## 0. Hard Constraints (Do Not Violate)

- [x] Use FAA raw source from: `C:/VIRAK/Python Code/aero-guardian/data/raw/faa`
- [x] Use RFlyMAD raw source from: `C:/VIRAK/Python Code/aero-guardian-full-version-including-dl&ml/data/raw/rflymad`
- [x] Write any newly produced dataset artifacts only to: `C:/VIRAK/Python Code/aero-guardian/data/new_data`
- [x] Keep LLM #1 in enforced raw-only mode (no heuristic hint injection)
- [ ] Keep report claims traceable to validated telemetry and explicit regulatory evidence

## 1. Baseline and Reproducibility Setup

- [x] Freeze a run manifest (timestamp, commit hash, runner command, case list)
- [ ] Define fixed case subsets for fast regression and full runs
- [x] Standardize output naming for verification artifacts (`raw_only_evaluation_*`)
- [ ] Record environment assumptions (PX4 version, vehicle model, headless/GUI mode)

Exit Criteria:
- [x] Manifest template exists and is used in all runs
- [ ] Repeated run with same manifest reproduces identical case selection

## 2. FAA Raw-to-Rich Extraction Layer (Physics + Regulation)

Target areas:
- `scripts/process_faa_data.py`
- `src/faa/*` loaders

- [ ] Preserve all key raw fields from FAA rows (`date`, `city`, `state`, narrative, altitude indicators, descriptors)
- [x] Implement deterministic altitude extraction and normalization (feet/meters)
- [x] Add altitude plausibility checks and rule flags (Part 107.51)
- [x] Add close-approach / near-miss extraction and hazard flags
- [x] Add VLOS and Remote ID contextual indicators when present in narrative
- [x] Persist structured regulatory flags in processed records
- [x] Export upgraded dataset snapshots to `data/new_data/faa/`

Exit Criteria:
- [x] Row-level traceability back to source file and row index
- [x] No silent field loss between raw record and processed representation
- [x] Regulatory flags are reproducible with deterministic rules

## 10. Progress Log (Execution Evidence)

### 2026-03-14 FAA Processor Rebuild from Zero

Completed:
1. Deleted legacy `scripts/process_faa_data.py` implementation.
2. Recreated `scripts/process_faa_data.py` from zero with new-plan architecture:
	- deterministic classifier
	- provenance-preserving record construction
	- schema diagnostics scanner
	- deterministic regulatory/physics flags
	- default output path `data/new_data/faa`
3. Regenerated FAA dataset from raw source (`data/raw/faa`) to new output path.

Fresh run evidence (rebuilt script):
1. `generated_at`: `2026-03-14T21:04:36.722567`
2. Raw records processed: 8918
3. Simulatable incidents: 8523
4. ACTUAL_FAILURE: 22
5. HIGH_RISK_SIGHTING: 8501

Field integrity checks (rebuilt outputs):
1. Provenance fields present: `source_file`, `source_row_index`, `source_quarter`
2. Regulatory flags present per record: `part_107_51_altitude_violation`, `part_107_31_vlos_indicator`, `part_89_remote_id_indicator`, `close_approach_flag`, `closest_proximity_ft`
3. Physics flags present per record: `high_altitude_proxy_required`, `observation_confidence_score`

### 2026-03-14 Phase 0 + Phase 1 Execution

Completed:
1. Added canonical run manifest support in `scripts/run_raw_only_evaluation.py`.
2. Added FAA schema diagnostics scan and output in `scripts/process_faa_data.py`.
3. Added `source_quarter` provenance field in FAA processed records.
4. Updated default FAA upgraded dataset output location to `data/new_data/faa`.

Evidence artifacts:
1. `data/new_data/faa/faa_reports.json`
2. `data/new_data/faa/faa_simulatable.json`
3. `data/new_data/faa/faa_schema_diagnostics.json`
4. `data/new_data/faa/faa_actual_failures.json`
5. `data/new_data/faa/faa_high_risk_sightings.json`

Observed run summary:
1. Raw records processed: 8918
2. Simulatable incidents: 8031
3. Actual failures: 31
4. High-risk sightings: 8000

### 2026-03-14 Phase 2 Execution (Physics + Regulatory Flags)

Completed:
1. Added deterministic regulatory flag extraction in `scripts/process_faa_data.py`:
	- `part_107_51_altitude_violation`
	- `part_107_31_vlos_indicator`
	- `part_89_remote_id_indicator`
	- `close_approach_flag`
	- `closest_proximity_ft`
2. Added deterministic physics plausibility/context flags:
	- `high_altitude_proxy_required`
	- `observation_confidence_score`
3. Regenerated FAA upgraded dataset from raw source into `data/new_data/faa`.

Evidence:
1. `data/new_data/faa/faa_simulatable.json` generated_at: `2026-03-14T20:57:54.458578`
2. Sample validation: first 200 incidents contain both `regulatory_flags` and `physics_flags` dictionaries.

### 2026-03-14 Feedback Integration Upgrade

Completed from reviewer feedback:
1. Added `part_107_51_high_certainty_violation` (threshold > 500 ft / 152.4 m) to regulatory flags.
2. Added deterministic UAS descriptor extraction to physics flags:
	- `uas_descriptors.sizes`
	- `uas_descriptors.shapes`
	- `uas_descriptors.colors`
3. Added `physical_description_summary` to support richer downstream reporting context.

Evidence:
1. `data/new_data/faa/faa_simulatable.json` includes all new fields.
2. Example values observed include both `part_107_51_high_certainty_violation: true` and populated `physical_description_summary` strings.

### 2026-03-14 Phase 3 Execution (LLM #1 Contract Hardening)

Completed:
1. Enforced raw-only LLM #1 payload construction in `src/llm/client.py` with required metadata fields:
	- `Report ID`
	- `Date`
	- `City`
	- `State`
	- `Description`
2. Removed derived hint injection path from `generate_full_px4_config` prompt assembly.
3. Added prompt-audit fail-fast gate in `src/llm/scenario_generator.py`:
	- required field presence checks
	- forbidden derived-token checks (`fault_type`, `classification`, `hazard_category`, `confidence`, etc.)
	- artifact writer for `phase3_prompt_audit_<report_id>.json` under run `evaluation/` output directory
4. Added strict post-parse validators in `src/llm/scenario_generator.py`:
	- enum validation for `uav_model`, `failure_category`, `failure_component`, `flight_phase`, `outcome`, `environment`
	- waypoint JSON schema validation (`lat`, `lon`, `alt`, `action`)
5. Added explicit MAVSDK-facing fault fields in `src/llm/client.py`:
	- `fault_severity`
	- `trigger` (`time_elapsed_sec` + onset value)

Evidence:
1. Validator smoke snippet executed successfully:
	- `audit_pass=True`
	- `missing_required_fields=[]`
	- `found_forbidden_tokens=[]`
	- waypoint schema check passed (3 valid waypoints)
2. Static diagnostics report no syntax/problems in:
	- `src/llm/client.py`
	- `src/llm/scenario_generator.py`

## 3. LLM #1 Signature and Input Hardening

Target areas:
- `src/llm/signatures.py`
- `src/llm/scenario_generator.py`
- `src/llm/client.py`

- [x] Ensure LLM #1 input contract uses only raw narrative + raw metadata (`report_id`, `date`, `city`, `state`)
- [x] Keep derived labels out of prompt body (`fault_type`, `classification`, `hazard_category`, confidence hints)
- [x] Enforce strict output enums and JSON-valid waypoint schema
- [x] Add fail-fast post-parse validators for scenario fields
- [x] Keep MAVSDK-compatible fault fields explicit (type/category/severity/trigger)

Exit Criteria:
- [x] Prompt audit confirms no derived hint fields in LLM #1 request payload
- [x] Zero invalid enum emissions over smoke set
- [x] Zero malformed waypoint payloads over smoke set

## 4. RFlyMAD Telemetry Validation Strategy

Target areas:
- `src/evaluation/ground_truth_benchmark.py`
- `src/evaluation/behavior_validation.py`
- `src/analysis/telemetry_analyzer.py`

- [x] Build explicit mapping table: RFlyMAD fault taxonomy -> AeroGuardian fault taxonomy
- [ ] Validate signature uniqueness across mapped fault classes
- [ ] Compute BRR, false-positive behavior, and onset-delay metrics
- [ ] Verify subsystem attribution against RFlyMAD ground truth
- [x] Export telemetry-validation datasets/results to `data/new_data/rflymad/` (dataset-level outputs only)

Exit Criteria:
- [x] Mapping table is versioned and used by benchmark scripts
- [ ] BRR and onset delay are reported per fault class and aggregate
- [ ] Validation report is reproducible from raw RFlyMAD inputs

## 5. LLM #2 Safety Report Quality and Regulatory Traceability

Target areas:
- `src/llm/signatures.py`
- `src/llm/report_generator.py`
- `src/reporting/*`

- [ ] Ensure LLM #2 input contains validated telemetry summary, not raw telemetry stream
- [ ] Include explicit regulatory violation summary fields in report generation
- [ ] Ensure each recommendation is numerically grounded in telemetry evidence
- [ ] Ensure hazard level/verdict are justified by evidence and constraints
- [ ] Add transparency statement for simulation/proxy limitations

Exit Criteria:
- [ ] Reports include evidence-linked recommendations (no generic boilerplate)
- [ ] Regulatory references are explicit and consistent with extracted flags
- [ ] Unsupported causal claims are flagged or suppressed

## 6. Evaluation Framework Upgrade (Publication-Grade)

Target areas:
- `src/evaluation/*`
- `scripts/run_raw_only_evaluation.py`

- [ ] Retain existing internal metrics (CCR/SFS alias, BRR, AGI/ECC aliases, URS, EES)
- [ ] Add/track executability and plausibility checks where implemented
- [ ] Add run-level quality gates and HOLD policy for failed thresholds
- [ ] Emit per-case + aggregate metric tables in one canonical format

Exit Criteria:
- [ ] Canonical raw-only runner produces one standardized JSON+MD package
- [ ] Metrics schema is stable across runs
- [ ] Threshold failures produce explicit remediation notes

## 7. Data and Output Governance

- [x] Keep new dataset outputs only under `data/new_data`
- [ ] Keep non-dataset verification outputs under `outputs/verification`
- [ ] Document dataset lineage (`source_path`, transform version, generation timestamp)
- [ ] Prevent mixed old-vs-new naming in active workflow

### 2026-03-14 Legacy Dataset Purge

Completed:
1. Updated active FAA loader path in `src/faa/sighting_filter.py` from `data/processed/faa_reports/*` to `data/new_data/faa/*`.
2. Removed legacy hint fields from loader output payload (`classification`, `fault_type`, `hazard_category`, confidence/hint flags).
3. Removed deprecated processed dataset directory:
	- deleted `data/processed/faa_reports/`
	- removed empty `data/processed/`
4. Updated dataset input reference in `README.md` to `data/new_data/faa/faa_simulatable.json`.

Evidence:
1. Workspace text scan shows zero remaining `data/processed` references in active text files.
2. Loader smoke check resolves to `data/new_data/faa/faa_high_risk_sightings.json` and loads 8501 records successfully.

### 2026-03-14 New-Data Runtime Smoke (Pre-Next-Phase Gate)

Completed:
1. Verified all required FAA new-data artifacts are present under `data/new_data/faa`.
2. Verified runtime loader paths/counts use only new-data files:
	- sightings: 8501
	- failures: 22
3. Executed live LLM #1 smoke generation from new-data records (one `sightings`, one `failures`) using `LLMClient.generate_scenario_config`.
4. Confirmed Phase 3 prompt-audit artifacts generated and passing for both records.

Evidence:
1. Smoke output directory: `outputs/verification/phase3_newdata_smoke_20260314_215812/`
2. Prompt-audit files:
	- `outputs/verification/phase3_newdata_smoke_20260314_215812/evaluation/phase3_prompt_audit_FAA_Apr2020-Jun2020_1.json`
	- `outputs/verification/phase3_newdata_smoke_20260314_215812/evaluation/phase3_prompt_audit_FAA_Apr2020-Jun2020_20.json`

### 2026-03-14 New-Data Batch5 Smoke (Phase 3 Exit-Gate Validation)

Completed:
1. Added reusable smoke runner `scripts/_phase3_batch5_smoke.py` for deterministic Phase 3 regression checks.
2. Executed 5-case mixed-source smoke from new-data loader outputs:
	- sightings: 3 cases
	- failures: 2 cases
3. Verified per-case pass conditions:
	- required fault contract fields present (`fault_type`, `fault_category`, `fault_severity`, `trigger`)
	- trigger schema valid (`type=time_elapsed_sec`)
	- waypoint arrays valid and non-empty with required keys
	- prompt audit exists and passes (`missing_required_fields=[]`, `found_forbidden_tokens=[]`)

Evidence:
1. Batch output directory: `outputs/verification/phase3_newdata_batch5_20260314_220620/`
2. Summary artifacts:
	- `outputs/verification/phase3_newdata_batch5_20260314_220620/phase3_newdata_batch5_summary.json`
	- `outputs/verification/phase3_newdata_batch5_20260314_220620/phase3_newdata_batch5_summary.md`
3. Batch results:
	- total: 5
	- passed: 5
	- failed: 0
	- pass_rate: 1.0
4. Prompt-audit files generated for all 5 cases in:
	- `outputs/verification/phase3_newdata_batch5_20260314_220620/evaluation/`

### 2026-03-14 Phase 4 Execution (Scenario-to-Simulation Fault Semantics)

Completed:
1. Added deterministic fault-semantics gate in `scripts/run_automated_pipeline.py`:
	- validates `fault_injection_supported` <-> `px4_commands.fault` marker consistency
	- rejects invalid marker values
	- enforces behavior-only marker for unsupported scenarios
	- marks run invalid by raising if gate fails
2. Removed ambiguity in runtime severity mapping:
	- mission executor now reads `fault_severity` from `fault_injection`
	- backward-compatible fallback to legacy `severity`
3. Added explicit runtime fault injection status propagation:
	- `native`, `emulated`, `fallback`, `none`, `failed`
	- persisted into `flight_config.fault_injection_status`
4. Added stronger report/config consistency metadata in `src/reporting/unified_reporter.py`:
	- marker mismatch warning
	- serialized `fault_semantics_validation` block in uncertainty analysis

Evidence:
1. Semantics smoke output:
	- `outputs/verification/phase4_semantics_smoke_20260314_221334/phase4_semantics_smoke_summary.json`
2. Gate result:
	- `gate_pass: true`
	- `violations: []`
3. Deterministic negative-check (tampered marker) confirms rejection:
	- `tamper_gate_pass: false`
	- violations include `marker_mismatch` and `unsupported_fault_must_use_behavioral_only_marker`

### 2026-03-14 Phase 5 Execution Start (RFlyMAD Taxonomy Mapping)

Completed:
1. Added versioned RFlyMAD mapping artifact at:
	- `data/new_data/rflymad/fault_taxonomy_mapping_v1.json`
2. Integrated mapping loader into benchmark engine (`src/evaluation/ground_truth_benchmark.py`):
	- auto-loads default mapping file from `data/new_data/rflymad/`
	- supports explicit override with config/CLI mapping path
	- normalizes keys/values and records mapping metadata (`source`, `path`, `version`)
3. Integrated CLI wiring in `scripts/run_benchmark.py`:
	- `--fault-mapping` argument to use alternate mapping files
4. Added mapping metadata into benchmark JSON output payload for reproducibility:
	- `fault_taxonomy_mapping` block with mapping source/version/entries

Evidence:
1. Mapping-loader smoke output confirms file-backed mapping:
	- `mapping_source: file`
	- `mapping_version: rflymad_to_aeroguardian_v1`
	- `mapping_entries: 4`
	- `wind_fault_maps_to: control`
2. Mapping file exists at governed new-data path:
	- `data/new_data/rflymad/fault_taxonomy_mapping_v1.json`

### 2026-03-14 RFlyMAD Source Correction (Authoritative Raw Path)

Completed:
1. Corrected RFlyMAD benchmark loaders to use authoritative raw root path provided by user:
	- `C:/VIRAK/Python Code/aero-guardian-full-version-including-dl&ml/data/raw/rflymad`
2. Added deterministic resolver behavior in benchmark loaders:
	- searches for `rflymad_cleaned.csv` under authoritative root
	- fails fast with explicit error if cleaned aggregate is missing
3. Updated benchmark runner user-facing guidance to reference authoritative RFlyMAD root and cleaned aggregate requirement.
4. Removed obsolete helper script to reduce confusion:
	- deleted `scripts/_phase3_batch5_smoke.py`
5. Cleaned stale duplicate Phase 3 verification folder:
	- removed `outputs/verification/phase3_newdata_batch5_20260314_220325/`

Evidence:
1. Resolver check emits explicit authoritative-path error when aggregate file is absent:
	- `FileNotFoundError: RFlyMAD authoritative root found but cleaned aggregate CSV missing...`
2. `outputs/verification/` now retains only the latest Phase 3 batch folder:
	- `phase3_newdata_batch5_20260314_220620/`

### 2026-03-14 RFlyMAD Deep Extraction + Coverage Validation

Completed:
1. Implemented multi-schema RFlyMAD extractor in `scripts/process_rflymad_data.py`:
	- supports TestCase + `TestInfo.csv` structure (HIL/SIL wind)
	- supports Real-* case folders with date-prefixed `*vehicle1.csv` and `TestInfo_*.xlsx`
	- parses both CSV and Excel metadata for deterministic fault onset flags
2. Added robust case discovery logic and metadata resolution:
	- fallback case-dir detection by nearest folder containing TestInfo metadata
	- automatic testinfo selection across `TestInfo.csv` and `TestInfo*.xlsx`
3. Fixed flight identity collisions by deriving `flight_id` from raw-root-relative case path (unique per case).
4. Regenerated canonical cleaned RFlyMAD dataset under governed new-data path.
5. Executed RFlyMAD-only benchmark validation on regenerated dataset.

Evidence:
1. Dataset artifact:
	- `data/new_data/rflymad/rflymad_cleaned.csv`
2. Extraction manifests:
	- `data/new_data/rflymad/rflymad_extraction_manifest.json`
	- `data/new_data/rflymad/rflymad_case_manifest.json`
3. Extraction coverage (manifest):
	- `total_cases: 823`
	- `total_rows: 96477`
	- `fault_case_counts: {wind_fault: 539, motor_fault: 117, sensor_fault: 127, normal: 40}`
4. Flight-ID integrity check:
	- unique flights in cleaned dataset: 823 (matches extracted case count)
5. Benchmark validation outputs:
	- `outputs/verification/benchmark_results.json`
	- `outputs/verification/benchmark_report.txt`
6. Benchmark headline metrics (RFlyMAD-only run):
	- flights: 823
	- precision: 0.739
	- recall: 0.675
	- f1: 0.706
	- avg detection latency: 3.552s

### 2026-03-14 RFlyMAD-Only Validation Hardening + Paper Artifacts

Completed:
1. Removed ALFA dependence from PX4 comparison benchmark path in `scripts/run_benchmark_validation.py`.
2. Enforced strict RFlyMAD-only behavior as default validation mode:
	- legacy mixed benchmark mode now requires explicit `--include-legacy-benchmarks`
	- no implicit ALFA loading in default execution
3. Added deterministic export of publication-ready validation artifacts after benchmark run:
	- detailed metrics CSV (overall + per class)
	- confusion matrix CSV
	- professional confusion matrix image
4. Added per-class confusion count fields (`tp`, `tn`, `fp`, `fn`) in benchmark output JSON for traceability.

Evidence:
1. Strict-run benchmark results file contains only RFlyMAD dataset:
	- `outputs/verification/benchmark_results.json`
	- `mode: rflymad_only`
	- `datasets: [RflyMAD]`
	- no `px4_comparison` block present in strict mode
2. Detailed paper artifacts generated:
	- `outputs/verification/rflymad_validation_metrics_detailed.csv`
	- `outputs/verification/rflymad_confusion_matrix.csv`
	- `outputs/verification/rflymad_confusion_matrix.png`
3. Updated report regenerated from strict mode:
	- `outputs/verification/benchmark_report.txt`

### 2026-03-14 RFlyMAD Validation Strengthening (Phase V1 Execution)

Completed:
1. Upgraded benchmark validator outputs in `scripts/run_benchmark_validation.py` without changing detector logic:
	- added imbalance-aware aggregate metrics (`macro_f1`, `micro_f1`, `weighted_f1`)
	- added onset-delay quantiles (`mean`, `median`, `p90`, `p95`)
	- added per-flight prediction trace export fields and flight-level fault decisions
	- added flight-level confusion matrix block in benchmark JSON results
2. Extended artifact export pipeline to produce:
	- `rflymad_per_flight_predictions.csv`
	- `rflymad_onset_delay_distribution.csv`
3. Re-ran strict default RFlyMAD-only validation to regenerate full artifacts package.

Evidence:
1. Regenerated strict benchmark results:
	- `outputs/verification/benchmark_results.json`
	- contains `mode: rflymad_only`, `datasets: [RflyMAD]`
2. New Phase V1 artifacts:
	- `outputs/verification/rflymad_per_flight_predictions.csv`
	- `outputs/verification/rflymad_onset_delay_distribution.csv`
3. Updated detailed metrics now include aggregate F1 variants and latency quantiles:
	- `outputs/verification/rflymad_validation_metrics_detailed.csv`
4. Flight-level confusion matrix now serialized in JSON:
	- `flight_level_confusion_matrix: {tp: 616, tn: 36, fp: 4, fn: 167}`

Exit Criteria:
- [ ] No new dataset artifacts appear outside `data/new_data`
- [ ] Artifact naming is raw-only canonical

## 8. Final Acceptance Gates

- [ ] End-to-end raw-only run completes on fixed case set
- [ ] FAA raw-to-processed lineage is reproducible and auditable
- [x] RFlyMAD validation report is generated from raw source path
- [ ] LLM #1 prompt audit passes raw-only policy checks
- [ ] LLM #2 report quality audit passes evidence/regulatory traceability checks
- [ ] Checklist status updated with dated evidence links

## 9. Execution Order (Recommended)

1. Baseline + manifest freeze
2. FAA extraction/validation hardening
3. LLM #1 contract hardening
4. RFlyMAD mapping + validation runs
5. LLM #2 report quality hardening
6. Canonical raw-only evaluation run
7. Final acceptance audit and manuscript-ready evidence packaging
