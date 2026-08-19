# Baseline Retrieval Examples

## Cấu hình

- Corpus dùng chung: `data/processed/chunks_normalized.csv` (1.242 chunk, 15 văn bản).
- BM25: `rank-bm25==0.2.2`; tokenizer Unicode giữ mã có `/`, `-`, số điều và từ tiếng Việt.
- Dense: `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5`, vector 384 chiều, cosine similarity trên embedding đã chuẩn hóa.
- Cache Dense: `cache/dense_embeddings_9c5ee5216ba5bdb7.npz`.
- Mỗi bảng dưới đây là kết quả chạy thật với `top_k=5`. Bảng rút gọn hiển thị top 3 để dễ so sánh.
- Neural reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, chạy CPU trên đúng 20 Hybrid candidates, không chạy trên 1.242 chunk của corpus.

Hai baseline luôn trả cùng schema:

```text
rank, chunk_id, document_id, text, retrieval_score, retrieval_method, citation
```

Hybrid dùng RRF với `candidate_k=20`, `top_k=5`, `rrf_k=60`; không cộng raw BM25 score với cosine score. Schema Hybrid:

```text
final_rank, chunk_id, document_id, bm25_rank, dense_rank, rrf_score, text, citation
```

## 1. Câu hỏi có mã cụ thể

```text
01/2014/TT-NHNN
```

### BM25

| Rank | Score | Chunk | Nội dung |
|---:|---:|---|---|
| 1 | 4.652853 | `44209-chunk-0002` | Chương I - Quy định chung |
| 2 | 4.644509 | `44209-chunk-0051` | Mục 4 - Vào, ra kho tiền |
| 3 | 4.644509 | `44209-chunk-0086` | Chương VI - Tổ chức thực hiện |

### Dense

| Rank | Score | Chunk | Văn bản/kết quả |
|---:|---:|---|---|
| 1 | 0.697999 | `185630-chunk-0002` | Thông tư 63/2025/TT-NHNN |
| 2 | 0.670057 | `185630-chunk-0024` | Thông tư 63/2025/TT-NHNN |
| 3 | 0.662469 | `185630-chunk-0009` | Đoạn nhắc 01/2025/TT-NHNN |

### Hybrid RRF

| Rank | BM25 rank | Dense rank | RRF | Chunk |
|---:|---:|---:|---:|---|
| 1 | 3 | 14 | 0.02938653 | `44209-chunk-0086` |
| 2 | 4 | 15 | 0.02895833 | `44209-chunk-0091` |
| 3 | 2 | 18 | 0.02894955 | `44209-chunk-0051` |
| 4 | - | 1 | 0.01639344 | `185630-chunk-0002` |
| 5 | 1 | - | 0.01639344 | `44209-chunk-0002` |

### Hybrid + Neural Rerank

| Rank mới | Hybrid rank | Rerank score | Chunk |
|---:|---:|---:|---|
| 1 | 1 | 10.515202 | `44209-chunk-0086` |
| 2 | 20 | 10.493008 | `44209-chunk-0025` |
| 3 | 2 | 10.433990 | `44209-chunk-0091` |
| 4 | 12 | 10.430249 | `44209-chunk-0021` |
| 5 | 10 | 10.365792 | `44209-chunk-0056` |

**Nhận xét:** BM25 đưa đúng văn bản `01/2014/TT-NHNN` lên toàn bộ top đầu vì tokenizer giữ nguyên mã thành một token chính xác. Dense không phù hợp với chuỗi mã đơn lẻ. Hybrid đưa đúng văn bản trở lại top 1. Reranker giữ nguyên top 1, đưa thêm các mục/chương đúng của văn bản vào top 5 và loại văn bản `63/2025/TT-NHNN`; tuy nhiên query chỉ có mã nên không đủ ý định để chọn điều khoản trả lời cụ thể.

## 2. Câu hỏi diễn đạt semantic

```text
Muốn mở một ngân hàng mới thì phải nộp những giấy tờ nào?
```

### BM25

| Rank | Score | Chunk | Nội dung |
|---:|---:|---|---|
| 1 | 17.954472 | `44209-chunk-0041` | Bảo quản chìa khóa gian kho, két sắt |
| 2 | 17.510418 | `44209-chunk-0040` | Bảo quản chìa khóa cửa kho tiền |
| 3 | 15.920401 | `44209-chunk-0045` | Mở hộp chìa khóa dự phòng |

### Dense

| Rank | Score | Chunk | Nội dung |
|---:|---:|---|---|
| 1 | 0.659221 | `6e689cd0-...-chunk-0086` | Phụ lục/giấy tờ liên quan đến hồ sơ cấp phép |
| 2 | 0.640043 | `173695-chunk-0034` | Trách nhiệm lập và gửi hồ sơ cấp phép |
| 3 | 0.639337 | `173695-chunk-0042` | Xử lý hồ sơ đề nghị cấp giấy phép |

### Hybrid RRF

| Rank | BM25 rank | Dense rank | RRF | Chunk |
|---:|---:|---:|---:|---|
| 1 | 8 | 11 | 0.02879039 | `44209-chunk-0018` |
| 2 | 13 | 10 | 0.02798434 | `174218-chunk-0032` |
| 3 | 1 | - | 0.01639344 | `44209-chunk-0041` |
| 4 | - | 1 | 0.01639344 | `6e689cd0-...-chunk-0086` |
| 5 | - | 2 | 0.01612903 | `173695-chunk-0034` |

### Hybrid + Neural Rerank

