# P9 Structure Comparison Report

> **P9 RERUN UPDATE (2026-08-24):** UI da duoc dong bo voi corpus hop nhat sau P6/P7 rerun.

## Pham vi

So sanh ket qua P9 trong `Buoi_17/app.py` voi cay thu muc mau trong `Buoi_17/Buoi_17.md` va cac artifact thuc te dang co.

## Ket qua chuc nang P9

`Buoi_17/app.py` da co day du cac thanh phan UI chinh va da duoc cap nhat de dung corpus hop nhat:

- Sidebar User ID, User Role, Top-k va trang thai Neo4j.
- Tab `TRA CUU QUY DINH`.
- Tab `COMPLIANCE GAP CHECKER`, goi module P7 va hien thi ket qua that.
- Tab `AUDIT`.
- Answer, citation, document/chunk ID, access decision va request ID.
- Gap tab hien thi external/internal citation, classification, reason, confidence va review status.
- Audit chi doc event phu hop voi role dang chon.
- Khong hien thi secret.

Kiem tra runtime:

```text
APP_SYNTAX: PASS
MODULE_IMPORTS: PASS
STREAMLIT HEALTH: 200 / ok
NEO4J: READY
FINAL VALIDATION: PASS
```

## So sanh voi cay mau

### Da co

- `app.py`
- `scripts/audit_logger.py`
- `scripts/encryption_demo.py`
- `scripts/final_validation.py`
- `scripts/internal_lookup.py`
- `scripts/secure_retrieval_adapter.py`
- `scripts/security_tests.py`
- `outputs/dependency_report.md`
- `outputs/rbac_reuse_report.md`
- `outputs/audit_log.jsonl`
- `outputs/internal_lookup_demo.md`
- `outputs/compliance_gap_report.md`
- `outputs/security_test_report.md`
- `outputs/final_validation_report.md`
- `outputs/secure_retrieval_test.md`
- `outputs/encryption_demo_report.md`
- `outputs/graph_gap_integration_report.md`
- `outputs/gap_input_catalog.md`

### Khac voi cay mau

Cac path mau chua co:

```text
README.md
config/rbac_policy.json
scripts/rbac.py
scripts/secure_retrieval.py
scripts/compliance_gap.py
outputs/rbac_test_report.md
outputs/compliance_gap_results.csv
```

Giai thich:

- `scripts/secure_retrieval.py` duoc thay bang `scripts/secure_retrieval_adapter.py` vi Buoi 14 khong co class `SecureRetriever` rieng de copy.
- `scripts/rbac.py` khong can tao vi RBAC helper duoc tai su dung tu Buoi 14.
- `scripts/compliance_gap.py` va `compliance_gap_results.csv` da co sau khi P6 rerun xac nhan `INTERNAL_POLICY`.
- `outputs/rbac_test_report.md` duoc bao phu boi `rbac_reuse_report.md` va `secure_retrieval_test.md`.
- `README.md` va `config/rbac_policy.json` chua duoc tao trong pham vi cac prompt da thuc hien.

## File bo sung dang co

Ngoai cay mau, thu muc hien co:

```text
Buoi_17/data/agribank_internal_policies.csv
Buoi_17/data/chunks_combined_secure.csv
outputs/audit_log.jsonl.fernet
outputs/encryption_demo.key
__pycache__/
```

`encryption_demo.key` duoc bao ve boi `.gitignore` voi `*.key`. Khong dua key vao report.

Hai file trong `Buoi_17/data/` khong duoc P6 su dung; P6 da su dung dung nguon duoc chi dinh la `../buoi_16/data/processed/chunks_secure.csv`. Can xac nhan nguon chinh thuc truoc khi thay doi ket luan data-gap.

## Kiem tra rerun P9

```text
COMBINED_CORPUS: 811 chunks / 25 documents
RISK_MANAGER_LOOKUP: ALLOW / 2 citations
UNKNOWN_ROLE_LOOKUP: DENY / 0 citations
STREAMLIT HEALTH: 200 / ok
```

Role selector hien dung role cua corpus Buoi 17:

```text
Admin, HR, Risk_Manager, Staff, Guest
```

## Ket luan

```text
P9 FUNCTIONAL RESULT: PASS
P9 STRUCTURE MATCH: PARTIAL
P9 UI READY: YES
COMPLIANCE GAP UI: RESULTS MODE
READY FOR DEMO: YES
```
