from __future__ import annotations

import html
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import VALID_ROLES
from src.retrieval import RetrievalPipeline, graph_hints
from src.secure_retriever import filter_secure_corpus

METHOD_LABELS = {
    "BM25": "bm25",
    "Dense": "dense",
    "Hybrid": "hybrid",
    "Hybrid + Rerank": "hybrid_rerank",
}


st.set_page_config(
    page_title="Secure RAG — Buổi 15",
    page_icon=":material/security:",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
    :root {
        --ink: #13231d;
        --muted: #586760;
        --paper: #f4f7f3;
        --line: #dfe7e1;
        --green: #1e5d47;
        --green-soft: #eaf3ee;
        --gold: #9a6c0c;
        --gold-soft: #f7efd7;
        --red: #8c2f2f;
        --red-soft: #fbe7e7;
    }
    .stApp { color: var(--ink); background: var(--paper); font-family: "IBM Plex Sans", sans-serif; }
    h1, h2, h3 { font-family: "Source Serif 4", serif !important; color: var(--ink) !important; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: rgba(255,255,255,0.85); }
    .kicker { color: var(--green); font-size: 0.78rem; letter-spacing: 0.08em; font-weight: 700; text-transform: uppercase; }
    .subtitle { color: var(--muted); margin-top: 0.25rem; margin-bottom: 1.2rem; }
    .pill {
        display: inline-block; background: var(--green-soft); border: 1px solid #d3e4d9; color: var(--green); border-radius: 999px;
        padding: 0.25rem 0.7rem; font-size: 0.76rem; font-weight: 600; margin: 0.25rem 0.35rem 0.25rem 0;
    }
    .result-card { border: 1px solid var(--line); background: rgba(255,255,255,0.82); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .meta { color: var(--muted); font-size: 0.82rem; margin-bottom: 0.5rem; }
    .score { color: var(--green); font-weight: 600; }
    .warning-box { background: var(--red-soft); border-left: 4px solid var(--red); padding: 0.75rem 0.9rem; border-radius: 8px; color: #6d2020; }
    .citation-box { background: var(--gold-soft); border-left: 4px solid var(--gold); padding: 0.7rem 0.8rem; border-radius: 8px; color: #66460a; }
    .result-text { white-space: pre-wrap; line-height: 1.7; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_pipeline() -> RetrievalPipeline:
    return RetrievalPipeline()


@st.cache_data(show_spinner=False)
def load_secure_role_map() -> dict[str, list[str]]:
    secure_path = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"
    if not secure_path.is_file():
        return {}
    df = pd.read_csv(secure_path, dtype=str, keep_default_na=False, encoding="utf-8")
    role_map: dict[str, list[str]] = {}
    for row in df.itertuples(index=False):
        chunk_id = str(getattr(row, "chunk_id", "")).strip()
        raw_roles = getattr(row, "allowed_roles", "[]")
        if not chunk_id:
            continue
        try:
            parsed = __import__("json").loads(raw_roles)
        except Exception:
            parsed = []
        if isinstance(parsed, list):
            role_map[chunk_id] = [str(item).strip() for item in parsed if str(item).strip()]
        else:
            role_map[chunk_id] = []
    return role_map


def apply_role_filter(results: pd.DataFrame, user_roles: list[str]) -> tuple[pd.DataFrame, int]:
    if results.empty:
        return results.copy(), 0
    if not user_roles:
        return results.iloc[0:0].copy(), len(results)

    role_map = load_secure_role_map()
    enriched = results.copy()
    enriched["allowed_roles"] = enriched["chunk_id"].map(lambda chunk_id: role_map.get(str(chunk_id), []))

    filtered_rows = []
    for row in enriched.itertuples(index=False):
        allowed_roles = getattr(row, "allowed_roles", None)
        if isinstance(allowed_roles, str):
            parsed = [part.strip() for part in allowed_roles.split(",") if part.strip()]
        elif isinstance(allowed_roles, list):
            parsed = [str(item).strip() for item in allowed_roles if str(item).strip()]
        else:
            parsed = []
        if any(role in parsed for role in user_roles):
            filtered_rows.append(row)

    filtered = pd.DataFrame(filtered_rows)
    if filtered.empty:
        return filtered, len(results)
    return filtered, len(results) - len(filtered)


st.markdown('<div class="kicker">Secure retrieval workbench</div>', unsafe_allow_html=True)
st.title("RBAC RAG Search — Buổi 15")
st.markdown(
    '<div class="subtitle">Lọc quyền truy cập theo vai trò trước khi hiển thị kết quả tìm kiếm và graph hints.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Cấu hình")
    user_roles = st.multiselect(
        "Vai trò của bạn (Your Roles)",
        options=list(VALID_ROLES),
        default=["Guest"],
    )
    st.caption("Chỉ các chunk có ít nhất một role chung với danh sách này mới được hiển thị.")

    method_label = st.selectbox("Method", options=list(METHOD_LABELS.keys()), index=3)
    top_k = st.select_slider("Top-k", options=[1, 3, 5, 10], value=5)

with st.form("secure_search_form", border=True):
    question = st.text_area(
        "Câu hỏi",
        value="Thông tư 41/2016/TT-NHNN quy định tỷ lệ an toàn vốn như thế nào?",
        height=96,
        placeholder="Nhập câu hỏi về quy định...",
    )
    submitted = st.form_submit_button("Tìm kiếm", type="primary", use_container_width=True)

if submitted:
    if not question.strip():
        st.warning("Vui lòng nhập câu hỏi.", icon=":material/edit_note:")
    elif not user_roles:
        st.warning("Vui lòng chọn ít nhất một vai trò.", icon=":material/lock:")
    else:
        method = METHOD_LABELS[method_label]
        try:
            with st.spinner("Đang truy xuất theo quyền RBAC..."):
                results, before = get_pipeline().retrieve_with_details(question, method, top_k)
                filtered_results, filtered_out = apply_role_filter(results, list(user_roles))
                hints, graph_status = graph_hints(filtered_results)

            st.session_state["latest_results"] = filtered_results
            st.session_state["latest_before"] = before
            st.session_state["latest_hints"] = hints
            st.session_state["latest_graph_status"] = graph_status
            st.session_state["latest_method"] = method_label
            st.session_state["latest_roles"] = list(user_roles)
            st.session_state["filtered_out_count"] = filtered_out
        except Exception as error:
            st.error(f"Không thể hoàn tất truy vấn: {type(error).__name__}: {error}")

if "latest_results" in st.session_state:
    results = st.session_state["latest_results"]
    before = st.session_state["latest_before"]
    method_label = st.session_state["latest_method"]
    current_roles = st.session_state["latest_roles"]
    filtered_out_count = st.session_state.get("filtered_out_count", 0)

    st.markdown(f'<div class="pill">Method: {method_label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pill">Roles: {", ".join(current_roles)}</div>', unsafe_allow_html=True)

    if filtered_out_count > 0:
        st.markdown(
            f'<div class="warning-box">Đã lọc bỏ {filtered_out_count} kết quả do không đủ quyền truy cập.</div>',
            unsafe_allow_html=True,
        )

    if results.empty:
        st.warning("Không có kết quả nào phù hợp với vai trò đã chọn.", icon=":material/lock:")
    else:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Results", len(results))
        metric_cols[1].metric("Selected roles", len(current_roles))
        metric_cols[2].metric("Top score", f"{float(results.iloc[0]['score']):.4f}")

        if before is not None and not before.empty:
            left, right = st.columns(2)
            with left:
                st.subheader("Before rerank")
                st.dataframe(before.head(5)[["rank", "chunk_id", "score"]], hide_index=True, use_container_width=True)
            with right:
                st.subheader("After rerank")
                st.dataframe(results.head(5)[["rank", "chunk_id", "score"]], hide_index=True, use_container_width=True)

        st.subheader("Kết quả truy vấn")
        for _, row in results.iterrows():
            text = str(row.get("text", "")).strip()
            citation = str(row.get("citation", "")).strip()
            allowed_roles = row.get("allowed_roles", [])
            if isinstance(allowed_roles, str):
                try:
                    import json

                    allowed_roles = json.loads(allowed_roles)
                except Exception:
                    allowed_roles = []
            if not isinstance(allowed_roles, list):
                allowed_roles = []

            with st.container(border=True):
                st.markdown(f"### #{int(row['rank'])} · {row['chunk_id']}")
                st.markdown(
                    f"""
                    <div class="meta">
                        <strong>Document:</strong> {html.escape(str(row['document_id']))} &nbsp;|&nbsp;
                        <strong>Method:</strong> {html.escape(str(row['retrieval_method']))} &nbsp;|&nbsp;
                        <strong>Quyền xem:</strong> {html.escape(', '.join(allowed_roles) if allowed_roles else 'Không có quyền')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f'<div class="score">Score: {float(row["score"]):.6f}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="citation-box"><strong>Citation</strong><br>{html.escape(citation)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="result-text">{html.escape(text)}</div>', unsafe_allow_html=True)

        st.subheader("Graph hints")
        if st.session_state["latest_hints"]:
            for hint in st.session_state["latest_hints"]:
                doc_id = html.escape(str(hint["document_id"]))
                chunk_id = html.escape(str(hint["chunk_id"]))
                relations = hint.get("relations", [])
                if relations:
                    rel_text = " · ".join(
                        f"{rel['direction']} {rel['type']} {rel['other_document_id']}"
                        for rel in relations
                    )
                else:
                    rel_text = "Không có quan hệ VanBan trực tiếp"
                st.markdown(
                    f"""
                    <div class="result-card">
                        <strong>{doc_id}</strong> → {chunk_id}<br>
                        <span>{html.escape(rel_text)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Không có Graph hints nào phù hợp với quyền hiện tại.")

        if st.session_state["latest_graph_status"]:
            st.caption(st.session_state["latest_graph_status"])

st.caption("Security policy: fail-closed. Nếu không có quyền, dữ liệu sẽ bị ẩn hoàn toàn.")
