from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
AUDIT_LOG_PATH = PROJECT_ROOT / "outputs" / "audit_log.jsonl"


def load_environment() -> str:
    load_dotenv(ENV_PATH, override=False)
    return os.getenv("LLM_PROVIDER", "ollama").strip().casefold()


def authorized_corpus(corpus: pd.DataFrame, user_role: str) -> pd.DataFrame:
    role = str(user_role).strip()
    if not role or "allowed_roles" not in corpus.columns:
        return corpus.iloc[0:0].copy()
    allowed = corpus["allowed_roles"].map(_has_role(role))
    return corpus.loc[allowed].copy()


def _has_role(role: str):
    def matches(value: object) -> bool:
        try:
            return role in {str(item).strip() for item in json.loads(str(value))}
        except (TypeError, json.JSONDecodeError):
            return False

    return matches


def rank_evidence(corpus: pd.DataFrame, query: str, top_k: int = 3) -> pd.DataFrame:
    terms = set(re.findall(r"[\wÀ-ỹĐđ]+", query.casefold()))
    if corpus.empty or not terms:
        return corpus.iloc[0:0].copy()
    scores = corpus.apply(
        lambda row: len(terms & set(re.findall(r"[\wÀ-ỹĐđ]+", f"{row.get('title', '')} {row.get('text', '')}".casefold()))),
        axis=1,
    )
    ranked = corpus.assign(retrieval_score=scores).sort_values("retrieval_score", ascending=False)
    return ranked[ranked["retrieval_score"] > 0].head(top_k).copy()


def generate_json(prompt: str) -> dict[str, Any] | list[Any] | None:
    provider = load_environment()
    try:
        if provider == "ollama":
            from ollama_adapter import OllamaClient

            response = OllamaClient().generate(prompt, format_json=True)
            return response if not (isinstance(response, dict) and response.get("status") == "FALLBACK") else None
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
            model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
            if not api_key or api_key.startswith("YOUR_"):
                return None
            from google import genai

            raw = str(genai.Client(api_key=api_key).models.generate_content(model=model, contents=prompt).text or "").strip()
            parsed = json.loads(raw.removeprefix("```json").removesuffix("```").strip())
            return parsed if isinstance(parsed, (dict, list)) else None
    except Exception:
        return None
    return None


def _sanitize_audit_query(query: str) -> str:
    patterns = (
        r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+",
        r"\bAIza[\w-]+\b",
    )
    sanitized = str(query)
    for pattern in patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized)
    return sanitized


def append_audit_event(*, action: str, query: str, user_role: str, rows: pd.DataFrame, status: str = "SUCCESS") -> str:
    request_id = str(uuid4())
    event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "user_id_demo": "buoi-19-demo",
        "user_role": user_role,
        "action": action,
        "query": _sanitize_audit_query(query),
        "retrieval_method": "local-token-rank",
        "retrieved_document_ids": [str(value) for value in rows.get("document_id", pd.Series(dtype=str)).tolist()],
        "retrieved_chunk_ids": [str(value) for value in rows.get("chunk_id", pd.Series(dtype=str)).tolist()],
        "citation_ids": [str(value) for value in rows.get("citation", pd.Series(dtype=str)).tolist()],
        "rbac_filtered_candidate_count": 0,
        "status": status,
    }
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    return request_id
