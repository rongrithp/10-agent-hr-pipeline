import os
import sys
import json
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
    
class JobPosting(BaseModel):
    platform: str = Field(description="ชื่อแพลตฟอร์ม (เช่น LinkedIn, Facebook)")
    post_content: str = Field(description="เนื้อหาประกาศรับสมัครที่ปรับแต่งให้เหมาะกับแพลตฟอร์มนั้นๆ")

class BroadcastingPlanIS3(BaseModel):
    job_title: str = Field(description="ชื่อตำแหน่งงาน")
    postings: List[JobPosting] = Field(description="รายการประกาศรับสมัคร")
    recommended_posting_time: str = Field(description="คำแนะนำช่วงเวลาโพสต์")

class GeminiContentBroadcaster:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def broadcast(self, is2_sourcing_plan: str) -> BroadcastingPlanIS3:
        system_instruction = (
            "คุณคือ Agent_3_Content_Broadcaster ประจำฝ่าย HR\n"
            "รับ 'กลยุทธ์การสรรหา (IS2)' มาเขียนประกาศรับสมัครงานแยกตามแพลตฟอร์ม"
        )
        prompt = f"กลยุทธ์การสรรหา (IS2):\n{is2_sourcing_plan}\n\nโปรดร่างประกาศรับสมัครงานตาม Schema"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=BroadcastingPlanIS3,
                temperature=0.6, 
            ),
        )
        return BroadcastingPlanIS3.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ [Agent 3] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)

    # [NEW ARCHITECTURE] ชี้เป้า File I/O
    input_file = os.path.join(paths["specs"], "is2_output_sourcing_strategy.json")
    output_file = os.path.join(paths["specs"], "is3_output_job_postings.json")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            is2_data = f.read()

        print(f"⚡ [Agent 3] เข้าสู่ Workspace: {job_id} กำลังร่างประกาศ...")
        agent = GeminiContentBroadcaster(api_key=MY_GEMINI_API_KEY)
        is3_result = agent.broadcast(is2_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is3_result.model_dump_json(indent=2))

        print(f"✅ [Agent 3] ร่างประกาศเสร็จสิ้น เซฟลงโฟลเดอร์ specs")
        print(f"⏸️ [System] Phase 1 เสร็จสมบูรณ์! ระบบเข้าสู่โหมดรอรับเรซูเม่ (Transient Hypofrontality) สำหรับ {job_id}")
        
        # ⚠️ ไม่เตะปลุก Agent 4 รอให้ Actuator ข้างนอกเอา CV มาหย่อนแล้วค่อยสั่งรัน
        
    except Exception as e:
        print(f"❌ [Agent 3] Error: {e}")
        sys.exit(1)