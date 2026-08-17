import os
import sys
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ใส่ API Key ของคุณที่นี่!
MY_GEMINI_API_KEY = "AIzaSyDpFinTIgVB0g44Acu9TRjqEp6Nn-Wk1Ak"

# ==========================================
# Schema IS10 (Output)
# ==========================================
# STREAMING_CHUNK: Defining Pydantic models for Talent Profiling...
class SkillMatrix(BaseModel):
    core_competencies: List[str] = Field(description="ทักษะหลักที่พนักงานคนนี้เชี่ยวชาญสุดๆ")
    areas_for_development: List[str] = Field(description="จุดที่ควรพัฒนาเพิ่มเติม (อิงจากตอนสัมภาษณ์หรือโปรไฟล์)")
    suggested_training: List[str] = Field(description="คอร์สเรียนหรือการฝึกอบรมที่แนะนำให้ลงเรียนในปีแรก")

class CareerPath(BaseModel):
    short_term_goal: str = Field(description="เป้าหมายที่คาดหวังใน 6-12 เดือนแรก")
    potential_next_role: str = Field(description="ตำแหน่งในอนาคตที่สามารถเติบโตไปได้ (เช่น จาก Dev เป็น Senior Dev หรือ Tech Lead)")

class EmployeeProfileIS10(BaseModel):
    employee_id: str = Field(description="รหัสพนักงาน (สร้างขึ้นมาใหม่แบบสุ่ม เช่น EMP-2026001)")
    name: str
    job_title: str
    department: str = Field(description="แผนกที่สังกัด", default="Technology")
    skill_matrix: SkillMatrix
    career_path_projection: CareerPath
    manager_brief: str = Field(description="สรุปสั้นๆ ให้หัวหน้างานอ่าน เพื่อให้รู้ว่าควรบริหารจัดการพนักงานคนนี้อย่างไรให้ดึงศักยภาพออกมาได้ดีที่สุด")

# ==========================================
# Agent Class
# ==========================================
# STREAMING_CHUNK: Configuring Agent 10 Talent Profiler...
class GeminiTalentProfiler:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def create_profile(self, is9_onboarding: str, mock_cvs: str, mock_notes: str) -> EmployeeProfileIS10:
        system_instruction = (
            "คุณคือ Agent_10_Talent_Profiler ประจำระบบ HR (ตัวสุดท้ายของ Pipeline)\n"
            "หน้าที่ของคุณคือรวบรวมข้อมูลทั้งหมดของพนักงานใหม่ (จากแผน Onboarding, CV เดิม และ Note สัมภาษณ์)\n"
            "เพื่อสร้าง 'Employee Profile & Development Plan' (IS10) ส่งเข้าสู่ระบบ HRIS ของบริษัท\n"
            "คุณต้องวิเคราะห์ทักษะ, วางแผนสายอาชีพ (Career Path), และเขียนคำแนะนำให้หัวหน้างานว่าควรดึงศักยภาพคนนี้ออกมาอย่างไร"
        )
        
        # ป้อนข้อมูลรวบยอดให้ AI รู้จักพนักงานคนนี้ทะลุปรุโปร่ง
        prompt = f"แผน Onboarding (IS9):\n{is9_onboarding}\n\nเรซูเม่ (Mock CVs - ให้หาข้อมูลเฉพาะคนที่ชื่อตรงกับ IS9):\n{mock_cvs}\n\nบันทึกสัมภาษณ์ (Mock Notes):\n{mock_notes}\n\nโปรดสร้างโปรไฟล์และแผนพัฒนาบุคลากรตาม Schema ที่กำหนด"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=EmployeeProfileIS10,
                temperature=0.5, # ให้อุณหภูมินิดนึงเพื่อความสร้างสรรค์ในการเขียนแผนพัฒนา
            ),
        )
        return EmployeeProfileIS10.model_validate_json(response.text)

# ==========================================
# Execution Block
# ==========================================
# STREAMING_CHUNK: Handling File I/O for the final agent...
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 3:
        print("Usage: python agent_10_talent_profiler.py <input_is9_file> <output_is10_file>")
        sys.exit(1)

    input_file = sys.argv[1] 
    output_file = sys.argv[2]
    
    cv_file = "payloads/mock_cv_batch.json"
    notes_file = "payloads/mock_interview_notes.txt"

    try:
        # อ่านข้อมูลที่จำเป็นทั้งหมด
        with open(input_file, "r", encoding="utf-8") as f:
            is9_data = f.read()
            
        with open(cv_file, "r", encoding="utf-8") as f:
            cv_data = f.read()
            
        with open(notes_file, "r", encoding="utf-8") as f:
            notes_data = f.read()

        print(f"⚡ [Agent 10] กำลังสร้างโปรไฟล์พนักงานและแผนพัฒนาจาก: {input_file} ...")
        agent = GeminiTalentProfiler(api_key=MY_GEMINI_API_KEY)
        is10_result = agent.create_profile(is9_data, cv_data, notes_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is10_result.model_dump_json(indent=2))

        print(f"✅ [Agent 10] Success! สร้างโปรไฟล์พนักงานเสร็จสิ้น คายประจุ IS10 ลงไฟล์: {output_file}")
    except Exception as e:
        import sys
        print(f"❌ [Agent 10] Error: {e}", file=sys.stderr)
        sys.exit(1)