# AeroGuardian Evaluation Framework: A Multi-Dimensional Approach to Trustworthiness

**Author:** Manus AI
**Date:** 2026-03-14

## 1. Introduction

This document presents a comprehensive, multi-dimensional evaluation framework designed to rigorously assess the trustworthiness and performance of the AeroGuardian pipeline. The existing evaluation metrics (ESRI, SFS, BRR, ECC) provide a strong foundation for measuring the *internal consistency* of the system. However, to meet the standards of a top-tier publication like DASC 2026 and to build a truly trustworthy system, the evaluation must be expanded to address external validity, physical plausibility, and the quality of the generated safety intelligence, especially in the absence of labeled ground truth data.

This framework is structured to directly address the key research questions and reviewer feedback, providing a robust methodology to validate the contributions of the AeroGuardian project. It is designed to be implemented before the camera-ready deadline of April 25, 2026.

### 1.1. Clarifying the FAA Dataset Count

A foundational step in rigorous evaluation is accurate data accounting. Our analysis of the official FAA UAS Sightings Report public records [1] reveals a discrepancy with the numbers presented in the abstract and repository. A direct count of the available quarterly Excel files from October 2019 to September 2025 shows a total of **8,176** reported sightings. The remaining files for FY2022-2023 are on HTML pages and are estimated to contain another ~1,500-2,000 reports, bringing the estimated total to over 10,000.

**Recommendation:** For the camera-ready paper, it is critical to update all dataset numbers to reflect this verified count. The methods section should explicitly state the exact date range of reports used and the total number of incidents processed. For example:

> "We processed a total of **8,176** UAS sighting reports from the FAA public database, spanning from October 2019 to September 2025. After an automated filtering process to identify reports with sufficient narrative detail for simulation, a corpus of **[Correct Filtered Number]** reports was used for this study."

This transparency is crucial for reproducibility and credibility.

---

## 2. Evaluation Framework for Step 1: Narrative-to-Configuration (LLM #1)

The current Scenario Fidelity Score (SFS) is a good starting point for measuring keyword-level consistency. To build a truly robust evaluation, we must move beyond internal consistency and assess the **executability, plausibility, and stability** of the LLM's output. We propose three new metrics to complement the SFS.

### 2.1. Metric 1: Configuration Executability Rate (CER)

This metric directly challenges the current "successful conversion rate" by redefining success not as syntactic validity, but as functional executability within the PX4 SITL environment.

*   **Objective:** To measure the percentage of LLM-generated configurations that can be successfully loaded and executed by the PX4 simulator without causing immediate crashes or setup errors.
*   **Methodology:**
    1.  For a large, random sample of FAA reports (e.g., N=1,000), generate a PX4 configuration using LLM #1.
    2.  Automate a script that launches the PX4 SITL environment and attempts to run the generated mission profile.
    3.  A configuration is deemed "executable" if the simulation initializes, the drone arms, takes off, and begins its mission without critical pre-flight failures.
    4.  **CER = (Number of Executable Configurations / Total Configurations Attempted) * 100**
*   **Justification:** This provides a much stronger, more operationally relevant baseline for success. A configuration that is syntactically correct but operationally invalid is a failure of the pipeline. This metric directly assesses the LLM's ability to generate functionally sound outputs.

### 2.2. Metric 2: Physical Plausibility Score (PPS)

This metric addresses the core issue of whether the 31+ generated parameters are physically and operationally realistic. It moves beyond keyword matching to a rules-based validation of the configuration's content.

*   **Objective:** To quantify the physical realism of the generated simulation parameters.
*   **Methodology:** Develop a validation module that checks the generated configuration against a set of engineering and common-sense heuristics. Each check that passes contributes to the score.

