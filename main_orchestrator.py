import os
import sys
import json
import time
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

        # อ้างอิง Workspace Path ผ่าน config.get_workspace เสมอ
        workspace_path = data.get("workspace_path")
        if not workspace_path and job_id:
            workspace_path = config.get_workspace(job_id)["root"]
        elif not workspace_path:
            workspace_path = ""

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


def run_orchestrated_pipeline(job_id: str):
    """ทำหน้าที่เป็นศูนย์กลางควบคุมลำดับการรัน Agents ทั้งหมด 12 ตัวตามลำดับ (Sequential Orchestration)"""
    print("\n" + "=" * 80)
    print(f"🛸 CENTRAL PIPELINE ORCHESTRATOR FOR WORKSPACE: {job_id}")
    print(f"⏰ Execution Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    pipeline_agents = [
        ("Agent 1 (Job Description Generator)", "agent_1_job_description.py"),
        ("Agent 2 (Sourcing Strategist)", "agent_2_sourcing_strategist.py"),
        ("Agent 3 (Content Broadcaster)", "agent_3_content_broadcaster.py"),
        ("Agent 4 (Resume Screener Engine)", "agent_4_resume_screener.py"),
        ("Agent 5 (Interview Scheduler)", "agent_5_interview_scheduler.py"),
        ("Agent 6 (Interview Evaluator Engine)", "agent_6_interview_evaluator.py"),
        ("Agent 7 (Compliance Checker)", "agent_7_compliance_checker.py"),
        ("Agent 8 (Offer Negotiator Engine)", "agent_8_offer_negotiator.py"),
        ("Agent 9 (Onboarding Planner)", "agent_9_onboarding_planner.py"),
        ("Agent 10 (Master Talent Profiler)", "agent_10_talent_profiler.py"),
        ("Agent 11 (Enterprise Database Sync)", "agent_11_database_sync.py"),
        ("Agent 12 (Executive Telegram Notifier)", "agent_12_telegram_notify.py"),
    ]

    summary_results = []
    overall_start_time = time.time()

    for agent_name, script_file in pipeline_agents:
        script_path = os.path.join(config.ENGINE_DIR, script_file)
        print(f"\n▶️ [Orchestrator] Executing {agent_name}...")
        print(f"   Script Path: {script_path}")

        step_start = time.time()
        try:
            res = subprocess.run(
                [sys.executable, script_path, job_id],
                cwd=config.BASE_DIR,
                text=True,
                check=False
            )
            step_duration = time.time() - step_start

            if res.returncode == 0:
                print(f"   ✅ {agent_name} COMPLETED (Exit Code: 0, Time: {step_duration:.2f}s)")
                summary_results.append({
                    "name": agent_name,
                    "status": "PASSED",
                    "code": 0,
                    "time": f"{step_duration:.2f}s"
                })
            else:
                print(f"   ❌ {agent_name} FAILED with Exit Code {res.returncode}")
                summary_results.append({
                    "name": agent_name,
                    "status": "FAILED",
                    "code": res.returncode,
                    "time": f"{step_duration:.2f}s"
                })
                print(f"\n🛑 Pipeline Execution Halted due to failure in {agent_name}")
                sys.exit(res.returncode)

        except Exception as err:
            step_duration = time.time() - step_start
            print(f"   ❌ {agent_name} EXCEPTION: {err}")
            summary_results.append({
                "name": agent_name,
                "status": "EXCEPTION",
                "code": 1,
                "time": f"{step_duration:.2f}s"
            })
            print(f"\n🛑 Pipeline Execution Halted due to exception in {agent_name}")
            sys.exit(1)

    total_pipeline_time = time.time() - overall_start_time
    print("\n" + "=" * 80)
    print("🎉 FULL RECRUITMENT PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
    print(f"⏱️ Total Execution Time: {total_pipeline_time:.2f} seconds")
    print("=" * 80)
    for item in summary_results:
        print(f"  • {item['name']:<42} -> STATUS: {item['status']} (Exit Code {item['code']}, Time: {item['time']})")
    print("=" * 80 + "\n")


def main():
    if len(sys.argv) < 2:
        print("❌ [Orchestrator] ขัดข้อง: ไม่ได้รับ Job ID")
        sys.exit(1)

    job_id = sys.argv[1].strip()
    print(f"🛸 [Orchestrator] รับไม้ผลัด Job: {job_id} กำลังเข้าสู่ Workspace...")

    paths = config.get_workspace(job_id)
    payload_path = os.path.join(paths["specs"], 'is0_job_ticket.json')

    if os.path.exists(payload_path):
        with open(payload_path, 'r', encoding='utf-8') as f:
            job_data = json.load(f)

        sync_job_tracker(job_data)

        agent1_input_path = os.path.join(paths["specs"], 'is1_input_spec.txt')
        config.ensure_parent_dir(agent1_input_path)

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

    # Launch Central Sequential Pipeline Execution
    run_orchestrated_pipeline(job_id)


if __name__ == '__main__':
    main()