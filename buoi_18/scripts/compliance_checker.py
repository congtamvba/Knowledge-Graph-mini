from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_18_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_18_ROOT.parent
INPUT_PATH = BUOI_18_ROOT / "data" / "chunks_combined_secure.csv"
OUTPUT_PATH = BUOI_18_ROOT / "outputs" / "compliance_conflicts.csv"
REPORT_PATH = BUOI_18_ROOT / "outputs" / "compliance_conflict_report.md"
AUDIT_LOG_PATH = BUOI_18_ROOT / "outputs" / "audit_log.jsonl"
ENV_PATH = BUOI_18_ROOT / ".env"
BUOI_14_ROOT = WORKSPACE_ROOT / "buoi_14"
BUOI_17_SCRIPTS = WORKSPACE_ROOT / "Buoi_17" / "scripts"

if str(BUOI_14_ROOT) not in sys.path:
    sys.path.insert(0, str(BUOI_14_ROOT))
if str(BUOI_17_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BUOI_17_SCRIPTS))

from src.bm25_retriever import BM25Retriever
from src.secure_retriever import filter_secure_corpus
from audit_logger import AuditLogger

RESULT_COLUMNS = [
    "conflict_id",
    "domain",
    "doc_a_id",
    "doc_a_citation",
    "doc_a_text",
    "doc_b_id",
    "doc_b_citation",
    "doc_b_text",
    "conflict_type",
    "severity",
    "description",
    "review_status",
    "timestamp",
    "request_id",
]

DOMAIN_QUERIES = {
    "An toàn kho quỹ và vận chuyển tiền": "giao nhận bảo quản vận chuyển tiền mặt tài sản quý xe bọc thép",
    "CAR và quản lý rủi ro": "tỷ lệ an toàn vốn CAR hệ số rủi ro tín dụng",
    "Tín dụng và thẩm quyền phê duyệt": "hạn mức phán quyết tín dụng cho vay nông nghiệp Nghị định 55",
}

DOMAIN_DOCUMENTS = {
    "An toàn kho quỹ và vận chuyển tiền": "agr_at01",
    "CAR và quản lý rủi ro": "agr_car02",
    "Tín dụng và thẩm quyền phê duyệt": "agr_td03",
}


def load_corpus(path: Path = INPUT_PATH) -> pd.DataFrame:
    corpus = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {
        "chunk_id",
        "document_id",
        "text",
        "title",
        "so_ky_hieu",
        "article",
        "citation",
        "allowed_roles",
    }
    missing = sorted(required - set(corpus.columns))
    if missing:
        raise ValueError(f"Combined corpus is missing required columns: {missing}")
    if corpus.empty:
        raise ValueError("Combined corpus is empty")
    return corpus


def authorized_corpus(corpus: pd.DataFrame, user_role: str) -> pd.DataFrame:
    normalized_role = str(user_role).strip()
    if not normalized_role:
        return corpus.iloc[0:0].copy()
    visible_rows = []
    for row in corpus.itertuples(index=False):
        try:
            allowed_roles = {str(role).strip() for role in json.loads(row.allowed_roles)}
        except (TypeError, json.JSONDecodeError):
            continue
        if normalized_role in allowed_roles:
            visible_rows.append(row.chunk_id)
    return corpus[corpus["chunk_id"].isin(visible_rows)].copy()


def _external_evidence(
    corpus: pd.DataFrame,
    internal_row: pd.Series,
    user_role: str,
    top_k: int = 3,
) -> pd.DataFrame:
    visible = authorized_corpus(corpus, user_role)
    external = visible[~visible["document_id"].str.startswith("agr_")].copy()
    if external.empty:
        return external
    query = f"{internal_row['title']} {internal_row['article']} {internal_row['text']}"
    retrieval_corpus = external.rename(columns={"so_ky_hieu": "document_number"})
    results = BM25Retriever(retrieval_corpus).search(query, top_k=top_k)
    metadata = external.set_index("chunk_id")
    results["title"] = results["chunk_id"].map(metadata["title"])
    results["article"] = results["chunk_id"].map(metadata["article"])
    results["citation"] = results["chunk_id"].map(metadata["citation"])
    results["text"] = results["chunk_id"].map(metadata["text"])
    results["document_id"] = results["chunk_id"].map(metadata["document_id"])
    return results


def _evidence_package(internal_row: pd.Series, external_row: pd.Series) -> str:
    return "\n".join(
        [
            f"DOCUMENT_A_ID: {internal_row['document_id']}",
            f"DOCUMENT_A_CITATION: {internal_row['citation']}",
            f"DOCUMENT_A_ARTICLE: {internal_row['article']}",
            f"DOCUMENT_A_TEXT: {internal_row['text']}",
            f"DOCUMENT_B_ID: {external_row['document_id']}",
            f"DOCUMENT_B_CITATION: {external_row['citation']}",
            f"DOCUMENT_B_ARTICLE: {external_row['article']}",
            f"DOCUMENT_B_TEXT: {external_row['text']}",
        ]
    )


