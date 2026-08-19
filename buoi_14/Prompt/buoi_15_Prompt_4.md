# BUỔI 15 - PROMPT 4: TÍCH HỢP PHÂN QUYỀN VÀO STREAMLIT WEB APP

```text
Tiếp tục bài thực hành Buổi 15. Hãy nâng cấp giao diện Streamlit Web App của chúng ta để minh họa trực quan tính năng kiểm soát truy cập dữ liệu.

Nhiệm vụ: Tạo hoặc cập nhật file `buoi_14/app_secure.py`.

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

Hãy tạo hoặc cập nhật giao diện Streamlit để cho phép người dùng chọn vai trò và thực hiện truy vấn tìm kiếm theo mô hình an toàn.

1. YÊU CẦU GIAO DIỆN

- Dùng Streamlit.
- Giữ nguyên cấu hình của Buổi 14 như `Method`, `Top-k`, `Câu hỏi`.
- Bổ sung một mục mới trong sidebar:
  - **Vai trò của bạn (Your Roles)**
  - dạng `multiselect`
  - cho phép người dùng chọn một hoặc nhiều vai trò trong danh sách hợp lệ.

2. YÊU CẦU CHỨC NĂNG

- Khi người dùng nhập câu hỏi và bấm tìm kiếm, ứng dụng sẽ:
  - đọc `user_roles` từ sidebar
  - gọi `secure_retriever.py` hoặc logic lọc quyền tương đương
  - lọc kết quả truy vấn theo quyền truy cập dữ liệu trước khi hiển thị

3. BẢO MẬT VÀ LỌC QUYỀN

- Chỉ hiển thị các chunk mà người dùng có quyền đọc:
  - tức là `allowed_roles` của chunk phải có ít nhất một vai trò nằm trong `user_roles`.
- Nếu một số kết quả bị loại do không đủ quyền, hiển thị cảnh báo hoặc thống kê nhỏ như:

```text
Đã lọc bỏ X kết quả do không đủ quyền truy cập.
```

- Không được hiển thị dữ liệu nhạy cảm cho role không có quyền.
- Không được dựa vào `VanBan.allowed_roles` để bỏ qua lọc ở mức chunk.

4. HIỂN THỊ KẾT QUẢ

- Hiển thị danh sách kết quả theo dạng chuẩn của Buổi 14.
- Thêm thông tin rõ ràng:
  - `Quyền xem: [...]`
  - `Document ID`
  - `Chunk ID`
  - `Method`
  - `Score`
  - `Citation`
- Nếu có dữ liệu bị ẩn, hiển thị `filtered_out_count` rõ ràng.

5. GRAPH HINTS CÓ BẢO MẬT

- Nếu Graph Hints được render, chỉ hiển thị các document/chunk mà người dùng có quyền xem.
- Nếu Neo4j không sẵn sàng, hiện trạng thái lỗi cụ thể nhưng không làm hỏng app.

6. THỰC THI NHIỆM VỤ

Hãy:

1. Tạo file `buoi_14/app_secure.py`.
2. Dùng danh sách `VALID_ROLES` từ `buoi_14/src/config.py`.
3. Tạo helper `apply_role_filter()` để lọc kết quả bằng `allowed_roles`.
4. Tạo UI sidebar với `multiselect` cho vai trò.
5. Gọi Retrieval Pipeline theo `method` đang chọn.
6. Giữ lại `allowed_roles` trong kết quả hiển thị để người dùng dễ kiểm tra.
7. Thực thi và báo cáo hiệu quả kiểm thử ban đầu.

7. QUY TẮC AN TOÀN

- Luôn fail-closed.
- Không truy xuất dữ liệu ngoài quyền.
- Không dùng `DELETE`, `DETACH DELETE`, `DROP` trong app.
- Không thay đổi graph Buổi 14.
- Không in password/token hoặc credentials ra console/UI.

8. BÁO CÁO KẾT QUẢ

Sau khi chạy ứng dụng, hãy in ra/hiển thị trạng thái tương tự:

```text
SECURE APP REPORT
- Selected roles: ...
- Results returned: ...
- Results filtered out: ...
- Security status: PASS / FAIL
```

Hãy thực hiện thật, không giả dữ liệu, không bỏ qua lỗi, và không thay đổi dữ liệu gốc.
```
