import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# [Low-Level Actuator] บังคับท่อส่งข้อมูลให้เป็น UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# ⚙️ CONFIGURATION (พิกัดเป้าหมายและกุญแจ)
# ==========================================
SPREADSHEET_ID = '13f5p_vrtjihGeWms1UvE9oJcvnlUl3Ous4-kSeifsrw'
CREDENTIALS_FILE = 'gcp_credentials.json'
PAYLOAD_FILE = 'payloads/is10_employee_profile.json' # จุดดึงข้อมูลผลลัพธ์สุดท้าย

def sync_to_database():
    print("🚀 [Agent 11] Initiating Database Sync...")
    
    # 1. Sensory Validation: เช็กว่ามีกุญแจและไฟล์ผลลัพธ์พร้อมไหม
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ CRITICAL ERROR: ไม่พบไฟล์กุญแจ {CREDENTIALS_FILE} กรุณาตรวจสอบ IP Shield")
        sys.exit(1)
        
    if not os.path.exists(PAYLOAD_FILE):
        print(f"❌ CRITICAL ERROR: ไม่พบไฟล์ผลลัพธ์ {PAYLOAD_FILE} (ระบบรันมาไม่ถึง Agent 10 หรือเปล่า?)")
        sys.exit(1)

    try:
        # 2. Authorization: ใช้กุญแจปลดล็อกสิทธิ์ระดับ Cloud
        print("🔑 Authenticating with GCP...")
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(credentials)
        
        # 3. Connection: เปิดไฟล์ Google Sheet ตามรหัสเป้าหมาย
        print("📂 Opening Google Sheet...")
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1 # เล็งไปที่ชีทแรก (Sheet1)
        
        # 4. Data Extraction: สูบข้อมูลจาก Digital Tokens
        print(f"📖 Reading {PAYLOAD_FILE}...")
        with open(PAYLOAD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # สกัดข้อมูล (ถ้าโครงสร้าง JSON ของคุณชื่อ Key ไม่ตรงกับตรงนี้ มันจะใส่คำว่า Unknown ให้แทนเพื่อป้องกันระบบแครช)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = data.get("name", data.get("candidate_name", "Unknown"))
        role = data.get("role", data.get("position", "Unknown"))
        status = data.get("status", "Onboarding Ready")
        
        # บีบอัดไฟล์ JSON ทั้งก้อนเป็น Text เพื่อเก็บเป็น Log ฐานข้อมูลหลังบ้าน
        raw_json = json.dumps(data, ensure_ascii=False)

        # 5. Structure Formatting: จัดเรียงแถวข้อมูล
        row_data = [timestamp, name, role, status, raw_json]
        
        # ตรวจสอบว่ามี Header หรือยัง ถ้าชีทว่างเปล่าให้สร้าง Header ก่อน
        existing_data = sheet.head(1) if hasattr(sheet, 'head') else sheet.get_all_values()
        if len(existing_data) == 0:
            sheet.append_row(["Timestamp", "Candidate Name", "Role", "Status", "Raw Payload (JSON)"])
        
        # 6. Physical Impact (Actuation): ยิงข้อมูลลงชีท!
        print("💾 Writing data to Google Sheets...")
        sheet.append_row(row_data)
        
        print("✅ SUCCESS: Dynamic Balance Achieved! Data synchronized to Google Sheets.")
        
    except Exception as e:
        print(f"❌ [Agent 11] Error during database sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_to_database()