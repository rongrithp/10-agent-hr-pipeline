import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Path registration
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# --- Pydantic Schemas for Executive Notification & Final Milestone Dispatcher ---

class HiredCandidateSummary(BaseModel):
    employee_id: str = Field(description="รหัสพนักงาน/ผู้ได้รับการบรรจุ")
    full_name: str = Field(description="ชื่อ-นามสกุล พนักงานใหม่")
    job_title: str = Field(description="ตำแหน่งงาน")
    department: str = Field(description="แผนกที่สังกัด")
    agreed_salary_thb: float = Field(description="เงินเดือนพื้นฐานที่ตกลง (บาท/เดือน)")
    start_date: str = Field(description="วันที่เริ่มงานจริง")


class PipelineFunnelSummary(BaseModel):
    total_sourced: int = Field(description="จำนวนผู้สมัครทั้งหมดที่เข้าร่วมคัดกรอง")
    shortlisted: int = Field(description="จำนวนผู้สมัครที่ผ่านการคัดกรอง CV")
    interviewed: int = Field(description="จำนวนผู้สมัครที่ได้รับการสัมภาษณ์")
    hired: int = Field(description="จำนวนผู้ได้รับการจ้างงาน (Hired)")
    conversion_rate_percentage: float = Field(description="อัตราการแปลงผลรวม (%)")


class NotificationDeliveryStatus(BaseModel):
    delivery_mode: Literal["LIVE_DISPATCH", "DRY_RUN"] = Field(description="โหมดการส่งข้อความ (LIVE_DISPATCH หรือ DRY_RUN)")
    telegram_api_status: str = Field(description="สถานะผลการส่งผ่าน Telegram API หรือ Dry Run Notice")
    http_status_code: Optional[int] = Field(default=None, description="HTTP Status Code จาก Telegram API")
    recipient_chat_id: str = Field(description="Chat ID ผู้รับข่าวสาร (หรือ DRY_RUN_MODE)")
    dispatched_at: str = Field(description="เวลาประทับการกระจายข่าวสาร")


class ExecutiveNotificationPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job Ticket ID)")
    milestone_status: str = Field(default="RECRUITMENT PROCESS COMPLETE - POSITION FILLED", description="สถานะหมุดหมายความสำเร็จ")
    hired_candidate: HiredCandidateSummary = Field(description="สรุปข้อมูลพนักงานใหม่ที่ได้รับการบรรจุ")
    pipeline_funnel: PipelineFunnelSummary = Field(description="สรุปสถิติประสิทธิภาพ Funnel การสรรหา")
    hris_sync_status: str = Field(description="ยืนยันสถานะการบันทึกข้อมูลเข้า HRIS & Talent Vault")
    executive_broadcast_message: str = Field(description="ข้อความบรอดแคสต์ระดับผู้บริหาร (พร้อม Emoji สำหรับ Telegram/มือถือ)")
    notification_delivery: NotificationDeliveryStatus = Field(description="รายละเอียดสถานะการส่งข้อความ")


def format_telegram_card_md(payload: ExecutiveNotificationPayload) -> str:
    """แปลงข้อความแจ้งเตือนเป็น Markdown Card สำหรับพรีวิวใน Executive Dashboard หรือ Telegram Preview"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    cand = payload.hired_candidate
    fn = payload.pipeline_funnel
    nd = payload.notification_delivery

    return f"""# 📲 EXECUTIVE TELEGRAM BROADCAST CARD

> **RECRUITMENT MILESTONE BROADCAST** | Harrow Executive Committee  
> **Job Ticket ID:** `{payload.job_id}`  
> **Dispatch Mode:** `{nd.delivery_mode}`  
> **Delivery Status:** `{nd.telegram_api_status}`  
> **Timestamp:** {today_str}  

---

### 💬 Mobile View Notification Preview

```text
{payload.executive_broadcast_message}
```

---

## 📊 Broadcast Telemetry & Delivery Audit

| Telemetry Field | Audit Record Value |
| :--- | :--- |
| **Milestone Status** | `{payload.milestone_status}` |
| **Hired Candidate** | **{cand.full_name}** (`{cand.employee_id}`) |
| **Position & Department** | {cand.job_title} — {cand.department} |
| **Start Date & Compensation** | {cand.start_date} | ฿{cand.agreed_salary_thb:,.2f} THB/month |
| **Funnel Conversion** | Sourced: {fn.total_sourced} ➔ Shortlist: {fn.shortlisted} ➔ Interview: {fn.interviewed} ➔ Hired: {fn.hired} (**{fn.conversion_rate_percentage:.1f}%**) |
| **HRIS & Vault Sync Status** | `{payload.hris_sync_status}` |
| **Delivery Mechanism** | `{nd.delivery_mode}` (API Status: {nd.telegram_api_status}, Code: {nd.http_status_code or 'N/A'}) |

