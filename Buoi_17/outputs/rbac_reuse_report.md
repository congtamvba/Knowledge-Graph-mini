# RBAC Reuse Report - Buoi 17

## Pham vi

Da tiep tuc dung corpus read-only:

```text
../buoi_16/data/processed/chunks_secure.csv
```

Khong tao policy moi va khong sua du lieu Buoi 16.

## Role co trong corpus

Cac role hop le trong `allowed_roles`:

```text
Admin
Employee
Guest
HR_Manager
Risk_Officer
```

Thong ke so chunk co moi role:

| Role | So chunk |
|---|---:|
| Admin | 1242 |
| Employee | 1155 |
| Guest | 783 |
| HR_Manager | 870 |
| Risk_Officer | 1155 |

Tat ca 1242 dong `allowed_roles` deu parse thanh cong, khong co dong loi format.

Prompt yeu cau test role `Staff`, nhung `Staff` khong ton tai trong corpus va khong nam trong danh sach role hop le. Role tuong ung dang co trong du lieu la `Employee`.

## Module tai su dung

Module RBAC hien co tai:

```text
buoi_14/src/secure_retriever.py
```

Cac ham tai su dung:

- `load_secure_corpus(path)`
- `parse_allowed_roles(value)`
- `user_has_access(allowed_roles, user_roles)`
- `filter_secure_corpus(corpus, user_roles)`

Khong tim thay class ten `SecureRetriever`. Cac ham tren la implementation secure retrieval/RBAC dang co va co the duoc goi lai tu Buoi 17.

## Input va output

- Input role: danh sach role, vi du `['Admin']`.
- Input corpus: DataFrame co cot `allowed_roles`.
- Output khi co chunk duoc phep: DataFrame co `chunk_id`, `document_id`, `text`, `title`, `document_type`, `article`, `status`, `allowed_roles`.
- `source_url` khong duoc giu trong output cua `filter_secure_corpus`; day la citation alias can duoc bo sung khi adapter chuan hoa ket qua.

## Test cung mot query

Query dung cho tat ca role:

```text
quy dinh giao nhan bao quan van chuyen tien mat
```

De kiem tra filter truoc retrieval, corpus day du duoc loc theo `chunk_id` authorized truoc, sau do dung `BM25Retriever` hien co tren tap da loc.

| Role | Chunk duoc phep | Ket qua |
|---|---:|---|
| Admin | 1242 | 3/3 top result authorized |
| HR_Manager | 870 | 3/3 top result authorized |
| Risk_Officer | 1155 | 3/3 top result authorized |
| Employee | 1155 | 3/3 top result authorized |
| Staff | 0 | Retrieval khong chay, default deny |
| Guest | 783 | 3/3 top result authorized |

Khong co unauthorized chunk trong ket qua retrieval cua cac role co quyen.

## Unknown role va edge case

`Staff` khong match bat ky `allowed_roles` nao, nen ket qua la tap rong. Day la hanh vi default deny: **PASS**.

Phat hien mot gioi han interface: khi tap loc rong, `filter_secure_corpus` tra ve DataFrame rong khong co cot. Neu code tiep theo truy cap `filtered['chunk_id']` se gap `KeyError`. Adapter Buoi 17 can kiem tra `filtered.empty` truoc khi doc cot va tra ve ket qua DENY rong.

## Vi tri filter

`filter_secure_corpus` thuc hien loc `allowed_roles` truoc khi cac ket qua duoc dua vao BM25 trong bai test nay. Vi vay khong co chunk unauthorized vao tap retrieval/context.

Tuy nhien, `buoi_14/src/retrieval.py` (`RetrievalPipeline`) hien tai doc `chunks_normalized.csv` va khong tu dong goi `filter_secure_corpus`. Viec filter truoc retrieval chi duoc dam bao khi caller/orchestration cua Buoi 17 goi helper nay truoc pipeline.

## Ket luan va reuse plan

```text
RBAC REUSED: YES
FILTER BEFORE RETRIEVAL: PASS khi caller goi filter truoc retrieval
UNKNOWN ROLE DEFAULT DENY: PASS
```

Ke hoach:

1. Tiep tuc tai su dung cac ham RBAC cua Buoi 14.
2. Khong copy hoac viet lai Hybrid/BM25/Rerank.
3. O Buoi 17, dung adapter/orchestration de filter corpus truoc retrieval.
4. Xu ly tap rong truoc khi truy cap cot, tra ve access decision DENY.
5. Bao toan citation bang cach map `source_url` thanh citation sau khi filter, vi khong sua corpus nguon.
