import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Path registration
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ [Agent 8] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Total Rewards & Job Offer Generator ---

class AllowanceItem(BaseModel):
    allowance_name: str = Field(description="ชื่อเงินช่วยเหลือ/ค่าตอบแทนพิเศษ (เช่น Executive Housing Allowance)")
    monthly_amount_thb: float = Field(description="มูลค่าต่อเดือน (บาท)")


class CompensationBreakdown(BaseModel):
    monthly_base_salary_thb: float = Field(description="เงินเดือนพื้นฐานประจำเดือน (บาท)")
    fixed_allowances: List[AllowanceItem] = Field(description="รายการค่าตอบแทนพิเศษประจำเดือน")
    total_monthly_guaranteed_thb: float = Field(description="รวมเงินตอบแทนการันตีต่อเดือน (บาท)")
    annual_base_salary_thb: float = Field(description="เงินตอบแทนการันตีต่อปี (บาท)")
    target_performance_bonus: str = Field(description="โครงสร้างโบนัสตามผลงาน (Target Bonus Structure)")
    benefits_package_highlights: List[str] = Field(description="ไฮไลต์สวัสดิการและสิทธิประโยชน์ (ประกันภัย, กองทุน, ค่าเล่าเรียนลูก)")
    probation_period_days: int = Field(default=90, description="ระยะเวลาทดลองงาน (วัน)")


class ContractualTerms(BaseModel):
    target_start_date: str = Field(description="วันที่คาดว่าจะเริ่มงาน (Target Start Date)")
    working_hours: str = Field(description="เวลาการทำงานและวันทำงานประจำสัปดาห์")
    annual_leave_days: int = Field(default=20, description="วันหยุดพักผ่อนประจำปี (วัน/ปี)")
    notice_period_months: int = Field(default=2, description="ระยะเวลาแจ้งลาออกล่วงหน้า (เดือน)")
    offer_acceptance_deadline: str = Field(description="วันสิ้นสุดการตอบรับข้อเสนอ (Offer Acceptance Deadline)")


class OfferPackagePayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    candidate_id: str = Field(description="รหัสผู้สมัคร")
    candidate_name: str = Field(description="ชื่อ-นามสกุล ผู้สมัคร")
    current_role: str = Field(description="ตำแหน่งงานปัจจุบันของผู้สมัคร")
    compensation_breakdown: CompensationBreakdown = Field(description="1. โครงสร้างผลตอบแทน Total Rewards")
    contractual_terms: ContractualTerms = Field(description="2. เงื่อนไขสัญญาการจ้างงาน")
    pre_conditions: List[str] = Field(description="3. เงื่อนไขบังคับก่อนเริ่มงานตามผลตรวจประวัติ IS7")
    offer_status: Literal["OFFER_GENERATED", "CONTINGENT_OFFER", "HELD_FOR_CLEARANCE"] = Field(
        description="สถานะข้อเสนอ: OFFER_GENERATED, CONTINGENT_OFFER, หรือ HELD_FOR_CLEARANCE"
    )
    executive_offer_summary: str = Field(description="สรุปเหตุผลประกอบข้อเสนอฉบับผู้บริหาร")
    signatory_authority: str = Field(default="Director of Human Resources", description="ผู้มีอำนาจลงนามในจดหมายเสนองาน")


def format_formal_markdown(payload: OfferPackagePayload) -> str:
    """แปลงข้อเสนอจ้างงานเป็นเอกสาร Formal Offer Letter ฉบับทางการ จัดหน้าสวยงามระดับ Corporate"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    comp = payload.compensation_breakdown
    terms = payload.contractual_terms

    fixed_allowance_sum = sum(item.monthly_amount_thb for item in comp.fixed_allowances)
    allowance_rows = "\n".join([
        f"| **Allowance: {item.allowance_name}** | ฿{item.monthly_amount_thb:,.2f} / month |"
        for item in comp.fixed_allowances
    ])

    benefits_list = "\n".join([f"- 🎁 {b}" for b in comp.benefits_package_highlights])
    conditions_list = "\n".join([f"{idx}. 📌 {cond}" for idx, cond in enumerate(payload.pre_conditions, start=1)]) if payload.pre_conditions else "None (Full Clearance Granted)."

    return f"""# 📜 PRIVATE & CONFIDENTIAL: FORMAL LETTER OF OFFER

