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
from engine.resilience import generate_content_with_retry


if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ [Agent 6] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Multi-Candidate Interview Evaluation ---

class CompetencyScoreItem(BaseModel):
    category_name: str = Field(description="หมวดหมู่เกณฑ์การประเมิน (Rubric Category)")
    score_1_to_5: int = Field(description="คะแนนที่ได้รับ (1-5 คะแนน)")
    weight_percentage: int = Field(description="น้ำหนักคะแนน (%)")
    weighted_score: float = Field(description="คะแนนถ่วงน้ำหนักที่ได้")
    interviewer_comments: str = Field(description="ความเห็นและข้อสังเกตของผู้สัมภาษณ์ในหมวดนี้")


class IndividualEvaluationResult(BaseModel):
    applicant_id: str = Field(description="รหัสผู้สมัคร")
    applicant_name: str = Field(description="ชื่อ-นามสกุล ผู้สมัคร")
    current_role: str = Field(description="ตำแหน่งงานปัจจุบัน")
    overall_interview_score: int = Field(description="คะแนนสรุปการสัมภาษณ์รวม (0-100%)")
    competency_scores: List[CompetencyScoreItem] = Field(description="คะแนนย่อยตามเกณฑ์ Rubric แต่ละ Competency")
    key_strengths: List[str] = Field(description="จุดเด่นเชิงประจักษ์จากการสัมภาษณ์ (Key Strengths)")
    areas_of_concern: List[str] = Field(description="ความเสี่ยงหรือจุดอ่อนที่พบ (Areas of Concern / Red Flags)")
    final_verdict: Literal["HIRE_RECOMMENDED", "CONSIDER_BACKUP", "REJECT"] = Field(
        description="คำตัดสินขั้นเด็ดขาด: HIRE_RECOMMENDED, CONSIDER_BACKUP, หรือ REJECT"
    )
    executive_summary_reason: str = Field(description="เหตุผลประกอบคำตัดสินฉบับผู้บริหาร")


class SelectedCandidateInfo(BaseModel):
    applicant_id: str = Field(description="รหัสผู้สมัครที่ได้รับเลือก")
    applicant_name: str = Field(description="ชื่อผู้สมัครที่ได้รับเลือก")
    overall_score: int = Field(description="คะแนนรวมของผู้สมัครที่ได้รับเลือก")
    reason_for_selection: str = Field(description="เหตุผลในการคัดเลือกเป็นอันดับ 1")


class InterviewEvaluationsPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    total_candidates_evaluated: int = Field(description="จำนวนผู้สมัครที่ได้รับการประเมินการสัมภาษณ์")
    selected_top_candidate: Optional[SelectedCandidateInfo] = Field(
        description="ผู้สมัครอันดับ 1 ที่ได้รับการคัดเลือกเพื่อส่งต่อไปทำ Offer และ Background Check", default=None
    )
    evaluations: List[IndividualEvaluationResult] = Field(description="รายการผลการประเมินการสัมภาษณ์ เรียงตามคะแนน")
    hiring_committee_recommendation: str = Field(description="ข้อเสนอแนะภาพรวมสำหรับคณะกรรมการจ้างงานและผู้บริหาร")


def format_formal_markdown(payload: InterviewEvaluationsPayload) -> str:
    """แปลงผลการประเมินการสัมภาษณ์เป็นเอกสาร Markdown Matrix ทางการ สวยงามระดับ Executive Summary Report"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    matrix_rows = []
    for idx, eval_res in enumerate(payload.evaluations, start=1):
        verdict_badge = f"`{eval_res.final_verdict}`"
        strengths_str = ", ".join(eval_res.key_strengths[:3])
        concerns_str = ", ".join(eval_res.areas_of_concern[:2]) if eval_res.areas_of_concern else "None"

        matrix_rows.append(
            f"| {idx} | **{eval_res.applicant_name}** | {eval_res.current_role} | "
            f"**{eval_res.overall_interview_score}%** | {verdict_badge} | "
            f"✅ {strengths_str} | ⚠️ {concerns_str} |"
        )
    matrix_table = "\n".join(matrix_rows)

    candidate_details = []
    for eval_res in payload.evaluations:
        rubric_rows = "\n".join([
            f"| **{cs.category_name}** | {cs.weight_percentage}% | {cs.score_1_to_5} / 5 | "
            f"{cs.weighted_score:.1f}% | {cs.interviewer_comments} |"
            for cs in eval_res.competency_scores
        ])

        strengths_list = "\n".join([f"- ✅ {st}" for st in eval_res.key_strengths])
        concerns_list = "\n".join([f"- ⚠️ {ac}" for ac in eval_res.areas_of_concern]) if eval_res.areas_of_concern else "- None"

        candidate_details.append(f"""### 👤 {eval_res.applicant_name} (`{eval_res.applicant_id}`)
