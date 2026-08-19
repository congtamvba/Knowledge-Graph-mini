from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bm25_retriever import BM25Retriever
from src.corpus import load_corpus
from src.dense_retriever import DEFAULT_MODEL_NAME, DenseRetriever
from src.hybrid_retriever import HybridRetriever


DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "cache"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hybrid Search with RRF fusion.")
    parser.add_argument("--query", required=True, help="Question to retrieve evidence for")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    return parser.parse_args()


def display_rank(value: object) -> str:
    return "-" if pd.isna(value) else str(int(value))


def print_results(results) -> None:
    print("\nHYBRID RESULTS")
    print("Rank | Chunk | BM25 rank | Dense rank | RRF | Citation")
    print("-" * 120)
    for row in results.itertuples(index=False):
        print(
            f"{row.final_rank} | {row.chunk_id} | {display_rank(row.bm25_rank)} | "
            f"{display_rank(row.dense_rank)} | {row.rrf_score:.8f} | {row.citation}"
        )
        print(f"  {row.text[:240].replace(chr(10), ' ')}")


def main() -> None:
    args = parse_args()
    if args.top_k < 1 or args.candidate_k < 1:
        raise ValueError("--top-k and --candidate-k must be at least 1")
    if args.top_k > args.candidate_k * 2:
        raise ValueError("--top-k cannot exceed the maximum fused candidate count")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    corpus_path = args.corpus.resolve()
    corpus = load_corpus(corpus_path)
    bm25 = BM25Retriever(corpus)
    dense = DenseRetriever(
        corpus,
        corpus_path=corpus_path,
        cache_dir=args.cache_dir.resolve(),
        model_name=args.model,
    )
    hybrid = HybridRetriever(bm25, dense, rrf_k=args.rrf_k)
    results = hybrid.search(args.query, top_k=args.top_k, candidate_k=args.candidate_k)

    print(f"Query: {args.query}")
    print(f"Candidate k per retriever: {args.candidate_k}; RRF k: {args.rrf_k}")
    print_results(results)


if __name__ == "__main__":
    main()