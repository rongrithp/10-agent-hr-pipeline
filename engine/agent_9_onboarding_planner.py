import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Path registration
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config
from engine.resilience import generate_content_with_retry


if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ [Agent 9] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Corporate-Grade Onboarding & 30-60-90 Day Roadmap ---

class PreArrivalChecklist(BaseModel):
    it_assets_assigned: str = Field(description="อุปกรณ์และเครื่องมือ IT ที่จัดเตรียมให้ (เช่น MacBook Pro, Dual Monitors)")
    work_email_format: str = Field(description="อีเมลองค์กรที่สร้างขึ้นใหม่")
    system_access_permissions: List[str] = Field(description="สิทธิ์การเข้าถึงระบบต่าง ๆ (AWS, GitHub, Jira, Student DB)")
    workplace_setup: str = Field(description="รายละเอียดการเตรียมโต๊ะทำงานหรือสถานที่ทำงาน")


class DayOneAgendaItem(BaseModel):
    time_slot: str = Field(description="ช่วงเวลา (เช่น 08:30 - 09:30)")
    activity: str = Field(description="กิจกรรมต้อนรับ/ปฐมนิเทศ")
    host_or_responsible_person: str = Field(description="ผู้รับผิดชอบหรือวิทยากร")
    location_or_link: str = Field(description="สถานที่หรือลิงก์เข้าประชุม")


class ProbationRoadmapPhase(BaseModel):
    phase_name: str = Field(description="ชื่อระยะของ Roadmap (เช่น Days 1 - 30: Learn & Absorb)")
    objective: str = Field(description="เป้าหมายยุทธศาสตร์ของระยะนี้")
    key_deliverables: List[str] = Field(description="รายการผลงาน/หมุดหมายสำคัญที่ต้องบรรลุ")
    success_kpis: str = Field(description="เกณฑ์ประเมินความสำเร็จและ KPIs")


class ProbationRoadmap306090(BaseModel):
    days_1_30: ProbationRoadmapPhase = Field(description="ระยะที่ 1 (1-30 วัน): เรียนรู้งานและระบบ (Learn & Absorb)")
    days_31_60: ProbationRoadmapPhase = Field(description="ระยะที่ 2 (31-60 วัน): เริ่มลงมือปฏิบัติงานจริง (Execute & Deliver)")
    days_61_90: ProbationRoadmapPhase = Field(description="ระยะที่ 3 (61-90 วัน): ทำงานอย่างเป็นอิสระและวัดผล (Autonomy & KPI Evaluation)")


class BuddyAndMentorAssignment(BaseModel):
    onboarding_buddy: str = Field(description="ชื่อและตำแหน่งของพี่เลี้ยง (Onboarding Buddy)")
    buddy_responsibilities: str = Field(description="บทบาทหน้าที่ของพี่เลี้ยงในการช่วยเหลือประจำวัน")
    assigned_mentor: str = Field(description="ชื่อและตำแหน่งของที่ปรึกษา (Assigned Mentor)")
    mentor_responsibilities: str = Field(description="บทบาทหน้าที่ของที่ปรึกษาด้านยุทธศาสตร์และการเติบโต")


class OnboardingPlanPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    employee_id: str = Field(description="รหัสพนักงาน")
    employee_name: str = Field(description="ชื่อ-นามสกุล พนักงานใหม่")
    start_date: str = Field(description="วันที่เริ่มงานจริง")
    department: str = Field(default="Technology & AI Innovation Department", description="แผนกที่สังกัด")
    pre_arrival_checklist: PreArrivalChecklist = Field(description="1. รายการเตรียมความพร้อมก่อนวันเริ่มงาน (Pre-Arrival Checklist)")
    day_1_agenda: List[DayOneAgendaItem] = Field(description="2. ตารางกิจกรรมวันแรก (Day-1 Welcoming Agenda)")
    probation_roadmap_30_60_90: ProbationRoadmap306090 = Field(description="3. แผนพัฒนาช่วงทดลองงาน 30-60-90 วัน")
    buddy_and_mentor_assignment: BuddyAndMentorAssignment = Field(description="4. การมอบหมายพี่เลี้ยงและที่ปรึกษา")
    welcome_message_draft: str = Field(description="ร่างข้อความต้อนรับแนะนำตัวพนักงานใหม่ฉบับบริษัท")


