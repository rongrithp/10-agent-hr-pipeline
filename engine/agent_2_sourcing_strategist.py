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
from engine.resilience import generate_content_with_retry


if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(config.ENV_PATH)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ [Agent 2] CRITICAL ERROR: ขาด GEMINI_API_KEY ในไฟล์ .env")
    sys.exit(1)


# --- Pydantic Schemas for Sourcing Strategy ---

class CandidatePersona(BaseModel):
    target_title: str = Field(description="ชื่อตำแหน่งเป้าหมายและตำแหน่งเทียบเท่า (Target Job Titles)")
    years_of_experience: str = Field(description="ช่วงประสบการณ์การทำงานเป้าหมาย (Target Years of Experience)")
    industry_background: str = Field(description="อุตสาหกรรม/ธุรกิจเป้าหมาย (Target Industry & Background)")
    key_skills_and_competencies: list[str] = Field(description="ทักษะและความเชี่ยวชาญสำคัญ (Core Competencies)")
    behavioral_traits: list[str] = Field(description="พฤติกรรม วัฒนธรรมองค์กร และลักษณะนิสัย (Behavioral & Cultural Traits)")


class ChannelRecommendation(BaseModel):
    channel_name: str = Field(description="ชื่อช่องทาง/แพลตฟอร์ม (Channel/Platform Name)")
    priority: str = Field(description="ระดับความสำคัญ (Primary / Secondary)")
    rationale: str = Field(description="เหตุผลเชิงกลยุทธ์ในการเลือกช่องทางนี้ (Strategic Rationale)")


class BooleanSearchStrings(BaseModel):
    linkedin_recruiter_string: str = Field(description="ชุดคำค้นหา Boolean สำหรับ LinkedIn Recruiter / Talent Solutions")
    google_xray_string: str = Field(description="ชุดคำค้นหา Google X-Ray Search Syntax")
    generic_boolean_string: str = Field(description="ชุดคำค้นหา Boolean ทั่วไปสำหรับ Job Boards / CV Databases")


class HeadhuntingOutreachTemplate(BaseModel):
    subject_line: str = Field(description="หัวข้อข้อความ/อีเมลทักทาย (InMail / Email Subject Line)")
    message_body: str = Field(description="เนื้อหาข้อความทักทาย Cold Outreach ระดับพรีเมียม (Personalized Outreach Message)")
    call_to_action: str = Field(description="คำเชิญชวนให้ตอบกลับหรือนัดคุย (Call to Action)")


class TimelineMilestone(BaseModel):
    phase_name: str = Field(description="ชื่อระยะการดำเนินงาน (Phase Name)")
    timeframe: str = Field(description="ระยะเวลาที่ใช้ (Timeframe / Duration)")
    deliverables: list[str] = Field(description="ผลลัพธ์/เป้าหมายในระยะนี้ (Phase Deliverables)")


class Agent4ScreeningDirectives(BaseModel):
    must_have_keywords: list[str] = Field(description="คีย์เวิร์ดบังคับที่ต้องมีในเรซูเม่ (Must-have Keywords)")
    nice_to_have_keywords: list[str] = Field(description="คีย์เวิร์ดเสริมที่เพิ่มคะแนน (Nice-to-have Keywords)")
    red_flags: list[str] = Field(description="จุดสังเกต/ข้อควรระวัง/ข้อห้าม (Red Flags / Dealbreakers)")
    screening_guidance: str = Field(description="คำแนะนำพิเศษสำหรับ Agent 4 ในการคัดกรองเรซูเม่")


class SourcingStrategyPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน (Position Title)")
    candidate_persona: CandidatePersona = Field(description="1. Candidate Persona (โปรไฟล์ผู้สมัครเป้าหมาย)")
    recommended_channels: list[ChannelRecommendation] = Field(description="2. Recommended Channels (ช่องทางการสรรหา)")
    boolean_search_strings: BooleanSearchStrings = Field(description="3. Boolean Search Strings (ชุดคำค้นหา)")
    headhunting_outreach_template: HeadhuntingOutreachTemplate = Field(description="4. Headhunting Outreach Template (ข้อความทักทาย Cold Outreach)")
    timeline_and_milestones: list[TimelineMilestone] = Field(description="5. Timeline & Milestones (กำหนดการดำเนินงาน)")
    agent4_screening_directives: Agent4ScreeningDirectives = Field(description="6. Agent 4 Screening Directives (เกณฑ์คัดกรองสำหรับ Agent 4)")


