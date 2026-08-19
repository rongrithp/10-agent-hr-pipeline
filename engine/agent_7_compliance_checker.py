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
    
class DocumentStatus(BaseModel):
    doc_type: str = Field(description="ประเภทเอกสาร เช่น บัตรประชาชน, Transcript")
    status: str = Field(description="สถานะ: PASS, MISSING, WARNING, REJECT")
    remark: Optional[str] = Field(default=None, description="หมายเหตุ")

class VerificationStatusIS7(BaseModel):
    applicant_name: str
    documents: List[DocumentStatus] = Field(description="รายการสถานะเอกสาร")
    overall_risk_assessment: str = Field(description="ประเมินความเสี่ยงโดยรวม")
    final_clearance: str = Field(description="สถานะเคลียร์ริ่ง: CLEARED, PENDING_DOCS, FLAG_FOR_REVIEW")
    action_required: str = Field(description="สิ่งที่ HR ต้องทำต่อไป")

class GeminiComplianceChecker:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def verify_documents(self, is6_evaluation: str, mock_docs: str) -> VerificationStatusIS7:
        system_instruction = (
            "คุณคือ Agent_7_Compliance_Checker ประจำฝ่าย HR\n"
            "รับ 'ผลตัดสิน (IS6)' และ 'รายการเอกสาร'\n"
            "ตรวจสอบความครบถ้วน ประเมินความเสี่ยง และสรุปว่าทำสัญญาจ้างได้หรือไม่"
        )
        prompt = f"ผลตัดสิน (IS6):\n{is6_evaluation}\n\nรายการเอกสารผู้สมัคร:\n{mock_docs}\n\nโปรดตรวจสอบเอกสารตาม Schema"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=VerificationStatusIS7,
                temperature=0.1,
            ),
        )
        return VerificationStatusIS7.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 7] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    is6_file = os.path.join(paths["evaluations"], "is6_output_interview_evaluation.json")
    docs_file = os.path.join(paths["dropzone"], "mock_documents.txt")
    output_file = os.path.join(paths["evaluations"], "is7_output_compliance_check.json")

    try:
        if not os.path.exists(is6_file):
            print(f"⚠️ [Agent 7] สแตนด์บาย: ไม่พบไฟล์ผลประเมิน IS6 ใน 03_evaluations")
            sys.exit(0)

        if not os.path.exists(docs_file):
            # สร้างข้อมูลจำลองเอกสารกรณีไม่มีไฟล์ใน dropzone
            docs_data = "Document Checklist:\n- ID Card: Verified\n- Educational Transcript: Verified\n- Criminal Record Check: Pending"
        else:
            with open(docs_file, "r", encoding="utf-8") as f:
                docs_data = f.read()

        with open(is6_file, "r", encoding="utf-8") as f:
            is6_data = f.read()

        print(f"⚡ [Agent 7] เข้าสู่ Workspace: {job_id} ตรวจสอบประวัติและเอกสาร...")
        agent = GeminiComplianceChecker(api_key=MY_GEMINI_API_KEY)
        is7_result = agent.verify_documents(is6_data, docs_data)

        # Safety Guard: สร้าง parent directory รองรับเสมอก่อนบันทึกไฟล์
        config.ensure_parent_dir(output_file)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is7_result.model_dump_json(indent=2))

        print(f"✅ [Agent 7] ตรวจเอกสารเสร็จสิ้น เซฟลงโฟลเดอร์ 03_evaluations")
        
        # ชี้เป้าให้ตรงกับชื่อไฟล์จริง agent_8_offer_negotiator.py
        print(f"🚀 [Agent 7] เตรียมเตะปลุก Agent 8 ร่างข้อเสนอจ้างงาน...")
        next_agent = os.path.join(config.ENGINE_DIR, "agent_8_offer_negotiator.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 7] Error: {e}")
        sys.exit(1)