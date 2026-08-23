# Gap Input Catalog - Buoi 17

> **P6 RERUN UPDATE (2026-08-24):** Phan duoi day cap nhat ket qua sau khi bo sung nguon `Buoi_17/data/agribank_internal_policies.csv` va dung `Buoi_17/data/chunks_combined_secure.csv` lam corpus hop nhat. Ket luan P6 rerun o cuoi file thay the ket luan data-gap truoc do.

## Pham vi va nguyen tac

Nguon du lieu read-only:

```text
../buoi_16/data/processed/chunks_secure.csv
```

Phan loai chi dua tren metadata that trong corpus. Khong coi van ban phap luat ben ngoai la `INTERNAL_POLICY` va khong tao gap finding khi corpus khong co evidence noi bo.

## Tong quan

- Tong so chunk: `1242`
- Tong so document: `15`
- `document_type`:
  - Thong tu: `9`
  - Nghi dinh: `3`
  - Luat: `2`
  - Van ban hop nhat: `1`
- `issuing_authority`:
  - Ngan hang Nha nuoc Viet Nam: `9`
  - Chinh phu: `3`
  - Quoc hoi: `2`
  - Bo Tai chinh: `1`
- Cot citation theo yeu cau khong ton tai; truong citation tuong ung trong corpus la `source_url`.
- Cac truong tuong ung khac:
  - `so_ky_hieu` -> `document_number`
  - `loai_van_ban` -> `document_type`
  - `co_quan_ban_hanh` -> `issuing_authority`
  - `ngay_ban_hanh` -> `issue_date`

## Phan loai document

Tat ca document duoc phan loai la `EXTERNAL_REQUIREMENT` vi co it nhat mot bang chung sau: loai van ban phap luat, so van ban, co quan ban hanh cap nha nuoc, hoac tieu de quy dinh/thong tu/nghi dinh/luat. Khong co document nao du bang chung de phan loai `INTERNAL_POLICY`.

| document_id | title | document_number | document_type | issuing_authority | issue_date | chunk_count | classification | evidence |
|---|---|---|---|---|---|---:|---|---|
| 112025 | Nghi dinh so 73/2016/NĐ-CP Quy dinh chi tiet thi hanh Luat kinh doanh bao hiem va Luat sua doi, bo sung mot so dieu cua Luat kinh doanh bao hiem | 73/2016/NĐ-CP | Nghi dinh | Chinh phu | 01/07/2016 | 173 | EXTERNAL_REQUIREMENT | Nghi dinh do Chinh phu ban hanh |
| 112924 | Thong tu so 105/2016/TT-BTC Huong dan hoat dong dau tu gian tiep ra nuoc ngoai cua to chuc kinh doanh chung khoan, quy dau tu chung khoan, cong ty dau tu chung khoan va doanh nghiep kinh doanh bao hiem | 105/2016/TT-BTC | Thong tu | Bo Tai chinh | 29/06/2016 | 48 | EXTERNAL_REQUIREMENT | Thong tu co so hieu TT-BTC, co quan ban hanh Bo Tai chinh |
| 117310 | Thong tu so 41/2016/TT-NHNN Quy dinh ty le an toan von doi voi ngan hang, chi nhanh ngan hang nuoc ngoai | 41/2016/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 30/12/2016 | 59 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 163441 | Nghi dinh so 46/2023/NĐ-CP Quy dinh chi tiet thi hanh mot so dieu cua Luat Kinh doanh bao hiem | 46/2023/NĐ-CP | Nghi dinh | Chinh phu | 01/07/2023 | 257 | EXTERNAL_REQUIREMENT | Nghi dinh do Chinh phu ban hanh |
| 166269 | Luat Hop tac xa so 17/2023/QH15 | 17/2023/QH15 | Luat | Quoc hoi | 20/06/2023 | 155 | EXTERNAL_REQUIREMENT | Luat do Quoc hoi ban hanh |
| 168220 | Thong tu so 27/2024/TT-NHNN Quy dinh ve viec ngan hang hop tac xa, viec trich nop, quan ly va su dung Quy bao dam an toan he thong quy tin dung nhan dan | 27/2024/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 28/06/2024 | 49 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 169221 | Thong tu so 43/2024/TT-NHNN sua doi, bo sung mot so dieu cua Thong tu so 01/2014/TT-NHNN | 43/2024/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 09/08/2024 | 17 | EXTERNAL_REQUIREMENT | Thong tu NHNN, tieu de neu sua doi van ban phap luat |
| 173695 | Thong tu so 56/2024/TT-NHNN Quy dinh ho so, thu tuc cap Giay phep lan dau cua ngan hang thuong mai, chi nhanh ngan hang nuoc ngoai, van phong dai dien nuoc ngoai | 56/2024/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 24/12/2024 | 46 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 174218 | Thong tu so 62/2024/TT-NHNN Quy dinh dieu kien, ho so, thu tuc chap thuan viec to chuc lai ngan hang thuong mai, to chuc tin dung phi ngan hang | 62/2024/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 31/12/2024 | 56 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 177271 | Thong tu so 01/2025/TT-NHNN Quy dinh ve cap Giay phep lan dau, cap doi Giay phep cua quy tin dung nhan dan | 01/2025/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 29/04/2025 | 35 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 185630 | Thong tu so 63/2025/TT-NHNN Sua doi, bo sung mot so dieu cua mot so Thong tu ve quy tin dung nhan dan | 63/2025/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 31/12/2025 | 26 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 25692 | Ngan hang Nha nuoc Viet Nam | 46/2010/QH12 | Luat | Quoc hoi | 16/06/2010 | 84 | EXTERNAL_REQUIREMENT | Luat co so hieu QH12, co quan ban hanh Quoc hoi |
| 44209 | Thong tu so 01/2014/TT-NHNN Quy dinh ve giao nhan, bao quan, van chuyen tien mat, tai san quy, giay to co gia | 01/2014/TT-NHNN | Thong tu | Ngan hang Nha nuoc Viet Nam | 06/01/2014 | 93 | EXTERNAL_REQUIREMENT | Thong tu NHNN do co quan quan ly nha nuoc ban hanh |
| 6e689cd0-6f81-11f1-94d6-fd5d6d5ff793 | Quy dinh ho so, thu tuc cap Giay phep lan dau cua ngan hang thuong mai, chi nhanh ngan hang nuoc ngoai, van phong dai dien nuoc ngoai | 52/VBHN-NHNN | Van ban hop nhat | Ngan hang Nha nuoc Viet Nam | 21/05/2026 | 89 | EXTERNAL_REQUIREMENT | Van ban hop nhat NHNN, co so hieu VBHN-NHNN |
| 95652 | Nghi dinh so 135/2015/NĐ-CP Quy dinh ve dau tu gian tiep ra nuoc ngoai | 135/2015/NĐ-CP | Nghi dinh | Chinh phu | 31/12/2015 | 55 | EXTERNAL_REQUIREMENT | Nghi dinh do Chinh phu ban hanh |

