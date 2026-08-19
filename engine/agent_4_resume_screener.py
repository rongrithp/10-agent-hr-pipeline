import os
import sys
import json
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys
import os
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
    
class CandidateScore(BaseModel):
    applicant_id: str
    applicant_name: str
    match_score: int = Field(description="คะแนนความเหมาะสม 0-100")
    strengths: List[str] = Field(description="จุดแข็งที่ตรงกับสเปก")
    weaknesses: List[str] = Field(description="จุดอ่อนหรือข้อควรระวัง")
    recommendation: str = Field(description="คำแนะนำ: เชิญสัมภาษณ์ / สำรอง / ปฏิเสธ")

class ScreeningResultIS4(BaseModel):
    job_code: str
    top_candidates: List[CandidateScore] = Field(description="รายชื่อผู้สมัครที่ผ่านการคัดกรอง เรียงตามคะแนน")

class GeminiResumeScreener:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def screen_resumes(self, jd_criteria: str, mock_cv_data: str) -> ScreeningResultIS4:
        system_instruction = (
            "คุณคือ Agent_4_Resume_Screener ประจำระบบ HR\n"
            "รับ 'Job Description (IS1)' และ 'ข้อมูลเรซูเม่ผู้สมัคร'\n"
            "มาวิเคราะห์ ให้คะแนนความเหมาะสม ตัดสินใจตามงบประมาณและทักษะที่ต้องการ"
        )
        prompt = f"เกณฑ์ที่ต้องการ (IS1):\n{jd_criteria}\n\nรายชื่อผู้สมัคร:\n{mock_cv_data}"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ScreeningResultIS4,
                temperature=0.1,
            ),
        )
        return ScreeningResultIS4.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 4] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    # [NEW ARCHITECTURE] ดึง JD จาก specs และ CV จาก dropzone
    jd_file = os.path.join(paths["specs"], "is1_output_job_description.txt")
    resumes_file = os.path.join(paths["dropzone"], "mock_cv_batch.json")
    output_file = os.path.join(paths["evaluations"], "is4_output_candidate_scores.json")

    try:
        # ระบบป้องกันภัย (Predictive Risk Mitigation)
        if not os.path.exists(resumes_file):
            print(f"⚠️ [Agent 4] สแตนด์บาย: ยังไม่มีไฟล์เรซูเม่ (mock_cv_batch.json) ในโฟลเดอร์ 02_sourcing_dropzone ของ {job_id}")
            sys.exit(0)

        with open(jd_file, "r", encoding="utf-8") as f:
            is1_data = f.read()
            
        with open(resumes_file, "r", encoding="utf-8") as f:
            resumes_data = f.read()

        print(f"⚡ [Agent 4] โหลด CV ของ {job_id} เสร็จสิ้น กำลังคัดกรอง...")
        agent = GeminiResumeScreener(api_key=MY_GEMINI_API_KEY)
        is4_result = agent.screen_resumes(is1_data, resumes_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is4_result.model_dump_json(indent=2))

        print(f"✅ [Agent 4] คัดกรองเรซูเม่เสร็จสิ้น เซฟลงโฟลเดอร์ 03_evaluations")
    except Exception as e:
        print(f"❌ [Agent 4] Error: {e}")
        sys.exit(1)