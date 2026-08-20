import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Path registration
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import config

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(root_dir) / "data"
INDEX_FILE = DATA_DIR / "talent_pool_index.json"


def build_talent_index() -> Dict[str, Any]:
    """สแกนค้นหาไฟล์ Dossier ทั้งหมดใน workspaces/*/05_onboarding_vault/ และสร้างดรรชนีสืบค้น Central Talent Store"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    workspaces_dir = Path(root_dir) / "workspaces"
    
    talent_records = []
    
    if workspaces_dir.exists():
        for job_folder in sorted(workspaces_dir.iterdir()):
            if job_folder.is_dir():
                onboarding_vault = job_folder / "05_onboarding_vault"
                if onboarding_vault.exists():
                    dossier_files = list(onboarding_vault.glob("is10_*.json"))
                    for df in dossier_files:
                        try:
                            with open(df, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            
                            hired = data.get("hired_candidate_dossier", {})
                            employee_id = hired.get("employee_id", data.get("employee_id", "CAND-001"))
                            employee_name = hired.get("employee_name", data.get("name", "Unknown Candidate"))
                            job_title = hired.get("job_title", data.get("job_title", "Unassigned Position"))
                            department = hired.get("department", data.get("department", "General"))
                            skills = hired.get("verified_key_skills", data.get("skills", []))
                            exec_summary = hired.get("executive_dossier_summary", data.get("summary", ""))
                            
                            record = {
                                "job_id": job_folder.name,
                                "employee_id": employee_id,
                                "employee_name": employee_name,
                                "job_title": job_title,
                                "department": department,
                                "skills": skills,
                                "executive_summary": exec_summary,
                                "dossier_source": df.name,
                                "indexed_at": datetime.now().isoformat(),
                                "raw_payload": data
                            }
                            talent_records.append(record)
                        except Exception as e:
                            print(f"⚠️ [Talent Memory] อ่านไฟล์ {df.name} ล้มเหลว: {e}")

    index_payload = {
        "total_records": len(talent_records),
        "last_updated": datetime.now().isoformat(),
        "records": talent_records
    }

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_payload, f, ensure_ascii=False, indent=2)
        
    print(f"✅ [Talent Memory Engine] อัปเดต Central Talent Store สำเร็จ ({len(talent_records)} Records ➔ {INDEX_FILE.name})")
    return index_payload


def calculate_relevance_score(query: str, record: Dict[str, Any]) -> float:
    """คำนวณคะแนนความตรงกัน (Relevance Score 0-100%) ระหว่างคำค้นหา กับ Candidate Record"""
    query_terms = [q.lower().strip() for q in query.split() if q.strip()]
    if not query_terms:
        return 0.0

    score = 0.0
    text_corpus = (
        f"{record.get('employee_name', '')} "
        f"{record.get('job_title', '')} "
        f"{record.get('department', '')} "
        f"{' '.join(record.get('skills', []))} "
        f"{record.get('executive_summary', '')}"
    ).lower()

    for term in query_terms:
        if term in record.get("job_title", "").lower():
            score += 35.0
        if any(term in s.lower() for s in record.get("skills", [])):
            score += 25.0
        if term in record.get("employee_name", "").lower():
            score += 20.0
        if term in text_corpus:
            score += 15.0

    max_possible = len(query_terms) * 50.0
    percentage = min(100.0, round((score / max_possible) * 100, 1)) if max_possible > 0 else 0.0
    return percentage


def search_talent_pool(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """สืบค้น Talent Pool ข้าม Workspace ด้วย Semantic/Keyword Search และจัดลำดับความเหมาะสม"""
    if not INDEX_FILE.exists():
        build_talent_index()

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    records = index_data.get("records", [])
    results = []

    for r in records:
        match_score = calculate_relevance_score(query, r)
        if match_score > 0:
            results.append({
                "match_score": match_score,
                "record": r
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_k]


def print_search_results(query: str, results: List[Dict[str, Any]]):
    """แสดงผลการค้นหา Candidate Search Card บนหน้าจอ"""
    print(f"\n🔍 [Talent Memory Search Results for Query: '{query}']")
    print("=" * 75)
    if not results:
        print("❌ ไม่พบประวัติผู้สมัครที่ตรงกับคำค้นหาใน Central Talent Store")
        print("=" * 75)
        return

    for rank, res in enumerate(results, start=1):
        score = res["match_score"]
        rec = res["record"]
        skills_str = ", ".join(rec.get("skills", []))
        print(f"🏆 Rank #{rank} | Match Score: {score}%")
        print(f"👤 Candidate Name: {rec.get('employee_name')} ({rec.get('employee_id')})")
        print(f"💼 Role & Dept:    {rec.get('job_title')} — {rec.get('department')}")
        print(f"📍 Original Job:   {rec.get('job_id')}")
        print(f"🛠️ Key Skills:     {skills_str}")
        print(f"📝 Summary:        {rec.get('executive_summary')[:150]}...")
        print("-" * 75)


def main():
    parser = argparse.ArgumentParser(description="Talent Memory & Semantic Candidate Retrieval Engine")
    parser.add_argument("--search", type=str, help="คำค้นหาสำหรับสืบค้นผู้สมัคร (เช่น 'Senior AI Architect LLM')")
    parser.add_argument("--reindex", action="store_true", help="รีอินเดกซ์ข้อมูลจากทุก Workspace")
    parser.add_argument("--top_k", type=int, default=3, help="จำนวนผลลัพธ์สูงสุดที่ต้องการ")
    args = parser.parse_args()

    if args.reindex:
        build_talent_index()

    if args.search:
        results = search_talent_pool(args.search, top_k=args.top_k)
        print_search_results(args.search, results)
    elif not args.reindex:
        # Default indexing check if run without args
        build_talent_index()


if __name__ == "__main__":
    main()
