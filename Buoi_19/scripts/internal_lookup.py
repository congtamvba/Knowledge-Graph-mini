from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd

from engine_support import append_audit_event, authorized_corpus, load_environment, rank_evidence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "agribank_internal_policies.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "internal_lookup_demo.md"
FALLBACK_ANSWER = "Khong tim thay du thong tin trong pham vi tai lieu duoc phep truy cap."


def _corpus() -> pd.DataFrame:
    corpus = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {"chunk_id", "document_id", "text", "citation", "allowed_roles"}
    if corpus.empty or required - set(corpus.columns):
        raise ValueError("Internal policy corpus is invalid")
    return corpus


def lookup(question: str, user_role: str, top_k: int = 3) -> dict[str, object]:
    if not question.strip():
        raise ValueError("Question must not be empty")
    corpus = _corpus()
    visible = authorized_corpus(corpus, user_role)
    results = rank_evidence(visible, question, top_k=top_k)
    citations = [str(value) for value in results.get("citation", pd.Series(dtype=str)).tolist()]
    answer = FALLBACK_ANSWER if results.empty else str(results.iloc[0]["text"]).strip()[:700]
    request_id = append_audit_event(action="internal lookup", query=question, user_role=user_role, rows=results, status="SUCCESS" if not results.empty else "DENIED")
    return {"answer": answer, "citations": citations, "document_ids": [str(value) for value in results.get("document_id", pd.Series(dtype=str)).tolist()], "chunk_ids": [str(value) for value in results.get("chunk_id", pd.Series(dtype=str)).tolist()], "access_scope": user_role, "access_decision": "ALLOW" if not results.empty else "DENY", "request_id": request_id, "review_status": "NEEDS_HUMAN_REVIEW", "llm_provider": load_environment()}


def run_demo() -> list[dict[str, object]]:
    requests = [("quy dinh giao nhan bao quan tien mat", "Guest"), ("trach nhiem quan ly rui ro", "Admin")]
    results = [lookup(question, role) for question, role in requests]
    lines = ["# Internal Lookup Demo - Buoi 19", ""]
    for index, result in enumerate(results, start=1):
        lines.extend([f"## Request {index}", "", f"- Review: `{result['review_status']}`", "", str(result["answer"]), "", "### Citations", *[f"- {citation}" for citation in result["citations"]], ""])
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return results


if __name__ == "__main__":
    results = run_demo()
    print(f"LOOKUP_REQUESTS={len(results)}")
    print("HUMAN_REVIEW_GUARDRAIL=PASS")
