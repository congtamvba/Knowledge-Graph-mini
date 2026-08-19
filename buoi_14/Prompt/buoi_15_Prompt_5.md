# BUỔI 15 - PROMPT 5: KIỂM THỬ RÒ RỈ DỮ LIỆU BẢO MẬT (SECURITY AUDIT)

```text
Tiếp tục bài thực hành Buổi 15. Hãy viết một script kiểm định bảo mật tự động để đảm bảo hệ thống không bị rò rỉ dữ liệu (data leakage).

Nhiệm vụ: Tạo file `buoi_14/scripts/security_audit.py`.

Toàn bộ code triển khai trực tiếp trong thư mục `buoi_14/`.

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

Hãy phát triển một bộ kiểm thử tự động để chứng minh hệ thống không bao giờ trả về dữ liệu mà người dùng không được phép xem.

1. YÊU CẦU CHUNG

- Script phải đọc dữ liệu từ `buoi_14/data/processed/chunks_secure.csv`.
- Dùng logic `allowed_roles` để xác minh quyền xem trên từng chunk.
- Dùng danh sách role hợp lệ từ `buoi_14/src/config.py`.
- Đọc `.env` trong `buoi_14/` nếu cần truy vấn Neo4j.
- Không hard-code credentials hoặc in password/token ra terminal/report.
- Không xóa hoặc thay đổi graph buổi 14.

2. YÊU CẦU TESTCASE

Viết ít nhất 5 test case tự động. Mỗi test case phải gồm:

- `query`: câu hỏi có chứa từ khóa nhạy cảm
- `target_sensitive_document_id`: mã văn bản nhạy cảm cần kiểm tra
- `unauthorized_roles`: các vai trò KHÔNG được phép đọc tài liệu ấy
- `authorized_roles`: các vai trò được phép đọc tài liệu ấy

Ví dụ:

- query: "Bảng lương cấp quản lý"
- target_sensitive_document_id: "HR-001"
- unauthorized_roles: ["Guest", "Employee"]
- authorized_roles: ["Admin", "HR_Manager"]

3. KIỂM THỬ MỘT BẢN CÓ THỂ THẤY DỮ LIỆU NHẠY CẢM

Với mỗi test case:

- Chạy truy vấn với `unauthorized_roles`.
- Assert rằng kết quả trả về Top-K không chứa chunk nào thuộc `target_sensitive_document_id`.
- Nếu một chunk bị rò rỉ, test fail.

4. KIỂM THỬ MỘT BẢN ĐƯỢC PHÉP TRUY CẬP

- Chạy truy vấn với `authorized_roles`.
- Xác nhận rằng dữ liệu nhạy cảm có thể xuất hiện trong top-K nếu nó phù hợp với câu hỏi.
- Nếu không xuất hiện vì query không phù hợp, script phải báo “not triggered” và không coi đó là fail nếu dữ liệu tương ứng không nằm trong ngữ cảnh câu hỏi.

5. TÍCH HỢP DỮ LIỆU NEO4J

- Nếu Neo4j sẵn sàng, script có thể chạy kiểm tra bằng Cypher với điều kiện:

```cypher
WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
```

- Nếu Neo4j không sẵn sàng, script phải ghi rõ lỗi và tiếp tục test trên dataset CSV tương ứng.
- Không được giả dữ liệu.

6. BÁO CÁO OUTPUT

Xuất ra file:

`buoi_14/outputs/security_audit_report.md`

và in ra terminal theo cấu trúc sau:

```text
SECURITY AUDIT REPORT
- Input: buoi_14/data/processed/chunks_secure.csv
- Valid roles: Admin, HR_Manager, Risk_Officer, Employee, Guest
- Total test cases: ...
- Passed: ...
- Failed: ...
- Security status: PASS / FAIL
```

7. THỰC THI NHIỆM VỤ

Hãy:

1. Viết file `buoi_14/scripts/security_audit.py`.
2. Tạo ít nhất 5 test case thật.
3. Thiết kế hàm `run_security_audit()`
4. Ghi báo cáo ra `outputs/security_audit_report.md`
5. Chạy và xác nhận kết quả thực tế.
6. Không bỏ qua lỗi.

8. QUY TẮC AN TOÀN

- Luôn fail-closed.
- Không cho phép data leakage.
- Không dùng `DETACH DELETE`, `DELETE`, `DROP`.
- Không thay đổi dữ liệu Buổi 14.
- Không in password hoặc token ra console/report.

9. KẾT LUẬN

Hãy làm đúng theo hướng dẫn của Prompt 2 và Prompt 3: quyền truy cập phải được kiểm tra ở mức dữ liệu, không chỉ ở UI.

Khi hoàn thành, hãy in báo cáo đủ chi tiết và không giả kết quả.
```
