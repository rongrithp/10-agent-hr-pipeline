import os
import sys
import json
import subprocess
from typing import List
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
    print("❌ [Agent 5] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Tailored Interview Planning ---

class InterviewSession(BaseModel):
    date_time: str = Field(description="วันและเวลาสัมภาษณ์ (Scheduled Date & Time)")
    format: str = Field(description="รูปแบบการสัมภาษณ์ (Google Meet / On-site Campus)")
    panel_members: List[str] = Field(description="คณะกรรมการผู้สัมภาษณ์ (Interview Panel)")
    duration_minutes: int = Field(default=60, description="ระยะเวลาสัมภาษณ์ (นาที)")


class TailoredQuestionItem(BaseModel):
    focus_topic: str = Field(description="หัวข้อเจาะจงเฉพาะตัวบุคคล")
    question: str = Field(description="คำถามสัมภาษณ์เจาะลึกเฉพาะตัวบุคคล")
    target_response_guideline: str = Field(description="แนวทางการประเมินคำตอบที่ดี (Expected Answer Indicators)")


class CoreCompetencyQuestion(BaseModel):
    competency: str = Field(description="ทักษะหลัก/สมรรถนะที่ต้องการวัด (Core Competency)")
    star_question: str = Field(description="คำถามตามแนวทาง STAR Technique (Situation, Task, Action, Result)")
    star_eval_criteria: str = Field(description="เกณฑ์การประเมินองค์ประกอบ STAR")


class RubricItem(BaseModel):
    category: str = Field(description="หมวดหมู่เกณฑ์การประเมิน")
    weight_percentage: int = Field(description="น้ำหนักคะแนน (%)")
    scale_1_poor: str = Field(description="คำอธิบายคะแนน 1 (Unsatisfactory)")
    scale_3_competent: str = Field(description="คำอธิบายคะแนน 3 (Competent / Meets Standard)")
    scale_5_exceptional: str = Field(description="คำอธิบายคะแนน 5 (Exceptional / Outstanding)")


class CandidateInterviewPlan(BaseModel):
    applicant_id: str = Field(description="รหัสผู้สมัคร")
    applicant_name: str = Field(description="ชื่อ-นามสกุล ผู้สมัคร")
    current_role: str = Field(description="ตำแหน่งงานปัจจุบัน")
    interview_session: InterviewSession = Field(description="1. รายละเอียดเซสชันการสัมภาษณ์ (Schedule & Format)")
    tailored_question_set: List[TailoredQuestionItem] = Field(description="2. ชุดคำถามเจาะจงเฉพาะตัวบุคคล (Tailored Questions)")
    core_competency_questions: List[CoreCompetencyQuestion] = Field(description="3. คำถามวัดทักษะหลัก STAR Technique")
    evaluation_rubric: List[RubricItem] = Field(description="4. เกณฑ์การประเมิน 1-5 คะแนน (Evaluation Rubric)")


class InterviewSchedulePayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน")
    qualified_candidates_count: int = Field(description="จำนวนผู้สมัครที่ได้รับการเตรียมแผนสัมภาษณ์")
    candidate_interview_plans: List[CandidateInterviewPlan] = Field(
        description="แผนและคู่มือการสัมภาษณ์แยกตามผู้สมัครแต่ละคน"
    )


def format_formal_markdown(payload: InterviewSchedulePayload) -> str:
    """แปลงคู่มือและตารางเตรียมสัมภาษณ์เป็นเอกสาร Markdown ทางการ สวยงามระดับ Executive Guide"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    candidate_guides = []
    for idx, plan in enumerate(payload.candidate_interview_plans, start=1):
        sess = plan.interview_session
        panel_str = ", ".join(sess.panel_members)

        # Tailored Questions table
        tailored_rows = "\n".join([
            f"| **{tq.focus_topic}** | {tq.question} | {tq.target_response_guideline} |"
            for tq in plan.tailored_question_set
        ])

        # STAR Competency Questions table
        star_rows = "\n".join([
            f"| **{cq.competency}** | {cq.star_question} | {cq.star_eval_criteria} |"
            for cq in plan.core_competency_questions
        ])

        # Rubric table
        rubric_rows = "\n".join([
            f"| **{rb.category}** | {rb.weight_percentage}% | {rb.scale_1_poor} | {rb.scale_3_competent} | {rb.scale_5_exceptional} | `[   ]` |"
            for rb in plan.evaluation_rubric
        ])

        candidate_guides.append(f"""### 👤 Candidate {idx}: {plan.applicant_name} (`{plan.applicant_id}`)

#### 📅 1. Session Logistics & Panel Info
| Parameter | Details |
| :--- | :--- |
| **Candidate Name** | **{plan.applicant_name}** |
| **Current Role** | {plan.current_role} |
| **Date & Time** | {sess.date_time} |
| **Format & Venue** | {sess.format} |
| **Panel Members** | {panel_str} |
| **Duration** | {sess.duration_minutes} Minutes |

---

#### 🎯 2. Tailored Personal Questions (Based on Screening Focus)

| Focus Topic | Question for Candidate | Expected Answer Indicators / Evaluation Notes |
| :--- | :--- | :--- |
{tailored_rows}

---

#### 🧠 3. Core Competency Questions (STAR Technique)

| Competency | STAR Behavioral Question | Evaluation & STAR Guidelines |
| :--- | :--- | :--- |
{star_rows}

---

#### ⚖️ 4. Candidate Evaluation Rubric (1 – 5 Scale)

| Evaluation Category | Weight | 1 - Unsatisfactory | 3 - Competent (Meets Standard) | 5 - Exceptional | Score (1-5) |
| :--- | :---: | :--- | :--- | :--- | :---: |
{rubric_rows}

**Total Weighted Score:** _____ / 100%  
**Interviewer Signature:** ___________________________ **Date:** ______________
""")

    guides_text = "\n---\n\n".join(candidate_guides)

    return f"""# 📋 FORMAL INTERVIEW GUIDE & EVALUATION RUBRIC

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{payload.job_id}`  
> **Target Position:** **{payload.position_title}**  
> **Document Status:** Official Interview Prep Guide  
> **Date Generated:** {today_str}  

---

## 📈 Qualified Candidates Overview

- **Position Title:** {payload.position_title}
- **Total Shortlisted Candidates (`QUALIFIED_FOR_INTERVIEW`):** {payload.qualified_candidates_count} Candidate(s)

---

## 👤 CANDIDATE INTERVIEW GUIDES

{guides_text}

---

> *This Formal Interview Guide was generated automatically by Agent 5 (Tailored Interview Planner & Guide Generator).*  
> *Authorized for Panel Interviewers and Hiring Managers.*
"""


def main():
    if len(sys.argv) < 2:
        print("❌ [Agent 5] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    evaluations_dir = Path(paths["evaluations"])

    # Output Paths
    json_output_path = evaluations_dir / "is5_output_interview_schedule.json"
    md_output_path = evaluations_dir / "is5_interview_guide_formal.md"

    print(f"🚀 [Agent 5] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Read IS4 Screening Results
    is4_json_path = evaluations_dir / "is4_output_screening_results.json"
    is4_legacy_path = evaluations_dir / "is4_output_candidate_scores.json"

    is4_data_str = ""
    if is4_json_path.exists():
        with open(is4_json_path, "r", encoding="utf-8") as f:
            is4_data_str = f.read()
        print(f"📄 [Agent 5] อ่านข้อมูลการคัดกรองจาก {is4_json_path.name} สำเร็จ")
    elif is4_legacy_path.exists():
        with open(is4_legacy_path, "r", encoding="utf-8") as f:
            is4_data_str = f.read()
        print(f"📄 [Agent 5] อ่านข้อมูลการคัดกรองจาก {is4_legacy_path.name} สำเร็จ")
    else:
        print(f"❌ [Agent 5] ขัดข้อง: ไม่พบไฟล์ผลการคัดกรองเรซูเม่ (is4) ใน {evaluations_dir}")
        sys.exit(1)

    # Read JD Context for Job Info
    jd_json_path = specs_dir / "is1_output_job_description.json"
    jd_txt_path = specs_dir / "is1_output_job_description.txt"

    jd_context_str = ""
    if jd_json_path.exists():
        with open(jd_json_path, "r", encoding="utf-8") as f:
            jd_context_str = f.read()
    elif jd_txt_path.exists():
        with open(jd_txt_path, "r", encoding="utf-8") as f:
            jd_context_str = f.read()

    # Filter qualified candidates check
    try:
        is4_data = json.loads(is4_data_str)
        qualified_candidates = []
        if "candidates" in is4_data:
            qualified_candidates = [c for c in is4_data["candidates"] if c.get("decision") == "QUALIFIED_FOR_INTERVIEW"]
        elif "top_candidates" in is4_data:
            qualified_candidates = is4_data["top_candidates"]

        if not qualified_candidates:
            print(f"⚠️ [Agent 5] สแตนด์บาย: ไม่พบผู้สมัครที่ผ่านเกณฑ์ QUALIFIED_FOR_INTERVIEW ใน Workspace {job_id}")
            sys.exit(0)
    except Exception as parse_err:
        print(f"⚠️ [Agent 5] คำเตือน: ไม่สามารถพาร์ส IS4 เพื่อกรองผู้สมัครก่อนส่ง LLM: {parse_err}")

    system_instruction = (
        "คุณคือ Agent 5 (Tailored Interview Planner & Guide Generator)\n"
        "หน้าที่ของคุณคือการจัดเตรียมแผนและคู่มือการสัมภาษณ์เชิงลึกเฉพาะบุคคลสำหรับผู้สมัครที่ผ่านเกณฑ์ (QUALIFIED_FOR_INTERVIEW) เท่านั้น\n"
        "โครงสร้างคู่มือการสัมภาษณ์สำหรับผู้สมัครแต่ละคนต้องประกอบด้วย 4 ส่วนสำคัญ:\n"
        "1. interview_session: กำหนดวัน/เวลา, รูปแบบ (Google Meet / On-site), คณะกรรมการสัมภาษณ์ (Panel Members), และระยะเวลา\n"
        "2. tailored_question_set: ชุดคำถามเจาะจงเฉพาะตัวบุคคลตาม recommended_interview_focus ของ Agent 4 พร้อมแนวทางการประเมินคำตอบที่ดี\n"
        "3. core_competency_questions: คำถามวัดทักษะหลักและ Culture Fit ตามแนวทาง STAR Technique (Situation, Task, Action, Result) พร้อมเกณฑ์ประเมิน\n"
        "4. evaluation_rubric: เกณฑ์การประเมิน 1-5 คะแนน (Unsatisfactory, Competent, Exceptional) พร้อมระบุน้ำหนักคะแนน (%) รวม 100%\n\n"
        "โปรดสร้างคู่มือการสัมภาษณ์ที่เข้มข้น มีความเป็นมืออาชีพสูง และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลบริบทตำแหน่งงาน (Job Description):
{jd_context_str}

ข้อมูลผลการคัดกรองเรซูเม่ (IS4 Results - QUALIFIED Candidates Only):
{is4_data_str}

กรุณาสร้างแผนและคู่มือการสัมภาษณ์เชิงลึกสำหรับผู้สมัครทุกคนที่ผ่านเกณฑ์ QUALIFIED_FOR_INTERVIEW บันทึกลงใน Schema ให้ครบถ้วนสมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=InterviewSchedulePayload,
                temperature=0.3,
            ),
        )

        schedule_payload = InterviewSchedulePayload.model_validate_json(response.text)
        schedule_payload.job_id = job_id
        schedule_payload.qualified_candidates_count = len(schedule_payload.candidate_interview_plans)

        json_str = schedule_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(schedule_payload)

        # Safety Guards & File Operations
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        print(f"✅ [Agent 5] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 5] บันทึกไฟล์ {md_output_path.name} (Formal Interview Guide) สำเร็จ")

    except Exception as e:
        print(f"❌ [Agent 5] ระบบสมองประมวลผลล้มเหลว: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()