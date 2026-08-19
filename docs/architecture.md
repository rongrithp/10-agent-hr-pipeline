```mermaid
flowchart TD
    %% Global Nodes & Triggers
    StartTicket(["🎫 New Hiring Ticket (is0)"]) --> Orch["🛸 Orchestrator"]
    Orch -->|Write Ticket & Gen Spec| GSheet1[("📊 Google Sheets: Main Log")]
    Orch -->|is1_input_spec.txt| A1["🚀 Agent 1: Job Description"]

    %% Phase 1: Planning & Broadcasting
    subgraph Phase1 ["Phase 1: Planning & Sourcing"]
        A1 -->|is1_output_job_description.txt| A2["⚡ Agent 2: Sourcing Strategist"]
        A2 -->|is2_output_sourcing_strategy.json| A3["⚡ Agent 3: Content Broadcaster"]
        A3 -->|is3_output_recruitment_broadcast.json| P1_Pause(["⏸️ Standby: Wait for Resumes"])
    end

    %% Phase 2: Resume Screening & Scheduling
    subgraph Phase2 ["Phase 2: Screening & Interview Setup"]
        P1_Pause -.->|Sensory Input: mock_cv_batch.json| A4["⚡ Agent 4: Resume Screener"]
        A4 -->|is4_output_candidate_scores.json| A5["⚡ Agent 5: Interview Scheduler"]
        A5 -->|is5_output_interview_schedule.json| P2_Pause(["⏸️ Standby: Wait for Interview Notes"])
    end

    %% Phase 3: Evaluation & Autonomous Domino Loop
    subgraph Phase3 ["Phase 3: Autonomous Domino Loop"]
        P2_Pause -.->|Sensory Input: mock_interview_notes.txt| A6["⚡ Agent 6: Interview Evaluator"]
        A6 -->|is6_output_interview_evaluation.json| A7["⚡ Agent 7: Compliance Checker"]
        A7 -->|is7_output_compliance_check.json| A8["⚡ Agent 8: Offer Negotiator"]
        A8 -->|is8_output_offer_details.json| A9["⚡ Agent 9: Onboarding Planner"]
        A9 -->|is9_output_onboarding_plan.json| A10["⚡ Agent 10: Talent Profiler"]
    end

    %% Phase 4: Actuation & Physical Impact
    subgraph Phase4 ["Phase 4: Data Sync & Actuation"]
        A10 -->|is10_output_employee_profile.json| A11["🚀 Agent 11: Database Sync"]
        A11 -->|Append Row| GSheet2[("📊 Google Sheets: Onboarded_Talents")]
        A11 -->|Subprocess Trigger| A12["🚀 Agent 12: Telegram Notify"]
        A12 -->|HTTPS Payload| TelegramBot[("📡 Telegram Server / Channel")]
    end

    TelegramBot --> Complete(["🏁 Pipeline Completed!"])

    %% Styling
    classDef orchestrator fill:#1f2430,stroke:#cbccc6,stroke-width:2px,color:#fff;
    classDef phaseBox fill:#141925,stroke:#4f5b66,stroke-width:1px,color:#d8dee9;
    classDef agent fill:#0d1117,stroke:#58a6ff,stroke-width:2px,color:#58a6ff;
    classDef pauseNode fill:#3b2d18,stroke:#f2994a,stroke-width:1px,color:#f2994a;
    classDef external fill:#1b2838,stroke:#2bb673,stroke-width:2px,color:#2bb673;
    classDef endNode fill:#1a3a2a,stroke:#27ae60,stroke-width:2px,color:#27ae60;

    class Orch orchestrator;
    class A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11,A12 agent;
    class P1_Pause,P2_Pause pauseNode;
    class GSheet1,GSheet2,TelegramBot external;
    class StartTicket,Complete endNode;
    ```