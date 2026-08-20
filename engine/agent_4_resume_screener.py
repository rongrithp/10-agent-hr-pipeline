import os
import sys
import json
from typing import List, Literal
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

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ [Agent 4] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for High-Precision Resume Screening ---

class SubScores(BaseModel):
    skills_match_score: int = Field(description="คะแนนความตรงของทักษะ (0-100)")
    experience_relevance_score: int = Field(description="คะแนนความเกี่ยวข้องของประสบการณ์ (0-100)")
    education_certifications_score: int = Field(description="คะแนนวุฒิการศึกษาและใบรับรอง (0-100)")


class CandidateScreeningResult(BaseModel):
    applicant_id: str = Field(description="รหัสผู้สมัคร (Candidate ID)")
    applicant_name: str = Field(description="ชื่อ-นามสกุล ผู้สมัคร")
    current_role: str = Field(description="ตำแหน่งปัจจุบันหรือล่าสุด")
    years_of_experience: int = Field(description="จำนวนปีประสบการณ์รวม")
    overall_match_score: int = Field(description="คะแนนความเหมาะสมรวม (0-100%)")
    sub_scores: SubScores = Field(description="คะแนนย่อย 3 ด้าน (Skills, Experience, Education)")
    matched_must_have_keywords: List[str] = Field(description="คีย์เวิร์ดบังคับที่พบในเรซูเม่")
    missing_must_have_keywords: List[str] = Field(description="คีย์เวิร์ดบังคับที่ไม่พบ")
    identified_red_flags: List[str] = Field(description="จุดสังเกต/ข้อควรระวัง/Red Flags ที่พบ")
    strengths: List[str] = Field(description="จุดแข็งหลักที่โดดเด่น")
    decision: Literal["QUALIFIED_FOR_INTERVIEW", "ON_HOLD", "REJECTED"] = Field(
        description="คำตัดสิน: QUALIFIED_FOR_INTERVIEW, ON_HOLD, หรือ REJECTED"
    )
    executive_summary_reason: str = Field(description="เหตุผลประกอบคำตัดสินฉบับผู้บริหาร (Executive Summary Reason)")
    recommended_interview_focus: List[str] = Field(
        description="หัวข้อที่ต้องเจาะสัมภาษณ์เพิ่มเติม (Recommended Interview Focus)"
    )


class CandidateScreeningPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    total_candidates_screened: int = Field(description="จำนวนผู้สมัครทั้งหมดที่ได้รับการคัดกรอง")
    qualified_count: int = Field(description="จำนวนผู้สมัครที่ผ่านเข้ารอบสัมภาษณ์ (QUALIFIED_FOR_INTERVIEW)")
    on_hold_count: int = Field(description="จำนวนผู้สมัครสำรอง (ON_HOLD)")
    rejected_count: int = Field(description="จำนวนผู้สมัครที่ไม่ผ่านเกณฑ์ (REJECTED)")
    candidates: List[CandidateScreeningResult] = Field(description="รายการผลการคัดกรองผู้สมัครทุกคน เรียงตามคะแนน")


def format_formal_markdown(payload: CandidateScreeningPayload) -> str:
    """แปลงผลการคัดกรองเรซูเม่เป็นเอกสาร Markdown Matrix ทางการ สวยงามระดับ Executive Summary"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    matrix_rows = []
    for idx, c in enumerate(payload.candidates, start=1):
        red_flag_str = "<br/>".join([f"⚠️ {rf}" for rf in c.identified_red_flags]) if c.identified_red_flags else "None"
        strength_str = ", ".join(c.strengths[:3])
        status_badge = f"`{c.decision}`"
        
        matrix_rows.append(
            f"| {idx} | **{c.applicant_name}** | {c.current_role} | **{c.overall_match_score}%** | "
            f"{c.sub_scores.skills_match_score}% | {c.sub_scores.experience_relevance_score}% | "
            f"{c.sub_scores.education_certifications_score}% | {status_badge} | "
            f"✅ {strength_str}<br/>{red_flag_str} |"
        )
    matrix_table = "\n".join(matrix_rows)

    detailed_breakdowns = []
    for c in payload.candidates:
        matched_kw = ", ".join([f"`{kw}`" for kw in c.matched_must_have_keywords]) if c.matched_must_have_keywords else "None"
        missing_kw = ", ".join([f"`{kw}`" for kw in c.missing_must_have_keywords]) if c.missing_must_have_keywords else "None"
        rf_list = "\n".join([f"  - ⚠️ {rf}" for rf in c.identified_red_flags]) if c.identified_red_flags else "  - None"
        focus_list = "\n".join([f"  - 🎯 {fcs}" for fcs in c.recommended_interview_focus])

        detailed_breakdowns.append(f"""### 👤 {c.applicant_name} (`{c.applicant_id}`)
