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


# --- Pydantic Schemas for Multi-Channel Job Postings & JobsDB 50-Field Payload ---

class JobsDB50FieldPayload(BaseModel):
    # Category 1: Core Job Metadata (10 fields)
    job_id: str = Field(description="1. Job Ticket ID")
    job_title: str = Field(description="2. Job Position Title")
    job_function_code: str = Field(description="3. Primary Job Function Category Code (e.g. IT-AI-001)")
    sub_function: str = Field(description="4. Sub-Function Specialization")
    industry_type: str = Field(description="5. Target Industry Category")
    employment_type: str = Field(description="6. Employment Type (Full-time / Contract / Part-time)")
    career_level: str = Field(description="7. Seniority Level (Executive / Senior / Mid / Junior)")
    years_experience_min: int = Field(description="8. Minimum Required Experience Years")
    years_experience_max: int = Field(description="9. Maximum Expected Experience Years")
    headcount_total: int = Field(description="10. Total Open Headcount")

    # Category 2: Compensation & Privacy (7 fields)
    min_salary: int = Field(description="11. Minimum Monthly Base Salary (THB)")
    max_salary: int = Field(description="12. Maximum Monthly Base Salary (THB)")
    currency: str = Field(description="13. Currency ISO Code (THB)")
    pay_frequency: str = Field(description="14. Payment Cycle (Monthly)")
    is_salary_negotiable: bool = Field(description="15. Flag if salary is negotiable based on candidate experience")
    show_salary_to_candidate: bool = Field(description="16. Flag whether to display salary range publicly")
    confidential_posting: bool = Field(description="17. Flag if company name should be hidden")

    # Category 3: Location & Working Model (7 fields)
    workplace_type: str = Field(description="18. Workplace Model (On-site / Hybrid / Remote)")
    country: str = Field(description="19. Country Location (Thailand)")
    province: str = Field(description="20. Province (e.g. Bangkok)")
    district: str = Field(description="21. District / Sub-region")
    postal_code: str = Field(description="22. Postal Code")
    work_address: str = Field(description="23. Full Physical Work Office Address")
    geo_location_coordinates: str = Field(description="24. Latitude, Longitude GPS Coordinates")

    # Category 4: Requirements & Qualifications (7 fields)
    min_degree_level: str = Field(description="25. Minimum Education Degree (Bachelor / Master / Ph.D.)")
    major_fields: list[str] = Field(description="26. Field of Study / Major Requirements")
    required_skills: list[str] = Field(description="27. Mandatory Must-have Hard/Soft Skills")
    preferred_skills: list[str] = Field(description="28. Preferred Advantageous Skills")
    language_requirements: list[str] = Field(description="29. Required Language Proficiency Levels")
    certifications_required: list[str] = Field(description="30. Required Professional Certifications")
    minimum_gpa: float = Field(description="31. Minimum GPA Requirement (0.0 if not applicable)")

    # Category 5: Job Descriptions & Responsibilities (9 fields)
    role_summary: str = Field(description="32. Executive Summary of the Role")
    primary_responsibilities: list[str] = Field(description="33. Core Daily Responsibilities")
    key_deliverables: list[str] = Field(description="34. Expected Milestones and KPIs")
    technical_stack: list[str] = Field(description="35. Primary Technologies, Frameworks & Tools Used")
    management_level: str = Field(description="36. Management Scope (Individual Contributor / Team Lead)")
    perks_and_benefits: list[str] = Field(description="37. Array of Corporate Benefits and Perks")
    health_insurance_coverage: bool = Field(description="38. Health / Dental / Life Insurance Provided")
    flexible_working_hours: bool = Field(description="39. Flexible Work Hours Allowed")
    performance_bonus: bool = Field(description="40. Performance Bonus Program Offered")

    # Category 6: Application & Recruiter Controls (10 fields)
    auto_screening_questions: list[str] = Field(description="41. Pre-application Screening Questions")
    expiry_days: int = Field(description="42. Job Posting Duration in Days (default 30)")
    posting_priority: str = Field(description="43. Job Board Tier (Standard / Featured / Premium)")
    recruiter_contact_name: str = Field(description="44. Lead Recruiter / Contact Person Name")
    recruiter_contact_email: str = Field(description="45. Application Receipt Email Address")
    recruiter_contact_phone: str = Field(description="46. Recruiter Direct Telephone Number")
    notification_preferences: str = Field(description="47. Real-time Email Notification Preference")
    internal_reference_code: str = Field(description="48. Internal HR ERP Tracking Code")
    employer_brand_name: str = Field(description="49. Public Brand Display Name")
    application_redirect_url: str = Field(description="50. External ATS Application URL Link")
    probation_period_months: int = Field(default=4, description="51. Probation Period Duration in Months")



