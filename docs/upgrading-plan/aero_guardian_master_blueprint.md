# AeroGuardian Project: Master Blueprint for AI Coding Assistant

**Author:** Manus AI
**Date:** 2026-03-14

## 1. Executive Summary: AeroGuardian's Vision for World-Class UAS Safety Intelligence

This Master Blueprint serves as the definitive guide for the AI Coding Assistant to implement the next generation of the AeroGuardian project. Our ambition is to transform raw, often ambiguous FAA UAS sighting reports into **predictive, physics-informed, and regulatory-aware safety intelligence**. This system will not merely describe past incidents but will simulate potential scenarios, identify causal factors, flag regulatory violations, and provide actionable guidance to prevent future occurrences. This approach significantly surpasses existing descriptive analyses, such as the AIAA research discussed, by offering a **trustworthy, verifiable, and impactful solution** to a critical real-world problem.

## 2. Core Philosophy: Trustworthiness through Grounded Intelligence

The central tenet of AeroGuardian is to ensure **trustworthiness** at every stage. This is achieved by combining the strengths of Large Language Models (LLMs) with **rigorous, physics-informed, and rule-based validation layers**. We explicitly reject a purely 
purely LLM-driven approach for critical safety applications, as it lacks the inherent verifiability and grounding required for trustworthiness. Instead, we leverage the LLM for its powerful inference capabilities, but always within a framework of **pre-validated inputs and post-validated outputs**.

## 3. Addressing User Concerns & Enhancing Trustworthiness

### 3.1. The Superiority of "Hard-Code + Physics" Extraction (Response to User Question 1)

**User Concern:** "How can we make sure that the extracting from raw FAA in hard code is useful, correct and better than inserting all raw of each report to the LLM#1? Doesn't this lead to bad context info?"

**AeroGuardian's Approach:** The "Hard-Code + Physics" layer is **not a low-quality extraction**; it is a **physics-informed, rule-based validation and enrichment layer**. Its superiority over feeding raw text directly to LLM #1 stems from:

1.  **Grounded Facts:** Raw FAA reports are often vague, incomplete, or contain subjective observations. The physics-informed layer extracts objective, quantifiable facts (e.g., altitude, UAS type, proximity) and validates them against known physical limits and drone performance characteristics. This provides LLM #1 with **grounded numerical and categorical data**, rather than ambiguous natural language.
2.  **Prevention of Hallucinations:** LLMs are prone to hallucinating plausible but incorrect information when faced with ambiguous input. By pre-validating parameters like altitude (e.g., flagging physically impossible altitudes or those requiring specialized UAS), we prevent the LLM from generating unrealistic PX4 configurations.
3.  **Regulatory Context Integration:** This layer explicitly checks for violations of FAA regulations (e.g., Part 107.51 altitude limits, Part 107.31 VLOS indicators). This critical information is then passed to the LLM as a **structured regulatory flag**, ensuring that the LLM is aware of the legal context during scenario generation and report writing.
4.  **Efficiency and Focus:** The LLM can then focus its cognitive resources on complex inference tasks (e.g., inferring failure modes from narrative nuances) rather than spending tokens on parsing and validating basic facts that can be deterministically checked.

**Conclusion:** The "Hard-Code + Physics" layer acts as a **trustworthy guardian**, ensuring that the LLM receives a high-quality, physics-validated, and regulatory-aware representation of the FAA report, leading to more accurate and reliable PX4 configurations.

### 3.2. The Purpose of RFlyMAD Validation (Response to User Question 2)

**User Concern:** "Our main purpose of using RFlyMAD dataset to validate the flight telemetry and avoiding inputting raw telemetry to the LLM to analyze and also provide the raw FAA data information again to the LLM#2 along with validated telemetry. Do you really fully understand this?"

**AeroGuardian's Approach:** Yes, I fully understand and endorse this critical distinction. The RFlyMAD dataset is paramount for **validating the fidelity and accuracy of our telemetry analysis components** (`TelemetryAnalyzer` and `BehaviorValidator`).

