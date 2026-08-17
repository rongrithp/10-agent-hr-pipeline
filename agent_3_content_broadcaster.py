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
# Schema IS3 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic model for Job Postings...
class JobPosting(BaseModel):
    platform: str = Field(description="ชื่อแพลตฟอร์ม (เช่น LinkedIn, Facebook, JobsDB)")
    post_content: str = Field(description="เนื้อหาประกาศรับสมัครที่ปรับแต่งให้เหมาะกับแพลตฟอร์มนั้นๆ (มี Emoji, Hashtag, ความยาวที่เหมาะสม)")

class BroadcastingPlanIS3(BaseModel):
    job_title: str = Field(description="ชื่อตำแหน่งงาน")
    postings: List[JobPosting] = Field(description="รายการประกาศรับสมัครสำหรับแต่ละแพลตฟอร์ม")
    recommended_posting_time: str = Field(description="คำแนะนำช่วงเวลาที่เหมาะสมที่สุดในการโพสต์ประกาศ")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 3...
class GeminiContentBroadcaster:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def broadcast(self, is2_sourcing_plan: str) -> BroadcastingPlanIS3:
        system_instruction = (
            "คุณคือ Agent_3_Content_Broadcaster ประจำฝ่าย HR ที่เชี่ยวชาญด้าน Employer Branding\n"
            "หน้าที่ของคุณคือรับ 'กลยุทธ์การสรรหา (IS2)' มาเขียนประกาศรับสมัครงาน (Job Posting) ที่น่าดึงดูดใจ\n"
            "คุณต้องเขียนแยกตามแพลตฟอร์มที่แนะนำมาใน IS2 โดยใช้ภาษาที่เหมาะสมกับแต่ละแพลตฟอร์ม (เช่น LinkedIn ดูเป็นทางการ, Facebook ดูเป็นกันเอง)"
        )
        
        prompt = f"กลยุทธ์การสรรหา (IS2):\n{is2_sourcing_plan}\n\nโปรดร่างประกาศรับสมัครงานตาม Schema ที่กำหนด"

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

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_3_content_broadcaster.py <input_is2_file> <output_is3_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            is2_data = f.read()

        # พิมพ์บอก Orchestrator ให้รู้ว่ากำลังทำอะไร
        print(f"⚡ [Agent 3] กำลังร่างประกาศรับสมัครงานจากกลยุทธ์: {input_file} ...")
        
        agent = GeminiContentBroadcaster(api_key=MY_GEMINI_API_KEY)
        is3_result = agent.broadcast(is2_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is3_result.model_dump_json(indent=2))

        # พิมพ์บอก Orchestrator ให้รู้ว่าทำเสร็จแล้ว
        print(f"✅ [Agent 3] Success! ร่างประกาศเสร็จสิ้น คายประจุ IS3 ลงไฟล์: {output_file}")
    except Exception as e:
        # พิมพ์ Error ออกมาให้ Orchestrator จับได้
        print(f"❌ [Agent 3] Error: {e}")
        sys.exit(1)