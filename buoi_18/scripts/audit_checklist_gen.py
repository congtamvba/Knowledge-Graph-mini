from __future__ import annotations

import json
import os
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
OUTPUT_PATH = BUOI_18_ROOT / "outputs" / "audit_checklist_results.csv"
REPORT_PATH = BUOI_18_ROOT / "outputs" / "audit_checklist_report.md"
AUDIT_LOG_PATH = BUOI_18_ROOT / "outputs" / "audit_log.jsonl"
ENV_PATH = BUOI_18_ROOT / ".env"
BUOI_17_SCRIPTS = WORKSPACE_ROOT / "Buoi_17" / "scripts"

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
if str(BUOI_17_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BUOI_17_SCRIPTS))

from audit_logger import AuditLogger
from compliance_checker import authorized_corpus, load_corpus
from src.bm25_retriever import BM25Retriever

RESULT_COLUMNS = [
    "item_id",
    "domain",
    "unit_scope",
    "audit_question",
    "risk_description",
    "risk_level",
    "source_citation",
    "recommendation",
    "review_status",
]

DOMAIN_CONFIG = {
    "An toàn kho quỹ": {
        "document_id": "agr_at01",
        "unit_scope": "Chi nhánh loại 1; Phòng giao dịch",
        "query": "giao nhận bảo quản vận chuyển tiền mặt xe bọc thép camera kho tiền",
        "external_document_ids": {"44209"},
    },
    "Bảo mật CNTT & AI": {
        "document_id": "agr_it07",
        "unit_scope": "Khối CNTT",
        "query": "bảo mật dữ liệu AI mã hóa audit trail JSON Lines lưu trữ hệ thống RAG",
        "external_document_ids": set(),
    },
}


def _legal_match(
    corpus: pd.DataFrame,
    internal_row: pd.Series,
    user_role: str,
    allowed_document_ids: set[str],
) -> pd.Series | None:
    if not allowed_document_ids:
        return None
    visible = authorized_corpus(corpus, user_role)
    external = visible[visible["document_id"].isin(allowed_document_ids)].copy()
    if external.empty:
        return None
    retrieval_corpus = external.rename(columns={"so_ky_hieu": "document_number"})
    query = f"{internal_row['title']} {internal_row['article']} {internal_row['text']}"
    ranked = BM25Retriever(retrieval_corpus).search(query, top_k=1)
    if ranked.empty:
        return None
    return external.set_index("chunk_id").loc[str(ranked.iloc[0]["chunk_id"])]


def _fallback_item(domain: str, unit_scope: str, row: pd.Series, legal_row: pd.Series | None, item_number: int) -> dict[str, Any]:
    text = str(row["text"])
    article = str(row["article"])
    lower_text = text.casefold()
    if "mã hóa" in lower_text or "aes" in lower_text or "audit" in lower_text:
        risk_level = "HIGH"
        question = f"{unit_scope} có thực hiện đúng yêu cầu tại {article}, bao gồm bảo vệ dữ liệu và lưu audit trail đầy đủ không?"
        risk = "Lộ dữ liệu nhạy cảm, mất khả năng truy vết hoặc không đáp ứng yêu cầu an toàn thông tin."
        recommendation = "Kiểm tra cấu hình mã hóa, quyền truy cập, trường log bắt buộc và bằng chứng lưu trữ audit trail."
    elif "3 tỷ" in lower_text or "xe ô tô bọc thép" in lower_text or "chìa khóa" in lower_text:
        risk_level = "HIGH"
        question = f"{unit_scope} có tuân thủ yêu cầu an toàn vận chuyển/kho tiền tại {article} không?"
        risk = "Thất thoát tiền mặt hoặc xâm phạm an toàn kho quỹ do không đáp ứng phương án bảo vệ."
        recommendation = "Đối chiếu hồ sơ chuyến vận chuyển, phương tiện, nhân sự bảo vệ và biên bản kiểm soát thực tế."
    elif "camera" in lower_text or "niêm phong" in lower_text or "kiểm đếm" in lower_text:
        risk_level = "MEDIUM"
        question = f"{unit_scope} có thực hiện kiểm đếm, giám sát và niêm phong theo {article} không?"
        risk = "Sai lệch kiểm đếm, thất thoát hoặc không phát hiện tiền nghi giả kịp thời."
        recommendation = "Kiểm tra video giám sát, biên bản kiểm đếm, biên bản niêm phong và thời điểm báo cáo."
    else:
        risk_level = "MEDIUM"
        question = f"{unit_scope} có thực hiện đúng yêu cầu tại {article} không?"
        risk = "Vi phạm quy định nội bộ và phát sinh rủi ro vận hành."
        recommendation = "Thu thập hồ sơ thực hiện, phỏng vấn người phụ trách và đối chiếu với điều khoản nguồn."

    citations = [str(row["citation"]).strip()]
    if legal_row is not None and str(legal_row["citation"]).strip():
        citations.append(str(legal_row["citation"]).strip())
    return {
        "item_id": f"CHK_{item_number:02d}",
        "domain": domain,
        "unit_scope": unit_scope,
        "audit_question": question,
        "risk_description": risk,
        "risk_level": risk_level,
        "source_citation": "\n".join(citations),
        "recommendation": recommendation,
        "review_status": "NEEDS_HUMAN_REVIEW",
    }


