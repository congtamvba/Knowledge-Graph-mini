from __future__ import annotations

import argparse
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
LAB_SESSION = "buoi_14"
DEFAULT_METADATA_PATH = WORKSPACE_ROOT / "kb+hops" / "metadata.csv"
DEFAULT_CONTENT_PATH = WORKSPACE_ROOT / "kb+hops" / "content.csv"
DEFAULT_RELATIONSHIPS_PATH = WORKSPACE_ROOT / "kb+hops" / "relationships.csv"
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
DEFAULT_ENV_PATH = WORKSPACE_ROOT / ".env"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "outputs" / "kg_build_report.md"

EXPECTED_METADATA_COLUMNS = {"id", "title", "loai_van_ban", "tinh_trang_hieu_luc"}
EXPECTED_CONTENT_COLUMNS = {"id", "content_html"}
EXPECTED_RELATIONSHIP_COLUMNS = {
    "doc_id",
    "other_doc_id",
    "relationship",
    "relationship_type",
}
EXPECTED_CHUNK_COLUMNS = {
    "chunk_id",
    "document_id",
    "text",
    "article",
    "document_type",
    "status",
}
ALLOWED_RELATIONSHIP_TYPES = {
    "CAN_CU",
    "HOP_NHAT",
    "SUA_DOI_BO_SUNG",
    "THAY_THE",
    "VAN_BAN_BO_SUNG",
}

SCHEMA_QUERIES = [
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
    """
    CREATE INDEX dieu_khoan_document_id IF NOT EXISTS
    FOR (d:DieuKhoan)
    ON (d.document_id)
    """,
]

UPSERT_DOCUMENTS = """
UNWIND $rows AS row
MERGE (v:VanBan {lab_session: $lab_session, id: row.id})
SET v.title = row.title,
    v.document_type = row.document_type,
    v.status = row.status,
    v.source_file = 'metadata.csv'
"""

UPSERT_CHUNKS = """
UNWIND $rows AS row
MERGE (d:DieuKhoan {lab_session: $lab_session, id: row.id})
SET d.document_id = row.document_id,
    d.text = row.text,
    d.article = row.article,
    d.document_type = row.document_type,
    d.status = row.status,
    d.source_file = 'chunks_normalized.csv'
"""

UPSERT_CONTAINS = """
UNWIND $rows AS row
MATCH (v:VanBan {lab_session: $lab_session, id: row.document_id})
MATCH (d:DieuKhoan {lab_session: $lab_session, id: row.chunk_id})
MERGE (v)-[r:CONTAINS {lab_session: $lab_session}]->(d)
SET r.source_file = 'chunks_normalized.csv'
"""

UPSERT_NEXT = """
UNWIND $rows AS row
MATCH (current:DieuKhoan {lab_session: $lab_session, id: row.current_id})
MATCH (next:DieuKhoan {lab_session: $lab_session, id: row.next_id})
MERGE (current)-[r:NEXT {lab_session: $lab_session}]->(next)
SET r.document_id = row.document_id,
    r.source_file = 'chunks_normalized.csv'
"""


@dataclass(frozen=True)
class GraphData:
    documents: list[dict[str, str]]
    chunks: list[dict[str, str]]
    contains: list[dict[str, str]]
    next_edges: list[dict[str, str]]
    document_relationships: list[dict[str, str]]
    relationship_counts: Counter[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load the Buoi 14 mini knowledge graph safely.")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT_PATH)
    parser.add_argument("--relationships", type=Path, default=DEFAULT_RELATIONSHIPS_PATH)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data and report planned counts without connecting to Neo4j.",
    )
    return parser.parse_args()


def read_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing = required_columns - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    return frame