*   **Telemetry Vetting:** RFlyMAD provides ground truth for various fault types and their onset. By running our `FailureEmulator` with RFlyMAD-derived faults and then analyzing the resulting telemetry with our `TelemetryAnalyzer` and `BehaviorValidator`, we can quantitatively measure:
    *   **Signature Uniqueness:** Does each fault produce a distinct telemetry signature?
    *   **Detection Rate:** How accurately do we detect the injected faults?
    *   **Onset Delay:** How quickly do we detect them?
    *   **Subsystem Attribution:** Can we correctly identify the affected subsystem?
*   **Avoiding Raw Telemetry to LLM #2:** The goal is *not* to feed raw telemetry to LLM #2. Instead, LLM #2 receives a **structured, validated summary** from the `TelemetryAnalyzer` and `BehaviorValidator`. This summary includes key statistics, detected anomalies, and their severity. This pre-processed, physics-vetted telemetry evidence is far more reliable and interpretable for the LLM than raw sensor data, preventing misinterpretations and ensuring the safety report is grounded in engineering facts.

**Conclusion:** RFlyMAD is the cornerstone for establishing the **trustworthiness of our telemetry analysis**, which in turn provides the high-fidelity evidence required for LLM #2 to generate accurate and actionable safety reports.

### 3.3. Applicability of FAA Regulations (Response to User Question 3, Part 1)

**User Concern:** "Is the rule apply to all even if the model of UAV or the reported is not limited under the regulation?"

**AeroGuardian's Approach:** Generally, **yes, FAA regulations apply broadly to UAS operations within the National Airspace System (NAS)**, regardless of the specific model, unless a specific waiver or authorization has been granted. The primary regulations relevant to AeroGuardian are:

*   **Part 107 (Small Unmanned Aircraft Systems):** Applies to most commercial and recreational drone operations. Key limitations include altitude (400 ft AGL), visual line of sight (VLOS), and operations over people. While some waivers exist, the default assumption for an observed UAS sighting is that Part 107 rules apply unless explicitly stated otherwise (which is rare in FAA sighting reports).
*   **Part 89 (Remote Identification):** Requires most drones operating in the NAS to broadcast identification and location information. This is a newer regulation but broadly applicable.

**Edge Cases:** While some UAS (e.g., very small, tethered, or those operating under specific research exemptions) might have different rules, for the purpose of analyzing general FAA sighting reports, assuming adherence to Part 107 and Part 89 provides a robust baseline for identifying potential violations. The system can be designed to flag observations that *might* indicate an exception (e.g., "UAS operating under waiver" if such information were available in the narrative, though unlikely).

**Conclusion:** For the vast majority of FAA sighting reports, the rules under Part 107 and Part 89 are applicable. AeroGuardian will flag deviations from these standard rules as potential violations, providing critical regulatory context to the safety reports.

### 3.4. Inclusion of FAA Rules in LLM #1 and LLM #2 (Response to User Question 3, Part 2)

**User Concern:** "Where do we include the rule of FAA? Both of LLM#1 and LLM#2 to produce report and mention in report?"

**AeroGuardian's Approach:** FAA regulations will be strategically integrated into both LLM #1 and LLM #2 to enhance both the scenario generation and the safety reporting:

1.  **LLM #1 (Scenario Generator) - Contextual Awareness:**
    *   **Input:** The "Hard-Code + Physics" layer will explicitly provide `regulatory_violations` (e.g., `altitude_violation_flag: True`, `vlos_violation_flag: True`) as structured input to LLM #1. This informs the LLM about the *context* of the incident.
    *   **Impact:** While LLM #1's primary role is to generate a PX4 configuration, knowing about a regulatory violation (e.g., extreme altitude) can influence its interpretation of the narrative and the plausibility of certain parameters. For instance, if an altitude violation is detected, the LLM might be prompted to consider more extreme environmental conditions or a more severe failure mode that could lead to such an altitude.
    *   **Example:** If the narrative mentions "UAS at 1000 ft AGL," the physics layer flags `altitude_violation_flag: True`. LLM #1 then receives this flag and can generate a scenario that accurately reflects this high altitude, potentially inferring a control loss or environmental factor that led to it.