def _llm_items(domain: str, unit_scope: str, rows: pd.DataFrame, legal_rows: list[pd.Series]) -> list[dict[str, Any]] | None:
    load_dotenv(ENV_PATH, override=False)
    api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    model = os.getenv("LLM_MODEL")
    if not api_key or not model:
        return None
    evidence = []
    for row, legal_row in zip(rows.itertuples(index=False), legal_rows):
        evidence.append(
            f"INTERNAL_CITATION: {row.citation}\nINTERNAL_TEXT: {row.text}\n"
            f"EXTERNAL_CITATION: {legal_row['citation'] if legal_row is not None else ''}\n"
            f"EXTERNAL_TEXT: {legal_row['text'] if legal_row is not None else ''}"
        )
    prompt = f"""Sinh checklist kiểm toán bằng tiếng Việt chỉ dựa trên evidence dưới đây.
Domain: {domain}
Unit: {unit_scope}
Trả về JSON array duy nhất. Mỗi item có audit_question, risk_description, risk_level (HIGH/MEDIUM/LOW), recommendation và source_citation.
source_citation phải sao chép nguyên văn một hoặc nhiều citation trong evidence, không được bịa citation.
Không đưa ra kết luận đã được phê duyệt; mọi item phải cần human review.

EVIDENCE:\n{chr(10).join(evidence)}"""
    try:
        from google import genai

        response = genai.Client(api_key=api_key).models.generate_content(model=model, contents=prompt)
        raw = str(response.text or "").replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or not parsed:
            return None
        valid_citations = {str(value) for row in rows.itertuples(index=False) for value in [row.citation]}
        result = []
        for index, item in enumerate(parsed, start=1):
            citation = str(item.get("source_citation", "")).strip()
            if not citation or not any(value in citation for value in valid_citations):
                return None
            if item.get("risk_level") not in {"HIGH", "MEDIUM", "LOW"}:
                return None
            result.append({
                "item_id": f"CHK_{index:02d}",
                "domain": domain,
                "unit_scope": unit_scope,
                "audit_question": str(item.get("audit_question", "")).strip(),
                "risk_description": str(item.get("risk_description", "")).strip(),
                "risk_level": str(item["risk_level"]),
                "source_citation": citation,
                "recommendation": str(item.get("recommendation", "")).strip(),
                "review_status": "NEEDS_HUMAN_REVIEW",
            })
        if any(not result_item[field] for result_item in result for field in RESULT_COLUMNS):
            return None
        return result
    except Exception:
        return None


