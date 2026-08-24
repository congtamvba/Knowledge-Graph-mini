# Kết quả Buổi 18

## 1. Tổng quan

Báo cáo này tổng hợp kết quả thực hiện từ Prompt Setup đến Prompt 6 cho project **AI Compliance Checker & AI Audit Checklist Generator**.

Môi trường Python sử dụng:

```text
C:\RAG\Knowledge Graph mini\buoi_14\.venv\Scripts\python.exe
Python 3.11.2
```

Dữ liệu nguồn được đọc ở chế độ chỉ đọc; không ghi API key, password hoặc secret vào báo cáo này.

## 2. Prompt Setup

| Hạng mục | Kết quả |
|---|---|
| Python virtual environment | PASS - sử dụng `buoi_14\\.venv` |
| Python và dependency chính | PASS |
| `data/agribank_internal_policies.csv` | PASS - 24 chunks, 10 documents |
| `data/chunks_combined_secure.csv` | PASS - 811 chunks, 25 documents |
| 14 trường metadata | PASS |
| `article`, `citation`, `allowed_roles` | PASS - không rỗng |
| `.env` và đường dẫn dữ liệu | PASS |
| `scripts/`, `outputs/` | PASS |

Cấu hình data trong `.env`:

```ini
SOURCE_SECURE_CSV=data/agribank_internal_policies.csv
SOURCE_NORMALIZED_CSV=data/chunks_combined_secure.csv
LLM_MODEL=gemini-2.5-flash
```

## 3. Prompt 1 - Data Cataloging

Artifact:

- `outputs/b18_data_catalog.md`

Kết quả:

```text
DATA CATALOGING: PASS
DOMAINS DETECTED: 10
READY FOR UC3 & UC4: YES
```

Đã catalog 10 domain nghiệp vụ nội bộ:

1. An toàn kho quỹ và vận chuyển tiền
2. CAR và quản lý rủi ro
3. Tín dụng và thẩm quyền phê duyệt
4. Ngoại tệ và giao dịch ngoại hối
5. Mạng lưới chi nhánh và phòng giao dịch
6. Bảo hiểm rủi ro nghiệp vụ và tài sản
7. Bảo mật CNTT, dữ liệu và AI
8. Nhân sự và thẩm quyền bổ nhiệm
9. Tài chính và mua sắm nội bộ
10. Phân loại nợ và xử lý nợ xấu

## 4. Prompt 2 - AI Compliance Checker

Artifacts:

- `scripts/compliance_checker.py`
- `outputs/compliance_conflicts.csv`
- `outputs/compliance_conflict_report.md`

Đã chạy thử 3 domain:

- An toàn kho quỹ và vận chuyển tiền
- CAR và quản lý rủi ro
- Tín dụng và thẩm quyền phê duyệt

Kết quả hiện tại:

```text
COMPLIANCE CHECKER ENGINE: PASS
CONFLICTS DETECTED: 3
HUMAN REVIEW GUARDRAIL: PASS
```

Các kiểm tra đạt:

- RBAC được thực hiện trước BM25 và evidence package.
- Citation A/B lấy từ metadata thật trong dataset.
- CSV đúng schema P2.
- Mọi dòng có `NEEDS_HUMAN_REVIEW`.
- Audit event được ghi cho từng lần cross-comparison.
- Khi chưa đủ bằng chứng, hệ thống dùng `KHONG_XUNG_DOT` hoặc `CHUA_DU_BANG_CHUNG`, không kết luận chỉ từ retrieval score.

## 5. Prompt 3 - AI Audit Checklist Generator

Artifacts:

- `scripts/audit_checklist_gen.py`
- `outputs/audit_checklist_results.csv`
- `outputs/audit_checklist_report.md`

Đã chạy thử:

- An toàn kho quỹ / Chi nhánh loại 1: 4 items
- Bảo mật CNTT & AI / Khối CNTT: 2 items

Kết quả:

```text
CHECKLIST GENERATOR ENGINE: PASS
CHECKLIST ITEMS GENERATED: 6
CITATIONS ATTACHED: YES
HUMAN REVIEW GUARDRAIL: PASS
```