2.  **LLM #2 (Safety Report Generator) - Explicit Reporting:**
    *   **Input:** LLM #2 will receive the `regulatory_violations` flags (from the initial physics layer) and potentially new violations detected during simulation (e.g., if the simulated drone exceeds altitude limits even without an initial violation). It will also receive the `validated_telemetry_stats` which might show evidence of regulatory non-compliance (e.g., excessive speed).
    *   **Output:** LLM #2 will be explicitly prompted to generate a `regulatory_violation_summary` field in its output. This field will clearly state the violated FAA rule(s) and provide context.
    *   **Example:** "The incident involved a likely violation of FAA Part 107.51 (c) which limits small UAS operations to 400 feet AGL, as the reported altitude was 1000 feet AGL. Additionally, the telemetry analysis indicated sustained speeds exceeding 100 mph, potentially violating Part 107.51 (a)."

**Conclusion:** FAA rules are integrated as **contextual cues for LLM #1** to generate realistic scenarios and as **explicit reporting elements for LLM #2** to provide actionable, legally relevant safety intelligence.

## 4. Detailed Master Plan for AI Coding Assistant

This section provides a granular, step-by-step plan for the AI Coding Assistant, including file modifications and expected outcomes.

### 4.1. Phase 1: Raw-to-Rich FAA Data Analysis (Physics-Informed Pre-processing)

**Goal:** To transform raw FAA Excel data into a structured, physics-validated, and regulatory-aware input for LLM #1, enhancing trustworthiness and preventing hallucinations.

**Sub-steps:**

1.  **Modify `scripts/process_faa_data.py`:**
    *   **Action:** Refactor `_create_incident_record` to extract and preserve *all* relevant raw fields from the FAA Excel rows. This includes `Date`, `City`, `State`, `Summary`, `Description`, `Altitude`, `UAS Type`, `Incident Type`, and any other potentially useful columns.
    *   **New Functionality:** Implement a new `PhysicsInformedValidator` class (or similar functions) within this script or as a new module (e.g., `src/data_processing/physics_validator.py`). This validator will:
        *   **Altitude Plausibility:** Parse altitude strings (e.g., "500 feet", "1000ft AGL") and convert to meters. Flag `altitude_violation_flag: True` if > 400ft AGL (Part 107.51).
        *   **UAS Type Consistency:** Analyze `UAS Type` and `Description` fields. If a "small quadcopter" is reported at 8000ft, generate `observation_confidence_score: LOW` and `physics_anomaly_flag: True`.
        *   **Proximity/Hazard Detection:** Extract distances from manned aircraft. Flag `close_approach_flag: True` if < 500ft, `nm_air_collision_flag: True` if evasive action mentioned.
        *   **VLOS Indicators:** Analyze narrative for phrases suggesting beyond visual line of sight (e.g., "lost sight", "far away"). Flag `vlos_violation_flag: True`.
        *   **Remote ID Indicators:** If the report mentions lack of identification or evasive action to avoid identification, flag `remote_id_violation_flag: True` (Part 89).
    *   **Output Structure:** The script will now output a JSON record for each FAA sighting that includes:
        ```json
        {
            "report_id": "fy24_q2_1",
            "raw_fields": { /* all original Excel fields */ },
            "validated_parameters": {
                "altitude_m": 152.4, // Physics-validated altitude
                "uas_type_inferred": "multirotor",
                "location_lat": 25.79,
                "location_lon": -80.29
            },
            "physics_flags": {
                "physics_anomaly_flag": false,
                "observation_confidence_score": "HIGH"
            },
            "regulatory_flags": {
                "altitude_violation_flag": true, // > 400ft AGL
                "vlos_violation_flag": false,
                "close_approach_flag": true,
                "remote_id_violation_flag": false
            },
            "narrative_summary_for_llm": "...cleaned and summarized narrative..."
        }
        ```