| Plausibility Check | Category | Rationale | Example | Score Weight |
| :--- | :--- | :--- | :--- | :--- |
| **Waypoint Geometry** | Mission | Are waypoints geographically clustered around the start lat/lon? Are there impossibly large jumps between points? | Check if distance between consecutive waypoints is < 5km. | 0.25 |
| **Altitude Validity** | Mission | Is the max altitude within legal limits (e.g., < 122m AGL for Part 107) and physically achievable by the drone? | `max_altitude_m <= 122` and `takeoff_altitude_m < max_altitude_m`. | 0.20 |
| **Temporal Consistency** | Fault | Is the `fault_onset_sec` a reasonable time *after* takeoff and *before* the mission ends? | `10 < fault_onset_sec < mission_duration_sec - 10`. | 0.20 |
| **Fault Parameter Congruence** | Fault | Do the specific fault parameters match the `fault_type`? | If `fault_type` is `MOTOR_FAILURE`, is `affected_motor` specified correctly (e.g., `motor_1`)? | 0.20 |
| **Environmental Realism** | Environment | Are environmental parameters (wind, temperature) within a normal operational envelope? | `-20 < temperature_c < 50`. | 0.15 |

*   **Scoring:** The PPS for a single configuration is the weighted sum of the passed checks. The overall PPS for the system is the average across a large sample of configurations.
*   **Justification:** This metric directly addresses the concern that the LLM might be generating "nonsense" parameters that are syntactically correct but physically impossible. It provides a quantitative measure of the LLM's ability to reason about the physical world.

### 2.3. Metric 3: Cross-Run Semantic Stability (CRSS)

This metric directly addresses Reviewer 1's concern about the large degrees of freedom. Instead of seeking a single "correct" output, we measure the *consistency* of the LLM's interpretation across multiple runs.

*   **Objective:** To evaluate the stability and consistency of the LLM's interpretation of a given FAA narrative over multiple generation attempts.
*   **Methodology:**
    1.  For a smaller, diverse sample of FAA reports (e.g., N=100), run the LLM #1 generation process 5 times for each report (with temperature > 0 to allow for diversity).
    2.  For each report, this yields 5 different PX4 configurations.
    3.  Compare the key semantic outputs across the 5 runs.
*   **Scoring:** Stability is measured across key fields:

| Field | Stability Metric | Rationale |
| :--- | :--- | :--- |
| **`failure_category`** | Fleiss' Kappa or simple % agreement | The inferred high-level cause should be consistent. |
| **`failure_mode`** | % agreement | The specific inferred fault should be stable. |
| **`environment`** | % agreement | The inferred environment type should not change randomly. |
| **`waypoints_json`** | Average Haversine distance between the centroids of the 5 generated flight paths. | While trajectories will vary, their geographic center should remain stable. A low average distance indicates high spatial stability. |

*   **Justification:** High CRSS would indicate that while the specific parameters may vary, the LLM has a stable *semantic understanding* of the incident. Low stability would suggest the LLM is guessing and its output cannot be trusted. This provides a powerful way to measure reliability without needing a single ground truth.

---

## 3. Evaluation Framework for Step 2: Telemetry-to-Report (LLM #2)

Evaluating the quality of the final safety report is arguably the most critical and challenging part of this project. The current Evidence-Conclusion Consistency (ECC) metric is a vital first step, confirming that the report's claims are grounded in telemetry. However, it does not measure the *quality, actionability, or transferability* of the advice given. Since no "ground truth" safety reports exist, we must create a robust evaluation framework using structured analysis and expert-defined criteria.

### 3.1. Metric 4: Safety Report Quality Index (SRQI)

This metric introduces a formal, rubric-based scoring system to move beyond simple consistency checks and evaluate the overall quality of the generated report. This is the most effective way to quantitatively assess qualitative output in the absence of a direct ground truth.

*   **Objective:** To provide a quantitative score for the quality, actionability, specificity, and trustworthiness of the generated safety report.
*   **Methodology:** A human evaluator (or a future, well-prompted LLM-as-a-judge) scores each generated report against a detailed rubric. The final SRQI is the average score across all evaluated reports.

**SRQI Evaluation Rubric:**

