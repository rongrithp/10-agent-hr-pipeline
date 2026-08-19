import os
import sys
import json
import subprocess
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config 

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SPREADSHEET_ID = '13f5p_vrtjihGeWms1UvE9oJcvnlUl3Ous4-kSeifsrw'
CREDENTIALS_FILE = str(config.GCP_CREDENTIALS_PATH)
TARGET_SHEET_NAME = 'Job_Tracker'

def sync_job_tracker(data):
    """บันทึกหรืออัปเดตใบงานลงในแท็บ Job_Tracker ตามลำดับคอลัมน์ A ถึง N"""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"⚠️ [Orchestrator] ไม่พบไฟล์กุญแจ GCP Credentials: {CREDENTIALS_FILE}")
        return

    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        try:
            sheet = spreadsheet.worksheet(TARGET_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠️ [Orchestrator] ไม่พบชีท '{TARGET_SHEET_NAME}' กำลังสร้างชีทใหม่ให้อัตโนมัติ...")
            sheet = spreadsheet.add_worksheet(title=TARGET_SHEET_NAME, rows="100", cols="20")

        headers = [
            "Job_ID", "Open_Date", "Client_Name", "Contact_Info", "Position",
            "Headcount", "Salary_Budget", "Target_Start_Date", "Current_Stage",
            "Placed_Candidate", "Fee_Amount", "Payment_Status", "Workspace_Path", "Remarks"
        ]

        existing_data = sheet.get_all_values()
        if len(existing_data) == 0:
            sheet.append_row(headers)
        elif existing_data[0] != headers:
            sheet.update('A1:N1', [headers])

        job_id = data.get("job_id", "")
        open_date = data.get("open_date", data.get("date", datetime.now().strftime("%Y-%m-%d")))
        client_name = data.get("client", data.get("client_name", ""))
        contact_info = data.get("contact_info", data.get("requester", ""))
        position = data.get("position", "")
        headcount = data.get("headcount", 1)
        salary_budget = data.get("budget", data.get("salary_budget", ""))
        target_start_date = data.get("target_start_date", data.get("timeline", ""))
        current_stage = data.get("current_stage", data.get("status", "OPEN"))
        placed_candidate = data.get("placed_candidate", "")
        fee_amount = data.get("fee_amount", "")
        payment_status = data.get("payment_status", "Pending")
        workspace_path = data.get("workspace_path", f"workspaces/{job_id}/")
        remarks = data.get("remarks", "")

        row_data = [
            job_id, open_date, client_name, contact_info, position,
            headcount, salary_budget, target_start_date, current_stage,
            placed_candidate, fee_amount, payment_status, workspace_path, remarks
        ]

        found_row_idx = None
        if len(existing_data) > 1:
            for idx, row in enumerate(existing_data[1:], start=2):
                if len(row) > 0 and row[0].strip() == job_id.strip():
                    found_row_idx = idx
                    break

        if found_row_idx:
            range_to_update = f"A{found_row_idx}:N{found_row_idx}"
            sheet.update(range_to_update, [row_data])
            print(f"✅ [Orchestrator] อัปเดตข้อมูลใบงาน {job_id} ในแท็บ '{TARGET_SHEET_NAME}' แถวที่ {found_row_idx} สำเร็จ")
        else:
            sheet.append_row(row_data)
            print(f"✅ [Orchestrator] บันทึกใบงานใหม่ {job_id} ลงแท็บ '{TARGET_SHEET_NAME}' สำเร็จ")

    except Exception as e:
        print(f"❌ [Orchestrator] เกิดข้อผิดพลาดในการบันทึก Google Sheets: {e}")

def main():
    if len(sys.argv) < 2:
        print("❌ [Orchestrator] ขัดข้อง: ไม่ได้รับ Job ID จาก Agent 0")
        sys.exit(1)
        
    job_id = sys.argv[1].strip()
    print(f"🛸 [Orchestrator] รับไม้ผลัด Job: {job_id} กำลังเข้าสู่ Workspace...")
    
    paths = config.get_workspace(job_id)
    payload_path = os.path.join(paths["specs"], 'is0_job_ticket.json')
    
    with open(payload_path, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    sync_job_tracker(job_data)
        
    agent1_input_path = os.path.join(paths["specs"], 'is1_input_spec.txt')
    with open(agent1_input_path, 'w', encoding='utf-8') as f:
        f.write(
            f"Job ID: {job_data.get('job_id')}\n"
            f"Position: {job_data.get('position')}\n"
            f"Client: {job_data.get('client')}\n"
            f"Contact Info: {job_data.get('contact_info', job_data.get('requester', '-'))}\n"
            f"Headcount: {job_data.get('headcount', 1)}\n"
            f"Budget: {job_data.get('budget')}\n"
            f"Timeline/Target Start: {job_data.get('target_start_date', job_data.get('timeline'))}\n"
            f"Remarks: {job_data.get('remarks', '-')}\n"
        )
        
    print("🚀 [Orchestrator] เตรียมส่งไม้ผลัดปลุก Agent 1...")
    
    # [NEW ARCHITECTURE] เตะปลุกด้วย Absolute Path
    next_agent = os.path.join(config.ENGINE_DIR, "agent_1_job_description.py")
    subprocess.Popen([sys.executable, next_agent, job_id])

if __name__ == '__main__':
    main()