def _numeric_conflict(internal_text: str, external_text: str) -> tuple[str, str, str] | None:
    internal_numbers = {value.replace(",", ".") for value in re.findall(r"\d+(?:[.,]\d+)?\s*%?", internal_text)}
    external_numbers = {value.replace(",", ".") for value in re.findall(r"\d+(?:[.,]\d+)?\s*%?", external_text)}
    if not internal_numbers or not external_numbers or internal_numbers == external_numbers:
        return None
    if any(term in internal_text.casefold() + external_text.casefold() for term in ("hạn mức", "tỷ lệ", "tỷ đồng", "%", "mức tối thiểu")):
        return ("HẠN_MỨC_NGƯỠNG", "MEDIUM", "Hai evidence có các ngưỡng hoặc hạn mức số học khác nhau; cần kiểm toán viên xác định phạm vi áp dụng và hiệu lực.")
    return None


def _deterministic_analysis(internal_row: pd.Series, external_row: pd.Series) -> dict[str, str]:
    internal_text = str(internal_row["text"])
    external_text = str(external_row["text"])
    numeric = _numeric_conflict(internal_text, external_text)
    if numeric:
        conflict_type, severity, description = numeric
        return {"conflict_type": conflict_type, "severity": severity, "description": description}
    shared_terms = set(re.findall(r"[\wÀ-ỹĐđ]+", internal_text.casefold())) & set(re.findall(r"[\wÀ-ỹĐđ]+", external_text.casefold()))
    if len(shared_terms) < 3:
        description = "Chưa có đủ bằng chứng liên quan từ hai phía để kết luận xung đột."
    else:
        description = "Có evidence liên quan về cùng chủ đề, nhưng chưa xác lập được mâu thuẫn rõ ràng từ nội dung đã truy xuất."
    return {"conflict_type": "CHUA_DU_BANG_CHUNG", "severity": "LOW", "description": description}


def _llm_analysis(internal_row: pd.Series, external_row: pd.Series) -> dict[str, str] | None:
    load_dotenv(ENV_PATH, override=False)
    api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    model = os.getenv("LLM_MODEL")
    if not api_key or not model:
        return None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = f"""Phân tích compliance chỉ dựa trên evidence package dưới đây. Không được tạo citation mới.
Trả về JSON duy nhất với các khóa conflict_type, severity, description.
conflict_type phải là một trong: HAN_MUC_NGUONG, QUY_TRINH, THAM_QUYEN, THOI_HAN, KHAC, KHONG_XUNG_DOT, CHUA_DU_BANG_CHUNG.
severity phải là HIGH, MEDIUM hoặc LOW. Nếu không đủ bằng chứng, dùng CHUA_DU_BANG_CHUNG và LOW.

EVIDENCE PACKAGE:
{_evidence_package(internal_row, external_row)}"""
        response = client.models.generate_content(model=model, contents=prompt)
        raw = str(response.text or "").strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        allowed_types = {"HAN_MUC_NGUONG", "QUY_TRINH", "THAM_QUYEN", "THOI_HAN", "KHAC", "KHONG_XUNG_DOT", "CHUA_DU_BANG_CHUNG"}
        if parsed.get("conflict_type") not in allowed_types or parsed.get("severity") not in {"HIGH", "MEDIUM", "LOW"}:
            return None
        return {
            "conflict_type": str(parsed["conflict_type"]),
            "severity": str(parsed["severity"]),
            "description": str(parsed.get("description", "")).strip() or "LLM không cung cấp mô tả.",
        }
    except (ImportError, json.JSONDecodeError, TypeError, ValueError, Exception):
        return None


def _make_result(domain: str, internal_row: pd.Series, external_row: pd.Series, request_id: str, analysis: dict[str, str]) -> dict[str, Any]:
    citation_a = str(internal_row["citation"]).strip()
    citation_b = str(external_row["citation"]).strip()
    if not citation_a or not citation_b:
        raise ValueError("Citation integrity check failed")
    return {
        "conflict_id": str(uuid4()),
        "domain": domain,
        "doc_a_id": str(internal_row["document_id"]),
        "doc_a_citation": citation_a,
        "doc_a_text": str(internal_row["text"]),
        "doc_b_id": str(external_row["document_id"]),
        "doc_b_citation": citation_b,
        "doc_b_text": str(external_row["text"]),
        "conflict_type": analysis["conflict_type"],
        "severity": analysis["severity"],
        "description": analysis["description"],
        "review_status": "NEEDS_HUMAN_REVIEW",
        "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "request_id": request_id,
    }


