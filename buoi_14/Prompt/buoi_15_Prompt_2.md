# BUỔI 15 - PROMPT 2: NẠP DỮ LIỆU BẢO MẬT VÀO NEO4J

```text
Tiếp tục bài thực hành Buổi 15: Cài đặt RBAC ở mức dữ liệu.

Chúng ta làm việc hoàn toàn trong thư mục:

buoi_14/

TUYỆT ĐỐI KHÔNG sửa, ghi đè hoặc xóa dữ liệu gốc trong:

../kb+hops/

Không xóa hoặc thay đổi dữ liệu Neo4j của Buổi 14 có:

lab_session = "buoi_14"

Các role hợp lệ duy nhất trong toàn bộ bài thực hành là:

- Admin
- HR_Manager
- Risk_Officer
- Employee
- Guest

NHIỆM VỤ

Hãy tạo script:

buoi_14/scripts/load_secure_kg.py

để đọc dữ liệu đã gắn quyền từ:

buoi_14/data/processed/chunks_secure.csv

và nạp một graph bảo mật riêng vào Neo4j với:

lab_session = "buoi_15"

Đồng thời tạo báo cáo:

buoi_14/outputs/secure_kg_load_report.md

1. KIỂM TRA INPUT

- Kiểm tra file chunks_secure.csv tồn tại.
- Đọc CSV bằng UTF-8 và giữ ID ở dạng string.
- Kiểm tra tối thiểu các cột:
  - chunk_id
  - document_id
  - text
  - title
  - document_type
  - article
  - status
  - allowed_roles
- Nếu thiếu file, thiếu cột, duplicate chunk_id hoặc dữ liệu rỗng thì báo lỗi và dừng.
- Parse allowed_roles từ JSON string thành List[str].
- Mọi allowed_roles phải không rỗng và chỉ chứa role thuộc danh sách hợp lệ.
- Không tạo dữ liệu giả khi input không hợp lệ.

2. ĐỌC CẤU HÌNH DATABASE

Đọc cấu hình Neo4j từ file cục bộ:

buoi_14/.env

Các biến bắt buộc:

- NEO4J_URI
- NEO4J_USER
- NEO4J_PASSWORD
- NEO4J_DATABASE

Không hard-code hoặc in password/token ra terminal và báo cáo.

3. SESSION ISOLATION

- Mọi node và relationship mới phải có:

  lab_session = "buoi_15"

- Dùng khóa MERGE gồm lab_session và id để không trùng với graph Buổi 14.
- Không cập nhật node có lab_session = "buoi_14".
- Trước và sau khi nạp, đếm node/cạnh Buổi 14 để xác minh counts không thay đổi.

4. NODE VÀ THUỘC TÍNH

Tạo hoặc cập nhật bằng MERGE:

(:VanBan)
- id
- title
- document_type
- status
- allowed_roles: List[str]
- lab_session: "buoi_15"
- source_file: "chunks_secure.csv"

(:DieuKhoan)
- id = chunk_id
- document_id
- text
- article
- document_type
- status
- allowed_roles: List[str]
- lab_session: "buoi_15"
- source_file: "chunks_secure.csv"

DieuKhoan.allowed_roles phải giữ nguyên đúng danh sách role của từng dòng chunks_secure.csv.

Vì một văn bản có thể chứa các chunk có quyền khác nhau, VanBan.allowed_roles phải được tính theo nguyên tắc fail-closed:

- Lấy giao (intersection) allowed_roles của tất cả chunk thuộc document_id.
- Ý nghĩa: các role này có quyền đọc toàn bộ văn bản.
- Quyền đọc một chunk cụ thể ở Prompt 3 phải kiểm tra DieuKhoan.allowed_roles; không được chỉ dựa vào VanBan.allowed_roles.

5. QUAN HỆ CẤU TRÚC

Tạo bằng MERGE:

(:VanBan)-[:CONTAINS]->(:DieuKhoan)
(:DieuKhoan)-[:NEXT]->(:DieuKhoan)

Yêu cầu:

- CONTAINS nối VanBan với mọi chunk cùng document_id.
- NEXT chỉ nối hai chunk liên tiếp trong cùng document_id theo thứ tự xuất hiện trong chunks_secure.csv.
- Mọi relationship có lab_session = "buoi_15" và source_file = "chunks_secure.csv".

6. AN TOÀN CYPHER

- Dùng parameterized Cypher cho dữ liệu.
- Dùng MERGE để script chạy lại không nhân đôi dữ liệu.
- Xử lý theo batch.
- TUYỆT ĐỐI KHÔNG dùng:

  MATCH (n) DETACH DELETE n
  DETACH DELETE
  DELETE
  DROP

- Không xóa dữ liệu Buổi 14 hoặc dữ liệu ngoài lab_session buoi_15.

7. KIỂM TRA SAU KHI NẠP

Sau khi ghi, chạy query kiểm tra thực tế:

- Số node VanBan của buoi_15.
- Số node DieuKhoan của buoi_15.
- Số VanBan có allowed_roles.
- Số DieuKhoan có allowed_roles.
- Số CONTAINS.
- Số NEXT.
- Số node có allowed_roles null/rỗng.
- Số role không hợp lệ trong Neo4j.
- Số DieuKhoan không có CONTAINS.
- Số node/cạnh thiếu lab_session.
- Counts Buổi 14 trước và sau có giữ nguyên hay không.

8. KIỂM TRA MẪU

Lấy ít nhất một VanBan của buoi_15 và tối đa ba DieuKhoan liên kết, hiển thị:

- VanBan.id
- VanBan.allowed_roles
- DieuKhoan.id
- DieuKhoan.allowed_roles

Không hiển thị credentials.

9. IDEMPOTENCY

- Chạy script thật.
- Chạy lại lần hai.
- Xác minh số node và relationship của buoi_15 không tăng sau lần hai.

10. BÁO CÁO

Ghi file:

buoi_14/outputs/secure_kg_load_report.md

và in kết quả dạng:

SECURE KG LOAD REPORT

Input:
buoi_14/data/processed/chunks_secure.csv

Database: <tên database, không in credentials>
Lab session: buoi_15
Roles: Admin, HR_Manager, Risk_Officer, Employee, Guest

VanBan nodes: ...
DieuKhoan nodes: ...
VanBan with allowed_roles: ...
DieuKhoan with allowed_roles: ...
CONTAINS relationships: ...
NEXT relationships: ...
Empty allowed_roles: ...
Invalid roles: ...
Orphan DieuKhoan: ...
Missing lab_session: ...
Buoi 14 preserved: YES/NO
Idempotent: YES/NO

Status: SUCCESS / FAILED

Nếu FAILED, giải thích chính xác nguyên nhân và không giả kết quả.

11. THỰC THI

Hãy:

1. Viết code load_secure_kg.py.
2. Chạy validation input.
3. Kết nối Neo4j từ buoi_14/.env.
4. Chạy script thật.
5. Chạy lại lần hai để kiểm tra idempotency.
6. Đọc lại Neo4j và báo counts thực tế.
7. Chạy tests/diagnostics liên quan.
8. Không bỏ qua lỗi.
```