def format_formal_markdown(payload: OnboardingPlanPayload) -> str:
    """แปลงแผน Onboarding เป็นเอกสาร Markdown Formal Roadmap สวยงามระดับ Executive Guide"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    pre = payload.pre_arrival_checklist
    rd = payload.probation_roadmap_30_60_90
    bm = payload.buddy_and_mentor_assignment

    access_str = ", ".join(pre.system_access_permissions)

    agenda_rows = "\n".join([
        f"| **{ag.time_slot}** | {ag.activity} | {ag.host_or_responsible_person} | {ag.location_or_link} |"
        for ag in payload.day_1_agenda
    ])

    deliv_1_30 = "\n".join([f"  - 📌 {d}" for d in rd.days_1_30.key_deliverables])
    deliv_31_60 = "\n".join([f"  - 📌 {d}" for d in rd.days_31_60.key_deliverables])
    deliv_61_90 = "\n".join([f"  - 📌 {d}" for d in rd.days_61_90.key_deliverables])

    return f"""# 🚀 CORPORATE ONBOARDING & 30-60-90 DAY PROBATION ROADMAP

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment & Talent Management  
> **Job Ticket ID:** `{payload.job_id}`  
> **New Employee:** **{payload.employee_name}** (`{payload.employee_id}`)  
> **Target Position:** **{payload.position_title}**  
> **Department:** {payload.department}  
> **Start Date:** **{payload.start_date}**  
> **Document Status:** Formal Onboarding Guide  

---

## 📈 Executive Welcome & Overview

Dear **{payload.employee_name}**,

Welcome to Harrow International School! We are thrilled to have you join our team as **{payload.position_title}**. This comprehensive Onboarding & Probation Roadmap is designed to ensure a smooth transition, set clear expectations, and empower you to succeed in your new role.

> **Welcome Message:**  
> {payload.welcome_message_draft}

---

## 🛠️ 1. Pre-Arrival IT & Workspace Preparation Checklist

| Category | Provisioning Details |
| :--- | :--- |
| **Work Email Created** | `{pre.work_email_format}` |
| **IT Hardware Assigned** | {pre.it_assets_assigned} |
| **System & Cloud Access** | {access_str} |
| **Workplace Location** | {pre.workplace_setup} |

---

## 📅 2. Day-1 Orientation & Welcoming Agenda

| Time Slot | Activity Description | Responsible Host / Facilitator | Venue / Location |
| :---: | :--- | :--- | :--- |
{agenda_rows}

---

## 🗺️ 3. 30-60-90 Day Probation Development Roadmap

### 🎯 Phase 1: Days 1 – 30 | Learn & Absorb
- **Strategic Objective:** {rd.days_1_30.objective}
- **Key Deliverables & Milestones:**
{deliv_1_30}
- **Phase Success KPIs:** {rd.days_1_30.success_kpis}

---

### 🚀 Phase 2: Days 31 – 60 | Execute & Deliver
- **Strategic Objective:** {rd.days_31_60.objective}
- **Key Deliverables & Milestones:**
{deliv_31_60}
- **Phase Success KPIs:** {rd.days_31_60.success_kpis}

---

### 🏆 Phase 3: Days 61 – 90 | Autonomy & KPI Evaluation
- **Strategic Objective:** {rd.days_61_90.objective}
- **Key Deliverables & Milestones:**
{deliv_61_90}
- **Phase Success KPIs:** {rd.days_61_90.success_kpis}

---

## 👥 4. Buddy & Mentor Support System

| Support Role | Assigned Name & Title | Core Responsibilities & Support Focus |
| :--- | :--- | :--- |
| **Onboarding Buddy** | **{bm.onboarding_buddy}** | {bm.buddy_responsibilities} |
| **Assigned Mentor** | **{bm.assigned_mentor}** | {bm.mentor_responsibilities} |

---

## ✍️ Onboarding Sign-off & Confirmation

| Role | Name | Signature Status | Date |
| :--- | :--- | :---: | :---: |
| **New Employee** | {payload.employee_name} | `[ ACKNOWLEDGED ]` | ___________ |
| **Direct Manager** | Head of Technology | `[ APPROVED ]` | {today_str} |
| **HR Partner** | Talent Management Officer | `[ VERIFIED ]` | {today_str} |

---

