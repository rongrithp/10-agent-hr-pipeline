# 🗺️ 12-Agent Recruitment Process Automation: Epoch Roadmap & Evolution Log

> **Project Version**: 1.0.0 (Epoch 1 Completed)  
> **Repository**: `rongrithp/10-agent-hr-pipeline`  
> **Last Updated**: August 2026  

---

## 📌 1. System Overview & Core Philosophy

### 1.1 Project Objective
ระบบ **12-Agent Recruitment Process Automation** ถูกออกแบบเพื่อแปลงกระบวนการสรรหาและคัดเลือกบุคลากรแบบ End-to-End ให้เป็นระบบอัตโนมัติที่ทำงานร่วมกันอย่างสมบูรณ์แบบ ผ่าน Multi-Agent Architecture จำนวน 13 สคริปต์ (Agent 0 ถึง Agent 12) ครอบคลุม 5 Lifecycles หลัก ตั้งแต่การเปิดรับสมัครงานจนถึงการแจ้งเตือนผู้บริหารรับ Onboarding

### 1.2 The 5 Recruitment Lifecycles Architecture
```mermaid
flowchart LR
    L1["Lifecycle 1: Job Spec & Sourcing\n(Agent 0 - 3)"] --> L23["Lifecycles 2 & 3: Screening & Evaluation\n(Agent 4 - 6)"]
    L23 --> L4["Lifecycle 4: Compliance & Offer\n(Agent 7 - 8)"]
    L4 --> L5["Lifecycle 5: Onboarding & Notification\n(Agent 9 - 12)"]
```

### 1.3 Core Engineering Philosophy & Standards
1. **Dual Output Standard (`.json` + `.md`)**:
   - ทุก Agent จะทำการปล่อย Output 2 รูปแบบเสมอใน Workspace Vault:
     * **Machine-Readable Payload (`.json`)**: สำหรับการส่งต่อข้อมูลระหว่าง Agent ใน Pipeline และบันทึกลง Database
     * **Human-Readable Document (`.md`)**: สำหรับมนุษย์ (HR / Hiring Manager / Executive) อ่าน ตรวจสอบ หรือพิมพ์ออกเป็นเอกสาร
2. **Pydantic Schema Validation & Data Contracts**:
   - ควบคุมโครงสร้างข้อมูลเข้า-ออกของทุก Agent ด้วย Pydantic V2 BaseModels เพื่อสร้าง Data Contracts ที่แข็งแกร่งและป้องกัน Runtime Data Mutation
3. **Workspace Vault Isolation**:
   - การประมวลผลแยกตาม Job Code ในโฟลเดอร์ `workspaces/<JOB-CODE>/` โดยแบ่งเป็น Vault ตามแต่ละ Stage ของ Recruitment Lifecycle (`00_intake_vault/`, `01_job_spec_vault/`, `02_sourcing_dropzone/`, `03_broadcasting_kits/`, `04_candidate_eval_vault/`, `05_onboarding_vault/`)

---

## 🟢 2. Epoch 1: Core Foundation & Data Contracts [COMPLETED]

### 2.1 Overview & Key Milestones
ใน **Epoch 1** ระบบสำเร็จการสร้างรากฐาน Core Pipeline และ Data Contracts ครบถ้วนทั้ง 12 Agents (Agent 0 ถึง Agent 12) และทำการทดสอบ End-to-End Recruitment Cycle พร้อมส่ง Live Broadcast เข้าสู่ Telegram Group ผู้บริหารสำเร็จเรียบร้อย

### 2.2 Agent Summary by Lifecycle