| Category | Dimension | Scoring Criteria (1-5 Scale) | Weight |
| :--- | :--- | :--- | :--- |
| **Hazard Analysis** | **Clarity & Consistency** | **1:** Hazard is vague or contradicts the input `fault_type`. **3:** Hazard matches `fault_type` but is generic. **5:** `primary_hazard` and `observed_effect` are specific, clear, and perfectly aligned with the `fault_type` and telemetry summary. | 0.20 |
| | **Causal Reasoning** | **1:** `causal_chain` is illogical or contradicts the `subsystem_evidence_summary`. **3:** Chain is plausible but lacks temporal evidence. **5:** `causal_chain` presents a clear, temporally-ordered progression of failure, directly supported by the evidence summary. | 0.20 |
| **Actionable Guidance** | **Recommendation Specificity** | **1:** Recommendations are generic boilerplate (e.g., "Fly safely"). **3:** Recommendations are relevant but general (e.g., "Check motors"). **5:** Recommendations are highly specific and directly address the failure mode (e.g., "Implement pre-flight check for motor temperature and current draw anomalies > 2 standard deviations from baseline"). | 0.25 |
| | **Recommendation Actionability** | **1:** Recommendations are impractical or impossible for an operator to implement. **3:** Recommendations are technically possible but require significant effort. **5:** Recommendations are practical, cost-effective, and can be implemented by a typical UAS operator or maintenance crew. | 0.15 |
| **Trust & Transparency** | **Honesty & Limitations** | **1:** Report hallucinates telemetry evidence or makes claims of certainty. **3:** Report is accurate but omits limitations. **5:** Report explicitly and clearly states that it is a *simulation*, acknowledges the use of a *proxy aircraft*, and is honest about whether the expected behavior was reproduced. | 0.10 |
| | **Verdict Justification** | **1:** The final GO/CAUTION/NO-GO verdict is arbitrary. **3:** The verdict is weakly connected to the report content. **5:** The verdict is a direct, logical, and well-justified conclusion based on the evidence and analysis presented in the report. | 0.10 |

*   **Justification:** The SRQI provides a structured, repeatable method for evaluating the most important output of the AeroGuardian system. It directly addresses the user's concern about the trustworthiness of the report and provides a framework for answering RQ3 in a rigorous, quantitative manner. A high SRQI score would be a powerful indicator of a high-quality, useful system.

### 3.2. Metric 5: Platform Transferability Assessment (PTA)

This metric directly confronts the challenge that the simulation uses a generic quadrotor, while FAA reports involve a wide variety of aircraft. It evaluates how well the system handles this model mismatch.

*   **Objective:** To assess whether the safety report's recommendations are applicable to the *actual* aircraft type in the FAA report and whether the system is transparent about the simulation proxy.
*   **Methodology:** This is a two-part metric.
    1.  **Transparency Check (Automated):** A script parses the `explanation` field of every generated report. It searches for keywords related to the simulation proxy (e.g., "proxy," "surrogate," "represents quadrotor dynamics," "may not match the reported aircraft"). A score of **1** is given if a disclaimer is present, **0** otherwise.
    2.  **Applicability Score (Expert Review):** For a curated subset of N=50 reports where the aircraft type is known and is *not* a standard quadrotor (e.g., fixed-wing, helicopter drone), a domain expert rates the applicability of the generated recommendations on a 1-3 scale:
        *   **1 (Inapplicable):** The recommendation makes no sense for the target aircraft (e.g., recommending "redundant motor configuration" for a single-engine fixed-wing drone).
        *   **2 (Partially Applicable):** The recommendation is conceptually relevant but needs significant adaptation (e.g., "check control surfaces" is relevant for all aircraft, but the specifics differ).
        *   **3 (Directly Applicable):** The recommendation is valid and useful for the target aircraft with little or no modification (e.g., "verify battery health and discharge curves").
*   **Scoring:** The final PTA is a combination of the two parts: **PTA = (Average Transparency Score) * (Average Applicability Score / 3)**. A high PTA score indicates that the system is both honest about its limitations and generates advice that is general enough to be useful across different platforms.
*   **Justification:** This metric demonstrates a sophisticated understanding of the problem's constraints. It shows the evaluation is not naive to the proxy simulation issue and provides a clear measure of how well the system manages it, which will be a point of strength in the paper.

---

## 4. Consolidated Evaluation Framework

To provide a clear overview, the complete, enhanced evaluation framework combines the existing metrics with the new proposed metrics. This creates a two-tiered approach: **Tier 1** for automated, large-scale internal consistency checks, and **Tier 2** for deeper, more qualitative and externally-focused validation.

**Consolidated Metrics Table:**

