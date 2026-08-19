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
from src.reranker import DEFAULT_RERANKER_MODEL, NeuralReranker


DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "data" / "eval" / "questions.csv"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "cache"
DEFAULT_COMPARISON_PATH = PROJECT_ROOT / "outputs" / "retrieval_comparison.csv"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "outputs" / "evaluation_report.md"
METHODS = ["bm25", "dense", "hybrid", "hybrid_rerank"]
QUERY_TYPES = ["EXACT_KEYWORD", "SEMANTIC", "MIXED"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate four retrieval configurations.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMPARISON_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--dense-model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--reranker-model", default=DEFAULT_RERANKER_MODEL)
    return parser.parse_args()


def load_questions(path: Path, corpus: pd.DataFrame) -> pd.DataFrame:
    required = {"question_id", "question", "expected_chunk_id", "query_type", "note"}
    questions = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing = required - set(questions.columns)
    if missing:
        raise ValueError(f"Questions file is missing columns: {sorted(missing)}")
    if questions.empty or questions["question_id"].duplicated().any():
        raise ValueError("Questions must be non-empty and question_id must be unique")
    invalid_types = set(questions["query_type"]) - set(QUERY_TYPES)
    if invalid_types:
        raise ValueError(f"Unsupported query types: {sorted(invalid_types)}")
    corpus_ids = set(corpus["chunk_id"])
    missing_gold = set(questions["expected_chunk_id"]) - corpus_ids
    if missing_gold:
        raise ValueError(f"Gold chunks do not exist in corpus: {sorted(missing_gold)}")
    return questions


def score_ranking(expected_chunk_id: str, retrieved_ids: list[str]) -> dict[str, object]:
    gold_rank = retrieved_ids.index(expected_chunk_id) + 1 if expected_chunk_id in retrieved_ids else None
    return {
        "gold_rank": gold_rank,
        "hit_at_1": int(gold_rank is not None and gold_rank <= 1),
        "hit_at_3": int(gold_rank is not None and gold_rank <= 3),
        "hit_at_5": int(gold_rank is not None and gold_rank <= 5),
        "reciprocal_rank": 1.0 / gold_rank if gold_rank else 0.0,
    }


def result_ids(results: pd.DataFrame) -> list[str]:
    return results["chunk_id"].astype(str).tolist()


def evaluation_record(
    question: pd.Series,
    method: str,
    retrieved_ids: list[str],
    error: str = "",
) -> dict[str, object]:
    scores = score_ranking(question["expected_chunk_id"], retrieved_ids) if not error else {
        "gold_rank": None,
        "hit_at_1": 0,
        "hit_at_3": 0,
        "hit_at_5": 0,
        "reciprocal_rank": 0.0,
    }
    padded = (retrieved_ids + [""] * 5)[:5]
    return {
        "question_id": question["question_id"],
        "question": question["question"],
        "query_type": question["query_type"],
        "expected_chunk_id": question["expected_chunk_id"],
        "method": method,
        **scores,
        "top_1_chunk_id": padded[0],
        "top_2_chunk_id": padded[1],
        "top_3_chunk_id": padded[2],
        "top_4_chunk_id": padded[3],
        "top_5_chunk_id": padded[4],
        "error": error,
    }


def evaluate(
    questions: pd.DataFrame,
    bm25: BM25Retriever,
    dense: DenseRetriever,
    hybrid: HybridRetriever,
    reranker: NeuralReranker,
    candidate_k: int,
    top_k: int,
) -> pd.DataFrame:
    records = []
    for question in questions.to_dict(orient="records"):
        question_series = pd.Series(question)
        query = question["question"]
        print(f"Evaluating {question['question_id']}: {query}")

        outputs: dict[str, list[str]] = {}
        errors: dict[str, str] = {}
        try:
            outputs["bm25"] = result_ids(bm25.search(query, top_k=top_k))
        except Exception as error:
            errors["bm25"] = f"{type(error).__name__}: {error}"
        try:
            outputs["dense"] = result_ids(dense.search(query, top_k=top_k))
        except Exception as error:
            errors["dense"] = f"{type(error).__name__}: {error}"

        hybrid_candidates = None
        try:
            hybrid_candidates = hybrid.search(query, top_k=candidate_k, candidate_k=candidate_k)
            outputs["hybrid"] = result_ids(hybrid_candidates.head(top_k))
        except Exception as error:
            errors["hybrid"] = f"{type(error).__name__}: {error}"
        try:
            if hybrid_candidates is None:
                raise RuntimeError("Hybrid candidates unavailable")
            outputs["hybrid_rerank"] = result_ids(
                reranker.rerank(query, hybrid_candidates, top_k=top_k)
            )
        except Exception as error:
            errors["hybrid_rerank"] = f"{type(error).__name__}: {error}"

        for method in METHODS:
            records.append(
                evaluation_record(
                    question_series,
                    method,
                    outputs.get(method, []),
                    errors.get(method, ""),
                )
            )
    return pd.DataFrame.from_records(records)


def metric_table(results: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    return (
        results.groupby(group_columns, sort=False)
        .agg(
            questions=("question_id", "count"),
            errors=("error", lambda values: int(values.ne("").sum())),
            hit_at_1=("hit_at_1", "mean"),
            hit_at_3=("hit_at_3", "mean"),
            hit_at_5=("hit_at_5", "mean"),
            mrr=("reciprocal_rank", "mean"),
        )
        .reset_index()
    )


def markdown_metrics(table: pd.DataFrame, label_column: str) -> str:
    lines = [
        f"| {label_column} | Questions | Errors | Hit@1 | Hit@3 | Hit@5 | MRR |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in table.itertuples(index=False):
        label = getattr(row, label_column)
        lines.append(
            f"| `{label}` | {row.questions} | {row.errors} | {row.hit_at_1:.3f} | "
            f"{row.hit_at_3:.3f} | {row.hit_at_5:.3f} | {row.mrr:.3f} |"
        )
    return "\n".join(lines)


def build_report(results: pd.DataFrame, candidate_k: int, top_k: int) -> str:
    overall = metric_table(results, ["method"])
    by_type = metric_table(results, ["query_type", "method"])
    error_count = int(results["error"].ne("").sum())

    type_sections = []
    best_by_type = []
    for query_type in QUERY_TYPES:
        subset = by_type[by_type["query_type"] == query_type].copy()
        type_sections.append(f"### {query_type}\n\n{markdown_metrics(subset, 'method')}")
        best = subset.sort_values(["hit_at_5", "mrr"], ascending=False, kind="stable").iloc[0]
        best_by_type.append(
            f"- `{query_type}`: `{best['method']}` cao nhất theo Hit@5 rồi MRR "
            f"({best['hit_at_5']:.3f}, {best['mrr']:.3f})."
        )

    metric_lookup = overall.set_index("method")
    hybrid_hit5 = float(metric_lookup.loc["hybrid", "hit_at_5"])
    baseline_hit5 = max(
        float(metric_lookup.loc["bm25", "hit_at_5"]),
        float(metric_lookup.loc["dense", "hit_at_5"]),
    )
    hybrid_assessment = (
        "Hybrid cải thiện Hit@5 so với baseline tốt nhất."
        if hybrid_hit5 > baseline_hit5
        else "Hybrid không cải thiện Hit@5 so với baseline tốt nhất."
        if hybrid_hit5 == baseline_hit5
        else "Hybrid làm giảm Hit@5 so với baseline tốt nhất."
    )

    hybrid_rows = results[results["method"] == "hybrid"].set_index("question_id")
    rerank_rows = results[results["method"] == "hybrid_rerank"].set_index("question_id")
    changed = []
    for question_id in hybrid_rows.index:
        hybrid_order = hybrid_rows.loc[question_id, [f"top_{index}_chunk_id" for index in range(1, 6)]].tolist()
        rerank_order = rerank_rows.loc[question_id, [f"top_{index}_chunk_id" for index in range(1, 6)]].tolist()
        if hybrid_order != rerank_order:
            changed.append(question_id)

    failures = results[(results["hit_at_5"] == 0) | results["error"].ne("")]
    if failures.empty:
        failure_text = "Không có failure case tại Hit@5 trong bộ câu hỏi này."
    else:
        failure_lines = []
        for row in failures.itertuples(index=False):
            detail = row.error or f"gold `{row.expected_chunk_id}` không có trong top 5"
            failure_lines.append(f"- `{row.question_id}` / `{row.method}`: {detail}.")
        failure_text = "\n".join(failure_lines)

    return f"""# Evaluation Report

## Protocol

- Số câu hỏi: **{results['question_id'].nunique()}**.
- Nhóm: 3 `EXACT_KEYWORD`, 3 `SEMANTIC`, 3 `MIXED`.
- Corpus dùng chung: `data/processed/chunks_normalized.csv`.
- Gold được khóa từ nội dung điều khoản trước khi chạy retrieval.
- Cùng `top_k={top_k}` cho bốn cấu hình; Hybrid lấy `candidate_k={candidate_k}` cho RRF và reranking.
- Reranker chỉ chấm {candidate_k} Hybrid candidates, không chấm toàn corpus.
- Lỗi không bị bỏ qua; tổng lỗi ghi nhận: **{error_count}**.

## Overall Metrics

{markdown_metrics(overall, 'method')}

## Metrics By Query Type

{chr(10).join(type_sections)}

## Nhận xét theo nhóm

{chr(10).join(best_by_type)}

## Hybrid có giúp không?

{hybrid_assessment} Kết luận này chỉ áp dụng cho bộ gold nhỏ hiện tại; xem thêm MRR và failure cases để tránh kết luận từ một metric.

## Reranking có đổi thứ hạng không?

Reranking đổi thứ tự top 5 ở **{len(changed)}/{results['question_id'].nunique()}** câu hỏi: {', '.join(f'`{item}`' for item in changed) if changed else 'không có'}.

## Failure Cases

{failure_text}

## Giới hạn

- Mỗi câu chỉ có một `expected_chunk_id`; các chunk khác có thể vẫn liên quan nhưng bị tính là miss.
- Bộ 9 câu nhỏ, được chọn từ các điều khoản có bằng chứng rõ; chưa đại diện toàn bộ miền pháp lý.
- Hit@k và MRR đo khả năng tìm đúng chunk đã gán, không đo độ đúng của câu trả lời sinh bởi LLM.
- Không thay gold sau khi xem kết quả. Muốn kết luận mạnh hơn cần nhiều người gán nhãn và nhiều relevant chunks cho mỗi câu.
"""


def main() -> None:
    args = parse_args()
    if args.top_k != 5:
        raise ValueError("This evaluation protocol requires --top-k 5")
    if args.candidate_k < args.top_k:
        raise ValueError("--candidate-k must be at least --top-k")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    corpus_path = args.corpus.resolve()
    corpus = load_corpus(corpus_path)
    questions = load_questions(args.questions.resolve(), corpus)
    bm25 = BM25Retriever(corpus)
    dense = DenseRetriever(
        corpus,
        corpus_path=corpus_path,
        cache_dir=args.cache_dir.resolve(),
        model_name=args.dense_model,
    )
    hybrid = HybridRetriever(bm25, dense, rrf_k=args.rrf_k)
    reranker = NeuralReranker(hybrid, model_name=args.reranker_model)

    results = evaluate(
        questions,
        bm25,
        dense,
        hybrid,
        reranker,
        candidate_k=args.candidate_k,
        top_k=args.top_k,
    )
    output_path = args.output.resolve()
    report_path = args.report.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False, encoding="utf-8")
    report_path.write_text(build_report(results, args.candidate_k, args.top_k), encoding="utf-8")

    print(f"Comparison: {output_path}")
    print(f"Report: {report_path}")
    print("\nEVALUATION SUMMARY")
    print(metric_table(results, ["method"]).to_string(index=False))


if __name__ == "__main__":
    main()