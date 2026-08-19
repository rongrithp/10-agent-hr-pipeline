# 🏗️ System Architecture & Process Flow: HR Recruitment Autonomous Pipeline

เอกสารนี้อธิบายสถาปัตยกรรมระบบ (System Architecture) และลำดับกระบวนการทำงาน (Process Flow Diagram) ของระบบ **Harrow Recruitment Process Automation** ตั้งแต่จุดเริ่มต้นการรับเรื่องผ่าน Telegram Bot (`Agent 0`) การรันระบบ Orchestration ไปจนถึงการประมวลผลด้วย Agent ทั้ง 12 ตัว สรุปผลลง Google Sheets และส่งแจ้งเตือนสุดท้ายกลับไปยัง Telegram (`Agent 12`)

---

## 📊 1. Process Block Diagram (Mermaid Flowchart)

```mermaid
flowchart TD
    %% Custom Styling
    classDef external fill:#2b2d42,stroke:#8d99ae,stroke-width:2px,color:#fff
    classDef trigger fill:#d90429,stroke:#ef233c,stroke-width:2px,color:#fff
    classDef orchestrator fill:#7209b7,stroke:#f72585,stroke-width:2px,color:#fff
    classDef agentPhase1 fill:#0077b6,stroke:#00b4d8,stroke-width:2px,color:#fff
    classDef agentPhase2 fill:#38b000,stroke:#70e000,stroke-width:2px,color:#fff
    classDef agentPhase3 fill:#f77f00,stroke:#fcbf49,stroke-width:2px,color:#fff
    classDef pause fill:#6c757d,stroke:#adb5bd,stroke-width:2px,color:#fff,stroke-dasharray: 5 5

    %% External Systems & Users
    User(("👤 HR / User"))
    TelegramAPI["💬 Telegram Bot API"]
    SheetsAPI["📊 Google Sheets API"]
    GeminiAPI["🧠 Google Gemini 2.5 Flash"]

    %% Phase 0: Entry Point & Orchestration
    subgraph Phase0 ["Phase 0: Entry Point & Job Ticket Creation"]
        A0["🤖 Agent 0: Telegram Gatekeeper<br/>(agent_0_telegram_gatekeeper.py)"]
        IS0[("📄 specs/is0_job_ticket.json")]
        ORCH["🛸 Main Orchestrator<br/>(main_orchestrator.py)"]
        IS1_IN[("📄 specs/is1_input_spec.txt")]
    end

    %% Phase 1: Spec & Sourcing Strategy Setup
    subgraph Phase1 ["Phase 1: Spec & Sourcing Strategy (Auto Domino)"]
        A1["🤖 Agent 1: Job Description Generator<br/>(agent_1_job_description.py)"]
        IS1_OUT[("📄 specs/is1_output_job_description.txt")]
        
        A2["🤖 Agent 2: Sourcing Strategist<br/>(agent_2_sourcing_strategist.py)"]
        IS2_OUT[("📄 specs/is2_output_sourcing_strategy.json")]
        
        A3["🤖 Agent 3: Content Broadcaster<br/>(agent_3_content_broadcaster.py)"]
        IS3_OUT[("📄 specs/is3_output_job_postings.json")]
    end

    %% Pause Gate 1
    P1{{"⏸️ PAUSE: Wait for Resumes<br/>(cv_dropzone/mock_cv_batch.json)"}}

    %% Phase 2: Screening & Interview Setup
    subgraph Phase2 ["Phase 2: Resume Screening & Interview Setup"]
        A4["🤖 Agent 4: Resume Screener<br/>(agent_4_resume_screener.py)"]
        IS4_OUT[("📄 results/is4_output_candidate_scores.json")]
        
        A5["🤖 Agent 5: Interview Scheduler<br/>(agent_5_interview_scheduler.py)"]
        IS5_OUT[("📄 results/is5_output_interview_schedule.json")]
    end

    %% Pause Gate 2
    P2{{"⏸️ PAUSE: Wait for Interview Notes<br/>(cv_dropzone/mock_interview_notes.txt)"}}

    %% Phase 3: Evaluation, Offer, Onboarding & Database Sync
    subgraph Phase3 ["Phase 3: Evaluation, Offer, Onboarding & Sync (Auto Domino)"]
        A6["🤖 Agent 6: Interview Evaluator<br/>(agent_6_interview_evaluator.py)"]
        IS6_OUT[("📄 results/is6_output_interview_evaluation.json")]
        
        A7["🤖 Agent 7: Compliance Checker<br/>(agent_7_compliance_checker.py)"]
        IS7_OUT[("📄 results/is7_output_compliance_check.json")]
        
        A8["🤖 Agent 8: Offer Negotiator<br/>(agent_8_offer_negotiator.py)"]
        IS8_OUT[("📄 results/is8_output_offer_details.json")]
        
        A9["🤖 Agent 9: Onboarding Planner<br/>(agent_9_onboarding_planner.py)"]
        IS9_OUT[("📄 results/is9_output_onboarding_plan.json")]
        
        A10["🤖 Agent 10: Talent Profiler<br/>(agent_10_talent_profiler.py)"]
        IS10_OUT[("📄 results/is10_output_employee_profile.json")]
        
        A11["🤖 Agent 11: Database Sync<br/>(agent_11_database_sync.py)"]
        
        A12["🤖 Agent 12: Telegram Notify<br/>(agent_12_telegram_notify.py)"]
    end

    %% Flow Connections (Domino Triggers & Data Exchange)
    User <-->|"1. Chat / Command"| TelegramAPI
    TelegramAPI <-->|"2. Long Polling"| A0
    A0 <-->|"3. Conversational AI"| GeminiAPI
    A0 -->|"4. Save Job Ticket"| IS0
    A0 -->|"5. Domino Trigger (subprocess)"| ORCH
    
    ORCH -->|"6. Log Job Ticket"| SheetsAPI
    ORCH -->|"7. Read Ticket"| IS0
    ORCH -->|"8. Write Spec"| IS1_IN
    ORCH -->|"9. Domino Trigger (subprocess)"| A1

    %% Phase 1 Domino
    IS1_IN --> A1
    A1 <-->|"LLM Call"| GeminiAPI
    A1 --> IS1_OUT
    A1 -->|"10. Domino Trigger"| A2

    IS1_OUT --> A2
    A2 <-->|"LLM Call (Structured JSON)"| GeminiAPI
    A2 --> IS2_OUT
    A2 -->|"11. Domino Trigger"| A3

    IS2_OUT --> A3
    A3 <-->|"LLM Call (Structured JSON)"| GeminiAPI
    A3 --> IS3_OUT
    A3 --> P1

    %% Phase 2
    P1 --> A4
    IS1_OUT --> A4
    A4 <-->|"LLM Call"| GeminiAPI
    A4 --> IS4_OUT

    IS4_OUT --> A5
    A5 <-->|"LLM Call"| GeminiAPI
    A5 --> IS5_OUT
    A5 --> P2

    %% Phase 3 Domino
    P2 --> A6
    IS1_OUT --> A6
    A6 <-->|"LLM Call"| GeminiAPI
    A6 --> IS6_OUT
    A6 -->|"12. Domino Trigger"| A7

    IS6_OUT --> A7
    A7 <-->|"LLM Call"| GeminiAPI
    A7 --> IS7_OUT
    A7 -->|"13. Domino Trigger"| A8

    IS7_OUT --> A8
    IS1_OUT --> A8
    A8 <-->|"LLM Call"| GeminiAPI
    A8 --> IS8_OUT
    A8 -->|"14. Domino Trigger"| A9

    IS8_OUT --> A9
    A9 <-->|"LLM Call"| GeminiAPI
    A9 --> IS9_OUT
    A9 -->|"15. Domino Trigger"| A10

    IS9_OUT --> A10
    A10 <-->|"LLM Call"| GeminiAPI
    A10 --> IS10_OUT
    A10 -->|"16. Domino Trigger"| A11

    IS10_OUT --> A11
    A11 -->|"17. Append Row ('Onboarded_Talents')"| SheetsAPI
    A11 -->|"18. Domino Trigger"| A12

    IS10_OUT --> A12
    A12 -->|"19. Send Final Notification"| TelegramAPI
    TelegramAPI -->|"20. Notify Completed Pipeline"| User

    %% Class Assignments
    class TelegramAPI,SheetsAPI,GeminiAPI external
    class A0 trigger
    class ORCH orchestrator
    class A1,A2,A3 agentPhase1
    class A4,A5 agentPhase2
    class A6,A7,A8,A9,A10,A11,A12 agentPhase3
    class P1,P2 pause
```