| Lifecycle | Agent ID & Name | Core Responsibility | Primary Output Artifacts | Status |
| :--- | :--- | :--- | :--- | :---: |
| **L1: Job Spec & Sourcing** | **Agent 0**: Telegram Gatekeeper | รับข้อความผ่าน Telegram/CLI เพื่อสร้าง Intake Workspace | `is0_output_job_intake_payload.json`<br>`is0_intake_summary_card.md` | ✅ Completed |
| | **Agent 1**: Job Spec Synthesizer | สังเคราะห์ Job Spec ชัดเจนตามโครงสร้างองค์กร | `is1_output_job_description_payload.json`<br>`is1_job_description_document.md` | ✅ Completed |
| | **Agent 2**: Sourcing Strategist | วางยุทธศาสตร์ค้นหาและกำหนด Channel Matrix | `is2_output_sourcing_strategy_payload.json`<br>`is2_sourcing_strategy_document.md` | ✅ Completed |
| | **Agent 3**: Content Broadcaster | สร้างสื่อประชาสัมพันธ์ตำแหน่งงาน (JobsDB, Social, Email) | `is3_output_broadcasting_content_payload.json`<br>`is3_broadcasting_content_kit.md` | ✅ Completed |
| **L2 & L3: Screening & Evaluation** | **Agent 4**: Resume Screener | คัดกรองและให้คะแนนเรซูเม่เทียบกับ Job Spec | `is4_output_resume_screening_payload.json`<br>`is4_resume_screening_report.md` | ✅ Completed |
| | **Agent 5**: Interview Scheduler | จัดตารางสัมภาษณ์และสร้าง Calendar Invites | `is5_output_interview_schedule_payload.json`<br>`is5_interview_schedule_notice.md` | ✅ Completed |
| | **Agent 6**: Interview Evaluator | ประเมินผลสัมภาษณ์ สรุป Competency Matrix | `is6_output_interview_evaluation_payload.json`<br>`is6_interview_evaluation_report.md` | ✅ Completed |
| **L4: Compliance & Offer** | **Agent 7**: Compliance Checker | ตรวจสอบ Background Check, Reference & Risk Assessment | `is7_output_compliance_check_payload.json`<br>`is7_compliance_check_report.md` | ✅ Completed |
| | **Agent 8**: Offer Negotiator | คำนวณผลตอบแทนและออกร่างสัญญาจ้าง (Offer Letter) | `is8_output_offer_negotiation_payload.json`<br>`is8_offer_letter_document.md` | ✅ Completed |
| **L5: Onboarding & Notification** | **Agent 9**: Onboarding Planner | วางแผนปฐมนิเทศ เตรียม IT Asset & Day-1 Checklist | `is9_output_onboarding_plan_payload.json`<br>`is9_onboarding_plan_document.md` | ✅ Completed |
| | **Agent 10**: Talent Profiler | สรุปโปรไฟล์ผู้สมัครแบบ 360 องศาเพื่อบันทึกคลังผู้มีศักยภาพ | `is10_output_talent_profile_payload.json`<br>`is10_talent_profile_dossier.md` | ✅ Completed |
| | **Agent 11**: Database Sync | บันทึกข้อมูลขึ้น Google Sheets Central DB | `is11_output_database_sync_payload.json`<br>`is11_database_sync_report.md` | ✅ Completed |
| | **Agent 12**: Telegram Notify | สรุปรายงานสุดท้ายและบรอดแคสต์เข้า Telegram Group ผู้บริหาร | `is12_output_notification_payload.json`<br>`is12_telegram_broadcast_card.md` | ✅ Completed |

### 2.3 Critical Technical Challenges & Solutions Solved in Epoch 1
1. **Idempotency Guard Implementation**:
   - ปัญหา: การรัน Pipeline ซ้ำทำให้ไฟล์หรือการ Dispatch Telegram เกิดการส่งข้อความซ้ำซ้อน
   - วิธีแก้ไข: ฝัง Idempotency Check ใน Agent 12 (ตรวจสอบการมีอยู่ของ `is12_output_notification_payload.json`) และระบบ CLI Flag เพื่อควบคุมพฤติกรรม re-run
