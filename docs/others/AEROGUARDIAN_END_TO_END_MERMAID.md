# AeroGuardian End-to-End Mermaid Flows

Date: 2026-03-12

This document provides two Mermaid flow definitions:
- Detailed system flow with subprocesses and evaluation gates.
- Concrete worked example flow for one FAA sighting case.

Naming policy used here follows full-meaning abbreviations:
- CCR: Constraint Correctness Rate
- BRS: Behavior Reproduction Score
- AGI: Actionability and Grounding Index
- URS: Uncertainty Robustness Score
- EES: End-to-End Evaluation Score, EES = CCR * BRS * AGI * URS

Line style policy:
- Normal operational flow uses solid arrows (-->)
- Evaluation and validation flow uses dotted arrows (-.->)

## 1) Detailed End-to-End Flow (with subprocesses)

~~~mermaid
flowchart TD

    %% Color and style definitions
    classDef data fill:#E8F4FD,stroke:#2B6CB0,stroke-width:1.5px,color:#1A202C;
    classDef llm fill:#FEEBC8,stroke:#C05621,stroke-width:1.5px,color:#1A202C;
    classDef sim fill:#E6FFFA,stroke:#2C7A7B,stroke-width:1.5px,color:#1A202C;
    classDef eval fill:#FFF5F5,stroke:#C53030,stroke-width:2px,color:#1A202C;
    classDef score fill:#FAF089,stroke:#975A16,stroke-width:2px,color:#1A202C;
    classDef output fill:#E9D8FD,stroke:#6B46C1,stroke-width:1.5px,color:#1A202C;

    A[FAA UAS Sighting Narrative]
    B[Phase 1 | LLM1 (DSPy) -> Executable PX4 Configuration]
    C[Phase 2 | PX4 SITL + MAVSDK Telemetry]
    D[Phase 3 | LLM2 (Narrative + Telemetry) -> Risk Advisory Report]

    A --> B --> C --> D

    subgraph E1[Evaluation Layer]
        E11[CCR: Narrative -> Config fidelity]
        E12[BRS: Telemetry anomaly reproduction]
        E13[AGI: Actionability and evidence grounding]
        E14[URS: Robustness under narrative ambiguity]
    end

    A -.-> E11
    B -.-> E11
    C -.-> E12
    C -.-> E13
    D -.-> E13
    A -.-> E14
    B -.-> E14
    C -.-> E14

    F[EES = CCR * BRS * AGI * URS]
    G[Analyst-Facing Output: Traceable FAA case analysis]
    H[Operator-Facing Advisory after analyst confirmation]

    E11 --> F
    E12 --> F
    E13 --> F
    E14 --> F
    D --> G --> H
    F --> G

    class A data;
    class B,D llm;
    class C sim;
    class E11,E12,E13,E14 eval;
    class F score;
    class G,H output;
~~~

## 2) Actual Worked Example Flow

~~~mermaid
flowchart TD

    %% Color and style definitions
    classDef data fill:#E8F4FD,stroke:#2B6CB0,stroke-width:1.5px,color:#1A202C;
    classDef llm fill:#FEEBC8,stroke:#C05621,stroke-width:1.5px,color:#1A202C;
    classDef sim fill:#E6FFFA,stroke:#2C7A7B,stroke-width:1.5px,color:#1A202C;
    classDef eval fill:#FFF5F5,stroke:#C53030,stroke-width:2px,color:#1A202C;
    classDef score fill:#FAF089,stroke:#975A16,stroke-width:2px,color:#1A202C;
    classDef output fill:#E9D8FD,stroke:#6B46C1,stroke-width:1.5px,color:#1A202C;

    A[Example FAA Case: Motor failure + parachute deployment]
    B[LLM1 Output: motor_failure, multirotor config, mission parameters]
    C[PX4 Run: fault injection + telemetry capture]
    D[LLM2 Output: UAS Pre-Flight Risk Advisory]

    A --> B --> C --> D

    E1[CCR check]
    E2[BRS check]
    E3[AGI check]
    E4[URS check]

    A -.-> E1
    B -.-> E1
    C -.-> E2
    C -.-> E3
    D -.-> E3
    A -.-> E4
    B -.-> E4
    C -.-> E4

    F[EES Final Score]
    G[Analyst Decision Package]
    H[Operator Mitigation Advisory]

    E1 --> F
    E2 --> F
    E3 --> F
    E4 --> F
    D --> G --> H
    F --> G

    class A data;
    class B,D llm;
    class C sim;
    class E1,E2,E3,E4 eval;
    class F score;
    class G,H output;
~~~
