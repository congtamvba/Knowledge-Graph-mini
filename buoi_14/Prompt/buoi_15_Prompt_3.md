# BUỔI 15 - PROMPT 3: XÂY DỰNG BỘ LỌC TRUY VẤN AN TOÀN (SECURE RETRIEVAL PIPELINE)

```text
Tiếp tục bài thực hành Buổi 15. Hãy nâng cấp hệ thống tìm kiếm (Retrieval Pipeline) thành một hệ thống tìm kiếm an toàn (Secure Retrieval) trực tiếp trong thư mục `buoi_14/`.

Mục tiêu: xây dựng một bộ lọc truy vấn theo vai trò (RBAC) ở tầng dữ liệu để đảm bảo người dùng chỉ thấy các chunk mà họ được phép xem.

Toàn bộ code và dữ liệu phải nằm trong thư mục:

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

buoi_14/src/secure_retriever.py

dùng để xử lý truy vấn tìm kiếm có lọc quyền truy cập theo role và tích hợp vào pipeline nếu cần.

1. YÊU CẦU CHUNG

- Hàm tìm kiếm phải nhận vào hai tham số bắt buộc:
  - `query`: câu hỏi người dùng
  - `user_roles`: danh sách vai trò của người dùng hiện tại, ví dụ `["Guest"]` hoặc `["HR_Manager", "Admin"]`
- Đọc cấu hình database Neo4j từ file cục bộ:
  - `buoi_14/.env`
- Tất cả role phải hợp lệ theo danh sách quan định ở trên.
- Không được hard-code credentials hoặc in password/token ra terminal.
- Không được để dữ liệu nhạy cảm lọt qua mà không kiểm tra quyền.

2. LỌC QUYỀN THEO ROLE Ở MỨC CHUNK

Đảm bảo logic chính xác như sau:

- Mỗi chunk có trường `allowed_roles` trong `buoi_14/data/processed/chunks_secure.csv`.
- Khi người dùng gửi query, chỉ giữ lại các chunk mà có ít nhất một vai trò chung với `user_roles`.
- Quy tắc an toàn: nếu `allowed_roles` không hợp lệ hoặc không parse được, chunk phải bị loại bỏ.
- Không được dựa vào `VanBan.allowed_roles` để mở khóa truy cập chunk cụ thể.
- `VanBan.allowed_roles` chỉ là quyền xem toàn bộ văn bản, không phải quyền đọc một chunk riêng lẻ.

3. TÍCH HỢP VÀO CÁC PHƯƠNG PHÁP TÌM KIẾM

Cần tích hợp kiểm tra truy cập vào cả 3 phương thức chính sau:

### 3.1. BM25 Search
- Đọc dữ liệu từ `buoi_14/data/processed/chunks_secure.csv`.
- Lọc dataframe trước khi tính BM25 hoặc sau khi tính điểm.
- Chỉ giữ các hàng mà `allowed_roles` chứa ít nhất một role trong `user_roles`.

### 3.2. Dense Search
- Dùng vector embedding như trong Buổi 14.
- Thực hiện hậu lọc (post-filtering) hoặc tiền lọc metadata (nếu có thể) dựa trên `allowed_roles`.
- Không được cho phép kết quả nào không có quyền đọc đi qua bước reranker.

### 3.3. Graph Retrieval (Neo4j)
- Truy vấn Cypher phải kiểm tra:

```cypher
WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
```

- Chỉ truy vấn các `DieuKhoan` thuộc `lab_session = "buoi_15"`.
- Nếu query đến `VanBan`, chỉ dùng `VanBan.allowed_roles` như meta-role, nhưng quyền truy cập ở mức chunk vẫn phải kiểm tra `DieuKhoan.allowed_roles`.

4. HYBRID FUSION VÀ RERANKING

- Hybrid Fusion (RRF) chỉ làm việc trên các candidate đã vượt qua lọc quyền.
- Cross-Encoder Reranker cũng chỉ được xếp hạng trên các ứng viên đã hợp lệ về RBAC.
- Tuyệt đối không để một chunk bị cấm lọt vào danh sách được rerank.

5. CẤU TRÚC KẾT QUẢ TRẢ VỀ

Trả về kết quả chuẩn hóa theo kiểu của Buổi 14, nhưng thêm trường:

- `allowed_roles`

Ví dụ schema:

```python
{
  "rank": 1,
  "chunk_id": "...",
  "document_id": "...",
  "text": "...",
  "score": 0.123,
  "citation": "[...]",
  "retrieval_method": "bm25|dense|hybrid|hybrid_rerank",
  "allowed_roles": ["Admin", "HR_Manager"]
}
```

6. THỰC THI NHIỆM VỤ

Hãy:

1. Viết file `buoi_14/src/secure_retriever.py`.
2. Tạo/kiểm tra các hàm chính:
   - `parse_allowed_roles()`
   - `user_has_access()`
   - `filter_secure_corpus()`
   - `load_secure_corpus()`
   - `graph_visible_chunks()`
3. Đảm bảo `user_roles` không rỗng, không chứa vai trò không hợp lệ.
4. Chạy validation dữ liệu khóa và test logic RBAC cơ bản.
5. Nếu file `.env` hoặc Neo4j không sẵn sàng, trả về rõ ràng trạng thái lỗi nhưng không giả dữ liệu.
6. Viết báo cáo ngắn gọn hoặc in log đầy đủ về hiệu suất lọc quyền và số lượng chunk được giữ lại cho từng vai trò.

7. KIỂM THỬ BẢO MẬT CƠ BẢN

Thực hiện ít nhất các test sau:

- Guest chỉ thấy chunk có `Guest` trong `allowed_roles`
- Admin thấy nhiều hơn Guest
- Role không hợp lệ phải báo lỗi và không chạy tiếp
- Chunk có `allowed_roles = []` hoặc `null` phải bị từ chối
- Khi `user_roles = ["Admin"]`, phải giữ lại những chunk mà có quyền `Admin`

8. BÁO CÁO KẾT QUẢ

Sau khi thực hiện, hãy in ra một báo cáo dạng:

```text
SECURE RETRIEVAL REPORT
- Input: buoi_14/data/processed/chunks_secure.csv
- Roles checked: ...
- Visible chunks for Guest: ...
- Visible chunks for Admin: ...
- Graph-filtered chunks: ...
- Security status: PASS / FAIL
```

9. QUY TẮC AN TOÀN

- Không dùng `MATCH (n) DETACH DELETE n`
- Không dùng `DELETE`, `DROP` để xóa dữ liệu graph
- Không thay đổi graph Buổi 14
- Không cho phép data leakage
- Mọi tìm kiếm phải fail-closed

10. CHÍNH XÁC VỀ NHIỆM VỤ

Bạn phải làm đúng theo hướng dẫn của Prompt 2 về dữ liệu bảo mật và đúng theo hướng dẫn của Prompt 3 về secure retrieval pipeline.

Mục tiêu là đảm bảo hệ thống tìm kiếm có bảo vệ phân quyền ở mức dữ liệu, không chỉ là hiển thị UI.

Hãy thực thi thật, không làm giả kết quả, không bỏ qua lỗi, và báo cáo số liệu thực tế sau khi chạy.
```
