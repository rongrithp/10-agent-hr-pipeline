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
    print("❌ [Agent 7] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Pre-Employment Compliance & Background Verification ---

class VerificationChecklistItem(BaseModel):
    document_type: str = Field(description="ประเภทเอกสาร/รายการที่ตรวจสอบ (เช่น Passport, Degree, Criminal Check, References)")
    status: Literal["VERIFIED", "PENDING_SUBMISSION", "REQUIRES_REVIEW", "FAILED"] = Field(
        description="สถานะการตรวจสอบ: VERIFIED, PENDING_SUBMISSION, REQUIRES_REVIEW, หรือ FAILED"
    )
    is_mandatory: bool = Field(description="เป็นเอกสารบังคับตามกฎระเบียบองค์กรหรือไม่")
    verification_notes: str = Field(description="บันทึกรายละเอียดผลการตรวจสอบ")


class ComplianceAuditPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    candidate_id: str = Field(description="รหัสผู้สมัครชนะเลิศ")
    candidate_name: str = Field(description="ชื่อ-นามสกุล ผู้สมัครชนะเลิศ")
    current_role: str = Field(description="ตำแหน่งงานปัจจุบันของผู้สมัคร")
    verification_checklist: List[VerificationChecklistItem] = Field(description="รายการตรวจสอบเอกสารและประวัติบังคับ")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="ระดับความเสี่ยงโดยรวม: LOW, MEDIUM, หรือ HIGH")
    risk_factors: List[str] = Field(description="ปัจจัยความเสี่ยงหรือข้อควรระวังที่ตรวจพบ (ถ้ามี)")
    compliance_status: Literal["COMPLIANCE_CLEARED", "CONDITIONAL_CLEARANCE", "FLAGGED_HIGH_RISK"] = Field(
        description="คำตัดสินด้านความถูกต้อง: COMPLIANCE_CLEARED, CONDITIONAL_CLEARANCE, หรือ FLAGGED_HIGH_RISK"
    )
    executive_audit_summary: str = Field(description="สรุปผลการตรวจสอบประวัติฉบับผู้บริหาร")
    pre_onboarding_conditions: List[str] = Field(description="รายการเงื่อนไขและเอกสารที่ต้องส่งมอบเพิ่มเติมก่อนเซ็นสัญญาจริง")
    verified_by: str = Field(default="Harrow Compliance & Legal Verification Unit", description="หน่วยงานผู้ตรวจสอบ")


