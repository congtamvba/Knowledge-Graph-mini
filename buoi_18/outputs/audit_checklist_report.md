# Audit Checklist Report - Buoi 18

Checklist được sinh từ evidence đã lọc RBAC. Citation được lấy từ metadata nguồn; kết quả chỉ là bản nháp cần kiểm toán viên xác minh.

- Checklist items: 6
- Domains: An toàn kho quỹ, Bảo mật CNTT & AI
- Retrieval: BM25 trên corpus đã lọc quyền
- Demo generation: deterministic evidence fallback; LLM adapter có thể bật khi cấu hình model/API hợp lệ

## Results

| Item | Domain | Unit | Risk | Citation | Review |
|---|---|---|---|---|---|
| CHK_01 | An toàn kho quỹ | Chi nhánh loại 1 | HIGH | [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT \| Điều 1 \| doc_agr_at01_01]<br>[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá \| Điều 39. Đối tượng được vào kho tiền \| doc_44209_điều_39__đối_tượng_được_vào_kho_tiền_39] | NEEDS_HUMAN_REVIEW |
| CHK_02 | An toàn kho quỹ | Chi nhánh loại 1 | HIGH | [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT \| Điều 12 \| doc_agr_at01_02]<br>[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá \| Điều 56. Trách nhiệm bảo vệ vận chuyển \| doc_44209_điều_56__trách_nhiệm_bảo_vệ_vận_chuyển_56] | NEEDS_HUMAN_REVIEW |
| CHK_03 | An toàn kho quỹ | Chi nhánh loại 1 | MEDIUM | [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT \| Điều 25 \| doc_agr_at01_03]<br>[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá \| Điều 62. Hội đồng kiểm kê, Hội đồng kiểm đếm, phân loại tiền \| doc_44209_điều_62__hội_đồng_kiểm_kê__hội_đồng_kiểm_đếm__phân_loại_tiền_62] | NEEDS_HUMAN_REVIEW |
| CHK_04 | An toàn kho quỹ | Chi nhánh loại 1 | MEDIUM | [100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT \| Điều 30 \| doc_agr_at01_04]<br>[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá \| Điều 26. Quy định ủy quyền của các thành viên tham gia quản lý tiền mặt, tài sản quý, giấy tờ có giá và kho tiền \| doc_44209_điều_26__quy_định_ủy_quyền_của_các_thành_viên_tham_gia_quản_lý_tiền_mặt__tài_sản_quý__giấy_tờ_có_giá_và_kho_tiền_26] | NEEDS_HUMAN_REVIEW |
| CHK_01 | Bảo mật CNTT & AI | Khối CNTT | HIGH | [600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT \| Điều 9 \| doc_agr_it07_01] | NEEDS_HUMAN_REVIEW |
| CHK_02 | Bảo mật CNTT & AI | Khối CNTT | HIGH | [600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT \| Điều 16 \| doc_agr_it07_02] | NEEDS_HUMAN_REVIEW |

```text
CHECKLIST GENERATOR ENGINE: PASS
CHECKLIST ITEMS GENERATED: 6
CITATIONS ATTACHED: YES
HUMAN REVIEW GUARDRAIL: PASS
```
