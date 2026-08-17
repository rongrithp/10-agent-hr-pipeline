import os
import sys
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# [Low-Level Actuator] บังคับท่อส่งข้อมูลให้เป็น UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# โหลดข้อมูลอ้างอิงจากไฟล์ .env
load_dotenv() 

MY_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not MY_GEMINI_API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY not found! Please check your .env file.")
    sys.exit(1)
    
    
# ==========================================
# Schema IS9 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic models for Onboarding Plan...
class ITSetup(BaseModel):
    email_created: str = Field(description="รูปแบบอีเมลองค์กรที่จะสร้างให้พนักงานใหม่ (เช่น somchai.c@company.com)")
    hardware_assigned: List[str] = Field(description="อุปกรณ์ที่ต้องเตรียมให้ เช่น Laptop, โทรศัพท์, จอเสริม")
    software_access: List[str] = Field(description="สิทธิ์การเข้าถึงระบบที่จำเป็นตามตำแหน่งงาน (เช่น GitHub, AWS, Slack)")

class DayOneSchedule(BaseModel):
    time: str = Field(description="เวลา เช่น '09:00 - 10:00'")
    activity: str = Field(description="กิจกรรม เช่น 'ปฐมนิเทศกับ HR', 'รับอุปกรณ์ IT', 'ทานข้าวเที่ยงกับทีม'")
    person_in_charge: str = Field(description="ผู้รับผิดชอบหรือผู้ดูแลกิจกรรมนั้น")

class OnboardingPlanIS9(BaseModel):
    employee_name: str
    job_title: str
    start_date: str = Field(description="วันที่เริ่มงาน (สมมติว่าเป็นวันจันทร์หน้า)")
    it_setup_checklist: ITSetup
    day_one_agenda: List[DayOneSchedule]
    welcome_email_draft: str = Field(description="ร่างอีเมลต้อนรับ ส่งให้พนักงานทุกคนในองค์กรเพื่อแนะนำตัวพนักงานใหม่แบบเป็นกันเอง")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 9 Onboarding Planner...
class GeminiOnboardingPlanner:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def plan_onboarding(self, is8_offer_data: str) -> OnboardingPlanIS9:
        system_instruction = (
            "คุณคือ Agent_9_Onboarding_Planner ประจำระบบ HR\n"
            "หน้าที่ของคุณคือรับ 'ข้อมูล Offer Letter ที่ตอบรับแล้ว (IS8)'\n"
            "มาวางแผนการรับพนักงานใหม่เข้าทำงาน (Onboarding) โดยวิเคราะห์จากตำแหน่งงานของเขา เพื่อเตรียมรายการอุปกรณ์ IT ที่เหมาะสม, "
            "จัดตารางเวลาวันแรกให้ราบรื่น และร่างอีเมลแนะนำตัวพนักงานใหม่ให้คนทั้งบริษัททราบ"
        )
        prompt = f"ข้อมูลข้อเสนองานที่ตกลงแล้ว (IS8):\n{is8_offer_data}\n\nโปรดจัดทำแผน Onboarding ตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=OnboardingPlanIS9,
                temperature=0.4,
            ),
        )
        return OnboardingPlanIS9.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_9_onboarding_planner.py <input_is8_file> <output_is9_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            is8_data = f.read()

        print(f"⚡ [Agent 9] กำลังวางแผน Onboarding จาก Offer: {input_file} ...")
        agent = GeminiOnboardingPlanner(api_key=MY_GEMINI_API_KEY)
        is9_result = agent.plan_onboarding(is8_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is9_result.model_dump_json(indent=2))

        print(f"✅ [Agent 9] Success! วางแผนรับน้องใหม่เสร็จสิ้น คายประจุ IS9 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 9] Error: {e}", file=sys.stderr)
        sys.exit(1)