class LinkedInPost(BaseModel):
    headline: str = Field(description="Headline โพสต์ทางการระดับองค์กร (Executive Headline)")
    narrative_hook: str = Field(description="เปิดเรื่องดึงดูดความสนใจ (Narrative Hook)")
    key_highlights: list[str] = Field(description="จุดเด่นของตำแหน่งและภารกิจหลัก (Key Highlights)")
    key_benefits: list[str] = Field(description="สวัสดิการและผลประโยชน์เด่น (Standout Benefits)")
    call_to_action: str = Field(description="ข้อความเชิญชวนสมัครและช่องทางติดต่อ (Call to Action)")
    hashtags: list[str] = Field(description="แฮชแท็กวิชาชีพสำหรับ LinkedIn")
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


class EmailCandidateOutreach(BaseModel):
    subject: str = Field(description="หัวข้ออีเมลทักหาแคนดิเดต (Email Subject Line)")
    greeting: str = Field(description="คำทักทายสุภาพเป็นทางการ")
    body: str = Field(description="เนื้อหาอีเมลชวนสมัครงาน ระบุจุดเด่นตำแหน่งและสวัสดิการ")
    call_to_action: str = Field(description="CTA นัดคุยหรือเชิญส่ง CV")
    signature: str = Field(description="ลายเซ็นทีม Talent Acquisition")
    full_email_text: str = Field(description="เนื้อหาอีเมลฉบับสมบูรณ์พร้อมส่งต่อทันที")


class JobPostingsPayload(BaseModel):
    job_id: str = Field(description="รหัสใบงาน (Job ID)")
    position_title: str = Field(description="ชื่อตำแหน่งงาน (Position Title)")
    jobsdb_50_fields: JobsDB50FieldPayload = Field(description="1. Payload 50 ฟิลด์สำหรับ JobsDB/JobStreet Form Mapping")
    linkedin_post: LinkedInPost = Field(description="2. โพสต์ทางการระดับองค์กรบน LinkedIn")
    facebook_community_post: FacebookCommunityPost = Field(description="3. โพสต์แนวเข้าถึงง่ายสำหรับ Facebook Community")
    short_messaging_ad: ShortMessagingAd = Field(description="4. ข้อความสั้นกระชับสำหรับ LINE OA / Telegram / WhatsApp")
    job_board_teaser: JobBoardTeaser = Field(description="5. ข้อความสรุปย่อสำหรับ Job Board Teaser / Meta Description")
    email_outreach: EmailCandidateOutreach = Field(description="6. เทมเพลตอีเมลทักหา Candidate เชิงรุก (Cold Outreach)")
    recommended_posting_schedule: str = Field(description="คำแนะนำช่วงเวลาที่เหมาะสมในการโพสต์แต่ละแพลตฟอร์ม")


