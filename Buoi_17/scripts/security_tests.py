from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

import pandas as pd
from dotenv import load_dotenv

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_17_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_17_ROOT.parent
SECURE_PATH = BUOI_17_ROOT / "data" / "chunks_combined_secure.csv"
AUDIT_PATH = BUOI_17_ROOT / "outputs" / "audit_log.jsonl"
GAP_REPORT_PATH = BUOI_17_ROOT / "outputs" / "compliance_gap_report.md"
RESULTS_PATH = BUOI_17_ROOT / "outputs" / "compliance_gap_results.csv"
REPORT_PATH = BUOI_17_ROOT / "outputs" / "security_test_report.md"

if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from secure_retrieval_adapter import SecureRetrievalAdapter


class SecurityTestRunner:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []

    def check(self, name: str, passed: bool, detail: str) -> None:
        self.results.append((name, "PASS" if passed else "FAIL", detail))

    def run(self) -> bool:
        corpus = pd.read_csv(SECURE_PATH, dtype=str, keep_default_na=False, encoding="utf-8")
        adapter = SecureRetrievalAdapter(SECURE_PATH)
        query = "quy dinh giao nhan bao quan van chuyen tien mat"

        allowed = adapter.retrieve(query, "Guest", top_k=3)
        self.check("allowed role", not allowed.empty, "Guest nhan duoc ket qua authorized")

        restricted = corpus[corpus["allowed_roles"].map(lambda value: "Guest" not in json.loads(value))]
        restricted_row = restricted.iloc[0]
        denied_context = adapter.retrieve(str(restricted_row["title"]), "Guest", top_k=10)
        denied_ids = set(denied_context["chunk_id"]) if "chunk_id" in denied_context.columns else set()
        self.check(
            "unauthorized role cannot see restricted text/citation",
            restricted_row["chunk_id"] not in denied_ids,
            f"chunk={restricted_row['chunk_id']}; guest_context_contains_target={restricted_row['chunk_id'] in denied_ids}",
        )

        self.check(
            "restricted chunk excluded from LLM context",
            all("Guest" in json.loads(value) for value in allowed["allowed_roles"]),
            "Moi chunk trong tap context Guest deu co Guest trong allowed_roles",
        )

        unknown = adapter.retrieve(query, "Unknown", top_k=3)
        self.check("unknown role default deny", unknown.empty, "Unknown khong co chunk authorized")

        audit_events = []
        if AUDIT_PATH.is_file():
            for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
                try:
                    audit_events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        statuses = {event.get("status") for event in audit_events}
        self.check("audit SUCCESS and DENIED", {"SUCCESS", "DENIED"} <= statuses, f"statuses={sorted(statuses)}")
        audit_text = AUDIT_PATH.read_text(encoding="utf-8") if AUDIT_PATH.is_file() else ""
        secret_found = any(term in audit_text.casefold() for term in ("password", "api_key", "apikey", "secret", "token"))
        self.check("audit log contains no secret", not secret_found, "Khong tim thay ten truong secret trong audit log")

        citation_ok = not allowed.empty and allowed["citation"].astype(str).str.strip().ne("").all()
        self.check("citation exists", citation_ok, "Citation ton tai trong moi ket qua allowed")

        gap_report = GAP_REPORT_PATH.read_text(encoding="utf-8") if GAP_REPORT_PATH.is_file() else ""
        results_exist = RESULTS_PATH.is_file()
        gap_results = pd.read_csv(RESULTS_PATH, dtype=str, keep_default_na=False, encoding="utf-8") if results_exist else pd.DataFrame()
        evidence_ok = results_exist and not gap_results.empty and all(
            (row["classification"] == "CHUA_DU_BANG_CHUNG")
            or (str(row["external_citation"]).strip() and str(row["internal_citation"]).strip())
            for _, row in gap_results.iterrows()
        )
        self.check(
            "gap has evidence or data-gap status",
            evidence_ok,
            f"rows={len(gap_results)}; evidence_or_unknown={evidence_ok}",
        )
        all_reviewed = results_exist and not gap_results.empty and gap_results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        self.check(
            "all gap results require human review",
            all_reviewed,
            f"all_reviewed={all_reviewed}",
        )

        neo4j_status, neo4j_detail = self._neo4j_truth_check()
        self.check("Neo4j reports truthful status", neo4j_status in {"READY", "UNAVAILABLE", "NOT_CONFIGURED"}, neo4j_detail)

        report_lines = [
            "# Security Test Report - Buoi 17",
            "",
            "Kiem thu read-only tren secure corpus, adapter, audit log, gap report va Neo4j runtime.",
            "",
            "| Test | Status | Detail |",
            "|---|---|---|",
        ]
        report_lines.extend(f"| {name} | {status} | {detail} |" for name, status, detail in self.results)
        passed = sum(status == "PASS" for _, status, _ in self.results)
        failed = len(self.results) - passed
        overall = "PASS" if failed == 0 else "FAIL"
        report_lines.extend(
            [
                "",
                f"Passed: `{passed}`; Failed: `{failed}`",
                "",
                "```text",
                f"SECURITY TESTS: {overall}",
                "```",
                "",
            ]
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"SECURITY_TESTS={overall}")
        print(f"PASSED={passed}")
        print(f"FAILED={failed}")
        return failed == 0

    @staticmethod
    def _neo4j_truth_check() -> tuple[str, str]:
        load_dotenv(BUOI_17_ROOT / ".env", override=False)
        required = [os.getenv(name) for name in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE")]
        if not all(required):
            return "NOT_CONFIGURED", "Neo4j variables chua day du"
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(required[0], auth=(required[1], required[2]))
            try:
                driver.verify_connectivity()
            finally:
                driver.close()
            return "READY", "verify_connectivity thanh cong"
        except Exception as error:
            return "UNAVAILABLE", f"Bao cao that: {type(error).__name__}"


if __name__ == "__main__":
    sys.exit(0 if SecurityTestRunner().run() else 1)
