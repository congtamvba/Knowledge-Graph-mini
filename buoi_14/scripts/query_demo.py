from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval import SUPPORTED_METHODS, graph_hints, retrieve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified retrieval demo with graph hints.")
    parser.add_argument("--query", required=True, help="Question to retrieve evidence for")
    parser.add_argument("--method", choices=SUPPORTED_METHODS, default="hybrid_rerank")
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def optional_scores(row) -> str:
    values = []
    for name in (
        "bm25_rank",
        "dense_rank",
        "rrf_score",
        "hybrid_rank",
        "hybrid_score",
        "rerank_score",
    ):
        if hasattr(row, name):
            value = getattr(row, name)
            values.append(f"{name}={value}")
    return ", ".join(values)


def print_results(results) -> None:
    print("\nRETRIEVAL RESULTS")
    print("Rank | Score | Method | Chunk | Document")
    print("-" * 100)
    for row in results.itertuples(index=False):
        print(
            f"{row.rank} | {row.score:.6f} | {row.retrieval_method} | "
            f"{row.chunk_id} | {row.document_id}"
        )
        details = optional_scores(row)
        if details:
            print(f"  {details}")
        print(f"  Citation: {row.citation}")
        print(f"  Text: {row.text[:360].replace(chr(10), ' ')}")


def print_graph_hints(hints: list[dict[str, object]], status: str) -> None:
    print("\nGRAPH HINTS")
    print(f"Status: {status}")
    for hint in hints:
        print(f"- document_id={hint['document_id']}; chunk_id={hint['chunk_id']}")
        relations = hint["relations"]
        if not relations:
            print("  Direct VanBan relations: none")
            continue
        for relation in relations:
            arrow = "->" if relation["direction"] == "OUT" else "<-"
            print(
                f"  {arrow} {relation['type']} {relation['other_document_id']}"
            )


def main() -> None:
    args = parse_args()
    if args.top_k < 1:
        raise ValueError("--top-k must be at least 1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    results = retrieve(args.query, args.method, args.top_k)
    print(f"Query: {args.query}")
    print(f"Method: {args.method}; Top-k: {args.top_k}")
    print_results(results)
    hints, status = graph_hints(results)
    print_graph_hints(hints, status)


if __name__ == "__main__":
    main()