from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bm25_retriever import BM25Retriever, tokenize
from src.corpus import RESULT_COLUMNS
from src.hybrid_retriever import HYBRID_RESULT_COLUMNS, HybridRetriever
from src.reranker import RERANK_RESULT_COLUMNS, NeuralReranker
from src.retrieval import COMMON_RESULT_COLUMNS, RetrievalPipeline, graph_hints

SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from compare_retrieval import score_ranking
from load_mini_kg import (
    EXPECTED_CHUNK_COLUMNS,
    EXPECTED_CONTENT_COLUMNS,
    EXPECTED_METADATA_COLUMNS,
    EXPECTED_RELATIONSHIP_COLUMNS,
    planned_counts,
    prepare_graph_data,
    read_csv,
    relationship_query,
)


class TokenizerTests(unittest.TestCase):
    def test_preserves_vietnamese_article_and_document_number(self) -> None:
        tokens = tokenize("Điều 5 của 01/2014/TT-NHNN quy định bảo quản tiền mặt")

        self.assertIn("điều", tokens)
        self.assertIn("5", tokens)
        self.assertIn("01/2014/tt-nhnn", tokens)
        self.assertIn("bảo", tokens)


class BM25RetrieverTests(unittest.TestCase):
    def test_returns_shared_result_schema_and_real_citation_fields(self) -> None:
        corpus = pd.DataFrame(
            [
                {
                    "chunk_id": "doc-1-chunk-0001",
                    "document_id": "doc-1",
                    "text": "Điều 5. Tỷ lệ an toàn vốn của ngân hàng.",
                    "source_file": "content.csv",
                    "title": "Thông tư về an toàn vốn",
                    "document_number": "41/2016/TT-NHNN",
                    "document_type": "Thông tư",
                    "article": "Điều 5. Tỷ lệ an toàn vốn",
                    "effective_date": "",
                    "status": "Còn hiệu lực",
                },
                {
                    "chunk_id": "doc-2-chunk-0001",
                    "document_id": "doc-2",
                    "text": "Quy định về bảo quản chìa khóa kho tiền.",
                    "source_file": "content.csv",
                    "title": "Thông tư về kho tiền",
                    "document_number": "01/2014/TT-NHNN",
                    "document_type": "Thông tư",
                    "article": "Điều 28. Bảo quản chìa khóa",
                    "effective_date": "",
                    "status": "Còn hiệu lực",
                },
            ]
        )

        results = BM25Retriever(corpus).search("41/2016/TT-NHNN an toàn vốn", top_k=1)

        self.assertEqual(RESULT_COLUMNS, results.columns.tolist())
        self.assertEqual("doc-1-chunk-0001", results.iloc[0]["chunk_id"])
        self.assertEqual("bm25", results.iloc[0]["retrieval_method"])
        self.assertIn("41/2016/TT-NHNN", results.iloc[0]["citation"])
        self.assertIn("Điều 5", results.iloc[0]["citation"])


class StubRetriever:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self.results = pd.DataFrame(results, columns=RESULT_COLUMNS)

    def search(self, question: str, top_k: int = 5) -> pd.DataFrame:
        return self.results.head(top_k).copy()


def retrieval_result(rank: int, chunk_id: str, method: str) -> dict[str, object]:
    return {
        "rank": rank,
        "chunk_id": chunk_id,
        "document_id": f"doc-{chunk_id}",
        "text": f"Text for {chunk_id}",
        "retrieval_score": 1.0 / rank,
        "retrieval_method": method,
        "citation": f"[Citation {chunk_id}]",
    }