def format_jobsdb_preview_markdown(jobsdb: JobsDB50FieldPayload) -> str:
    """สร้างเอกสาร Markdown Preview ฉบับ JobsDB 50-field Form Mapping"""
    resp_bullets = "\n".join([f"- {r}" for r in jobsdb.primary_responsibilities])
    deliv_bullets = "\n".join([f"- {d}" for d in jobsdb.key_deliverables])
    perk_bullets = "\n".join([f"- {p}" for p in jobsdb.perks_and_benefits])
    questions = "\n".join([f"{idx+1}. {q}" for idx, q in enumerate(jobsdb.auto_screening_questions)])

    return f"""# 🏢 JobsDB / JobStreet Official Posting Preview

> **Position Title:** **{jobsdb.job_title}**  
> **Job ID / Internal Ref:** `{jobsdb.job_id}` | `{jobsdb.internal_reference_code}`  
> **Employer Brand:** **{jobsdb.employer_brand_name}**  
> **Posting Tier:** `{jobsdb.posting_priority}` | **Expiry:** {jobsdb.expiry_days} Days  

---

## 📌 1. Core Job Metadata (10 Fields)
- **Job Title:** {jobsdb.job_title}
- **Function Code:** `{jobsdb.job_function_code}` ({jobsdb.sub_function})
- **Industry Type:** {jobsdb.industry_type}
- **Employment Type:** {jobsdb.employment_type}
- **Career Level:** {jobsdb.career_level}
- **Experience Required:** {jobsdb.years_experience_min} - {jobsdb.years_experience_max} Years
- **Headcount:** {jobsdb.headcount_total}
- **Internal Ref Code:** `{jobsdb.internal_reference_code}`

---

## 💰 2. Compensation & Privacy (7 Fields)
- **Salary Range:** {jobsdb.min_salary:,} - {jobsdb.max_salary:,} {jobsdb.currency} / {jobsdb.pay_frequency}
- **Public Salary Display:** {"✅ Visible to Jobseekers" if jobsdb.show_salary_to_candidate else "🔒 Hidden"}
- **Salary Negotiable:** {"Yes" if jobsdb.is_salary_negotiable else "No"}
- **Confidential Posting:** {"Yes (Company Hidden)" if jobsdb.confidential_posting else "No (Public Company)"}

---

## 📍 3. Location & Working Model (7 Fields)
- **Workplace Model:** **{jobsdb.workplace_type}**
- **Address:** {jobsdb.work_address}, {jobsdb.district}, {jobsdb.province} {jobsdb.postal_code}, {jobsdb.country}
- **GPS Coordinates:** `{jobsdb.geo_location_coordinates}`

---

## 🎓 4. Requirements & Qualifications (7 Fields)
- **Min Education:** {jobsdb.min_degree_level} (Majors: {', '.join(jobsdb.major_fields)})
- **Min GPA:** {jobsdb.minimum_gpa if jobsdb.minimum_gpa > 0 else 'N/A'}
- **Required Mandatory Skills:** {', '.join(jobsdb.required_skills)}
- **Preferred Skills:** {', '.join(jobsdb.preferred_skills)}
- **Language Requirements:** {', '.join(jobsdb.language_requirements)}
- **Certifications Required:** {', '.join(jobsdb.certifications_required)}

---

## 📝 5. Role Overview & Responsibilities (9 Fields)
### Role Summary
{jobsdb.role_summary}

### Primary Responsibilities
{resp_bullets}

### Key Deliverables & KPIs
{deliv_bullets}

### Technical Stack & Management Scope
- **Tech Stack:** {', '.join(jobsdb.technical_stack)}
- **Management Scope:** {jobsdb.management_level}

### Perks & Benefits
{perk_bullets}
- Health/Dental Insurance: {"✅ Yes" if jobsdb.health_insurance_coverage else "❌ No"}
- Flexible Hours: {"✅ Yes" if jobsdb.flexible_working_hours else "❌ No"}
- Performance Bonus: {"✅ Yes" if jobsdb.performance_bonus else "❌ No"}

---

## ❓ 6. Application & Recruiter Controls (10 Fields)
### Auto-Screening Questions
{questions}

### Recruiter Contact & ATS Redirect
- **Contact Recruiter:** {jobsdb.recruiter_contact_name} ({jobsdb.recruiter_contact_email} / {jobsdb.recruiter_contact_phone})
- **Notification Preference:** {jobsdb.notification_preferences}
- **Probation Period:** {jobsdb.probation_period_months} Months
- **ATS External Redirect:** [{jobsdb.application_redirect_url}]({jobsdb.application_redirect_url})

---
> *Generated by Agent 3 (JobsDB 50-Field Payload Generator)*
"""


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