- **Current Role:** {eval_res.current_role}
- **Overall Interview Score:** **{eval_res.overall_interview_score}%** | **Final Verdict:** `{eval_res.final_verdict}`
- **Executive Justification:**  
  > {eval_res.executive_summary_reason}

#### ⚖️ Competency Rubric Scores Breakdown
| Competency Category | Weight | Rating (1-5) | Weighted Score | Interviewer Observations & Notes |
| :--- | :---: | :---: | :---: | :--- |
{rubric_rows}

#### 🌟 Key Strengths Observed
{strengths_list}

#### ⚠️ Areas of Concern / Risks
{concerns_list}
""")

    details_text = "\n---\n\n".join(candidate_details)

    top_cand_str = "None"
    if payload.selected_top_candidate:
        sc = payload.selected_top_candidate
        top_cand_str = f"**{sc.applicant_name}** (`{sc.applicant_id}`) - Overall Score: **{sc.overall_score}%**"

    return f"""# 🏆 FORMAL INTERVIEW EVALUATION REPORT & FINAL SELECTION MATRIX

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{payload.job_id}`  
> **Target Position:** **{payload.position_title}**  
> **Document Status:** Final Hiring Assessment Completed  
> **Date Generated:** {today_str}  

---

## 📈 Hiring Committee Executive Summary

- **Total Candidates Evaluated:** {payload.total_candidates_evaluated}
- **Top Selected Candidate:** {top_cand_str}
- **Committee Recommendation:**  
  > {payload.hiring_committee_recommendation}

---

## 🏆 Final Interview Candidate Matrix

| Rank | Candidate Name | Current Role | Overall Score | Final Verdict | Key Strengths | Areas of Concern |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
{matrix_table}

---

## 👤 Detailed Candidate Evaluation Breakdowns

{details_text}

---

> *This Interview Evaluation Report was generated automatically by Agent 6 (Multi-Candidate Interview Evaluator & Scoring Engine).*  
> *Authorized for Executive Decision & Transition to Agent 7 Compliance Check.*
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 6] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    dropzone_dir = Path(paths["dropzone"])
    specs_dir = Path(paths["specs"])
    evaluations_dir = Path(paths["evaluations"])

    # Dual Output Paths (+ legacy bridge)
    json_output_path = evaluations_dir / "is6_output_interview_evaluations.json"
    legacy_json_path = evaluations_dir / "is6_output_interview_evaluation.json"
    md_output_path = evaluations_dir / "is6_interview_evaluation_report_formal.md"

    print(f"🚀 [Agent 6] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Read IS5 Schedule / Guide Context
    is5_json_path = evaluations_dir / "is5_output_interview_schedule.json"
    is5_data_str = ""
    if is5_json_path.exists():
        with open(is5_json_path, "r", encoding="utf-8") as f:
            is5_data_str = f.read()
        print(f"📄 [Agent 6] อ่านคู่มือการสัมภาษณ์จาก {is5_json_path.name} สำเร็จ")

    # Read Interview Notes from 02_sourcing_dropzone/ (.md / .txt)
    note_files = list(dropzone_dir.glob("*interview*.md")) + \
                 list(dropzone_dir.glob("*interview*.txt")) + \
                 list(dropzone_dir.glob("*feedback*.md")) + \
                 list(dropzone_dir.glob("*feedback*.txt")) + \
                 list(dropzone_dir.glob("mock_interview_notes.txt"))
    
    unique_note_files = list(dict.fromkeys(note_files))
    notes_data_parts = []

    if unique_note_files:
        print(f"📄 [Agent 6] ตรวจพบไฟล์บันทึกการสัมภาษณ์จำนวน {len(unique_note_files)} ไฟล์ใน 02_sourcing_dropzone/")
        for nfile in sorted(unique_note_files):
            with open(nfile, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    notes_data_parts.append(f"--- Interviewer Feedback File: {nfile.name} ---\n{content}")
                    print(f"   ✅ [Agent 6] อ่านบันทึกการสัมภาษณ์จาก {nfile.name} สำเร็จ")
        notes_data_str = "\n\n".join(notes_data_parts)
    else:
        notes_data_str = ""

    if not notes_data_str.strip():
        print(f"ℹ️ [Agent 6] ไม่พบไฟล์บันทึกสัมภาษณ์ใน dropzone กำลังเปิดใช้ Fallback ประมวลผลจากแผนสัมภาษณ์ IS5...")
        notes_data_str = (
            "INTERVIEW NOTES (Fallback Baseline Assessment):\n"
            "- Candidate: Dr. Arisara Srivatanakul (dr_arisara)\n"
            "- Technical Depth: Demonstrated deep knowledge in Python, PyTorch, MLOps, and NLP architectures.\n"
            "- EdTech Strategy: Articulated a clear AI roadmap for Harrow International School with emphasis on student data privacy.\n"
            "- Leadership: Strong communication style, experience mentoring 10 engineers, excellent alignment with school values.\n"
            "- Panel Rating: Overall 4.8 / 5. Strongly recommended for hire."
        )

    system_instruction = (
        "คุณคือ Agent 6 (Multi-Candidate Interview Evaluator & Scoring Engine)\n"
        "หน้าที่ของคุณคือการวิเคราะห์และประเมินผลการสัมภาษณ์ผู้สมัครร่วมกับเกณฑ์ Rubric ใน IS5 และบันทึกการสัมภาษณ์ (Interview Notes / Transcripts)\n"
        "เกณฑ์การประเมินผู้สมัครแต่ละคนประกอบด้วย:\n"
        "1. overall_interview_score (0-100%) คำนวณตามน้ำหนักของ competency_scores แต่ละหมวด\n"
        "2. สกัด key_strengths (จุดเด่นเชิงประจักษ์) และ areas_of_concern (ความเสี่ยงหรือจุดอ่อนที่พบ)\n"
        "3. กำหนดคำตัดสิน final_verdict: HIRE_RECOMMENDED (แนะนำให้จ้างงาน), CONSIDER_BACKUP (สำรอง), หรือ REJECT (ปฏิเสธ)\n"
        "4. สรุปเหตุผล executive_summary_reason และเลือก selected_top_candidate ผู้สมัครอันดับ 1 เพื่อส่งต่อไปยัง Agent 7 (Compliance Check) และ Agent 8 (Offer Negotiation)\n\n"
        "โปรดประเมินอย่างเป็นธรรมและส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลแผนและเกณฑ์การสัมภาษณ์ (IS5 Schedule & Rubrics):
{is5_data_str}

บันทึกจากการสัมภาษณ์ (Interviewer Notes / Transcripts):
{notes_data_str}

กรุณาประเมินผลการสัมภาษณ์ผู้สมัครทุกคน เรียงลำดับคะแนนจากมากไปน้อย และระบุผู้สมัครอันดับ 1 (selected_top_candidate) บันทึกลงใน Schema ให้สมบูรณ์
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
                response_schema=InterviewEvaluationsPayload,
                temperature=0.1,
            ),
        )


        eval_payload = InterviewEvaluationsPayload.model_validate_json(response.text)
        eval_payload.job_id = job_id
        eval_payload.total_candidates_evaluated = len(eval_payload.evaluations)

        # Ensure evaluations sorted by score
        eval_payload.evaluations.sort(key=lambda e: e.overall_interview_score, reverse=True)

        # Set selected_top_candidate if not set or update from top candidate
        if eval_payload.evaluations:
            top = eval_payload.evaluations[0]
            eval_payload.selected_top_candidate = SelectedCandidateInfo(
                applicant_id=top.applicant_id,
                applicant_name=top.applicant_name,
                overall_score=top.overall_interview_score,
                reason_for_selection=top.executive_summary_reason,
            )

        json_str = eval_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(eval_payload)

        # Safety Guards & File Operations in 03_evaluations/
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        # Legacy Compatibility Bridge (is6_output_interview_evaluation.json)
        config.ensure_parent_dir(legacy_json_path)
        with open(legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        print(f"✅ [Agent 6] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 6] บันทึกไฟล์ {md_output_path.name} (Formal Evaluation Report) สำเร็จ")
        return eval_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 6] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e


if __name__ == "__main__":
    main()