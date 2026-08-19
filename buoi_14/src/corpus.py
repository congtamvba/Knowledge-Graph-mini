from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = {
    "chunk_id",
    "document_id",
    "text",
    "source_file",
    "title",
    "document_number",
    "document_type",
    "article",
    "effective_date",
    "status",
}

RESULT_COLUMNS = [
    "rank",
    "chunk_id",
    "document_id",
    "text",
    "retrieval_score",
    "retrieval_method",
    "citation",
]


def load_corpus(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Normalized corpus not found: {path}. Run scripts/prepare_corpus.py first."
        )

    corpus = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing_columns = REQUIRED_COLUMNS - set(corpus.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Normalized corpus is missing columns: {missing}")
    if corpus.empty:
        raise ValueError("Normalized corpus is empty")
    if corpus["chunk_id"].duplicated().any():
        raise ValueError("Normalized corpus contains duplicate chunk IDs")
    if corpus["text"].str.strip().eq("").any():
        raise ValueError("Normalized corpus contains empty text")
    return corpus


def build_retrieval_texts(corpus: pd.DataFrame) -> list[str]:
    retrieval_texts = []
    for row in corpus.itertuples(index=False):
        parts = [row.document_number, row.title, row.article, row.text]
        retrieval_texts.append("\n".join(part for part in parts if part).strip())
    return retrieval_texts


def format_citation(row: pd.Series) -> str:
    parts = [row["title"]]
    if row["document_number"]:
        parts.append(f"Số {row['document_number']}")
    if row["article"]:
        parts.append(row["article"])
    parts.append(row["chunk_id"])
    return f"[{' | '.join(parts)}]"


def build_results(
    corpus: pd.DataFrame,
    indices: Iterable[int],
    scores: Iterable[float],
    method: str,
) -> pd.DataFrame:
    records = []
    for rank, (index, score) in enumerate(zip(indices, scores), start=1):
        row = corpus.iloc[int(index)]
        records.append(
            {
                "rank": rank,
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "text": row["text"],
                "retrieval_score": float(score),
                "retrieval_method": method,
                "citation": format_citation(row),
            }
        )
    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)