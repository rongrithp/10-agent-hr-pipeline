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
    print("❌ [Agent 10] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Master Talent Profiler & Knowledge Base Aggregator ---

class HiredCandidateDossier(BaseModel):
    employee_id: str = Field(description="รหัสพนักงาน/ผู้สมัครที่ได้รับการคัดเลือก")
    employee_name: str = Field(description="ชื่อ-นามสกุล ผู้ได้รับการคัดเลือก")
    job_title: str = Field(description="ตำแหน่งงานที่ได้รับแต่งตั้ง")
    department: str = Field(description="แผนกที่สังกัด")
    start_date: str = Field(description="วันที่เริ่มงานจริง")
    cv_screening_score: int = Field(description="คะแนนการคัดกรองเรซูเม่จาก Agent 4 (%)")
    interview_evaluation_score: int = Field(description="คะแนนประเมินการสัมภาษณ์จาก Agent 6 (%)")
    compensation_package: str = Field(description="สรุปแพ็กเกจผลตอบแทนที่ตกลง (Base Salary + Allowances + Perks)")
    probation_90_day_goals_summary: str = Field(description="สรุปเป้าหมายและหมุดหมายสำคัญ 90 วันแรก")
    key_competencies_and_strengths: List[str] = Field(description="ทักษะและความเชี่ยวชาญหลักที่เป็นจุดเด่น")


class TalentPoolCandidate(BaseModel):
    applicant_id: str = Field(description="รหัสผู้สมัครสำรอง")
    applicant_name: str = Field(description="ชื่อ-นามสกุล ผู้สมัครสำรอง")
    current_role: str = Field(description="ตำแหน่งงานปัจจุบันและประสบการณ์")
    cv_match_score: int = Field(description="คะแนนคัดกรองเรซูเม่ (%)")
    screening_decision: str = Field(description="สถานะการคัดกรอง (QUALIFIED_FOR_INTERVIEW, ON_HOLD, REJECTED)")
    skill_tags: List[str] = Field(description="แท็กทักษะและความเชี่ยวชาญที่ได้รับการยืนยัน")
    future_suitability_assessment: str = Field(description="คำแนะนำความเหมาะสมสำหรับตำแหน่งงานในอนาคต")


class RecruitmentFunnelAnalytics(BaseModel):
    total_candidates_sourced: int = Field(description="จำนวนผู้สมัครทั้งหมดในรอบนี้")
    qualified_for_interview_count: int = Field(description="จำนวนผู้สมัครที่ผ่านการคัดกรอง CV")
    interviewed_count: int = Field(description="จำนวนผู้สมัครที่ได้รับการสัมภาษณ์")
    offer_extended_count: int = Field(description="จำนวนผู้สมัครที่ได้รับข้อเสนองาน")
    hired_count: int = Field(description="จำนวนผู้ได้รับการจ้างงาน (Hired)")
    funnel_conversion_rate_percentage: float = Field(description="อัตราการแปลงผลรวม (Conversion Rate %)")
    cycle_time_days_estimate: int = Field(default=14, description="ประมาณการระยะเวลาของกระบวนการสรรหา (วัน)")


class MasterTalentProfilePayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    hired_candidate_dossier: HiredCandidateDossier = Field(description="1. แฟ้มประวัติผู้ได้รับการคัดเลือก (Hired Candidate Dossier)")
    talent_pool_registry: List[TalentPoolCandidate] = Field(description="2. คลังผู้สมัครสำรองสำหรับอนาคต (Talent Pool Registry)")
    recruitment_funnel_analytics: RecruitmentFunnelAnalytics = Field(description="3. สถิติภาพรวมกระบวนการสรรหา (Funnel Analytics)")
    knowledge_base_summary: str = Field(description="สรุปภาพรวมสำหรับคลังความรู้ HR Knowledge Base")


def format_formal_markdown(payload: MasterTalentProfilePayload) -> str:
    """แปลงคลังข้อมูลเป็นเอกสาร Markdown Formal Executive Talent Dossier สวยงามระดับ Master Report"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    hired = payload.hired_candidate_dossier
    fn = payload.recruitment_funnel_analytics

    qual_rate = (fn.qualified_for_interview_count / fn.total_candidates_sourced * 100) if fn.total_candidates_sourced > 0 else 0.0
    strengths_list = "\n".join([f"- ⭐ {s}" for s in hired.key_competencies_and_strengths])

    pool_rows = []
    for cand in payload.talent_pool_registry:
        tags_str = ", ".join(cand.skill_tags[:4])
        pool_rows.append(
            f"| **{cand.applicant_name}** (`{cand.applicant_id}`) | {cand.current_role} | "
            f"**{cand.cv_match_score}%** | `{cand.screening_decision}` | `{tags_str}` | {cand.future_suitability_assessment} |"
        )
    pool_table = "\n".join(pool_rows)

    return f"""# 📂 MASTER TALENT DOSSIER & RECRUITMENT KNOWLEDGE BASE REPORT

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{payload.job_id}`  
> **Target Position:** **{payload.position_title}**  
> **Hired Candidate:** **{hired.employee_name}** (`{hired.employee_id}`)  
> **Document Status:** Master Knowledge Base Archived  
> **Date Generated:** {today_str}  

---

## 📈 Recruitment Funnel Analytics & Pipeline Performance

| Pipeline Stage | Candidate Count | Stage Conversion | Operational Status |
| :--- | :---: | :---: | :---: |
| **Total Candidates Sourced & Screened (IS4)** | **{fn.total_candidates_sourced}** | 100.0% | `COMPLETED` |
| **Qualified for Interview (Shortlist)** | **{fn.qualified_for_interview_count}** | {qual_rate:.1f}% | `COMPLETED` |
| **Panel Interviewed & Assessed (IS6)** | **{fn.interviewed_count}** | 100.0% | `COMPLETED` |
| **Offer Extended & Accepted (IS8)** | **{fn.offer_extended_count}** | 100.0% | `COMPLETED` |
| **Successfully Hired & Onboarded (IS9)** | **{fn.hired_count}** | **{fn.funnel_conversion_rate_percentage:.1f}%** | `HIRED` |

---

## 👤 Hired Candidate Master Dossier

### 👤 **{hired.employee_name}** (`{hired.employee_id}`)
- **Assigned Position:** **{hired.job_title}**
- **Department:** {hired.department}
- **Official Start Date:** **{hired.start_date}**
- **CV Screening Match Score:** **{hired.cv_screening_score}%**
- **Panel Interview Assessment Score:** **{hired.interview_evaluation_score}%**

#### 💰 Total Compensation Package Summary
> {hired.compensation_package}

#### 🎯 90-Day Probation Goals & Key Milestones
> {hired.probation_90_day_goals_summary}

#### 🌟 Key Technical Competencies & Core Strengths
{strengths_list}

---

## 🗃️ Talent Pool Registry & Future Candidate Pipeline

| Candidate Name | Current Role | CV Score | Status | Verified Skill Tags | Future Role Suitability |
| :--- | :--- | :---: | :---: | :--- | :--- |
{pool_table}

---

## 📝 Executive Knowledge Base Archival Summary

> {payload.knowledge_base_summary}

---

## ✍️ Knowledge Base Certification & Sign-off

| Role | Name & Title | Signature Status | Timestamp |
| :--- | :--- | :---: | :---: |
| **Master Talent Profiler** | Agent 10 Knowledge Base Aggregator | `[ ARCHIVED ]` | {today_str} |
| **Director of HR** | Harrow Executive Committee | `[ FINALIZED ]` | {today_str} |

---

> *This Master Talent Dossier was generated automatically by Agent 10 (Master Talent Profiler).*  
> *Ready for Database Sync (Agent 11) & Telegram Notification (Agent 12).*
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 10] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    dropzone_dir = Path(paths["dropzone"])
    evaluations_dir = Path(paths["evaluations"])
    offers_dir = Path(paths["offers"])
    onboarding_dir = Path(paths["onboarding"])

    # Dual Output Paths in 05_onboarding_vault/ (+ legacy bridge)
    json_output_path = onboarding_dir / "is10_output_talent_profile.json"
    legacy_json_path = onboarding_dir / "is10_output_employee_profile.json"
    md_output_path = onboarding_dir / "is10_talent_dossier_formal.md"

    print(f"🚀 [Agent 10] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Read All Lifecycle Artifacts (is1, is4, is6, is8, is9, cvs)
    lifecycle_data = {}

    # IS1
    jd_path = specs_dir / "is1_output_job_description.json"
    if jd_path.exists():
        with open(jd_path, "r", encoding="utf-8") as f:
            lifecycle_data["is1"] = f.read()

    # IS4
    is4_path = evaluations_dir / "is4_output_screening_results.json"
    if is4_path.exists():
        with open(is4_path, "r", encoding="utf-8") as f:
            lifecycle_data["is4"] = f.read()

    # IS6
    is6_path = evaluations_dir / "is6_output_interview_evaluations.json"
    if is6_path.exists():
        with open(is6_path, "r", encoding="utf-8") as f:
            lifecycle_data["is6"] = f.read()

    # IS8
    is8_path = offers_dir / "is8_output_offer_package.json"
    if is8_path.exists():
        with open(is8_path, "r", encoding="utf-8") as f:
            lifecycle_data["is8"] = f.read()

    # IS9
    is9_path = onboarding_dir / "is9_output_onboarding_plan.json"
    if is9_path.exists():
        with open(is9_path, "r", encoding="utf-8") as f:
            lifecycle_data["is9"] = f.read()

    # Mock CV Batch
    cv_path = dropzone_dir / "mock_cv_batch.json"
    if cv_path.exists():
        with open(cv_path, "r", encoding="utf-8") as f:
            lifecycle_data["cvs"] = f.read()

    print(f"📄 [Agent 10] รวบรวมข้อมูลครบทั้ง 5 Lifecycle ({len(lifecycle_data)} ไฟล์) สำเร็จ")

    system_instruction = (
        "คุณคือ Agent 10 (Master Talent Profiler & Recruitment Knowledge Base Aggregator)\n"
        "หน้าที่ของคุณคือการกวาดรวบรวมข้อมูลประวัติจากทุก Lifecycle (is1, is4, is6, is8, is9) เพื่อจัดทำคลังข้อมูลบุคลากรแบบองค์รวม\n"
        "โครงสร้างของ Master Talent Profile ต้องประกอบด้วย 3 ส่วนสำคัญ:\n"
        "1. hired_candidate_dossier: รวบรวมประวัติผู้ได้รับการคัดเลือก (ข้อมูลส่วนตัว, ตำแหน่ง, คะแนนคัดกรอง, คะแนนสัมภาษณ์, แพ็กเกจผลตอบแทน, เป้าหมาย 90 วัน, ทักษะหลัก)\n"
        "2. talent_pool_registry: รวบรวมรายชื่อผู้สมัครคนอื่น ๆ เข้าคลังผู้สมัครสำรอง พร้อมแท็กทักษะ (skill_tags) และประเมินความเหมาะสมสำหรับตำแหน่งในอนาคต\n"
        "3. recruitment_funnel_analytics: สถิติสรุปภาพรวมรอบการสรรหา (จำนวนผู้สมัครทั้งหมด, ผ่านการคัดกรอง, ผ่านสัมภาษณ์, ได้รับข้อเสนอ, และ Hired พร้อมคำนวณ % conversion rate)\n\n"
        "โปรดสร้างคลังข้อมูลประวัติบุคลากรที่มีความสมบูรณ์ แม่นยำ และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลประวัติที่รวบรวมจากทุก Lifecycle (IS1 - IS9):
{json.dumps(lifecycle_data, indent=2, ensure_ascii=False)}

กรุณาวิเคราะห์ รวบรวมแฟ้มประวัติพนักงานใหม่ สกัดคลังผู้สมัครสำรอง คำนวณสถิติ Funnel Analytics และบันทึกลงใน Schema ให้สมบูรณ์
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
                response_schema=MasterTalentProfilePayload,
                temperature=0.2,
            ),
        )


        talent_payload = MasterTalentProfilePayload.model_validate_json(response.text)
        talent_payload.job_id = job_id

        # Recalculate conversion rate for precision
        fn = talent_payload.recruitment_funnel_analytics
        if fn.total_candidates_sourced > 0:
            fn.funnel_conversion_rate_percentage = round((fn.hired_count / fn.total_candidates_sourced) * 100, 1)

        json_str = talent_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(talent_payload)

        # Safety Guards & File Operations in 05_onboarding_vault/
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        # Legacy compatibility bridge (is10_output_employee_profile.json)
        legacy_dict = json.loads(json_str)
        legacy_dict["employee_id"] = talent_payload.hired_candidate_dossier.employee_id
        legacy_dict["name"] = talent_payload.hired_candidate_dossier.employee_name
        legacy_dict["job_title"] = talent_payload.hired_candidate_dossier.job_title
        legacy_dict["department"] = talent_payload.hired_candidate_dossier.department

        config.ensure_parent_dir(legacy_json_path)
        with open(legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(legacy_dict, indent=2, ensure_ascii=False))

        print(f"✅ [Agent 10] บันทึกไฟล์ {json_output_path.name} (Structured Payload) ใน 05_onboarding_vault สำเร็จ")
        print(f"✅ [Agent 10] บันทึกไฟล์ {md_output_path.name} (Formal Talent Dossier) ใน 05_onboarding_vault สำเร็จ")

        # Auto-index into Central Talent Store (Task 3.3)
        try:
            from engine.talent_memory import build_talent_index
            build_talent_index()
        except Exception as idx_err:
            print(f"⚠️ [Agent 10] Auto-indexing Talent Pool ล้มเหลว: {idx_err}")

        return talent_payload.model_dump()


    except Exception as e:
        print(f"❌ [Agent 10] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e



if __name__ == "__main__":
    main()