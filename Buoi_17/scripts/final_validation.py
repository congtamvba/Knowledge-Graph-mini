from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_17_ROOT = SCRIPT_ROOT.parent
WORKSPACE_ROOT = BUOI_17_ROOT.parent
SOURCE_FILES = [
    WORKSPACE_ROOT / "buoi_16" / "data" / "processed" / "chunks_secure.csv",
    WORKSPACE_ROOT / "buoi_16" / "data" / "processed" / "chunks_normalized.csv",
]
REPORT_PATH = BUOI_17_ROOT / "outputs" / "final_validation_report.md"


class FinalValidator:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.results.append((name, "PASS" if passed else "FAIL", detail))

    def run(self) -> bool:
        self.validate_source_data()
        self.validate_secure_retrieval()
        self.validate_audit()
        self.validate_citation()
        self.validate_gap_guardrail()
        self.validate_human_review()
        self.validate_streamlit()
        self.validate_neo4j()
        self.validate_test_suite()
        self.write_report()
        failed = [result for result in self.results if result[1] == "FAIL"]
        print(f"FINAL_VALIDATION={'PASS' if not failed else 'FAIL'}")
        print(f"PASSED={len(self.results) - len(failed)}")
        print(f"FAILED={len(failed)}")
        return not failed

    def validate_source_data(self) -> None:
        exists = all(path.is_file() for path in SOURCE_FILES)
        git_status = subprocess.run(
            ["git", "status", "--short", "--", "buoi_16/data/processed/chunks_secure.csv", "buoi_16/data/processed/chunks_normalized.csv"],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip().splitlines()
        modified_or_deleted = [line for line in git_status if line[:2].strip() in {"M", "D", "A"}]
        self.add(
            "workspace isolation",
            exists and not modified_or_deleted,
            "Source files exist and are not marked modified/deleted; untracked baseline is preserved if present",
        )

    def validate_secure_retrieval(self) -> None:
        adapter_path = BUOI_17_ROOT / "scripts" / "secure_retrieval_adapter.py"
        source = adapter_path.read_text(encoding="utf-8") if adapter_path.is_file() else ""
        self.add(
            "secure retrieval",
            "filter_secure_corpus" in source and "BM25Retriever" in source,
            "Adapter reuses RBAC filter and existing BM25 retriever",
        )
        self.add(
            "RBAC before retrieval",
            source.find("visible = filter_secure_corpus") < source.find("BM25Retriever(authorized_corpus)"),
            "RBAC filter is applied before constructing/searching BM25",
        )

    def validate_audit(self) -> None:
        path = BUOI_17_ROOT / "outputs" / "audit_log.jsonl"
        events = []
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        required = {"timestamp_utc", "request_id", "user_id_demo", "user_role", "action", "query", "retrieval_method", "retrieved_document_ids", "retrieved_chunk_ids", "citation_ids", "rbac_filtered_candidate_count", "status"}
        complete = bool(events) and all(required <= set(event) for event in events)
        statuses = {event.get("status") for event in events}
        secret_terms = ("password", "api_key", "apikey", "secret", "token")
        no_secrets = not any(term in path.read_text(encoding="utf-8").casefold() for term in secret_terms) if path.is_file() else False
        self.add("audit trail", complete and {"SUCCESS", "DENIED"} <= statuses and no_secrets, f"events={len(events)}; statuses={sorted(statuses)}")

    def validate_citation(self) -> None:
        path = BUOI_17_ROOT / "outputs" / "internal_lookup_demo.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        self.add("citation", "CITATION: PASS" in text and text.count("## Request ") >= 3 and "### Citations" in text, "Internal lookup report contains three requests and citations")

    def validate_gap_guardrail(self) -> None:
        path = BUOI_17_ROOT / "outputs" / "compliance_gap_report.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        results_path = BUOI_17_ROOT / "outputs" / "compliance_gap_results.csv"
        results = pd.read_csv(results_path, dtype=str, keep_default_na=False, encoding="utf-8") if results_path.is_file() else pd.DataFrame()
        valid_classifications = {"DAP_UNG", "THIEU", "CHENH_LECH", "CHUA_DU_BANG_CHUNG"}
        classifications_ok = not results.empty and results["classification"].isin(valid_classifications).all()
        evidence_ok = not results.empty and results.apply(
            lambda row: bool(str(row["external_citation"]).strip()) and bool(str(row["internal_citation"]).strip()),
            axis=1,
        ).all()
        self.add("compliance gap", "GAP CHECKER: PASS" in text and classifications_ok and evidence_ok, f"rows={len(results)}; valid_classifications={classifications_ok}; citations={evidence_ok}")

    def validate_human_review(self) -> None:
        path = BUOI_17_ROOT / "outputs" / "compliance_gap_report.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        results_path = BUOI_17_ROOT / "outputs" / "compliance_gap_results.csv"
        results = pd.read_csv(results_path, dtype=str, keep_default_na=False, encoding="utf-8") if results_path.is_file() else pd.DataFrame()
        reviewed = not results.empty and results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        self.add("human review guardrail", "HUMAN REVIEW REQUIRED: YES" in text and reviewed, f"all_reviewed={reviewed}")

    def validate_streamlit(self) -> None:
        try:
            with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=5) as response:
                body = response.read().decode("utf-8").strip()
            self.add("streamlit", response.status == 200 and body == "ok", f"health_status={response.status}; body={body}")
        except Exception as error:
            self.add("streamlit", False, f"health check failed: {type(error).__name__}")

    def validate_neo4j(self) -> None:
        load_dotenv(BUOI_17_ROOT / ".env", override=False)
        values = [os.getenv(name) for name in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE")]
        if not all(values):
            self.add("neo4j", False, "Neo4j configuration is incomplete")
            return
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(values[0], auth=(values[1], values[2]))
            try:
                driver.verify_connectivity()
            finally:
                driver.close()
            self.add("neo4j", True, "verify_connectivity succeeded")
        except Exception as error:
            self.add("neo4j", False, f"truthful runtime status: {type(error).__name__}")

    def validate_test_suite(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=WORKSPACE_ROOT / "buoi_14",
            capture_output=True,
            text=True,
            check=False,
        )
        self.add("existing test suite", result.returncode == 0, "Buoi 14 unittest discovery completed")

    def write_report(self) -> None:
        passed = sum(status == "PASS" for _, status, _ in self.results)
        failed = len(self.results) - passed
        overall = "PASS" if failed == 0 else "FAIL"
        lines = [
            "# Final Validation Report - Buoi 17",
            "",
            "Kiem tra read-only cac artifact Buoi 17, source isolation, runtime service va test suite.",
            "",
            "| Criterion | Status | Detail |",
            "|---|---|---|",
        ]
        lines.extend(f"| {name} | {status} | {detail} |" for name, status, detail in self.results)
        lines.extend(
            [
                "",
                f"Passed: `{passed}`; Failed: `{failed}`",
                "",
                "```text",
                f"RBAC: {'PASS' if self._passed('RBAC before retrieval') else 'FAIL'}",
                f"SECURE RETRIEVAL: {'PASS' if self._passed('secure retrieval') else 'FAIL'}",
                f"AUDIT TRAIL: {'PASS' if self._passed('audit trail') else 'FAIL'}",
                f"CITATION: {'PASS' if self._passed('citation') else 'FAIL'}",
                f"COMPLIANCE GAP: {'PASS' if self._passed('compliance gap') else 'FAIL'}",
                f"HUMAN REVIEW GUARDRAIL: {'PASS' if self._passed('human review guardrail') else 'FAIL'}",
                f"STREAMLIT: {'PASS' if self._passed('streamlit') else 'FAIL'}",
                f"WORKSPACE ISOLATION: {'PASS' if self._passed('workspace isolation') else 'FAIL'}",
                "READY FOR DEMO: YES" if overall == "PASS" else "READY FOR DEMO: NO",
                "```",
                "",
            ]
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    def _passed(self, name: str) -> bool:
        return any(test_name == name and status == "PASS" for test_name, status, _ in self.results)


if __name__ == "__main__":
    raise SystemExit(0 if FinalValidator().run() else 1)
