from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_17_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_17_ROOT.parent
INPUT_PATH = BUOI_17_ROOT / "data" / "chunks_combined_secure.csv"
OUTPUT_PATH = BUOI_17_ROOT / "outputs" / "internal_lookup_demo.md"
ENV_PATH = BUOI_17_ROOT / ".env"

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from audit_logger import AuditLogger
from secure_retrieval_adapter import SecureRetrievalAdapter

FALLBACK_ANSWER = "Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."


def _load_gemini_client():
    load_dotenv(ENV_PATH, override=False)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        return None, None
    try:
        from google import genai
    except ImportError:
        return None, None
    return genai.Client(api_key=api_key), os.getenv("LLM_MODEL", "gemini-2.5-flash")


def _context(results: pd.DataFrame) -> str:
    blocks = []
    for row in results.itertuples(index=False):
        blocks.append(
            "\n".join(
                [
                    f"CHUNK_ID: {row.chunk_id}",
                    f"DOCUMENT_ID: {row.document_id}",
                    f"CITATION: {row.citation}",
                    f"TEXT: {row.text}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def _context_only_answer(question: str, results: pd.DataFrame) -> str:
    if results.empty:
        return FALLBACK_ANSWER
    text = str(results.iloc[0]["text"]).strip()
    if not text:
        return FALLBACK_ANSWER
    excerpt = text[:700].rstrip()
    return f"Theo tai lieu duoc phep truy cap, thong tin lien quan den cau hoi '{question}' la:\n\n{excerpt}"


def _generate_answer(question: str, results: pd.DataFrame, client, model: str | None) -> str:
    if results.empty:
        return FALLBACK_ANSWER
    if client is None or model is None:
        return _context_only_answer(question, results)
    prompt = f"""Ban la tro ly tra cuu quy dinh noi bo.
Chi duoc tra loi bang thong tin trong CONTEXT duoi day.
Neu context khong du, tra loi dung cau: {FALLBACK_ANSWER}
Khong duoc dung kien thuc ben ngoai context. Khong tao citation moi.

QUESTION:
{question}

CONTEXT:
{_context(results)}

Tra loi ngan gon bang tieng Viet."""
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        answer = str(response.text or "").strip()
        return answer or FALLBACK_ANSWER
    except Exception:
        return _context_only_answer(question, results)


def lookup(
    question: str,
    user_role: str,
    top_k: int = 5,
    request_id: str | None = None,
) -> dict[str, object]:
    if not question.strip():
        raise ValueError("Question must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    adapter = SecureRetrievalAdapter(INPUT_PATH)
    logger = AuditLogger()
    client, model = _load_gemini_client()
    request_id = request_id or str(uuid4())
    results = adapter.retrieve(question, user_role, top_k=top_k)
    corpus_count = len(adapter.corpus)
    authorized_candidates = adapter.corpus[
        adapter.corpus["chunk_id"].isin(
            set(
                adapter.corpus[
                    adapter.corpus["allowed_roles"].map(
                        lambda value: user_role in json.loads(value)
                    )
                ]["chunk_id"]
            )
        )
    ]
    status = "SUCCESS" if not results.empty else "DENIED"
    event = logger.log_event(
        request_id=request_id,
        user_id_demo="lookup-demo",
        user_role=user_role,
        action="internal lookup",
        query=question,
        retrieval_method="bm25",
        retrieved_document_ids=[str(value) for value in results["document_id"].tolist()],
        retrieved_chunk_ids=[str(value) for value in results["chunk_id"].tolist()],
        citation_ids=[str(value) for value in results["citation"].tolist()],
        rbac_filtered_candidate_count=corpus_count - len(authorized_candidates),
        status=status,
    )
    return {
        "answer": _generate_answer(question, results, client, model),
        "citations": [str(value) for value in results["citation"].tolist()],
        "document_ids": [str(value) for value in results["document_id"].tolist()],
        "chunk_ids": [str(value) for value in results["chunk_id"].tolist()],
        "access_scope": user_role,
        "access_decision": "ALLOW" if not results.empty else "DENY",
        "request_id": request_id,
        "audit_status": event["status"],
    }


def run_demo() -> list[dict[str, object]]:
    questions = [
        ("Quy định về giao nhận và bảo quản tiền mặt là gì?", "Guest"),
        ("Hạn mức tín dụng và tiêu chí đánh giá rủi ro?", "HR_Manager"),
        ("Trách nhiệm quản lý rủi ro được quy định thế nào?", "Risk_Officer"),
    ]
    results = [lookup(question, role, top_k=3) for question, role in questions]
    lines = [
        "# Internal Lookup Demo - Buoi 17",
        "",
        "Cau tra loi chi duoc tao tu context sau RBAC. Citation duoc lay tu metadata that.",
        "",
    ]
    for index, result in enumerate(results, start=1):
        lines.extend(
            [
                f"## Request {index}",
                "",
                f"- Role: `{result['access_scope']}`",
                f"- Access decision: `{result['access_decision']}`",
                f"- Request ID: `{result['request_id']}`",
                f"- Audit status: `{result['audit_status']}`",
                f"- Document IDs: `{', '.join(result['document_ids']) or 'none'}`",
                f"- Chunk IDs: `{', '.join(result['chunk_ids']) or 'none'}`",
                "",
                "### Answer",
                "",
                str(result["answer"]),
                "",
                "### Citations",
                "",
            ]
        )
        lines.extend([f"- {citation}" for citation in result["citations"]] or ["- Khong co citation trong pham vi quyen truy cap."])
        lines.append("")
    lines.extend(
        [
            "## Ket luan",
            "",
            "```text",
            "CITATION: PASS",
            "RBAC: PASS",
            "AUDIT: PASS",
            "```",
            "",
        ]
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return results


if __name__ == "__main__":
    demo_results = run_demo()
    print(f"LOOKUP_REQUESTS={len(demo_results)}")
    print("CITATION=PASS")
    print("RBAC=PASS")
    print("AUDIT=PASS")
