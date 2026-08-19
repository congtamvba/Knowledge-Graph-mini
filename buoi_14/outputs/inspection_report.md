# PROJECT PRE-CHECK

## Ket luan

- **Working root:** `C:\RAG\Knowledge Graph mini\buoi_14`
- **Data:** Da doc truc tiep du 3 CSV trong `..\kb+hops\`; khong copy, move, sua hoac ghi de.
- **Existing code:** Khong co file Python hoac pipeline cu trong `buoi_14/`.
- **Environment:** Python 3.11.2, interpreter `buoi_14\.venv\Scripts\python.exe`, import `pandas` thanh cong.
- **Potential risks:** Noi dung la HTML dai, mot so metadata bi khuyet, ID can duoc nap duoi dang chuoi, va `.env` chua secrets cuc bo.
- **Safe to continue:** **YES**

Bao cao nay chi kiem tra project va du lieu. Chua xay retrieval, reranking hay Knowledge Graph.

## 1. Cau truc va file hien co

```text
buoi_14/
|-- .venv/
|-- Prompt/
|   `-- buoi14.md
`-- outputs/
    `-- inspection_report.md

kb+hops/
|-- metadata.csv
|-- content.csv
`-- relationships.csv
```

| Pham vi | File |
|---|---|
| `buoi_14/` | `Prompt/buoi14.md` |
| Workspace root | `requirements.txt`, `.env` |
| Nguon chi doc | `../kb+hops/metadata.csv`, `content.csv`, `relationships.csv` |

Truoc khi tao bao cao, `buoi_14/` khong co file `.py`, `.csv`, `.json`, `requirements.txt` hoac `.env`. Thu muc `.venv/` la dependency ben thu ba, khong phai code cu cua project.

## 2. Tong quan du lieu nguon

Ca ba file deu doc thanh cong bang **UTF-8, khong BOM**. So dong khong tinh header.

| File | Dong | Cot | Dong trung lap | Encoding |
|---|---:|---:|---:|---|
| `metadata.csv` | 15 | 17 | 0 | UTF-8 |
| `content.csv` | 15 | 2 | 0 | UTF-8 |
| `relationships.csv` | 8 | 4 | 0 | UTF-8 |

### metadata.csv

Cot thuc te:

```text
id, title, so_ky_hieu, ngay_ban_hanh, loai_van_ban,
ngay_co_hieu_luc, ngay_het_hieu_luc, nguon_thu_thap,
ngay_dang_cong_bao, nganh, linh_vuc, co_quan_ban_hanh,
chuc_danh, nguoi_ky, pham_vi, thong_tin_ap_dung,
tinh_trang_hieu_luc
```

- Khoa uu tien: `id` (15/15 unique, khong null).
- `title` va `so_ky_hieu` cung unique trong tap hien tai, nhung nen la metadata thay vi khoa he thong.
- Khong co dong trung lap.

| Cot | Null |
|---|---:|
| `id`, `title`, `so_ky_hieu`, `ngay_ban_hanh`, `loai_van_ban` | 0 |
| `ngay_co_hieu_luc` | 1 |
| `ngay_het_hieu_luc` | 14 |
| `nguon_thu_thap` | 5 |
| `ngay_dang_cong_bao` | 11 |
| `nganh` | 3 |
| `linh_vuc` | 2 |
| `co_quan_ban_hanh`, `chuc_danh`, `nguoi_ky`, `pham_vi` | 0 |
| `thong_tin_ap_dung` | 15 |
| `tinh_trang_hieu_luc` | 0 |

Retrieval co the bo sung `title`, `so_ky_hieu`, `loai_van_ban`, `linh_vuc`, `co_quan_ban_hanh`; noi dung chinh van lay tu `content.csv`.

Citation nen giu `id`, `title`, `so_ky_hieu`, `loai_van_ban`, `ngay_ban_hanh`, `ngay_co_hieu_luc`, `co_quan_ban_hanh`, `tinh_trang_hieu_luc`, va `nguon_thu_thap` khi co gia tri. `thong_tin_ap_dung` rong 100%, khong nen la truong citation bat buoc.

### content.csv

Cot: `id`, `content_html`.

- Khoa: `id` (15/15 unique, khong null), dong thoi noi den `metadata.id`.
- Null: `id` = 0, `content_html` = 0.
- Khong co dong, ID hay noi dung trung lap.
- Truong retrieval: `content_html`, nhung phai parse thanh plain text truoc khi chunk/index; khong index HTML raw.
- Sau khi tach HTML: 15/15 van ban co text; do dai 21,864-310,500 ky tu, median 50,857.
- Citation: dung `id` de join metadata. Du lieu hien chua co `chunk_id`, so dieu hay offset citation.

Doi chieu `metadata.id` va `content.id` khop chinh xac 15/15; khong co ID chi xuat hien o mot bang.

### relationships.csv

Cot: `doc_id`, `other_doc_id`, `relationship`, `relationship_type`.

- Khoa canh ung vien: (`doc_id`, `other_doc_id`, `relationship_type`).
- Null: 0 tren moi cot.
- Dong trung lap: 0; canh trung theo khoa ung vien: 0; self-loop: 0.
- Ca hai dau mut cua ca 8 canh deu ton tai trong `metadata.id`; orphan: 0.
- `doc_id` unique trong tap hien tai, nhung khong nen coi la khoa lau dai vi mot van ban co the co nhieu quan he.

| `relationship_type` | Nhan | So luong |
|---|---|---:|
| `CAN_CU` | Can cu | 4 |
| `SUA_DOI_BO_SUNG` | Sua doi, bo sung | 1 |
| `VAN_BAN_BO_SUNG` | Van ban bo sung | 1 |
| `THAY_THE` | Thay the | 1 |
| `HOP_NHAT` | Hop nhat | 1 |

`relationship_type` phu hop lam loai canh, `relationship` lam nhan hien thi. Khong tu tao loai quan he nghiep vu ngoai du lieu hien co.

## 3. Kiem tra code va thao tac nguy hiem

Khong co code ung dung hien co trong `buoi_14/`, nen khong co luong doc/ghi cu, hard-code path, API key hay password trong code du an.

Ket qua tim theo pham vi file du an, loai tru `.venv/`:

- `os.remove`: khong co trong code du an.
- `shutil.rmtree`: khong co trong code du an.
- `open(..., "w")`: khong co trong code du an.
- `DELETE`, `DROP`, `DETACH DELETE`: khong co trong code du an.

`Prompt/buoi14.md` co nhac cac chuoi tren nhu huong dan, khong phai lenh dang chay. Ket qua ben trong `.venv/Lib/site-packages` thuoc dependency ben thu ba, khong phai code cu cua project.

Workspace root co `.env` chua cau hinh dich vu. Bao cao khong ghi gia tri bi mat; `.env` da duoc `.gitignore` bo qua. Code tuong lai phai doc bien moi truong va khong hard-code credential.

Khong co thao tac pha du lieu, copy, move, sua hoac ghi de ba CSV nguon.

## 4. Moi truong

| Hang muc | Ket qua |
|---|---|
| Python | 3.11.2 |
| Virtual environment | `C:\RAG\Knowledge Graph mini\buoi_14\.venv` |
| VS Code/Pylance interpreter | `buoi_14\.venv\Scripts\python.exe` |
| pandas | `2.2.3`, import OK |
| Dependency consistency | `pip check`: No broken requirements found |

## 5. Rui ro va rang buoc buoc sau

1. `content_html` rat dai va co markup; can parse co cau truc, normalize va chunk.
2. Corpus chua co `chunk_id`; Prompt 1 can tao ID chunk on dinh va duy nhat.
3. Tat ca ID can doc voi `dtype=str`; neu khong, pandas suy luan `other_doc_id` thanh so nguyen va co the lam loi join.
4. Cac metadata tuy chon co null; khong tu suy dien gia tri.
5. Chi su dung nam loai quan he thuc su co trong CSV.
6. `.env` chua secrets; khong log, commit hoac dua gia tri vao output.
7. Ba CSV trong `../kb+hops/` tiep tuc la read-only; moi processed data/output phai nam trong `buoi_14/`.

## 6. Dau van tay file nguon

Hash truoc va sau khi doc khong thay doi:

| File | SHA-256 |
|---|---|
| `metadata.csv` | `cb250e3a9341bb5cfcfb21fc4ae79a28149e7eb6f702209992562af5ffcdc25c` |
| `content.csv` | `fa7028f0a2c698cc5832cce90ee3655c2980cee4e5ef52a4b9c5dfb0ab4f2910` |
| `relationships.csv` | `50d6e4ca7725aa981dcd63b960cbc5927c472d3989100fa142d513a34909c5eb` |

---

```text
PROJECT PRE-CHECK

Working root: C:\RAG\Knowledge Graph mini\buoi_14
Data: 3/3 source CSV files read successfully; integrity checks passed
Existing code: None
Environment: Python 3.11.2; buoi_14/.venv; pandas import OK
Potential risks: HTML requires parsing/chunking; nullable metadata; IDs must remain strings
Safe to continue: YES
```
