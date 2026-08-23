# Secure Retrieval Test - Buoi 17

## Pham vi

Da tao adapter tai:

```text
buoi_17/scripts/secure_retrieval_adapter.py
```

Adapter khong copy hoac viet lai Hybrid/Rerank. Adapter goi lai:

- `load_secure_corpus`
- `filter_secure_corpus`
- `BM25Retriever` hien co

Corpus duoc doc read-only tu:

```text
../buoi_16/data/processed/chunks_secure.csv
```

## Luong xu ly

```text
question + user_role
        |
        v
load secure corpus
        |
        v
filter allowed_roles
        |
        v
chi dua authorized chunk vao BM25
        |
        v
retrieval result + metadata + citation
```

Neu khong co chunk duoc phep, adapter tra ve DataFrame rong co schema ket qua day du va khong chay retrieval tiep.

## Schema output

Adapter chuan hoa ket qua thanh cac truong:

```text
rank
chunk_id
document_id
title
article
citation
allowed_roles
access_decision
retrieval_method
text
retrieval_score
```

Citation duoc tao boi BM25 retriever hien co tu metadata that (`title`, `document_number`, `article`, `chunk_id`), khong tao citation gia.

## Test da chay

Query dung chung:

```text
quy dinh giao nhan bao quan van chuyen tien mat
```

Ket qua:

| Test | Ket qua |
|---|---|
| Adapter import | PASS |
| Role `Guest` co ket qua | PASS, 5 rows |
| Role `Guest`, moi chunk trong context co `Guest` | PASS |
| `rank`, `chunk_id`, `document_id` ton tai | PASS |
| `citation` ton tai va khong rong | PASS |
| `access_decision` cua ket qua duoc phep | `ALLOW` |
| Role `Staff` khong co quyen | PASS, 0 rows |
| Role `Staff` khong co context | PASS |

### Unauthorized chunk test

Da chon chunk:

```text
chunk_id: 44209-chunk-0001
allowed_roles: [Admin, Risk_Officer, Employee]
```

Chunk nay khong cap quyen cho `Guest`. Khi dung title cua chunk lam query voi role `Guest`:

```text
TARGET_IN_GUEST_CONTEXT: False
GUEST_CONTEXT_AUTHORIZED: True
```

Ket qua: chunk bi cam khong xuat hien trong context.

## Gioi han da ghi nhan

- Module Buoi 14 khong co class ten `SecureRetriever`; adapter goi lai cac ham RBAC hien co.
- Adapter hien tai ho tro method `bm25`, phu hop voi implementation secure co the tai su dung truc tiep.
- `RetrievalPipeline` thong thuong cua Buoi 14 khong tu dong filter `allowed_roles`; adapter phai la lop bao ngoai va duoc goi truoc retrieval.
- `source_url` khong duoc `filter_secure_corpus` giu lai, nen adapter dung metadata corpus goc de bao toan citation.

## Ket luan

```text
SECURE RETRIEVAL REUSE: PASS
NO UNAUTHORIZED CONTEXT: PASS
CITATION PRESERVED: PASS
```
