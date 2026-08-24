from __future__ import annotations

from typing import Any

import pandas as pd

from compliance_checker import load_corpus
from engine_support import append_audit_event, authorized_corpus, generate_json, load_environment

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "audit_checklist_results.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "audit_checklist_report.md"
RESULT_COLUMNS = ["item_id", "domain", "unit_scope", "audit_question", "risk_description", "risk_level", "source_citation", "recommendation", "review_status"]
DOMAIN_CONFIG = {"An toan kho quy": ("agr_at01", "Chi nhanh loai 1"), "Bao mat CNTT va AI": ("agr_it07", "Khoi CNTT")}


def _fallback(domain: str, unit: str, row: pd.Series, index: int) -> dict[str, str]:
    article = str(row.get("article", "quy dinh nguon"))
    return {"item_id": f"CHK_{index:02d}", "domain": domain, "unit_scope": unit, "audit_question": f"{unit} co thuc hien dung yeu cau tai {article} khong?", "risk_description": "Rui ro van hanh hoac khong tuan thu quy dinh noi bo.", "risk_level": "MEDIUM", "source_citation": str(row["citation"]), "recommendation": "Thu thap bang chung, doi chieu dieu khoan nguon va yeu cau kiem toan vien xac minh.", "review_status": "NEEDS_HUMAN_REVIEW"}


def _items(domain: str, unit: str, rows: pd.DataFrame) -> list[dict[str, Any]] | None:
    evidence = "\n".join(f"CITATION: {row.citation}\nTEXT: {row.text}" for row in rows.itertuples(index=False))
    prompt = f'''Chi dung evidence de sinh checklist kiem toan cho {domain}, don vi {unit}.
Tra ve JSON array, moi object co audit_question, risk_description, risk_level (HIGH/MEDIUM/LOW), recommendation, source_citation.
source_citation phai sao chep dung mot citation trong evidence. Khong dua ra ket luan phe duyet.
EVIDENCE:\n{evidence}'''
    response = generate_json(prompt)
    if not isinstance(response, list) or not response:
        return None
    valid_citations = set(rows["citation"].astype(str))
    items = []
    for index, item in enumerate(response, start=1):
        if not isinstance(item, dict) or item.get("risk_level") not in {"HIGH", "MEDIUM", "LOW"}:
            return None
        citation = str(item.get("source_citation", "")).strip()
        if citation not in valid_citations:
            return None
        items.append({"item_id": f"CHK_{index:02d}", "domain": domain, "unit_scope": unit, "audit_question": str(item.get("audit_question", "")).strip(), "risk_description": str(item.get("risk_description", "")).strip(), "risk_level": str(item["risk_level"]), "source_citation": citation, "recommendation": str(item.get("recommendation", "")).strip(), "review_status": "NEEDS_HUMAN_REVIEW"})
    return items if all(all(str(value).strip() for value in item.values()) for item in items) else None


def generate_checklist(domain: str, unit: str = "", user_role: str = "Admin") -> pd.DataFrame:
    if domain not in DOMAIN_CONFIG:
        raise LookupError("Chua co cau hinh cho domain duoc yeu cau.")
    document_id, default_unit = DOMAIN_CONFIG[domain]
    corpus = load_corpus()
    visible = authorized_corpus(corpus, user_role)
    rows = visible[visible["document_id"].eq(document_id)].copy()
    if rows.empty:
        raise PermissionError("Role khong co evidence cho domain nay.")
    result_rows = _items(domain, unit or default_unit, rows) or [_fallback(domain, unit or default_unit, row, index) for index, (_, row) in enumerate(rows.iterrows(), start=1)]
    results = pd.DataFrame(result_rows, columns=RESULT_COLUMNS)
    if results.empty or not results["source_citation"].str.strip().all() or not results["review_status"].eq("NEEDS_HUMAN_REVIEW").all():
        raise ValueError("Citation or human review guardrail failed")
    append_audit_event(action="audit checklist generation", query=domain, user_role=user_role, rows=rows)
    return results


def run_demo() -> pd.DataFrame:
    groups = [generate_checklist(domain) for domain in DOMAIN_CONFIG]
    results = pd.concat(groups, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    citations_ok = results["source_citation"].str.strip().all()
    reviews_ok = results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    REPORT_PATH.write_text(f"# Audit Checklist Report - Buoi 19\n\nLLM provider: `{load_environment()}`\n\nItems: {len(results)}\nCitation integrity: {'PASS' if citations_ok else 'FAIL'}\nHuman review guardrail: {'PASS' if reviews_ok else 'FAIL'}\n", encoding="utf-8")
    print(f"CHECKLIST_ITEMS={len(results)}")
    print(f"CITATIONS_ATTACHED={'YES' if citations_ok else 'NO'}")
    print(f"HUMAN_REVIEW_GUARDRAIL={'PASS' if reviews_ok else 'FAIL'}")
    print(f"CHECKLIST_GENERATOR={'PASS' if not results.empty else 'FAIL'}")
    return results


if __name__ == "__main__":
    run_demo()
