import os
import sys
import json
import requests
from dotenv import load_dotenv

# [Low-Level Actuator] บังคับท่อส่งข้อมูลให้เป็น UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# โหลด IP Shield
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAYLOAD_FILE = 'payloads/is10_employee_profile.json'

def send_telegram_notify():
    print("🚀 [Agent 12] Initiating Telegram Actuator...")

    # 1. Sensory Validation
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ CRITICAL ERROR: ไม่พบ TELEGRAM_BOT_TOKEN หรือ TELEGRAM_CHAT_ID ในไฟล์ .env")
        sys.exit(1)

    if not os.path.exists(PAYLOAD_FILE):
        print(f"❌ CRITICAL ERROR: ไม่พบไฟล์ผลลัพธ์ {PAYLOAD_FILE}")
        sys.exit(1)

    try:
        # 2. Data Extraction
        print("📖 Reading candidate data for physical transmission...")
        with open(PAYLOAD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        name = data.get("name", data.get("candidate_name", "Unknown Candidate"))
        role = data.get("role", data.get("position", "Unknown Role"))
        score = data.get("evaluation_score", data.get("score", "ไม่ระบุคะแนน")) 
        
        # 3. Message Formatting (ปั้นข้อความเตือน)
        message = f"✅ [HR Pipeline] จบกระบวนการ!\n"
        message += f"👤 ผู้สมัคร: {name}\n"
        message += f"🎯 ตำแหน่ง: {role}\n"
        message += f"📊 คะแนน: {score}\n"
        message += f"💾 สถานะ: บันทึกลง Google Sheets เรียบร้อย!"

        # 4. Actuation (ยิง API ทะลุเข้า Telegram)
        print("📡 Transmitting data to Telegram Server...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("✅ SUCCESS: Dynamic Balance Achieved! Notification sent to Telegram.")
        else:
            print(f"❌ [Agent 12] API Error: {response.status_code} - {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ [Agent 12] Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send_telegram_notify()