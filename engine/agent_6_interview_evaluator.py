import os
import sys
import json
import subprocess
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config # [NEW ARCHITECTURE]

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH) 
MY_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not MY_GEMINI_API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY not found!")
    sys.exit(1)
    
class AssessmentScores(BaseModel):
    technical_skills: int = Field(description="คะแนนทักษะ (0-100)")
    communication: int = Field(description="คะแนนการสื่อสาร (0-100)")
    cultural_fit: int = Field(description="คะแนนวัฒนธรรมองค์กร (0-100)")

class InterviewResult(BaseModel):
    applicant_name: str
    scores: AssessmentScores
    interviewer_feedback_summary: str = Field(description="สรุปความคิดเห็นจากโน้ต")
    final_decision: str = Field(description="HIRE / REJECT / KEEPINVIEW")
    reason_for_decision: str = Field(description="เหตุผลหลักที่สนับสนุนการตัดสินใจ")

class InterviewEvaluationIS6(BaseModel):
    job_title: str
    evaluations: List[InterviewResult] = Field(description="ผลการประเมินผู้สมัครทุกคน")
    hired_candidate: Optional[str] = Field(description="ชื่อผู้สมัครที่ได้รับการคัดเลือก (ถ้ามี)", default=None)

class GeminiInterviewEvaluator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def evaluate(self, is1_jd_data: str, mock_notes: str) -> InterviewEvaluationIS6:
        system_instruction = (
            "คุณคือ Agent_6_Interview_Evaluator ประจำฝ่าย HR\n"
            "รับ 'เกณฑ์ (IS1)' และ 'บันทึกการสัมภาษณ์'\n"
            "มาวิเคราะห์ ให้คะแนนแยกหมวดหมู่ สรุปความเห็น และตัดสินใจ HIRE/REJECT"
        )
        prompt = f"เกณฑ์ที่ต้องการ (JD):\n{is1_jd_data}\n\nบันทึกจากการสัมภาษณ์:\n{mock_notes}\n\nโปรดตัดสินใจจ้างงานตาม Schema"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=InterviewEvaluationIS6,
                temperature=0.1,
            ),
        )
        return InterviewEvaluationIS6.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 6] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    jd_file = os.path.join(paths["specs"], "is1_output_job_description.txt")
    notes_file = os.path.join(paths["dropzone"], "mock_interview_notes.txt")
    output_file = os.path.join(paths["evaluations"], "is6_output_interview_evaluation.json")

    try:
        # ตรวจสอบไฟล์บันทึกสัมภาษณ์จาก dropzone ก่อน หรือเผื่อมีอยู่ใน specs
        if not os.path.exists(notes_file):
            fallback_notes = os.path.join(paths["specs"], "mock_interview_notes.txt")
            if os.path.exists(fallback_notes):
                notes_file = fallback_notes
            else:
                print(f"⚠️ [Agent 6] สแตนด์บาย: ไม่พบบันทึกการสัมภาษณ์ในโฟลเดอร์ 02_sourcing_dropzone ของ {job_id}")
                sys.exit(0)
            
        with open(jd_file, "r", encoding="utf-8") as f:
            is1_data = f.read()
            
        with open(notes_file, "r", encoding="utf-8") as f:
            notes_data = f.read()

        print(f"⚡ [Agent 6] เข้าสู่ Workspace: {job_id} กำลังประเมินผลสัมภาษณ์...")
        agent = GeminiInterviewEvaluator(api_key=MY_GEMINI_API_KEY)
        is6_result = agent.evaluate(is1_data, notes_data)

        # Safety Guard: สร้าง parent directory รองรับเสมอก่อนบันทึกไฟล์
        config.ensure_parent_dir(output_file)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is6_result.model_dump_json(indent=2))

        print(f"✅ [Agent 6] ประเมินผลและฟันธงเสร็จสิ้น เซฟลงโฟลเดอร์ 03_evaluations")
        
        # เตะปลุก Agent 7 ต่อทันทีแบบอัตโนมัติ
        print(f"🚀 [Agent 6] เตรียมเตะปลุก Agent 7 ตรวจสอบประวัติ...")
        next_agent = os.path.join(config.ENGINE_DIR, "agent_7_compliance_checker.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 6] Error: {e}")
        sys.exit(1)