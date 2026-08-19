from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval import RetrievalPipeline, graph_hints


METHOD_LABELS = {
    "BM25": "bm25",
    "Dense": "dense",
    "Hybrid": "hybrid",
    "Hybrid + Rerank": "hybrid_rerank",
}


st.set_page_config(
    page_title="RAG Hybrid Search — Buổi 14",
    page_icon=":material/account_tree:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');

    :root {
        --ink: #17211d;
        --muted: #5d6762;
        --paper: #f6f7f3;
        --line: #d8ddd7;
        --green: #1f6048;
        --green-soft: #e7f0eb;
        --gold: #a66b0a;
        --gold-soft: #f6ecd9;
    }

    .stApp {
        color: var(--ink);
        background-color: var(--paper);
        background-image:
            linear-gradient(rgba(31, 96, 72, 0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(31, 96, 72, 0.025) 1px, transparent 1px);
        background-size: 28px 28px;
        font-family: "IBM Plex Sans", sans-serif;
    }

    h1, h2, h3 {
        font-family: "Source Serif 4", serif !important;
        letter-spacing: 0 !important;
        color: var(--ink) !important;
    }

    h1 { font-size: 2.35rem !important; }
    h2 { font-size: 1.45rem !important; }
    h3 { font-size: 1.08rem !important; }

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { right: 1rem; }

    .app-kicker {
        color: var(--green);
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .app-subtitle {
        color: var(--muted);
        max-width: 760px;
        margin: -0.45rem 0 1.5rem;
        line-height: 1.6;
    }

    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 1.15rem 1.25rem 0.4rem;
        box-shadow: 0 8px 24px rgba(23, 33, 29, 0.05);
    }

    .result-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem 1.1rem;
        color: var(--muted);
        font-size: 0.82rem;
        margin-bottom: 0.65rem;
    }

    .result-citation {
        border-left: 3px solid var(--gold);
        background: var(--gold-soft);
        padding: 0.65rem 0.8rem;
        color: #62410b;
        font-size: 0.9rem;
        line-height: 1.45;
        margin: 0.7rem 0;
    }

    .result-text {
        white-space: pre-wrap;
        line-height: 1.65;
        color: #26322d;
    }

    .score-line {
        color: var(--green);
        font-size: 0.84rem;
        font-weight: 600;
        margin-top: 0.4rem;
    }

    .graph-line {
        padding: 0.65rem 0;
        border-bottom: 1px solid var(--line);
        line-height: 1.55;
    }

    .graph-relation {
        color: var(--green);
        font-weight: 500;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line) !important;
        border-radius: 6px !important;
        background: rgba(255, 255, 255, 0.82);
    }

    .stButton > button, [data-testid="stFormSubmitButton"] button {
        border-radius: 4px;
        font-weight: 600;
        min-height: 2.65rem;
    }

    [data-testid="stMetric"] {
        background: var(--green-soft);
        border-left: 3px solid var(--green);
        padding: 0.7rem 0.85rem;
    }

    @media (max-width: 640px) {
        .block-container { padding: 1.1rem 0.8rem 3rem; }
        h1 { font-size: 1.85rem !important; }
        .result-meta { display: grid; grid-template-columns: 1fr; gap: 0.2rem; }
        [data-testid="stForm"] { padding: 0.9rem 0.8rem 0.25rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_pipeline() -> RetrievalPipeline:
    return RetrievalPipeline()


def score_details(row: pd.Series) -> str:
    details = []
    labels = {
        "bm25_rank": "BM25 rank",
        "dense_rank": "Dense rank",
        "rrf_score": "RRF",
        "hybrid_rank": "Hybrid rank",
        "hybrid_score": "Hybrid score",
        "rerank_score": "Rerank score",
    }
    for column, label in labels.items():
        if column not in row.index or pd.isna(row[column]):
            continue
        value = row[column]
        formatted = str(int(value)) if column.endswith("rank") else f"{float(value):.6f}"
        details.append(f"{label}: {formatted}")
    return " · ".join(details)


def ranking_table(results: pd.DataFrame, before: bool = False) -> pd.DataFrame:
    score_column = "rrf_score" if before else "rerank_score"
    rank_column = "rank"
    table = results[[rank_column, "chunk_id", score_column]].copy()
    table.columns = ["Rank", "Chunk", "Score"]
    table["Score"] = table["Score"].map(lambda value: f"{float(value):.6f}")
    return table


def render_results(results: pd.DataFrame) -> None:
    st.subheader("Kết quả")
    st.caption(f"{len(results)} passages · xếp theo {results.iloc[0]['retrieval_method']}")
    for _, row in results.iterrows():
        chunk_id = html.escape(str(row["chunk_id"]))
        document_id = html.escape(str(row["document_id"]))
        retrieval_method = html.escape(str(row["retrieval_method"]))
        citation = html.escape(str(row["citation"]))
        text = html.escape(str(row["text"]))
        with st.container(border=True):
            st.markdown(f"### #{int(row['rank'])} · {chunk_id}")
            st.markdown(
                f"""
                <div class="result-meta">
                    <span><strong>Document</strong> {document_id}</span>
                    <span><strong>Method</strong> {retrieval_method}</span>
                    <span><strong>Score</strong> {float(row['score']):.6f}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            details = score_details(row)
            if details:
                st.markdown(f'<div class="score-line">{details}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="result-citation"><strong>Citation</strong><br>{citation}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="result-text">{text}</div>', unsafe_allow_html=True)


def render_before_after(before: pd.DataFrame, results: pd.DataFrame) -> None:
    st.subheader("Before / After Rerank")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### BEFORE RERANK")
        st.dataframe(
            ranking_table(before, before=True),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.markdown("#### AFTER RERANK")
        st.dataframe(
            ranking_table(results),
            hide_index=True,
            use_container_width=True,
        )


def render_graph_hints(hints: list[dict[str, object]], status: str) -> None:
    st.subheader("Graph hints")
    if status == "Neo4j ready":
        st.success(status, icon=":material/check_circle:")
    else:
        st.warning(status, icon=":material/database_off:")
    for hint in hints:
        document_id = html.escape(str(hint["document_id"]))
        chunk_id = html.escape(str(hint["chunk_id"]))
        relations = hint["relations"]
        relation_text = "Không có quan hệ VanBan trực tiếp"
        if relations:
            parts = []
            for relation in relations:
                arrow = "→" if relation["direction"] == "OUT" else "←"
                parts.append(
                    f"{arrow} {html.escape(str(relation['type']))} "
                    f"{html.escape(str(relation['other_document_id']))}"
                )
            relation_text = " · ".join(parts)
        st.markdown(
            f"""
            <div class="graph-line">
                <strong>{document_id}</strong> → <code>{chunk_id}</code><br>
                <span class="graph-relation">{relation_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown('<div class="app-kicker">Retrieval workbench</div>', unsafe_allow_html=True)
st.title("RAG Hybrid Search — Buổi 14")
st.markdown(
    '<div class="app-subtitle">So sánh lexical match, semantic retrieval, RRF fusion và neural reranking trên cùng corpus quy định.</div>',
    unsafe_allow_html=True,
)

with st.form("search_form", border=True):
    question = st.text_area(
        "Câu hỏi",
        value="Thông tư 41/2016/TT-NHNN quy định tỷ lệ an toàn vốn như thế nào?",
        height=96,
        placeholder="Nhập câu hỏi về quy định...",
    )
    method_label = st.segmented_control(
        "Method",
        options=list(METHOD_LABELS),
        default="Hybrid + Rerank",
        selection_mode="single",
    )
    top_k = st.select_slider("Top-k", options=[1, 3, 5, 10], value=5)
    submitted = st.form_submit_button(
        "Tìm kiếm",
        type="primary",
        icon=":material/search:",
        use_container_width=True,
    )

if submitted:
    if not question.strip():
        st.warning("Vui lòng nhập câu hỏi.", icon=":material/edit_note:")
    elif method_label is None:
        st.warning("Vui lòng chọn phương pháp retrieval.")
    else:
        method = METHOD_LABELS[method_label]
        try:
            with st.spinner("Đang truy xuất và xếp hạng..."):
                results, before = get_pipeline().retrieve_with_details(question, method, top_k)
                hints, graph_status = graph_hints(results)
            st.session_state["latest_results"] = results
            st.session_state["latest_before"] = before
            st.session_state["latest_hints"] = hints
            st.session_state["latest_graph_status"] = graph_status
            st.session_state["latest_method"] = method_label
        except Exception as error:
            st.error(f"Không thể hoàn tất truy vấn: {type(error).__name__}: {error}")

if "latest_results" in st.session_state:
    results = st.session_state["latest_results"]
    before = st.session_state["latest_before"]
    method_label = st.session_state["latest_method"]
    metric_columns = st.columns(3)
    metric_columns[0].metric("Method", method_label)
    metric_columns[1].metric("Results", len(results))
    metric_columns[2].metric("Top score", f"{float(results.iloc[0]['score']):.4f}")
    if before is not None:
        render_before_after(before, results)
    render_results(results)
    render_graph_hints(
        st.session_state["latest_hints"],
        st.session_state["latest_graph_status"],
    )