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
OUTPUTS_ROOT = APP_ROOT / "outputs"
AUDIT_LOG_PATH = OUTPUTS_ROOT / "audit_log.jsonl"
ENV_PATH = APP_ROOT / ".env"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from audit_checklist_gen import DOMAIN_CONFIG, generate_checklist
from compliance_checker import DOMAIN_DOCUMENTS, load_corpus, run_checker
from audit_logger import _sanitize

load_dotenv(ENV_PATH, override=False)

VALID_ROLES = ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]
DOMAINS = list(DOMAIN_DOCUMENTS)
CHECKLIST_DOMAINS = list(DOMAIN_CONFIG)
UNITS = ["Chi nhánh loại 1", "Phòng giao dịch", "Khối CNTT", "Phòng Kế toán"]

st.set_page_config(
    page_title="AI Compliance & Audit - Buổi 18",
    page_icon=":material/fact_check:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
    :root { --ink:#17231f; --muted:#5c6a63; --paper:#f4f7f3; --panel:#fff; --line:#dce5df; --green:#1f6048; --green-soft:#e6f1eb; --gold:#a66b0a; --gold-soft:#f8efd9; --red:#8e3030; }
    .stApp { color:var(--ink); background:var(--paper); background-image:linear-gradient(rgba(31,96,72,.028) 1px,transparent 1px),linear-gradient(90deg,rgba(31,96,72,.028) 1px,transparent 1px); background-size:28px 28px; font-family:"IBM Plex Sans",sans-serif; }
    h1,h2,h3 { font-family:"Source Serif 4",serif !important; color:var(--ink) !important; letter-spacing:0 !important; }
    .block-container { max-width:1200px; padding-top:2rem; padding-bottom:3rem; }
    .kicker { color:var(--green); font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
    .subtitle { color:var(--muted); line-height:1.6; margin:-.35rem 0 1.35rem; }
    .banner { background:var(--gold-soft); border-left:4px solid var(--gold); padding:.8rem 1rem; margin:.6rem 0 1.4rem; color:#66460a; }
    .citation { background:var(--gold-soft); border-left:3px solid var(--gold); padding:.65rem .8rem; margin:.55rem 0; color:#66460a; line-height:1.5; }
    .meta { color:var(--muted); font-size:.86rem; line-height:1.55; }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_audit_events() -> list[dict[str, object]]:
    if not AUDIT_LOG_PATH.is_file():
        return []
    events = []
    for line in AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            events.append(_sanitize(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return events


def data_status() -> tuple[bool, bool]:
    try:
        corpus = load_corpus()
        internal_ready = corpus["document_id"].str.startswith("agr_").any()
        combined_ready = len(corpus) > 0
        return bool(internal_ready), bool(combined_ready)
    except Exception:
        return False, False


def markdown_download(path: Path) -> bytes:
    return path.read_bytes() if path.is_file() else b""


st.markdown('<div class="kicker">Governed AI audit workbench</div>', unsafe_allow_html=True)
st.title("AI Compliance & Audit - Buổi 18")
st.markdown(
    '<div class="subtitle">Đối chiếu quy định, lập checklist và theo dõi audit trail trong một workspace có kiểm soát quyền.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="banner">Demo sản phẩm AI Kiểm toán - Kết quả gợi ý cần kiểm toán viên xác minh trước khi ban hành.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Phiên làm việc")
    user_id = st.text_input("User ID", value="demo-b18")
    user_role = st.selectbox("User Role", VALID_ROLES, index=0)
    internal_ready, combined_ready = data_status()
    st.divider()
    st.caption("Trạng thái dữ liệu")
    (st.success if internal_ready else st.error)("Internal Policies: READY" if internal_ready else "Internal Policies: MISSING")
    (st.success if combined_ready else st.error)("External / Combined Docs: READY" if combined_ready else "External / Combined Docs: MISSING")
    st.caption(f"LLM model: {os.getenv('LLM_MODEL', 'not configured')}")
    if st.button("Reset Session", icon=":material/refresh:"):
        st.session_state.clear()
        st.rerun()
    if st.button("Clean Audit Log", icon=":material/delete_sweep:"):
        if AUDIT_LOG_PATH.is_file():
            AUDIT_LOG_PATH.unlink()
        st.session_state.pop("audit_events", None)
        st.success("Audit log đã được xóa cho phiên demo.")

compliance_tab, checklist_tab, audit_tab = st.tabs(
    ["UC3 · Compliance Checker", "UC4 · Audit Checklist", "Audit Log · System Trail"]
)

with compliance_tab:
    st.subheader("AI Compliance Checker")
    st.caption("RBAC được lọc trước BM25. Các phát hiện chỉ là bằng chứng cần human review.")
    selected_domain = st.selectbox("Domain đối chiếu", ["Toàn bộ domain"] + DOMAINS)
    if st.button("Phát hiện xung đột & mâu thuẫn", type="primary", icon=":material/compare_arrows:"):
        try:
            with st.spinner("Đang lọc quyền và đối chiếu evidence..."):
                results = run_checker(user_role=user_role, user_id=user_id, use_llm=True)
            if selected_domain != "Toàn bộ domain":
                results = results[results["domain"].eq(selected_domain)].copy()
            st.session_state["compliance_results"] = results
        except Exception as error:
            st.error(f"Không thể hoàn tất kiểm tra: {type(error).__name__}: {error}")

    results = st.session_state.get("compliance_results")
    if results is not None:
        if results.empty:
            st.warning("Chưa có evidence phù hợp trong phạm vi quyền truy cập.")
        else:
            metrics = st.columns(4)
            metrics[0].metric("Findings", len(results))
            metrics[1].metric("HIGH", int((results["severity"] == "HIGH").sum()))
            metrics[2].metric("MEDIUM", int((results["severity"] == "MEDIUM").sum()))
            metrics[3].metric("Human review", "REQUIRED")
            display = results[["domain", "doc_a_id", "doc_a_citation", "doc_b_id", "doc_b_citation", "conflict_type", "severity", "review_status"]]
            st.dataframe(display, hide_index=True, use_container_width=True)
            st.info("Không có nút phê duyệt tự động. Kiểm toán viên phải xác minh evidence trước khi ban hành.", icon=":material/rule:")
            st.download_button("Tải CSV", results.to_csv(index=False, encoding="utf-8-sig"), "compliance_conflicts.csv", "text/csv", icon=":material/download:")
            report_path = OUTPUTS_ROOT / "compliance_conflict_report.md"
            if report_path.is_file():
                st.download_button("Tải Markdown", markdown_download(report_path), "compliance_conflict_report.md", "text/markdown", icon=":material/description:")
            with st.expander("Xem mô tả evidence"):
                for row in results.itertuples(index=False):
                    st.markdown(f"**{row.domain} · {row.conflict_type} · {row.severity}**")
                    st.markdown(f"- A: {row.doc_a_text}")
                    st.markdown(f"- B: {row.doc_b_text}")
                    st.markdown(f"- Phân tích: {row.description}")
                    st.divider()

with checklist_tab:
    st.subheader("AI Audit Checklist Generator")
    st.caption("Checklist bám theo domain/unit đã chọn; citation được giữ từ evidence nguồn.")
    checklist_domain = st.selectbox("Phạm vi kiểm toán", CHECKLIST_DOMAINS)
    default_unit = DOMAIN_CONFIG[checklist_domain]["unit_scope"].split(";")[0].strip()
    unit = st.selectbox("Đơn vị được kiểm toán", UNITS, index=UNITS.index(default_unit) if default_unit in UNITS else 0)
    if st.button("Tạo bản nháp Checklist kiểm toán", type="primary", icon=":material/fact_check:"):
        try:
            with st.spinner("Đang truy xuất evidence và tạo checklist..."):
                checklist = generate_checklist(checklist_domain, unit, user_role=user_role, user_id=user_id, use_llm=True)
            st.session_state["checklist_results"] = checklist
        except Exception as error:
            st.error(f"Không thể tạo checklist: {type(error).__name__}: {error}")

    checklist = st.session_state.get("checklist_results")
    if checklist is not None:
        metrics = st.columns(3)
        metrics[0].metric("Checklist items", len(checklist))
        metrics[1].metric("Citations", "ATTACHED")
        metrics[2].metric("Review", "REQUIRED")
        st.dataframe(checklist[["item_id", "audit_question", "risk_description", "risk_level", "source_citation", "review_status"]], hide_index=True, use_container_width=True)
        st.download_button("Tải Checklist CSV", checklist.to_csv(index=False, encoding="utf-8-sig"), "audit_checklist_results.csv", "text/csv", icon=":material/download:")
        st.download_button("Tải Checklist JSON", checklist.to_json(orient="records", force_ascii=False, indent=2), "audit_checklist_results.json", "application/json", icon=":material/data_object:")
        report_path = OUTPUTS_ROOT / "audit_checklist_report.md"
        if report_path.is_file():
            st.download_button("Tải báo cáo Markdown", markdown_download(report_path), "audit_checklist_report.md", "text/markdown", icon=":material/description:")

with audit_tab:
    st.subheader("Audit Log & System Trail")
    events = load_audit_events()
    event_roles = sorted({str(event.get("user_role", "")) for event in events if event.get("user_role")})
    event_actions = sorted({str(event.get("action", "")) for event in events if event.get("action")})
    role_filter = st.selectbox("Lọc theo Role", ["Tất cả"] + event_roles)
    action_filter = st.selectbox("Lọc theo Action", ["Tất cả"] + event_actions)
    filtered = [event for event in events if (role_filter == "Tất cả" or event.get("user_role") == role_filter) and (action_filter == "Tất cả" or event.get("action") == action_filter)]
    st.caption(f"Hiển thị {len(filtered)} / {len(events)} audit events.")
    if filtered:
        st.dataframe(pd.DataFrame(filtered), hide_index=True, use_container_width=True)
    else:
        st.info("Chưa có audit event phù hợp.", icon=":material/history:")