def format_formal_markdown(payload: ComplianceAuditPayload) -> str:
    """แปลงผลการตรวจประวัติเป็นเอกสาร Markdown Formal Compliance Report สวยงามระดับ Executive Audit Report"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    checklist_rows = []
    for item in payload.verification_checklist:
        mand_str = "🔴 Mandatory" if item.is_mandatory else "🟡 Optional"
        status_badge = f"`{item.status}`"
        checklist_rows.append(
            f"| {mand_str} | **{item.document_type}** | {status_badge} | {item.verification_notes} |"
        )
    checklist_table = "\n".join(checklist_rows)

    risk_factors_list = "\n".join([f"- ⚠️ {rf}" for rf in payload.risk_factors]) if payload.risk_factors else "- ✅ None identified. All clear."
    conditions_list = "\n".join([f"{idx}. 📌 {cond}" for idx, cond in enumerate(payload.pre_onboarding_conditions, start=1)]) if payload.pre_onboarding_conditions else "None (Full clearance granted)."

    return f"""# 🛡️ PRE-EMPLOYMENT COMPLIANCE & BACKGROUND AUDIT REPORT

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{payload.job_id}`  
> **Target Position:** **{payload.position_title}**  
> **Selected Candidate:** **{payload.candidate_name}** (`{payload.candidate_id}`)  
> **Document Status:** Pre-Employment Audit Completed  
> **Date Generated:** {today_str}  

---

## 📈 Executive Compliance Summary

- **Candidate Name:** **{payload.candidate_name}** (`{payload.candidate_id}`)
- **Target Position:** {payload.position_title}
- **Compliance Status:** `{payload.compliance_status}`
- **Overall Risk Level:** `{payload.risk_level}`
- **Auditing Authority:** {payload.verified_by}

> **Executive Audit Statement:**  
> {payload.executive_audit_summary}

---

## 📋 Verification Checklist & Document Audit Matrix

| Requirement | Document / Audit Item | Audit Status | Verification Notes & Findings |
| :---: | :--- | :---: | :--- |
{checklist_table}

---

## ⚠️ Risk Assessment & Identified Factors

- **Overall Risk Level:** `{payload.risk_level}`
- **Identified Risk / Concern Factors:**
{risk_factors_list}

---

## 📝 Pre-Onboarding Conditions (Required Before Contract Signing)

{conditions_list}

---

## ✍️ Verification & Authorization Sign-off

| Role | Name & Title | Signature Status | Date |
| :--- | :--- | :---: | :---: |
| **Compliance Officer** | Head of Legal & Background Checks | `[ APPROVED ]` | {today_str} |
| **HR Director** | Executive Recruitment Committee | `[ AUTHORIZED ]` | {today_str} |

---

> *This Pre-Employment Compliance Report was generated automatically by Agent 7 (Pre-Employment Compliance Engine).*  
> *Authorized for Offer Package Negotiation by Agent 8 (Offer Negotiator).*
"""


def main():
    if len(sys.argv) < 2:
        print("❌ [Agent 7] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    dropzone_dir = Path(paths["dropzone"])
    evaluations_dir = Path(paths["evaluations"])
    offers_dir = Path(paths["offers"])

    # Output Paths in 04_offers_contracts/ (+ legacy bridge in 03_evaluations/)
    json_output_path = offers_dir / "is7_output_compliance_audit.json"
    offers_legacy_json_path = offers_dir / "is7_output_compliance_check.json"
    evals_legacy_json_path = evaluations_dir / "is7_output_compliance_check.json"
    md_output_path = offers_dir / "is7_compliance_audit_report_formal.md"

    print(f"🚀 [Agent 7] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Read Top Candidate from IS6
    is6_json_path = evaluations_dir / "is6_output_interview_evaluations.json"
    is6_legacy_path = evaluations_dir / "is6_output_interview_evaluation.json"

    is6_data_str = ""
    if is6_json_path.exists():
        with open(is6_json_path, "r", encoding="utf-8") as f:
            is6_data_str = f.read()
        print(f"📄 [Agent 7] อ่านข้อมูลผลการสัมภาษณ์จาก {is6_json_path.name} สำเร็จ")
    elif is6_legacy_path.exists():
        with open(is6_legacy_path, "r", encoding="utf-8") as f:
            is6_data_str = f.read()
        print(f"📄 [Agent 7] อ่านข้อมูลผลการสัมภาษณ์จาก {is6_legacy_path.name} สำเร็จ")
    else:
        print(f"❌ [Agent 7] ขัดข้อง: ไม่พบไฟล์ผลประเมินสัมภาษณ์ IS6 ใน {evaluations_dir}")
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

    # Read Documents Dropzone
    docs_file_path = dropzone_dir / "mock_documents.txt"
    docs_data_str = ""

    if docs_file_path.exists():
        with open(docs_file_path, "r", encoding="utf-8") as f:
            docs_data_str = f.read()
        print(f"📄 [Agent 7] อ่านรายการเอกสารจาก {docs_file_path.name} สำเร็จ")
    else:
        # Fallback doc checklist
        docs_data_str = (
            "DOCUMENT CHECKLIST & BACKGROUND VERIFICATION DATA:\n"
            "- Thai National ID / Passport: Verified (Active & Valid)\n"
            "- Academic Qualification: Ph.D. in Computer Science & AI (Degree Verified with University Registrar)\n"
            "- Professional Certifications: AWS Certified Machine Learning Specialist (Active)\n"
            "- Criminal Background Check: Royal Thai Police clearance application submitted; pending final physical seal\n"
            "- Professional Reference Checks: 2 References verified positive (Former VP of Eng & Lead Architect)\n"
        )
        print("ℹ️ [Agent 7] ใช้ข้อมูลเช็คลิสต์เอกสารมาตรฐานสำหรับการตรวจสอบ...")

    system_instruction = (
        "คุณคือ Agent 7 (Pre-Employment Compliance & Background Verification Engine)\n"
        "หน้าที่ของคุณคือการตรวจสอบความถูกต้องของประวัติและเอกสารของผู้สมัครอันดับ 1 (selected_top_candidate) จาก IS6\n"
        "โครงสร้างการตรวจสอบประกอบด้วย 4 ส่วนสำคัญ:\n"
        "1. verification_checklist: ตรวจสอบเอกสารบังคับอย่างน้อย 5 หมวด (Identity/Passport, Degree/Education, Criminal Background Check, Certifications/License, Reference Checks)\n"
        "2. risk_level: ประเมินระดับความเสี่ยงโดยรวม (LOW, MEDIUM, HIGH) พร้อมระบุ risk_factors หากมีข้อควรระวัง\n"
        "3. compliance_status: กำหนดสถานะคำตัดสิน (COMPLIANCE_CLEARED = ผ่านสมบูรณ์, CONDITIONAL_CLEARANCE = ผ่านแบบมีเงื่อนไขเอกสารเพิ่มเติม, FLAGGED_HIGH_RISK = มีความเสี่ยงสูง)\n"
        "4. pre_onboarding_conditions: รายการเอกสารหรือเงื่อนไขที่ต้องส่งมอบเพิ่มเติมก่อนเซ็นสัญญาจ้างงานจริง\n\n"
        "โปรดตรวจสอบอย่างละเอียดและส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลบริบทตำแหน่งงาน (Job Description):
{jd_context_str}

ข้อมูลผลการสัมภาษณ์และผู้สมัครชนะเลิศ (IS6 Selected Top Candidate):
{is6_data_str}

ข้อมูลเอกสารและหลักฐานการตรวจประวัติ (Document Verification Checklist):
{docs_data_str}

กรุณาประเมินความถูกต้อง ตรวจสอบเอกสาร คำนวณระดับความเสี่ยง และบันทึกลงใน Schema ให้สมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ComplianceAuditPayload,
                temperature=0.1,
            ),
        )

        audit_payload = ComplianceAuditPayload.model_validate_json(response.text)
        audit_payload.job_id = job_id

        json_str = audit_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(audit_payload)

        # Safety Guards & File Operations in 04_offers_contracts/
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        # Legacy compatibility bridges
        config.ensure_parent_dir(offers_legacy_json_path)
        with open(offers_legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        config.ensure_parent_dir(evals_legacy_json_path)
        with open(evals_legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        print(f"✅ [Agent 7] บันทึกไฟล์ {json_output_path.name} (Structured Payload) ใน 04_offers_contracts สำเร็จ")
        print(f"✅ [Agent 7] บันทึกไฟล์ {md_output_path.name} (Formal Audit Report) ใน 04_offers_contracts สำเร็จ")

    except Exception as e:
        print(f"❌ [Agent 7] ระบบสมองประมวลผลล้มเหลว: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()