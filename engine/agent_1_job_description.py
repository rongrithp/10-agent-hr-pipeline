import os
import sys
import subprocess
import google.generativeai as genai
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

# [NEW ARCHITECTURE] โหลดกุญแจจาก Root
load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def main():
    if len(sys.argv) < 2:
        print("❌ [Agent 1] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)
        
    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    # [NEW ARCHITECTURE] ชี้เป้า File I/O
    INPUT_FILE = os.path.join(paths["specs"], "is1_input_spec.txt")
    OUTPUT_FILE = os.path.join(paths["specs"], "is1_output_job_description.txt")

    print(f"🚀 [Agent 1] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        job_spec = f.read()

    prompt = f"""
    คุณคือ Agent 1 (Expert HR Copywriter) 
    หน้าที่ของคุณคือการเขียนประกาศรับสมัครงาน (Job Description) ที่ดึงดูด น่าเชื่อถือ และชัดเจน
    ข้อมูลดิบจากลูกค้า (Input Spec):\n{job_spec}
    ข้อกำหนด (System Constraints):
    1. โครงสร้างต้องประกอบด้วย: ชื่อตำแหน่ง, สรุปภาพรวมงาน, หน้าที่ความรับผิดชอบหลัก, คุณสมบัติที่ต้องการ, และสวัสดิการ/งบประมาณ
    2. ใช้ภาษาไทยที่เป็นทางการ สื่อสารตรงประเด็น (Zero Friction)
    3. จัดรูปแบบข้อความด้วย Markdown Format
    """
    
    try:
        response = model.generate_content(prompt)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print(f"✅ [Agent 1] สร้างไฟล์ JD เรียบร้อยในโฟลเดอร์ specs")
        print("🚀 [Agent 1] เตรียมส่งไม้ผลัดปลุก Agent 2...")
        
        # [NEW ARCHITECTURE] เตะปลุก Agent 2
        next_agent = os.path.join(config.ENGINE_DIR, "agent_2_sourcing_strategist.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 1] ระบบสมองประมวลผลล้มเหลว: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()