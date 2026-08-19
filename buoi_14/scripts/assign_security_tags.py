from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    ADMIN,
    EMPLOYEE,
    GUEST,
    HR_MANAGER,
    RISK_OFFICER,
    VALID_ROLES,
    validate_roles,
)


DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"
REQUIRED_COLUMNS = {"document_id", "text"}

HR_TERMS = (
    "nhân sự",
    "lương",
    "lương thưởng",
    "tuyển dụng",
    "bổ nhiệm",
    "kỷ luật",
    "hồ sơ nhân sự",
    "chế độ nhân viên",
)
RISK_TERMS = (
    "tín dụng",
    "rủi ro",
    "hạn mức",
    "phê duyệt vay",
    "phê duyệt tín dụng",
    "khoản vay",
    "quản trị rủi ro",
)

HR_ROLES = (ADMIN, HR_MANAGER)
RISK_ROLES = (ADMIN, RISK_OFFICER, EMPLOYEE)
GENERAL_ROLES = VALID_ROLES

HR_GROUP = "HR"
RISK_GROUP = "RISK"
GENERAL_GROUP = "GENERAL"
GROUP_ORDER = (HR_GROUP, RISK_GROUP, GENERAL_GROUP)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign RBAC allowed_roles to every normalized chunk."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_corpus(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Normalized corpus not found: {path}")

    corpus = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing_columns = REQUIRED_COLUMNS - set(corpus.columns)
    if missing_columns:
        raise ValueError(f"Corpus is missing required columns: {sorted(missing_columns)}")
    if corpus.empty:
        raise ValueError("Normalized corpus is empty")
    return corpus


def contains_any_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    normalized_value = re.sub(r"[-_/]+", " ", str(value).casefold())
    normalized_value = re.sub(r"\s+", " ", normalized_value)
    return any(keyword.casefold() in normalized_value for keyword in keywords)


def classify_chunk(document_id: str, text: str) -> tuple[str, tuple[str, ...]]:
    searchable_value = f"{document_id} {text}"
    if contains_any_keyword(searchable_value, HR_TERMS):
        return HR_GROUP, validate_roles(HR_ROLES)
    if contains_any_keyword(searchable_value, RISK_TERMS):
        return RISK_GROUP, validate_roles(RISK_ROLES)
    return GENERAL_GROUP, validate_roles(GENERAL_ROLES)


def encode_roles(roles: tuple[str, ...]) -> str:
    return json.dumps(roles, ensure_ascii=False)


def parse_allowed_roles(value: str) -> tuple[str, ...]:
    try:
        roles = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"allowed_roles is not valid JSON: {value!r}") from error
    if not isinstance(roles, list) or not roles:
        raise ValueError("allowed_roles must be a non-empty JSON array")
    if not all(isinstance(role, str) for role in roles):
        raise ValueError("Every allowed role must be a string")
    return validate_roles(roles)


def assign_security_tags(corpus: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    decisions = corpus.apply(
        lambda row: classify_chunk(row["document_id"], row["text"]),
        axis=1,
    )
    secure_corpus = corpus.copy(deep=True)
    secure_corpus["allowed_roles"] = decisions.map(lambda item: encode_roles(item[1]))
    groups = decisions.map(lambda item: item[0])
    validate_secure_corpus(corpus, secure_corpus)
    return secure_corpus, groups


def validate_secure_corpus(source: pd.DataFrame, secure: pd.DataFrame) -> None:
    if "allowed_roles" not in secure.columns:
        raise ValueError("Secure corpus is missing allowed_roles")
    expected_columns = source.columns.tolist() + ["allowed_roles"]
    if secure.columns.tolist() != expected_columns:
        raise ValueError("Secure corpus must preserve source columns and only add allowed_roles")
    if len(source) != len(secure):
        raise ValueError("Row count changed during security tagging")
    if secure["allowed_roles"].isna().any() or secure["allowed_roles"].str.strip().eq("").any():
        raise ValueError("allowed_roles contains null or empty values")

    secure["allowed_roles"].map(parse_allowed_roles)
    for column in source.columns:
        if not source[column].equals(secure[column]):
            raise ValueError(f"Original column was modified: {column}")


def validate_written_output(
    source: pd.DataFrame,
    output_path: Path,
) -> tuple[pd.DataFrame, int, set[str]]:
    written = pd.read_csv(
        output_path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
    )
    validate_secure_corpus(source, written)
    parsed_roles = written["allowed_roles"].map(parse_allowed_roles)
    empty_count = int(parsed_roles.map(len).eq(0).sum())
    invalid_roles = {
        role for roles in parsed_roles for role in roles if role not in VALID_ROLES
    }
    return written, empty_count, invalid_roles


def print_sample(corpus: pd.DataFrame, groups: pd.Series, group: str) -> None:
    matches = corpus.loc[groups == group, ["document_id", "text", "allowed_roles"]]
    if matches.empty:
        print(f"Sample {group}: NOT AVAILABLE - no real rows matched this group")
        return
    record = matches.iloc[0].to_dict()
    record["text"] = str(record["text"])[:300]
    print(f"Sample {group}: {record}")


def print_report(
    source: pd.DataFrame,
    secure: pd.DataFrame,
    groups: pd.Series,
    input_path: Path,
    output_path: Path,
    input_hash_before: str,
    input_hash_after: str,
    empty_count: int,
    invalid_roles: set[str],
) -> None:
    group_counts = Counter(groups)
    parsed_roles = secure["allowed_roles"].map(parse_allowed_roles)
    role_counts = {
        role: int(parsed_roles.map(lambda roles: role in roles).sum())
        for role in VALID_ROLES
    }
    original_modified = input_hash_before != input_hash_after
    row_count_preserved = len(source) == len(secure)

    print("\nSECURITY TAGGING REPORT")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print("Roles:")
    for role in VALID_ROLES:
        print(role)
    print(f"Total chunks: {len(secure)}")
    print(f"HR chunks: {group_counts[HR_GROUP]}")
    print(f"Risk chunks: {group_counts[RISK_GROUP]}")
    print(f"General chunks: {group_counts[GENERAL_GROUP]}")
    for role in VALID_ROLES:
        print(f"{role}: {role_counts[role]}")
    print("Validation:")
    print(f"- Empty allowed_roles: {empty_count}")
    print(f"- Invalid roles: {sorted(invalid_roles)}")
    print(f"- Row count preserved: {'YES' if row_count_preserved else 'NO'}")
    print(f"- Original data modified: {'YES' if original_modified else 'NO'}")
    print("Status: SUCCESS")


def main() -> None:
    args = parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if input_path == output_path:
        raise ValueError("Output must not overwrite chunks_normalized.csv")

    input_hash_before = file_sha256(input_path)
    source = read_corpus(input_path)
    secure, groups = assign_security_tags(source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    secure.to_csv(output_path, index=False, encoding="utf-8")

    written, empty_count, invalid_roles = validate_written_output(source, output_path)
    input_hash_after = file_sha256(input_path)
    for group in GROUP_ORDER:
        print_sample(written, groups, group)
    print_report(
        source,
        written,
        groups,
        input_path,
        output_path,
        input_hash_before,
        input_hash_after,
        empty_count,
        invalid_roles,
    )


if __name__ == "__main__":
    main()
