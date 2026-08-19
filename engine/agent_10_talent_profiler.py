import os
import sys
import json
import subprocess
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
    
class SkillMatrix(BaseModel):
    core_competencies: List[str] = Field(description="ทักษะหลักที่เชี่ยวชาญ")
    areas_for_development: List[str] = Field(description="จุดที่ควรพัฒนาเพิ่มเติม")
    suggested_training: List[str] = Field(description="คอร์สเรียนที่แนะนำในปีแรก")

class CareerPath(BaseModel):
    short_term_goal: str = Field(description="เป้าหมาย 6-12 เดือนแรก")
    potential_next_role: str = Field(description="ตำแหน่งในอนาคตที่สามารถเติบโตไปได้")

class EmployeeProfileIS10(BaseModel):
    employee_id: str = Field(description="รหัสพนักงาน")
    name: str
    job_title: str
    department: str = Field(description="แผนกที่สังกัด", default="Technology")
    skill_matrix: SkillMatrix
    career_path_projection: CareerPath
    manager_brief: str = Field(description="สรุปสั้นๆ ให้หัวหน้างานอ่าน")

class GeminiTalentProfiler:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def create_profile(self, is9_onboarding: str, mock_cvs: str, mock_notes: str) -> EmployeeProfileIS10:
        system_instruction = (
            "คุณคือ Agent_10_Talent_Profiler ประจำระบบ HR\n"
            "รวบรวมข้อมูลพนักงานใหม่ (แผน Onboarding, CV, Note สัมภาษณ์)\n"
            "วิเคราะห์ทักษะ วางแผนสายอาชีพ และเขียนคำแนะนำให้หัวหน้างาน"
        )
        prompt = f"แผน Onboarding (IS9):\n{is9_onboarding}\n\nเรซูเม่ (Mock CVs):\n{mock_cvs}\n\nบันทึกสัมภาษณ์ (Mock Notes):\n{mock_notes}\n\nโปรดสร้างโปรไฟล์และแผนพัฒนาบุคลากรตาม Schema"

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=EmployeeProfileIS10,
                temperature=0.5, 
            ),
        )
        return EmployeeProfileIS10.model_validate_json(response.text)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("Usage: python agent_10_talent_profiler.py <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    input_file = os.path.join(paths["onboarding"], "is9_output_onboarding_plan.json")
    cv_file = os.path.join(paths["dropzone"], "mock_cv_batch.json")
    notes_file = os.path.join(paths["dropzone"], "mock_interview_notes.txt")
    output_file = os.path.join(paths["onboarding"], "is10_output_employee_profile.json")

    try:
        if not os.path.exists(input_file):
            print(f"⚠️ [Agent 10] สแตนด์บาย: ไม่พบไฟล์ IS9 ใน 05_onboarding_vault")
            sys.exit(0)

        # Fallback หากบันทึกสัมภาษณ์อยู่ใน 01_specs
        if not os.path.exists(notes_file):
            fallback_notes = os.path.join(paths["specs"], "mock_interview_notes.txt")
            if os.path.exists(fallback_notes):
                notes_file = fallback_notes

        with open(input_file, "r", encoding="utf-8") as f:
            is9_data = f.read()
        with open(cv_file, "r", encoding="utf-8") as f:
            cv_data = f.read()
        with open(notes_file, "r", encoding="utf-8") as f:
            notes_data = f.read()

        print(f"⚡ [Agent 10] เข้าสู่ Workspace: {job_id} กำลังสร้างโปรไฟล์พนักงาน...")
        agent = GeminiTalentProfiler(api_key=MY_GEMINI_API_KEY)
        is10_result = agent.create_profile(is9_data, cv_data, notes_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(is10_result.model_dump_json(indent=2))

        print(f"✅ [Agent 10] สร้างโปรไฟล์พนักงานเสร็จสิ้น คายประจุลงโฟลเดอร์ 05_onboarding_vault")
        
        # 🚀 [NEW] สับสวิตช์เตะปลุก Agent 11 เพื่อซิงค์ลง Google Sheets ต่อเนื่องทันที
        print(f"🚀 [Agent 10] เตรียมเตะปลุก Agent 11 ซิงค์ฐานข้อมูล Google Sheets...")
        next_agent = os.path.join(config.ENGINE_DIR, "agent_11_database_sync.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        import sys
        print(f"❌ [Agent 10] Error: {e}", file=sys.stderr)
        sys.exit(1)