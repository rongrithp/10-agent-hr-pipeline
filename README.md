# 🤖 10-Agent HR Autonomous Recruitment Pipeline

ระบบ Automation สำหรับกระบวนการสรรหาและบรรจุบุคลากร (Recruitment & Onboarding Lifecycle) ขับเคลื่อนด้วย Multi-Agent System (Gemini API) ทำงานประสานกันแบบ End-to-End ตั้งแต่เปิดใบงานผ่าน Telegram, จัดการเอกสาร, คัดกรองสัมภาษณ์, ประเมินผล ไปจนถึง Onboarding และ Sync ผลลัพธ์ขึ้น Google Sheets แบบ Real-time

---

## 🏛️ System Architecture & Workflow

ระบบแบ่งการทำงานออกเป็น 13 โมดูลย่อย (Agent 0 - 12) ผ่านการควบคุมของ `main_orchestrator.py`:

```text
[Telegram Chat] 
       │
       ▼
[Agent 0: Telegram Gatekeeper] ────► บันทึกใบงานลง Google Sheets (Job_Tracker: Col A-N)
       │
       ▼
[main_orchestrator.py] ──────────► ขับเคลื่อน Pipeline ผ่าน 5 Lifecycles
       ├─► Agent 1: Job Description Generator (สร้าง JD ตามสเปกลูกค้า)
       ├─► Agent 2: Sourcing Strategist (วางกลยุทธ์ช่องทางการหาคน)
       ├─► Agent 3: Content Broadcaster (เขียน Copywriting สำหรับยิงประกาศ)
       ├─► Agent 4: Resume Screener (คัดกรองเรซูเม่และให้คะแนนเทียบ JD)
       ├─► Agent 5: Interview Scheduler (วางตารางและคำถามสัมภาษณ์เฉพาะตำแหน่ง)
       ├─► Agent 6: Interview Evaluator (ประเมินคะแนนจากการสัมภาษณ์จริง)
       ├─► Agent 7: Compliance & Reference Checker (ตรวจสอบประวัติและคุณสมบัติ)
       ├─► Agent 8: Offer Negotiator (จัดทำแพ็กเกจข้อเสนอและสัญญาจ้าง)
       ├─► Agent 9: Onboarding Planner (วางแผนปฐมนิเทศและการรับเข้าทำงาน)
       └─► Agent 10: Talent Profiler (จัดทำโปรไฟล์พนักงานและ Vault บุคลากร)
       │
       ▼
[Agent 11: Database Sync] ────────► Sync ข้อมูลลง Onboarded_Talents (Col A-N) & ปิด Job_Tracker
       │
       ▼
[Agent 12: Telegram Notify] ──────► แจ้งเตือนสรุปผลสำเร็จปิดงานเข้ากลุ่ม Telegram
```
