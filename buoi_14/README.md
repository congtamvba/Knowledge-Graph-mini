# Buoi 14 - Hybrid Search, Reranking va Mini Knowledge Graph

## Moi truong

Tu workspace root tren Windows, chay script bang virtual environment cua Buoi 14:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\prepare_corpus.py"
```

Script chi doc ba file nguon trong `kb+hops/` va ghi corpus da chuan hoa vao:

```text
buoi_14/data/processed/chunks_normalized.csv
```

Co the thay doi gioi han mem cua chunk:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\prepare_corpus.py" --max-chars 2000
```

Moi chunk co `chunk_id` duy nhat, `document_id`, plain `text`, `source_file`, cac nhan cau truc tim thay trong van ban va metadata citation lay truc tiep tu `metadata.csv`.

Ba CSV trong `kb+hops/` la du lieu nguon chi doc. Khong dat output vao thu muc nay.

## Baseline retrieval

BM25 va Dense cung doc `data/processed/chunks_normalized.csv`. Dense dung model tieng Viet `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5` tren CPU va luu document embeddings trong `buoi_14/cache/`.

Tu workspace root:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\baseline_retrieval.py" --query "Quy dinh an toan von ngan hang" --top-k 5
```

Script in rieng `BM25 RESULTS` va `DENSE RESULTS`. Moi ket qua co cung schema: `rank`, `chunk_id`, `document_id`, `text`, `retrieval_score`, `retrieval_method`, `citation`.

Lan chay Dense dau tien tao cache; cac lan sau tai su dung cache neu corpus va model khong doi.

Bao cao ket qua chay that cho ba loai truy van nam tai:

```text
outputs/retrieval_examples.md
```

Chay kiem thu tokenizer va schema ket qua:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" -m unittest discover ".\buoi_14\tests" -v
```

## Hybrid Search bang RRF

Hybrid tai su dung chinh BM25 va Dense o tren, lay `candidate-k` tu moi retriever va fusion theo Reciprocal Rank Fusion. Raw BM25 score va cosine score khong duoc cong truc tiep.

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\hybrid_search.py" --query "Thong tu 41/2016/TT-NHNN quy dinh ty le an toan von nhu the nao?" --candidate-k 20 --top-k 5
```

Output co `bm25_rank`, `dense_rank`, `rrf_score`, citation va van giu candidate chi xuat hien trong mot retriever. Dau `-` o cot rank nghia la chunk khong nam trong top `candidate-k` cua retriever do.

## Neural Reranking

Reranker dung Cross-Encoder multilingual `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` tren CPU. Model chi cham cac candidate tu Hybrid, khong cham toan corpus.

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\rerank.py" --query "Muon mo mot ngan hang moi thi phai nop nhung giay to nao?" --candidate-k 20 --top-k 5
```

Terminal in `BEFORE RERANK` va `AFTER RERANK`. Output sau rerank giu `hybrid_rank`, `hybrid_score`, `rerank_score`, text va citation. Day la neural reranker that, khong phai fallback va khong phai sort lai RRF.

## Evaluation

Bo 9 cau hoi gold da xac minh tu corpus nam tai `data/eval/questions.csv`, gom 3 `EXACT_KEYWORD`, 3 `SEMANTIC` va 3 `MIXED`. Chay cung protocol cho BM25, Dense, Hybrid va Hybrid + Rerank:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\compare_retrieval.py" --candidate-k 20 --top-k 5
```

Output:

```text
outputs/retrieval_comparison.csv
outputs/evaluation_report.md
```

CSV giu ket qua cua moi cau hoi va moi method, ke ca miss/error. Report tong hop Hit@1, Hit@3, Hit@5, MRR, metric theo query type, thay doi ranking va failure cases. Gold khong duoc thay doi sau khi xem ket qua.

## Mini Knowledge Graph

Loader tao ontology `(:VanBan)-[:CONTAINS]->(:DieuKhoan)` va chuoi `(:DieuKhoan)-[:NEXT]->(:DieuKhoan)`. Nam quan he VanBan duoc whitelist truc tiep tu `relationships.csv`: `CAN_CU`, `HOP_NHAT`, `SUA_DOI_BO_SUNG`, `THAY_THE`, `VAN_BAN_BO_SUNG`.

Tat ca node va relationship co `lab_session="buoi_14"`. Loader dung parameterized `MERGE`, khong co lenh xoa graph va khong hard-code credentials.

Kiem tra plan ma khong ket noi Neo4j:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\load_mini_kg.py" --dry-run
```

Sau khi khoi dong Neo4j 5.x, bat Bolt va dat dung `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` trong `.env`, chay:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\load_mini_kg.py"
```

Schema va query demo nam trong `cypher/schema.cypher` va `cypher/demo_queries.cypher`. Bao cao nap/ly do chua nap nam tai `outputs/kg_build_report.md`.

## Unified Retrieval va Graph Hints

API chung:

```python
from src.retrieval import retrieve

results = retrieve(question, method, top_k=5)
```

`method` ho tro `bm25`, `dense`, `hybrid`, `hybrid_rerank`. Moi result luon co `rank`, `chunk_id`, `document_id`, `text`, `score`, `citation`, `retrieval_method`; cac method nang cao giu them rank/score thanh phan.

CLI:

```powershell
& ".\buoi_14\.venv\Scripts\python.exe" ".\buoi_14\scripts\query_demo.py" --query "Thong tu 41/2016/TT-NHNN quy dinh ty le an toan von nhu the nao?" --method hybrid_rerank --top-k 5
```

Phan `GRAPH HINTS` in `document_id`, `chunk_id` va quan he VanBan truc tiep trong Neo4j. Day chi la mot hop truc tiep, khong phai Graph RAG hay multi-hop traversal. Neu Neo4j khong san sang, retrieval van tra ket qua va Graph Hints bao trang thai loi rieng.

## Streamlit Demo

Tu thu muc `buoi_14/`, chay:

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run app.py
```

Dung URL thuc te do terminal Streamlit in ra. De dung app, quay lai terminal dang chay server va nhan `Ctrl+C`.

Giao dien co bon method:

- `BM25`: khop tu khoa, ma van ban va so dieu chinh xac.
- `Dense`: tim theo semantic similarity.
- `Hybrid`: RRF fusion; hien them `BM25 rank`, `Dense rank`, `RRF`.
- `Hybrid + Rerank`: Cross-Encoder xep lai Hybrid candidates; hien bang `BEFORE RERANK` va `AFTER RERANK`.

Chon `Top-k`, nhap `Cau hoi`, sau do bam `Tim kiem`. Moi result hien:

- `rank`, `chunk_id`, `document_id`;
- `score` va `retrieval_method`;
- citation lay tu metadata that;
- text cua chunk;
- cac score/rank thanh phan neu method co.

`Graph hints` hien quan he VanBan truc tiep cua `document_id` va `chunk_id`. Neu Neo4j tat, retrieval van hoat dong va khu vuc nay hien `Neo4j chua san sang`; app khong render toan bo Knowledge Graph.