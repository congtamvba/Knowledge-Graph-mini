from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_18_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_18_ROOT.parent
DATA_PATH = BUOI_18_ROOT / "data" / "chunks_combined_secure.csv"
OUTPUTS_ROOT = BUOI_18_ROOT / "outputs"
RESULTS_PATH = OUTPUTS_ROOT / "compliance_conflicts.csv"
CHECKLIST_PATH = OUTPUTS_ROOT / "audit_checklist_results.csv"
AUDIT_LOG_PATH = OUTPUTS_ROOT / "audit_log.jsonl"
REPORT_PATH = OUTPUTS_ROOT / "security_test_b18_report.md"

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from audit_checklist_gen import generate_checklist
from compliance_checker import load_corpus

RESULT_COLUMNS = [
    "conflict_id", "domain", "doc_a_id", "doc_a_citation", "doc_a_text",
    "doc_b_id", "doc_b_citation", "doc_b_text", "conflict_type", "severity",
    "description", "review_status", "timestamp", "request_id",
]
CHECKLIST_COLUMNS = [
    "item_id", "domain", "unit_scope", "audit_question", "risk_description",
    "risk_level", "source_citation", "recommendation", "review_status",
]
SENSITIVE_TERMS = ("api_key", "apikey", "password", "secret", "private_key", "token")


def _test_rbac(corpus: pd.DataFrame) -> tuple[bool, str]:
    restricted = corpus[corpus["document_id"].eq("agr_it07")]
    staff_visible = restricted[restricted["allowed_roles"].map(lambda value: "Staff" in json.loads(value))]
    admin_visible = restricted[restricted["allowed_roles"].map(lambda value: "Admin" in json.loads(value))]
    passed = not restricted.empty and staff_visible.empty and not admin_visible.empty
    return passed, f"agr_it07 chunks={len(restricted)}; Staff_visible={len(staff_visible)}; Admin_visible={len(admin_visible)}"


def _test_citations(corpus: pd.DataFrame, conflicts: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    citations = set(corpus["citation"].astype(str))
    conflict_ok = not conflicts.empty and conflicts["doc_a_citation"].isin(citations).all() and conflicts["doc_b_citation"].isin(citations).all()
    checklist_ok = not checklist.empty and checklist["source_citation"].map(lambda value: any(citation in str(value) for citation in citations)).all()
    return bool(conflict_ok and checklist_ok), f"conflicts={len(conflicts)}; checklist={len(checklist)}; conflict_citations={conflict_ok}; checklist_citations={checklist_ok}"


def _test_hallucination(corpus: pd.DataFrame, conflicts: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    corpus_rows = corpus.set_index("chunk_id")
    conflict_text_ok = all(
        row.doc_a_text == corpus_rows.loc[row.doc_a_citation.split("|")[-1].strip(), "text"]
        if row.doc_a_citation.split("|")[-1].strip() in corpus_rows.index else row.doc_a_text in set(corpus["text"])
        for row in conflicts.itertuples(index=False)
    )
    known_citations = set(corpus["citation"].astype(str))
    checklist_citation_ok = checklist["source_citation"].map(lambda value: all(part in known_citations for part in str(value).split("\n"))).all()
    return bool(conflict_text_ok and checklist_citation_ok), f"conflict_texts={conflict_text_ok}; checklist_citations={checklist_citation_ok}"


def _test_review(conflicts: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    passed = (
        not conflicts.empty
        and not checklist.empty
        and conflicts["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        and checklist["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
    )
    return bool(passed), f"conflicts_reviewed={conflicts['review_status'].eq('NEEDS_HUMAN_REVIEW').all()}; checklist_reviewed={checklist['review_status'].eq('NEEDS_HUMAN_REVIEW').all()}"


def _test_audit_privacy() -> tuple[bool, str]:
    if not AUDIT_LOG_PATH.is_file():
        return False, "audit_log.jsonl is missing"
    raw = AUDIT_LOG_PATH.read_text(encoding="utf-8")
    events = []
    for line in raw.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            return False, "invalid JSON Lines entry"
    key_names_ok = not any(any(term in str(key).casefold() for term in SENSITIVE_TERMS) for event in events for key in event)
    values_ok = not any(any(term in str(value).casefold() for term in SENSITIVE_TERMS) for event in events for value in event.values())
    return bool(events and key_names_ok and values_ok), f"events={len(events)}; sensitive_field_names={not key_names_ok}; sensitive_values={not values_ok}"


def _test_unknown_domain() -> tuple[bool, str]:
    try:
        generate_checklist("Domain không tồn tại", "Khối CNTT", user_role="Admin", use_llm=False)
    except LookupError as error:
        message = str(error)
        return "Chưa có dữ liệu quy định" in message, message
    return False, "unknown domain did not raise LookupError"


def _test_exports(conflicts: pd.DataFrame, checklist: pd.DataFrame) -> tuple[bool, str]:
    passed = list(conflicts.columns) == RESULT_COLUMNS and list(checklist.columns) == CHECKLIST_COLUMNS
    return bool(passed), f"conflict_schema={list(conflicts.columns) == RESULT_COLUMNS}; checklist_schema={list(checklist.columns) == CHECKLIST_COLUMNS}"


def run_tests() -> bool:
    corpus = load_corpus()
    conflicts = pd.read_csv(RESULTS_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    checklist = pd.read_csv(CHECKLIST_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    tests = [
        ("RBAC restricted access", *_test_rbac(corpus)),
        ("Citation integrity", *_test_citations(corpus, conflicts, checklist)),
        ("Hallucination check", *_test_hallucination(corpus, conflicts, checklist)),
        ("Human review guardrail", *_test_review(conflicts, checklist)),
        ("Audit log privacy", *_test_audit_privacy()),
        ("Unknown domain", *_test_unknown_domain()),
        ("File export verification", *_test_exports(conflicts, checklist)),
    ]
    report_lines = [
        "# Security & Guardrail Test Report - Buoi 18",
        "",
        "Kiểm thử trên artifact UC3/UC4 hiện có; dữ liệu nguồn được đọc read-only.",
        "",
        "| Test | Status | Detail |",
        "|---|---|---|",
    ]
    for name, passed, detail in tests:
        report_lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {detail} |")
    passed_count = sum(result[1] for result in tests)
    failed_count = len(tests) - passed_count
    overall = failed_count == 0
    report_lines.extend(
        [
            "",
            f"Passed: `{passed_count}`; Failed: `{failed_count}`",
            "",
            "```text",
            f"SECURITY & GUARDRAIL TESTS: {'PASS' if overall else 'FAIL'}",
            "```",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"SECURITY_TESTS_PASSED={passed_count}")
    print(f"SECURITY_TESTS_FAILED={failed_count}")
    print(f"SECURITY_TESTS={'PASS' if overall else 'FAIL'}")
    return overall


if __name__ == "__main__":
    raise SystemExit(0 if run_tests() else 1)
