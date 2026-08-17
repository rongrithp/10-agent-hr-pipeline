import os
import sys
import json
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

MY_GEMINI_API_KEY = "AIzaSyDpFinTIgVB0g44Acu9TRjqEp6Nn-Wk1Ak"

# ==========================================
# Schema IS5 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic models for Interview Preparation...
class InterviewPrep(BaseModel):
    applicant_name: str
    email_subject: str = Field(description="หัวข้ออีเมลเชิญสัมภาษณ์")
    email_body: str = Field(description="เนื้อหาอีเมล นัดวันเวลา และแจ้งรายละเอียดการสัมภาษณ์")
    custom_questions: List[str] = Field(description="คำถามสัมภาษณ์ 3-5 ข้อ ที่เจาะลึกตามจุดแข็ง/จุดอ่อนของผู้สมัครคนนี้")

class InterviewScheduleIS5(BaseModel):
    job_title: str
    action_items: List[InterviewPrep] = Field(description="รายการเตรียมสัมภาษณ์สำหรับผู้สมัครที่ผ่านเข้ารอบทุกคน")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 5 Interview Scheduler...
class GeminiInterviewScheduler:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def schedule_interviews(self, is4_shortlist_data: str) -> InterviewScheduleIS5:
        system_instruction = (
            "คุณคือ Agent_5_Interview_Scheduler ประจำฝ่าย HR\n"
            "หน้าที่ของคุณคือรับ 'รายชื่อผู้สมัครที่ผ่านเข้ารอบ (IS4)' คัดเฉพาะคนที่สถานะเป็น 'SHORTLIST'\n"
            "1. ร่างอีเมลเชิญสัมภาษณ์ที่เป็นทางการและสุภาพ\n"
            "2. คิดคำถามสัมภาษณ์เฉพาะบุคคล (Personalized) โดยวิเคราะห์จากจุดแข็งและจุดอ่อนของเขาที่ส่งมา"
        )
        prompt = f"ข้อมูลผู้สมัครที่ผ่านการคัดกรอง (IS4):\n{is4_shortlist_data}\n\nโปรดเตรียมการสัมภาษณ์ตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=InterviewScheduleIS5,
                temperature=0.4, # ให้อุณหภูมินิดนึงเผื่อแต่งอีเมลและคำถามให้ไหลลื่น
            ),
        )
        return InterviewScheduleIS5.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_5_interview_scheduler.py <input_is4_file> <output_is5_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            is4_data = f.read()

        print(f"⚡ [Agent 5] กำลังเตรียมการสัมภาษณ์จากรายชื่อผู้ผ่านเข้ารอบ: {input_file} ...")
        agent = GeminiInterviewScheduler(api_key=MY_GEMINI_API_KEY)
        is5_result = agent.schedule_interviews(is4_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is5_result.model_dump_json(indent=2))

        print(f"✅ [Agent 5] Success! ร่างอีเมลและคำถามสัมภาษณ์เสร็จสิ้น คายประจุ IS5 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 5] Error: {e}", file=sys.stderr)
        sys.exit(1)