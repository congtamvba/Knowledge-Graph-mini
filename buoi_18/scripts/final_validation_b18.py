from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import pandas as pd

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_18_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_18_ROOT.parent
DATA_PATH = BUOI_18_ROOT / "data" / "chunks_combined_secure.csv"
INTERNAL_PATH = BUOI_18_ROOT / "data" / "agribank_internal_policies.csv"
OUTPUTS_ROOT = BUOI_18_ROOT / "outputs"
CONFLICTS_PATH = OUTPUTS_ROOT / "compliance_conflicts.csv"
CHECKLIST_PATH = OUTPUTS_ROOT / "audit_checklist_results.csv"
AUDIT_LOG_PATH = OUTPUTS_ROOT / "audit_log.jsonl"
REPORT_PATH = OUTPUTS_ROOT / "final_validation_b18_report.md"
APP_PATH = BUOI_18_ROOT / "app.py"
COMPLIANCE_SCRIPT = SCRIPT_ROOT / "compliance_checker.py"
CHECKLIST_SCRIPT = SCRIPT_ROOT / "audit_checklist_gen.py"

RESULT_COLUMNS = [
    "conflict_id", "domain", "doc_a_id", "doc_a_citation", "doc_a_text",
    "doc_b_id", "doc_b_citation", "doc_b_text", "conflict_type", "severity",
    "description", "review_status", "timestamp", "request_id",
]
CHECKLIST_COLUMNS = [
    "item_id", "domain", "unit_scope", "audit_question", "risk_description",
    "risk_level", "source_citation", "recommendation", "review_status",
]
AUDIT_REQUIRED_FIELDS = {
    "timestamp_utc", "request_id", "user_id_demo", "user_role", "action", "query",
    "retrieval_method", "retrieved_document_ids", "retrieved_chunk_ids", "citation_ids",
    "rbac_filtered_candidate_count", "status",
}


