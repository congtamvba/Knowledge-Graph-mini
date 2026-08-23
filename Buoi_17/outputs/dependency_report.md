# Dependency Report - Buoi 17

## Pham vi kiem tra

Da doc read-only cac file:

- `buoi_16/data/processed/chunks_secure.csv`
- `buoi_16/data/processed/chunks_normalized.csv`
- `buoi_14/src/secure_retriever.py`
- `buoi_14/src/retrieval.py`

Khong sua corpus Buoi 16 va khong tao policy moi.

## Moi truong

- Python: `3.11.2`
- Virtual environment: `buoi_14/.venv`
- Dependency chinh import duoc: `pandas 2.2.3`, `python-dotenv`, `neo4j 5.28.1`
- File `buoi_17/.env`: ton tai va co cac bien cau hinh can thiet.
- Neo4j: chua ket noi trong Prompt 0 vi chua co buoc dung Neo4j.

## Source data

### `chunks_secure.csv`

- So dong: `1242`
- So cot: `16`
- Cac cot:

```text
chunk_id, document_id, text, source_file, title, document_number,
document_type, chapter, section, article, effective_date, issue_date,
status, issuing_authority, source_url, allowed_roles
```

### `chunks_normalized.csv`

- So dong: `1242`
- So cot: `15`
- Cac cot:

```text
chunk_id, document_id, text, source_file, title, document_number,
document_type,
chapter, section, article, effective_date, issue_date, status,
issuing_authority, source_url
```

### So sanh

- Hai file co cung so dong: **YES**
- Cac cot chung giong nhau theo tung dong: **YES**
- Cot chi co trong `chunks_secure.csv`: `allowed_roles`
- Cot chi co trong `chunks_normalized.csv`: khong co
- Ket luan: `chunks_secure.csv = chunks_normalized.csv + allowed_roles`
- `chunk_id` unique: **YES**
- `document_id` unique: **NO**, vi mot document co the co nhieu chunk; day la binh thuong.

Du lieu thuc te khac so lieu ky vong trong tai lieu (1242 dong, 16/15 cot thay vi 787 dong, 14/13 cot), nhung cau truc hai file van nhat quan.

## Metadata mapping

Mot so ten truong trong yeu cau khac voi ten truong thuc te:

| Yeu cau | Truong thuc te | Trang thai |
|---|---|---|
| `chunk_id` | `chunk_id` | Co |
| `document_id` | `document_id` | Co |
| `citation` | `source_url` | Alias, khong co cot `citation` |
| `title` | `title` | Co |
| `loai_van_ban` | `document_type` | Alias |
| `co_quan_ban_hanh` | `issuing_authority` | Alias |
| `ngay_ban_hanh` | `issue_date` | Alias |
| `allowed_roles` | `allowed_roles` | Co |

Mau metadata dau tien:

```text
chunk_id: 44209-chunk-0001
document_id: 44209
title: Thong tu so 01/2014/TT-NHNN Quy dinh ve giao nhan, bao quan, van chuyen tien mat, tai san quy, giay to co gia
document_type: Thong tu
issuing_authority: Ngan hang Nha nuoc Viet Nam
issue_date: 06/01/2014
source_url: Cong bao so 891 + 892
allowed_roles: [Admin, Risk_Officer, Employee]
```

## RBAC va Secure Retrieval

Module [buoi_14/src/secure_retriever.py](../../buoi_14/src/secure_retriever.py) co cac ham chinh:

- `load_secure_corpus(path)` doc CSV secure va kiem tra cac cot bat buoc.
- `parse_allowed_roles(value)` parse JSON role list, loai role khong hop le.
- `user_has_access(allowed_roles, user_roles)` tra ve `False` neu role rong, sai hoac khong co quyen.
- `filter_secure_corpus(corpus, user_roles)` chi giu cac chunk ma user co quyen.

### Input va output

- Input role: danh sach role, vi du `['Admin']`.
- Input corpus: DataFrame co `allowed_roles`.
- Output: DataFrame chi gom cac chunk duoc phep; giu `chunk_id`, `document_id`, `text`, `title`, `document_type`, `article`, `status`, `allowed_roles`.
- `filter_secure_corpus` khong giu lai `source_url`, do do citation dang alias `source_url` se bi mat neu goi ham nay truc tiep.

### Ket qua RBAC

- `Admin`: 1242 chunk
- `HR_Manager`: 870 chunk
- `Risk_Officer`: 1155 chunk
- `Employee`: 1155 chunk
- `Guest`: 783 chunk
- Parse `allowed_roles`: 1242/1242 dong thanh cong
- Unknown role khong co quyen: **PASS**

### Vi tri filter

Ham `filter_secure_corpus` thuc hien loc `allowed_roles` truoc khi ket qua duoc dua vao lop retrieval neu caller dung ham nay lam buoc tien xu ly. Tuy nhien, `buoi_14/src/retrieval.py` hien tai la `RetrievalPipeline` thong thuong, doc `chunks_normalized.csv` va khong tu dong goi `filter_secure_corpus`.

Vi vay:

- RBAC helper co the tai su dung: **YES**
- Class ten `SecureRetriever`: **KHONG TIM THAY**
- Secure retrieval pipeline da tich hop san: **CHUA CO**
- Can adapter/orchestration o Buoi 17 de goi filter secure truoc `RetrievalPipeline`.

## Test da chay

```text
3 tests SecureRetriever helpers: PASS
```

Cac test xac nhan parse role, Guest access va Admin access deu hoat dong.

## Ket luan

```text
SOURCE DATA: PASS
RBAC DATA AVAILABLE: YES
SECURE RETRIEVER REUSABLE: PARTIAL
REUSE PLAN: Tai su dung load_secure_corpus, parse_allowed_roles,
             user_has_access va filter_secure_corpus tu Buoi 14;
             dung RetrievalPipeline Hybrid/Rerank hien co sau buoc RBAC;
             tao adapter o Buoi 17 neu can chuan hoa output va bao toan citation.
```

Ghi chu: Prompt 0 yeu cau cac ten cot legacy (`citation`, `loai_van_ban`, `co_quan_ban_hanh`, `ngay_ban_hanh`), trong khi corpus hien tai dung cac ten tuong ung (`source_url`, `document_type`, `issuing_authority`, `issue_date`). Khong sua source data de doi ten cot.
