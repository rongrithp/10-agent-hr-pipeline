import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime

import streamlit as st

# Setup Root Directory & Path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import Talent Memory Engine
try:
    from engine.talent_memory import search_talent_pool, build_talent_index
except ImportError:
    search_talent_pool = None
    build_talent_index = None

# Page Config
st.set_page_config(
    page_title="Central Recruitment Operations Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }
    
    .kpi-card {
        background: linear-gradient(145deg, #1e293b, #111827);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: #3b82f6;
    }
    
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .status-badge-completed {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    .status-badge-progress {
        background-color: #78350f;
        color: #fbbf24;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    .status-badge-pending {
        background-color: #1f2937;
        color: #9ca3af;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    .candidate-card {
        background: #1e293b;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #1e293b;
        border-radius: 8px 8px 0px 0px;
        color: #94a3b8;
        font-weight: 600;
        padding: 0px 20px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Data Loaders ---
def load_json_file(filepath: Path) -> dict:
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_markdown_file(filepath: Path) -> str:
    if not filepath.exists():
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def scan_workspace_job(job_folder: Path) -> dict:
    job_id = job_folder.name
    
    # Check ticket
    ticket_file = job_folder / "01_specs" / "is0_job_ticket.json"
    if not ticket_file.exists():
        ticket_file = job_folder / "01_specs" / "is0_output_job_intake_payload.json"
    ticket_data = load_json_file(ticket_file)
    
    # Stages Check (IS0 to IS12)
    stage_files = {
        0: [job_folder / "01_specs" / "is0_job_ticket.json", job_folder / "01_specs" / "is0_output_job_intake_payload.json"],
        1: [job_folder / "01_specs" / "is1_output_job_description.json", job_folder / "01_specs" / "is1_job_description_formal.md"],
        2: [job_folder / "01_specs" / "is2_output_sourcing_strategy.json", job_folder / "01_specs" / "is2_sourcing_strategy_formal.md"],
        3: [job_folder / "01_specs" / "is3_output_broadcasting_content_payload.json", job_folder / "01_specs" / "is3_broadcasting_content_kit.md", job_folder / "03_broadcasting_kits" / "is3_output_broadcasting_content_payload.json"],
        4: [job_folder / "03_evaluations" / "is4_output_screening_results.json", job_folder / "03_evaluations" / "is4_output_candidate_scores.json"],
        5: [job_folder / "03_evaluations" / "is5_output_interview_schedule.json", job_folder / "03_evaluations" / "is5_interview_guide_formal.md"],
        6: [job_folder / "03_evaluations" / "is6_output_interview_evaluation.json", job_folder / "03_evaluations" / "is6_output_interview_evaluations.json"],
        7: [job_folder / "03_evaluations" / "is7_output_compliance_check.json", job_folder / "04_offers_contracts" / "is7_output_compliance_audit.json"],
        8: [job_folder / "04_offers_contracts" / "is8_output_offer_details.json", job_folder / "04_offers_contracts" / "is8_formal_job_offer_letter.md"],
        9: [job_folder / "05_onboarding_vault" / "is9_output_onboarding_plan.json", job_folder / "05_onboarding_vault" / "is9_onboarding_roadmap_formal.md"],
        10: [job_folder / "05_onboarding_vault" / "is10_output_employee_profile.json", job_folder / "05_onboarding_vault" / "is10_output_talent_profile.json"],
        11: [job_folder / "05_onboarding_vault" / "is11_output_db_sync_payload.json"],
        12: [job_folder / "05_onboarding_vault" / "is12_output_notification_payload.json", job_folder / "05_onboarding_vault" / "is12_telegram_broadcast_card.md"],
    }
    
    completed_stages = []
    for stage_num, paths in stage_files.items():
        if any(p.exists() for p in paths):
            completed_stages.append(stage_num)
            
    completed_count = len(completed_stages)
    progress_pct = min(100, int((completed_count / 13) * 100))
    
    if completed_count >= 12:
        status_label = "COMPLETED"
        status_class = "status-badge-completed"
    elif completed_count > 0:
        status_label = "IN PROGRESS"
        status_class = "status-badge-progress"
    else:
        status_label = "PENDING"
        status_class = "status-badge-pending"
        
    # Screening Candidates Count
    is4_file = job_folder / "03_evaluations" / "is4_output_screening_results.json"
    if not is4_file.exists():
        is4_file = job_folder / "03_evaluations" / "is4_output_candidate_scores.json"
    is4_data = load_json_file(is4_file)
    screened_count = is4_data.get("total_candidates_screened", len(is4_data.get("candidates", [])))
    
    # Hired / Accepted Count
    is8_file = job_folder / "04_offers_contracts" / "is8_output_offer_details.json"
    is10_file = job_folder / "05_onboarding_vault" / "is10_output_employee_profile.json"
    hired_count = 1 if (is8_file.exists() or is10_file.exists()) else 0
    
    return {
        "job_id": job_id,
        "folder_path": job_folder,
        "position": ticket_data.get("position", ticket_data.get("job_title", job_id)),
        "department": ticket_data.get("department", "General"),
        "client": ticket_data.get("client", "Harrow International School"),
        "hiring_manager": ticket_data.get("hiring_manager", "N/A"),
        "salary_budget": ticket_data.get("salary_budget", "N/A"),
        "headcount": ticket_data.get("headcount", 1),
        "completed_stages": completed_stages,
        "completed_count": completed_count,
        "progress_pct": progress_pct,
        "status_label": status_label,
        "status_class": status_class,
        "screened_count": screened_count,
        "hired_count": hired_count,
        "ticket_data": ticket_data
    }


def load_all_workspaces() -> list:
    workspaces_dir = ROOT_DIR / "workspaces"
    jobs = []
    if workspaces_dir.exists():
        for item in sorted(workspaces_dir.iterdir()):
            if item.is_dir():
                jobs.append(scan_workspace_job(item))
    return jobs


# --- Main Dashboard Application ---
def main():
    # Sidebar
    st.sidebar.image("https://img.icons8.com/isometric/100/workspace.png", width=70)
    st.sidebar.title("Recruitment Hub")
    st.sidebar.markdown("---")
    
    # Global Refresh Action
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("### 📌 Navigation")
    menu = st.sidebar.radio("Go to section:", [
        "📊 Executive Overview",
        "🔍 Job Pipeline Inspector",
        "🧠 Talent Pool Search",
        "⚙️ Engine Status"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.caption("⚡ 12-Agent System v1.0.0")
    st.sidebar.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")

    # Scan Workspace Data
    jobs = load_all_workspaces()
    total_jobs = len(jobs)
    total_screened = sum(j["screened_count"] for j in jobs)
    total_hired = sum(j["hired_count"] for j in jobs)
    
    # Top Banner Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size: 2.2rem; font-weight:800;">⚡ Central Recruitment Operations Dashboard</h1>
        <p style="color:#94a3b8; margin-top:6px; font-size:1rem;">
            Real-time Monitoring & Inspection Interface for 12-Agent Multi-Agent Recruitment Pipeline
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header & High-Level KPIs
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    with col_kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_jobs}</div>
            <div class="kpi-label">Active Job Positions</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_screened}</div>
            <div class="kpi-label">Candidates Screened</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_kpi3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_hired}</div>
            <div class="kpi-label">Offers & Onboarded</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_kpi4:
        avg_progress = int(sum(j["progress_pct"] for j in jobs) / max(1, total_jobs))
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{avg_progress}%</div>
            <div class="kpi-label">Pipeline Completion</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- SECTION 1: Executive Overview ---
    if menu == "📊 Executive Overview":
        st.subheader("📋 Job Pipeline Overview")
        
        if not jobs:
            st.warning("⚠️ No job workspaces found in `workspaces/`.")
            return

        # Overview Table / Cards
        for j in jobs:
            with st.container():
                st.markdown(f"""
                <div style="background:#1e293b; border-radius:12px; padding:18px; margin-bottom:16px; border: 1px solid #334155;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:1.2rem; font-weight:700; color:#f8fafc;">{j['position']}</span>
                            <span style="margin-left:10px; color:#94a3b8; font-size:0.9rem;">({j['job_id']})</span>
                        </div>
                        <div>
                            <span class="{j['status_class']}">{j['status_label']}</span>
                        </div>
                    </div>
                    <div style="margin-top:10px; color:#cbd5e1; font-size:0.9rem;">
                        📍 <b>Dept:</b> {j['department']} &nbsp;|&nbsp; 
                        👥 <b>Headcount:</b> {j['headcount']} &nbsp;|&nbsp; 
                        💰 <b>Budget:</b> {j['salary_budget']} &nbsp;|&nbsp; 
                        🎯 <b>Screened:</b> {j['screened_count']} Candidates
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Progress Bar
                c_lbl, c_bar = st.columns([1, 4])
                with c_lbl:
                    st.caption(f"Stage Progress: {j['completed_count']}/13 ({j['progress_pct']}%)")
                with c_bar:
                    st.progress(j['progress_pct'] / 100)

    # --- SECTION 2: Deep-Dive Job Inspector ---
    elif menu == "🔍 Job Pipeline Inspector":
        st.subheader("🔍 Deep-Dive Job Inspector")
        
        job_options = {f"{j['job_id']} - {j['position']}": j for j in jobs}
        if not job_options:
            st.warning("No jobs found.")
            return

        selected_option = st.selectbox("Select Job Position to Inspect:", list(job_options.keys()))
        selected_job = job_options[selected_option]
        job_dir = selected_job["folder_path"]
        
        st.markdown("---")
        
        # 4 Main Deep-Dive Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Job Specs & Strategy",
            "📢 Broadcasting Kits",
            "🎯 Candidate Matrix & Evaluation",
            "🤝 Offer & Onboarding Vault"
        ])
        
        # TAB 1: Job Specs & Strategy (IS1, IS2)
        with tab1:
            st.markdown("### 📋 IS1 & IS2: Job Description & Sourcing Strategy")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 📄 Job Description Document (IS1)")
                is1_md = load_markdown_file(job_dir / "01_specs" / "is1_job_description_formal.md")
                if is1_md:
                    st.markdown(is1_md)
                else:
                    is1_json = load_json_file(job_dir / "01_specs" / "is1_output_job_description.json")
                    if is1_json:
                        st.json(is1_json)
                    else:
                        st.info("No IS1 document generated yet.")
                        
            with c2:
                st.markdown("#### 🎯 Sourcing Strategy Document (IS2)")
                is2_md = load_markdown_file(job_dir / "01_specs" / "is2_sourcing_strategy_formal.md")
                if is2_md:
                    st.markdown(is2_md)
                else:
                    is2_json = load_json_file(job_dir / "01_specs" / "is2_output_sourcing_strategy.json")
                    if is2_json:
                        st.json(is2_json)
                    else:
                        st.info("No IS2 document generated yet.")

        # TAB 2: Broadcasting Kits (IS3)
        with tab2:
            st.markdown("### 📢 IS3: Multi-Channel Broadcasting Content Kits")
            is3_md = load_markdown_file(job_dir / "01_specs" / "is3_broadcasting_content_kit.md")
            if not is3_md:
                is3_md = load_markdown_file(job_dir / "03_broadcasting_kits" / "is3_broadcasting_content_kit.md")
                
            if is3_md:
                st.markdown(is3_md)
            else:
                is3_json = load_json_file(job_dir / "01_specs" / "is3_output_broadcasting_content_payload.json")
                if is3_json:
                    st.json(is3_json)
                else:
                    st.info("No IS3 broadcasting kit generated yet.")

        # TAB 3: Candidate Matrix & Evaluation (IS4, IS6)
        with tab3:
            st.markdown("### 🎯 IS4 & IS6: Resume Screening & Interview Scorecards")
            
            e1, e2 = st.columns(2)
            with e1:
                st.markdown("#### 📊 Resume Screening Scorecard (IS4)")
                is4_md = load_markdown_file(job_dir / "03_evaluations" / "is4_screening_matrix_formal.md")
                if is4_md:
                    st.markdown(is4_md)
                else:
                    is4_json = load_json_file(job_dir / "03_evaluations" / "is4_output_screening_results.json")
                    if is4_json:
                        st.json(is4_json)
                    else:
                        st.info("No IS4 screening matrix generated yet.")
                        
            with e2:
                st.markdown("#### 🎙️ Interview Evaluation Report (IS6)")
                is6_md = load_markdown_file(job_dir / "03_evaluations" / "is6_interview_evaluation_report_formal.md")
                if is6_md:
                    st.markdown(is6_md)
                else:
                    is6_json = load_json_file(job_dir / "03_evaluations" / "is6_output_interview_evaluation.json")
                    if is6_json:
                        st.json(is6_json)
                    else:
                        st.info("No IS6 evaluation report generated yet.")

        # TAB 4: Offer & Onboarding Vault (IS8, IS9, IS10)
        with tab4:
            st.markdown("### 🤝 IS8, IS9 & IS10: Offer, Onboarding & Talent Dossier")
            
            o1, o2, o3 = st.columns(3)
            with o1:
                st.markdown("#### 📜 Offer Letter (IS8)")
                is8_md = load_markdown_file(job_dir / "04_offers_contracts" / "is8_formal_job_offer_letter.md")
                if is8_md:
                    st.markdown(is8_md)
                else:
                    st.info("No IS8 Offer Letter found.")
                    
            with o2:
                st.markdown("#### 🗺️ Onboarding Plan (IS9)")
                is9_md = load_markdown_file(job_dir / "05_onboarding_vault" / "is9_onboarding_roadmap_formal.md")
                if is9_md:
                    st.markdown(is9_md)
                else:
                    st.info("No IS9 Onboarding Plan found.")
                    
            with o3:
                st.markdown("#### 👤 Employee Dossier (IS10)")
                is10_md = load_markdown_file(job_dir / "05_onboarding_vault" / "is10_talent_dossier_formal.md")
                if is10_md:
                    st.markdown(is10_md)
                else:
                    st.info("No IS10 Talent Dossier found.")

    # --- SECTION 3: Talent Pool Memory Search ---
    elif menu == "🧠 Talent Pool Search":
        st.subheader("🧠 Central Talent Pool Memory Search")
        st.markdown("Search across all past candidate dossiers using skill keywords, job titles, or experience.")
        
        c_btn1, c_btn2 = st.columns([4, 1])
        with c_btn2:
            if st.button("⚡ Re-index Store", use_container_width=True):
                if build_talent_index:
                    res = build_talent_index()
                    st.success(f"Indexed {res.get('total_records', 0)} candidates successfully!")
                else:
                    st.error("Talent Memory Engine missing.")
                    
        query = st.text_input("🔍 Enter search terms (e.g., 'Golf Coach', 'PGA Certified', 'Data Scientist'):", value="Golf Coach")
        
        if query:
            if search_talent_pool:
                results = search_talent_pool(query, top_k=5)
                if not results:
                    st.info("No matching candidates found in Central Talent Store.")
                else:
                    st.markdown(f"### Found {len(results)} Matching Candidate Records:")
                    for idx, item in enumerate(results, start=1):
                        rec = item["record"]
                        score = item["match_score"]
                        
                        st.markdown(f"""
                        <div class="candidate-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:1.1rem; font-weight:700; color:#60a5fa;">
                                    #{idx} {rec.get('employee_name')} ({rec.get('employee_id')})
                                </span>
                                <span style="background:#1d4ed8; color:#ffffff; padding:2px 10px; border-radius:12px; font-weight:700;">
                                    Match: {score}%
                                </span>
                            </div>
                            <div style="margin-top:6px; color:#e2e8f0; font-size:0.9rem;">
                                💼 <b>Role:</b> {rec.get('job_title')} | 🏢 <b>Dept:</b> {rec.get('department')} | 📍 <b>Workspace:</b> {rec.get('job_id')}
                            </div>
                            <div style="margin-top:6px; color:#94a3b8; font-size:0.85rem;">
                                🛠️ <b>Skills:</b> {', '.join(rec.get('skills', []))}
                            </div>
                            <div style="margin-top:8px; font-size:0.85rem; color:#cbd5e1; background:#0f172a; padding:10px; border-radius:6px;">
                                📝 {rec.get('executive_summary')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("Talent memory search function unavailable.")

    # --- SECTION 4: Engine Status ---
    elif menu == "⚙️ Engine Status":
        st.subheader("⚙️ System Architecture & 12-Agent Status")
        st.markdown("Overview of the 5 Recruitment Lifecycles and Agent operational readiness.")
        
        agents_data = [
            {"ID": "Agent 0", "Name": "Telegram Gatekeeper", "Lifecycle": "L1: Job Spec & Sourcing", "Status": "Active ✅"},
            {"ID": "Agent 1", "Name": "Job Description Synthesizer", "Lifecycle": "L1: Job Spec & Sourcing", "Status": "Active ✅"},
            {"ID": "Agent 2", "Name": "Sourcing Strategist", "Lifecycle": "L1: Job Spec & Sourcing", "Status": "Active ✅"},
            {"ID": "Agent 3", "Name": "Content Broadcaster", "Lifecycle": "L1: Job Spec & Sourcing", "Status": "Active ✅"},
            {"ID": "Agent 4", "Name": "Resume Screener", "Lifecycle": "L2: Screening", "Status": "Active ✅"},
            {"ID": "Agent 5", "Name": "Interview Scheduler", "Lifecycle": "L3: Evaluation", "Status": "Active ✅"},
            {"ID": "Agent 6", "Name": "Interview Evaluator", "Lifecycle": "L3: Evaluation", "Status": "Active ✅"},
            {"ID": "Agent 7", "Name": "Compliance Checker", "Lifecycle": "L4: Compliance & Offer", "Status": "Active ✅"},
            {"ID": "Agent 8", "Name": "Offer Negotiator", "Lifecycle": "L4: Compliance & Offer", "Status": "Active ✅"},
            {"ID": "Agent 9", "Name": "Onboarding Planner", "Lifecycle": "L5: Onboarding & Notify", "Status": "Active ✅"},
            {"ID": "Agent 10", "Name": "Talent Profiler", "Lifecycle": "L5: Onboarding & Notify", "Status": "Active ✅"},
            {"ID": "Agent 11", "Name": "Database Sync", "Lifecycle": "L5: Onboarding & Notify", "Status": "Active ✅"},
            {"ID": "Agent 12", "Name": "Telegram Notify", "Lifecycle": "L5: Onboarding & Notify", "Status": "Active ✅"},
        ]
        
        st.table(agents_data)


if __name__ == "__main__":
    main()
