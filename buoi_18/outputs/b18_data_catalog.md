# Buổi 18 - Data Catalog

## 1. Phạm vi và phương pháp

Báo cáo được lập từ hai tệp dữ liệu:

- `data/agribank_internal_policies.csv`
- `data/chunks_combined_secure.csv`

Các tệp nguồn được đọc ở chế độ chỉ đọc. Dataset không có cột `domain` riêng, vì vậy domain/nghiệp vụ được phân loại dựa trên `title`, `so_ky_hieu` và nội dung điều khoản trong cột `text`. Không có dữ liệu nguồn nào bị sửa đổi.

## 2. Tổng quan dữ liệu

| Tệp | Số chunk | Số văn bản duy nhất | Số cột |
|---|---:|---:|---:|
| `agribank_internal_policies.csv` | 24 | 10 | 14 |
| `chunks_combined_secure.csv` | 811 | 25 | 14 |

Tập kết hợp gồm 10 văn bản nội bộ Agribank và 15 văn bản pháp luật/văn bản bên ngoài.

## 3. 14 trường metadata

Schema được xác nhận đầy đủ trong cả hai tệp:

1. `chunk_id`
2. `document_id`
3. `text`
4. `source_file`
5. `title`
6. `so_ky_hieu`
7. `loai_van_ban`
8. `co_quan_ban_hanh`
9. `ngay_ban_hanh`
10. `chapter`
11. `section`
12. `article`
13. `citation`
14. `allowed_roles`

| Kiểm tra | Internal policies | Combined data |
|---|---:|---:|
| Đủ 14 cột | PASS | PASS |
| `article` không rỗng | 24/24 | 811/811 |
| `citation` không rỗng | 24/24 | 811/811 |
| `allowed_roles` không rỗng | 24/24 | 811/811 |

## 4. Catalog văn bản nội bộ Agribank

| # | Document ID | Tiêu đề | Số ký hiệu | Loại | Ngày ban hành | Domain/nghiệp vụ |
|---:|---|---|---|---|---|---|
| 1 | `agr_at01` | Quy định nội bộ số 100/QĐ-NHNO-AT về Giao nhận, bảo quản, vận chuyển tiền mặt và tài sản quý Agribank | `100/QĐ-NHNO-AT` | Quy định nội bộ | 15/03/2024 | An toàn kho quỹ và vận chuyển tiền |
| 2 | `agr_car02` | Quy định nội bộ số 250/QĐ-NHNO-QLRR về Quản lý tỷ lệ an toàn vốn và định mức rủi ro Agribank | `250/QĐ-NHNO-QLRR` | Quy định nội bộ | 20/06/2024 | CAR và quản lý rủi ro |
| 3 | `agr_td03` | Quy chế tín dụng nội bộ số 315/QC-NHNO-TD về Phán quyết và Phân cấp ủy quyền cho vay tại Agribank | `315/QC-NHNO-TD` | Quy chế nội bộ | 10/01/2024 | Tín dụng và thẩm quyền phê duyệt |
| 4 | `agr_fx04` | Quy định nội bộ số 410/QĐ-NHNO-TTNH về Quản lý trạng thái ngoại tệ và giao dịch ngoại hối Agribank | `410/QĐ-NHNO-TTNH` | Quy định nội bộ | 05/09/2024 | Ngoại tệ và giao dịch ngoại hối |
| 5 | `agr_gp05` | Quy chế số 520/QC-NHNO-MANGLUOI về Mở rộng mạng lưới chi nhánh và phòng giao dịch Agribank | `520/QC-NHNO-MANGLUOI` | Quy chế nội bộ | 18/11/2024 | Mạng lưới chi nhánh và phòng giao dịch |
| 6 | `agr_bh06` | Quy định nội bộ số 180/QĐ-NHNO-BH về Mua bảo hiểm rủi ro nghiệp vụ và tài sản Agribank | `180/QĐ-NHNO-BH` | Quy định nội bộ | 14/02/2024 | Bảo hiểm rủi ro nghiệp vụ và tài sản |
| 7 | `agr_it07` | Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT về An toàn thông tin và Quản trị dữ liệu AI Agribank | `600/QC-NHNO-CNTT` | Quy chế nội bộ | 01/03/2025 | Bảo mật CNTT, dữ liệu và AI |
| 8 | `agr_hr08` | Quy định nội bộ số 88/QĐ-NHNO-NS về Quy hoạch, bổ nhiệm và quản lý nhân sự Agribank | `88/QĐ-NHNO-NS` | Quy định nội bộ | 10/01/2025 | Nhân sự và thẩm quyền bổ nhiệm |
| 9 | `agr_tc09` | Quy chế tài chính số 720/QC-NHNO-TC về Chế độ chi tiêu và mua sắm tài sản nội bộ Agribank | `720/QC-NHNO-TC` | Quy chế nội bộ | 05/12/2024 | Tài chính và mua sắm nội bộ |
| 10 | `agr_xln10` | Quy định nội bộ số 390/QĐ-NHNO-XLN về Phân loại nợ và Xử lý nợ xấu tại Agribank | `390/QĐ-NHNO-XLN` | Quy định nội bộ | 22/07/2024 | Phân loại nợ và xử lý nợ xấu |

