import os
import sys
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
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
# Schema IS2 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic model for Sourcing Strategy...
class SourcingPlanIS2(BaseModel):
    target_candidate_profile: str = Field(description="สรุปโปรไฟล์ผู้สมัครในอุดมคติที่ควรค้นหา (Persona)")
    recommended_platforms: list[str] = Field(description="แพลตฟอร์มที่เหมาะสมที่สุดในการประกาศรับสมัคร (เช่น LinkedIn, JobsDB, Facebook)")
    search_keywords: list[str] = Field(description="คีย์เวิร์ดสำหรับให้ HR ใช้ค้นหาเรซูเม่ (Boolean Search terms หรือ Skill keywords)")
    salary_analysis: str = Field(description="วิเคราะห์ว่าเงินเดือนที่เสนอมาเหมาะสมกับตลาดหรือไม่ ดึงดูดคนได้ไหม")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 2...
class GeminiSourcingStrategist:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def strategize(self, is1_jd_data: str) -> SourcingPlanIS2:
        system_instruction = (
            "คุณคือ Agent_2_Sourcing_Strategist ประจำฝ่าย HR ระดับมืออาชีพ\n"
            "หน้าที่ของคุณคือรับ Job Description (IS1) มาวิเคราะห์เพื่อวางกลยุทธ์ในการค้นหาผู้สมัคร (Sourcing Strategy)\n"
            "คุณต้องแนะนำแพลตฟอร์มที่ตรงกลุ่มเป้าหมายที่สุด คิดคีย์เวิร์ดสำหรับค้นหา และวิเคราะห์ความเหมาะสมของเงินเดือนเทียบกับตลาดปัจจุบัน"
        )
        
        prompt = f"ข้อมูล Job Description (IS1):\n{is1_jd_data}\n\nโปรดวางกลยุทธ์การสรรหาตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=SourcingPlanIS2,
                temperature=0.4,
            ),
        )
        return SourcingPlanIS2.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_2_sourcing_strategist.py <input_is1_file> <output_is2_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            is1_data = f.read()

        print(f"⚡ [Agent 2] กำลังวางกลยุทธ์สรรหาบุคลากรจาก JD: {input_file} ...")
        agent = GeminiSourcingStrategist(api_key=MY_GEMINI_API_KEY)
        is2_result = agent.strategize(is1_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is2_result.model_dump_json(indent=2))

        print(f"✅ [Agent 2] Success! วางกลยุทธ์เสร็จสิ้น คายประจุ IS2 ลงไฟล์: {output_file}")
    except Exception as e:
        print(f"❌ [Agent 2] Error: {e}")
        sys.exit(1)