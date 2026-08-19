from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from neo4j import GraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import VALID_ROLES, load_database_environment, validate_roles


LAB_SESSION = "buoi_15"
SOURCE_FILE = "chunks_secure.csv"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "processed" / SOURCE_FILE
DEFAULT_REPORT_PATH = PROJECT_ROOT / "outputs" / "secure_kg_load_report.md"
REQUIRED_COLUMNS = {
    "chunk_id",
    "document_id",
    "text",
    "title",
    "document_type",
    "article",
    "status",
    "allowed_roles",
}

SCHEMA_QUERIES = (
    """
    CREATE CONSTRAINT van_ban_session_id IF NOT EXISTS
    FOR (v:VanBan)
    REQUIRE (v.lab_session, v.id) IS UNIQUE
    """,
    """
    CREATE CONSTRAINT dieu_khoan_session_id IF NOT EXISTS
    FOR (d:DieuKhoan)
    REQUIRE (d.lab_session, d.id) IS UNIQUE
    """,
)

UPSERT_DOCUMENTS = """
UNWIND $rows AS row
MERGE (v:VanBan {lab_session: $lab_session, id: row.id})
SET v.title = row.title,
    v.document_type = row.document_type,
    v.status = row.status,
    v.allowed_roles = row.allowed_roles,
    v.source_file = $source_file
"""

UPSERT_CHUNKS = """
UNWIND $rows AS row
MERGE (d:DieuKhoan {lab_session: $lab_session, id: row.id})
SET d.document_id = row.document_id,
    d.text = row.text,
    d.article = row.article,
    d.document_type = row.document_type,
    d.status = row.status,
    d.allowed_roles = row.allowed_roles,
    d.source_file = $source_file
"""

UPSERT_CONTAINS = """
UNWIND $rows AS row
MATCH (v:VanBan {lab_session: $lab_session, id: row.document_id})
MATCH (d:DieuKhoan {lab_session: $lab_session, id: row.chunk_id})
MERGE (v)-[r:CONTAINS {lab_session: $lab_session}]->(d)
SET r.source_file = $source_file
"""

UPSERT_NEXT = """
UNWIND $rows AS row
MATCH (current:DieuKhoan {lab_session: $lab_session, id: row.current_id})
MATCH (next:DieuKhoan {lab_session: $lab_session, id: row.next_id})
MERGE (current)-[r:NEXT {lab_session: $lab_session}]->(next)
SET r.document_id = row.document_id,
    r.source_file = $source_file
"""


@dataclass(frozen=True)
class SecureGraphData:
    documents: list[dict[str, object]]
    chunks: list[dict[str, object]]
    contains: list[dict[str, str]]
    next_edges: list[dict[str, str]]


@dataclass(frozen=True)
class GraphInspection:
    van_ban: int
    dieu_khoan: int
    van_ban_with_roles: int
    dieu_khoan_with_roles: int
    contains: int
    next_edges: int
    empty_allowed_roles: int
    invalid_roles: tuple[str, ...]
    orphan_chunks: int
    missing_lab_session: int

    def structural_counts(self) -> tuple[int, int, int, int]:
        return self.van_ban, self.dieu_khoan, self.contains, self.next_edges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load the Buoi 15 RBAC graph without changing Buoi 14."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--batch-size", type=int, default=500)
    return parser.parse_args()


def parse_allowed_roles(value: str) -> tuple[str, ...]:
    try:
        roles = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid allowed_roles JSON: {value!r}") from error
    if not isinstance(roles, list) or not roles:
        raise ValueError("allowed_roles must be a non-empty JSON array")
    if not all(isinstance(role, str) for role in roles):
        raise ValueError("Every allowed role must be a string")
    return validate_roles(roles)


