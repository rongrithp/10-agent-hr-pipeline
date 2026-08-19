import os
import sys
import json
import subprocess
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
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
    
class SourcingPlanIS2(BaseModel):
    target_candidate_profile: str = Field(description="สรุปโปรไฟล์ผู้สมัครในอุดมคติ (Persona)")
    recommended_platforms: list[str] = Field(description="แพลตฟอร์มที่เหมาะสมที่สุด (เช่น LinkedIn, JobsDB)")
    search_keywords: list[str] = Field(description="คีย์เวิร์ดสำหรับให้ HR ใช้ค้นหาเรซูเม่")
    salary_analysis: str = Field(description="วิเคราะห์ความเหมาะสมของเงินเดือน")

class GeminiSourcingStrategist:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def strategize(self, is1_jd_data: str) -> SourcingPlanIS2:
        system_instruction = (
            "คุณคือ Agent_2_Sourcing_Strategist ประจำฝ่าย HR ระดับมืออาชีพ\n"
            "รับ Job Description (IS1) มาวิเคราะห์เพื่อวางกลยุทธ์ในการค้นหาผู้สมัคร"
        )
        prompt = f"ข้อมูล Job Description (IS1):\n{is1_jd_data}\n\nโปรดวางกลยุทธ์ตาม Schema"

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 2] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)

    # [NEW ARCHITECTURE] ชี้เป้า File I/O
    input_file = os.path.join(paths["specs"], "is1_output_job_description.txt")
    output_file = os.path.join(paths["specs"], "is2_output_sourcing_strategy.json")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            is1_data = f.read()

        print(f"⚡ [Agent 2] เข้าสู่ Workspace: {job_id} กำลังวางกลยุทธ์สรรหา...")
        agent = GeminiSourcingStrategist(api_key=MY_GEMINI_API_KEY)
        is2_result = agent.strategize(is1_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is2_result.model_dump_json(indent=2))

        print(f"✅ [Agent 2] วางกลยุทธ์เสร็จสิ้น เซฟลงโฟลเดอร์ specs")
        print("🚀 [Agent 2] เตรียมส่งไม้ผลัดปลุก Agent 3...")
        
        # [NEW ARCHITECTURE] เตะปลุก Agent 3
        next_agent = os.path.join(config.ENGINE_DIR, "agent_3_content_broadcaster.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 2] Error: {e}")
        sys.exit(1)