> *This Corporate Onboarding Roadmap was generated automatically by Agent 9 (Corporate-Grade Onboarding Planner).*  
> *Authorized for Employee & Manager Onboarding Briefing.*
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 9] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    offers_dir = Path(paths["offers"])
    onboarding_dir = Path(paths["onboarding"])

    # Dual Output Paths in 05_onboarding_vault/
    json_output_path = onboarding_dir / "is9_output_onboarding_plan.json"
    md_output_path = onboarding_dir / "is9_onboarding_roadmap_formal.md"

    print(f"🚀 [Agent 9] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Read Offer Package (IS8)
    is8_json_path = offers_dir / "is8_output_offer_package.json"
    is8_legacy_path = offers_dir / "is8_output_offer_details.json"

    is8_data_str = ""
    if is8_json_path.exists():
        with open(is8_json_path, "r", encoding="utf-8") as f:
            is8_data_str = f.read()
        print(f"📄 [Agent 9] อ่านข้อมูลสัญญาจ้างจาก {is8_json_path.name} สำเร็จ")
    elif is8_legacy_path.exists():
        with open(is8_legacy_path, "r", encoding="utf-8") as f:
            is8_data_str = f.read()
        print(f"📄 [Agent 9] อ่านข้อมูลสัญญาจ้างจาก {is8_legacy_path.name} สำเร็จ")
    else:
        print(f"❌ [Agent 9] ขัดข้อง: ไม่พบไฟล์ข้อเสนอจ้างงาน IS8 ใน Workspace {job_id}")
        sys.exit(1)

    # Read JD Context
    jd_json_path = specs_dir / "is1_output_job_description.json"
    jd_txt_path = specs_dir / "is1_output_job_description.txt"

    jd_context_str = ""
    if jd_json_path.exists():
        with open(jd_json_path, "r", encoding="utf-8") as f:
            jd_context_str = f.read()
    elif jd_txt_path.exists():
        with open(jd_txt_path, "r", encoding="utf-8") as f:
            jd_context_str = f.read()

    system_instruction = (
        "คุณคือ Agent 9 (Corporate-Grade Onboarding & 30-60-90 Day Roadmap Generator)\n"
        "หน้าที่ของคุณคือการออกแบบแผนต้อนรับพนักงานใหม่และสร้าง Roadmap ช่วงทดลองงาน 30-60-90 วัน\n"
        "โครงสร้างของแผน Onboarding ต้องประกอบด้วย 4 ส่วนสำคัญ:\n"
        "1. pre_arrival_checklist: จัดทำรายการเตรียมความพร้อม IT Assets, Work Email, System Access, และ Workplace Setup\n"
        "2. day_1_agenda: กำหนดตารางกิจกรรมวันแรก (Orientation, Team Intro, Workspace Handover, Manager Sync)\n"
        "3. probation_roadmap_30_60_90: ออกแบบแผนพัฒนา 3 ระยะ (days_1_30: Learn & Absorb, days_31_60: Execute & Deliver, days_61_90: Autonomy & KPI Evaluation)\n"
        "4. buddy_and_mentor_assignment: มอบหมายพี่เลี้ยง (Onboarding Buddy) และที่ปรึกษา (Assigned Mentor) พร้อมระบุบทบาทความรับผิดชอบ\n\n"
        "โปรดออกแบบแผน Onboarding ที่มีความเป็นมืออาชีพสูง สร้างความประทับใจวันแรก และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลสัญญาจ้างและข้อเสนองาน (IS8 Offer Package):
{is8_data_str}

ข้อมูลบริบทตำแหน่งงาน (Job Description):
{jd_context_str}

กรุณาออกแบบแผน Onboarding ตารางกิจกรรมวันแรก Roadmap 30-60-90 วัน และบันทึกลงใน Schema ให้สมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=OnboardingPlanPayload,
                temperature=0.3,
            ),
        )


        onboarding_payload = OnboardingPlanPayload.model_validate_json(response.text)
        onboarding_payload.job_id = job_id

        json_str = onboarding_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(onboarding_payload)

        # Safety Guards & File Operations in 05_onboarding_vault/
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        print(f"✅ [Agent 9] บันทึกไฟล์ {json_output_path.name} (Structured Payload) ใน 05_onboarding_vault สำเร็จ")
        print(f"✅ [Agent 9] บันทึกไฟล์ {md_output_path.name} (Formal Roadmap Guide) ใน 05_onboarding_vault สำเร็จ")
        return onboarding_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 9] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e



if __name__ == "__main__":
    main()