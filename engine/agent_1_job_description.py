import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
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
    print("❌ [Agent 1] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Structured Output Schema Definitions (7 Key Categories) ---

class PositionContext(BaseModel):
    job_title: str = Field(description="ชื่อตำแหน่งงาน (Official Position Title)")
    client_or_organization: str = Field(description="ชื่อองค์กร/โรงเรียน/ลูกค้า (Client or Organization Name)")
    department_school: str = Field(description="แผนก/ฝ่าย/โรงเรียนที่สังกัด (Department / School Unit)")
    reporting_line: str = Field(description="ผู้บังคับบัญชาตามสายงาน (Reporting Line / Reports To)")
    location: str = Field(description="สถานที่ปฏิบัติงาน (Work Location / Campus)")
    employment_type: str = Field(description="ประเภทสัญญาจ้าง (e.g. Full-Time Permanent, 2-Year Contract)")
    headcount: int = Field(default=1, description="จำนวนอัตราที่รับ (Headcount)")


class PrimaryObjective(BaseModel):
    summary: str = Field(description="วัตถุประสงค์หลักและเป้าหมายเชิงกลยุทธ์ของตำแหน่งงาน (Primary Role Objective)")


class Qualifications(BaseModel):
    minimum_required: list[str] = Field(
        description="คุณสมบัติขั้นต่ำที่จำเป็น (Hard Skills, Soft Skills, วุฒิการศึกษา, ประสบการณ์, Certifications)"
    )
    preferred: list[str] = Field(
        description="คุณสมบัติพิเศษเพิ่มเติมที่จะพิจารณาเป็นพิเศษ (Preferred / Bonus Qualifications)"
    )


class SuccessMetrics(BaseModel):
    day_30_goals: list[str] = Field(description="เป้าหมายและความสำเร็จช่วง 30 วันแรก (Month 1 Milestones)")
    day_60_goals: list[str] = Field(description="เป้าหมายและความสำเร็จช่วง 60 วันแรก (Month 2 Milestones)")
    day_90_goals: list[str] = Field(description="เป้าหมายและ KPIs 90 วันแรก (Month 3 / 90-Day KPIs)")


class CompensationBenefits(BaseModel):
    salary_range: str = Field(description="งบประมาณเงินเดือนและค่าตอบแทน (Salary Budget / Range)")
    benefits_package: list[str] = Field(description="สวัสดิการและสิทธิประโยชน์ระดับองค์กร")


class JobDescriptionPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_context: PositionContext = Field(description="1. Position & Organization Context")
    primary_role_objective: PrimaryObjective = Field(description="2. Primary Role Objective")
    key_responsibilities: list[str] = Field(description="3. Key Responsibilities (แบ่งเป็นข้อ ๆ ชัดเจน)")
    qualifications: Qualifications = Field(description="4. Minimum Required Qualifications & 5. Preferred Qualifications")
    success_metrics_90_days: SuccessMetrics = Field(description="6. 90-Day Success Metrics / KPIs")
    compensation_and_benefits: CompensationBenefits = Field(description="7. Compensation & Benefits Package")


def format_formal_markdown(jd: JobDescriptionPayload) -> str:
    """แปลงข้อมูล JD Payload เป็นเอกสาร Markdown ทางการ สวยงามระดับ Corporate-Grade"""
    ctx = jd.position_context
    obj = jd.primary_role_objective
    quals = jd.qualifications
    metrics = jd.success_metrics_90_days
    comp = jd.compensation_and_benefits

    resp_items = "\n".join([f"- {r}" for r in jd.key_responsibilities])
    min_qual_items = "\n".join([f"- {q}" for q in quals.minimum_required])
    pref_qual_items = "\n".join([f"- {q}" for q in quals.preferred])

    m30_items = "\n".join([f"  - {m}" for m in metrics.day_30_goals])
    m60_items = "\n".join([f"  - {m}" for m in metrics.day_60_goals])
    m90_items = "\n".join([f"  - {m}" for m in metrics.day_90_goals])

    benefits_items = "\n".join([f"- {b}" for b in comp.benefits_package])

    today_str = datetime.now().strftime("%Y-%m-%d")

    return f"""# 🏛️ CORPORATE JOB DESCRIPTION

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{jd.job_id}`  
> **Document Status:** Official & Approved  
> **Date Generated:** {today_str}  

---

## 📌 1. Position & Organization Context

| Property | Details |
| :--- | :--- |
| **Position Title** | **{ctx.job_title}** |
| **Client / Organization** | {ctx.client_or_organization} |
| **Department / School Unit** | {ctx.department_school} |
| **Reporting Line** | {ctx.reporting_line} |
| **Work Location** | {ctx.location} |
| **Employment Type** | {ctx.employment_type} |
| **Headcount** | {ctx.headcount} Position(s) |

---

## 🎯 2. Primary Role Objective

{obj.summary}

---

## 📋 3. Key Responsibilities

{resp_items}

---

## 🎓 4. Minimum Required Qualifications

{min_qual_items}

---

## 🌟 5. Preferred Qualifications

{pref_qual_items}

---

## 🚀 6. 90-Day Success Metrics / KPIs

### 📅 Month 1 (Day 1 – 30): Onboarding & Foundation
{m30_items}

### 📅 Month 2 (Day 31 – 60): Execution & Integration
{m60_items}

### 📅 Month 3 (Day 61 – 90): Optimization & Key Performance Indicators (KPIs)
{m90_items}

---

## 💰 7. Compensation & Benefits Package

- **Salary Range / Budget:** {comp.salary_range}
- **Benefits & Perks:**
{benefits_items}

---

> *This Job Description was generated automatically by Agent 1 (Corporate-Grade Job Description Generator).*  
> *Authorized for recruitment and talent acquisition purposes.*
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 1] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])

    ticket_json_path = specs_dir / "is0_job_ticket.json"
    input_spec_path = specs_dir / "is1_input_spec.txt"

    # Dual Output Paths
    json_output_path = specs_dir / "is1_output_job_description.json"
    md_output_path = specs_dir / "is1_job_description_formal.md"
    txt_output_path = specs_dir / "is1_output_job_description.txt"

    print(f"🚀 [Agent 1] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    ticket_content = ""
    if ticket_json_path.exists():
        with open(ticket_json_path, "r", encoding="utf-8") as f:
            ticket_content = f.read()
        print(f"📄 [Agent 1] อ่านข้อมูลจาก {ticket_json_path.name} สำเร็จ")
    elif input_spec_path.exists():
        with open(input_spec_path, "r", encoding="utf-8") as f:
            ticket_content = f.read()
        print(f"📄 [Agent 1] ไม่พบ ticket json อ่านข้อมูลจาก {input_spec_path.name} สำเร็จ")
    else:
        err_msg = f"ไม่พบไฟล์ Ticket หรือ Input Spec ใน {specs_dir}"
        print(f"❌ [Agent 1] ขัดข้อง: {err_msg}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise RuntimeError(err_msg)

    system_instruction = (
        "คุณคือ Agent 1 (Corporate-Grade HR Copywriter & Talent Acquisition Strategist)\n"
        "หน้าที่ของคุณคือการวิเคราะห์ข้อมูล Job Ticket สกัดและสร้างเอกสาร Job Description (JD) มาตรฐานสากลระดับองค์กรชั้นนำ\n"
        "เอกสารต้องครอบคลุม 7 หมวดสำคัญ ดังนี้:\n"
        "1. Position & Organization Context (Reporting Line, School/Client, Location, Employment Type, Headcount)\n"
        "2. Primary Role Objective (วัตถุประสงค์หลักและภาพรวมภารกิจ)\n"
        "3. Key Responsibilities (หน้าที่ความรับผิดชอบหลัก แบ่งเป็นข้อ ๆ ชัดเจน)\n"
        "4. Minimum Required Qualifications (Hard/Soft skills, Certifications, วุฒิการศึกษา, ประสบการณ์)\n"
        "5. Preferred Qualifications (คุณสมบัติพิเศษเพิ่มเติมที่ได้รับพิจารณาเป็นพิเศษ)\n"
        "6. 90-Day Success Metrics / KPIs (เป้าหมาย 30 วัน, 60 วัน, และ 90 วันแรก)\n"
        "7. Compensation & Benefits Package (งบประมาณเงินเดือนและสวัสดิการระดับมาตรฐานองค์กร)\n\n"
        "โปรดขยายความให้เป็นมืออาชีพ ละเอียด ครอบคลุม และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูล Job Ticket สำหรับสร้าง Job Description:
- Job ID: {job_id}
- ข้อมูลดิบจาก Ticket:
{ticket_content}

กรุณาสร้าง Corporate-Grade Job Description โดยกรอกข้อมูลลงใน Schema ให้ครบถ้วนทั้ง 7 หมวดสำคัญ
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
                response_schema=JobDescriptionPayload,
                temperature=0.3,
            ),
        )


        jd_payload = JobDescriptionPayload.model_validate_json(response.text)
        # รับประกันว่า job_id ใน payload ตรงกับ job_id ของระบบ
        jd_payload.job_id = job_id

        json_str = jd_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(jd_payload)

        # Safety Guards & File Operations
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        # Legacy Compatibility Bridge (.txt)
        config.ensure_parent_dir(txt_output_path)
        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        print(f"✅ [Agent 1] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 1] บันทึกไฟล์ {md_output_path.name} (Formal Document) สำเร็จ")
        return jd_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 1] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e



if __name__ == "__main__":
    main()