> **HARROW INTERNATIONAL SCHOOL RECRUITMENT AUTOMATION**  
> **Job Ticket ID:** `{payload.job_id}`  
> **Document Date:** {today_str}  
> **Offer Status:** `{payload.offer_status}`  

---

**To:** **{payload.candidate_name}** (`{payload.candidate_id}`)  
**Current Role:** {payload.current_role}  
**Offered Position:** **{payload.position_title}**  

Dear **{payload.candidate_name}**,

On behalf of Harrow International School, we are delighted to offer you the position of **{payload.position_title}**. We were exceptionally impressed by your background, technical leadership, strategic vision, and expertise during our rigorous recruitment process.

Below are the detailed terms, compensation breakdown, and conditions of our employment offer:

---

## 💰 1. Total Rewards & Compensation Package Breakdown

| Compensation Element | Details & Amount (THB) |
| :--- | :--- |
| **Monthly Base Salary** | **฿{comp.monthly_base_salary_thb:,.2f}** |
{allowance_rows}
| **Total Guaranteed Monthly Package** | **฿{comp.total_monthly_guaranteed_thb:,.2f}** |
| **Annualized Base Guarantee** | **฿{comp.annual_base_salary_thb:,.2f}** |
| **Target Performance Bonus** | {comp.target_performance_bonus} |
| **Probationary Period** | {comp.probation_period_days} Days |

### 🎁 Key Benefits & Perks Included
{benefits_list}

---

## 📅 2. Employment Terms & Contractual Conditions

| Term Parameter | Details |
| :--- | :--- |
| **Target Start Date** | **{terms.target_start_date}** |
| **Working Hours** | {terms.working_hours} |
| **Annual Paid Vacation Leave** | {terms.annual_leave_days} Days per Annum |
| **Notice Period** | {terms.notice_period_months} Months |
| **Offer Acceptance Deadline** | **{terms.offer_acceptance_deadline}** |

---

## ⚠️ 3. Pre-Employment Conditions & Contingencies

This offer of employment is **{payload.offer_status}** subject to the fulfillment of the following pre-employment requirements prior to your start date:
{conditions_list}

---

## ✍️ Acceptance & Confirmation of Offer

To accept this offer of employment, please sign and date this letter below and return it to HR before **{terms.offer_acceptance_deadline}**.

### For and on behalf of Harrow International School:

**Signature:** ___________________________  
**Name:** {payload.signatory_authority}  
**Title:** Executive Director of Human Resources  
**Date:** {today_str}  

---

### Candidate Acceptance Statement:

> *"I, **{payload.candidate_name}**, hereby accept the offer of employment for the position of **{payload.position_title}** under the terms and conditions outlined in this letter."*