def prepare_graph_data(
    metadata: pd.DataFrame,
    content: pd.DataFrame,
    relationships: pd.DataFrame,
    chunks: pd.DataFrame,
) -> GraphData:
    if metadata["id"].duplicated().any() or content["id"].duplicated().any():
        raise ValueError("metadata.id and content.id must be unique")
    if chunks["chunk_id"].duplicated().any():
        raise ValueError("chunks.chunk_id must be unique")

    metadata_ids = set(metadata["id"])
    if metadata_ids != set(content["id"]):
        raise ValueError("metadata.id and content.id do not match")
    if set(chunks["document_id"]) != metadata_ids:
        raise ValueError("Every document must have metadata and at least one chunk")

    actual_types = set(relationships["relationship_type"])
    unsupported_types = actual_types - ALLOWED_RELATIONSHIP_TYPES
    if unsupported_types:
        raise ValueError(f"Unmapped relationship types: {sorted(unsupported_types)}")
    if actual_types != ALLOWED_RELATIONSHIP_TYPES:
        missing_types = ALLOWED_RELATIONSHIP_TYPES - actual_types
        raise ValueError(f"Expected source relationship types are absent: {sorted(missing_types)}")

    relationship_endpoints = set(relationships["doc_id"]) | set(relationships["other_doc_id"])
    orphan_endpoints = relationship_endpoints - metadata_ids
    if orphan_endpoints:
        raise ValueError(f"Relationship endpoints missing from metadata: {sorted(orphan_endpoints)}")

    documents = [
        {
            "id": row.id,
            "title": row.title,
            "document_type": row.loai_van_ban,
            "status": row.tinh_trang_hieu_luc,
        }
        for row in metadata.itertuples(index=False)
    ]
    chunk_records = [
        {
            "id": row.chunk_id,
            "document_id": row.document_id,
            "text": row.text,
            "article": row.article,
            "document_type": row.document_type,
            "status": row.status,
        }
        for row in chunks.itertuples(index=False)
    ]
    contains = [
        {"document_id": row.document_id, "chunk_id": row.chunk_id}
        for row in chunks.itertuples(index=False)
    ]

    next_edges = []
    for document_id, document_chunks in chunks.groupby("document_id", sort=False):
        chunk_ids = document_chunks["chunk_id"].tolist()
        next_edges.extend(
            {
                "document_id": document_id,
                "current_id": current_id,
                "next_id": next_id,
            }
            for current_id, next_id in zip(chunk_ids, chunk_ids[1:])
        )

    document_relationships = [
        {
            "source_id": row.doc_id,
            "target_id": row.other_doc_id,
            "relationship": row.relationship,
            "relationship_type": row.relationship_type,
            "source_file": "relationships.csv",
        }
        for row in relationships.itertuples(index=False)
    ]
    return GraphData(
        documents=documents,
        chunks=chunk_records,
        contains=contains,
        next_edges=next_edges,
        document_relationships=document_relationships,
        relationship_counts=Counter(relationships["relationship_type"]),
    )


def batches(rows: list[dict[str, str]], batch_size: int) -> Iterable[list[dict[str, str]]]:
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def execute_batches(driver, database: str, query: str, rows: list[dict[str, str]], batch_size: int) -> None:
    for batch in batches(rows, batch_size):
        driver.execute_query(query, rows=batch, lab_session=LAB_SESSION, database_=database)


def relationship_query(relationship_type: str) -> str:
    if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
        raise ValueError(f"Relationship type is not allowed: {relationship_type}")
    return f"""
    UNWIND $rows AS row
    MATCH (source:VanBan {{lab_session: $lab_session, id: row.source_id}})
    MATCH (target:VanBan {{lab_session: $lab_session, id: row.target_id}})
    MERGE (source)-[r:{relationship_type} {{lab_session: $lab_session}}]->(target)
    SET r.source_file = row.source_file,
        r.source_relationship = row.relationship,
        r.source_relationship_type = row.relationship_type
    """


def load_graph(driver, database: str, data: GraphData, batch_size: int) -> None:
    for query in SCHEMA_QUERIES:
        driver.execute_query(query, database_=database)
    execute_batches(driver, database, UPSERT_DOCUMENTS, data.documents, batch_size)
    execute_batches(driver, database, UPSERT_CHUNKS, data.chunks, batch_size)
    execute_batches(driver, database, UPSERT_CONTAINS, data.contains, batch_size)
    execute_batches(driver, database, UPSERT_NEXT, data.next_edges, batch_size)

    for relationship_type in sorted(data.relationship_counts):
        rows = [
            row for row in data.document_relationships
            if row["relationship_type"] == relationship_type
        ]
        execute_batches(driver, database, relationship_query(relationship_type), rows, batch_size)


def inspect_graph(driver, database: str) -> tuple[dict[str, int], dict[str, int], int, int]:
    node_records, _, _ = driver.execute_query(
        """
        MATCH (n {lab_session: $lab_session})
        UNWIND labels(n) AS label
        RETURN label, count(*) AS count
        ORDER BY label
        """,
        lab_session=LAB_SESSION,
        database_=database,
    )
    relationship_records, _, _ = driver.execute_query(
        """
        MATCH ()-[r {lab_session: $lab_session}]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY type
        """,
        lab_session=LAB_SESSION,
        database_=database,
    )
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
    isolated_nodes = driver.execute_query(
        """
        MATCH (n {lab_session: $lab_session})
        WHERE NOT (n)--()
        RETURN count(n) AS count
        """,
        lab_session=LAB_SESSION,
        database_=database,
    ).records[0]["count"]
    return (
        {record["label"]: record["count"] for record in node_records},
        {record["type"]: record["count"] for record in relationship_records},
        int(orphan_chunks),
        int(isolated_nodes),
    )


