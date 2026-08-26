from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)

from audit_checklist_gen import DOMAIN_CONFIG, generate_checklist
from compliance_checker import DOMAIN_QUERIES, run_checker
from internal_lookup import lookup

st.set_page_config(page_title="Agribank Local AI", page_icon=":material/verified_user:", layout="wide")
st.title("Agribank Local AI Compliance")
st.caption(f"Provider: {os.getenv('LLM_PROVIDER', 'ollama')} | Model: {os.getenv('OLLAMA_MODEL', 'qwen3:0.6b')}")

role_label = st.sidebar.selectbox(
    "User role",
    ["Kiểm toán viên", "Admin", "Risk_Manager", "Staff", "Guest"],
)
role = "Admin" if role_label == "Kiểm toán viên" else role_label
lookup_tab, compliance_tab, checklist_tab = st.tabs(["Internal Lookup", "UC3 Compliance", "UC4 Audit Checklist"])

with lookup_tab:
    question = st.text_input("Question", value="quy dinh giao nhan bao quan tien mat")
    if st.button("Search", type="primary"):
        result = lookup(question, role)
        st.write(result["answer"])
        st.caption(f"Review status: {result['review_status']}")
        st.dataframe(pd.DataFrame({"citation": result["citations"]}), use_container_width=True)

with compliance_tab:
    if st.button("Run compliance checker"):
        try:
            results = run_checker(role)
            st.dataframe(results, use_container_width=True)
        except Exception as error:
            st.error(str(error))
    st.caption("Domains: " + ", ".join(DOMAIN_QUERIES))

with checklist_tab:
    domain = st.selectbox("Audit domain", list(DOMAIN_CONFIG))
    if st.button("Generate checklist"):
        try:
            results = generate_checklist(domain, user_role=role)
            st.dataframe(results, use_container_width=True)
        except Exception as error:
            st.error(str(error))
