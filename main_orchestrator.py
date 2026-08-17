import os
import time
import subprocess
import sys
from datetime import datetime

# บังคับ Terminal ให้อ่านภาษาไทย/อีโมจิได้
sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# ⚙️ Configuration & Pipeline
# ==========================================
# STREAMING_CHUNK: Defining Pipeline Stages
PIPELINE_STAGES = [
    {
        "module": "agent_1_requirement_analyzer.py",
        "input_file": "payloads/is0_hiring_request.txt",      
        "output_file": "payloads/is1_job_description.json"
    },
    {
        "module": "agent_2_sourcing_strategist.py",
        "input_file": "payloads/is1_job_description.json",    
        "output_file": "payloads/is2_sourcing_plan.json"
    },
    {
        "module": "agent_3_content_broadcaster.py",
        "input_file": "payloads/is2_sourcing_plan.json",
        "output_file": "payloads/is3_job_postings.json"
    },
    {
        "module": "agent_4_resume_screener.py",
        "input_file": "payloads/is3_job_postings.json",
        "output_file": "payloads/is4_shortlisted_candidates.json"
    },
    {
        "module": "agent_5_interview_scheduler.py",
        "input_file": "payloads/is4_shortlisted_candidates.json",
        "output_file": "payloads/is5_interview_prep.json"
    },
    {
        "module": "agent_6_interview_evaluator.py",
        "input_file": "payloads/is5_interview_prep.json",
        "output_file": "payloads/is6_evaluation_result.json"
    },
    {
        "module": "agent_7_compliance_checker.py",
        "input_file": "payloads/is6_evaluation_result.json",
        "output_file": "payloads/is7_verification_status.json"
    },
    {
        "module": "agent_8_offer_negotiator.py",
        "input_file": "payloads/is7_verification_status.json",
        "output_file": "payloads/is8_offer_letter.json"
    },
    {
        "module": "agent_9_onboarding_planner.py",
        "input_file": "payloads/is8_offer_letter.json",
        "output_file": "payloads/is9_onboarding_plan.json"
    },
    {
        "module": "agent_10_talent_profiler.py",
        "input_file": "payloads/is9_onboarding_plan.json",
        "output_file": "payloads/is10_employee_profile.json"
    }
]

PAYLOAD_DIR = "payloads"
LOG_FILE = "orchestrator_log.txt"

# STREAMING_CHUNK: Setup Environment Function
def setup_environment():
    if not os.path.exists(PAYLOAD_DIR):
        os.makedirs(PAYLOAD_DIR)
        log_event("SYSTEM", f"Created directory: {PAYLOAD_DIR}")

# STREAMING_CHUNK: Logging Function
def log_event(agent_name, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{agent_name}] {message}"
    print(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# STREAMING_CHUNK: Run Agent Function
def run_agent(module_name, input_file, output_file):
    log_event("ORCHESTRATOR", f"Triggering {module_name}...")
    
    cmd = ["python", module_name, input_file, output_file]

    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='utf-8'
        )
        if result.stdout:
            print(result.stdout.strip())
        log_event(module_name, "EXECUTION SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        log_event(module_name, f"CRITICAL ERROR: {e.stderr}")
        return False

# STREAMING_CHUNK: Main Pipeline Logic
def run_pipeline():
    log_event("SYSTEM", "Starting 24/7 HR Agentic Pipeline Monitor...")
    
    while True:
        # Check if the initial input file exists
        if os.path.exists(PIPELINE_STAGES[0]["input_file"]):
            log_event("SYSTEM", "New Hiring Request detected. Initiating Pipeline.")
            
            pipeline_broken = False
            for stage in PIPELINE_STAGES:
                # 1. Check if input file exists
                if not os.path.exists(stage["input_file"]):
                    break # Stop and wait for the previous stage to finish
                
                # 2. If input exists, but output doesn't, run the agent
                if not os.path.exists(stage["output_file"]):
                    success = run_agent(stage["module"], stage["input_file"], stage["output_file"])
                    if not success:
                        log_event("ORCHESTRATOR", f"Pipeline halted at {stage['module']} due to error.")
                        pipeline_broken = True
                        break 
            
            # If all stages completed successfully, rename the input file to prevent re-running
            if not pipeline_broken and os.path.exists(PIPELINE_STAGES[-1]["output_file"]):
                log_event("SYSTEM", "🎉 HR PIPELINE COMPLETED SUCCESSFULLY! 🎉")
                os.rename(PIPELINE_STAGES[0]["input_file"], f"{PAYLOAD_DIR}/is0_processed_{int(time.time())}.txt")
                
        time.sleep(5) 

# STREAMING_CHUNK: Main Execution Block
if __name__ == "__main__":
    setup_environment()
    try:
        run_pipeline()
    except KeyboardInterrupt:
        log_event("SYSTEM", "Orchestrator terminated by user.")