- **Current Role:** {c.current_role} ({c.years_of_experience} Years Exp)
- **Overall Match Score:** **{c.overall_match_score}%** | **Decision:** `{c.decision}`
- **Sub-Score Breakdown:** Skills: {c.sub_scores.skills_match_score}% | Experience: {c.sub_scores.experience_relevance_score}% | Education: {c.sub_scores.education_certifications_score}%
- **Matched Must-Haves:** {matched_kw}
- **Missing Must-Haves:** {missing_kw}
- **Identified Red Flags / Warnings:**
{rf_list}
- **Executive Summary Reason:**  
  > {c.executive_summary_reason}
- **Recommended Interview Focus:**
{focus_list}
""")

    breakdowns_text = "\n---\n\n".join(detailed_breakdowns)

    return f"""# 📊 CANDIDATE SCREENING MATRIX & EVALUATION REPORT

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{payload.job_id}`  
> **Target Position:** **{payload.position_title}**  
> **Document Status:** Evaluation Completed  
> **Date Generated:** {today_str}  

---

## 📈 Executive Summary

- **Total Candidates Screened:** {payload.total_candidates_screened}
- **Qualified for Interview (`QUALIFIED_FOR_INTERVIEW`):** {payload.qualified_count}
- **On Hold (`ON_HOLD`):** {payload.on_hold_count}
- **Rejected (`REJECTED`):** {payload.rejected_count}

---

## 🏆 Candidate Comparison Matrix

| Rank | Candidate Name | Current Role | Overall Score | Skills | Exp | Edu | Decision | Summary Highlights & Red Flags |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
{matrix_table}

---

## 👤 Detailed Candidate Evaluation Breakdowns

{breakdowns_text}

---

> *This Candidate Screening Matrix was generated automatically by Agent 4 (High-Precision Resume Screener & Candidate Scoring Engine).*  
> *Authorized for HR Lead & Hiring Manager Review.*
"""


def main():
    if len(sys.argv) < 2:
        print("❌ [Agent 4] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    dropzone_dir = Path(paths["dropzone"])
    specs_dir = Path(paths["specs"])
    evaluations_dir = Path(paths["evaluations"])

    # Output Paths
    json_output_path = evaluations_dir / "is4_output_screening_results.json"
    md_output_path = evaluations_dir / "is4_screening_matrix_formal.md"
    legacy_json_path = evaluations_dir / "is4_output_candidate_scores.json"

    print(f"🚀 [Agent 4] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Check CV file in dropzone
    cv_batch_path = dropzone_dir / "mock_cv_batch.json"
    cv_data_str = ""

    if cv_batch_path.exists():
        with open(cv_batch_path, "r", encoding="utf-8") as f:
            cv_data_str = f.read()
        print(f"📄 [Agent 4] อ่านไฟล์เรซูเม่จาก {cv_batch_path.name} สำเร็จ")
    else:
        # Check alternative json/txt files in dropzone
        other_cv_files = list(dropzone_dir.glob("*.json")) + list(dropzone_dir.glob("*.txt"))
        if other_cv_files:
            with open(other_cv_files[0], "r", encoding="utf-8") as f:
                cv_data_str = f.read()
            print(f"📄 [Agent 4] อ่านไฟล์เรซูเม่จาก {other_cv_files[0].name} สำเร็จ")
        else:
            print(f"⚠️ [Agent 4] สแตนด์บาย: ยังไม่มีไฟล์เรซูเม่ (mock_cv_batch.json) ในโฟลเดอร์ 02_sourcing_dropzone ของ {job_id}")
            sys.exit(0)

    # Read Specs (JD & Sourcing Strategy Directives)
    jd_json_path = specs_dir / "is1_output_job_description.json"
    strategy_json_path = specs_dir / "is2_output_sourcing_strategy.json"
    jd_txt_path = specs_dir / "is1_output_job_description.txt"

    spec_context_parts = []
    if jd_json_path.exists():
        with open(jd_json_path, "r", encoding="utf-8") as f:
            spec_context_parts.append(f"--- Job Description (IS1) ---\n{f.read()}")
    elif jd_txt_path.exists():
        with open(jd_txt_path, "r", encoding="utf-8") as f:
            spec_context_parts.append(f"--- Job Description (IS1) ---\n{f.read()}")

    if strategy_json_path.exists():
        with open(strategy_json_path, "r", encoding="utf-8") as f:
            spec_context_parts.append(f"--- Sourcing Strategy Directives (IS2) ---\n{f.read()}")

    combined_specs = "\n\n".join(spec_context_parts)

    system_instruction = (
        "คุณคือ Agent 4 (High-Precision Resume Screener & Candidate Scoring Engine)\n"
        "หน้าที่ของคุณคือการคัดกรองและประเมินเรซูเม่ผู้สมัครอย่างแม่นยำและเป็นธรรม โดยเปรียบเทียบกับ Job Description (IS1) และ Sourcing Directives (IS2)\n"
        "เกณฑ์การประเมินผู้สมัครแต่ละคนประกอบด้วย:\n"
        "1. overall_match_score (0-100%) พร้อม sub_scores 3 ด้าน (Skills Match, Experience Relevance, Education/Certifications)\n"
        "2. ตรวจสอบ matched_must_have_keywords และ missing_must_have_keywords อย่างละเอียด\n"
        "3. ระบุ identified_red_flags (ข้อควรระวัง/ข้อห้าม/ประสบการณ์ไม่ครบ) อย่างตรงไปตรงมา\n"
        "4. ให้สถานะคำตัดสิน decision: QUALIFIED_FOR_INTERVIEW (ผ่านเกณฑ์สัมภาษณ์), ON_HOLD (สำรอง), หรือ REJECTED (ไม่ผ่าน)\n"
        "5. สรุปเหตุผล executive_summary_reason และกำหนด recommended_interview_focus หัวข้อที่ต้องเจาะสัมภาษณ์เพิ่มเติม\n\n"
        "โปรดเรียงลำดับผู้สมัครตาม overall_match_score จากมากไปน้อย และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลเกณฑ์การคัดเลือก (JD & Sourcing Directives):
{combined_specs}

ข้อมูลเรซูเม่ผู้สมัคร (Candidate CVs):
{cv_data_str}

กรุณาคัดกรองและประเมินผู้สมัครทุกคนอย่างละเอียดถี่ถ้วน แล้วบันทึกผลลงใน Schema ให้สมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=CandidateScreeningPayload,
                temperature=0.2,
            ),
        )

        screening_payload = CandidateScreeningPayload.model_validate_json(response.text)
        screening_payload.job_id = job_id

        # Update candidate summary counts
        screening_payload.total_candidates_screened = len(screening_payload.candidates)
        screening_payload.qualified_count = sum(1 for c in screening_payload.candidates if c.decision == "QUALIFIED_FOR_INTERVIEW")
        screening_payload.on_hold_count = sum(1 for c in screening_payload.candidates if c.decision == "ON_HOLD")
        screening_payload.rejected_count = sum(1 for c in screening_payload.candidates if c.decision == "REJECTED")

        # Sort candidates by overall score descending
        screening_payload.candidates.sort(key=lambda c: c.overall_match_score, reverse=True)

        json_str = screening_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(screening_payload)

        # Safety Guards & File Operations
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        # Legacy Compatibility Bridge (is4_output_candidate_scores.json)
        config.ensure_parent_dir(legacy_json_path)
        with open(legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        print(f"✅ [Agent 4] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 4] บันทึกไฟล์ {md_output_path.name} (Formal Screening Matrix) สำเร็จ")
        print(f"🚀 [Agent 4] คัดกรองเรซูเม่เสร็จสิ้น เซฟลงโฟลเดอร์ 03_evaluations")

    except Exception as e:
        print(f"❌ [Agent 4] ระบบสมองประมวลผลล้มเหลว: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()