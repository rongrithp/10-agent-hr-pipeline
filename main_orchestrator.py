import os
import sys
import json
import time
import argparse
import threading
import gspread
from concurrent.futures import ThreadPoolExecutor, as_completed
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

print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    """Thread-safe console print helper"""
    with print_lock:
        print(*args, **kwargs)


def sync_job_tracker(data: dict):
    """บันทึกหรืออัปเดตใบงานลงในแท็บ Job_Tracker ตามลำดับคอลัมน์ A ถึง N (Thread-Safe)"""
    if not os.path.exists(CREDENTIALS_FILE):
        safe_print(f"⚠️ [Orchestrator] ไม่พบไฟล์กุญแจ GCP Credentials: {CREDENTIALS_FILE}")
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
        contact_info = data.get("contact_info", data.get("contact", data.get("requester", "")))
        position = data.get("position", "")
        headcount = data.get("headcount", 1)
        salary_budget = data.get("salary_budget", data.get("budget", ""))
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
            safe_print(f"✅ [Orchestrator:{job_id}] อัปเดตข้อมูลใบงานในแท็บ '{TARGET_SHEET_NAME}' แถวที่ {found_row_idx} สำเร็จ")
        else:
            sheet.append_row(row_data)
            safe_print(f"✅ [Orchestrator:{job_id}] บันทึกใบงานใหม่ลงแท็บ '{TARGET_SHEET_NAME}' สำเร็จ")

    except Exception as e:
        safe_print(f"❌ [Orchestrator:{data.get('job_id')}] เกิดข้อผิดพลาดในการบันทึก Google Sheets: {e}")


def run_orchestrated_pipeline(job_id: str) -> bool:
    """ทำหน้าที่เป็น Central State Engine ควบคุมการรัน In-Memory Pipeline ครบถ้วน 13 Agents Across 5 Lifecycles"""
    safe_print("\n" + "=" * 80)
    safe_print(f"🛸 CENTRAL IN-MEMORY PIPELINE ENGINE FOR WORKSPACE: {job_id}")
    safe_print(f"⏰ Execution Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("=" * 80 + "\n")

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
        safe_print(f"\n▶️ {step_str} [{job_id}] [{lifecycle_name}] Running {agent_name} (In-Memory)...")

        step_start = time.time()
        try:
            # Direct In-Memory Function Call
            result_payload = agent_func(job_id)
            step_duration = time.time() - step_start

            pipeline_state[agent_name] = result_payload

            safe_print(f"   ✅ {step_str} [{job_id}] {agent_name} COMPLETED (In-Memory Execution, Time: {step_duration:.2f}s)")
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
            safe_print(f"   ❌ {step_str} [{job_id}] {agent_name} FAILED / EXCEPTION: {err}")
            summary_results.append({
                "step": step_str,
                "lifecycle": lifecycle_name,
                "name": agent_name,
                "status": "FAILED",
                "code": 1,
                "time": f"{step_duration:.2f}s"
            })
            safe_print(f"\n🛑 Pipeline Execution Halted for {job_id} due to failure in {agent_name} (Step {idx}/{total_steps})")
            return False

    total_pipeline_time = time.time() - overall_start_time
    safe_print("\n" + "=" * 80)
    safe_print(f"🎉 IN-MEMORY RECRUITMENT PIPELINE FOR {job_id} COMPLETED SUCCESSFULLY!")
    safe_print(f"⏱️ Total Execution Time: {total_pipeline_time:.2f} seconds")
    safe_print("=" * 80)
    for item in summary_results:
        safe_print(f"  • [{job_id}] {item['step']} {item['name']:<42} -> STATUS: {item['status']} ({item['time']})")
    safe_print("=" * 80 + "\n")
    return True


def discover_job_workspaces() -> list[str]:
    """สแกนหาโฟลเดอร์ใบงานทั้งหมดใน workspaces/ ที่มีไฟล์ is0_job_ticket.json"""
    workspaces_dir = Path(root_dir) / "workspaces"
    job_ids = []
    if workspaces_dir.exists():
        for folder in sorted(workspaces_dir.iterdir()):
            if folder.is_dir():
                ticket_path = folder / "01_specs" / "is0_job_ticket.json"
                if ticket_path.exists():
                    job_ids.append(folder.name)
    return job_ids


def process_single_job(job_id: str) -> bool:
    """ประมวลผลทั้ง 13 Agents สำหรับ Job Ticket เดียวผ่าน In-Memory Pipeline"""
    safe_print(f"🛸 [Orchestrator Thread] รับไม้ผลัด Job: {job_id} กำลังเข้าสู่ Workspace...")

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
                f"Contact Info: {job_data.get('contact_info', job_data.get('contact', '-'))}\n"
                f"Headcount: {job_data.get('headcount', 1)}\n"
                f"Budget: {job_data.get('salary_budget', job_data.get('budget'))}\n"
                f"Timeline/Target Start: {job_data.get('target_start_date', job_data.get('timeline'))}\n"
                f"Remarks: {job_data.get('remarks', '-')}\n"
            )

    return run_orchestrated_pipeline(job_id)


def main():
    parser = argparse.ArgumentParser(description="Multi-Role Concurrent Recruitment Orchestrator Engine")
    parser.add_argument("jobs", nargs="*", help="รายชื่อ Job IDs ที่ต้องการประมวลผลพร้อมกัน (เช่น JOB-VERIFY-2026 JOB-DATA-2026)")
    parser.add_argument("--all", action="store_true", help="สแกนประมวลผลทุก Job Ticket ใน workspaces/")
    parser.add_argument("--workers", type=int, default=3, help="จำนวน Threads สูงสุดสำหรับ Concurrent Execution (default: 3)")
    args = parser.parse_args()

    job_ids = args.jobs

    if args.all:
        job_ids = discover_job_workspaces()
        print(f"🔍 [Orchestrator] ตรวจพบ {len(job_ids)} Workspaces จากการสแกน --all: {job_ids}")

    if not job_ids:
        print("❌ [Orchestrator] ขัดข้อง: ไม่พบ Job ID สำหรับประมวลผล (กรุณาระบุ Job ID หรือใช้ --all)")
        sys.exit(1)

    if len(job_ids) == 1:
        # Run single job synchronously
        success = process_single_job(job_ids[0])
        if not success:
            sys.exit(1)
    else:
        print(f"🚀 [Multi-Role Orchestrator] เริ่มประมวลผลแบบ Concurrent สำหรับ {len(job_ids)} ตำแหน่งงานพร้อมกัน (Workers: {args.workers})")
        print("=" * 80)
        
        start_time = time.time()
        results = {}
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_job = {executor.submit(process_single_job, jid): jid for jid in job_ids}
            for future in as_completed(future_to_job):
                jid = future_to_job[future]
                try:
                    success = future.result()
                    results[jid] = "PASSED" if success else "FAILED"
                except Exception as exc:
                    results[jid] = f"FAILED ({exc})"

        total_time = time.time() - start_time
        print("\n" + "=" * 80)
        print("🎉 MULTI-ROLE CONCURRENT ORCHESTRATION COMPLETED!")
        print(f"⏱️ Total Execution Time: {total_time:.2f} seconds")
        print("=" * 80)
        for jid, status in results.items():
            print(f"  • Workspace: {jid:<25} ➔ Status: {status}")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    main()