from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np
import pandas as pd
from sentence_transformers import CrossEncoder

from src.hybrid_retriever import HybridRetriever


DEFAULT_RERANKER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
RERANK_RESULT_COLUMNS = [
    "final_rank",
    "chunk_id",
    "document_id",
    "hybrid_rank",
    "hybrid_score",
    "rerank_score",
    "text",
    "citation",
]


class PairScorer(Protocol):
    def predict(
        self,
        sentences: Sequence[Sequence[str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> np.ndarray: ...


class NeuralReranker:
    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        model_name: str = DEFAULT_RERANKER_MODEL,
        batch_size: int = 8,
        model: PairScorer | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.hybrid_retriever = hybrid_retriever
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = model or CrossEncoder(model_name, device="cpu", max_length=512)

    def search(
        self,
        question: str,
        candidate_k: int = 20,
        top_k: int = 5,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        if not question.strip():
            raise ValueError("Question must not be empty")
        if candidate_k < 1 or top_k < 1:
            raise ValueError("candidate_k and top_k must be at least 1")
        if top_k > candidate_k:
            raise ValueError("top_k cannot exceed candidate_k")

        candidates = self.hybrid_retriever.search(
            question,
            top_k=candidate_k,
            candidate_k=candidate_k,
        )
        reranked = self.rerank(question, candidates, top_k=top_k)
        return candidates, reranked

    def rerank(
        self,
        question: str,
        candidates: pd.DataFrame,
        top_k: int = 5,
    ) -> pd.DataFrame:
        if candidates.empty:
            return pd.DataFrame(columns=RERANK_RESULT_COLUMNS)
        if candidates["chunk_id"].duplicated().any():
            raise ValueError("Hybrid candidates contain duplicate chunk IDs")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        pairs = [
            [question, f"{row.citation}\n{row.text}"]
            for row in candidates.itertuples(index=False)
        ]
        scores = np.asarray(
            self.model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            ),
            dtype=np.float64,
        ).reshape(-1)
        if len(scores) != len(candidates):
            raise ValueError("Reranker returned a score count that does not match candidates")

        scored = candidates.copy()
        scored["rerank_score"] = scores
        scored = scored.sort_values(
            ["rerank_score", "rrf_score", "final_rank"],
            ascending=[False, False, True],
            kind="stable",
        ).head(top_k)

        records = []
        for final_rank, row in enumerate(scored.itertuples(index=False), start=1):
            records.append(
                {
                    "final_rank": final_rank,
                    "chunk_id": row.chunk_id,
                    "document_id": row.document_id,
                    "hybrid_rank": int(row.final_rank),
                    "hybrid_score": float(row.rrf_score),
                    "rerank_score": float(row.rerank_score),
                    "text": row.text,
                    "citation": row.citation,
                }
            )
        return pd.DataFrame.from_records(records, columns=RERANK_RESULT_COLUMNS)