2.  **Modify `src/llm/signatures.py` (for LLM #1 `FAA_To_PX4_Complete`):**
    *   **Action:** Update the `FAA_To_PX4_Complete` signature to accept the new, rich input structure.
    *   **Input Fields:** Add `dspy.InputField`s for `validated_parameters`, `physics_flags`, `regulatory_flags`, and `narrative_summary_for_llm`.
    *   **Prompting:** Revise the prompt to instruct the LLM to synthesize information from all these structured inputs. Emphasize using `validated_parameters` as primary facts and `regulatory_flags` as critical context for scenario generation.

3.  **Modify `src/llm/scenario_generator.py`:**
    *   **Action:** Update the `generate` method to pass the new structured input from `process_faa_data.py` to the `FAA_To_PX4_Complete` LLM call.
    *   **Logic:** Adapt the internal logic to utilize the `validated_parameters` and `regulatory_flags` when constructing the `ScenarioConfig`.

### 4.2. Phase 2: LLM Optimization for MAVSDK Compatibility & Regulatory Reporting

**Goal:** Ensure LLM outputs are precise, MAVSDK-compatible for robust fault injection, and generate regulatory-aware safety reports.

**Sub-steps:**

1.  **Modify `src/llm/signatures.py` (for LLM #1 `FAA_To_PX4_Complete` output):**
    *   **Action:** Replace the ambiguous `px4_fault_cmd` string output with structured, MAVSDK-compatible parameters.
    *   **Output Fields:** Introduce `dspy.OutputField`s:
        *   `sim_fault_category: str` (e.g., `PROPULSION`, `NAVIGATION`, matching `FailureCategory` enum).
        *   `sim_fault_type_specific: str` (e.g., `motor_failure`, `gps_loss`, matching `FailureEmulator` internal types).
        *   `sim_fault_severity: float` (0.0-1.0).
        *   `sim_parachute_trigger: bool`.
        *   `waypoints_json: str` (JSON string of MAVSDK-compatible waypoints).
        *   `reasoning: str` (LLM's justification for these parameters).

2.  **Modify `src/llm/scenario_generator.py`:**
    *   **Action:** Update the `generate` method to directly use the new structured outputs from LLM #1 to call the `FailureEmulator`.
    *   **Logic:** Remove any parsing logic for `px4_fault_cmd`. Directly pass `sim_fault_category`, `sim_fault_type_specific`, `sim_fault_severity`, and `sim_parachute_trigger` to `failure_emulator.emulate()`.

3.  **Modify `src/llm/signatures.py` (for LLM #2 `GeneratePreFlightReport` input/output):**
    *   **Action:** Refine the input to LLM #2 and enhance its output for regulatory reporting.
    *   **Input Fields:** Update `GeneratePreFlightReport` to accept:
        *   `original_faa_report_summary: str` (the `narrative_summary_for_llm` from Phase 1).
        *   `simulated_scenario_config: str` (JSON representation of the `ScenarioConfig` used for simulation).
        *   `validated_telemetry_summary: str` (the `to_summary_text` from `TelemetryStats`).
        *   `detected_anomalies_list: List[str]` (from `TelemetryAnalyzer`).
        *   `overall_anomaly_severity: str` (from `TelemetryAnalyzer`).
        *   `brr_score: float` (from `BehaviorValidator`).
        *   `regulatory_violations_detected: List[str]` (list of specific FAA rule violations, e.g., "Part 107.51(c) Altitude Limit").
    *   **Output Fields:** Enhance output to include:
        *   `regulatory_violation_summary: str` (explicitly state violated FAA rules with context).
        *   `actionable_guidance: str` (specific recommendations for operators/investigators, e.g., "Review Part 107.31 VLOS requirements").
        *   `subsystem_evidence_summary: str` (detailed explanation of telemetry evidence for identified subsystem failure).

### 4.3. Phase 3: RFlyMAD-Based Telemetry Validation

**Goal:** Rigorously validate the `TelemetryAnalyzer` and `BehaviorValidator` against ground truth from the RFlyMAD dataset, ensuring high-fidelity telemetry evidence for LLM #2.

**Sub-steps:**

1.  **Detailed RFlyMAD Fault Mapping:**
    *   **Action:** Create a comprehensive, explicit mapping between RFlyMAD's 11 fault types (e.g., "Motor(1-4)", "GPS") and AeroGuardian's `FailureCategory` enum and `sim_fault_type_specific` strings.
    *   **Location:** This mapping should reside in a dedicated configuration file (e.g., `config/rflymad_mapping.yaml`) or directly within `src/evaluation/ground_truth_benchmark.py`.

2.  **Modify `src/evaluation/ground_truth_benchmark.py`:**
    *   **Action:** Update `BenchmarkConfig.fault_mapping` to use the detailed RFlyMAD mapping.
    *   **Ground Truth Onset Time:** Implement logic to extract precise fault onset times from RFlyMAD's `GTData` (`fault_state`) or ULog/ROSBAG (`rfly_ctrl_lxl` message).
    *   **Integration with `FailureEmulator`:** Modify the benchmark runner to:
        *   For each RFlyMAD flight, use the ground truth fault type and severity to call the `FailureEmulator` (which now accepts structured `sim_fault_category`, `sim_fault_type_specific`, `sim_fault_severity`).
        *   Collect the simulated telemetry.
        *   Run the `TelemetryAnalyzer` and `BehaviorValidator` on this simulated telemetry.
        *   Compare the `BehaviorValidator`'s detected anomalies and inferred subsystem against the RFlyMAD ground truth.
    *   **New Metrics:** Calculate and report:
        *   **Signature Uniqueness Score (SUS):** Analyze telemetry patterns for distinctness across fault types.
        *   **Mean Onset Delay (MOD):** Measure the time from ground truth fault onset to detection.
        *   **Subsystem Attribution Accuracy:** Percentage of correctly identified subsystems.

3.  **Modify `src/evaluation/behavior_validation.py`:**
    *   **Action:** Refine the `FAULT_TO_ANOMALIES` dictionary to align perfectly with the RFlyMAD fault types and their expected telemetry signatures.
    *   **Dynamic Thresholds (Optional but Recommended):** Explore implementing adaptive anomaly detection thresholds. This could involve:
        *   **Baseline Learning:** Computing baseline telemetry statistics from "No Fault" RFlyMAD flights.
        *   **Adaptive Thresholds:** Adjusting anomaly thresholds based on the learned baseline, making detection more sensitive to deviations from normal flight behavior.

### 4.4. Phase 4: High-Fidelity Validation & Evidence Generation

**Goal:** Generate quantitative evidence and paper-ready plots to demonstrate the trustworthiness and performance of the AeroGuardian system.

**Sub-steps:**

1.  **Data Collection Strategy:**
    *   **Full FAA Dataset Processing:** Process all 8,031 simulatable FAA records through the updated LLM #1 to generate a comprehensive set of PX4 configurations.
    *   **RFlyMAD Simulation Runs:** Execute the `FailureEmulator` for all RFlyMAD fault cases, logging detailed telemetry for each.
    *   **Telemetry Logging:** Ensure all simulation runs (both FAA-derived and RFlyMAD-derived) log detailed telemetry in a consistent format.

2.  **Quantitative Metrics and Plots:**
    *   **LLM #1 Accuracy (FAA to PX4 Config):**
        *   **Configuration Executability Rate (CER):** Plot the percentage of LLM-generated PX4 configurations that successfully execute in PX4 SITL without errors.
        *   **Physical Plausibility Score (PPS):** For a statistically significant subset of FAA reports, conduct human expert review (if feasible) or use advanced rule-based checks to assess the physical plausibility of generated parameters. Plot the distribution of PPS.
        *   **Cross-Run Semantic Stability (CRSS):** Run LLM #1 multiple times with the same FAA input and measure the consistency of key output parameters (e.g., `sim_fault_category`, `waypoints_json`). Plot variance and agreement scores.
        *   **Parameter Accuracy:** Compare LLM-inferred values (e.g., altitude, UAS type) against baselines derived from the "Hard-Code + Physics" layer. Plot accuracy scores.
    *   **LLM #2 Accuracy (Telemetry to Safety Report):**
        *   **Safety Report Quality Index (SRQI):** Implement the structured rubric for SRQI (Completeness, Specificity, Traceability, Actionability, Regulatory Compliance) and apply it to a sample of generated safety reports. Plot the distribution of SRQI scores.
        *   **Primary Hazard/Causal Chain Accuracy:** Compare LLM-inferred `primary_hazard` and `causal_chain` against the known fault injected in RFlyMAD simulations. Plot accuracy metrics.
        *   **Subsystem Attribution Accuracy:** Compare LLM-inferred `subsystem_evidence_summary` against the actual subsystem affected in RFlyMAD simulations. Plot accuracy metrics.
    *   **Behavior Reproduction Rate (BRR) - RFlyMAD Validation:**
        *   **Detection Rate (True Positive Rate):** Plot the percentage of injected RFlyMAD faults correctly detected by the `TelemetryAnalyzer` and `BehaviorValidator`.
        *   **False Positive Rate:** Plot the percentage of normal flights (from RFlyMAD) incorrectly flagged as anomalous.
        *   **Onset Delay:** Plot the distribution of time difference between actual fault injection and detection.
        *   **Subsystem Attribution Accuracy:** Plot the accuracy of `BehaviorValidator` in identifying the correct subsystem affected by the fault.

3.  **Evidence Traceability:**
    *   **LLM Reasoning Analysis:** Log and analyze the `reasoning` field from both LLMs for consistency, logical flow, and adherence to provided inputs and regulatory context. This can be a qualitative analysis supported by quantitative metrics.
    *   **Telemetry Markers:** Utilize `telemetry_markers` from `FailureEmulator` to precisely correlate fault injection events with observed telemetry anomalies in plots.

### 4.5. Phase 5: File and Folder Structure Updates

To support these enhancements, the following file and folder structure updates are crucial:

*   **`data/processed/faa_reports/`**: Will store the richer, physics-validated, and regulatory-aware JSON representations of FAA reports.
*   **`src/data_processing/`**: New directory for `physics_validator.py` and other data pre-processing utilities.
*   **`src/llm/signatures.py`**: Updated with new `dspy.InputField`s and `dspy.OutputField`s for both LLMs.
*   **`src/llm/scenario_generator.py`**: Modified to handle new structured inputs and outputs from LLM #1.
*   **`src/analysis/telemetry_analyzer.py`**: Updated to provide more structured output for LLM #2.
*   **`src/evaluation/ground_truth_benchmark.py`**: Significantly updated for detailed RFlyMAD fault mapping, ground truth onset times, and direct comparison of LLM-inferred fault types.
*   **`src/evaluation/behavior_validation.py`**: `FAULT_TO_ANOMALIES` mapping refined and potentially includes dynamic thresholds.
*   **`scripts/process_faa_data.py`**: Refactored to extract and preserve all relevant raw fields and apply physics/regulatory validation.
*   **`config/`**: New directory for `rflymad_mapping.yaml` and other configuration files.
*   **`outputs/evaluation_results/`**: Stores detailed JSON and CSV results from the expanded evaluation.
*   **`outputs/plots/`**: Stores all generated plots and visualizations for the paper.

## 5. Conclusion: AeroGuardian as a Landmark in UAS Safety

This Master Blueprint outlines a path for AeroGuardian to become a landmark project in UAS safety. By meticulously integrating physics-informed validation, regulatory awareness, and rigorous telemetry vetting, the system will provide a level of trustworthiness and actionable intelligence currently unavailable. This will not only lead to a highly impactful publication at DASC 2026 but will also lay the groundwork for a system that can genuinely enhance the safety and security of the national airspace, fulfilling the ambitious vision of its creators.