def check_source_data() -> tuple[bool, str]:
    try:
        internal = pd.read_csv(INTERNAL_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        combined = pd.read_csv(DATA_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        status = subprocess.run(
            ["git", "status", "--short", "--", "buoi_18/data"],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        changed_source = [
            line for line in status.stdout.splitlines()
            if line[:2].strip() in {"M", "D"}
        ]
        clean = not changed_source
        passed = len(internal) == 24 and len(combined) == 811 and clean
        return passed, f"internal_rows={len(internal)}; combined_rows={len(combined)}; source_git_status_clean={clean}"
    except Exception as error:
        return False, f"{type(error).__name__}: {error}"


def check_uc3(corpus: pd.DataFrame, conflicts: pd.DataFrame) -> tuple[bool, str]:
    source_citations = set(corpus["citation"].astype(str))
    passed = (
        list(conflicts.columns) == RESULT_COLUMNS
        and len(conflicts) == 3
        and conflicts["doc_a_citation"].isin(source_citations).all()
        and conflicts["doc_b_citation"].isin(source_citations).all()
        and conflicts["severity"].isin({"HIGH", "MEDIUM", "LOW"}).all()
    )
    return bool(passed), f"rows={len(conflicts)}; schema={list(conflicts.columns) == RESULT_COLUMNS}; citations={conflicts['doc_a_citation'].isin(source_citations).all() and conflicts['doc_b_citation'].isin(source_citations).all()}"


def check_uc4(corpus: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    source_citations = set(corpus["citation"].astype(str))
    citation_ok = not checklist.empty and checklist["source_citation"].map(lambda value: all(part in source_citations for part in str(value).split("\n"))).all()
    passed = list(checklist.columns) == CHECKLIST_COLUMNS and len(checklist) == 6 and citation_ok and checklist["risk_level"].isin({"HIGH", "MEDIUM", "LOW"}).all()
    return bool(passed), f"rows={len(checklist)}; schema={list(checklist.columns) == CHECKLIST_COLUMNS}; citations={citation_ok}"


def check_citation_linking(corpus: pd.DataFrame, conflicts: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    source_citations = set(corpus["citation"].astype(str))
    conflict_ok = conflicts["doc_a_citation"].isin(source_citations).all() and conflicts["doc_b_citation"].isin(source_citations).all()
    checklist_ok = checklist["source_citation"].map(lambda value: all(part in source_citations for part in str(value).split("\n"))).all()
    return bool(conflict_ok and checklist_ok), f"conflict_links={conflict_ok}; checklist_links={checklist_ok}"


def check_rbac(corpus: pd.DataFrame) -> tuple[bool, str]:
    it_rows = corpus[corpus["document_id"].eq("agr_it07")]
    staff_rows = it_rows[it_rows["allowed_roles"].map(lambda value: "Staff" in json.loads(value))]
    admin_rows = it_rows[it_rows["allowed_roles"].map(lambda value: "Admin" in json.loads(value))]
    source = COMPLIANCE_SCRIPT.read_text(encoding="utf-8")
    filter_before_retrieval = source.find("visible = authorized_corpus") < source.find("retrieval_corpus = external_candidates")
    passed = not it_rows.empty and staff_rows.empty and not admin_rows.empty and filter_before_retrieval
    return bool(passed), f"restricted_it_chunks={len(it_rows)}; staff_visible={len(staff_rows)}; admin_visible={len(admin_rows)}; filter_before_bm25={filter_before_retrieval}"


def check_streamlit() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen("http://localhost:8502/_stcore/health", timeout=5) as response:
            body = response.read().decode("utf-8").strip()
        return response.status == 200 and body == "ok", f"health_status={response.status}; body={body}"
    except Exception as error:
        return False, f"health check failed: {type(error).__name__}"


def check_audit() -> tuple[bool, str]:
    if not AUDIT_LOG_PATH.is_file():
        return False, "audit_log.jsonl is missing"
    events = []
    raw = AUDIT_LOG_PATH.read_text(encoding="utf-8")
    try:
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except json.JSONDecodeError as error:
        return False, f"invalid JSON Lines: {error}"
    complete = bool(events) and all(AUDIT_REQUIRED_FIELDS <= set(event) for event in events)
    actions = {event.get("action") for event in events}
    secret_terms = ("api_key", "apikey", "password", "secret", "private_key", "token")
    no_secrets = not any(term in raw.casefold() for term in secret_terms)
    passed = complete and {"compliance cross-comparison", "audit checklist generation"} <= actions and no_secrets
    return bool(passed), f"events={len(events)}; required_fields={complete}; actions={sorted(actions)}; no_secrets={no_secrets}"


def check_human_review(conflicts: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    conflict_ok = not conflicts.empty and conflicts["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    checklist_ok = not checklist.empty and checklist["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    return bool(conflict_ok and checklist_ok), f"conflicts={conflict_ok}; checklist={checklist_ok}"


def run_validation() -> bool:
    corpus = pd.read_csv(DATA_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    conflicts = pd.read_csv(CONFLICTS_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    checklist = pd.read_csv(CHECKLIST_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    checks = [
        ("Source data integrity", *check_source_data()),
        ("UC3 compliance checker", *check_uc3(corpus, conflicts)),
        ("UC4 audit checklist generator", *check_uc4(corpus, checklist)),
        ("Citation and linking", *check_citation_linking(corpus, conflicts, checklist)),
        ("RBAC and governance", *check_rbac(corpus)),
        ("Streamlit web interface", *check_streamlit()),
        ("Audit trail", *check_audit()),
        ("Human review guardrail", *check_human_review(conflicts, checklist)),
    ]
    lines = [
        "# Final Validation Report - Buoi 18",
        "",
        "Kiểm tra read-only dữ liệu nguồn và toàn bộ artifact UC3, UC4, UI, RBAC, audit trail và human review.",
        "",
        "| Criterion | Status | Detail |",
        "|---|---|---|",
    ]
    for name, passed, detail in checks:
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {detail} |")
    failed = [name for name, passed, _ in checks if not passed]
    overall = not failed
    lines.extend(
        [
            "",
            f"Passed: `{len(checks) - len(failed)}`; Failed: `{len(failed)}`",
            "",
            "```text",
            f"UC3 COMPLIANCE CHECKER: {'PASS' if checks[1][1] else 'FAIL'}",
            f"UC4 AUDIT CHECKLIST GEN: {'PASS' if checks[2][1] else 'FAIL'}",
            f"CITATION INTEGRITY: {'PASS' if checks[3][1] else 'FAIL'}",
            f"RBAC & GOVERNANCE: {'PASS' if checks[4][1] else 'FAIL'}",
            f"STREAMLIT DEMO: {'PASS' if checks[5][1] else 'FAIL'}",
            f"AUDIT TRAIL: {'PASS' if checks[6][1] else 'FAIL'}",
            f"SYSTEM READY FOR DEMO: {'YES' if overall else 'NO'}",
            "```",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"FINAL_VALIDATION={'PASS' if overall else 'FAIL'}")
    print(f"PASSED={len(checks) - len(failed)}")
    print(f"FAILED={len(failed)}")
    return overall


if __name__ == "__main__":
    raise SystemExit(0 if run_validation() else 1)
