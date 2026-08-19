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

# [NEW ARCHITECTURE] โหลดกุญแจจาก Root
load_dotenv(config.ENV_PATH) 
MY_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not MY_GEMINI_API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY not found!")
    sys.exit(1)

class InterviewPrep(BaseModel):
    applicant_name: str
    email_subject: str = Field(description="หัวข้ออีเมลเชิญสัมภาษณ์")
    email_body: str = Field(description="เนื้อหาอีเมล นัดวันเวลา และแจ้งรายละเอียดการสัมภาษณ์")
    custom_questions: List[str] = Field(description="คำถามสัมภาษณ์ 3-5 ข้อ ที่เจาะลึกตามจุดแข็ง/จุดอ่อนของผู้สมัคร")

class InterviewScheduleIS5(BaseModel):
    job_title: str
    action_items: List[InterviewPrep] = Field(description="รายการเตรียมสัมภาษณ์สำหรับผู้สมัครที่ผ่านเข้ารอบทุกคน")

class GeminiInterviewScheduler:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def schedule_interviews(self, is4_shortlist_data: str) -> InterviewScheduleIS5:
        system_instruction = (
            "คุณคือ Agent_5_Interview_Scheduler ประจำฝ่าย HR\n"
            "รับ 'รายชื่อผู้สมัครที่ผ่านเข้ารอบ (IS4)'\n"
            "1. ร่างอีเมลเชิญสัมภาษณ์ที่เป็นทางการ\n"
            "2. คิดคำถามสัมภาษณ์เฉพาะบุคคล (Personalized)"
        )
        prompt = f"ข้อมูลผู้สมัครที่ผ่านการคัดกรอง (IS4):\n{is4_shortlist_data}\n\nโปรดเตรียมการสัมภาษณ์ตาม Schema"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=InterviewScheduleIS5,
                temperature=0.4, 
            ),
        )
        return InterviewScheduleIS5.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 5] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    # [NEW ARCHITECTURE] ดึง IS4 จาก evaluations และคาย IS5 กลับไปที่ evaluations
    input_file = os.path.join(paths["evaluations"], "is4_output_candidate_scores.json")
    output_file = os.path.join(paths["evaluations"], "is5_output_interview_schedule.json")

    try:
        if not os.path.exists(input_file):
            print(f"⚠️ [Agent 5] ขัดข้อง: ไม่พบไฟล์ผลการคัดกรอง CV (is4) ใน Workspace {job_id}")
            sys.exit(1)

        with open(input_file, "r", encoding="utf-8") as f:
            is4_data = f.read()

        print(f"⚡ [Agent 5] เข้าสู่ Workspace: {job_id} กำลังเตรียมการสัมภาษณ์...")
        agent = GeminiInterviewScheduler(api_key=MY_GEMINI_API_KEY)
        is5_result = agent.schedule_interviews(is4_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is5_result.model_dump_json(indent=2))

        print(f"✅ [Agent 5] ร่างอีเมลและคำถามเสร็จสิ้น เซฟลงโฟลเดอร์ 03_evaluations")
        
        # ⚠️ ไม่ต้องเตะปลุก Agent 6 เพราะต้องรอให้การสัมภาษณ์เกิดขึ้นจริงก่อน (รอคนสัมภาษณ์จด Note)
        print(f"⏸️ [System] หยุดรอ... รอผู้สัมภาษณ์ป้อน Notes ใน 02_sourcing_dropzone เพื่อปลุก Agent 6 ในรอบถัดไป")
    except Exception as e:
        print(f"❌ [Agent 5] Error: {e}")
        sys.exit(1)