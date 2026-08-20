import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

AGENTS_SEQUENCE = [
    ("Agent 0 (Orchestrator Init)", "main_orchestrator.py"),
    ("Agent 1 (Job Description)", "engine/agent_1_job_description.py"),
    ("Agent 2 (Sourcing Strategist)", "engine/agent_2_sourcing_strategist.py"),
    ("Agent 3 (Content Broadcaster)", "engine/agent_3_content_broadcaster.py"),
    ("Agent 4 (Resume Screener)", "engine/agent_4_resume_screener.py"),
    ("Agent 5 (Interview Scheduler)", "engine/agent_5_interview_scheduler.py"),
    ("Agent 6 (Interview Evaluator)", "engine/agent_6_interview_evaluator.py"),
    ("Agent 7 (Compliance Checker)", "engine/agent_7_compliance_checker.py"),
    ("Agent 8 (Offer Negotiator)", "engine/agent_8_offer_negotiator.py"),
    ("Agent 9 (Onboarding Planner)", "engine/agent_9_onboarding_planner.py"),
    ("Agent 10 (Talent Profiler)", "engine/agent_10_talent_profiler.py"),
    ("Agent 11 (Database Sync)", "engine/agent_11_database_sync.py"),
    ("Agent 12 (Executive Telegram Notifier)", "engine/agent_12_telegram_notify.py"),
]

def run_full_pipeline(job_id: str):
    print("=" * 80)
    print(f"🚀 STARTING FULL 12-AGENT PIPELINE EXECUTION FOR WORKSPACE: {job_id}")
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    summary = []

    for name, rel_script_path in AGENTS_SEQUENCE:
        script_path = os.path.join(root_dir, rel_script_path)
        print(f"▶️ Executing Step: {name}")
        print(f"   Script: {rel_script_path}")

        start_t = time.time()
        proc = subprocess.run(
            [sys.executable, script_path, job_id],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        elapsed = time.time() - start_t

        print(proc.stdout)
        if proc.stderr:
            filtered_err = "\n".join([line for line in proc.stderr.splitlines() if "Warning" not in line and "warning" not in line])
            if filtered_err.strip():
                print(f"   ⚠️ Stderr: {filtered_err.strip()}")

        if proc.returncode == 0:
            print(f"   ✅ {name} PASSED (Exit Code: 0, Time: {elapsed:.2f}s)\n")
            summary.append({"step": name, "status": "PASSED", "code": 0, "time": f"{elapsed:.2f}s"})
        else:
            print(f"   ❌ {name} FAILED (Exit Code: {proc.returncode})\n")
            summary.append({"step": name, "status": "FAILED", "code": proc.returncode, "time": f"{elapsed:.2f}s"})
            sys.exit(proc.returncode)

    print("=" * 80)
    print("🎉 FULL PIPELINE EXECUTION SUMMARY (ALL 12 AGENTS COMPLETED)")
    print("=" * 80)
    for item in summary:
        print(f"  • {item['step']:<40} -> STATUS: {item['status']} (Exit Code {item['code']}, Time: {item['time']})")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    job_id = sys.argv[1] if len(sys.argv) > 1 else "JOB-VERIFY-2026"
    run_full_pipeline(job_id)
