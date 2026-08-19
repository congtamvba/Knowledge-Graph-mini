from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.secure_retriever import filter_secure_corpus, parse_allowed_roles, user_has_access


class SecureRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = pd.read_csv(
            PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv",
            dtype=str,
            keep_default_na=False,
            encoding="utf-8",
        )

    def test_parse_allowed_roles_keeps_exact_role_order(self) -> None:
        roles = parse_allowed_roles('["Admin", "HR_Manager", "Risk_Officer"]')
        self.assertEqual(["Admin", "HR_Manager", "Risk_Officer"], roles)

    def test_guest_access_filters_to_visible_chunks_only(self) -> None:
        filtered = filter_secure_corpus(self.corpus, ["Guest"])
        self.assertTrue(len(filtered) > 0)
        self.assertTrue(all(user_has_access(row["allowed_roles"], ["Guest"]) for _, row in filtered.iterrows()))

    def test_admin_access_keeps_more_sensitive_chunks(self) -> None:
        filtered = filter_secure_corpus(self.corpus, ["Admin"])
        self.assertTrue(len(filtered) >= len(filter_secure_corpus(self.corpus, ["Guest"])))
        self.assertTrue(all(user_has_access(row["allowed_roles"], ["Admin"]) for _, row in filtered.iterrows()))


if __name__ == "__main__":
    unittest.main()
