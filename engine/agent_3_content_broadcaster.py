import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
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

if not GEMINI_API_KEY:
    print("❌ [Agent 3] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Multi-Channel Job Postings ---

class LinkedInPost(BaseModel):
    headline: str = Field(description="Headline โพสต์ทางการระดับองค์กร (Executive Headline)")
    narrative_hook: str = Field(description="เปิดเรื่องดึงดูดความสนใจ (Narrative Hook)")
    key_highlights: list[str] = Field(description="จุดเด่นของตำแหน่งและภารกิจหลัก (Key Highlights)")
    key_benefits: list[str] = Field(description="สวัสดิการและผลประโยชน์เด่น (Standout Benefits)")
    call_to_action: str = Field(description="ข้อความเชิญชวนสมัครและช่องทางติดต่อ (Call to Action)")
    full_post_text: str = Field(description="เนื้อหาโพสต์ฉบับสมบูรณ์สำหรับ LinkedIn พร้อมใช้งาน")


class FacebookCommunityPost(BaseModel):
    headline: str = Field(description="หัวข้อโพสต์แนวเข้าถึงง่าย อ่านสะดวกบนมือถือ พร้อมอิโมจิ")
    body: str = Field(description="เนื้อหาจัดหมวดหมู่ชัดเจน อ่านง่าย อ่านสบายตาบน mobile")
    hashtags: list[str] = Field(description="แฮชแท็กตรงสายงานและกลุ่มเป้าหมาย")
    call_to_action: str = Field(description="คำเชิญชวนให้ทักแชทหรือส่งเรซูเม่")
    full_post_text: str = Field(description="เนื้อหาโพสต์ฉบับสมบูรณ์สำหรับ Facebook พร้อมใช้งาน")


class ShortMessagingAd(BaseModel):
    platform_target: str = Field(description="แพลตฟอร์มเป้าหมาย (LINE OA / Telegram / WhatsApp)")
    headline: str = Field(description="หัวข้อสั้นกระชับได้ใจความ")
    summary_bullet_points: list[str] = Field(description="จุดเด่น 3-4 ข้อ (ตำแหน่ง เงินเดือน สถานที่ ทักษะหลัก)")
    call_to_action: str = Field(description="CTA กระตุ้นให้คลิกหรือติดต่อทันที")
    full_ad_text: str = Field(description="ข้อความสั้นฉบับสมบูรณ์พร้อมส่งต่อทันที")


class JobBoardTeaser(BaseModel):
    summary_teaser: str = Field(description="ข้อความสรุปย่อ 2-3 บรรทัด สำหรับ Meta Description หรือพรีวิวบนเว็บหางาน")


class JobPostingsPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน (Position Title)")
    linkedin_post: LinkedInPost = Field(description="1. โพสต์ทางการระดับองค์กรบน LinkedIn")
    facebook_community_post: FacebookCommunityPost = Field(description="2. โพสต์แนวเข้าถึงง่ายสำหรับ Facebook Community")
    short_messaging_ad: ShortMessagingAd = Field(description="3. ข้อความสั้นกระชับสำหรับ LINE OA / Telegram / WhatsApp")
    job_board_teaser: JobBoardTeaser = Field(description="4. ข้อความสรุปย่อสำหรับ Job Board Teaser / Meta Description")
    recommended_posting_schedule: str = Field(description="คำแนะนำช่วงเวลาที่เหมาะสมในการโพสต์แต่ละแพลตฟอร์ม")


def format_formal_markdown(postings: JobPostingsPayload) -> str:
    """แปลง Copywriting ทั้งหมดเป็นเอกสาร Markdown จัดหน้าสวยงาม พร้อมคัดลอกใช้งาน"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    return f"""# 📢 MULTI-CHANNEL RECRUITMENT COPYWRITING PACK

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{postings.job_id}`  
> **Target Position:** **{postings.position_title}**  
> **Document Status:** Ready for Broadcasting  
> **Date Generated:** {today_str}  

---

## 💼 1. LinkedIn Corporate Official Post

```text
{postings.linkedin_post.full_post_text}
```

---

## 👥 2. Facebook Community & Group Post

```text
{postings.facebook_community_post.full_post_text}
```

---

## 📱 3. Short Messaging Ad (LINE OA / Telegram / WhatsApp)

```text
{postings.short_messaging_ad.full_ad_text}
```

---

## 🌐 4. Job Board Teaser & Meta Description

> {postings.job_board_teaser.summary_teaser}

---

## ⏰ Recommended Posting Schedule

> {postings.recommended_posting_schedule}

---

> *This Recruitment Copywriting Pack was generated automatically by Agent 3 (Multi-Channel Recruitment Copywriting Generator).*  
> *Ready for marketing execution and talent acquisition broadcasting.*
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 3] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])

    jd_json_path = specs_dir / "is1_output_job_description.json"
    strategy_json_path = specs_dir / "is2_output_sourcing_strategy.json"
    jd_txt_path = specs_dir / "is1_output_job_description.txt"
    ticket_json_path = specs_dir / "is0_job_ticket.json"
    input_spec_path = specs_dir / "is1_input_spec.txt"

    # Dual Output Paths
    json_output_path = specs_dir / "is3_output_job_postings.json"
    md_output_path = specs_dir / "is3_job_postings_ready.md"

    print(f"🚀 [Agent 3] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    context_parts = []
    if jd_json_path.exists():
        with open(jd_json_path, "r", encoding="utf-8") as f:
            context_parts.append(f"--- Job Description (IS1) ---\n{f.read()}")
    elif jd_txt_path.exists():
        with open(jd_txt_path, "r", encoding="utf-8") as f:
            context_parts.append(f"--- Job Description (IS1) ---\n{f.read()}")

    if strategy_json_path.exists():
        with open(strategy_json_path, "r", encoding="utf-8") as f:
            context_parts.append(f"--- Sourcing Strategy (IS2) ---\n{f.read()}")
    elif ticket_json_path.exists() and not context_parts:
        with open(ticket_json_path, "r", encoding="utf-8") as f:
            context_parts.append(f"--- Job Ticket (IS0) ---\n{f.read()}")
    elif input_spec_path.exists() and not context_parts:
        with open(input_spec_path, "r", encoding="utf-8") as f:
            context_parts.append(f"--- Input Spec ---\n{f.read()}")

    if not context_parts:
        err_msg = f"ไม่พบไฟล์ข้อมูลนำเข้าใน {specs_dir}"
        print(f"❌ [Agent 3] ขัดข้อง: {err_msg}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise RuntimeError(err_msg)

    combined_input = "\n\n".join(context_parts)
    print(f"📄 [Agent 3] ดึงข้อมูล Job Description และ Sourcing Strategy สำเร็จ")

    system_instruction = (
        "คุณคือ Agent 3 (Multi-Channel Recruitment Copywriter & Talent Acquisition Marketer)\n"
        "หน้าที่ของคุณคือการนำข้อมูล Job Description (IS1) และ Sourcing Strategy (IS2) มาแต่ง Copywriting ประกาศรับสมัครงาน 4 รูปแบบระดับมืออาชีพ:\n"
        "1. linkedin_post: โพสต์ทางการระดับองค์กร มี Headline, Narrative Hook, Key Highlights, สวัสดิการเด่น และ Call to Action (CTA)\n"
        "2. facebook_community_post: โพสต์แนวเข้าถึงง่าย อ่านสะดวกบนมือถือ มีอิโมจิประกอบพอเหมาะ จัดหมวดหมู่ชัดเจน และแฮชแท็กตรงสายงาน\n"
        "3. short_messaging_ad: ข้อความสั้นกระชับสำหรับกระจายผ่าน LINE OA, Telegram Channel หรือ WhatsApp\n"
        "4. job_board_teaser: ข้อความสรุปย่อ 2-3 บรรทัด สำหรับใช้เป็น Meta Description บนเว็บหางาน\n"
        "พร้อมทั้งให้คำแนะนำ recommended_posting_schedule ช่วงเวลาที่เหมาะสมที่สุดในการโพสต์\n\n"
        "โปรดเขียน Copywriting ให้มีพลัง ดึงดูดความสนใจ ตรงกลุ่มเป้าหมาย และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลนำเข้าสำหรับสร้าง Copywriting รับสมัครงาน:
- Job ID: {job_id}
{combined_input}

กรุณาเขียน Copywriting รับสมัครงานทั้ง 4 รูปแบบให้ครบถ้วนสมบูรณ์ตาม Schema
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=JobPostingsPayload,
                temperature=0.6,
            ),
        )

        postings_payload = JobPostingsPayload.model_validate_json(response.text)
        postings_payload.job_id = job_id

        json_str = postings_payload.model_dump_json(indent=2)
        ready_md = format_formal_markdown(postings_payload)

        # Safety Guards & File Operations
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(ready_md)

        print(f"✅ [Agent 3] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 3] บันทึกไฟล์ {md_output_path.name} (Ready Copywriting Pack) สำเร็จ")
        return postings_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 3] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e


if __name__ == "__main__":
    main()