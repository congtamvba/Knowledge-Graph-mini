# Evaluation Report

## Protocol

- Số câu hỏi: **9**.
- Nhóm: 3 `EXACT_KEYWORD`, 3 `SEMANTIC`, 3 `MIXED`.
- Corpus dùng chung: `data/processed/chunks_normalized.csv`.
- Gold được khóa từ nội dung điều khoản trước khi chạy retrieval.
- Cùng `top_k=5` cho bốn cấu hình; Hybrid lấy `candidate_k=20` cho RRF và reranking.
- Reranker chỉ chấm 20 Hybrid candidates, không chấm toàn corpus.
- Lỗi không bị bỏ qua; tổng lỗi ghi nhận: **0**.

## Overall Metrics

| method | Questions | Errors | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| `bm25` | 9 | 0 | 0.556 | 0.667 | 0.778 | 0.639 |
| `dense` | 9 | 0 | 0.111 | 0.222 | 0.222 | 0.148 |
| `hybrid` | 9 | 0 | 0.222 | 0.222 | 0.556 | 0.306 |
| `hybrid_rerank` | 9 | 0 | 0.556 | 0.667 | 0.778 | 0.639 |

## Metrics By Query Type

### EXACT_KEYWORD

| method | Questions | Errors | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| `bm25` | 3 | 0 | 0.333 | 0.333 | 0.667 | 0.417 |
| `dense` | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `hybrid` | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `hybrid_rerank` | 3 | 0 | 0.667 | 0.667 | 0.667 | 0.667 |
### SEMANTIC

| method | Questions | Errors | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| `bm25` | 3 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| `dense` | 3 | 0 | 0.333 | 0.667 | 0.667 | 0.444 |
| `hybrid` | 3 | 0 | 0.667 | 0.667 | 1.000 | 0.750 |
| `hybrid_rerank` | 3 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
### MIXED

| method | Questions | Errors | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| `bm25` | 3 | 0 | 0.333 | 0.667 | 0.667 | 0.500 |
| `dense` | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| `hybrid` | 3 | 0 | 0.000 | 0.000 | 0.667 | 0.167 |
| `hybrid_rerank` | 3 | 0 | 0.000 | 0.333 | 0.667 | 0.250 |

## Nhận xét theo nhóm

- `EXACT_KEYWORD`: `hybrid_rerank` cao nhất theo Hit@5 rồi MRR (0.667, 0.667).
- `SEMANTIC`: `bm25` cao nhất theo Hit@5 rồi MRR (1.000, 1.000).
- `MIXED`: `bm25` cao nhất theo Hit@5 rồi MRR (0.667, 0.500).

## Hybrid có giúp không?

Hybrid làm giảm Hit@5 so với baseline tốt nhất. Kết luận này chỉ áp dụng cho bộ gold nhỏ hiện tại; xem thêm MRR và failure cases để tránh kết luận từ một metric.

## Reranking có đổi thứ hạng không?

Reranking đổi thứ tự top 5 ở **9/9** câu hỏi: `E01`, `E02`, `E03`, `S01`, `S02`, `S03`, `M01`, `M02`, `M03`.

## Failure Cases

- `E01` / `dense`: gold `44209-chunk-0040` không có trong top 5.
- `E01` / `hybrid`: gold `44209-chunk-0040` không có trong top 5.
- `E02` / `dense`: gold `168220-chunk-0038` không có trong top 5.
- `E02` / `hybrid`: gold `168220-chunk-0038` không có trong top 5.
- `E03` / `bm25`: gold `112924-chunk-0008` không có trong top 5.
- `E03` / `dense`: gold `112924-chunk-0008` không có trong top 5.
- `E03` / `hybrid`: gold `112924-chunk-0008` không có trong top 5.
- `E03` / `hybrid_rerank`: gold `112924-chunk-0008` không có trong top 5.
- `S03` / `dense`: gold `112924-chunk-0011` không có trong top 5.
- `M01` / `dense`: gold `117310-chunk-0021` không có trong top 5.
- `M02` / `dense`: gold `177271-chunk-0017` không có trong top 5.
- `M02` / `hybrid`: gold `177271-chunk-0017` không có trong top 5.
- `M02` / `hybrid_rerank`: gold `177271-chunk-0017` không có trong top 5.
- `M03` / `bm25`: gold `6e689cd0-6f81-11f1-94d6-fd5d6d5ff793-chunk-0028` không có trong top 5.
- `M03` / `dense`: gold `6e689cd0-6f81-11f1-94d6-fd5d6d5ff793-chunk-0028` không có trong top 5.

## Giới hạn

- Mỗi câu chỉ có một `expected_chunk_id`; các chunk khác có thể vẫn liên quan nhưng bị tính là miss.
- Bộ 9 câu nhỏ, được chọn từ các điều khoản có bằng chứng rõ; chưa đại diện toàn bộ miền pháp lý.
- Hit@k và MRR đo khả năng tìm đúng chunk đã gán, không đo độ đúng của câu trả lời sinh bởi LLM.
- Không thay gold sau khi xem kết quả. Muốn kết luận mạnh hơn cần nhiều người gán nhãn và nhiều relevant chunks cho mỗi câu.