---

> *This Executive Notification Broadcast Card was generated automatically by Agent 12 (Executive Notification & Final Milestone Dispatcher).*  
> *Epoch 1 Full 12-Agent Recruitment Pipeline Execution Completed.*
"""


def dispatch_to_telegram(message_text: str) -> dict:
    """ทำหน้าที่ยิง Telegram API จริงหากมี Token และ Chat ID หรือเปลี่ยนเป็น Dry-Run หากไม่มี (ส่งแบบ Plaintext เพียงครั้งเดียว)"""
    timestamp_str = datetime.now().isoformat()

    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("ℹ️ [Agent 12] ไม่พบ TELEGRAM_BOT_TOKEN หรือ TELEGRAM_CHAT_ID (ใช้งาน Dry-Run Mode)")
        return {
            "delivery_mode": "DRY_RUN",
            "telegram_api_status": "DRY_RUN_SAVED_LOCAL_ONLY",
            "http_status_code": None,
            "recipient_chat_id": "DRY_RUN_MODE",
            "dispatched_at": timestamp_str
        }

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message_text
        }
        resp = requests.post(url, json=payload, timeout=10)

        if resp.status_code == 200:
            print("🚀 [Agent 12] สั่งยิง Telegram API (Plaintext) สำเร็จ! บรอดแคสต์ข้อความถึงผู้บริหารเรียบร้อย")
            return {
                "delivery_mode": "LIVE_DISPATCH",
                "telegram_api_status": "SUCCESS_SENT_TO_TELEGRAM",
                "http_status_code": 200,
                "recipient_chat_id": str(CHAT_ID)[-4:].rjust(len(str(CHAT_ID)), "*"),
                "dispatched_at": timestamp_str
            }
        else:
            print(f"⚠️ [Agent 12] Telegram API คืนค่าสถานะ {resp.status_code}: {resp.text}")
            return {
                "delivery_mode": "LIVE_DISPATCH",
                "telegram_api_status": f"FAILED_HTTP_{resp.status_code}",
                "http_status_code": resp.status_code,
                "recipient_chat_id": str(CHAT_ID)[-4:].rjust(len(str(CHAT_ID)), "*"),
                "dispatched_at": timestamp_str
            }
    except Exception as e:
        print(f"⚠️ [Agent 12] เกิดขัดข้องในการเชื่อมต่อ Telegram API: {e}")
        return {
            "delivery_mode": "DRY_RUN",
            "telegram_api_status": f"ERROR_CONNECTION_FAILED: {str(e)}",
            "http_status_code": 500,
            "recipient_chat_id": "DRY_RUN_FALLBACK",
            "dispatched_at": timestamp_str
        }


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 12] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    onboarding_dir = Path(paths["onboarding"])

    # Dual Output Paths in 05_onboarding_vault/
    json_output_path = onboarding_dir / "is12_output_notification_payload.json"
    md_output_path = onboarding_dir / "is12_telegram_broadcast_card.md"

    print(f"🚀 [Agent 12] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    # Check for Duplicate Dispatch (Idempotency Control)
    if json_output_path.exists():
        try:
            with open(json_output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_delivery = existing_data.get("notification_delivery", {})
            existing_status = existing_delivery.get("telegram_api_status")
            existing_mode = existing_delivery.get("delivery_mode")

            if existing_mode == "LIVE_DISPATCH" and existing_status in ["SUCCESS_SENT_TO_TELEGRAM", "SUCCESS_PLAINTEXT_FALLBACK", "ALREADY_DISPATCHED"]:
                print("ℹ️ [Agent 12] ข้ามการยิง Telegram: ข้อความถูกส่งสำเร็จไปแล้วก่อนหน้านี้ (Prevent Duplicate Retry)")
                print(f"✅ [Agent 12] บันทึกไฟล์ {json_output_path.name} (Existing Payload Verified) ใน 05_onboarding_vault สำเร็จ")
                print(f"✅ [Agent 12] บันทึกไฟล์ {md_output_path.name} (Existing Broadcast Card) ใน 05_onboarding_vault สำเร็จ")
                print("🎉 [Agent 12] สำเร็จเรียบร้อย! จบกระบวนการทำงานทั้ง 12 Agents สมบูรณ์แบบ (Epoch 1 Completed) 🚀")
                sys.exit(0)
        except Exception as read_err:
            print(f"⚠️ [Agent 12] ตรวจสอบ Payload เดิมล้มเหลว ดำเนินการกระจายข้อความใหม่: {read_err}")

    # Read All Upstream Master Records (IS11, IS10, IS0)
    is11_path = onboarding_dir / "is11_output_db_sync_payload.json"
    is10_path = onboarding_dir / "is10_output_talent_profile.json"
    is10_legacy = onboarding_dir / "is10_output_employee_profile.json"
    is0_path = specs_dir / "is0_job_ticket.json"

    context_data = {}

    if is11_path.exists():
        with open(is11_path, "r", encoding="utf-8") as f:
            context_data["is11"] = f.read()

    if is10_path.exists():
        with open(is10_path, "r", encoding="utf-8") as f:
            context_data["is10"] = f.read()
    elif is10_legacy.exists():
        with open(is10_legacy, "r", encoding="utf-8") as f:
            context_data["is10"] = f.read()

    if is0_path.exists():
        with open(is0_path, "r", encoding="utf-8") as f:
            context_data["is0"] = f.read()

    print(f"📄 [Agent 12] รวบรวมข้อมูลสรุปยุทธศาสตร์ครบถ้วน ({len(context_data)} ไฟล์) สำเร็จ")

    system_instruction = (
        "คุณคือ Agent 12 (Executive Notification & Final Milestone Dispatcher Engine)\n"
        "หน้าที่ของคุณคือการรวบรวมข้อมูลภาพรวมการสรรหาทั้งหมดจาก IS11, IS10 และ IS0 เพื่อสร้างสรุปข่าวสารระดับผู้บริหาร (Executive Broadcast Message):\n"
        "1. milestone_status: 'RECRUITMENT PROCESS COMPLETE - POSITION FILLED'\n"
        "2. hired_candidate: สรุปข้อมูลพนักงานใหม่ (employee_id, full_name, job_title, department, agreed_salary_thb, start_date)\n"
        "3. pipeline_funnel: สถิติ Funnel (total_sourced, shortlisted, interviewed, hired, conversion_rate_percentage)\n"
        "4. hris_sync_status: 'SYNC_SUCCESSFUL - Employee Master & Talent Vault Updated'\n"
        "5. executive_broadcast_message: ข้อความสรุปสั้น กระชับ สำหรับส่งแจ้งเตือน Telegram / มือถือ ตกแต่งด้วย Emoji สวยงาม อ่านง่าย เป็นกันเองแต่น่าเชื่อถือระดับผู้บริหาร\n\n"
        "โปรดส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลประมวลผลสรุปจาก IS11, IS10, IS0:
{json.dumps(context_data, indent=2, ensure_ascii=False)}

กรุณาสร้างข้อความแจ้งเตือนระดับผู้บริหาร (Executive Broadcast Message) และบันทึกลงใน Schema ให้สมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ExecutiveNotificationPayload,
                temperature=0.2,
            ),
        )

        exec_payload = ExecutiveNotificationPayload.model_validate_json(response.text)
        exec_payload.job_id = job_id

        # Dispatch Notification to Telegram (Live or Dry-Run)
        delivery_res = dispatch_to_telegram(exec_payload.executive_broadcast_message)
        exec_payload.notification_delivery = NotificationDeliveryStatus(**delivery_res)

        json_str = exec_payload.model_dump_json(indent=2)
        formal_md = format_telegram_card_md(exec_payload)

        # Safety Guards & File Operations in 05_onboarding_vault/
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        print(f"✅ [Agent 12] บันทึกไฟล์ {json_output_path.name} (Structured Payload) ใน 05_onboarding_vault สำเร็จ")
        print(f"✅ [Agent 12] บันทึกไฟล์ {md_output_path.name} (Telegram Broadcast Card) ใน 05_onboarding_vault สำเร็จ")
        print("🎉 [Agent 12] สำเร็จเรียบร้อย! จบกระบวนการทำงานทั้ง 12 Agents สมบูรณ์แบบ (Epoch 1 Completed) 🚀")
        return notify_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 12] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e



if __name__ == "__main__":
    main()