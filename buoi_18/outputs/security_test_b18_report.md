# Security & Guardrail Test Report - Buoi 18

Kiểm thử trên artifact UC3/UC4 hiện có; dữ liệu nguồn được đọc read-only.

| Test | Status | Detail |
|---|---|---|
| RBAC restricted access | PASS | agr_it07 chunks=2; Staff_visible=0; Admin_visible=2 |
| Citation integrity | PASS | conflicts=3; checklist=6; conflict_citations=True; checklist_citations=True |
| Hallucination check | PASS | conflict_texts=True; checklist_citations=True |
| Human review guardrail | PASS | conflicts_reviewed=True; checklist_reviewed=True |
| Audit log privacy | PASS | events=11; sensitive_field_names=False; sensitive_values=False |
| Unknown domain | PASS | Chưa có dữ liệu quy định cho domain được yêu cầu. |
| File export verification | PASS | conflict_schema=True; checklist_schema=True |

Passed: `7`; Failed: `0`

```text
SECURITY & GUARDRAIL TESTS: PASS
```