## Kiem tra internal policy

Khong tim thay document nao co bang chung la:

- chinh sach noi bo Agribank;
- quy che/quy trinh noi bo do don vi noi bo ban hanh;
- tai lieu co co quan ban hanh la don vi noi bo;
- nhan dang metadata phan biet `INTERNAL_POLICY`.

Cac tu khoa nhu `quy dinh` trong tieu de khong phai bang chung cua van ban noi bo; phan lon la cach mo ta noi dung van ban phap luat.

## Ket luan P6 truoc khi rerun

```text
COMPLIANCE GAP DATA: INSUFFICIENT
DATA GAP: INTERNAL POLICY NOT FOUND
```

Khong chay Compliance Gap Checker va khong sinh ket luan `DAP_UNG`, `THIEU` hoac `CHENH_LECH` tren corpus hien tai. Can bo sung mot nguon `INTERNAL_POLICY` co metadata/evidence ro rang truoc khi thuc hien P7.

## P6 rerun voi nguon bo sung

### Nguon duoc kiem tra

```text
Buoi_17/data/chunks_combined_secure.csv
```

File nay gom:

- `787` chunk external tu corpus Buoi 16;
- `24` chunk internal tu `Buoi_17/data/agribank_internal_policies.csv`;
- tong cong `811` chunk;
- `25` document, gom `15` external document va `10` internal document.

### Internal policy evidence

File `agribank_internal_policies.csv` co `14` cot, gom:

```text
chunk_id, document_id, text, source_file, title, so_ky_hieu,
loai_van_ban, co_quan_ban_hanh, ngay_ban_hanh, chapter, section,
article, citation, allowed_roles
```

10 document internal co prefix `agr_` va co metadata truc tiep chung minh:

- `loai_van_ban` la `Quy dinh noi bo` hoac `Quy che`;
- `co_quan_ban_hanh` la `Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank)`;
- tieu de ghi ro `Agribank` va chu de quy dinh noi bo;
- co `so_ky_hieu`, `article`, `citation` va `allowed_roles`.

10 internal document:

```text
agr_at01  Quy dinh noi bo 100/QD-NHNO-AT - Giao nhan, bao quan, van chuyen tien mat
agr_bh06  Quy dinh noi bo 180/QD-NHNO-BH - Mua bao hiem rui ro nghiep vu va tai san
agr_car02 Quy dinh noi bo 250/QD-NHNO-QLRR - Quan ly ty le an toan von va dinh muc rui ro
agr_fx04  Quy dinh noi bo 410/QD-NHNO-TTNH - Quan ly trang thai ngoai te va giao dich ngoai hoi
agr_gp05  Quy che 520/QC-NHNO-MANGLUOI - Mo rong mang luoi chi nhanh va phong giao dich
agr_hr08  Quy dinh noi bo 88/QD-NHNO-NS - Quy hoach, bo nhiem va quan ly nhan su
agr_it07  Quy che bao mat CNTT 600/QC-NHNO-CNTT - An toan thong tin va quan tri du lieu AI
agr_tc09  Quy che tai chinh 720/QC-NHNO-TC - Che do chi tieu va mua sam tai san noi bo
agr_td03  Quy che tin dung noi bo 315/QC-NHNO-TD - Phan quyet va phan cap uy quyen cho vay
agr_xln10 Quy dinh noi bo 390/QD-NHNO-XLN - Phan loai no va xu ly no xau
```

### Phan loai rerun

| Evidence side | So document | So chunk | Co so |
|---|---:|---:|---|
| `EXTERNAL_REQUIREMENT` | 15 | 787 | Thong tu/Nghi dinh/Luat/VBHN do NHNN, Chinh phu, Quoc hoi hoac Bo Tai chinh ban hanh |
| `INTERNAL_POLICY` | 10 | 24 | Quy dinh/Quy che Agribank, co quan ban hanh va so ky hieu noi bo ro rang |

Khong co document nao bi phan loai internal chi vi co tu `quy dinh`; 10 document internal co dong thoi title, loai van ban, co quan ban hanh va citation lam evidence.

## Ket luan P6 sau rerun

```text
COMPLIANCE GAP DATA: READY
INTERNAL_POLICY FOUND: YES
EXTERNAL_REQUIREMENT FOUND: YES
DATA SOURCE: Buoi_17/data/chunks_combined_secure.csv
```

P7 co the duoc chay lai voi corpus hop nhat nay. Khong thay doi source data trong qua trinh rerun.