def planned_counts(data: GraphData) -> dict[str, int]:
    counts = {
        "VanBan": len(data.documents),
        "DieuKhoan": len(data.chunks),
        "CONTAINS": len(data.contains),
        "NEXT": len(data.next_edges),
    }
    counts.update(data.relationship_counts)
    return counts


def report_text(
    status: str,
    data: GraphData,
    reason: str = "",
    node_counts: dict[str, int] | None = None,
    relationship_counts: dict[str, int] | None = None,
    orphan_chunks: int | None = None,
    isolated_nodes: int | None = None,
) -> str:
    plan = planned_counts(data)
    lines = [
        "# Mini Knowledge Graph Build Report",
        "",
        f"- **Status:** {status}",
        f"- **Lab session:** `{LAB_SESSION}`",
        "- **Write strategy:** parameterized `MERGE`; no global delete query exists in the loader.",
    ]
    if reason:
        lines.append(f"- **Reason:** {reason}")
    lines.extend(["", "## Validated Input", ""])
    lines.extend(
        [
            f"- VanBan source rows: **{len(data.documents)}**.",
            f"- DieuKhoan/chunk rows: **{len(data.chunks)}**.",
            f"- Source document relationships: **{len(data.document_relationships)}**.",
            "- Relationship endpoints missing from metadata: **0**.",
            "- Source files were read only.",
            "",
            "## Planned Counts",
            "",
            "| Type | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(f"| `{name}` | {count} |" for name, count in plan.items())

    if node_counts is not None and relationship_counts is not None:
        lines.extend(["", "## Actual Neo4j Counts", "", "### Nodes", ""])
        lines.extend(f"- `{name}`: **{count}**" for name, count in node_counts.items())
        lines.extend(["", "### Relationships", ""])
        lines.extend(f"- `{name}`: **{count}**" for name, count in relationship_counts.items())
        lines.extend(
            [
                "",
                "## Quality Checks",
                "",
                f"- DieuKhoan without CONTAINS: **{orphan_chunks}**.",
                f"- Isolated session nodes: **{isolated_nodes}**.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Neo4j Execution",
                "",
                "No graph counts are claimed because Neo4j was not loaded.",
                "Start a Neo4j 5.x instance with Bolt enabled, verify the `.env` values, then run:",
                "",
                "```powershell",
                '& ".\\.venv\\Scripts\\python.exe" ".\\scripts\\load_mini_kg.py"',
                "```",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")

    metadata = read_csv(args.metadata.resolve(), EXPECTED_METADATA_COLUMNS)
    content = read_csv(args.content.resolve(), EXPECTED_CONTENT_COLUMNS)
    relationships = read_csv(args.relationships.resolve(), EXPECTED_RELATIONSHIP_COLUMNS)
    chunks = read_csv(args.chunks.resolve(), EXPECTED_CHUNK_COLUMNS)
    data = prepare_graph_data(metadata, content, relationships, chunks)
    report_path = args.report.resolve()
    print("Validated graph plan:", planned_counts(data))

    if args.dry_run:
        write_report(report_path, report_text("NOT RUN (DRY RUN)", data, "Dry-run requested."))
        print(f"Report: {report_path}")
        return

    load_dotenv(args.env_file.resolve())
    required_variables = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE"]
    missing_variables = [name for name in required_variables if not os.getenv(name)]
    if missing_variables:
        reason = f"Missing environment variables: {', '.join(missing_variables)}"
        write_report(report_path, report_text("NOT RUN", data, reason))
        print(reason)
        print(f"Report: {report_path}")
        return

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    try:
        driver.verify_connectivity()
        database = os.environ["NEO4J_DATABASE"]
        load_graph(driver, database, data, args.batch_size)
        node_counts, relationship_counts, orphan_chunks, isolated_nodes = inspect_graph(
            driver, database
        )
        write_report(
            report_path,
            report_text(
                "LOADED",
                data,
                node_counts=node_counts,
                relationship_counts=relationship_counts,
                orphan_chunks=orphan_chunks,
                isolated_nodes=isolated_nodes,
            ),
        )
        print("Node counts:", node_counts)
        print("Relationship counts:", relationship_counts)
        print("Orphan DieuKhoan:", orphan_chunks)
        print("Isolated nodes:", isolated_nodes)
    except (ServiceUnavailable, Neo4jError, OSError) as error:
        reason = f"{type(error).__name__}: {error}"
        write_report(report_path, report_text("NOT RUN", data, reason))
        print("Neo4j was not loaded:", reason)
    finally:
        driver.close()
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()