import os
import sys
import json
import subprocess
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
    
class ITSetup(BaseModel):
    email_created: str = Field(description="รูปแบบอีเมลองค์กร")
    hardware_assigned: List[str] = Field(description="อุปกรณ์ที่ต้องเตรียมให้")
    software_access: List[str] = Field(description="สิทธิ์การเข้าถึงระบบ")

class DayOneSchedule(BaseModel):
    time: str = Field(description="เวลา")
    activity: str = Field(description="กิจกรรม")
    person_in_charge: str = Field(description="ผู้รับผิดชอบ")

class OnboardingPlanIS9(BaseModel):
    employee_name: str
    job_title: str
    start_date: str = Field(description="วันที่เริ่มงาน")
    it_setup_checklist: ITSetup
    day_one_agenda: List[DayOneSchedule]
    welcome_email_draft: str = Field(description="ร่างอีเมลต้อนรับแนะนำตัวพนักงานใหม่")

class GeminiOnboardingPlanner:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def plan_onboarding(self, is8_offer_data: str) -> OnboardingPlanIS9:
        system_instruction = (
            "คุณคือ Agent_9_Onboarding_Planner ประจำระบบ HR\n"
            "รับ 'ข้อมูล Offer (IS8)' มาวางแผนรับพนักงานใหม่เข้าทำงาน เตรียม IT จัดตารางวันแรก และร่างอีเมลแนะนำตัว"
        )
        prompt = f"ข้อมูลข้อเสนองานที่ตกลงแล้ว (IS8):\n{is8_offer_data}\n\nโปรดจัดทำแผน Onboarding ตาม Schema"

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 9] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    # [NEW ARCHITECTURE] ดึง IS8 จาก offers, เซฟผลลง onboarding
    input_file = os.path.join(paths["offers"], "is8_output_offer_details.json")
    output_file = os.path.join(paths["onboarding"], "is9_output_onboarding_plan.json")

    try:
        if not os.path.exists(input_file):
            print(f"⚠️ [Agent 9] สแตนด์บาย: ไม่พบไฟล์ IS8 ใน 04_offers_contracts")
            sys.exit(0)

        with open(input_file, "r", encoding="utf-8") as f:
            is8_data = f.read()

        print(f"⚡ [Agent 9] เข้าสู่ Workspace: {job_id} กำลังวางแผน Onboarding...")
        agent = GeminiOnboardingPlanner(api_key=MY_GEMINI_API_KEY)
        is9_result = agent.plan_onboarding(is8_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is9_result.model_dump_json(indent=2))

        print(f"✅ [Agent 9] วางแผนรับน้องใหม่เสร็จสิ้น เซฟลงโฟลเดอร์ 05_onboarding_vault")
        
        # [NEW ARCHITECTURE] เตะปลุก Agent 10 ตัวสุดท้าย
        print(f"🚀 [Agent 9] เตรียมเตะปลุก Agent 10 สรุปโปรไฟล์พนักงาน...")
        next_agent = os.path.join(config.ENGINE_DIR, "agent_10_talent_profiler.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 9] Error: {e}")
        sys.exit(1)