## 🏢 1. JobsDB 50-Field Form Summary
- **Position Title:** {postings.jobsdb_50_fields.job_title}
- **Category Code:** `{postings.jobsdb_50_fields.job_function_code}`
- **Salary Range:** {postings.jobsdb_50_fields.min_salary:,} - {postings.jobsdb_50_fields.max_salary:,} {postings.jobsdb_50_fields.currency}
- **Workplace Model:** {postings.jobsdb_50_fields.workplace_type} ({postings.jobsdb_50_fields.province})
- **Recruiter Contact:** {postings.jobsdb_50_fields.recruiter_contact_email}

---

## 💼 2. LinkedIn Corporate Official Post

```text
{postings.linkedin_post.full_post_text}
```

---

## 👥 3. Facebook Community & Group Post

```text
{postings.facebook_community_post.full_post_text}
```

---

## 📱 4. Short Messaging Ad (LINE OA / Telegram / WhatsApp)

```text
{postings.short_messaging_ad.full_ad_text}
```

---

## 🌐 5. Job Board Teaser & Meta Description

> {postings.job_board_teaser.summary_teaser}

---

## 📧 6. Cold Outreach Email Candidate Template

```text
{postings.email_outreach.full_email_text}
```

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

    # โฟลเดอร์แยกสำหรับ Broadcasting Kits (Task 2.2)
    broadcasting_kits_dir = Path(paths.get("broadcasting_kits", Path(paths["root"]) / "03_broadcasting_kits"))
    broadcasting_kits_dir.mkdir(parents=True, exist_ok=True)

    jd_json_path = specs_dir / "is1_output_job_description.json"
    strategy_json_path = specs_dir / "is2_output_sourcing_strategy.json"
    jd_txt_path = specs_dir / "is1_output_job_description.txt"
    ticket_json_path = specs_dir / "is0_job_ticket.json"
    input_spec_path = specs_dir / "is1_input_spec.txt"

    # Dual Output Paths หลักใน 01_specs/
    json_output_path = specs_dir / "is3_output_broadcasting_content_payload.json"
    md_output_path = specs_dir / "is3_broadcasting_content_kit.md"
    
    # Legacy Bridges ใน 01_specs/
    legacy_json_path = specs_dir / "is3_output_job_postings.json"
    legacy_md_path = specs_dir / "is3_job_postings_ready.md"

    # Specific Channel Kits ใน 03_broadcasting_kits/
    jobsdb_json_kit = broadcasting_kits_dir / "jobsdb_50_fields_payload.json"
    jobsdb_preview_kit = broadcasting_kits_dir / "jobsdb_posting_preview.md"
    linkedin_kit = broadcasting_kits_dir / "linkedin_post_copy.md"
    facebook_kit = broadcasting_kits_dir / "facebook_post_copy.md"
    email_kit = broadcasting_kits_dir / "email_candidate_outreach.md"

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
        "คุณคือ Agent 3 (Multi-Channel Recruitment Copywriter & JobsDB Form Automation Specialist)\n"
        "หน้าที่ของคุณคือการนำข้อมูล Job Description (IS1) และ Sourcing Strategy (IS2) มาสร้างชุดสื่อและแบบฟอร์มการประกาศงานดังนี้:\n"
        "1. jobsdb_50_fields: เติมข้อมูล JobsDB 50-field schema ครบถ้วนถูกต้องสมบูรณ์ (หมวดหมู่ metadata, เงินเดือน, พิกัดสถานที่, คุณสมบัติ, สวัสดิการ, คำถามคัดกรอง)\n"
        "2. linkedin_post: โพสต์ทางการระดับองค์กรบน LinkedIn พร้อม Headline, Highlights, Benefits, CTA และ Hashtags\n"
        "3. facebook_community_post: โพสต์แนวเข้าถึงง่ายบน Facebook อ่านสะดวกบนมือถือ พร้อมอิโมจิและแฮชแท็กตรงสายงาน\n"
        "4. short_messaging_ad: ข้อความสั้นกระชับสำหรับส่งผ่าน LINE OA / Telegram / WhatsApp\n"
        "5. job_board_teaser: ข้อความสรุปย่อ 2-3 บรรทัด สำหรับ Meta Description บนเว็บหางาน\n"
        "6. email_outreach: เทมเพลตอีเมลทักหาแคนดิเดตเชิงรุก (Cold Outreach Email) พร้อม Subject, Body และ Signature\n"
        "7. recommended_posting_schedule: ช่วงเวลาที่เหมาะสมที่สุดในการโพสต์ในแต่ละแพลตฟอร์ม\n\n"
        "โปรดเขียน Copywriting ให้มีพลัง ละเอียด สมบูรณ์แบบระดับมืออาชีพ และส่งคืนผลลัพธ์เป็น JSON ตาม Schema ที่กำหนดอย่างเคร่งครัด"
    )

    prompt = f"""
ข้อมูลนำเข้าสำหรับสร้าง Copywriting และ JobsDB 50-field Payload:
- Job ID: {job_id}
{combined_input}

กรุณาสร้างชุดประกาศงานและกรอก JobsDB 50-field Payload ให้ครบถ้วนสมบูรณ์ตาม Schema
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
                temperature=0.4,
            ),
        )

        postings_payload = JobPostingsPayload.model_validate_json(response.text)
        postings_payload.job_id = job_id
        postings_payload.jobsdb_50_fields.job_id = job_id

        json_str = postings_payload.model_dump_json(indent=2)
        ready_md = format_formal_markdown(postings_payload)
        jobsdb_preview_md = format_jobsdb_preview_markdown(postings_payload.jobsdb_50_fields)

        # 1. Dual Output หลักใน 01_specs/
        config.ensure_parent_dir(json_output_path)
        with open(json_output_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        config.ensure_parent_dir(md_output_path)
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(ready_md)

        # 2. Legacy Bridges ใน 01_specs/
        config.ensure_parent_dir(legacy_json_path)
        with open(legacy_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        config.ensure_parent_dir(legacy_md_path)
        with open(legacy_md_path, "w", encoding="utf-8") as f:
            f.write(ready_md)

        # 3. Specific Kits ใน 03_broadcasting_kits/ (Task 2.2)
        config.ensure_parent_dir(jobsdb_json_kit)
        with open(jobsdb_json_kit, "w", encoding="utf-8") as f:
            f.write(postings_payload.jobsdb_50_fields.model_dump_json(indent=2))

        config.ensure_parent_dir(jobsdb_preview_kit)
        with open(jobsdb_preview_kit, "w", encoding="utf-8") as f:
            f.write(jobsdb_preview_md)

        config.ensure_parent_dir(linkedin_kit)
        with open(linkedin_kit, "w", encoding="utf-8") as f:
            f.write(f"# 💼 LinkedIn Official Post\n\n```text\n{postings_payload.linkedin_post.full_post_text}\n```\n")

        config.ensure_parent_dir(facebook_kit)
        with open(facebook_kit, "w", encoding="utf-8") as f:
            f.write(f"# 👥 Facebook Community Post\n\n```text\n{postings_payload.facebook_community_post.full_post_text}\n```\n")

        config.ensure_parent_dir(email_kit)
        with open(email_kit, "w", encoding="utf-8") as f:
            f.write(f"# 📧 Cold Outreach Email Template\n\n```text\n{postings_payload.email_outreach.full_email_text}\n```\n")

        print(f"✅ [Agent 3] บันทึกไฟล์ {json_output_path.name} (Structured Payload) สำเร็จ")
        print(f"✅ [Agent 3] บันทึกไฟล์ {md_output_path.name} (Broadcasting Content Kit) สำเร็จ")
        print(f"🎉 [Agent 3] บันทึกไฟล์ครบ 5 สื่อใน {broadcasting_kits_dir.name}/ (JobsDB 50-field, LinkedIn, Facebook, Email) สำเร็จ!")
        return postings_payload.model_dump()

    except Exception as e:
        print(f"❌ [Agent 3] ระบบสมองประมวลผลล้มเหลว: {e}")
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e


if __name__ == "__main__":
    main()