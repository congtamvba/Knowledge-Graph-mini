from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from engine_support import append_audit_event, authorized_corpus, generate_json, rank_evidence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "chunks_combined_secure.csv"
RESULTS_PATH = PROJECT_ROOT / "outputs" / "compliance_gap_results.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "compliance_gap_report.md"
RESULT_COLUMNS = ["external_document_id", "external_chunk_id", "external_requirement", "external_citation", "internal_document_id", "internal_chunk_id", "internal_evidence", "internal_citation", "classification", "reason", "review_status", "request_id"]


def run_gap_checker(user_role: str = "Admin") -> pd.DataFrame:
    corpus = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    visible = authorized_corpus(corpus, user_role)
    external = visible[~visible["document_id"].str.startswith("agr_")].drop_duplicates("document_id").head(3)
    internal = visible[visible["document_id"].str.startswith("agr_")]
    rows: list[dict[str, Any]] = []
    for _, external_row in external.iterrows():
        candidates = rank_evidence(internal, str(external_row["text"]), top_k=1)
        internal_row = candidates.iloc[0] if not candidates.empty else None
        classification, reason = "CHUA_DU_BANG_CHUNG", "Can human review so sanh evidence hai phia truoc khi ket luan."
        if internal_row is not None:
            prompt = f'''Chi dung evidence; tra ve JSON object classification (DAP_UNG, THIEU, CHENH_LECH, CHUA_DU_BANG_CHUNG) va reason. Khong ket luan neu evidence khong du.\nEXTERNAL: {external_row["text"]}\nINTERNAL: {internal_row["text"]}'''
            analysis = generate_json(prompt)
            if isinstance(analysis, dict) and analysis.get("classification") == "CHUA_DU_BANG_CHUNG":
                reason = str(analysis.get("reason", reason)).strip() or reason
        evidence_rows = pd.DataFrame([external_row] + ([] if internal_row is None else [internal_row]))
        rows.append({"external_document_id": str(external_row["document_id"]), "external_chunk_id": str(external_row["chunk_id"]), "external_requirement": str(external_row["text"]), "external_citation": str(external_row["citation"]), "internal_document_id": "" if internal_row is None else str(internal_row["document_id"]), "internal_chunk_id": "" if internal_row is None else str(internal_row["chunk_id"]), "internal_evidence": "" if internal_row is None else str(internal_row["text"]), "internal_citation": "" if internal_row is None else str(internal_row["citation"]), "classification": classification, "reason": reason, "review_status": "NEEDS_HUMAN_REVIEW", "request_id": append_audit_event(action="compliance gap check", query=str(external_row["title"]), user_role=user_role, rows=evidence_rows)})
    results = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")
    review_ok = not results.empty and results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    REPORT_PATH.write_text(f"# Compliance Gap Report - Buoi 19\n\nResults: {len(results)}\nHuman review guardrail: {'PASS' if review_ok else 'FAIL'}\n", encoding="utf-8")
    print(f"GAP_RESULTS={len(results)}")
    print(f"HUMAN_REVIEW_REQUIRED={'YES' if review_ok else 'NO'}")
    return results


if __name__ == "__main__":
    run_gap_checker()