def format_formal_markdown(strategy: SourcingStrategyPayload) -> str:
    """แปลงแผนกลยุทธ์การสรรหาเป็นเอกสาร Markdown ทางการ สวยงามระดับ Corporate-Grade"""
    persona = strategy.candidate_persona
    bools = strategy.boolean_search_strings
    outreach = strategy.headhunting_outreach_template
    directives = strategy.agent4_screening_directives

    skills_list = "\n".join([f"- {s}" for s in persona.key_skills_and_competencies])
    traits_list = "\n".join([f"- {t}" for t in persona.behavioral_traits])

    channels_table_rows = "\n".join([
        f"| **{c.channel_name}** | `{c.priority}` | {c.rationale} |"
        for c in strategy.recommended_channels
    ])

    timeline_rows = []
    for tm in strategy.timeline_and_milestones:
        delivs = ", ".join(tm.deliverables)
        timeline_rows.append(f"| **{tm.phase_name}** | {tm.timeframe} | {delivs} |")
    timeline_table_rows = "\n".join(timeline_rows)

    must_haves = "\n".join([f"- `{kw}`" for kw in directives.must_have_keywords])
    nice_haves = "\n".join([f"- `{kw}`" for kw in directives.nice_to_have_keywords])
    red_flags = "\n".join([f"- ⚠️ {rf}" for rf in directives.red_flags])

    today_str = datetime.now().strftime("%Y-%m-%d")

    return f"""# 🎯 CORPORATE SOURCING STRATEGY & HEADHUNTING PLAN

> **CONFIDENTIAL DOCUMENT** | Harrow Recruitment Process Automation  
> **Job Ticket ID:** `{strategy.job_id}`  
> **Target Position:** **{strategy.position_title}**  
> **Document Status:** Approved Strategy  
> **Date Generated:** {today_str}  

---

## 👤 1. Target Candidate Persona

| Parameter | Specification |
| :--- | :--- |
| **Target Titles** | **{persona.target_title}** |
| **Years of Experience** | {persona.years_of_experience} |
| **Industry Background** | {persona.industry_background} |

### 🛠️ Core Competencies & Key Skills
{skills_list}

### 🧠 Behavioral & Cultural Traits
{traits_list}

---

## 📢 2. Recommended Sourcing Channels & Priorities

| Channel / Platform | Priority | Strategic Rationale |
| :--- | :--- | :--- |
{channels_table_rows}

---

## 🔍 3. Boolean Search Strings & X-Ray Search Syntax

### 💼 LinkedIn Recruiter Search String
```text
{bools.linkedin_recruiter_string}
```

### 🌐 Google X-Ray Search Query
```text
{bools.google_xray_string}
```

### 📋 Generic Boolean Search Syntax
```text
{bools.generic_boolean_string}
```

---

## ✉️ 4. Executive Cold Outreach Template

> **Subject:** {outreach.subject_line}  
>  
> {outreach.message_body}  
>  
> **Call to Action:** *{outreach.call_to_action}*  

---

## 📅 5. Timeline & Key Milestones

| Phase | Timeframe | Deliverables |
| :--- | :--- | :--- |
{timeline_table_rows}

---

## 🛡️ 6. Agent 4 Screening Directives & Criteria

### ✅ Must-Have Keywords (Mandatory)
{must_haves}

### 🌟 Nice-to-Have Keywords (Bonus Points)
{nice_haves}

### 🚫 Red Flags & Dealbreakers
{red_flags}

### 💡 Screening Guidance for Agent 4
> {directives.screening_guidance}

---

> *This Sourcing Strategy document was generated automatically by Agent 2 (Corporate-Grade Sourcing Strategist).*  
> *Authorized for Talent Acquisition execution.*
"""


