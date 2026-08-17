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
# Schema IS8 (Output)
# ==========================================
class CompensationPackage(BaseModel):
    base_salary: int = Field(description="เงินเดือนพื้นฐานที่เสนอ (บาท)")
    allowances: List[str] = Field(default=[], description="ค่าตอบแทนพิเศษหรือสวัสดิการอื่นๆ (เช่น ค่าเดินทาง, โบนัส, WFH)")
    probation_period: int = Field(default=90, description="ระยะเวลาทดลองงาน (วัน)")

class OfferDetailsIS8(BaseModel):
    applicant_name: str
    proposed_package: CompensationPackage
    negotiation_strategy: str = Field(description="กลยุทธ์ในการต่อรอง เช่น 'เสนอเงินเดือนน้อยกว่าที่ขอเล็กน้อย แต่ชดเชยด้วยสวัสดิการ'")
    offer_letter_draft: str = Field(description="ร่างจดหมายเสนองาน (Offer Letter) ฉบับสมบูรณ์ พร้อมให้ผู้สมัครเซ็นตอบรับ")
    status: str = Field(description="สถานะ: OFFER_READY (พร้อมส่ง)")

# ==========================================
# Agent Class
# ==========================================
class GeminiOfferNegotiator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def negotiate_offer(self, is7_status: str, is1_jd: str, mock_cvs: str) -> OfferDetailsIS8:
        system_instruction = (
            "คุณคือ Agent_8_Offer_Negotiator ประจำระบบ HR\n"
            "หน้าที่ของคุณคือรับ 'สถานะการตรวจเอกสาร (IS7)', 'งบประมาณ/JD (IS1)' และ 'เรซูเม่ผู้สมัคร (Mock CVs)'\n"
            "มาวิเคราะห์เพื่อหาจุดกึ่งกลางระหว่างงบประมาณบริษัทและเงินเดือนที่ผู้สมัครคาดหวัง\n"
            "จากนั้นให้ร่างจดหมายเสนองาน (Offer Letter) ที่มีความเป็นมืออาชีพ โน้มน้าวใจ และมีตัวเลขชัดเจน"
        )
        
        prompt = f"สถานะผู้สมัคร (IS7):\n{is7_status}\n\nเกณฑ์และงบประมาณ (IS1):\n{is1_jd}\n\nข้อมูลผู้สมัคร/เงินเดือนที่ขอ (Mock CVs):\n{mock_cvs}\n\nโปรดร่างข้อเสนองานตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=OfferDetailsIS8,
                temperature=0.4, # เพิ่มอุณหภูมินิดนึงให้มันคิดกลยุทธ์ต่อรองเก่งขึ้น
            ),
        )
        return OfferDetailsIS8.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_8_offer_negotiator.py <input_is7_file> <output_is8_file>")
        sys.exit(1)

    input_file = sys.argv[1] 
    output_file = sys.argv[2]
    
    jd_file = "payloads/is1_job_description.json"
    cv_file = "payloads/mock_cv_batch.json"

    try:
        # อ่าน IS7 เพื่อดูว่าใครผ่าน
        with open(input_file, "r", encoding="utf-8") as f:
            is7_data = f.read()
            
        # อ่าน IS1 เพื่อดูงบ
        with open(jd_file, "r", encoding="utf-8") as f:
            is1_data = f.read()
            
        # อ่าน CV เพื่อดูเงินเดือนที่เขาขอ
        with open(cv_file, "r", encoding="utf-8") as f:
            cv_data = f.read()

        print(f"⚡ [Agent 8] กำลังคำนวณตัวเลขและร่าง Offer Letter...")
        agent = GeminiOfferNegotiator(api_key=MY_GEMINI_API_KEY)
        is8_result = agent.negotiate_offer(is7_data, is1_data, cv_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is8_result.model_dump_json(indent=2))

        print(f"✅ [Agent 8] Success! ร่าง Offer Letter เสร็จสิ้น คายประจุ IS8 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 8] Error: {e}", file=sys.stderr)
        sys.exit(1)