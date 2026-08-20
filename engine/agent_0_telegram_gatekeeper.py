import os
import sys
import json
import datetime
import subprocess
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

# [NEW ARCHITECTURE] ดึงแผนที่จากห้องเครื่อง
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config 
from dotenv import load_dotenv

# [Low-Level Actuator] บังคับท่อส่งข้อมูลให้เป็น UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# [NEW ARCHITECTURE] ชี้เป้ากุญแจ IP Shield ให้ถูกต้องจาก Root
load_dotenv(config.ENV_PATH)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("❌ CRITICAL ERROR: ขาด TELEGRAM_BOT_TOKEN หรือ GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)

# เชื่อมต่อสมองและ Actuator
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

SPREADSHEET_ID = '13f5p_vrtjihGeWms1UvE9oJcvnlUl3Ous4-kSeifsrw'
CREDENTIALS_FILE = str(config.GCP_CREDENTIALS_PATH)
JOB_TRACKER_SHEET_NAME = 'Job_Tracker'

GATEKEEPER_PROMPT = """
คุณคือ Agent 0 (HR Gatekeeper) หน้าที่ของคุณคือสัมภาษณ์ผู้ใช้เพื่อเก็บข้อมูลรับงานใหม่ (Hiring Request)
ข้อมูลที่ต้องเก็บให้ครบมี 7 ข้อ:
1. Client_Name (ชื่อลูกค้า/โรงเรียน)
2. Contact_Info (ช่องทางติดต่อลูกค้า/ผู้ประสานงาน)
3. Position (ตำแหน่งงาน)
4. Headcount (จำนวนคนที่รับ)
5. Salary_Budget (งบประมาณเงินเดือน)
6. Target_Start_Date (วันเริ่มงานเป้าหมาย/Timeline)
7. Remarks (หมายเหตุ/เงื่อนไขพิเศษ ถ้ามี)

กฎเหล็ก:
- ถ้าข้อมูลขาดให้ถามกลับอย่างสุภาพ
- ถ้าข้อมูลครบให้ตอบเป็น JSON Format อย่างเดียว ห้ามมีข้อความอื่นเจือปน:
{
  "client": "...",
  "contact_info": "...",
  "position": "...",
  "headcount": 1,
  "budget": "...",
  "target_start_date": "...",
  "remarks": "..."
}
"""

user_chats = {}
pending_jobs = {}

def get_chat_session(chat_id):
    if chat_id not in user_chats:
        user_chats[chat_id] = model.start_chat(history=[
            {"role": "user", "parts": [GATEKEEPER_PROMPT]},
            {"role": "model", "parts": ["รับทราบ"]}
        ])
    return user_chats[chat_id]

def sync_job_tracker(data):
    """บันทึก/อัปเดตข้อมูลใบงานลง Google Sheets แท็บ Job_Tracker ตามลำดับคอลัมน์ A ถึง N"""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"⚠️ [Agent 0] ไม่พบไฟล์กุญแจ {CREDENTIALS_FILE} ข้ามการอัปเดต Google Sheets ชั่วคราว")
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
            sheet = spreadsheet.worksheet(JOB_TRACKER_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠️ [Agent 0] ไม่พบชีท '{JOB_TRACKER_SHEET_NAME}' กำลังสร้างชีทใหม่...")
            sheet = spreadsheet.add_worksheet(title=JOB_TRACKER_SHEET_NAME, rows="100", cols="20")

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
        open_date = data.get("open_date", data.get("date", datetime.datetime.now().strftime("%Y-%m-%d")))
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
        
        # ดึง Workspace Path ผ่าน config.get_workspace เสมอ
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
            print(f"✅ [Agent 0] อัปเดตข้อมูลใบงาน {job_id} ลง Google Sheets แท็บ '{JOB_TRACKER_SHEET_NAME}' แถวที่ {found_row_idx} สำเร็จ")
        else:
            sheet.append_row(row_data)
            print(f"✅ [Agent 0] บันทึกใบงานใหม่ {job_id} ลง Google Sheets แท็บ '{JOB_TRACKER_SHEET_NAME}' สำเร็จ")
            
    except Exception as e:
        print(f"⚠️ [Agent 0] ไม่สามารถซิงค์ Google Sheets ได้: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🟢 [Agent 0 Online] ระบบ Sensory Gatekeeper พร้อมรับคำสั่งรับงานใหม่")
    chat_id = message.chat.id
    if chat_id in pending_jobs: del pending_jobs[chat_id]
    user_chats[chat_id] = model.start_chat(history=[
        {"role": "user", "parts": [GATEKEEPER_PROMPT]},
        {"role": "model", "parts": ["รับทราบ"]}
    ])

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    if call.data == "action_confirm":
        if chat_id in pending_jobs:
            data = pending_jobs[chat_id]
            job_id = data["job_id"]
            
            # [NEW ARCHITECTURE] ขอพิกัด Workspace จาก config และเอาไฟล์ไปวางใน specs
            paths = config.get_workspace(job_id)
            target_path = os.path.join(paths["specs"], "is0_job_ticket.json")
            
            # Safety Guard: สร้าง parent directory รองรับเสมอก่อนบันทึกไฟล์
            config.ensure_parent_dir(target_path)
            
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # ซิงค์ข้อมูลลง Google Sheets แท็บ Job_Tracker
            sync_job_tracker(data)

            bot.edit_message_text(f"✅ ยืนยันสำเร็จ! สร้างใบงาน {job_id} เรียบร้อย", chat_id=chat_id, message_id=call.message.message_id)
            print(f"🚀 [Agent 0] สร้าง Workspace สำเร็จ! กำลังเตะส่งไม้ผลัดให้ Orchestrator")
            
            # [NEW ARCHITECTURE] เตะปลุกยานแม่ด้วย Absolute Path และ Python ใน .venv
            next_agent = os.path.join(config.BASE_DIR, "main_orchestrator.py")
            subprocess.Popen([sys.executable, next_agent, job_id])
            
            del pending_jobs[chat_id]
            user_chats[chat_id] = model.start_chat(history=[{"role": "user", "parts": [GATEKEEPER_PROMPT]}, {"role": "model", "parts": ["รับทราบ"]}])
        else:
            bot.answer_callback_query(call.id, "❌ ข้อมูลหมดอายุ")
            
    elif call.data == "action_edit":
        if chat_id in pending_jobs: del pending_jobs[chat_id]
        bot.edit_message_text("⚠️ โปรดพิมพ์ข้อมูลที่ต้องการแก้ไขมาได้เลยครับ", chat_id=chat_id, message_id=call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text.strip()
    
    if chat_id in pending_jobs:
        bot.reply_to(message, "⚠️ กรุณากดปุ่ม **[✅ ยืนยัน]** หรือ **[✏️ แก้ไข]** จากข้อความด้านบนก่อนครับ")
        return

    chat_session = get_chat_session(chat_id)
    loading_msg = bot.reply_to(message, "⏳ Agent 0 กำลังรับเรื่องและวิเคราะห์ข้อมูล...")
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        response = chat_session.send_message(user_text)
        reply_text = response.text
        bot.delete_message(chat_id, loading_msg.message_id)
        
        if "{" in reply_text and "}" in reply_text:
            try:
                start_idx = reply_text.find("{")
                end_idx = reply_text.rfind("}") + 1
                json_str = reply_text[start_idx:end_idx]
                data = json.loads(json_str)
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                today_code = datetime.datetime.now().strftime("%Y%m%d")
                job_id = f"JOB-{today_code}-{str(message.message_id)[-3:]}"
                
                data["job_id"] = job_id
                data["status"] = "OPEN"
                data["current_stage"] = "OPEN"
                data["open_date"] = today
                data["date"] = today
                data["workspace_path"] = config.get_workspace(job_id)["root"]
                
                pending_jobs[chat_id] = data
                
                summary = (
                    f"⚠️ **[ระบบรอการอนุมัติ]**\n"
                    f"🆔 Job ID: {job_id}\n"
                    f"🏢 Client: {data.get('client', data.get('client_name'))}\n"
                    f"📞 Contact Info: {data.get('contact_info', data.get('requester', '-'))}\n"
                    f"🎯 Position: {data.get('position')}\n"
                    f"👥 Headcount: {data.get('headcount', 1)}\n"
                    f"💰 Budget: {data.get('budget')}\n"
                    f"📅 Target Start Date: {data.get('target_start_date', data.get('timeline'))}\n"
                    f"📝 Remarks: {data.get('remarks', '-')}"
                )
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("✅ ยืนยันการสร้างใบงาน", callback_data="action_confirm"), 
                    InlineKeyboardButton("✏️ ต้องการแก้ไข", callback_data="action_edit")
                )
                bot.send_message(chat_id, summary, reply_markup=markup)
                
            except Exception as e:
                bot.reply_to(message, f"❌ [Error] ระบบแปลงไฟล์ล้มเหลว: {e}")
        else:
            bot.reply_to(message, reply_text)
            
    except Exception as e:
        bot.reply_to(message, f"❌ [API Error] การเชื่อมต่อ AI ล้มเหลว: {e}")

def main(job_id: str = None) -> dict:
    if not job_id:
        if len(sys.argv) > 1:
            job_id = sys.argv[1].strip()
        else:
            job_id = "JOB-VERIFY-2026"

    print(f"🚀 [Agent 0] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")
    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])
    
    target_path = specs_dir / "is0_job_ticket.json"
    intake_payload_path = specs_dir / "is0_output_job_intake_payload.json"
    summary_card_path = specs_dir / "is0_intake_summary_card.md"
    input_spec_path = specs_dir / "is1_input_spec.txt"

    data = {}
    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"📄 [Agent 0] โหลดข้อมูล Intake Ticket จาก {target_path.name} สำเร็จ")
    elif intake_payload_path.exists():
        with open(intake_payload_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"📄 [Agent 0] โหลดข้อมูล Intake Payload จาก {intake_payload_path.name} สำเร็จ")
    else:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        data = {
            "job_id": job_id,
            "client": "Harrow International School",
            "contact_info": "HR Talent Acquisition Team",
            "position": "Lead AI Engineer",
            "headcount": 1,
            "budget": "150,000 THB",
            "target_start_date": "2026-09-01",
            "status": "OPEN",
            "current_stage": "OPEN",
            "open_date": today,
            "workspace_path": str(paths["root"]),
            "remarks": "Automated verification ticket"
        }
        config.ensure_parent_dir(target_path)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ [Agent 0] สร้างข้อมูล Intake Ticket ใหม่: {target_path.name}")

    # Dual Output Generation (.json + .md)
    config.ensure_parent_dir(intake_payload_path)
    with open(intake_payload_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    summary_md = f"""# 📋 Job Intake Summary Card (IS0)

- **Job ID**: `{data.get('job_id')}`
- **Client / Organization**: {data.get('client', '-')}
- **Position**: {data.get('position', '-')}
- **Headcount**: {data.get('headcount', 1)}
- **Salary Budget**: {data.get('budget', '-')}
- **Target Start Date**: {data.get('target_start_date', data.get('timeline', '-'))}
- **Contact Info**: {data.get('contact_info', '-')}
- **Remarks**: {data.get('remarks', '-')}

> *Authorized by Agent 0 (Telegram Gatekeeper)*
"""
    config.ensure_parent_dir(summary_card_path)
    with open(summary_card_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    # Input Spec for Agent 1
    config.ensure_parent_dir(input_spec_path)
    with open(input_spec_path, "w", encoding="utf-8") as f:
        f.write(
            f"Job ID: {data.get('job_id')}\n"
            f"Position: {data.get('position')}\n"
            f"Client: {data.get('client')}\n"
            f"Contact Info: {data.get('contact_info', '-')}\n"
            f"Headcount: {data.get('headcount', 1)}\n"
            f"Budget: {data.get('budget')}\n"
            f"Timeline/Target Start: {data.get('target_start_date', data.get('timeline'))}\n"
            f"Remarks: {data.get('remarks', '-')}\n"
        )

    sync_job_tracker(data)
    print(f"✅ [Agent 0] บันทึกไฟล์ {intake_payload_path.name} (Structured Payload) สำเร็จ")
    print(f"✅ [Agent 0] บันทึกไฟล์ {summary_card_path.name} (Summary Card) สำเร็จ")
    return data


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("JOB-"):
        main(sys.argv[1])
    else:
        print("🚀 [Agent 0] Gatekeeper (Enterprise Workspace Mode) is ONLINE...")
        bot.infinity_polling()