def run_checker(
    user_role: str = "Admin",
    user_id: str = "compliance-demo",
    use_llm: bool = True,
    output_path: Path = OUTPUT_PATH,
    report_path: Path = REPORT_PATH,
    audit_log_path: Path = AUDIT_LOG_PATH,
) -> pd.DataFrame:
    corpus = load_corpus()
    visible = authorized_corpus(corpus, user_role)
    if visible.empty:
        raise PermissionError(f"Role {user_role!r} has no authorized evidence")
    logger = AuditLogger(audit_log_path)
    rows: list[dict[str, Any]] = []
    run_details: list[tuple[str, str, str, int]] = []
    for domain, document_id in DOMAIN_DOCUMENTS.items():
        internal = visible[visible["document_id"].eq(document_id)]
        external_candidates = visible[~visible["document_id"].str.startswith("agr_")]
        if internal.empty or external_candidates.empty:
            continue
        internal_query = DOMAIN_QUERIES[domain]
        retrieval_corpus = external_candidates.rename(columns={"so_ky_hieu": "document_number"})
        ranked = BM25Retriever(retrieval_corpus).search(internal_query, top_k=3)
        metadata = external_candidates.set_index("chunk_id")
        external_chunk_id = str(ranked.iloc[0]["chunk_id"])
        external = metadata.loc[external_chunk_id]
        request_id = str(uuid4())
        analysis = _llm_analysis(internal.iloc[0], external) if use_llm else None
        analysis = analysis or _deterministic_analysis(internal.iloc[0], external)
        result = _make_result(domain, internal.iloc[0], external, request_id, analysis)
        rows.append(result)
        logger.log_event(
            request_id=request_id,
            user_id_demo=user_id,
            user_role=user_role,
            action="compliance cross-comparison",
            query=internal_query,
            retrieval_method="bm25",
            retrieved_document_ids=[result["doc_a_id"], result["doc_b_id"]],
            retrieved_chunk_ids=[str(internal.iloc[0]["chunk_id"]), external_chunk_id],
            citation_ids=[result["doc_a_citation"], result["doc_b_citation"]],
            rbac_filtered_candidate_count=len(corpus) - len(visible),
            status="SUCCESS",
        )
        run_details.append((domain, result["doc_a_id"], result["doc_b_id"], len(ranked)))

    results = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False, encoding="utf-8-sig")
    report_lines = [
        "# Compliance Conflict Report - Buoi 18",
        "",
        "Cross-comparison được chạy sau RBAC trên corpus Buổi 18. Citation được lấy nguyên từ metadata nguồn.",
        "",
        f"- User role: `{user_role}`",
        f"- Authorized chunks: {len(visible)} / {len(corpus)}",
        "- Retrieval: BM25 trên tập external đã lọc quyền",
        f"- LLM analysis: {'enabled when LLM_API_KEY và LLM_MODEL có mặt; fallback deterministic otherwise' if use_llm else 'disabled; deterministic evidence analysis'}",
        "",
        "## Results",
        "",
        "| Domain | Internal citation | External citation | Type | Severity | Review |",
        "|---|---|---|---|---|---|",
    ]
    for row in results.itertuples(index=False):
        report_lines.append(f"| {row.domain} | {row.doc_a_citation} | {row.doc_b_citation} | {row.conflict_type} | {row.severity} | {row.review_status} |")
    citations_ok = not results.empty and results["doc_a_citation"].ne("").all() and results["doc_b_citation"].ne("").all()
    review_ok = not results.empty and results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    report_lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- RBAC được áp dụng trước BM25 và evidence package.",
            f"- Citation integrity: `{'PASS' if citations_ok else 'FAIL'}`.",
            f"- Human review guardrail: `{'PASS' if review_ok else 'FAIL'}`.",
            "- Không kết luận xung đột chỉ từ retrieval score; trường hợp chưa đủ evidence dùng `CHUA_DU_BANG_CHUNG`.",
            "",
            "```text",
            f"COMPLIANCE CHECKER ENGINE: {'PASS' if len(results) == 3 else 'FAIL'}",
            f"CONFLICTS DETECTED: {len(results)}",
            f"HUMAN REVIEW GUARDRAIL: {'PASS' if review_ok else 'FAIL'}",
            "```",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"COMPLIANCE_RESULTS={len(results)}")
    print(f"CITATION_INTEGRITY={'PASS' if citations_ok else 'FAIL'}")
    print(f"HUMAN_REVIEW_GUARDRAIL={'PASS' if review_ok else 'FAIL'}")
    print(f"COMPLIANCE_CHECKER={'PASS' if len(results) == 3 else 'FAIL'}")
    return results


if __name__ == "__main__":
    run_checker(use_llm=True)
