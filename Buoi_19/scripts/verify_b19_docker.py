from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from audit_checklist_gen import run_demo as run_checklist_demo
from compliance_checker import run_checker
from engine_support import AUDIT_LOG_PATH, load_environment
from ollama_adapter import OllamaClient

COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"
DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
REPORT_PATH = PROJECT_ROOT / "outputs" / "b19_docker_acceptance_report.md"


class B19DockerValidator:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []

    def check(self, name: str, passed: bool, detail: str) -> None:
        self.results.append((name, "PASS" if passed else "FAIL", detail))

    def run(self) -> bool:
        self.validate_ollama_connectivity()
        self.validate_model_availability()
        self.validate_dual_provider_switch()
        self.validate_docker_packaging()
        self.validate_local_engines()
        self.validate_guardrails_and_audit()
        self.write_report()
        failed = [result for result in self.results if result[1] == "FAIL"]
        print(f"FINAL_VALIDATION={'PASS' if not failed else 'FAIL'}")
        print(f"PASSED={len(self.results) - len(failed)}")
        print(f"FAILED={len(failed)}")
        return not failed

    def validate_ollama_connectivity(self) -> None:
        client = OllamaClient()
        health = client.check_health()
        self.check(
            "Ollama Server Connectivity",
            bool(health["online"]),
            f"base_url={client.base_url}; api_tags_online={health['online']}",
        )

    def validate_model_availability(self) -> None:
        health = OllamaClient().check_health()
        compatible = any(name.startswith(("qwen3:0.6b", "qwen2.5:")) for name in health["models"])
        self.check(
            "Local Model Availability",
            compatible,
            f"configured={health['configured_model']}; registered_models={', '.join(health['models']) or 'none'}",
        )

    def validate_dual_provider_switch(self) -> None:
        original = os.environ.get("LLM_PROVIDER")
        try:
            os.environ["LLM_PROVIDER"] = "ollama"
            ollama_selected = load_environment() == "ollama"
            os.environ["LLM_PROVIDER"] = "gemini"
            gemini_selected = load_environment() == "gemini"
        finally:
            if original is None:
                os.environ.pop("LLM_PROVIDER", None)
            else:
                os.environ["LLM_PROVIDER"] = original
        self.check(
            "Dual Provider Switch",
            ollama_selected and gemini_selected,
            f"ollama_selected={ollama_selected}; gemini_selected={gemini_selected}; runtime_default={load_environment()}",
        )

    def validate_docker_packaging(self) -> None:
        config = subprocess.run(
            ["docker", "compose", "config", "--quiet"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            with urlopen("http://localhost:8501/_stcore/health", timeout=15) as response:
                streamlit_ready = response.status == 200 and response.read().decode("utf-8").strip() == "ok"
        except OSError:
            streamlit_ready = False
        source_ok = DOCKERFILE_PATH.is_file() and COMPOSE_PATH.is_file()
        self.check(
            "Docker Compose Packaging",
            source_ok and config.returncode == 0 and streamlit_ready,
            f"files_present={source_ok}; compose_config_exit={config.returncode}; streamlit_ready={streamlit_ready}",
        )

    def validate_local_engines(self) -> None:
        results = run_checker(user_role="Admin")
        checklist = run_checklist_demo()
        compliance_ok = not results.empty and results["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        checklist_ok = not checklist.empty and checklist["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        self.check(
            "Local UC3 & UC4 Engines",
            compliance_ok and checklist_ok,
            f"uc3_results={len(results)}; uc4_items={len(checklist)}; provider={load_environment()}",
        )

    def validate_guardrails_and_audit(self) -> None:
        compliance_path = PROJECT_ROOT / "outputs" / "compliance_conflicts.csv"
        checklist_path = PROJECT_ROOT / "outputs" / "audit_checklist_results.csv"
        compliance = pd.read_csv(compliance_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        checklist = pd.read_csv(checklist_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        citations_ok = (
            not compliance.empty
            and not checklist.empty
            and compliance[["doc_a_citation", "doc_b_citation"]].apply(lambda column: column.str.strip().ne("").all()).all()
            and checklist["source_citation"].str.strip().ne("").all()
        )
        reviews_ok = compliance["review_status"].eq("NEEDS_HUMAN_REVIEW").all() and checklist["review_status"].eq("NEEDS_HUMAN_REVIEW").all()
        events = []
        if AUDIT_LOG_PATH.is_file():
            for line in AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        required = {"timestamp_utc", "request_id", "user_role", "action", "query", "citation_ids", "status"}
        audit_ok = bool(events) and all(required <= set(event) for event in events)
        secret_values = [value for value in (os.getenv("GEMINI_API_KEY"), os.getenv("LLM_API_KEY"), os.getenv("NEO4J_PASSWORD")) if value and not value.startswith("YOUR_")]
        secrets_absent = not any(value in AUDIT_LOG_PATH.read_text(encoding="utf-8") for value in secret_values) if AUDIT_LOG_PATH.is_file() else False
        self.check(
            "Human Review & Audit Log",
            citations_ok and reviews_ok and audit_ok and secrets_absent,
            f"citations={citations_ok}; reviews={reviews_ok}; audit_events={len(events)}; audit_schema={audit_ok}; secrets_absent={secrets_absent}",
        )

    def write_report(self) -> None:
        passed = sum(status == "PASS" for _, status, _ in self.results)
        failed = len(self.results) - passed
        overall = failed == 0
        lines = [
            "# Docker Acceptance Report - Buoi 19",
            "",
            "Final validation of the local Ollama, Streamlit, engine, guardrail, and audit artifacts.",
            "",
            "| Criterion | Status | Detail |",
            "|---|---|---|",
            *[f"| {name} | {status} | {detail} |" for name, status, detail in self.results],
            "",
            "```text",
            f"OLLAMA SERVER STATUS: {'PASS' if self._passed('Ollama Server Connectivity') else 'FAIL'}",
            f"LOCAL MODEL QWEN3: {'PASS' if self._passed('Local Model Availability') else 'FAIL'}",
            f"DOCKER CONTAINERIZATION: {'PASS' if self._passed('Docker Compose Packaging') else 'FAIL'}",
            f"LOCAL COMPLIANCE ENGINES: {'PASS' if self._passed('Local UC3 & UC4 Engines') else 'FAIL'}",
            "",
            f"LOCAL AI SYSTEM READY: {'YES' if overall else 'NO'}",
            "```",
            "",
        ]
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    def _passed(self, name: str) -> bool:
        return any(result_name == name and status == "PASS" for result_name, status, _ in self.results)


if __name__ == "__main__":
    raise SystemExit(0 if B19DockerValidator().run() else 1)