**Cơ quan ban hành:** Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) cho toàn bộ 24 chunk nội bộ.

**Phân bố loại văn bản nội bộ:**

- Quy định nội bộ: 15 chunk
- Quy chế nội bộ: 9 chunk

## 5. Phân loại domain/nghiệp vụ

| Domain | Văn bản nội bộ liên quan | Tín hiệu phân loại |
|---|---|---|
| An toàn kho quỹ và vận chuyển tiền | `agr_at01` | Giao nhận, kiểm đếm, bảo quản, vận chuyển tiền mặt, tài sản quý, xe bọc thép |
| CAR và quản lý rủi ro | `agr_car02` | Tỷ lệ an toàn vốn tối thiểu, định mức rủi ro, tài sản có rủi ro |
| Tín dụng và thẩm quyền phê duyệt | `agr_td03` | Phán quyết tín dụng, hạn mức cho vay, phân cấp ủy quyền |
| Ngoại tệ và giao dịch ngoại hối | `agr_fx04` | Trạng thái ngoại tệ, hạn mức và giao dịch ngoại hối |
| Mạng lưới chi nhánh và phòng giao dịch | `agr_gp05` | Mở rộng mạng lưới, thành lập chi nhánh và phòng giao dịch |
| Bảo hiểm rủi ro nghiệp vụ và tài sản | `agr_bh06` | Mua bảo hiểm, phạm vi bảo hiểm, tài sản và rủi ro nghiệp vụ |
| Bảo mật CNTT, dữ liệu và AI | `agr_it07` | An toàn thông tin, kiểm soát truy cập, mã hóa, quản trị dữ liệu AI |
| Nhân sự và thẩm quyền bổ nhiệm | `agr_hr08` | Quy hoạch, bổ nhiệm, quản lý và phân quyền nhân sự |
| Tài chính và mua sắm nội bộ | `agr_tc09` | Chế độ chi tiêu, ngân sách, mua sắm và tài sản nội bộ |
| Phân loại nợ và xử lý nợ xấu | `agr_xln10` | Phân loại nợ, thu hồi và xử lý khoản nợ xấu |

**Số domain phát hiện:** 10

## 6. Phân bố tập dữ liệu kết hợp

### Theo loại văn bản

| Loại văn bản | Số chunk |
|---|---:|
| Nghị định | 300 |
| Thông tư | 257 |
| Luật | 184 |
| Văn bản hợp nhất | 46 |
| Quy định nội bộ | 15 |
| Quy chế nội bộ | 9 |
| **Tổng cộng** | **811** |

### Theo cơ quan ban hành

| Cơ quan ban hành | Số chunk |
|---|---:|
| Chính phủ | 300 |
| Ngân hàng Nhà nước Việt Nam | 281 |
| Quốc hội | 184 |
| Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 24 |
| Bộ Tài chính | 22 |
| **Tổng cộng** | **811** |

### Phạm vi quyền truy cập trong metadata

Các giá trị `allowed_roles` đang có trong tập kết hợp:

- `Admin`, `HR`: 382 chunk
- `Admin`, `Risk_Manager`, `Staff`: 256 chunk
- `Admin`, `HR`, `Risk_Manager`, `Staff`, `Guest`: 162 chunk
- `Admin`, `Risk_Manager`: 11 chunk

Metadata quyền đã được nạp đầy đủ và có thể dùng làm điều kiện lọc RBAC trước retrieval/context.

## 7. Đánh giá mức độ sẵn sàng

- Dữ liệu nội bộ Agribank: PASS
- Dữ liệu pháp lý và nội bộ kết hợp: PASS
- Schema 14 trường metadata: PASS
- `article`, `citation`, `allowed_roles`: PASS
- Phân loại domain/nghiệp vụ: PASS
- Sẵn sàng làm đầu vào cho UC3 và UC4: PASS

DATA CATALOGING: PASS
DOMAINS DETECTED: 10
READY FOR UC3 & UC4: YES