class HybridRetrieverTests(unittest.TestCase):
    def test_rrf_keeps_single_source_candidates_and_removes_duplicates(self) -> None:
        bm25 = StubRetriever(
            [retrieval_result(1, "shared", "bm25"), retrieval_result(2, "bm25-only", "bm25")]
        )
        dense = StubRetriever(
            [retrieval_result(1, "dense-only", "dense"), retrieval_result(2, "shared", "dense")]
        )

        results = HybridRetriever(bm25, dense, rrf_k=60).search(
            "question", top_k=3, candidate_k=2
        )

        self.assertEqual(HYBRID_RESULT_COLUMNS, results.columns.tolist())
        self.assertTrue(results["chunk_id"].is_unique)
        self.assertEqual({"shared", "bm25-only", "dense-only"}, set(results["chunk_id"]))
        self.assertEqual("shared", results.iloc[0]["chunk_id"])
        self.assertEqual(1, results.iloc[0]["bm25_rank"])
        self.assertEqual(2, results.iloc[0]["dense_rank"])
        self.assertAlmostEqual(1 / 61 + 1 / 62, results.iloc[0]["rrf_score"])

        bm25_only = results.loc[results["chunk_id"] == "bm25-only"].iloc[0]
        dense_only = results.loc[results["chunk_id"] == "dense-only"].iloc[0]
        self.assertTrue(pd.isna(bm25_only["dense_rank"]))
        self.assertTrue(pd.isna(dense_only["bm25_rank"]))


class StubHybridRetriever:
    def __init__(self, candidates: pd.DataFrame) -> None:
        self.candidates = candidates
        self.calls: list[tuple[int, int]] = []

    def search(self, question: str, top_k: int = 5, candidate_k: int = 20) -> pd.DataFrame:
        self.calls.append((top_k, candidate_k))
        return self.candidates.head(top_k).copy()


