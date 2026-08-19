from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from assign_security_tags import (
    GENERAL_ROLES,
    HR_GROUP,
    HR_ROLES,
    RISK_GROUP,
    RISK_ROLES,
    assign_security_tags,
    classify_chunk,
    read_corpus,
)


class SecurityTaggingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = read_corpus(
            PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
        )
        cls.secure, cls.groups = assign_security_tags(cls.source)

    def test_preserves_every_original_column_and_value(self) -> None:
        self.assertEqual(
            self.source.columns.tolist() + ["allowed_roles"],
            self.secure.columns.tolist(),
        )
        self.assertEqual(len(self.source), len(self.secure))
        for column in self.source.columns:
            self.assertTrue(self.source[column].equals(self.secure[column]), column)

    def test_every_chunk_has_valid_json_roles(self) -> None:
        parsed = self.secure["allowed_roles"].map(json.loads)
        self.assertTrue(parsed.map(bool).all())
        self.assertTrue(
            parsed.map(lambda roles: all(role in GENERAL_ROLES for role in roles)).all()
        )

    def test_hr_has_priority_when_both_groups_match(self) -> None:
        group, roles = classify_chunk(
            "doc-1",
            "NHÂN SỰ thực hiện quản trị rủi ro tín dụng",
        )
        self.assertEqual(HR_GROUP, group)
        self.assertEqual(HR_ROLES, roles)

    def test_risk_matching_is_case_insensitive_and_supports_vietnamese(self) -> None:
        group, roles = classify_chunk("doc-2", "PHÊ DUYỆT TÍN DỤNG cho KHOẢN VAY")
        self.assertEqual(RISK_GROUP, group)
        self.assertEqual(RISK_ROLES, roles)

    def test_document_id_is_searchable(self) -> None:
        group, roles = classify_chunk("HỒ-SƠ-NHÂN-SỰ", "Nội dung không khớp")
        self.assertEqual(HR_GROUP, group)
        self.assertEqual(HR_ROLES, roles)

    def test_actual_corpus_has_all_three_real_groups(self) -> None:
        self.assertEqual({"HR", "RISK", "GENERAL"}, set(self.groups))


if __name__ == "__main__":
    unittest.main()