def main(job_id: str = None):
    if not job_id:
        if len(sys.argv) >= 2:
            job_id = sys.argv[1]
        else:
            print("❌ [Agent 2] ขัดข้อง: ไม่ได้รับ Job ID")
            raise ValueError("ไม่ได้รับ Job ID")

    paths = config.get_workspace(job_id)
    specs_dir = Path(paths["specs"])

    jd_json_path = specs_dir / "is1_output_job_description.json"
    jd_txt_path = specs_dir / "is1_output_job_description.txt"
    ticket_json_path = specs_dir / "is0_job_ticket.json"
    input_spec_path = specs_dir / "is1_input_spec.txt"

    # Dual Output Paths
    json_output_path = specs_dir / "is2_output_sourcing_strategy.json"
    md_output_path = specs_dir / "is2_sourcing_strategy_formal.md"

    print(f"🚀 [Agent 2] ตื่นขึ้นแล้ว! เข้าสู่ Workspace: {job_id}")

    input_data = ""
    source_name = ""

    if jd_json_path.exists():
        with open(jd_json_path, "r", encoding="utf-8") as f:
            input_data = f.read()
        source_name = jd_json_path.name
    elif jd_txt_path.exists():
        with open(jd_txt_path, "r", encoding="utf-8") as f:
            input_data = f.read()
        source_name = jd_txt_path.name
    elif ticket_json_path.exists():
        with open(ticket_json_path, "r", encoding="utf-8") as f:
            input_data = f.read()
        source_name = ticket_json_path.name
    elif input_spec_path.exists():
        with open(input_spec_path, "r", encoding="utf-8") as f:
            input_data = f.read()
        source_name = input_spec_path.name
    else:
        err_msg = f"ไม่พบไฟล์ Job Description หรือ Ticket ใน {specs_dir}"
        print(f"❌ [Agent 2] ขัดข้อง: {err_msg}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise RuntimeError(err_msg)

    print(f"📄 [Agent 2] อ่านข้อมูลนำเข้าจาก {source_name} สำเร็จ")

    system_instruction = (
        "คุณคือ Agent 2 (Corporate-Grade Sourcing Strategist & Executive Headhunter)\n"
        "รับข้อมูล Job Description มาวิเคราะห์เพื่อวางกลยุทธ์การสรรหาแคนดิเดตระดับพรีเมียม (Headhunting Strategy)\n"
        "ต้องวิเคราะห์และสร้างกลยุทธ์การสรรหาครอบคลุม 6 ด้านสำคัญ ดังนี้:\n"
        "1. candidate_persona: โปรไฟล์ผู้สมัครเป้าหมาย ประสบการณ์ และพฤติกรรม\n"
        "2. recommended_channels: ช่องทางการประกาศและ Direct Search พร้อมระบุเหตุผลและระดับ Priority (Primary / Secondary)\n"
        "3. boolean_search_strings: ชุดคำค้นหา Boolean Syntax พร้อมใช้งานสำหรับ LinkedIn Recruiter, Google X-Ray Search, และ Generic Search\n"
        "4. headhunting_outreach_template: ข้อความทักทายแคนดิเดตแบบ Cold Outreach ระดับพรีเมียม (Subject, Body, CTA)\n"
        "5. timeline_and_milestones: กำหนดการดำเนินงานเป็น Phase พร้อมประมาณการเวลาและ Deliverables\n"
        "6. agent4_screening_directives: คีย์เวิร์ดบังคับ (Must-have Keywords), คีย์เวิร์ดเสริม (Nice-to-have), จุดสังเกต (Red Flags) และคำแนะนำการประเมินสำหรับ Agent 4\n\n"
        "โปรดขยายความให้เป็นมืออาชีพ ลึกซึ้ง และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูล Job Description / Ticket สำหรับวางกลยุทธ์การสรรหา:
- Job ID: {job_id}
- ข้อมูลนำเข้า ({source_name}):
{input_data}

กรุณาวางกลยุทธ์การสรรหาและ Headhunting ครอบคลุมทั้ง 6 ด้านสำคัญลงใน Schema ให้ครบถ้วนสมบูรณ์
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=SourcingStrategyPayload,
                temperature=0.4,
            ),
        )


        strategy_payload = SourcingStrategyPayload.model_validate_json(response.text)
        strategy_payload.job_id = job_id

        json_str = strategy_payload.model_dump_json(indent=2)
        formal_md = format_formal_markdown(strategy_payload)

        # Safety Guards & File Operations
        Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        Path(md_output_path).parent.mkdir(parents=True, exist_ok=True)
        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(formal_md)

        print(f"✅ [Agent 2] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 2] บันทึกไฟล์ {md_output_path.name} (Formal Strategy Plan) สำเร็จ")
        return strategy_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 2] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e


if __name__ == "__main__":
    main()