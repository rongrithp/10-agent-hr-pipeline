import os
import sys
import json
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# [Low-Level Actuator] บังคับท่อส่งข้อมูลให้เป็น UTF-8 ตั้งแต่บรรทัดแรก ป้องกัน Windows ระเบิด
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# โหลดข้อมูลอ้างอิงจากไฟล์ .env
load_dotenv() 

MY_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not MY_GEMINI_API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY not found! Please check your .env file.")
    sys.exit(1)    
# ==========================================
# Schema IS1 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic model for Job Description...
class JobDescription(BaseModel):
    job_title: str = Field(description="ชื่อตำแหน่งงานอย่างเป็นทางการ")
    department: str = Field(description="แผนกที่สังกัด")
    key_responsibilities: list[str] = Field(description="หน้าที่ความรับผิดชอบหลัก 3-5 ข้อ")
    must_have_skills: list[str] = Field(description="ทักษะที่จำเป็นต้องมี (Must have)")
    nice_to_have_skills: list[str] = Field(description="ทักษะที่เป็นข้อได้เปรียบ (Nice to have)")
    suggested_salary_range: str = Field(description="ช่วงเงินเดือนที่เหมาะสมอ้างอิงจากตลาด (บาท)")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 1...
class GeminiRequirementAnalyzer:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def analyze_request(self, raw_request: str) -> JobDescription:
        system_instruction = (
            "คุณคือ Agent_1_Requirement_Analyzer ฝ่าย HR มืออาชีพ\n"
            "หน้าที่ของคุณคือรับคำขอจ้างงาน (Hiring Request) แบบดิบๆ จากหัวหน้าแผนก\n"
            "นำมาวิเคราะห์ ตีความ และแปลงเป็น Job Description (JD) ที่เป็นทางการ ชัดเจน และมีโครงสร้างที่ดี"
        )
        
        prompt = f"นี่คือคำขอจ้างงานจากหัวหน้าแผนก:\n'{raw_request}'\n\nโปรดสร้าง Job Description ตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=JobDescription,
                temperature=0.2, # อุณหภูมิต่ำเพื่อให้ได้ข้อมูลที่แม่นยำ ไม่เพ้อเจ้อ
            ),
        )
        return JobDescription.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_1_requirement_analyzer.py <input_is0_file> <output_is1_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_request = f.read()

        print(f"⚡ [Agent 1] กำลังวิเคราะห์คำขอจ้างงานจาก: {input_file} ...")
        agent = GeminiRequirementAnalyzer(api_key=MY_GEMINI_API_KEY)
        is1_result = agent.analyze_request(raw_request)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is1_result.model_dump_json(indent=2))

        print(f"✅ [Agent 1] Success! สร้าง Job Description สำเร็จ คายประจุ IS1 ลงไฟล์: {output_file}")
    except Exception as e:
        print(f"❌ [Agent 1] Error: {e}")
        sys.exit(1)