class StubPairScorer:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.pair_count = 0

    def predict(
        self,
        sentences: list[list[str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> np.ndarray:
        self.pair_count = len(sentences)
        return np.asarray(self.scores[: len(sentences)])


class NeuralRerankerTests(unittest.TestCase):
    def test_reranks_only_hybrid_candidates_and_preserves_citation(self) -> None:
        candidates = pd.DataFrame(
            [
                {
                    "final_rank": 1,
                    "chunk_id": "chunk-a",
                    "document_id": "doc-a",
                    "bm25_rank": 1,
                    "dense_rank": 2,
                    "rrf_score": 0.03,
                    "text": "Less relevant text",
                    "citation": "[Citation A]",
                },
                {
                    "final_rank": 2,
                    "chunk_id": "chunk-b",
                    "document_id": "doc-b",
                    "bm25_rank": 3,
                    "dense_rank": 1,
                    "rrf_score": 0.02,
                    "text": "More relevant text",
                    "citation": "[Citation B]",
                },
                {
                    "final_rank": 3,
                    "chunk_id": "chunk-c",
                    "document_id": "doc-c",
                    "bm25_rank": pd.NA,
                    "dense_rank": 3,
                    "rrf_score": 0.01,
                    "text": "Third text",
                    "citation": "[Citation C]",
                },
            ],
            columns=HYBRID_RESULT_COLUMNS,
        )
        hybrid = StubHybridRetriever(candidates)
        scorer = StubPairScorer([0.1, 0.9, -0.5])
        reranker = NeuralReranker(hybrid, model=scorer)

        before, after = reranker.search("question", candidate_k=3, top_k=2)

        self.assertEqual([(3, 3)], hybrid.calls)
        self.assertEqual(3, scorer.pair_count)
        self.assertEqual(3, len(before))
        self.assertEqual(RERANK_RESULT_COLUMNS, after.columns.tolist())
        self.assertEqual(["chunk-b", "chunk-a"], after["chunk_id"].tolist())
        self.assertEqual([2, 1], after["hybrid_rank"].tolist())
        self.assertEqual("[Citation B]", after.iloc[0]["citation"])
        self.assertEqual(0.9, after.iloc[0]["rerank_score"])


class EvaluationMetricTests(unittest.TestCase):
    def test_score_ranking_computes_hits_and_mrr(self) -> None:
        scores = score_ranking("gold", ["first", "gold", "third"])

        self.assertEqual(2, scores["gold_rank"])
        self.assertEqual(0, scores["hit_at_1"])
        self.assertEqual(1, scores["hit_at_3"])
        self.assertEqual(1, scores["hit_at_5"])
        self.assertEqual(0.5, scores["reciprocal_rank"])

    def test_score_ranking_counts_missing_gold_as_failure(self) -> None:
        scores = score_ranking("gold", ["first", "second"])

        self.assertIsNone(scores["gold_rank"])
        self.assertEqual(0, scores["hit_at_5"])
        self.assertEqual(0.0, scores["reciprocal_rank"])


class KnowledgeGraphDataTests(unittest.TestCase):
    def test_actual_sources_produce_expected_graph_plan(self) -> None:
        metadata = read_csv(
            PROJECT_ROOT.parent / "kb+hops" / "metadata.csv",
            EXPECTED_METADATA_COLUMNS,
        )
        content = read_csv(
            PROJECT_ROOT.parent / "kb+hops" / "content.csv",
            EXPECTED_CONTENT_COLUMNS,
        )
        relationships = read_csv(
            PROJECT_ROOT.parent / "kb+hops" / "relationships.csv",
            EXPECTED_RELATIONSHIP_COLUMNS,
        )
        chunks = read_csv(
            PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv",
            EXPECTED_CHUNK_COLUMNS,
        )

        counts = planned_counts(prepare_graph_data(metadata, content, relationships, chunks))

        self.assertEqual(15, counts["VanBan"])
        self.assertEqual(1242, counts["DieuKhoan"])
        self.assertEqual(1242, counts["CONTAINS"])
        self.assertEqual(1227, counts["NEXT"])
        self.assertEqual(4, counts["CAN_CU"])
        self.assertEqual(1, counts["THAY_THE"])

    def test_dynamic_relationship_type_is_whitelisted(self) -> None:
        self.assertIn("[r:CAN_CU", relationship_query("CAN_CU"))
        with self.assertRaises(ValueError):
            relationship_query("UNSAFE_TYPE")


class UnifiedRetrievalTests(unittest.TestCase):
    def test_normalizes_baseline_hybrid_and_rerank_schemas(self) -> None:
        baseline = pd.DataFrame(
            [retrieval_result(1, "baseline", "bm25")],
            columns=RESULT_COLUMNS,
        )
        hybrid = pd.DataFrame(
            [
                {
                    "final_rank": 1,
                    "chunk_id": "hybrid",
                    "document_id": "doc-hybrid",
                    "bm25_rank": 2,
                    "dense_rank": 1,
                    "rrf_score": 0.03,
                    "text": "Hybrid text",
                    "citation": "[Hybrid citation]",
                }
            ],
            columns=HYBRID_RESULT_COLUMNS,
        )
        reranked = pd.DataFrame(
            [
                {
                    "final_rank": 1,
                    "chunk_id": "reranked",
                    "document_id": "doc-reranked",
                    "hybrid_rank": 3,
                    "hybrid_score": 0.02,
                    "rerank_score": 4.2,
                    "text": "Reranked text",
                    "citation": "[Reranked citation]",
                }
            ],
            columns=RERANK_RESULT_COLUMNS,
        )

        normalized_bm25 = RetrievalPipeline._normalize_baseline(baseline, "bm25")
        normalized_hybrid = RetrievalPipeline._normalize_hybrid(hybrid)
        normalized_rerank = RetrievalPipeline._normalize_rerank(reranked)

        self.assertEqual(COMMON_RESULT_COLUMNS, normalized_bm25.columns.tolist())
        self.assertTrue(set(COMMON_RESULT_COLUMNS) <= set(normalized_hybrid.columns))
        self.assertTrue(set(COMMON_RESULT_COLUMNS) <= set(normalized_rerank.columns))
        self.assertEqual(0.03, normalized_hybrid.iloc[0]["score"])
        self.assertEqual(4.2, normalized_rerank.iloc[0]["score"])
        self.assertEqual("hybrid_rerank", normalized_rerank.iloc[0]["retrieval_method"])

    def test_graph_hints_degrades_when_neo4j_config_is_missing(self) -> None:
        results = pd.DataFrame(
            [{"document_id": "doc-1", "chunk_id": "chunk-1"}]
        )

        with patch.dict("os.environ", {}, clear=True):
            hints, status = graph_hints(results, env_path=PROJECT_ROOT / "missing.env")

        self.assertEqual([], hints)
        self.assertIn("Neo4j chưa sẵn sàng", status)


if __name__ == "__main__":
    unittest.main()