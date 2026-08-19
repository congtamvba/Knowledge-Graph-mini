from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

ADMIN = "Admin"
HR_MANAGER = "HR_Manager"
RISK_OFFICER = "Risk_Officer"
EMPLOYEE = "Employee"
GUEST = "Guest"

VALID_ROLES = (
    ADMIN,
    HR_MANAGER,
    RISK_OFFICER,
    EMPLOYEE,
    GUEST,
)
DEFAULT_ROLE = GUEST

REQUIRED_DATABASE_ENV_VARS = (
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_DATABASE",
)


def validate_roles(roles: Iterable[str]) -> tuple[str, ...]:
    selected_roles = tuple(dict.fromkeys(roles))
    if not selected_roles:
        raise ValueError("At least one role is required")

    invalid_roles = sorted(set(selected_roles) - set(VALID_ROLES))
    if invalid_roles:
        raise ValueError(
            f"Invalid roles: {invalid_roles}. Valid roles: {list(VALID_ROLES)}"
        )
    return selected_roles


def load_database_environment() -> Path:
    if not ENV_PATH.is_file():
        raise FileNotFoundError(f"Local database environment file not found: {ENV_PATH}")

    load_dotenv(ENV_PATH, override=False)
    missing_variables = [
        name for name in REQUIRED_DATABASE_ENV_VARS if not os.getenv(name)
    ]
    if missing_variables:
        raise RuntimeError(
            f"Missing database environment variables: {missing_variables}"
        )
    return ENV_PATH