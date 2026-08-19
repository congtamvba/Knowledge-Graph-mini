from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_ROLE, VALID_ROLES, validate_roles


class RoleConfigurationTests(unittest.TestCase):
    def test_choice_b_roles_are_exact_and_stable(self) -> None:
        self.assertEqual(
            (
                "Admin",
                "HR_Manager",
                "Risk_Officer",
                "Employee",
                "Guest",
            ),
            VALID_ROLES,
        )
        self.assertEqual("Guest", DEFAULT_ROLE)

    def test_validate_roles_rejects_typo(self) -> None:
        with self.assertRaises(ValueError):
            validate_roles(["Risk_Manager"])

    def test_validate_roles_deduplicates_without_reordering(self) -> None:
        self.assertEqual(
            ("Employee", "Admin"),
            validate_roles(["Employee", "Admin", "Employee"]),
        )


if __name__ == "__main__":
    unittest.main()