Checklist có đủ:

- `item_id`
- `domain`
- `unit_scope`
- `audit_question`
- `risk_description`
- `risk_level`
- `source_citation`
- `recommendation`
- `review_status`

Domain không tồn tại được từ chối với thông báo `Chưa có dữ liệu quy định cho domain được yêu cầu.`

## 6. Prompt 4 - Streamlit UI

Artifact:

- `app.py`

UI đã có:

- Sidebar User ID, User Role và trạng thái dữ liệu.
- Reset Session và Clean Audit Log.
- Tab UC3 Compliance Checker.
- Tab UC4 Audit Checklist Generator.
- Tab Audit Log & System Trail.
- Lọc audit log theo Role và Action.
- Export CSV, Markdown và JSON.
- Banner cảnh báo bắt buộc human review.

Kiểm tra runtime:

```text
APP_COMPILE=PASS
ENGINE_IMPORTS=PASS
HTTP_STATUS=200
BODY=ok
```

URL demo:

```text
http://localhost:8502
```

## 7. Prompt 5 - Security & Guardrail Testing

Artifacts:

- `scripts/security_tests_b18.py`
- `outputs/security_test_b18_report.md`

Đã chạy đủ 7 bài kiểm thử:

| Bài kiểm thử | Kết quả |
|---|---|
| RBAC restricted access | PASS |
| Citation integrity | PASS |
| Hallucination check | PASS |
| Human review guardrail | PASS |
| Audit log privacy | PASS |
| Unknown domain | PASS |
| File export verification | PASS |

Tổng kết:

```text
SECURITY_TESTS_PASSED=7
SECURITY_TESTS_FAILED=0
SECURITY_TESTS=PASS
```

Audit log có 11 events tại thời điểm kiểm thử và không chứa API key, password hoặc secret.

## 8. Prompt 6 - Final Validation

Artifacts:

- `scripts/final_validation_b18.py`
- `outputs/final_validation_b18_report.md`

Đã kiểm tra 8 tiêu chí:

| Tiêu chí | Kết quả |
|---|---|
| Source Data Integrity | PASS |
| UC3 Compliance Checker | PASS |
| UC4 Audit Checklist Generator | PASS |
| Citation & Linking | PASS |
| RBAC & Governance | PASS |
| Streamlit Demo | PASS |
| Audit Trail | PASS |
| Human Review Guardrail | PASS |

Kết quả tổng thể:

```text
FINAL_VALIDATION=PASS
PASSED=8
FAILED=0

UC3 COMPLIANCE CHECKER: PASS
UC4 AUDIT CHECKLIST GEN: PASS
CITATION INTEGRITY: PASS
RBAC & GOVERNANCE: PASS
STREAMLIT DEMO: PASS
AUDIT TRAIL: PASS
SYSTEM READY FOR DEMO: YES
```

## 9. Ghi chú vận hành

- P2 và P3 đã có nhánh tích hợp Gemini thông qua `GEMINI_API_KEY` và `LLM_MODEL`.
- Demo CLI được chạy bằng fallback deterministic để kiểm soát citation và không phụ thuộc mạng/API.
- Khi chạy từ UI, engine sẽ ưu tiên nhánh LLM nếu API phản hồi hợp lệ; nếu lỗi hoặc output không đúng schema, hệ thống tự động fallback an toàn.
- `LLM_API_KEY` riêng không bắt buộc trong implementation hiện tại vì engine dùng `GEMINI_API_KEY` làm fallback.
- Mọi kết quả AI chỉ là bản nháp và vẫn bắt buộc kiểm toán viên xác minh trước khi ban hành.

## 10. Kết luận

```text
PROMPT SETUP: PASS
P1 DATA CATALOGING: PASS
P2 COMPLIANCE CHECKER: PASS
P3 AUDIT CHECKLIST GENERATOR: PASS
P4 STREAMLIT UI: PASS
P5 SECURITY & GUARDRAIL TESTS: PASS
P6 FINAL VALIDATION: PASS
SYSTEM READY FOR DEMO: YES
```
