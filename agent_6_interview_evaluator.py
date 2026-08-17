import os
import sys
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

MY_GEMINI_API_KEY = "AIzaSyDpFinTIgVB0g44Acu9TRjqEp6Nn-Wk1Ak"

# ==========================================
# Schema IS6 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic models for Interview Evaluation...
class AssessmentScores(BaseModel):
    technical_skills: int = Field(description="คะแนนทักษะสายอาชีพ/เทคนิค (0-100)")
    communication: int = Field(description="คะแนนทักษะการสื่อสาร/การสอน (0-100)")
    cultural_fit: int = Field(description="คะแนนความเข้ากันได้กับนโยบายและวัฒนธรรมองค์กร (0-100)")

class InterviewResult(BaseModel):
    applicant_name: str
    scores: AssessmentScores
    interviewer_feedback_summary: str = Field(description="สรุปความคิดเห็นจากโน้ตการสัมภาษณ์")
    final_decision: str = Field(description="การตัดสินใจ: HIRE (รับเข้าทำงาน), REJECT (ปฏิเสธ), KEEPINVIEW (เก็บไว้พิจารณา)")
    reason_for_decision: str = Field(description="เหตุผลหลักที่สนับสนุนการตัดสินใจนี้")

class InterviewEvaluationIS6(BaseModel):
    job_title: str
    evaluations: List[InterviewResult] = Field(description="ผลการประเมินผู้สมัครทุกคนที่เข้ารับการสัมภาษณ์")
    hired_candidate: Optional[str] = Field(description="ชื่อผู้สมัครที่ได้รับการคัดเลือกให้ไปต่อ (ถ้ามี)", default=None)

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 6 Interview Evaluator...
class GeminiInterviewEvaluator:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def evaluate(self, is1_jd_data: str, mock_notes: str) -> InterviewEvaluationIS6:
        system_instruction = (
            "คุณคือ Agent_6_Interview_Evaluator ประจำฝ่าย HR\n"
            "หน้าที่ของคุณคือรับ 'เกณฑ์ความต้องการ (IS1)' และ 'บันทึกการสัมภาษณ์ (Mock Notes)'\n"
            "มาวิเคราะห์ ให้คะแนนแยกตามหมวดหมู่ (เทคนิค, สื่อสาร, วัฒนธรรม) สรุปความเห็น และทำการ 'ตัดสินใจขั้นเด็ดขาด' (HIRE/REJECT) ว่าจะรับใครเข้าทำงาน"
        )
        # ส่ง JD เป็นเกณฑ์ และ Note การสัมภาษณ์ไปให้ตัดสิน
        prompt = f"เกณฑ์ที่ต้องการ (JD - IS1):\n{is1_jd_data}\n\nบันทึกจดโน้ตจากการสัมภาษณ์:\n{mock_notes}\n\nโปรดประเมินผลการสัมภาษณ์และตัดสินใจจ้างงานตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=InterviewEvaluationIS6,
                temperature=0.1, # ต้องการการตัดสินใจที่อิงตามข้อเท็จจริงเป๊ะๆ
            ),
        )
        return InterviewEvaluationIS6.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O with multiple inputs...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_6_interview_evaluator.py <input_is5_trigger> <output_is6_file>")
        sys.exit(1)

    # Orchestrator จะส่ง is5_interview_prep.json มาเพื่อ trigger แต่ Agent 6 ใช้ JD และ Notes ในการทำงานจริง
    input_trigger = sys.argv[1] 
    output_file = sys.argv[2]
    
    jd_file = "payloads/is1_job_description.json"
    notes_file = "payloads/mock_interview_notes.txt"

    try:
        with open(jd_file, "r", encoding="utf-8") as f:
            is1_data = f.read()
            
        with open(notes_file, "r", encoding="utf-8") as f:
            notes_data = f.read()

        print(f"⚡ [Agent 6] กำลังประเมินผลสัมภาษณ์จากโน้ต: {notes_file} ...")
        agent = GeminiInterviewEvaluator(api_key=MY_GEMINI_API_KEY)
        is6_result = agent.evaluate(is1_data, notes_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is6_result.model_dump_json(indent=2))

        print(f"✅ [Agent 6] Success! ประเมินผลสัมภาษณ์และฟันธงเสร็จสิ้น คายประจุ IS6 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 6] Error: {e}", file=sys.stderr)
        sys.exit(1)