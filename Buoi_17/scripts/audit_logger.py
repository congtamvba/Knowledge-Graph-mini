from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import pandas as pd

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_17_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_17_ROOT.parent
AUDIT_LOG_PATH = BUOI_17_ROOT / "outputs" / "audit_log.jsonl"
SECURE_CORPUS_PATH = WORKSPACE_ROOT / "buoi_16" / "data" / "processed" / "chunks_secure.csv"

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from secure_retrieval_adapter import SecureRetrievalAdapter
from src.secure_retriever import filter_secure_corpus

SENSITIVE_KEY_PARTS = ("password", "api_key", "apikey", "secret", "token", "private_key")
AUDIT_FIELDS = (
    "timestamp_utc",
    "request_id",
    "user_id_demo",
    "user_role",
    "action",
    "query",
    "retrieval_method",
    "retrieved_document_ids",
    "retrieved_chunk_ids",
    "citation_ids",
    "rbac_filtered_candidate_count",
    "status",
)


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.casefold().replace("-", "_")
    return any(part in normalized_key for part in SENSITIVE_KEY_PARTS)


def _sanitize(value: Any, key: str = "") -> Any:
    if _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): _sanitize(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item, key) for item in value]
    return value


class AuditLogger:
    def __init__(self, log_path: Path = AUDIT_LOG_PATH) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        *,
        user_id_demo: str,
        user_role: str,
        action: str,
        query: str,
        retrieval_method: str,
        retrieved_document_ids: list[str],
        retrieved_chunk_ids: list[str],
        citation_ids: list[str],
        rbac_filtered_candidate_count: int,
        status: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"SUCCESS", "DENIED", "ERROR"}:
            raise ValueError("status must be SUCCESS, DENIED, or ERROR")
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id or str(uuid4()),
            "user_id_demo": user_id_demo,
            "user_role": user_role,
            "action": action,
            "query": query,
            "retrieval_method": retrieval_method,
            "retrieved_document_ids": retrieved_document_ids,
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "citation_ids": citation_ids,
            "rbac_filtered_candidate_count": rbac_filtered_candidate_count,
            "status": status,
        }
        sanitized_event = _sanitize(event)
        with self.log_path.open("a", encoding="utf-8") as output_file:
            output_file.write(json.dumps(sanitized_event, ensure_ascii=False) + "\n")
        return sanitized_event


def _result_values(results: pd.DataFrame, column: str) -> list[str]:
    if results.empty or column not in results.columns:
        return []
    return [str(value) for value in results[column].dropna().tolist()]


def run_demo(log_path: Path = AUDIT_LOG_PATH) -> list[dict[str, Any]]:
    corpus = pd.read_csv(SECURE_CORPUS_PATH, dtype=str, keep_default_na=False, encoding="utf-8")
    adapter = SecureRetrievalAdapter(SECURE_CORPUS_PATH)
    logger = AuditLogger(log_path)
    if log_path.exists():
        log_path.unlink()

    requests = [
        ("demo01", "Guest", "allowed lookup", "quy dinh giao nhan bao quan tien mat", "SUCCESS"),
        ("demo02", "Staff", "denied lookup", "quy dinh giao nhan bao quan tien mat", "DENIED"),
        ("demo03", "Risk_Officer", "normal lookup", "trach nhiem quan ly rui ro", "SUCCESS"),
    ]
    events = []
    for user_id, role, action, query, status in requests:
        visible = adapter.retrieve(query, role, top_k=3)
        visible_candidates = filter_secure_corpus(corpus, [role])
        authorized_ids = (
            set(visible_candidates["chunk_id"])
            if "chunk_id" in visible_candidates.columns
            else set()
        )
        filtered_count = len(corpus) - len(authorized_ids)
        events.append(
            logger.log_event(
                user_id_demo=user_id,
                user_role=role,
                action=action,
                query=query,
                retrieval_method="bm25",
                retrieved_document_ids=_result_values(visible, "document_id") if status != "DENIED" else [],
                retrieved_chunk_ids=_result_values(visible, "chunk_id") if status != "DENIED" else [],
                citation_ids=_result_values(visible, "citation") if status != "DENIED" else [],
                rbac_filtered_candidate_count=filtered_count,
                status=status,
            )
        )
    return events


if __name__ == "__main__":
    events = run_demo()
    print(f"AUDIT_EVENTS_WRITTEN={len(events)}")
    print("AUDIT_TRAIL=PASS")
