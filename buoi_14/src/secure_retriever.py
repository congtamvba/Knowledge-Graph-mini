from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from src.config import VALID_ROLES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
SECURE_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"


def parse_allowed_roles(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        raise ValueError("allowed_roles is required")
    if isinstance(value, str):
        items = json.loads(value)
    else:
        items = list(value)
    if not isinstance(items, list) or not items:
        raise ValueError("allowed_roles must be a non-empty list")
    normalized = [str(item).strip() for item in items if str(item).strip()]
    if not normalized:
        raise ValueError("allowed_roles cannot be empty after normalization")
    invalid = sorted(set(normalized) - set(VALID_ROLES))
    if invalid:
        raise ValueError(f"Invalid roles: {invalid}. Valid roles: {list(VALID_ROLES)}")
    return list(dict.fromkeys(normalized))


def user_has_access(allowed_roles: str | Iterable[str] | None, user_roles: Iterable[str]) -> bool:
    user_roles = [str(role).strip() for role in user_roles if str(role).strip()]
    if not user_roles:
        return False
    try:
        roles = parse_allowed_roles(allowed_roles)
    except ValueError:
        return False
    return any(role in roles for role in user_roles)


def filter_secure_corpus(corpus: pd.DataFrame, user_roles: Iterable[str]) -> pd.DataFrame:
    if corpus.empty:
        return corpus.copy()
    normalized_roles = [str(role).strip() for role in user_roles if str(role).strip()]
    if not normalized_roles:
        return corpus.iloc[0:0].copy()

    visible = []
    for row in corpus.itertuples(index=False):
        try:
            chunk_roles = parse_allowed_roles(getattr(row, "allowed_roles"))
        except ValueError:
            continue
        if any(role in chunk_roles for role in normalized_roles):
            visible.append(row)
    return pd.DataFrame.from_records(
        [
            {
                "chunk_id": row.chunk_id,
                "document_id": row.document_id,
                "text": row.text,
                "title": getattr(row, "title", ""),
                "document_type": getattr(row, "document_type", ""),
                "article": getattr(row, "article", ""),
                "status": getattr(row, "status", ""),
                "allowed_roles": row.allowed_roles,
            }
            for row in visible
        ]
    )


def load_secure_corpus(path: Path = SECURE_CORPUS_PATH) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Secure corpus not found: {path}")
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    required = {
        "chunk_id",
        "document_id",
        "text",
        "title",
        "document_type",
        "article",
        "status",
        "allowed_roles",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Secure corpus is missing required columns: {missing}")
    if df.empty:
        raise ValueError("Secure corpus is empty")
    if df["chunk_id"].duplicated().any():
        raise ValueError("Secure corpus contains duplicate chunk_id values")
    return df


def graph_access_query(user_roles: Iterable[str], lab_session: str = "buoi_15") -> tuple[str, dict[str, object]]:
    roles = [str(role).strip() for role in user_roles if str(role).strip()]
    if not roles:
        raise ValueError("user_roles must not be empty")
    query = """
    MATCH (d:DieuKhoan {lab_session: $lab_session})
    WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
    RETURN d
    """
    return query, {"user_roles": roles, "lab_session": lab_session}


def graph_visible_chunks(user_roles: Iterable[str], database: str | None = None) -> list[dict[str, object]]:
    load_dotenv(ENV_PATH, override=False)
    if database is None:
        database = os.getenv("NEO4J_DATABASE")
    if not database:
        raise RuntimeError("NEO4J_DATABASE is missing from .env")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not (uri and user and password):
        raise RuntimeError("Neo4j connection variables are missing from .env")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        records, _, _ = driver.execute_query(
            """
            MATCH (d:DieuKhoan {lab_session: $lab_session})
            WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
            RETURN d.id AS chunk_id, d.document_id AS document_id, d.allowed_roles AS allowed_roles
            ORDER BY d.id
            """,
            user_roles=[str(role).strip() for role in user_roles if str(role).strip()],
            lab_session="buoi_15",
            database_=database,
        )
        return [
            {
                "chunk_id": record["chunk_id"],
                "document_id": record["document_id"],
                "allowed_roles": list(record["allowed_roles"]),
            }
            for record in records
        ]
    except (ServiceUnavailable, Neo4jError, OSError) as error:
        raise RuntimeError(f"Unable to query Neo4j for authorized chunks: {error}") from error
    finally:
        driver.close()


__all__ = [
    "SECURE_CORPUS_PATH",
    "filter_secure_corpus",
    "graph_access_query",
    "graph_visible_chunks",
    "load_secure_corpus",
    "parse_allowed_roles",
    "user_has_access",
]
