import os
import sys
import json
import time
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config

# Imports for In-Memory Direct Pipeline Execution (Agent 0 - 12)
from engine.agent_0_telegram_gatekeeper import main as run_agent_0
from engine.agent_1_job_description import main as run_agent_1
from engine.agent_2_sourcing_strategist import main as run_agent_2
from engine.agent_3_content_broadcaster import main as run_agent_3
from engine.agent_4_resume_screener import main as run_agent_4
from engine.agent_5_interview_scheduler import main as run_agent_5
from engine.agent_6_interview_evaluator import main as run_agent_6
from engine.agent_7_compliance_checker import main as run_agent_7
from engine.agent_8_offer_negotiator import main as run_agent_8
from engine.agent_9_onboarding_planner import main as run_agent_9
from engine.agent_10_talent_profiler import main as run_agent_10
from engine.agent_11_database_sync import main as run_agent_11
from engine.agent_12_telegram_notify import main as run_agent_12

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SPREADSHEET_ID = '13f5p_vrtjihGeWms1UvE9oJcvnlUl3Ous4-kSeifsrw'
CREDENTIALS_FILE = str(config.GCP_CREDENTIALS_PATH)
TARGET_SHEET_NAME = 'Job_Tracker'


def sync_job_tracker(data: dict):
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

        workspace_path = data.get("workspace_path")
        if not workspace_path and job_id:
            workspace_path = str(config.get_workspace(job_id)["root"])
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
    """ทำหน้าที่เป็น Central State Engine ควบคุมการรัน In-Memory Pipeline ครบถ้วน 13 Agents Across 5 Lifecycles"""
    print("\n" + "=" * 80)
    print(f"🛸 CENTRAL IN-MEMORY PIPELINE ENGINE FOR WORKSPACE: {job_id}")
    print(f"⏰ Execution Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    pipeline_stages = [
        # Lifecycle 1: Job Specs & Sourcing Assets
        ("Lifecycle 1: Job Spec & Sourcing", "Agent 0 (Telegram Gatekeeper)", run_agent_0),
        ("Lifecycle 1: Job Spec & Sourcing", "Agent 1 (Job Spec Synthesizer)", run_agent_1),
        ("Lifecycle 1: Job Spec & Sourcing", "Agent 2 (Sourcing Strategist)", run_agent_2),
        ("Lifecycle 1: Job Spec & Sourcing", "Agent 3 (Content Broadcaster)", run_agent_3),
        # Lifecycle 2 & 3: Screening & Evaluation
        ("Lifecycles 2 & 3: Screening & Evaluation", "Agent 4 (Resume Screener Engine)", run_agent_4),
        ("Lifecycles 2 & 3: Screening & Evaluation", "Agent 5 (Interview Scheduler)", run_agent_5),
        ("Lifecycles 2 & 3: Screening & Evaluation", "Agent 6 (Interview Evaluator Engine)", run_agent_6),
        # Lifecycle 4: Compliance & Offer
        ("Lifecycle 4: Compliance & Offer", "Agent 7 (Compliance Checker)", run_agent_7),
        ("Lifecycle 4: Compliance & Offer", "Agent 8 (Offer Negotiator Engine)", run_agent_8),
        # Lifecycle 5: Onboarding, DB Sync & Notification
        ("Lifecycle 5: Onboarding & Notification", "Agent 9 (Onboarding Planner)", run_agent_9),
        ("Lifecycle 5: Onboarding & Notification", "Agent 10 (Master Talent Profiler)", run_agent_10),
        ("Lifecycle 5: Onboarding & Notification", "Agent 11 (Enterprise Database Sync)", run_agent_11),
        ("Lifecycle 5: Onboarding & Notification", "Agent 12 (Executive Telegram Notifier)", run_agent_12),
    ]

    summary_results = []
    pipeline_state = {}
    overall_start_time = time.time()
    total_steps = len(pipeline_stages)

    for idx, (lifecycle_name, agent_name, agent_func) in enumerate(pipeline_stages, start=1):
        step_str = f"[{idx}/{total_steps}]"
        print(f"\n▶️ {step_str} [{lifecycle_name}] Running {agent_name} (In-Memory)...")

        step_start = time.time()
        try:
            # Direct In-Memory Function Call
            result_payload = agent_func(job_id)
            step_duration = time.time() - step_start

            pipeline_state[agent_name] = result_payload

            print(f"   ✅ {step_str} {agent_name} COMPLETED (In-Memory Execution, Time: {step_duration:.2f}s)")
            summary_results.append({
                "step": step_str,
                "lifecycle": lifecycle_name,
                "name": agent_name,
                "status": "PASSED",
                "code": 0,
                "time": f"{step_duration:.2f}s"
            })

        except Exception as err:
            step_duration = time.time() - step_start
            print(f"   ❌ {step_str} {agent_name} FAILED / EXCEPTION: {err}")
            summary_results.append({
                "step": step_str,
                "lifecycle": lifecycle_name,
                "name": agent_name,
                "status": "FAILED",
                "code": 1,
                "time": f"{step_duration:.2f}s"
            })
            print(f"\n🛑 Pipeline Execution Halted cleanly due to failure in {agent_name} (Step {idx}/{total_steps})")
            sys.exit(1)

    total_pipeline_time = time.time() - overall_start_time
    print("\n" + "=" * 80)
    print("🎉 IN-MEMORY RECRUITMENT PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
    print(f"⏱️ Total Execution Time: {total_pipeline_time:.2f} seconds")
    print("=" * 80)
    for item in summary_results:
        print(f"  • {item['step']} {item['name']:<42} -> STATUS: {item['status']} ({item['time']})")
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

    # Launch In-Memory Direct Pipeline Execution
    run_orchestrated_pipeline(job_id)


if __name__ == '__main__':
    main()