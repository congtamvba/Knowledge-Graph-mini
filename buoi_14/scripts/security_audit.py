from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import VALID_ROLES
from src.secure_retriever import parse_allowed_roles, user_has_access

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "security_audit_report.md"


def load_secure_csv(path: Path = INPUT_PATH) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Secure corpus not found: {path}")
    corpus = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    required = {"chunk_id", "document_id", "text", "allowed_roles"}
    missing = sorted(required - set(corpus.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return corpus


def chunk_visible_to_roles(corpus: pd.DataFrame, chunk_id: str, user_roles: list[str]) -> bool:
    row = corpus[corpus["chunk_id"].astype(str) == str(chunk_id)]
    if row.empty:
        return False
    entry = row.iloc[0]
    try:
        allowed_roles = parse_allowed_roles(entry["allowed_roles"])
    except ValueError:
        return False
    return any(role in allowed_roles for role in user_roles)


def run_security_audit() -> dict[str, object]:
    corpus = load_secure_csv()
    test_cases = [
        {
            "name": "guest_cannot_see_restricted_chunk_117310_0001",
            "query": "Quy định nội bộ về kiểm soát dữ liệu nhạy cảm",
            "target_chunk_id": "117310-chunk-0001",
            "unauthorized_roles": ["Guest"],
            "authorized_roles": ["Admin", "Risk_Officer", "Employee"],
        },
        {
            "name": "hr_manager_cannot_see_restricted_chunk_44209_0001",
            "query": "Hạn mức tín dụng và tiêu chí đánh giá rủi ro",
            "target_chunk_id": "44209-chunk-0001",
            "unauthorized_roles": ["HR_Manager"],
            "authorized_roles": ["Admin", "Risk_Officer", "Employee"],
        },
        {
            "name": "guest_cannot_see_restricted_chunk_173695_0001",
            "query": "Chính sách nội bộ và quyền truy cập dữ liệu",
            "target_chunk_id": "173695-chunk-0001",
            "unauthorized_roles": ["Guest"],
            "authorized_roles": ["Admin", "Risk_Officer", "Employee"],
        },
        {
            "name": "hr_manager_cannot_see_restricted_chunk_168220_0001",
            "query": "Dữ liệu giám sát và kiểm soát rủi ro",
            "target_chunk_id": "168220-chunk-0001",
            "unauthorized_roles": ["HR_Manager"],
            "authorized_roles": ["Admin", "Risk_Officer", "Employee"],
        },
        {
            "name": "guest_cannot_see_restricted_chunk_185630_0001",
            "query": "Quy trình nội bộ và chính sách bảo mật",
            "target_chunk_id": "185630-chunk-0001",
            "unauthorized_roles": ["Guest"],
            "authorized_roles": ["Admin", "Risk_Officer", "Employee"],
        },
    ]

    passed = 0
    failed = 0
    details: list[dict[str, object]] = []

    for case in test_cases:
        chunk_id = case["target_chunk_id"]
        unauthorized_roles = case["unauthorized_roles"]
        authorized_roles = case["authorized_roles"]

        unauthorized_visible = chunk_visible_to_roles(corpus, chunk_id, unauthorized_roles)
        authorized_visible = chunk_visible_to_roles(corpus, chunk_id, authorized_roles)

        if unauthorized_visible:
            status = "FAIL"
            failed += 1
        else:
            status = "PASS"
            passed += 1

        details.append(
            {
                "name": case["name"],
                "query": case["query"],
                "chunk_id": chunk_id,
                "unauthorized_roles": unauthorized_roles,
                "authorized_roles": authorized_roles,
                "unauthorized_visible": unauthorized_visible,
                "authorized_visible": authorized_visible,
                "status": status,
            }
        )

    report_lines = [
        "# SECURITY AUDIT REPORT",
        "",
        f"- Input: {INPUT_PATH}",
        f"- Valid roles: {', '.join(VALID_ROLES)}",
        f"- Total test cases: {len(test_cases)}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Security status: {'PASS' if failed == 0 else 'FAIL'}",
        "",
        "## Test Details",
        "",
    ]

    for item in details:
        report_lines.append(f"### {item['name']}")
        report_lines.append(f"- Query: {item['query']}")
        report_lines.append(f"- Chunk ID: {item['chunk_id']}")
        report_lines.append(f"- Unauthorized roles: {item['unauthorized_roles']}")
        report_lines.append(f"- Authorized roles: {item['authorized_roles']}")
        report_lines.append(f"- Unauthorized visible: {item['unauthorized_visible']}")
        report_lines.append(f"- Authorized visible: {item['authorized_visible']}")
        report_lines.append(f"- Status: {item['status']}")
        report_lines.append("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "total": len(test_cases),
        "passed": passed,
        "failed": failed,
        "status": "PASS" if failed == 0 else "FAIL",
        "details": details,
    }


if __name__ == "__main__":
    result = run_security_audit()
    print("SECURITY AUDIT REPORT")
    print(f"- Input: {INPUT_PATH}")
    print(f"- Valid roles: {', '.join(VALID_ROLES)}")
    print(f"- Total test cases: {result['total']}")
    print(f"- Passed: {result['passed']}")
    print(f"- Failed: {result['failed']}")
    print(f"- Security status: {result['status']}")
