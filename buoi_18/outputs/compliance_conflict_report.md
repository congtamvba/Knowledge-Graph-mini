# Compliance Conflict Report - Buoi 18

Cross-comparison được chạy sau RBAC trên corpus Buổi 18. Citation được lấy nguyên từ metadata nguồn.

- User role: `Admin`
- Authorized chunks: 811 / 811
- Retrieval: BM25 trên tập external đã lọc quyền
- LLM analysis: enabled when LLM_API_KEY và LLM_MODEL có mặt; fallback deterministic otherwise

## Results

| Domain | Internal citation | External citation | Type | Severity | Review |
|---|---|---|---|---|---|
| An toàn kho quỹ và vận chuyển tiền | [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 1 | doc_agr_at01_01] | [01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 50. Phương tiện vận chuyển | doc_44209_điều_50__phương_tiện_vận_chuyển_50] | QUY_TRINH | MEDIUM | NEEDS_HUMAN_REVIEW |
| CAR và quản lý rủi ro | [250/QĐ-NHNO-QLRR - Quy định nội bộ số 250/QĐ-NHNO-QLRR | Điều 5 | doc_agr_car02_01] | [41/2016/TT-NHNN - Thông tư số 41/2016/TT-NHNN Quy định tỷ lệ an toàn vốn đối với ngân hàng, chi nhánh ngân hàng nước ngoài | Điều 6. Tỷ lệ an toàn vốn | doc_117310_điều_6__tỷ_lệ_an_toàn_vốn_6] | KHONG_XUNG_DOT | LOW | NEEDS_HUMAN_REVIEW |
| Tín dụng và thẩm quyền phê duyệt | [315/QC-NHNO-TD - Quy chế tín dụng nội bộ số 315/QC-NHNO-TD | Điều 8 | doc_agr_td03_01] | [73/2016/NĐ-CP - Nghị định số 73/2016/NĐ-CP Quy định chi tiết thi hành Luật kinh doanh bảo hiểm và Luật sửa đổi, bổ sung một số điều của Luật kinh doanh bảo hiểm | Điều 55. Dự phòng nghiệp vụ đối với bảo hiểm sức khỏe | doc_112025_điều_55__dự_phòng_nghiệp_vụ_đối_với_bảo_hiểm_sức_khỏe_55] | CHUA_DU_BANG_CHUNG | LOW | NEEDS_HUMAN_REVIEW |

## Guardrails

- RBAC được áp dụng trước BM25 và evidence package.
- Citation integrity: `PASS`.
- Human review guardrail: `PASS`.
- Không kết luận xung đột chỉ từ retrieval score; trường hợp chưa đủ evidence dùng `CHUA_DU_BANG_CHUNG`.

```text
COMPLIANCE CHECKER ENGINE: PASS
CONFLICTS DETECTED: 3
HUMAN REVIEW GUARDRAIL: PASS
```
