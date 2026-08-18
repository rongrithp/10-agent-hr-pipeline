```mermaid
graph TD
    Trigger((New Hiring Request)) --> A1[Agent 1: Requirement Analyzer]
    A1 -->|is1_job_description.json| A2[Agent 2: Sourcing Strategist]
    A2 -->|is2_sourcing_plan.json| A3[Agent 3: Content Broadcaster]
    A3 -->|is3_job_postings.json| A4[Agent 4: Resume Screener]
    A4 -->|is4_shortlisted.json| A5[Agent 5: Interview Scheduler]
    A5 -->|is5_interview_prep.json| A6[Agent 6: Interview Evaluator]
    A6 -->|is6_evaluation.json| A7[Agent 7: Compliance Checker]
    A7 -->|is7_verification.json| A8[Agent 8: Offer Negotiator]
    A8 -->|is8_offer_letter.json| A9[Agent 9: Onboarding Planner]
    A9 -->|is9_onboarding_plan.json| A10[Agent 10: Talent Profiler]
    A10 --> EndGoal((Employee Profile Completed))
    
    classDef agent fill:#0d1117,stroke:#58a6ff,stroke-width:2px,color:#c9d1d9;
    class A1,A2,A3,A4,A5,A6,A7,A8,A9,A10 agent;