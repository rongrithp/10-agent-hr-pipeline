import os
import sys
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

MY_GEMINI_API_KEY = "AIzaSyDpFinTIgVB0g44Acu9TRjqEp6Nn-Wk1Ak"

# ==========================================
# Schema IS7 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic models for Compliance Check...
class DocumentStatus(BaseModel):
    doc_type: str = Field(description="ประเภทเอกสาร เช่น บัตรประชาชน, Transcript, ตรวจประวัติอาชญากรรม")
    status: str = Field(description="สถานะ: PASS (ผ่าน), MISSING (ขาด), WARNING (มีข้อควรระวัง), REJECT (ไม่ผ่าน/เอกสารปลอม)")
    remark: Optional[str] = Field(default=None, description="หมายเหตุ เช่น สาเหตุที่ไม่ผ่าน หรือสิ่งที่ต้องติดตาม")

class VerificationStatusIS7(BaseModel):
    applicant_name: str
    documents: List[DocumentStatus] = Field(description="รายการสถานะเอกสารแต่ละชิ้น")
    overall_risk_assessment: str = Field(description="ประเมินความเสี่ยงโดยรวม (เช่น มีประวัติอาชญากรรมร้ายแรงไหม หรือแค่เรื่องเล็กน้อย)")
    final_clearance: str = Field(description="สถานะเคลียร์ริ่ง: CLEARED (ผ่าน), PENDING_DOCS (รอเอกสาร), FLAG_FOR_REVIEW (ต้องให้ผู้บริหารพิจารณาความเสี่ยง)")
    action_required: str = Field(description="สิ่งที่ HR ต้องทำต่อไป เช่น ตามเอกสาร, นัดคุยเรื่องประวัติ")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 7 Compliance Checker...
class GeminiComplianceChecker:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def verify_documents(self, is6_evaluation: str, mock_docs: str) -> VerificationStatusIS7:
        system_instruction = (
            "คุณคือ Agent_7_Compliance_Checker ประจำฝ่าย HR\n"
            "หน้าที่ของคุณคือรับ 'ผลการตัดสินใจจ้าง (IS6)' และ 'บันทึกรายการเอกสาร (Mock Docs)' ของผู้สมัครที่ผ่านการคัดเลือก\n"
            "มาตรวจสอบความครบถ้วน ประเมินความเสี่ยงจากประวัติ (เช่น อาชญากรรม) และสรุปว่าผู้สมัครคนนี้พร้อมสำหรับการทำสัญญาจ้าง (Offer) หรือไม่"
        )
        
        # ส่ง IS6 เพื่อให้รู้ว่าตรวจใคร และส่ง Mock Docs ให้ตรวจ
        prompt = f"ผลการตัดสินใจจ้าง (IS6):\n{is6_evaluation}\n\nบันทึกรายการเอกสารของผู้สมัคร:\n{mock_docs}\n\nโปรดตรวจสอบเอกสารและประเมินความเสี่ยงตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=VerificationStatusIS7,
                temperature=0.1, # ต้องการความแม่นยำสูง ไม่เพ้อเจ้อ
            ),
        )
        return VerificationStatusIS7.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O with multiple inputs...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_7_compliance_checker.py <input_is6_trigger> <output_is7_file>")
        sys.exit(1)

    input_trigger = sys.argv[1] 
    output_file = sys.argv[2]
    
    docs_file = "payloads/mock_documents.txt"

    try:
        # อ่าน IS6 (รู้ว่าใครได้ HIRE)
        with open(input_trigger, "r", encoding="utf-8") as f:
            is6_data = f.read()
            
        # อ่าน Mock Docs
        with open(docs_file, "r", encoding="utf-8") as f:
            docs_data = f.read()

        print(f"⚡ [Agent 7] กำลังตรวจสอบประวัติและเอกสารจาก: {docs_file} ...")
        agent = GeminiComplianceChecker(api_key=MY_GEMINI_API_KEY)
        is7_result = agent.verify_documents(is6_data, docs_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is7_result.model_dump_json(indent=2))

        print(f"✅ [Agent 7] Success! ตรวจเอกสารเสร็จสิ้น คายประจุ IS7 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 7] Error: {e}", file=sys.stderr)
        sys.exit(1)