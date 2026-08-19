# SECURITY AUDIT REPORT

- Input: C:\RAG\Knowledge Graph mini\buoi_14\data\processed\chunks_secure.csv
- Valid roles: Admin, HR_Manager, Risk_Officer, Employee, Guest
- Total test cases: 5
- Passed: 5
- Failed: 0
- Security status: PASS

## Test Details

### guest_cannot_see_restricted_chunk_117310_0001
- Query: Quy định nội bộ về kiểm soát dữ liệu nhạy cảm
- Chunk ID: 117310-chunk-0001
- Unauthorized roles: ['Guest']
- Authorized roles: ['Admin', 'Risk_Officer', 'Employee']
- Unauthorized visible: False
- Authorized visible: True
- Status: PASS

### hr_manager_cannot_see_restricted_chunk_44209_0001
- Query: Hạn mức tín dụng và tiêu chí đánh giá rủi ro
- Chunk ID: 44209-chunk-0001
- Unauthorized roles: ['HR_Manager']
- Authorized roles: ['Admin', 'Risk_Officer', 'Employee']
- Unauthorized visible: False
- Authorized visible: True
- Status: PASS

### guest_cannot_see_restricted_chunk_173695_0001
- Query: Chính sách nội bộ và quyền truy cập dữ liệu
- Chunk ID: 173695-chunk-0001
- Unauthorized roles: ['Guest']
- Authorized roles: ['Admin', 'Risk_Officer', 'Employee']
- Unauthorized visible: False
- Authorized visible: True
- Status: PASS

### hr_manager_cannot_see_restricted_chunk_168220_0001
- Query: Dữ liệu giám sát và kiểm soát rủi ro
- Chunk ID: 168220-chunk-0001
- Unauthorized roles: ['HR_Manager']
- Authorized roles: ['Admin', 'Risk_Officer', 'Employee']
- Unauthorized visible: False
- Authorized visible: True
- Status: PASS

### guest_cannot_see_restricted_chunk_185630_0001
- Query: Quy trình nội bộ và chính sách bảo mật
- Chunk ID: 185630-chunk-0001
- Unauthorized roles: ['Guest']
- Authorized roles: ['Admin', 'Risk_Officer', 'Employee']
- Unauthorized visible: False
- Authorized visible: True
- Status: PASS

