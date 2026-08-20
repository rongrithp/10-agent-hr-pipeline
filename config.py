import os
from pathlib import Path

# 1. พิกัด Root (Base Directory) แบบ Dynamic pathlib
BASE_DIR = Path(__file__).resolve().parent

# 2. ไดเรกทอรีหลักของระบบ (Production Directory Structure)
ENGINE_DIR = BASE_DIR / "engine"
WORKSPACES_DIR = BASE_DIR / "workspaces"
CREDENTIALS_DIR = BASE_DIR / "credentials"
LOGS_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
ENV_PATH = BASE_DIR / ".env"

# 3. พิกัดไฟล์ Credentials & Tokens
GCP_CREDENTIALS_PATH = CREDENTIALS_DIR / "gcp_credentials.json"
CREDENTIALS_GMAIL_PATH = CREDENTIALS_DIR / "credentials_gmail.json"
TOKEN_SHEETS_PATH = CREDENTIALS_DIR / "token_sheets.json"
TOKEN_GMAIL_PATH = CREDENTIALS_DIR / "token_gmail.json"

# สร้างโฟลเดอร์โครงสร้างหลักอัตโนมัติหากยังไม่มีอยู่ (Self-Healing Core Structure)
for folder in [WORKSPACES_DIR, CREDENTIALS_DIR, LOGS_DIR, DOCS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

def ensure_parent_dir(file_path: str | Path) -> Path:
    """Safety Guard: ตรวจสอบและสร้าง Parent Directory ของไฟล์ที่ต้องการเขียนเสมอ"""
    path_obj = Path(file_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj

def get_workspace(job_id: str) -> dict:
    """ฟังก์ชันสร้างและคืนค่าพิกัดโฟลเดอร์แยกตาม Job ID ตาม Production Lifecycle Standard (Self-Healing Workspace)"""
    job_dir = WORKSPACES_DIR / job_id
    
    paths = {
        "root": str(job_dir),
        "specs": str(job_dir / "01_specs"),
        "dropzone": str(job_dir / "02_sourcing_dropzone"),
        "broadcasting_kits": str(job_dir / "03_broadcasting_kits"),
        "evaluations": str(job_dir / "03_evaluations"),
        "offers": str(job_dir / "04_offers_contracts"),
        "onboarding": str(job_dir / "05_onboarding_vault")
    }

    
    # สร้างโฟลเดอร์ Lifecycle ทั้ง 5 และ Root Workspace ทันทีที่มีการเรียกใช้
    for path_str in paths.values():
        Path(path_str).mkdir(parents=True, exist_ok=True)
            
    return paths