def generate_checklist(
    domain: str,
    unit: str,
    user_role: str = "Admin",
    user_id: str = "checklist-demo",
    use_llm: bool = True,
) -> pd.DataFrame:
    if domain not in DOMAIN_CONFIG:
        raise LookupError("Chưa có dữ liệu quy định cho domain được yêu cầu.")
    corpus = load_corpus()
    visible = authorized_corpus(corpus, user_role)
    config = DOMAIN_CONFIG[domain]
    rows = visible[visible["document_id"].eq(config["document_id"])].copy()
    if rows.empty:
        raise PermissionError(f"Role {user_role!r} không có quyền truy cập domain {domain!r}.")
    legal_rows = [
        _legal_match(corpus, row, user_role, config["external_document_ids"])
        for _, row in rows.iterrows()
    ]
    result_rows = _llm_items(domain, unit or config["unit_scope"], rows, legal_rows) if use_llm else None
    if result_rows is None:
        result_rows = [
            _fallback_item(domain, unit or config["unit_scope"], row, legal_row, index)
            for index, ((_, row), legal_row) in enumerate(zip(rows.iterrows(), legal_rows), start=1)
        ]
    results = pd.DataFrame(result_rows, columns=RESULT_COLUMNS)
    if results.empty or not results["source_citation"].str.strip().all():
        raise ValueError("Checklist citation integrity check failed")
    if not results["review_status"].eq("NEEDS_HUMAN_REVIEW").all():
        raise ValueError("Human review guardrail check failed")
    request_id = str(uuid4())
    logger = AuditLogger(AUDIT_LOG_PATH)
    logger.log_event(
        request_id=request_id,
        user_id_demo=user_id,
        user_role=user_role,
        action="audit checklist generation",
        query=f"{domain} / {unit}",
        retrieval_method="bm25",
        retrieved_document_ids=[str(value) for value in rows["document_id"].tolist()],
        retrieved_chunk_ids=[str(value) for value in rows["chunk_id"].tolist()],
        citation_ids=[str(value) for value in rows["citation"].tolist()],
        rbac_filtered_candidate_count=len(corpus) - len(visible),
        status="SUCCESS",
    )
    return results


def run_demo() -> pd.DataFrame:
    outputs = []
    for domain, unit in [("An toàn kho quỹ", "Chi nhánh loại 1"), ("Bảo mật CNTT & AI", "Khối CNTT")]:
        outputs.append(generate_checklist(domain, unit, use_llm=False))
    results = pd.concat(outputs, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    citations_ok = results["source_citation"].str.strip().ne("").all()
    reviews_ok = results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    report_lines = [
        "# Audit Checklist Report - Buoi 18",
        "",
        "Checklist được sinh từ evidence đã lọc RBAC. Citation được lấy từ metadata nguồn; kết quả chỉ là bản nháp cần kiểm toán viên xác minh.",
        "",
        f"- Checklist items: {len(results)}",
        f"- Domains: {', '.join(results['domain'].drop_duplicates())}",
        "- Retrieval: BM25 trên corpus đã lọc quyền",
        "- Demo generation: deterministic evidence fallback; LLM adapter có thể bật khi cấu hình model/API hợp lệ",
        "",
        "## Results",
        "",
        "| Item | Domain | Unit | Risk | Citation | Review |",
        "|---|---|---|---|---|---|",
    ]
    for row in results.itertuples(index=False):
        citation = str(row.source_citation).replace("|", "\\|").replace("\n", "<br>")
        report_lines.append(f"| {row.item_id} | {row.domain} | {row.unit_scope} | {row.risk_level} | {citation} | {row.review_status} |")
    report_lines.extend(
        [
            "",
            "```text",
            f"CHECKLIST GENERATOR ENGINE: {'PASS' if len(results) > 0 else 'FAIL'}",
            f"CHECKLIST ITEMS GENERATED: {len(results)}",
            f"CITATIONS ATTACHED: {'YES' if citations_ok else 'NO'}",
            f"HUMAN REVIEW GUARDRAIL: {'PASS' if reviews_ok else 'FAIL'}",
            "```",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"CHECKLIST_ITEMS={len(results)}")
    print(f"CITATIONS_ATTACHED={'YES' if citations_ok else 'NO'}")
    print(f"HUMAN_REVIEW_GUARDRAIL={'PASS' if reviews_ok else 'FAIL'}")
    print("CHECKLIST_GENERATOR=PASS")
    return results


if __name__ == "__main__":
    run_demo()
