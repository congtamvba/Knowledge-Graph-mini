from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.corpus import build_results, build_retrieval_texts


DEFAULT_MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"
CACHE_VERSION = "dense-v1"


class DenseRetriever:
    def __init__(
        self,
        corpus: pd.DataFrame,
        corpus_path: Path,
        cache_dir: Path,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = 32,
    ) -> None:
        self.corpus = corpus.reset_index(drop=True)
        self.model_name = model_name
        self.batch_size = batch_size
        self.retrieval_texts = build_retrieval_texts(self.corpus)
        self.model = SentenceTransformer(model_name, device="cpu")

        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = self._cache_key(corpus_path)
        self.cache_path = cache_dir / f"dense_embeddings_{cache_key}.npz"
        self.embeddings, cache_hit = self._load_or_create_embeddings()
        print(f"Dense embedding cache: {'HIT' if cache_hit else 'CREATED'} ({self.cache_path})")

    def _cache_key(self, corpus_path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(CACHE_VERSION.encode("utf-8"))
        digest.update(self.model_name.encode("utf-8"))
        digest.update(corpus_path.read_bytes())
        return digest.hexdigest()[:16]

    def _load_or_create_embeddings(self) -> tuple[np.ndarray, bool]:
        expected_chunk_ids = self.corpus["chunk_id"].to_numpy(dtype=str)
        if self.cache_path.is_file():
            with np.load(self.cache_path, allow_pickle=False) as cached:
                embeddings = cached["embeddings"]
                chunk_ids = cached["chunk_ids"]
                cached_model = str(cached["model_name"].item())
            if (
                cached_model == self.model_name
                and np.array_equal(chunk_ids, expected_chunk_ids)
                and embeddings.shape[0] == len(self.corpus)
            ):
                return embeddings.astype(np.float32, copy=False), True

        embeddings = self.model.encode(
            self.retrieval_texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32, copy=False)

        temporary_path = self.cache_path.with_suffix(".tmp.npz")
        with temporary_path.open("wb") as handle:
            np.savez_compressed(
                handle,
                embeddings=embeddings,
                chunk_ids=expected_chunk_ids,
                model_name=np.asarray(self.model_name),
            )
        temporary_path.replace(self.cache_path)
        return embeddings, False

    def search(self, question: str, top_k: int = 5) -> pd.DataFrame:
        if not question.strip():
            raise ValueError("Question must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        query_embedding = self.model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0].astype(np.float32, copy=False)
        scores = self.embeddings @ query_embedding
        result_count = min(top_k, len(scores))
        top_indices = np.argsort(-scores, kind="stable")[:result_count]
        return build_results(
            self.corpus,
            top_indices,
            scores[top_indices],
            method="dense",
        )