---

## 🔄 2. Sequence Diagram (End-to-End Domino Lifecycle)

```mermaid
sequenceDiagram
    autonumber
    actor User as HR / User
    participant A0 as Agent 0 (Gatekeeper)
    participant Orch as Main Orchestrator
    participant A1_3 as Agents 1-3 (Phase 1)
    participant A4_5 as Agents 4-5 (Phase 2)
    participant A6_10 as Agents 6-10 (Phase 3)
    participant A11 as Agent 11 (DB Sync)
    participant A12 as Agent 12 (Telegram Notify)
    participant Ext as External APIs (Gemini/Sheets/Telegram)

    User->>A0: พิมพ์ความต้องการรับสมัครงาน (Client, Position, Budget, Timeline)
    A0->>Ext: (Gemini AI) คุยโต้ตอบ & สกัดข้อมูลลง JSON
    A0->>User: สรุปข้อมูล & ส่งปุ่ม [✅ ยืนยัน]
    User->>A0: กดปุ่ม [✅ ยืนยัน]
    A0->>A0: บันทึก specs/is0_job_ticket.json
    A0->>Orch: subprocess.Popen (ปลุก Main Orchestrator)
    
    Orch->>Ext: (Google Sheets API) บันทึกใบงานลงชี้ต Job_Tracker
    Orch->>Orch: สร้าง specs/is1_input_spec.txt
    Orch->>A1_3: subprocess.Popen (ปลุก Agent 1)

    Note over A1_3: Domino Loop Phase 1<br/>Agent 1 ➔ Agent 2 ➔ Agent 3
    A1_3->>Ext: (Gemini AI) ร่าง JD, วางกลยุทธ์ สรรหา และร่างประกาศ
    A1_3->>A1_3: บันทึก is1_output_job_description, is2_output_sourcing_strategy, is3_output_job_postings
    Note over A1_3: ⏸️ หยุดรอ CV ใน cv_dropzone/mock_cv_batch.json

    Note over A4_5: Phase 2: CV Screening & Schedule
    A4_5->>Ext: (Gemini AI) คัดกรอง CV & ร่างอีเมลสัมภาษณ์
    A4_5->>A4_5: บันทึก is4_output_candidate_scores, is5_output_interview_schedule
    Note over A4_5: ⏸️ หยุดรอ Note สัมภาษณ์ใน cv_dropzone/mock_interview_notes.txt

    Note over A6_10: Domino Loop Phase 3<br/>Agent 6 ➔ 7 ➔ 8 ➔ 9 ➔ 10
    A6_10->>Ext: (Gemini AI) ประเมินผลสัมภาษณ์, ตรวจเอกสาร, Offer, Onboarding, Talent Profile
    A6_10->>A6_10: บันทึก is6_output ถึง is10_output
    A6_10->>A11: subprocess.Popen (ปลุก Agent 11)

    A11->>Ext: (Google Sheets API) เพิ่มแถวพนักงานใหม่ลงแท็บ 'Onboarded_Talents'
    A11->>A12: subprocess.Popen (ปลุก Agent 12)

    A12->>Ext: (Telegram Bot API) ส่งข้อความแจ้งเตือนจบกระบวนการ
    Ext->>User: แจ้งเตือน 🏁 Pipeline Completed บน Telegram
```