2. **Telegram Dispatch Encoding & Format Safety**:
   - ปัญหา: Telegram Bot API มีข้อจำกัดสูงเกี่ยวกับการ parse MarkdownV2 (มักล้มเหลวจาก unescaped special characters เช่น `-`, `.`, `!`, `(`, `)`)
   - วิธีแก้ไข: ปรับ Agent 12 ให้ใช้ Plaintext Mode พร้อมกับการจัดเรียง Emoji และ Line Wrapping สวยงาม อ่านง่าย ป้องกัน HTTP 400 Bad Request
3. **Cross-Platform Path Safety & Environment Resilience**:
   - ปัญหา: ปัญหาการอ้างอิง Relative Path ระหว่าง Windows และ POSIX Environments ใน Google Drive Workspace
   - วิธีแก้ไข: ใช้ `pathlib.Path` ใน `config.py` เพื่อทำ Dynamic Path Resolution ให้อ่าน-เขียนไฟล์ใน Vault โฟลเดอร์ได้อย่างถูกต้องเสมอ

---

## 🟢 3. Epoch 2: Platform Integration & Production Inputs [COMPLETED]

### 3.1 Focus & Core Objectives
ยกระดับระบบจาก Prototype Workflow สู่ Production-Grade Operational Pipeline โดยมุ่งเน้นการปฏิรูปความเร็วในการประมวลผล (In-Memory Pipeline), การรองรับข้อมูลจากภายนอกจริง (Real PDF Parser), สื่อประชาสัมพันธ์ 50-field schema สำหรับ JobsDB และอินเทอร์เฟซรับข้อมูล Human-in-the-Loop

```mermaid
gantt
    title Epoch 2 Roadmap Milestones
    dateFormat  YYYY-MM-DD
    section Architecture
    Task 2.1 Refactor Orchestrator to In-Memory     :done, 2026-09-01, 7d
    section Integration
    Task 2.2 Deep Dive Agent 3 JobsDB 50-Field Payload :done, 2026-09-08, 7d
    Task 2.3 Live Resume Parsing PDF Dropzone       :done, 2026-09-15, 7d
    section Human-in-the-Loop
    Task 2.4 Human-in-the-Loop Interview Notes Input :done, 2026-09-22, 7d
```

### 3.2 Key Roadmap Tasks & Deliverables

#### 🎯 Task 2.1: Refactor `main_orchestrator.py` สู่ In-Memory Direct Pipeline [COMPLETED]
- **Problem**: ปัจจุบันการส่งต่อข้อมูลระหว่าง Agent พึ่งพาการเขียนไฟล์และอ่านไฟล์ `.json` กลับขึ้นมาใหม่ ทำให้เกิด I/O Overhead
- **Target Solution**:
  * ปรับปรับ `main_orchestrator.py` ให้อ่าน/เขียน In-Memory Python Objects (Pydantic models) ระหว่าง Agent execution ได้โดยตรง
  * ยังคงรักษาสัญญาณ Async Disk Write สำหรับบันทึก Audit Logs และ Vault Artifacts (`.json` + `.md`) ไว้สำหรับการตรวจสอบย้อนหลัง
- **Status**: ✅ **COMPLETED** (In-Memory Direct Engine Refactored for 13 Agents across 5 Lifecycles)


#### 🎯 Task 2.2: Deep Dive Agent 3 สำหรับ JobsDB 50-Field Payload & แยกโฟลเดอร์ `03_broadcasting_kits/` [COMPLETED]
- **Problem**: การประกาศงานในแพลตฟอร์มหลัก เช่น JobsDB/JobStreet ต้องการ Metadata ละเอียดกว่า 50 ฟิลด์ (เช่น Salary Range Code, Job Function Category Code, Work Location Coordinates, Benefits Flags)
- **Target Solution**:
  * พัฒนา `JobsDB50FieldSchema` ใน Pydantic Schema สำหรับ Agent 3
  * จัดสร้างยูนิตจัดเก็บเฉพาะใน Workspace โฟลเดอร์ `workspaces/<JOB-CODE>/03_broadcasting_kits/` แยกประเภท Channel เช่น JobsDB JSON Payload, LinkedIn Banner Copy, Facebook Post, และ Email Notification Templates