**Candidate Signature:** ___________________________  
**Date:** ______________  
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 8] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    evaluations_dir = Path(paths["evaluations"])
    offers_dir = Path(paths["offers"])

    # Dual Output Paths in 04_offers_contracts/ (+ legacy bridge)
    json_output_path = offers_dir / "is8_output_offer_package.json"
    legacy_json_path = offers_dir / "is8_output_offer_details.json"
    md_output_path = offers_dir / "is8_formal_job_offer_letter.md"

    print(f"🚀 [Agent 8] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Read Compliance Audit (IS7)
    is7_json_path = offers_dir / "is7_output_compliance_audit.json"
    is7_offers_legacy = offers_dir / "is7_output_compliance_check.json"
    is7_evals_legacy = evaluations_dir / "is7_output_compliance_check.json"

    is7_data_str = ""
    if is7_json_path.exists():
        with open(is7_json_path, "r", encoding="utf-8") as f:
            is7_data_str = f.read()
        print(f"📄 [Agent 8] อ่านข้อมูลผลตรวจประวัติจาก {is7_json_path.name} สำเร็จ")
    elif is7_offers_legacy.exists():
        with open(is7_offers_legacy, "r", encoding="utf-8") as f:
            is7_data_str = f.read()
        print(f"📄 [Agent 8] อ่านข้อมูลผลตรวจประวัติจาก {is7_offers_legacy.name} สำเร็จ")
    elif is7_evals_legacy.exists():
        with open(is7_evals_legacy, "r", encoding="utf-8") as f:
            is7_data_str = f.read()
        print(f"📄 [Agent 8] อ่านข้อมูลผลตรวจประวัติจาก {is7_evals_legacy.name} สำเร็จ")
    else:
        print(f"❌ [Agent 8] ขัดข้อง: ไม่พบไฟล์ผลตรวจประวัติ IS7 ใน Workspace {job_id}")
        sys.exit(1)

    # Read JD Context for Compensation & Benefits Budget
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
        "คุณคือ Agent 8 (Total Rewards & Job Offer Generator Engine)\n"
        "หน้าที่ของคุณคือการออกแบบโครงสร้างผลตอบแทน Total Rewards และสร้างร่างสัญญาจ้างงานฉบับทางการ (Offer Package)\n"
        "โครงสร้างของแพ็กเกจข้อเสนอต้องประกอบด้วย 4 ส่วนสำคัญ:\n"
        "1. compensation_breakdown: คำนวณ monthly_base_salary_thb, fixed_allowances, total_monthly_guaranteed_thb, annual_base_salary_thb, target_performance_bonus, benefits_package_highlights, และ probation_period_days\n"
        "2. contractual_terms: กำหนด target_start_date, working_hours, annual_leave_days, notice_period_months, และ offer_acceptance_deadline\n"
        "3. pre_conditions: นำรายการเงื่อนไข pre_onboarding_conditions จากผลตรวจประวัติ IS7 มาเป็นเงื่อนไขบังคับ\n"
        "4. offer_status: กำหนดสถานะข้อเสนอ (OFFER_GENERATED หากผ่านประวัติสมบูรณ์, CONTINGENT_OFFER หากผ่านแบบมีเงื่อนไขเอกสาร, HELD_FOR_CLEARANCE หากมีความเสี่ยงสูง)\n\n"
        "โปรดคำนวณและสร้างข้อเสนออย่างสมเหตุสมผล เสนอแพ็กเกจที่แข่งขันได้ในตลาด และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลบริบทตำแหน่งงานและงบประมาณ (Job Description & Budget):
{jd_context_str}

ข้อมูลผลการตรวจประวัติและสถานะผู้สมัคร (IS7 Compliance Audit):
{is7_data_str}

กรุณาออกแบบโครงสร้างผลตอบแทน กำหนดเงื่อนไขสัญญา และบันทึกลงใน Schema ให้สมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=OfferPackagePayload,
                temperature=0.3,
            ),
        )

        offer_payload = OfferPackagePayload.model_validate_json(response.text)
        offer_payload.job_id = job_id

        # Recalculate totals for precision consistency
        comp = offer_payload.compensation_breakdown
        allowance_sum = sum(a.monthly_amount_thb for a in comp.fixed_allowances)
        comp.total_monthly_guaranteed_thb = comp.monthly_base_salary_thb + allowance_sum
        comp.annual_base_salary_thb = comp.total_monthly_guaranteed_thb * 12

        json_str = offer_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(offer_payload)

        # Safety Guards & File Operations in 04_offers_contracts/
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        # Legacy compatibility bridge (is8_output_offer_details.json)
        config.ensure_parent_dir(legacy_json_path)
        with open(legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        print(f"✅ [Agent 8] บันทึกไฟล์ {json_output_path.name} (Structured Payload) ใน 04_offers_contracts สำเร็จ")
        print(f"✅ [Agent 8] บันทึกไฟล์ {md_output_path.name} (Formal Offer Letter) ใน 04_offers_contracts สำเร็จ")
        return offer_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 8] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e



if __name__ == "__main__":
    main()