| Tier | Step | Metric | What It Measures | Evaluation Method |
| :--- | :--- | :--- | :--- | :--- |
| **1** | 1: N-to-C | **SFS** (Scenario Fidelity Score) | **Internal Consistency:** Keyword alignment between FAA narrative and LLM config. | Automated Keyword Matching |
| **1** | 1: N-to-C | **CER** (Config Executability Rate) | **Functional Validity:** Can the generated config run in PX4 SITL? | Automated Script (Launch & Test) |
| **1** | 1: N-to-C | **PPS** (Physical Plausibility Score) | **Physical Realism:** Are the generated parameters physically and operationally plausible? | Automated Rule-Based Heuristics |
| **2** | 1: N-to-C | **CRSS** (Cross-Run Semantic Stability) | **LLM Reliability:** Is the LLM's interpretation of a narrative stable across multiple runs? | Statistical Analysis (Fleiss' Kappa, Centroid Distance) |
| **1** | 2: T-to-R | **ECC** (Evidence-Conclusion Consistency) | **Internal Consistency:** Are the report's claims backed by telemetry evidence? | Automated Keyword & Anomaly Matching |
| **2** | 2: T-to-R | **SRQI** (Safety Report Quality Index) | **Output Quality:** How actionable, specific, and trustworthy is the final report? | Human or LLM-based Rubric Scoring |
| **2** | 2: T-to-R | **PTA** (Platform Transferability Assessment) | **Generalizability:** Is the advice useful for the actual aircraft, not just the proxy model? | Automated Check + Expert Review |

## 5. Proposed Experimental Design for DASC 2026 Paper

Given the camera-ready deadline of April 25, 2026, the following experimental design is proposed to generate the data for this enhanced evaluation framework. This plan is ambitious but achievable.

**Experiment 1: Full-Scale Pipeline Run & Tier 1 Analysis**

*   **Objective:** To generate a large dataset for automated analysis and to calculate the Tier 1 metrics.
*   **Procedure:**
    1.  Run the entire AeroGuardian pipeline (Filter -> LLM #1 -> PX4 SITL -> LLM #2) on the largest possible number of reports from the verified FAA dataset (target N > 5,000).
    2.  For each successful end-to-end run, automatically calculate:
        *   Scenario Fidelity Score (SFS)
        *   Evidence-Conclusion Consistency (ECC)
        *   Configuration Executability Rate (CER)
        *   Physical Plausibility Score (PPS)
    3.  Aggregate the results to produce mean, median, and standard deviation for each metric. These will form the backbone of the quantitative results section.

**Experiment 2: Deep Dive on LLM Stability and Report Quality (Tier 2 Analysis)**

*   **Objective:** To perform the deeper, more resource-intensive Tier 2 evaluations on a representative sample.
*   **Procedure:**
    1.  Randomly select a diverse subset of **N=200** reports from the successfully executed runs in Experiment 1.
    2.  **For CRSS:** For each of these 200 reports, run the LLM #1 generation 5 times. Calculate the semantic stability metrics (agreement on `failure_category`, `failure_mode`, and `environment`, and the spatial stability of waypoints).
    3.  **For SRQI & PTA:** For these same 200 reports, generate the final safety report. Perform the human-led evaluation:
        *   Score each of the 200 reports using the detailed SRQI rubric.
        *   Perform the Platform Transferability Assessment (PTA), including the transparency check and the expert applicability rating.

## 6. Conclusion and Next Steps

This enhanced evaluation framework provides a clear and powerful path to dramatically strengthening the AeroGuardian paper. By moving beyond internal consistency to measure executability, plausibility, stability, and quality, this methodology will provide compelling evidence of the system's trustworthiness and utility. It directly addresses the key challenges of the project—the lack of ground truth and the ambiguity of the source data—by transforming them into measurable components of the evaluation itself.

**Recommended Next Steps:**

1.  **Update the Dataset:** Immediately correct the FAA data counts in the repository and paper draft.
2.  **Implement the Metrics:** Develop the automated scripts and rubrics for the CER, PPS, CRSS, SRQI, and PTA metrics.
3.  **Execute the Experiments:** Begin the proposed experimental design as soon as possible to ensure data is ready for the April 25th deadline.

By adopting this framework, the AeroGuardian project can present a far more compelling and defensible case for its contributions to the field of aviation safety.

---

## References

[1] Federal Aviation Administration. (2026, January 7). *UAS Sightings Report*. Retrieved from https://www.faa.gov/uas/resources/public_records/uas_sightings_report