- **Status**: ✅ **COMPLETED** (JobsDB 50-Field Schema & Multi-channel Broadcasting Kits Delivered)


#### 🎯 Task 2.3: Live Resume Parsing (PDF Dropzone in `02_sourcing_dropzone/`) [COMPLETED]
- **Problem**: ปัจจุบัน Resume Screening ใช้ Mock Candidate Payload
- **Target Solution**:
  * พัฒนา PDF Parsing Pipeline ด้วย PyPDF / pdfplumber ร่วมกับ Gemini Structured Output ใน Agent 4
  * กำหนด Dropzone โฟลเดอร์ `workspaces/<JOB-CODE>/02_sourcing_dropzone/` สำหรับการวางไฟล์ PDF Resume หลายไฟล์พร้อมกัน และทำการรัน Batch Screening สรุปเป็น Candidate Scorecard Matrix
- **Status**: ✅ **COMPLETED** (Live PDF Resume Batch Extractor & Candidate Matrix Engine Delivered)


#### 🎯 Task 2.4: Human-in-the-Loop Feedback Interface (Interview Notes Input) [COMPLETED]
- **Problem**: ผลการสัมภาษณ์งานจริงต้องรับมาจากบทสนทนาและบันทึกของกรรมการ (Interviewer Notes)
- **Target Solution**:
  * สร้าง CLI / Form Interface หรือ Webhook สั้นๆ รับ Raw Text / Audio Transcript จากกรรมการสัมภาษณ์บันทึกลงใน `.interview/` โฟลเดอร์
  * ให้ Agent 6 (Interview Evaluator) ทำการสกัด (Extract) คะแนน และ Competency Assessment จากบันทึกจริงเพื่อลงคะแนนตัดสินใจ Hiring Decision
- **Status**: ✅ **COMPLETED** (Human-in-the-Loop Interview Feedback Engine Delivered)

---

## 🔵 4. Epoch 3: Enterprise Hardening & Operational Resilience [FUTURE BACKLOG]

### 4.1 Vision & Long-term Goals
ยกระดับสู่ระบบ **Enterprise-Grade High-Reliability HR Agent Network** โดยเน้นความเสถียรและความทนทานต่อความผิดพลาด (Fault Tolerance), การป้องกันข้อมูลเสียหาย, การค้นหาข้อมูลเชิงความหมายใน Talent Pool และการรองรับการประมวลผลตำแหน่งงานหลายตำแหน่งพร้อมกัน (Concurrent Pipelines)

> [!IMPORTANT]
> **Architectural Decision Record (ADR-001: Human-as-the-Bridge for Broadcasting Kits)**
> - **Context**: เดิมวางแผนใช้ Headless Browser Automation (Playwright) เพื่ออัปโหลดประกาศงานไปยัง JobsDB, LinkedIn, และ JobStreet อัตโนมัติ
> - **Decision**: ตัดระบบ Playwright Automation ออก และใช้สถาปัตยกรรม **"Human-as-the-Bridge"** ร่วมกับ Broadcasting Kits ที่จัดเตรียมไว้ใน `03_broadcasting_kits/`
> - **Rationale**:
>   1. **System Reliability > 95%**: การพึ่งพา Web Automation เสี่ยงต่อความล้มเหลวสูงจาก DOM Mutation, Anti-bot Bot Detection, Cloudflare Captcha และ Account Ban
>   2. **Zero Overhead Maintenance**: ลดภาระงานรักษา Script เมื่อแพลตฟอร์มปรับปรุง UI
>   3. **Human Control & Audit**: ให้ HR Review สื่อและปรับแต่งแคปชันก่อนกดเผยแพร่จริง

---

### 4.2 Key Roadmap Tasks & Deliverables