---

## 📋 3. ตารางรายละเอียดของแต่ละ Module & Agent

| Stage / Module | ไฟล์ Python | ไฟล์ Input (อ่านจาก) | ไฟล์ Output (เขียนลง) | การเรียกใช้ External API / Library | กลไกการส่งไม้ผลัด (Domino Mechanism) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent 0** | `agent_0_telegram_gatekeeper.py` | Telegram Messages (Interactive) | `specs/is0_job_ticket.json` | Telegram Bot API (`telebot`), Google Gemini (`gemini-2.5-flash`) | เรียก `main_orchestrator.py` ผ่าน `subprocess.Popen` หลังกด [✅ ยืนยัน] |
| **Orchestrator** | `main_orchestrator.py` | `specs/is0_job_ticket.json` | `specs/is1_input_spec.txt`, Google Sheet Row | Google Sheets API (`googleapiclient`) | เรียก `agent_1_job_description.py` ผ่าน `subprocess.Popen` |
| **Agent 1** | `agent_1_job_description.py` | `specs/is1_input_spec.txt` | `specs/is1_output_job_description.txt` | Google Gemini (`gemini-2.5-flash`) | เรียก `agent_2_sourcing_strategist.py` ผ่าน `subprocess.Popen` |
| **Agent 2** | `agent_2_sourcing_strategist.py` | `specs/is1_output_job_description.txt` | `specs/is2_output_sourcing_strategy.json` | Google Gemini (`google.genai`, Pydantic Schema) | เรียก `agent_3_content_broadcaster.py` ผ่าน `subprocess.Popen` |
| **Agent 3** | `agent_3_content_broadcaster.py` | `specs/is2_output_sourcing_strategy.json` | `specs/is3_output_job_postings.json` | Google Gemini (`google.genai`, Pydantic Schema) | **PAUSE** (หยุดรอเรซูเม่หย่อนลง `cv_dropzone/mock_cv_batch.json`) |
| **Agent 4** | `agent_4_resume_screener.py` | `specs/is1_output_job_description.txt`, `cv_dropzone/mock_cv_batch.json` | `results/is4_output_candidate_scores.json` | Google Gemini (`google.genai`, Pydantic Schema) | คายผลลัพธ์ลง `results/` (รันอิสระเมื่อมี CV) |
| **Agent 5** | `agent_5_interview_scheduler.py` | `results/is4_output_candidate_scores.json` | `results/is5_output_interview_schedule.json` | Google Gemini (`google.genai`, Pydantic Schema) | **PAUSE** (หยุดรอผลสัมภาษณ์หย่อนลง `cv_dropzone/mock_interview_notes.txt`) |
| **Agent 6** | `agent_6_interview_evaluator.py` | `specs/is1_output_job_description.txt`, `cv_dropzone/mock_interview_notes.txt` | `results/is6_output_interview_evaluation.json` | Google Gemini (`google.genai`, Pydantic Schema) | เรียก `agent_7_compliance_checker.py` ผ่าน `subprocess.Popen` |
| **Agent 7** | `agent_7_compliance_checker.py` | `results/is6_output_interview_evaluation.json`, `cv_dropzone/mock_documents.txt` | `results/is7_output_compliance_check.json` | Google Gemini (`google.genai`, Pydantic Schema) | เรียก `agent_8_offer_negotiator.py` ผ่าน `subprocess.Popen` |
| **Agent 8** | `agent_8_offer_negotiator.py` | `results/is7_output_compliance_check.json`, `specs/is1_output_job_description.txt`, `cv_dropzone/mock_cv_batch.json` | `results/is8_output_offer_details.json` | Google Gemini (`google.genai`, Pydantic Schema) | เรียก `agent_9_onboarding_planner.py` ผ่าน `subprocess.Popen` |
| **Agent 9** | `agent_9_onboarding_planner.py` | `results/is8_output_offer_details.json` | `results/is9_output_onboarding_plan.json` | Google Gemini (`google.genai`, Pydantic Schema) | เรียก `agent_10_talent_profiler.py` ผ่าน `subprocess.Popen` |
| **Agent 10** | `agent_10_talent_profiler.py` | `results/is9_output_onboarding_plan.json`, `cv_dropzone/mock_cv_batch.json`, `cv_dropzone/mock_interview_notes.txt` | `results/is10_output_employee_profile.json` | Google Gemini (`google.genai`, Pydantic Schema) | เรียก `agent_11_database_sync.py` ผ่าน `subprocess.Popen` |
| **Agent 11** | `agent_11_database_sync.py` | `results/is10_output_employee_profile.json` | Google Sheet Tab `Onboarded_Talents` | Google Sheets & Drive API (`gspread`, Service Account) | เรียก `agent_12_telegram_notify.py` ผ่าน `subprocess.Popen` |
| **Agent 12** | `agent_12_telegram_notify.py` | `results/is10_output_employee_profile.json` | Telegram Chat Notification | Telegram Bot API (`requests` HTTPS POST) | **FINISH** (จบกระบวนการ Pipeline) |