def read_secure_corpus(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Secure corpus not found: {path}")
    corpus = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing_columns = REQUIRED_COLUMNS - set(corpus.columns)
    if missing_columns:
        raise ValueError(f"Secure corpus is missing columns: {sorted(missing_columns)}")
    if corpus.empty:
        raise ValueError("Secure corpus is empty")
    if corpus["chunk_id"].duplicated().any():
        duplicates = corpus.loc[corpus["chunk_id"].duplicated(), "chunk_id"].tolist()
        raise ValueError(f"Duplicate chunk IDs: {duplicates[:5]}")
    corpus = corpus.copy()
    corpus["parsed_roles"] = corpus["allowed_roles"].map(parse_allowed_roles)
    return corpus


def ordered_intersection(role_sets: Iterable[tuple[str, ...]]) -> list[str]:
    role_sets = list(role_sets)
    if not role_sets:
        raise ValueError("Cannot derive VanBan roles from an empty document")
    common_roles = set(role_sets[0]).intersection(*(set(roles) for roles in role_sets[1:]))
    ordered_roles = [role for role in VALID_ROLES if role in common_roles]
    if not ordered_roles:
        raise ValueError("VanBan role intersection is empty; refusing insecure graph data")
    return ordered_roles


def prepare_graph_data(corpus: pd.DataFrame) -> SecureGraphData:
    documents = []
    for document_id, chunks in corpus.groupby("document_id", sort=False):
        first = chunks.iloc[0]
        documents.append(
            {
                "id": str(document_id),
                "title": first["title"],
                "document_type": first["document_type"],
                "status": first["status"],
                "allowed_roles": ordered_intersection(chunks["parsed_roles"]),
            }
        )

    chunk_records = [
        {
            "id": row.chunk_id,
            "document_id": row.document_id,
            "text": row.text,
            "article": row.article,
            "document_type": row.document_type,
            "status": row.status,
            "allowed_roles": list(row.parsed_roles),
        }
        for row in corpus.itertuples(index=False)
    ]
    contains = [
        {"document_id": row.document_id, "chunk_id": row.chunk_id}
        for row in corpus.itertuples(index=False)
    ]
    next_edges = []
    for document_id, chunks in corpus.groupby("document_id", sort=False):
        chunk_ids = chunks["chunk_id"].tolist()
        next_edges.extend(
            {
                "document_id": str(document_id),
                "current_id": current_id,
                "next_id": next_id,
            }
            for current_id, next_id in zip(chunk_ids, chunk_ids[1:])
        )
    return SecureGraphData(documents, chunk_records, contains, next_edges)


def batches(rows: list[dict[str, object]], batch_size: int) -> Iterable[list[dict[str, object]]]:
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def execute_batches(driver, database: str, query: str, rows: list[dict[str, object]], batch_size: int) -> None:
    for batch in batches(rows, batch_size):
        driver.execute_query(
            query,
            rows=batch,
            lab_session=LAB_SESSION,
            source_file=SOURCE_FILE,
            database_=database,
        )


def load_graph(driver, database: str, data: SecureGraphData, batch_size: int) -> None:
    for query in SCHEMA_QUERIES:
        driver.execute_query(query, database_=database)
    execute_batches(driver, database, UPSERT_DOCUMENTS, data.documents, batch_size)
    execute_batches(driver, database, UPSERT_CHUNKS, data.chunks, batch_size)
    execute_batches(driver, database, UPSERT_CONTAINS, data.contains, batch_size)
    execute_batches(driver, database, UPSERT_NEXT, data.next_edges, batch_size)


def session_snapshot(driver, database: str, lab_session: str) -> dict[str, int]:
    records, _, _ = driver.execute_query(
        """
        OPTIONAL MATCH (n {lab_session: $lab_session})
        WITH count(n) AS nodes
        OPTIONAL MATCH ()-[r {lab_session: $lab_session}]->()
        RETURN nodes, count(r) AS relationships
        """,
        lab_session=lab_session,
        database_=database,
    )
    return {
        "nodes": int(records[0]["nodes"]),
        "relationships": int(records[0]["relationships"]),
    }


def inspect_graph(driver, database: str) -> GraphInspection:
    record = driver.execute_query(
        """
        MATCH (v:VanBan {lab_session: $lab_session})
        WITH count(v) AS van_ban,
             count(CASE WHEN v.allowed_roles IS NOT NULL AND size(v.allowed_roles) > 0 THEN 1 END)
                 AS van_ban_with_roles
        MATCH (d:DieuKhoan {lab_session: $lab_session})
        WITH van_ban, van_ban_with_roles,
             count(d) AS dieu_khoan,
             count(CASE WHEN d.allowed_roles IS NOT NULL AND size(d.allowed_roles) > 0 THEN 1 END)
                 AS dieu_khoan_with_roles,
             count(CASE WHEN d.allowed_roles IS NULL OR size(d.allowed_roles) = 0 THEN 1 END)
                 AS empty_allowed_roles
        OPTIONAL MATCH ()-[contains:CONTAINS {lab_session: $lab_session}]->()
        WITH van_ban, van_ban_with_roles, dieu_khoan, dieu_khoan_with_roles,
             empty_allowed_roles, count(contains) AS contains
        OPTIONAL MATCH ()-[next:NEXT {lab_session: $lab_session}]->()
        RETURN van_ban, van_ban_with_roles, dieu_khoan, dieu_khoan_with_roles,
               empty_allowed_roles, contains, count(next) AS next_edges
        """,
        lab_session=LAB_SESSION,
        database_=database,
    ).records[0]

    invalid_role_records = driver.execute_query(
        """
        MATCH (n {lab_session: $lab_session})
        UNWIND coalesce(n.allowed_roles, []) AS role
        WITH DISTINCT role
        WHERE NOT role IN $valid_roles
        RETURN role ORDER BY role
        """,
        lab_session=LAB_SESSION,
        valid_roles=list(VALID_ROLES),
        database_=database,
    ).records
    orphan_chunks = driver.execute_query(
        """
        MATCH (d:DieuKhoan {lab_session: $lab_session})
        WHERE NOT (:VanBan {lab_session: $lab_session})
                  -[:CONTAINS {lab_session: $lab_session}]->(d)
        RETURN count(d) AS count
        """,
        lab_session=LAB_SESSION,
        database_=database,
    ).records[0]["count"]
    missing_nodes = driver.execute_query(
        """
        MATCH (n)
        WHERE (n:VanBan OR n:DieuKhoan)
          AND n.source_file = $source_file
          AND n.lab_session IS NULL
        RETURN count(n) AS count
        """,
        source_file=SOURCE_FILE,
        database_=database,
    ).records[0]["count"]
    missing_relationships = driver.execute_query(
        """
        MATCH ()-[r]->()
        WHERE r.source_file = $source_file AND r.lab_session IS NULL
        RETURN count(r) AS count
        """,
        source_file=SOURCE_FILE,
        database_=database,
    ).records[0]["count"]
    return GraphInspection(
        van_ban=int(record["van_ban"]),
        dieu_khoan=int(record["dieu_khoan"]),
        van_ban_with_roles=int(record["van_ban_with_roles"]),
        dieu_khoan_with_roles=int(record["dieu_khoan_with_roles"]),
        contains=int(record["contains"]),
        next_edges=int(record["next_edges"]),
        empty_allowed_roles=int(record["empty_allowed_roles"]),
        invalid_roles=tuple(item["role"] for item in invalid_role_records),
        orphan_chunks=int(orphan_chunks),
        missing_lab_session=int(missing_nodes) + int(missing_relationships),
    )


def sample_records(driver, database: str) -> list[dict[str, object]]:
    records, _, _ = driver.execute_query(
        """
        MATCH (v:VanBan {lab_session: $lab_session})
              -[:CONTAINS {lab_session: $lab_session}]->
              (d:DieuKhoan {lab_session: $lab_session})
        WITH v, d ORDER BY v.id, d.id
        WITH v, collect(d)[0..3] AS chunks
        RETURN v.id AS document_id,
               v.allowed_roles AS document_allowed_roles,
               [chunk IN chunks | {
                   chunk_id: chunk.id,
                   allowed_roles: chunk.allowed_roles
               }] AS chunks
        ORDER BY document_id
        LIMIT 1
        """,
        lab_session=LAB_SESSION,
        database_=database,
    )
    return [dict(record) for record in records]


def validate_inspection(data: SecureGraphData, inspection: GraphInspection) -> None:
    expected = (
        len(data.documents),
        len(data.chunks),
        len(data.contains),
        len(data.next_edges),
    )
    if inspection.structural_counts() != expected:
        raise RuntimeError(
            f"Neo4j counts do not match input: actual={inspection.structural_counts()}, expected={expected}"
        )
    if inspection.van_ban_with_roles != len(data.documents):
        raise RuntimeError("Some VanBan nodes have no allowed_roles")
    if inspection.dieu_khoan_with_roles != len(data.chunks):
        raise RuntimeError("Some DieuKhoan nodes have no allowed_roles")
    if inspection.empty_allowed_roles or inspection.invalid_roles:
        raise RuntimeError("Invalid or empty allowed_roles found in Neo4j")
    if inspection.orphan_chunks or inspection.missing_lab_session:
        raise RuntimeError("Orphan chunks or missing lab_session found in Neo4j")


def report_text(
    input_path: Path,
    database: str,
    inspection: GraphInspection,
    buoi_14_preserved: bool,
    idempotent: bool,
    samples: list[dict[str, object]],
) -> str:
    return f"""# Secure KG Load Report

## SECURE KG LOAD REPORT

- **Input:** `{input_path}`
- **Database:** `{database}`
- **Lab session:** `{LAB_SESSION}`
- **Roles:** {', '.join(VALID_ROLES)}
- **Write strategy:** parameterized `MERGE`; no delete operation.
- **VanBan role policy:** intersection of all child chunk roles (fail-closed full-document access).
- **DieuKhoan role policy:** exact roles parsed from each `chunks_secure.csv` row.

## Actual Neo4j Counts

| Check | Result |
|---|---:|
| VanBan nodes | {inspection.van_ban} |
| DieuKhoan nodes | {inspection.dieu_khoan} |
| VanBan with allowed_roles | {inspection.van_ban_with_roles} |
| DieuKhoan with allowed_roles | {inspection.dieu_khoan_with_roles} |
| CONTAINS relationships | {inspection.contains} |
| NEXT relationships | {inspection.next_edges} |
| Empty allowed_roles | {inspection.empty_allowed_roles} |
| Invalid roles | {list(inspection.invalid_roles)} |
| Orphan DieuKhoan | {inspection.orphan_chunks} |
| Missing lab_session | {inspection.missing_lab_session} |
| Buoi 14 preserved | {'YES' if buoi_14_preserved else 'NO'} |
| Idempotent | {'YES' if idempotent else 'NO'} |

## Sample

```json
{json.dumps(samples, ensure_ascii=False, indent=2)}
```

## Security Notes

- `VanBan.allowed_roles` expresses full-document access and is intentionally fail-closed.
- Prompt 3 must authorize retrieval with `DieuKhoan.allowed_roles` for chunk-level access.
- The Buoi 14 graph is isolated by `lab_session="buoi_14"` and was not updated.

**Status:** SUCCESS
"""


def print_report(inspection: GraphInspection, buoi_14_preserved: bool, idempotent: bool) -> None:
    print("\nSECURE KG LOAD REPORT")
    print(f"VanBan nodes: {inspection.van_ban}")
    print(f"DieuKhoan nodes: {inspection.dieu_khoan}")
    print(f"VanBan with allowed_roles: {inspection.van_ban_with_roles}")
    print(f"DieuKhoan with allowed_roles: {inspection.dieu_khoan_with_roles}")
    print(f"CONTAINS relationships: {inspection.contains}")
    print(f"NEXT relationships: {inspection.next_edges}")
    print(f"Empty allowed_roles: {inspection.empty_allowed_roles}")
    print(f"Invalid roles: {list(inspection.invalid_roles)}")
    print(f"Orphan DieuKhoan: {inspection.orphan_chunks}")
    print(f"Missing lab_session: {inspection.missing_lab_session}")
    print(f"Buoi 14 preserved: {'YES' if buoi_14_preserved else 'NO'}")
    print(f"Idempotent: {'YES' if idempotent else 'NO'}")
    print("Status: SUCCESS")


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    input_path = args.input.resolve()
    corpus = read_secure_corpus(input_path)
    data = prepare_graph_data(corpus)
    env_path = load_database_environment()
    print(f"Validated input: {len(data.documents)} documents, {len(data.chunks)} chunks")
    print(f"Database environment: {env_path}")

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        driver.verify_connectivity()
        database = os.environ["NEO4J_DATABASE"]
        buoi_14_before = session_snapshot(driver, database, "buoi_14")

        load_graph(driver, database, data, args.batch_size)
        first_inspection = inspect_graph(driver, database)
        validate_inspection(data, first_inspection)

        load_graph(driver, database, data, args.batch_size)
        second_inspection = inspect_graph(driver, database)
        validate_inspection(data, second_inspection)

        buoi_14_after = session_snapshot(driver, database, "buoi_14")
        buoi_14_preserved = buoi_14_before == buoi_14_after
        idempotent = first_inspection == second_inspection
        if not buoi_14_preserved:
            raise RuntimeError("Buoi 14 graph counts changed during secure load")
        if not idempotent:
            raise RuntimeError("Second MERGE load changed Buoi 15 graph counts")

        samples = sample_records(driver, database)
        report_path = args.report.resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            report_text(
                input_path,
                database,
                second_inspection,
                buoi_14_preserved,
                idempotent,
                samples,
            ),
            encoding="utf-8",
        )
        print_report(second_inspection, buoi_14_preserved, idempotent)
        print(f"Sample: {json.dumps(samples, ensure_ascii=False)}")
        print(f"Report: {report_path}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
