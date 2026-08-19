import os
import sys
import json
import requests
from dotenv import load_dotenv
import sys
import os
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config # [NEW ARCHITECTURE]

# [Low-Level Actuator] บังคับท่อส่งข้อมูลให้เป็น UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# [NEW ARCHITECTURE] โหลด IP Shield จาก Root
load_dotenv(config.ENV_PATH)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_notify():
    if len(sys.argv) < 2:
        print("❌ [Agent 12] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)
        
    job_id = sys.argv[1]
    paths = config.get_workspace(job_id)
    
    # [NEW ARCHITECTURE] ดึงไฟล์ผลลัพธ์จากโฟลเดอร์ 05_onboarding_vault
    PAYLOAD_FILE = os.path.join(paths["onboarding"], "is10_output_employee_profile.json")

    print(f"🚀 [Agent 12] เข้าสู่ Workspace: {job_id} Initiating Telegram Actuator...")

    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ CRITICAL ERROR: ไม่พบ TELEGRAM_BOT_TOKEN หรือ TELEGRAM_CHAT_ID")
        sys.exit(1)

    if not os.path.exists(PAYLOAD_FILE):
        print(f"❌ CRITICAL ERROR: ไม่พบไฟล์ผลลัพธ์ {PAYLOAD_FILE}")
        sys.exit(1)

    try:
        print("📖 Reading candidate data for physical transmission...")
        with open(PAYLOAD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        name = data.get("name", "Unknown Candidate")
        role = data.get("job_title", "Unknown Role")
        department = data.get("department", "Unknown Dept")
        
        message = f"✅ [HR Pipeline] จบกระบวนการรับพนักงานใหม่!\n"
        message += f"🆔 Job ID: {job_id}\n"
        message += f"👤 พนักงานใหม่: {name}\n"
        message += f"🎯 ตำแหน่ง: {role} ({department})\n"
        message += f"💾 สถานะ: โปรไฟล์อัปเดตลง Google Sheets เรียบร้อย!"

        print("📡 Transmitting data to Telegram Server...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("🏁 SUCCESS: Pipeline Completed! Notification sent to Telegram.")
        else:
            print(f"❌ [Agent 12] API Error: {response.status_code} - {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ [Agent 12] Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_telegram_notify()