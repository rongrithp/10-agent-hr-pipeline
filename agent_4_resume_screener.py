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
class CandidateScore(BaseModel):
    applicant_id: str
    applicant_name: str
    match_score: int = Field(description="คะแนนความเหมาะสม 0-100")
    strengths: List[str] = Field(description="จุดแข็งที่ตรงกับสเปก")
    weaknesses: List[str] = Field(description="จุดอ่อนหรือข้อควรระวัง")
    recommendation: str = Field(description="คำแนะนำ: เชิญสัมภาษณ์ / สำรอง / ปฏิเสธ")

class ScreeningResultIS5(BaseModel):
    job_code: str
    top_candidates: List[CandidateScore] = Field(description="รายชื่อผู้สมัครที่ผ่านการคัดกรอง เรียงตามคะแนนจากมากไปน้อย")

# ==========================================
# Agent Class
# ==========================================
class GeminiResumeScreener:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def screen_resumes(self, is2_criteria: str, mock_cv_data: str) -> ScreeningResultIS5:
        system_instruction = (
            "คุณคือ Agent_4_Resume_Screener ประจำระบบ HR\n"
            "หน้าที่ของคุณคือรับ 'เกณฑ์การรับสมัคร (IS2)' และ 'ข้อมูลเรซูเม่ผู้สมัคร (Mock CVs)'\n"
            "มาวิเคราะห์ ให้คะแนนความเหมาะสม (0-100) สกัดจุดแข็ง-จุดอ่อน "
            "และแนะนำว่าควรเรียกสัมภาษณ์หรือไม่ ตัดสินใจอย่างเด็ดขาดตามงบประมาณและทักษะที่ต้องการ"
        )
        prompt = f"เกณฑ์ที่ต้องการ (IS2):\n{is2_criteria}\n\nรายชื่อผู้สมัคร:\n{mock_cv_data}"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ScreeningResultIS5,
                temperature=0.1,
            ),
        )
        return ScreeningResultIS5.model_validate_json(response.text)


# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O with multiple inputs...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_4_resume_screener.py <input_is3_file> <output_is4_file>")
        sys.exit(1)

    # หมายเหตุ: Orchestrator ส่ง IS3 มาเป็น input_file เพื่อบอกว่า Stage 3 เสร็จแล้ว
    # แต่จริงๆ แล้ว Agent 4 ต้องการ IS1 (JD) และ Mock Resumes ในการทำงาน
    input_is3_trigger = sys.argv[1] 
    output_file = sys.argv[2]
    
    jd_file = "payloads/is1_job_description.json"
    resumes_file = "payloads/mock_cv_batch.json"

    try:
        # อ่านไฟล์ JD (IS1)
        with open(jd_file, "r", encoding="utf-8") as f:
            is1_data = f.read()
            
        # อ่านไฟล์ Resumes
        with open(resumes_file, "r", encoding="utf-8") as f:
            resumes_data = f.read()

        print(f"⚡ [Agent 4] กำลังคัดกรองเรซูเม่ โดยอิงเกณฑ์จาก: {jd_file} ...")
        agent = GeminiResumeScreener(api_key=MY_GEMINI_API_KEY)
        is4_result = agent.screen_resumes(is1_data, resumes_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is4_result.model_dump_json(indent=2))

        print(f"✅ [Agent 4] Success! คัดกรองเรซูเม่เสร็จสิ้น คายประจุ IS4 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 4] Error: {e}", file=sys.stderr)
        sys.exit(1)