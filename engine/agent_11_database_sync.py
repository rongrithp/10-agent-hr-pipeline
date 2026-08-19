import os
import sys
import json
import gspread
import subprocess
import re
from google.oauth2.service_account import Credentials
from datetime import datetime
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config 

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SPREADSHEET_ID = '13f5p_vrtjihGeWms1UvE9oJcvnlUl3Ous4-kSeifsrw'
CREDENTIALS_FILE = str(config.GCP_CREDENTIALS_PATH)
TARGET_SHEET_NAME = 'Onboarded_Talents'
JOB_TRACKER_SHEET_NAME = 'Job_Tracker'

def parse_salary(salary_val):
    """แปลงค่าเงินเดือนเป็นตัวเลข Integer"""
    if isinstance(salary_val, (int, float)):
        return int(salary_val)
    if isinstance(salary_val, str):
        cleaned = re.sub(r'[^\d]', '', salary_val)
        if cleaned:
            return int(cleaned)
    return 0

def format_date_str(date_text):
    """ดึงและฟอร์แมตวันที่ในรูปแบบ YYYY-MM-DD"""
    if not date_text or not isinstance(date_text, str):
        return datetime.now().strftime("%Y-%m-%d")
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_text)
    if match:
        return match.group(0)
    return date_text.strip()

