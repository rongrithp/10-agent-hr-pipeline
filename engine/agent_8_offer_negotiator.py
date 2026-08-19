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
    
class CompensationPackage(BaseModel):
    base_salary: int = Field(description="เงินเดือนพื้นฐานที่เสนอ (บาท)")
    allowances: List[str] = Field(default=[], description="ค่าตอบแทนพิเศษหรือสวัสดิการอื่นๆ")
    probation_period: int = Field(default=90, description="ระยะเวลาทดลองงาน (วัน)")

class OfferDetailsIS8(BaseModel):
    applicant_name: str
    proposed_package: CompensationPackage
    negotiation_strategy: str = Field(description="กลยุทธ์ในการต่อรอง")
    offer_letter_draft: str = Field(description="ร่างจดหมายเสนองาน (Offer Letter) ฉบับสมบูรณ์")
    status: str = Field(description="สถานะ: OFFER_READY (พร้อมส่ง)")

class GeminiOfferNegotiator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def negotiate_offer(self, is7_status: str, is1_jd: str, mock_cvs: str) -> OfferDetailsIS8:
        system_instruction = (
            "คุณคือ Agent_8_Offer_Negotiator ประจำระบบ HR\n"
            "รับ 'สถานะตรวจเอกสาร (IS7)', 'งบ/JD (IS1)' และ 'เรซูเม่ (Mock CVs)'\n"
            "มาวิเคราะห์เพื่อหาจุดกึ่งกลางระหว่างงบประมาณและเงินเดือนที่ผู้สมัครคาดหวัง จากนั้นร่าง Offer Letter"
        )
        prompt = f"สถานะผู้สมัคร (IS7):\n{is7_status}\n\nเกณฑ์และงบประมาณ (IS1):\n{is1_jd}\n\nข้อมูลผู้สมัคร/เงินเดือนที่ขอ (Mock CVs):\n{mock_cvs}\n\nโปรดร่างข้อเสนองานตาม Schema"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=OfferDetailsIS8,
                temperature=0.4, 
            ),
        )
        return OfferDetailsIS8.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 8] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    # [NEW ARCHITECTURE] ดึงข้อมูลจากโซนย่อยตาม Lifecycle
    is7_file = os.path.join(paths["evaluations"], "is7_output_compliance_check.json")
    jd_file = os.path.join(paths["specs"], "is1_output_job_description.txt")
    cv_file = os.path.join(paths["dropzone"], "mock_cv_batch.json")
    output_file = os.path.join(paths["offers"], "is8_output_offer_details.json")

    try:
        if not os.path.exists(is7_file):
            print(f"⚠️ [Agent 8] สแตนด์บาย: ขาดไฟล์ IS7 ใน 03_evaluations")
            sys.exit(0)

        with open(is7_file, "r", encoding="utf-8") as f:
            is7_data = f.read()
        with open(jd_file, "r", encoding="utf-8") as f:
            is1_data = f.read()
        with open(cv_file, "r", encoding="utf-8") as f:
            cv_data = f.read()

        print(f"⚡ [Agent 8] เข้าสู่ Workspace: {job_id} กำลังคำนวณตัวเลขและร่าง Offer...")
        agent = GeminiOfferNegotiator(api_key=MY_GEMINI_API_KEY)
        is8_result = agent.negotiate_offer(is7_data, is1_data, cv_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is8_result.model_dump_json(indent=2))

        print(f"✅ [Agent 8] ร่าง Offer Letter เสร็จสิ้น เซฟลงโฟลเดอร์ 04_offers_contracts")
        
        # [NEW ARCHITECTURE] เตะปลุก Agent 9 ให้วางแผนรับพนักงานต่อ
        print(f"🚀 [Agent 8] เตรียมเตะปลุก Agent 9 วางแผน Onboarding...")
        next_agent = os.path.join(config.ENGINE_DIR, "agent_9_onboarding_planner.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 8] Error: {e}")
        sys.exit(1)