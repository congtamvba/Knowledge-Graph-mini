from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

BUOI_17_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BUOI_17_ROOT.parent
BUOI_14_ROOT = WORKSPACE_ROOT / "buoi_14"
SECURE_CORPUS_PATH = WORKSPACE_ROOT / "buoi_16" / "data" / "processed" / "chunks_secure.csv"

if str(BUOI_14_ROOT) not in sys.path:
    sys.path.insert(0, str(BUOI_14_ROOT))

from src.bm25_retriever import BM25Retriever
from src.secure_retriever import filter_secure_corpus


class SecureRetrievalAdapter:
    def __init__(self, corpus_path: Path = SECURE_CORPUS_PATH) -> None:
        self.corpus_path = corpus_path.resolve()
        self.corpus = pd.read_csv(self.corpus_path, dtype=str, keep_default_na=False, encoding="utf-8")
        self.corpus = self.corpus.rename(
            columns={
                "so_ky_hieu": "document_number",
                "loai_van_ban": "document_type",
                "co_quan_ban_hanh": "issuing_authority",
                "ngay_ban_hanh": "issue_date",
            }
        )
        required = {"chunk_id", "document_id", "text", "title", "document_number", "article", "citation", "allowed_roles"}
        missing = sorted(required - set(self.corpus.columns))
        if missing:
            raise ValueError(f"Secure corpus is missing required columns: {missing}")

    def retrieve(
        self,
        question: str,
        user_role: str | Iterable[str],
        top_k: int = 5,
        method: str = "bm25",
    ) -> pd.DataFrame:
        if not question.strip():
            raise ValueError("Question must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if method.strip().lower() != "bm25":
            raise ValueError("Secure adapter currently reuses BM25 retrieval")

        roles = [user_role] if isinstance(user_role, str) else list(user_role)
        visible = self._filter_combined_corpus(roles)
        visible_ids = set(visible["chunk_id"]) if "chunk_id" in visible.columns else set()
        authorized_corpus = self.corpus[self.corpus["chunk_id"].isin(visible_ids)].copy()

        if authorized_corpus.empty:
            return self._empty_result()

        results = BM25Retriever(authorized_corpus).search(question, top_k=top_k)
        metadata = authorized_corpus.set_index("chunk_id")
        results["title"] = results["chunk_id"].map(metadata["title"])
        results["article"] = results["chunk_id"].map(metadata["article"])
        results["allowed_roles"] = results["chunk_id"].map(metadata["allowed_roles"])
        results["access_decision"] = "ALLOW"
        results["retrieval_method"] = method.strip().lower()
        return results[
            [
                "rank",
                "chunk_id",
                "document_id",
                "title",
                "article",
                "citation",
                "allowed_roles",
                "access_decision",
                "retrieval_method",
                "text",
                "retrieval_score",
            ]
        ]

    def _filter_combined_corpus(self, roles: list[str]) -> pd.DataFrame:
        normalized_roles = {str(role).strip() for role in roles if str(role).strip()}
        visible_rows = []
        for row in self.corpus.itertuples(index=False):
            try:
                allowed_roles = {str(role).strip() for role in json.loads(row.allowed_roles)}
            except (TypeError, json.JSONDecodeError):
                continue
            if normalized_roles & allowed_roles:
                visible_rows.append(row)
        if not visible_rows:
            return self.corpus.iloc[0:0].copy()
        return pd.DataFrame.from_records([row._asdict() for row in visible_rows])

    @staticmethod
    def _empty_result() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "rank",
                "chunk_id",
                "document_id",
                "title",
                "article",
                "citation",
                "allowed_roles",
                "access_decision",
                "retrieval_method",
                "text",
                "retrieval_score",
            ]
        )


__all__ = ["SECURE_CORPUS_PATH", "SecureRetrievalAdapter"]
