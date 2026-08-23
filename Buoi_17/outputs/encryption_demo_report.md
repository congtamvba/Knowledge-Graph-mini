# Encryption Demo Report - Buoi 17

Muc tieu: minh hoa bao ve du lieu at-rest bang Fernet.
Day la demo dao tao, khong phai thiet ke production-ready.

- Input: `audit_log.jsonl`
- Encrypted artifact: `audit_log.jsonl.fernet`
- Runtime key: `encryption_demo.key` (duoc gitignore boi quy tac `*.key`)
- Decrypt byte-for-byte match: `True`

Can them TLS, key management, rotation, backup va IAM khi trien khai that.

```text
ENCRYPT: PASS
DECRYPT MATCH: PASS
PRODUCTION READY: NO
```
