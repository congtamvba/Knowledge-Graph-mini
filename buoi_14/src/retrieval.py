from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from src.bm25_retriever import BM25Retriever
from src.corpus import load_corpus
from src.dense_retriever import DEFAULT_MODEL_NAME, DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import DEFAULT_RERANKER_MODEL, NeuralReranker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "cache"
DEFAULT_ENV_PATH = WORKSPACE_ROOT / ".env"
SUPPORTED_METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")
COMMON_RESULT_COLUMNS = [
    "rank",
    "chunk_id",
    "document_id",
    "text",
    "score",
    "citation",
    "retrieval_method",
]


class RetrievalPipeline:
    def __init__(
        self,
        corpus_path: Path = DEFAULT_CORPUS_PATH,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        dense_model: str = DEFAULT_MODEL_NAME,
        reranker_model: str = DEFAULT_RERANKER_MODEL,
        candidate_k: int = 20,
        rrf_k: int = 60,
    ) -> None:
        if candidate_k < 1:
            raise ValueError("candidate_k must be at least 1")
        self.corpus_path = corpus_path.resolve()
        self.cache_dir = cache_dir.resolve()
        self.dense_model = dense_model
        self.reranker_model = reranker_model
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k
        self.corpus = load_corpus(self.corpus_path)
        self._bm25: BM25Retriever | None = None
        self._dense: DenseRetriever | None = None
        self._hybrid: HybridRetriever | None = None
        self._reranker: NeuralReranker | None = None

    @property
    def bm25(self) -> BM25Retriever:
        if self._bm25 is None:
            self._bm25 = BM25Retriever(self.corpus)
        return self._bm25

    @property
    def dense(self) -> DenseRetriever:
        if self._dense is None:
            self._dense = DenseRetriever(
                self.corpus,
                corpus_path=self.corpus_path,
                cache_dir=self.cache_dir,
                model_name=self.dense_model,
            )
        return self._dense

    @property
    def hybrid(self) -> HybridRetriever:
        if self._hybrid is None:
            self._hybrid = HybridRetriever(self.bm25, self.dense, rrf_k=self.rrf_k)
        return self._hybrid

    @property
    def reranker(self) -> NeuralReranker:
        if self._reranker is None:
            self._reranker = NeuralReranker(
                self.hybrid,
                model_name=self.reranker_model,
            )
        return self._reranker

    def retrieve(self, question: str, method: str, top_k: int = 5) -> pd.DataFrame:
        results, _ = self.retrieve_with_details(question, method, top_k)
        return results

    def retrieve_with_details(
        self,
        question: str,
        method: str,
        top_k: int = 5,
    ) -> tuple[pd.DataFrame, pd.DataFrame | None]:
        normalized_method = method.strip().lower()
        if normalized_method not in SUPPORTED_METHODS:
            raise ValueError(
                f"Unsupported method '{method}'. Choose from: {', '.join(SUPPORTED_METHODS)}"
            )
        if not question.strip():
            raise ValueError("Question must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        candidate_k = max(self.candidate_k, top_k)
        if normalized_method == "bm25":
            return self._normalize_baseline(self.bm25.search(question, top_k), "bm25"), None
        if normalized_method == "dense":
            return self._normalize_baseline(self.dense.search(question, top_k), "dense"), None
        if normalized_method == "hybrid":
            results = self.hybrid.search(question, top_k=top_k, candidate_k=candidate_k)
            return self._normalize_hybrid(results), None

        candidates, results = self.reranker.search(
            question,
            candidate_k=candidate_k,
            top_k=top_k,
        )
        before = self._normalize_hybrid(candidates.head(top_k))
        return self._normalize_rerank(results), before

    @staticmethod
    def _normalize_baseline(results: pd.DataFrame, method: str) -> pd.DataFrame:
        normalized = results.rename(columns={"retrieval_score": "score"}).copy()
        normalized["retrieval_method"] = method
        return normalized[COMMON_RESULT_COLUMNS]

    @staticmethod
    def _normalize_hybrid(results: pd.DataFrame) -> pd.DataFrame:
        normalized = results.rename(columns={"final_rank": "rank", "rrf_score": "score"}).copy()
        normalized["retrieval_method"] = "hybrid"
        normalized["rrf_score"] = normalized["score"]
        columns = COMMON_RESULT_COLUMNS + ["bm25_rank", "dense_rank", "rrf_score"]
        return normalized[columns]

    @staticmethod
    def _normalize_rerank(results: pd.DataFrame) -> pd.DataFrame:
        normalized = results.rename(columns={"final_rank": "rank", "rerank_score": "score"}).copy()
        normalized["retrieval_method"] = "hybrid_rerank"
        normalized["rerank_score"] = normalized["score"]
        columns = COMMON_RESULT_COLUMNS + ["hybrid_rank", "hybrid_score", "rerank_score"]
        return normalized[columns]


@lru_cache(maxsize=1)
def default_pipeline() -> RetrievalPipeline:
    return RetrievalPipeline()


def retrieve(question: str, method: str, top_k: int = 5) -> pd.DataFrame:
    return default_pipeline().retrieve(question, method, top_k)


def retrieve_with_details(
    question: str,
    method: str,
    top_k: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    return default_pipeline().retrieve_with_details(question, method, top_k)


def graph_hints(
    results: pd.DataFrame,
    env_path: Path = DEFAULT_ENV_PATH,
) -> tuple[list[dict[str, object]], str]:
    required_columns = {"document_id", "chunk_id"}
    if not required_columns <= set(results.columns):
        raise ValueError("Results must contain document_id and chunk_id for graph hints")
    if results.empty:
        return [], "No retrieved chunks"

    load_dotenv(env_path.resolve())
    required_variables = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE")
    missing = [name for name in required_variables if not os.getenv(name)]
    if missing:
        return [], f"Neo4j chưa sẵn sàng: thiếu {', '.join(missing)}"

    document_ids = results["document_id"].astype(str).drop_duplicates().tolist()
    chunk_ids = results["chunk_id"].astype(str).drop_duplicates().tolist()
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        driver.verify_connectivity()
        records, _, _ = driver.execute_query(
            """
            MATCH (v:VanBan {lab_session: $lab_session})
            WHERE v.id IN $document_ids
            OPTIONAL MATCH (v)-[outgoing]->(target:VanBan {lab_session: $lab_session})
            WITH v, collect(DISTINCT CASE WHEN outgoing IS NULL THEN null ELSE {
                direction: 'OUT', type: type(outgoing), other_document_id: target.id
            } END) AS outgoing_relations
            OPTIONAL MATCH (source:VanBan {lab_session: $lab_session})-[incoming]->(v)
            WITH v, outgoing_relations,
                 collect(DISTINCT CASE WHEN incoming IS NULL THEN null ELSE {
                     direction: 'IN', type: type(incoming), other_document_id: source.id
                 } END) AS incoming_relations
            RETURN v.id AS document_id, outgoing_relations + incoming_relations AS relations
            ORDER BY document_id
            """,
            lab_session="buoi_14",
            document_ids=document_ids,
            database_=os.environ["NEO4J_DATABASE"],
        )
        relations_by_document = {
            record["document_id"]: [relation for relation in record["relations"] if relation]
            for record in records
        }
        hints = [
            {
                "document_id": row.document_id,
                "chunk_id": row.chunk_id,
                "relations": relations_by_document.get(row.document_id, []),
            }
            for row in results[["document_id", "chunk_id"]].itertuples(index=False)
        ]
        return hints, "Neo4j ready"
    except (ServiceUnavailable, Neo4jError, OSError) as error:
        return [], f"Neo4j chưa sẵn sàng: {type(error).__name__}: {error}"
    finally:
        driver.close()