---

## 📁 4. โครงสร้างไดเรกทอรีของแต่ละ Workspace (`config.get_workspace(job_id)`)

เมื่อมี Job ID ใหม่เกิดขึ้น ระบบจะสร้างและแยกเก็บไฟล์ทั้งหมดไว้ใน Workspace เฉพาะตามโครงสร้างดังนี้:

```text
workspaces/
└── {JOB_ID}/                             # เช่น JOB-20260818-59
    ├── specs/                            # เก็บข้อมูลข้อกำหนดและกลยุทธ์ (Stage 0 - 3)
    │   ├── is0_job_ticket.json
    │   ├── is1_input_spec.txt
    │   ├── is1_output_job_description.txt
    │   ├── is2_output_sourcing_strategy.json
    │   └── is3_output_job_postings.json
    ├── cv_dropzone/                      # จุดรับไฟล์จากภายนอก (Drop Zone)
    │   ├── mock_cv_batch.json
    │   ├── mock_interview_notes.txt
    │   └── mock_documents.txt
    └── results/                          # เก็บผลการประเมินและการประมวลผล (Stage 4 - 10)
        ├── is4_output_candidate_scores.json
        ├── is5_output_interview_schedule.json
        ├── is6_output_interview_evaluation.json
        ├── is7_output_compliance_check.json
        ├── is8_output_offer_details.json
        ├── is9_output_onboarding_plan.json
        └── is10_output_employee_profile.json
```