def sync_to_database():
    if len(sys.argv) < 2:
        print("❌ [Agent 11] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)
        
    job_id = sys.argv[1].strip()
    paths = config.get_workspace(job_id)
    
    # พิกัดไฟล์ข้อมูลใน Workspace
    is10_path = os.path.join(paths["onboarding"], "is10_output_employee_profile.json")
    is9_path = os.path.join(paths["onboarding"], "is9_output_onboarding_plan.json")
    is8_path = os.path.join(paths["offers"], "is8_output_offer_details.json")
    is7_path = os.path.join(paths["evaluations"], "is7_output_compliance_check.json")
    is0_path = os.path.join(paths["specs"], "is0_job_ticket.json")
    cv_path = os.path.join(paths["dropzone"], "mock_cv_batch.json")

    print(f"🚀 [Agent 11] เข้าสู่ Workspace: {job_id} Initiating Database Sync...")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ CRITICAL ERROR: ไม่พบไฟล์กุญแจ {CREDENTIALS_FILE}")
        sys.exit(1)
        
    if not os.path.exists(is10_path):
        print(f"❌ CRITICAL ERROR: ไม่พบไฟล์ผลลัพธ์ {is10_path}")
        sys.exit(1)

    try:
        # 1. โหลดข้อมูลจาก JSON ทั้งหมด
        with open(is10_path, 'r', encoding='utf-8') as f:
            is10_data = json.load(f)
            
        is9_data = {}
        if os.path.exists(is9_path):
            with open(is9_path, 'r', encoding='utf-8') as f:
                is9_data = json.load(f)

        is8_data = {}
        if os.path.exists(is8_path):
            with open(is8_path, 'r', encoding='utf-8') as f:
                is8_data = json.load(f)

        is7_data = {}
        if os.path.exists(is7_path):
            with open(is7_path, 'r', encoding='utf-8') as f:
                is7_data = json.load(f)

        is0_data = {}
        if os.path.exists(is0_path):
            with open(is0_path, 'r', encoding='utf-8') as f:
                is0_data = json.load(f)

        cv_list = []
        if os.path.exists(cv_path):
            with open(cv_path, 'r', encoding='utf-8') as f:
                cv_list = json.load(f)

        # 2. สกัดฟิลด์ข้อมูลทั้ง 14 คอลัมน์ (A ถึง N)
        candidate_id = is10_data.get("employee_id", "CAND-001")
        full_name = is10_data.get("name", is8_data.get("applicant_name", "Unknown Candidate"))
        position = is10_data.get("job_title", is0_data.get("position", "Unknown Position"))
        department = is10_data.get("department", "Technology")
        client_school = is0_data.get("client", is0_data.get("client_name", "โรงเรียน Harrow"))
        
        # เงินเดือนที่ตกลง
        raw_salary = is8_data.get("proposed_package", {}).get("base_salary")
        agreed_salary = parse_salary(raw_salary)
        
        # วันเริ่มงาน
        start_date_raw = is9_data.get("start_date", is0_data.get("target_start_date", is0_data.get("timeline")))
        start_date = format_date_str(start_date_raw)
        
        onboarding_status = "Onboarded Successfully"
        
        # อีเมลและเบอร์โทร
        email = is9_data.get("it_setup_checklist", {}).get("email_created", "")
        phone = ""
        
        if isinstance(cv_list, list):
            for cv in cv_list:
                if cv.get("candidate_id") == candidate_id or cv.get("full_name") == full_name:
                    if not email:
                        email = cv.get("email", "")
                    phone = cv.get("phone", "")
                    break
                    
        if not email:
            email = f"{candidate_id.lower()}@example.com"
            
        # สถานะการตรวจเอกสาร
        compliance_status = is7_data.get("final_clearance", "PASS")
        if isinstance(compliance_status, list):
            compliance_status = "PASS"
            
        vault_path = f"05_onboarding_vault/{candidate_id}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. จัดเรียงข้อมูลใน Row (A ถึง N)
        row_data = [
            job_id,            # A: Job_ID
            candidate_id,      # B: Candidate_ID
            full_name,         # C: Full_Name
            position,          # D: Position
            department,        # E: Department
            client_school,     # F: Client_School
            agreed_salary,     # G: Agreed_Salary
            start_date,        # H: Start_Date
            onboarding_status, # I: Onboarding_Status
            email,             # J: Email
            phone,             # K: Phone
            compliance_status, # L: Compliance_Status
            vault_path,        # M: Vault_Path
            timestamp          # N: Timestamp
        ]

        # 4. เชื่อมต่อ GCP & Google Sheets API
        print("🔑 Authenticating with GCP...")
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        # 5. ซิงค์ลงแท็บ 'Onboarded_Talents'
        print(f"📂 Opening Google Sheet tab: '{TARGET_SHEET_NAME}'...")
        try:
            sheet_talents = spreadsheet.worksheet(TARGET_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠️ ไม่พบชีท '{TARGET_SHEET_NAME}' กำลังสร้างชีทใหม่ให้อัตโนมัติ...")
            sheet_talents = spreadsheet.add_worksheet(title=TARGET_SHEET_NAME, rows="100", cols="20")

        headers_talents = [
            "Job_ID", "Candidate_ID", "Full_Name", "Position", "Department",
            "Client_School", "Agreed_Salary", "Start_Date", "Onboarding_Status",
            "Email", "Phone", "Compliance_Status", "Vault_Path", "Timestamp"
        ]

        existing_talents = sheet_talents.get_all_values()
        if len(existing_talents) == 0:
            sheet_talents.append_row(headers_talents)
        elif existing_talents[0] != headers_talents:
            sheet_talents.update('A1:N1', [headers_talents])

        print(f"💾 Writing onboarding record to '{TARGET_SHEET_NAME}'...")
        sheet_talents.append_row(row_data)
        print(f"✅ SUCCESS: Data synchronized to Google Sheets tab '{TARGET_SHEET_NAME}'.")

        # 6. อัปเดตสถานะในแท็บ 'Job_Tracker'
        print(f"🔄 Updating status in Google Sheets tab: '{JOB_TRACKER_SHEET_NAME}'...")
        try:
            sheet_tracker = spreadsheet.worksheet(JOB_TRACKER_SHEET_NAME)
            existing_tracker = sheet_tracker.get_all_values()
            
            placed_info = f"{candidate_id} - {full_name}"
            
            for idx, row in enumerate(existing_tracker[1:], start=2):
                if len(row) > 0 and row[0].strip() == job_id.strip():
                    sheet_tracker.update_cell(idx, 9, "Completed")     # Column I: Current_Stage
                    sheet_tracker.update_cell(idx, 10, placed_info)     # Column J: Placed_Candidate
                    sheet_tracker.update_cell(idx, 12, "Invoiced")       # Column L: Payment_Status
                    print(f"✅ SUCCESS: Updated '{JOB_TRACKER_SHEET_NAME}' row {idx} for {job_id} -> Current_Stage='Completed', Placed_Candidate='{placed_info}'.")
                    break
        except Exception as tracker_err:
            print(f"⚠️ [Warning] Could not update Job_Tracker status: {tracker_err}")

        # 7. เตะปลุก Agent 12 แจ้งเตือน Telegram
        print(f"🚀 [Agent 11] เตรียมเตะปลุก Agent 12 แจ้งเตือน Telegram...")
        next_agent = os.path.join(config.ENGINE_DIR, "agent_12_telegram_notify.py")
        subprocess.Popen([sys.executable, next_agent, job_id])
        
    except Exception as e:
        print(f"❌ [Agent 11] Error during database sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_to_database()