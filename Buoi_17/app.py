from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = APP_ROOT / "scripts"
AUDIT_LOG_PATH = APP_ROOT / "outputs" / "audit_log.jsonl"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from audit_logger import _sanitize
from compliance_gap import run_gap_checker
from internal_lookup import lookup
from secure_retrieval_adapter import SecureRetrievalAdapter

load_dotenv(APP_ROOT / ".env", override=False)
VALID_ROLES = ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]

st.set_page_config(
    page_title="Secure RAG & Compliance - Buoi 17",
    page_icon=":material/verified_user:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
    :root {
        --ink: #17231f;
        --muted: #5c6a63;
        --paper: #f4f7f3;
        --panel: #ffffff;
        --line: #dce5df;
        --green: #1f6048;
        --green-soft: #e6f1eb;
        --gold: #a66b0a;
        --gold-soft: #f8efd9;
        --red: #8e3030;
        --red-soft: #fbe9e7;
    }
    .stApp {
        color: var(--ink);
        background-color: var(--paper);
        background-image: linear-gradient(rgba(31,96,72,.028) 1px, transparent 1px), linear-gradient(90deg, rgba(31,96,72,.028) 1px, transparent 1px);
        background-size: 28px 28px;
        font-family: "IBM Plex Sans", sans-serif;
    }
    h1, h2, h3 { font-family: "Source Serif 4", serif !important; color: var(--ink) !important; letter-spacing: 0 !important; }
    h1 { font-size: 2.3rem !important; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
    .kicker { color: var(--green); font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .subtitle { color: var(--muted); line-height: 1.6; margin: -.35rem 0 1.35rem; }
    .banner { background: var(--gold-soft); border-left: 4px solid var(--gold); padding: .75rem .9rem; margin: .6rem 0 1.4rem; color: #66460a; }
    .metric-card { background: var(--green-soft); border: 1px solid #d0e4d7; border-radius: 6px; padding: .8rem 1rem; }
    .meta { color: var(--muted); font-size: .86rem; line-height: 1.55; }
    .citation { background: var(--gold-soft); border-left: 3px solid var(--gold); padding: .65rem .8rem; margin: .55rem 0; color: #66460a; line-height: 1.5; }
    .answer { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 1rem 1.1rem; line-height: 1.7; white-space: pre-wrap; }
    .denied { background: var(--red-soft); border-left: 4px solid var(--red); padding: .75rem .9rem; color: #6d2020; }
    </style>
    """,
    unsafe_allow_html=True,
)


def neo4j_status() -> str:
    try:
        from neo4j import GraphDatabase

        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE")
        if not all((uri, user, password, database)):
            return "NOT_CONFIGURED"
        driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            driver.verify_connectivity()
            return "READY"
        finally:
            driver.close()
    except Exception as error:
        return f"UNAVAILABLE ({type(error).__name__})"


def load_audit_events() -> list[dict[str, object]]:
    if not AUDIT_LOG_PATH.is_file():
        return []
    events = []
    for line in AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(_sanitize(event))
    return events


@st.cache_resource(show_spinner=False)
def get_adapter() -> SecureRetrievalAdapter:
    return SecureRetrievalAdapter()


st.markdown('<div class="kicker">Governed retrieval workbench</div>', unsafe_allow_html=True)
st.title("Secure RAG & Compliance - Buoi 17")
st.markdown(
    '<div class="subtitle">Tra cứu theo quyền, truy vết request và kiểm tra trạng thái evidence trong cùng một workspace.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="banner">Demo dao tao - ket qua AI can duoc kiem toan vien xac minh.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Demo identity")
    user_id = st.text_input("User ID", value="demo01")
    user_role = st.selectbox("User Role", options=VALID_ROLES, index=VALID_ROLES.index("Guest"))
    top_k = st.slider("Top-k", min_value=1, max_value=10, value=3)
    st.divider()
    status = neo4j_status()
    if status == "READY":
        st.success(f"Neo4j: {status}", icon=":material/database:")
    else:
        st.warning(f"Neo4j: {status}", icon=":material/database_off:")

lookup_tab, gap_tab, audit_tab = st.tabs(["TRA CUU QUY DINH", "COMPLIANCE GAP CHECKER", "AUDIT"])

with lookup_tab:
    st.subheader("Tra cuu quy dinh noi bo")
    question = st.text_area(
        "Question",
        value="Quy dinh ve giao nhan va bao quan tien mat la gi?",
        height=100,
    )
    if st.button("Run lookup", type="primary", icon=":material/search:"):
        try:
            with st.spinner("Dang loc RBAC va truy xuat..."):
                result = lookup(question, user_role, top_k=top_k)
            st.session_state["lookup_result"] = result
        except Exception as error:
            st.error(f"Khong the hoan tat request: {type(error).__name__}: {error}")

    result = st.session_state.get("lookup_result")
    if result:
        if result["access_decision"] == "DENY":
            st.markdown('<div class="denied">Access denied: khong co chunk nao trong pham vi quyen truy cap.</div>', unsafe_allow_html=True)
        else:
            metric_columns = st.columns(3)
            metric_columns[0].metric("Documents", len(result["document_ids"]))
            metric_columns[1].metric("Chunks", len(result["chunk_ids"]))
            metric_columns[2].metric("Role", str(result["access_scope"]))
            st.markdown("### Answer")
            st.markdown(f'<div class="answer">{result["answer"]}</div>', unsafe_allow_html=True)
            st.markdown("### Evidence")
            for citation in result["citations"]:
                st.markdown(f'<div class="citation">{citation}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="meta"><strong>Document IDs:</strong> {", ".join(result["document_ids"])}<br>'
                f'<strong>Chunk IDs:</strong> {", ".join(result["chunk_ids"])}<br>'
                f'<strong>Access decision:</strong> {result["access_decision"]}<br>'
                f'<strong>Request ID:</strong> {result["request_id"]}</div>',
                unsafe_allow_html=True,
            )

with gap_tab:
    st.subheader("Compliance Gap Checker")
    st.info("Corpus hop nhat da co external requirement va internal policy Agribank. Moi ket qua van bat buoc human review.", icon=":material/info:")
    st.markdown("### Evidence status")
    st.dataframe(
        pd.DataFrame(
            [
                {"Evidence side": "EXTERNAL_REQUIREMENT", "Status": "AVAILABLE", "Source": "15 documents / 787 chunks"},
                {"Evidence side": "INTERNAL_POLICY", "Status": "AVAILABLE", "Source": "10 documents / 24 chunks"},
                {"Output": "Compliance classification", "Status": "READY", "Source": "P7 gap checker"},
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    if st.button("Run gap checker", icon=":material/compare_arrows:"):
        try:
            with st.spinner("Dang tim evidence va rerank..."):
                st.session_state["gap_results"] = run_gap_checker()
        except Exception as error:
            st.error(f"Khong the chay gap checker: {type(error).__name__}: {error}")
    gap_results = st.session_state.get("gap_results")
    if gap_results is not None and not gap_results.empty:
        st.dataframe(
            gap_results[
                [
                    "external_document_id",
                    "external_citation",
                    "internal_document_id",
                    "internal_citation",
                    "classification",
                    "reason",
                    "confidence",
                    "review_status",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )

with audit_tab:
    st.subheader("Audit trail")
    all_events = load_audit_events()
    role_events = [event for event in all_events if event.get("user_role") == user_role]
    st.caption(f"Hien thi {len(role_events)} event phu hop voi role `{user_role}`.")
    if role_events:
        st.dataframe(pd.DataFrame(role_events), hide_index=True, use_container_width=True)
    else:
        st.info("Chua co audit event phu hop voi role nay.", icon=":material/history:")
