from __future__ import annotations

from typing import Protocol

import pandas as pd


HYBRID_RESULT_COLUMNS = [
    "final_rank",
    "chunk_id",
    "document_id",
    "bm25_rank",
    "dense_rank",
    "rrf_score",
    "text",
    "citation",
]


class Retriever(Protocol):
    def search(self, question: str, top_k: int = 5) -> pd.DataFrame: ...


class HybridRetriever:
    def __init__(
        self,
        bm25_retriever: Retriever,
        dense_retriever: Retriever,
        rrf_k: int = 60,
    ) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be at least 1")
        self.bm25_retriever = bm25_retriever
        self.dense_retriever = dense_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        question: str,
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> pd.DataFrame:
        if not question.strip():
            raise ValueError("Question must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if candidate_k < 1:
            raise ValueError("candidate_k must be at least 1")

        bm25_results = self.bm25_retriever.search(question, candidate_k)
        dense_results = self.dense_retriever.search(question, candidate_k)
        candidates: dict[str, dict[str, object]] = {}

        self._add_results(candidates, bm25_results, rank_field="bm25_rank")
        self._add_results(candidates, dense_results, rank_field="dense_rank")

        records = []
        for candidate in candidates.values():
            bm25_rank = candidate.get("bm25_rank")
            dense_rank = candidate.get("dense_rank")
            rrf_score = 0.0
            if bm25_rank is not None:
                rrf_score += 1.0 / (self.rrf_k + int(bm25_rank))
            if dense_rank is not None:
                rrf_score += 1.0 / (self.rrf_k + int(dense_rank))
            records.append({**candidate, "rrf_score": rrf_score})

        records.sort(
            key=lambda record: (
                -float(record["rrf_score"]),
                min(
                    int(rank)
                    for rank in (record.get("bm25_rank"), record.get("dense_rank"))
                    if rank is not None
                ),
                str(record["chunk_id"]),
            )
        )

        output_records = []
        for final_rank, record in enumerate(records[:top_k], start=1):
            output_records.append(
                {
                    "final_rank": final_rank,
                    "chunk_id": record["chunk_id"],
                    "document_id": record["document_id"],
                    "bm25_rank": record.get("bm25_rank"),
                    "dense_rank": record.get("dense_rank"),
                    "rrf_score": record["rrf_score"],
                    "text": record["text"],
                    "citation": record["citation"],
                }
            )

        results = pd.DataFrame.from_records(output_records, columns=HYBRID_RESULT_COLUMNS)
        if not results.empty:
            results["bm25_rank"] = results["bm25_rank"].astype("Int64")
            results["dense_rank"] = results["dense_rank"].astype("Int64")
        return results

    @staticmethod
    def _add_results(
        candidates: dict[str, dict[str, object]],
        results: pd.DataFrame,
        rank_field: str,
    ) -> None:
        if results["chunk_id"].duplicated().any():
            raise ValueError(f"{rank_field} input contains duplicate chunk IDs")

        for row in results.itertuples(index=False):
            candidate = candidates.setdefault(
                row.chunk_id,
                {
                    "chunk_id": row.chunk_id,
                    "document_id": row.document_id,
                    "text": row.text,
                    "citation": row.citation,
                },
            )
            if (
                candidate["document_id"] != row.document_id
                or candidate["text"] != row.text
                or candidate["citation"] != row.citation
            ):
                raise ValueError(f"Inconsistent data for chunk {row.chunk_id}")
            candidate[rank_field] = int(row.rank)