---

## 🛡️ 5. สรุปจุดเชื่อมต่อ External API & Credentials

1. **Telegram Bot API**:
   - **Agent 0**: ใช้ `telebot` (`TELEGRAM_BOT_TOKEN`) รับฟังคำสั่งและโต้ตอบ
   - **Agent 12**: ใช้ `requests` ยิง HTTPS POST ตรงไปยัง `https://api.telegram.org/bot<TOKEN>/sendMessage` เพื่อแจ้งเตือน `TELEGRAM_CHAT_ID`

2. **Google Gemini API (Gemini 2.5 Flash)**:
   - ใช้ `GEMINI_API_KEY` จาก `.env`
   - Agent 0 & Agent 1: ใช้ `google.generativeai` / `genai.GenerativeModel`
   - Agent 2 - Agent 10: ใช้ SDK ใหม่ `google.genai.Client` ร่วมกับ Pydantic Structured Output Schemas (`response_mime_type="application/json"`)

3. **Google Sheets API**:
   - **Main Orchestrator**: ใช้ OAuth User Credentials (`token_sheets.json` / `credentials_gmail.json`) อัปเดตลงชี้ตแท็บ `Job_Tracker`
   - **Agent 11**: ใช้ Service Account Credentials (`gcp_credentials.json`) ผ่าน `gspread` อัปเดตลงชี้ตแท็บ `Onboarded_Talents`
