# Security Test Report - Buoi 17

Kiem thu read-only tren secure corpus, adapter, audit log, gap report va Neo4j runtime.

| Test | Status | Detail |
|---|---|---|
| allowed role | PASS | Guest nhan duoc ket qua authorized |
| unauthorized role cannot see restricted text/citation | PASS | chunk=doc_44209_quy_định_chung_0; guest_context_contains_target=False |
| restricted chunk excluded from LLM context | PASS | Moi chunk trong tap context Guest deu co Guest trong allowed_roles |
| unknown role default deny | PASS | Unknown khong co chunk authorized |
| audit SUCCESS and DENIED | PASS | statuses=['DENIED', 'SUCCESS'] |
| audit log contains no secret | PASS | Khong tim thay ten truong secret trong audit log |
| citation exists | PASS | Citation ton tai trong moi ket qua allowed |
| gap has evidence or data-gap status | PASS | rows=3; evidence_or_unknown=True |
| all gap results require human review | PASS | all_reviewed=True |
| Neo4j reports truthful status | PASS | verify_connectivity thanh cong |

Passed: `10`; Failed: `0`

```text
SECURITY TESTS: PASS
```
