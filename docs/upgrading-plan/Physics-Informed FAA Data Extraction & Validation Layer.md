# Physics-Informed FAA Data Extraction & Validation Layer

## 1. Overview
The "Hard-Code + Physics" layer serves as a **grounding filter** between the raw, often ambiguous FAA sighting reports and the LLM #1 (Scenario Generator). Its purpose is to extract verifiable facts, validate them against physical laws and FAA regulations, and provide a high-fidelity context that prevents LLM hallucinations.

## 2. Extraction & Validation Logic

### 2.1. Altitude Validation (§107.51)
*   **Extraction:** Identify all numerical values associated with "ft", "feet", "AGL", or "MSL".
*   **Physics Check:** If altitude > 10,000ft, flag as "High-Altitude Proxy Required" (fixed-wing or specialized UAS).
*   **Regulatory Check:** If altitude > 400ft AGL, flag as a **Part 107.51 Violation**.
*   **Output to LLM:** Provide `validated_altitude_m` and `altitude_violation_flag`.

### 2.2. UAS Type & Physical Characteristics
*   **Extraction:** Identify keywords for color (black, white, red, silver, gray), shape (quadcopter, fixed-wing, balloon, object), and size (small, medium, large).
*   **Physics Check:** Cross-reference shape with altitude. For example, a "small quadcopter" at 8,000ft is physically improbable due to battery and wind constraints; flag as "High-Uncertainty Observation".
*   **Output to LLM:** Provide `extracted_uas_type`, `physical_description_summary`, and `observation_confidence_score`.

### 2.3. Close Approach & Hazard Analysis (§107.37)
*   **Extraction:** Identify distances (e.g., "within 500 feet", "3 o'clock position") and evasive actions ("took evasive maneuvers", "NMAC").
*   **Hazard Check:** Categorize as "Near-Miss Air Collision (NMAC)" or "Close Approach".
*   **Output to LLM:** Provide `hazard_category` and `proximity_estimate_m`.

## 3. Benefits Over Raw-to-LLM
| Feature | Raw-to-LLM | Hard-Code + Physics (AeroGuardian) |
| :--- | :--- | :--- |
| **Accuracy** | Prone to hallucinating improbable altitudes/speeds. | Constrained by physical laws and drone performance limits. |
| **Regulatory Context** | May miss specific FAA rule violations. | Explicitly flags Part 107/89 violations for the report. |
| **Trustworthiness** | "Black box" inference. | Traceable, rule-based evidence for every claim. |
| **Efficiency** | LLM spends tokens parsing messy text. | LLM receives clean, structured "Engineering Context". |
