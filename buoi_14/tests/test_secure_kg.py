from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from load_secure_kg import (
    SCHEMA_QUERIES,
    UPSERT_CHUNKS,
    UPSERT_CONTAINS,
    UPSERT_DOCUMENTS,
    UPSERT_NEXT,
    ordered_intersection,
    prepare_graph_data,
    read_secure_corpus,
)


class SecureKnowledgeGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = read_secure_corpus(
            PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"
        )
        cls.graph = prepare_graph_data(cls.corpus)

    def test_actual_secure_corpus_produces_expected_graph_counts(self) -> None:
        self.assertEqual(15, len(self.graph.documents))
        self.assertEqual(1242, len(self.graph.chunks))
        self.assertEqual(1242, len(self.graph.contains))
        self.assertEqual(1227, len(self.graph.next_edges))

    def test_chunk_roles_are_preserved_as_neo4j_string_lists(self) -> None:
        expected = {
            row.chunk_id: list(row.parsed_roles)
            for row in self.corpus.itertuples(index=False)
        }
        actual = {row["id"]: row["allowed_roles"] for row in self.graph.chunks}
        self.assertEqual(expected, actual)
        self.assertTrue(all(isinstance(roles, list) for roles in actual.values()))

    def test_document_roles_use_fail_closed_intersection(self) -> None:
        roles_by_document = {
            row["id"]: row["allowed_roles"] for row in self.graph.documents
        }
        self.assertEqual(
            ["Admin", "Risk_Officer", "Employee"],
            roles_by_document["117310"],
        )
        self.assertEqual(["Admin"], roles_by_document["44209"])

    def test_ordered_intersection_uses_choice_b_order(self) -> None:
        roles = ordered_intersection(
            [
                ("Admin", "HR_Manager", "Risk_Officer", "Employee", "Guest"),
                ("Admin", "Risk_Officer", "Employee"),
            ]
        )
        self.assertEqual(["Admin", "Risk_Officer", "Employee"], roles)

    def test_loader_contains_no_delete_operations(self) -> None:
        queries = "\n".join(
            [*SCHEMA_QUERIES, UPSERT_DOCUMENTS, UPSERT_CHUNKS, UPSERT_CONTAINS, UPSERT_NEXT]
        ).upper()
        self.assertNotIn("DETACH DELETE", queries)
        self.assertNotIn(" DELETE ", queries)
        self.assertNotIn("DROP ", queries)


if __name__ == "__main__":
    unittest.main()