#### 🎯 Task 3.1: API Network Resilience & Exponential Backoff Retries [COMPLETED]
- **Problem**: การเรียก API ภายนอก (Gemini API, Telegram Bot API, Google Sheets API) อาจล้มเหลวจาก Transient Network Error หรือ Rate Limiting (HTTP 429 / 503)
- **Target Solution**:
  * เพิ่ม Decorator `@retry_with_backoff` สำหรับการเรียก API ทั้งหมดใน Agent 0 ถึง 12
  * รองรับ Exponential Backoff with Jitter เพื่อความเสถียรระดับ Enterprise
- **Status**: ✅ **COMPLETED** (`engine/resilience.py` module delivered with Exponential Backoff & Jitter retries)


#### 🎯 Task 3.2: Malformed & Encrypted PDF Isolation Guard (Agent 4) [COMPLETED]
- **Problem**: ไฟล์ PDF ใน `02_sourcing_dropzone/` ที่ติดรหัสผ่าน (Encrypted PDF), ไฟล์ชำรุด (Corrupted PDF) หรือสแกนภาพ (Image-only Scanned PDF) อาจทำให้ PDF Extractor ค้างหรือ Crash
- **Target Solution**:
  * เพิ่ม PDF Health Pre-checker ใน Agent 4 เพื่อแยกไฟล์ที่มีปัญหาไปไว้ที่ `02_sourcing_dropzone/.quarantine/`
  * ออกรายงานแจ้งเตือน HR พร้อมรันประมวลผลไฟล์ PDF ที่เหลือได้โดยไม่หยุดชะงัก
- **Status**: ✅ **COMPLETED** (Pre-flight PDF Health Guard & `.quarantine/` Isolation Delivered)


#### 🎯 Task 3.3: Vector Talent Search & Candidate Memory (Local Semantic Retrieval) [COMPLETED]
- **Problem**: ข้อมูลผู้สมัครในอดีต (Agent 10 Talent Dossiers) ไม่สามารถค้นหาเชิงความหมาย (Semantic Search) ได้
- **Target Solution**:
  * สร้าง Local Vector Embeddings (ChromaDB / FAISS / Gemini Embeddings) สำหรับจัดเก็บ Talent Dossiers
  * เพิ่ม Semantic Search Interface ให้ HR ค้นหาผู้สมัครเก่าใน Talent Pool ตามทักษะ หรือโปรไฟล์ความตรงได้อย่างรวดเร็ว
- **Status**: ✅ **COMPLETED** (`engine/talent_memory.py` Central Talent Store & Search Engine Delivered)


#### 🎯 Task 3.4: Multi-Role Concurrent Orchestration
- **Problem**: ปัจจุบัน Orchestrator รองรับการรันทีละ Job Ticket
- **Target Solution**:
  * อัปเกรด `main_orchestrator.py` ให้รองรับ Parallel/Async IO Executions สำหรับประมวลผลหลายตำแหน่งงานพร้อมกัน (Multi-Job Tickets) ด้วย Python `asyncio` / ThreadPoolExecutor

---

## 📅 Roadmap Execution Summary Matrix

| Epoch | Objective | Primary Deliverables | Target Timeline | Status |
| :---: | :--- | :--- | :---: | :---: |
| **Epoch 1** | Core Foundation & Data Contracts | 12-Agent Pipeline, Dual Output (.json/.md), Schema Validation, Telegram Live Dispatch | Q3 2026 | ✅ **COMPLETED** |
| **Epoch 2** | Platform Integration & Production Inputs | In-Memory Orchestrator, JobsDB 50-field Schema, PDF Resume Dropzone, Human-in-the-Loop Notes | Q4 2026 | ✅ **COMPLETED** |
| **Epoch 3** | Enterprise Hardening & Operational Resilience | API Backoff Retries, PDF Quarantine Guard, Vector Talent Search, Multi-Role Parallel Pipeline | Q1 2027 | 🔵 **FUTURE** |


