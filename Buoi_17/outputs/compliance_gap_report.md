# Compliance Gap Report - Buoi 17

P7 da chay tren corpus hop nhat, gom external requirement va internal policy Agribank.

- External chunks: 787
- Internal chunks: 24
- Retrieval: Hybrid (BM25 + Dense) -> Neural Rerank
- Role test: `Admin`
- Graph: khong dung de mo rong candidate trong run nay; cac edge graph khong noi truc tiep internal policy voi external requirement.

## Guardrails

- Khong phan loai chi tu similarity score.
- Khong gan `THIEU` khi retrieval khong tim thay evidence.
- Moi ket qua co external citation va internal citation candidate.
- Moi finding deu co `NEEDS_HUMAN_REVIEW`.

## Results

| External document | Internal document | Classification | Confidence | Review |
|---|---|---|---:|---|
| 44209 | agr_at01 | CHUA_DU_BANG_CHUNG | 0.0 | NEEDS_HUMAN_REVIEW |
| 174218 | agr_xln10 | CHUA_DU_BANG_CHUNG | 0.0 | NEEDS_HUMAN_REVIEW |
| 117310 | agr_gp05 | CHUA_DU_BANG_CHUNG | 0.0 | NEEDS_HUMAN_REVIEW |

```text
GAP CHECKER: PASS
HUMAN REVIEW REQUIRED: YES
```

Classification `CHUA_DU_BANG_CHUNG` la ket qua bao thu: can kiem toan vien doc va so sanh evidence hai phia truoc khi ket luan.