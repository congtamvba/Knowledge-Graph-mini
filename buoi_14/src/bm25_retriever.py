from __future__ import annotations

import re

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from src.corpus import build_results, build_retrieval_texts


TOKEN_PATTERN = re.compile(r"[\wÀ-ỹĐđ]+(?:[./-][\wÀ-ỹĐđ]+)*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(text)]


class BM25Retriever:
    def __init__(self, corpus: pd.DataFrame) -> None:
        self.corpus = corpus.reset_index(drop=True)
        tokenized_corpus = [tokenize(text) for text in build_retrieval_texts(self.corpus)]
        self.index = BM25Okapi(tokenized_corpus)

    def search(self, question: str, top_k: int = 5) -> pd.DataFrame:
        query_tokens = tokenize(question)
        if not query_tokens:
            raise ValueError("Question must contain at least one searchable token")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        scores = np.asarray(self.index.get_scores(query_tokens), dtype=np.float64)
        result_count = min(top_k, len(scores))
        top_indices = np.argsort(-scores, kind="stable")[:result_count]
        return build_results(
            self.corpus,
            top_indices,
            scores[top_indices],
            method="bm25",
        )