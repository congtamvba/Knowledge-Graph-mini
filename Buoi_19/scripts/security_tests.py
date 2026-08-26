from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pandas as pd

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from audit_checklist_gen import run_demo as run_checklist_demo
from compliance_checker import load_corpus, run_checker
from engine_support import AUDIT_LOG_PATH, ENV_PATH, authorized_corpus, load_environment

REPORT_PATH = PROJECT_ROOT / "outputs" / "b19_security_test_report.md"


class SecurityTestRunner:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []

    def check(self, name: str, passed: bool, detail: str) -> None:
        self.results.append((name, "PASS" if passed else "FAIL", detail))

    def run(self) -> bool:
        self.check_local_provider_path()
        self.check_rbac_enforcement()
        compliance_results = run_checker(user_role="Staff")
        checklist_results = run_checklist_demo()
        self.check_citation_integrity(compliance_results, checklist_results)
        self.check_human_review(compliance_results, checklist_results)
        self.check_audit_log_privacy()
        self.check_local_model_resilience()
        self.write_report()
        failed = [result for result in self.results if result[1] == "FAIL"]
        print(f"SECURITY_TESTS={'PASS' if not failed else 'FAIL'}")
        print(f"PASSED={len(self.results) - len(failed)}")
        print(f"FAILED={len(failed)}")
        return not failed

    def check_local_provider_path(self) -> None:
        source = (SCRIPT_ROOT / "engine_support.py").read_text(encoding="utf-8")
        provider = load_environment()
        base_url = os.getenv("OLLAMA_BASE_URL", "")
        local_path = provider == "ollama" and base_url in {"http://localhost:11434", "http://ollama:11434"}
        guarded = 'if provider == "ollama"' in source and "OllamaClient().generate" in source
        self.check(
            "local prompt routing",
            local_path and guarded,
            f"provider={provider}; base_url={base_url}; Ollama branch present={guarded}",
        )

    def check_rbac_enforcement(self) -> None:
        corpus = load_corpus()
        restricted = corpus[~corpus["allowed_roles"].map(self._has_staff_access)]
        visible = authorized_corpus(corpus, "Staff")
        restricted_ids = set(restricted["chunk_id"])
        leaked = restricted_ids & set(visible["chunk_id"])
        self.check(
            "RBAC Staff exclusion",
            bool(restricted_ids) and not leaked,
            f"restricted_chunks={len(restricted_ids)}; leaked_chunks={len(leaked)}",
        )

    def check_citation_integrity(self, compliance: pd.DataFrame, checklist: pd.DataFrame) -> None:
        corpus = load_corpus()
        known = set(corpus["citation"].astype(str).str.strip())
        compliance_ok = not compliance.empty and compliance["doc_a_citation"].isin(known).all() and compliance["doc_b_citation"].isin(known).all()
        checklist_ok = not checklist.empty and checklist["source_citation"].map(
            lambda value: all(part.strip() in known for part in str(value).split("\n") if part.strip())
        ).all()
        self.check("citation integrity", compliance_ok and checklist_ok, f"uc3={compliance_ok}; uc4={checklist_ok}")

    def check_human_review(self, compliance: pd.DataFrame, checklist: pd.DataFrame) -> None:
        passed = (
            not compliance.empty
            and not checklist.empty
            and compliance["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
            and checklist["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        )
        self.check("human review guardrail", passed, f"uc3_rows={len(compliance)}; uc4_rows={len(checklist)}")

    def check_audit_log_privacy(self) -> None:
        text = AUDIT_LOG_PATH.read_text(encoding="utf-8") if AUDIT_LOG_PATH.is_file() else ""
        sensitive_values = [
            value for value in (os.getenv("GEMINI_API_KEY"), os.getenv("LLM_API_KEY"), os.getenv("NEO4J_PASSWORD"))
            if value and not value.startswith("YOUR_")
        ]
        values_absent = all(value not in text for value in sensitive_values)
        unredacted_assignment = any(
            marker in text.casefold()
            for marker in ("api_key=", "token=", "secret=", "password=")
        )
        self.check(
            "audit log privacy",
            values_absent and not unredacted_assignment,
            f"events={len(text.splitlines())}; configured_secret_values_absent={values_absent}; unredacted_assignments={unredacted_assignment}",
        )

    def check_local_model_resilience(self) -> None:
        command = ["docker", "exec", "agribank-ollama-server", "ollama", "run", "qwen3:0.6b", "Reply with OK only"]
        result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False, timeout=90)
        self.check(
            "local model resilience",
            result.returncode == 0 and bool(result.stdout.strip()),
            f"exit_code={result.returncode}; response_received={bool(result.stdout.strip())}; model runs from persistent local volume",
        )

    def write_report(self) -> None:
        passed = sum(status == "PASS" for _, status, _ in self.results)
        failed = len(self.results) - passed
        lines = [
            "# Security & Local Guardrail Test Report - Buoi 19",
            "",
            "The tests verify the configured Ollama-only prompt path, RBAC data filtering, output guardrails, audit redaction, and a local model invocation.",
            "",
            "| Test | Status | Detail |",
            "|---|---|---|",
            *[f"| {name} | {status} | {detail} |" for name, status, detail in self.results],
            "",
            "## Infrastructure Note",
            "",
            "The application is configured to send prompts only to the local Ollama endpoint while `LLM_PROVIDER=ollama`. Docker's standard bridge network remains enabled to preserve host access to Streamlit and model-management operations; a physically air-gapped deployment requires host firewall or network-policy enforcement outside this Compose file.",
            "",
            "```text",
            f"SECURITY TESTS: {'PASS' if failed == 0 else 'FAIL'}",
            f"PASSED: {passed}",
            f"FAILED: {failed}",
            "```",
            "",
        ]
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _has_staff_access(value: object) -> bool:
        try:
            return "Staff" in {str(role).strip() for role in json.loads(str(value))}
        except (TypeError, json.JSONDecodeError):
            return False


if __name__ == "__main__":
    raise SystemExit(0 if SecurityTestRunner().run() else 1)
