from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from engine_support import append_audit_event, authorized_corpus, generate_json, load_environment, rank_evidence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "chunks_combined_secure.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "compliance_conflicts.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "compliance_conflict_report.md"
RESULT_COLUMNS = ["domain", "doc_a_citation", "doc_b_citation", "conflict_type", "severity", "description", "review_status", "request_id"]
DOMAIN_QUERIES = {
    "An toan kho quy va van chuyen tien": ("agr_at01", "giao nhan bao quan van chuyen tien mat xe boc thep"),
    "CAR va quan ly rui ro": ("agr_car02", "ty le an toan von CAR he so rui ro tin dung"),
    "Tin dung va tham quyen phe duyet": ("agr_td03", "han muc phe duyet tin dung cho vay"),
}


def load_corpus(path: Path = INPUT_PATH) -> pd.DataFrame:
    corpus = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {"chunk_id", "document_id", "text", "title", "citation", "allowed_roles"}
    missing = sorted(required - set(corpus.columns))
    if missing or corpus.empty:
        raise ValueError(f"Combined corpus is invalid; missing={missing}")
    return corpus


def _deterministic(internal: pd.Series, external: pd.Series) -> dict[str, str]:
    internal_terms = set(str(internal["text"]).casefold().split())
    external_terms = set(str(external["text"]).casefold().split())
    description = "Evidence co cung chu de nhung can kiem toan vien doi chieu pham vi ap dung."
    if len(internal_terms & external_terms) < 3:
        description = "Chua du bang chung tu hai evidence de ket luan xung dot."
    return {"conflict_type": "CHUA_DU_BANG_CHUNG", "severity": "LOW", "description": description}


def _analysis(internal: pd.Series, external: pd.Series) -> dict[str, str]:
    prompt = f'''Chi phan tich dung hai evidence duoi day, khong tao citation.
Tra ve JSON object duy nhat: conflict_type (HAN_MUC_NGUONG, QUY_TRINH, THAM_QUYEN, THOI_HAN, KHAC, KHONG_XUNG_DOT, CHUA_DU_BANG_CHUNG), severity (HIGH, MEDIUM, LOW), description.
DOCUMENT_A_CITATION: {internal["citation"]}
DOCUMENT_A_TEXT: {internal["text"]}
DOCUMENT_B_CITATION: {external["citation"]}
DOCUMENT_B_TEXT: {external["text"]}'''
    result = generate_json(prompt)
    if isinstance(result, dict) and result.get("conflict_type") in {"HAN_MUC_NGUONG", "QUY_TRINH", "THAM_QUYEN", "THOI_HAN", "KHAC", "KHONG_XUNG_DOT", "CHUA_DU_BANG_CHUNG"} and result.get("severity") in {"HIGH", "MEDIUM", "LOW"}:
        return {"conflict_type": str(result["conflict_type"]), "severity": str(result["severity"]), "description": str(result.get("description", "")).strip() or "LLM khong cung cap mo ta."}
    return _deterministic(internal, external)


def run_checker(user_role: str = "Admin") -> pd.DataFrame:
    corpus = load_corpus()
    visible = authorized_corpus(corpus, user_role)
    if visible.empty:
        raise PermissionError(f"Role {user_role!r} has no authorized evidence")
    rows: list[dict[str, Any]] = []
    for domain, (internal_id, query) in DOMAIN_QUERIES.items():
        internal = visible[visible["document_id"].eq(internal_id)]
        external = visible[~visible["document_id"].str.startswith("agr_")]
        ranked = rank_evidence(external, query)
        if internal.empty or ranked.empty:
            continue
        evidence_a, evidence_b = internal.iloc[0], ranked.iloc[0]
        analysis = _analysis(evidence_a, evidence_b)
        evidence_rows = pd.DataFrame([evidence_a, evidence_b])
        rows.append({"domain": domain, "doc_a_citation": str(evidence_a["citation"]), "doc_b_citation": str(evidence_b["citation"]), **analysis, "review_status": "NEEDS_HUMAN_REVIEW", "request_id": append_audit_event(action="compliance cross-comparison", query=query, user_role=user_role, rows=evidence_rows)})
    results = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    citations_ok = not results.empty and results[["doc_a_citation", "doc_b_citation"]].map(lambda value: bool(str(value).strip())).all().all()
    reviews_ok = not results.empty and results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    REPORT_PATH.write_text("\n".join(["# Compliance Conflict Report - Buoi 19", "", f"LLM provider: `{load_environment()}`", f"Results: {len(results)}", f"Citation integrity: {'PASS' if citations_ok else 'FAIL'}", f"Human review guardrail: {'PASS' if reviews_ok else 'FAIL'}", ""]), encoding="utf-8")
    print(f"COMPLIANCE_RESULTS={len(results)}")
    print(f"CITATION_INTEGRITY={'PASS' if citations_ok else 'FAIL'}")
    print(f"HUMAN_REVIEW_GUARDRAIL={'PASS' if reviews_ok else 'FAIL'}")
    print(f"COMPLIANCE_CHECKER={'PASS' if not results.empty and citations_ok and reviews_ok else 'FAIL'}")
    return results


if __name__ == "__main__":
    run_checker()
