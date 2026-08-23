from __future__ import annotations

import sys
from pathlib import Path

from cryptography.fernet import Fernet

SCRIPT_ROOT = Path(__file__).resolve().parent
BUOI_17_ROOT = SCRIPT_ROOT.parent
OUTPUT_ROOT = BUOI_17_ROOT / "outputs"
INPUT_PATH = OUTPUT_ROOT / "audit_log.jsonl"
KEY_PATH = OUTPUT_ROOT / "encryption_demo.key"
ENCRYPTED_PATH = OUTPUT_ROOT / "audit_log.jsonl.fernet"
REPORT_PATH = OUTPUT_ROOT / "encryption_demo_report.md"


def encrypt_file(input_path: Path, key_path: Path, encrypted_path: Path) -> None:
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    encrypted_path.write_bytes(Fernet(key).encrypt(input_path.read_bytes()))


def decrypt_file(encrypted_path: Path, key_path: Path, output_path: Path) -> None:
    key = key_path.read_bytes()
    output_path.write_bytes(Fernet(key).decrypt(encrypted_path.read_bytes()))


def run_demo() -> bool:
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Audit input not found: {INPUT_PATH}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    decrypted_path = OUTPUT_ROOT / "audit_log.decrypted.tmp"
    try:
        encrypt_file(INPUT_PATH, KEY_PATH, ENCRYPTED_PATH)
        decrypt_file(ENCRYPTED_PATH, KEY_PATH, decrypted_path)
        matches = decrypted_path.read_bytes() == INPUT_PATH.read_bytes()
    finally:
        decrypted_path.unlink(missing_ok=True)

    report = "\n".join(
        [
            "# Encryption Demo Report - Buoi 17",
            "",
            "Muc tieu: minh hoa bao ve du lieu at-rest bang Fernet.",
            "Day la demo dao tao, khong phai thiet ke production-ready.",
            "",
            f"- Input: `{INPUT_PATH.name}`",
            f"- Encrypted artifact: `{ENCRYPTED_PATH.name}`",
            f"- Runtime key: `{KEY_PATH.name}` (duoc gitignore boi quy tac `*.key`)",
            f"- Decrypt byte-for-byte match: `{matches}`",
            "",
            "Can them TLS, key management, rotation, backup va IAM khi trien khai that.",
            "",
            "```text",
            f"ENCRYPT: {'PASS' if ENCRYPTED_PATH.is_file() else 'FAIL'}",
            f"DECRYPT MATCH: {'PASS' if matches else 'FAIL'}",
            "PRODUCTION READY: NO",
            "```",
            "",
        ]
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    return matches


if __name__ == "__main__":
    decrypt_matches = run_demo()
    print(f"ENCRYPT={'PASS' if ENCRYPTED_PATH.is_file() else 'FAIL'}")
    print(f"DECRYPT_MATCH={'PASS' if decrypt_matches else 'FAIL'}")
    print("PRODUCTION_READY=NO")
    sys.exit(0 if decrypt_matches else 1)