| Rank mới | Hybrid rank | Rerank score | Chunk |
|---:|---:|---:|---|
| 1 | 11 | -0.862166 | `163441-chunk-0127` |
| 2 | 16 | -0.987893 | `6e689cd0-...-chunk-0028` |
| 3 | 15 | -1.174981 | `163441-chunk-0043` |
| 4 | 7 | -1.375099 | `173695-chunk-0042` |
| 5 | 18 | -1.735662 | `25692-chunk-0023` |

**Nhận xét:** BM25 bị kéo sang mở/bảo quản chìa khóa. Dense nhận ra ý định gần với thành lập ngân hàng và nộp hồ sơ. Hybrid **chưa cải thiện** vì hai đoạn overlap hạng thấp được cộng hai điểm RRF. Neural reranker loại cả hai false-consensus khỏi top 5 và đưa đúng đoạn “Hồ sơ đề nghị cấp Giấy phép thành lập và hoạt động ngân hàng liên doanh, ngân hàng 100% vốn nước ngoài” từ Hybrid rank 16 lên rank 2. Tuy nhiên rank 1 lại là hồ sơ doanh nghiệp môi giới bảo hiểm; reranking cải thiện nhưng chưa giải quyết hoàn toàn ambiguity giữa “mở ngân hàng” và “thành lập doanh nghiệp”.

## 3. Câu hỏi kết hợp mã và nội dung

```text
Thông tư 41/2016/TT-NHNN quy định tỷ lệ an toàn vốn như thế nào?
```

### BM25

| Rank | Score | Chunk | Nội dung |
|---:|---:|---|---|
| 1 | 28.931691 | `117310-chunk-0053` | Điều 20 - Công bố thông tin về tỷ lệ an toàn vốn |
| 2 | 26.675729 | `117310-chunk-0031` | Điều 9 - Hệ số rủi ro tín dụng |
| 3 | 25.735786 | `117310-chunk-0023` | Điều 7 - Vốn tự có |

### Dense

| Rank | Score | Chunk | Nội dung |
|---:|---:|---|---|
| 1 | 0.833909 | `117310-chunk-0051` | Mục 5 - Chế độ báo cáo và công bố thông tin |
| 2 | 0.812351 | `117310-chunk-0020` | Mục 1 - Tỷ lệ an toàn vốn và vốn tự có |
| 3 | 0.807616 | `117310-chunk-0043` | Mục 3 - Vốn yêu cầu cho rủi ro hoạt động |

### Hybrid RRF

| Rank | BM25 rank | Dense rank | RRF | Chunk |
|---:|---:|---:|---:|---|
| 1 | 4 | 2 | 0.03175403 | `117310-chunk-0020` |
| 2 | 8 | 4 | 0.03033088 | `117310-chunk-0019` |
| 3 | 13 | 1 | 0.03009207 | `117310-chunk-0051` |
| 4 | 5 | 10 | 0.02967033 | `117310-chunk-0022` |
| 5 | 3 | 14 | 0.02938653 | `117310-chunk-0023` |

### Hybrid + Neural Rerank

| Rank mới | Hybrid rank | Rerank score | Chunk |
|---:|---:|---:|---|
| 1 | 16 | 10.893123 | `117310-chunk-0001` |
| 2 | 5 | 10.818677 | `117310-chunk-0023` |
| 3 | 14 | 10.497891 | `117310-chunk-0053` |
| 4 | 1 | 10.461179 | `117310-chunk-0020` |
| 5 | 20 | 10.439946 | `117310-chunk-0013` |

**Nhận xét:** Cả bốn cấu hình đều xác định đúng văn bản. Hybrid đưa “Mục 1 - Tỷ lệ an toàn vốn và vốn tự có” lên top 1. Reranker chuyển passage mở đầu của đúng Thông tư từ Hybrid rank 16 lên rank 1, Điều 7 lên rank 2 và Điều 20 lên rank 3. Đây là context giàu thông tin hơn các heading ngắn, nhưng “Điều 6 - Tỷ lệ an toàn vốn” bị rơi khỏi rerank top 5; do đó chưa thể kết luận neural reranking luôn tốt hơn nếu chưa có gold relevance.

## Kết luận BM25, Dense, Hybrid và Reranking

- BM25 mạnh với số hiệu, mã văn bản và cụm từ pháp lý chính xác.
- Dense hữu ích khi câu hỏi diễn đạt khác từ ngữ trong tài liệu.
- Dense hiện có xu hướng xếp cao heading hoặc phụ lục ngắn khi title metadata khớp mạnh.
- Hybrid thực sự dùng cả hai retriever; output có `bm25_rank` và `dense_rank`, kể cả khi candidate chỉ xuất hiện ở một nhánh.
- RRF tránh cộng trực tiếp hai thang điểm không tương thích và giúp query exact/mixed giữ tín hiệu từ cả hai bảng xếp hạng.
- Hybrid cải thiện query mã so với Dense và tạo ranking cân bằng cho query mixed.
- Hybrid chưa cải thiện query semantic: overlap hạng thấp có thể lấn át candidate tốt chỉ xuất hiện ở một retriever.
- Neural reranker thực sự chấm cặp `(question, candidate)` trên 20 Hybrid candidates; không sort lại `rrf_score` và không rerank toàn corpus.
- Reranking thay đổi thứ tự ở cả ba query và giữ nguyên `chunk_id`, `document_id`, `hybrid_rank`, `hybrid_score`, text và citation.
- Reranking sửa false-consensus rõ nhất ở query semantic, nhưng vẫn có false positive bảo hiểm ở rank 1.
- Với query mixed, reranker ưu tiên passage đầy đủ hơn heading, nhưng làm mất Điều 6 khỏi top 5. Cần Prompt 5 với gold relevance trước khi kết luận chất lượng tổng thể.