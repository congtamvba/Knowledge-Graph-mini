# Secure KG Load Report

## SECURE KG LOAD REPORT

- **Input:** `C:\RAG\Knowledge Graph mini\buoi_14\data\processed\chunks_secure.csv`
- **Database:** `kb-hops`
- **Lab session:** `buoi_15`
- **Roles:** Admin, HR_Manager, Risk_Officer, Employee, Guest
- **Write strategy:** parameterized `MERGE`; no delete operation.
- **VanBan role policy:** intersection of all child chunk roles (fail-closed full-document access).
- **DieuKhoan role policy:** exact roles parsed from each `chunks_secure.csv` row.

## Actual Neo4j Counts

| Check | Result |
|---|---:|
| VanBan nodes | 15 |
| DieuKhoan nodes | 1242 |
| VanBan with allowed_roles | 15 |
| DieuKhoan with allowed_roles | 1242 |
| CONTAINS relationships | 1242 |
| NEXT relationships | 1227 |
| Empty allowed_roles | 0 |
| Invalid roles | [] |
| Orphan DieuKhoan | 0 |
| Missing lab_session | 0 |
| Buoi 14 preserved | YES |
| Idempotent | YES |

## Sample

```json
[
  {
    "document_id": "112025",
    "document_allowed_roles": [
      "Admin"
    ],
    "chunks": [
      {
        "allowed_roles": [
          "Admin",
          "HR_Manager",
          "Risk_Officer",
          "Employee",
          "Guest"
        ],
        "chunk_id": "112025-chunk-0001"
      },
      {
        "allowed_roles": [
          "Admin",
          "HR_Manager",
          "Risk_Officer",
          "Employee",
          "Guest"
        ],
        "chunk_id": "112025-chunk-0002"
      },
      {
        "allowed_roles": [
          "Admin",
          "HR_Manager",
          "Risk_Officer",
          "Employee",
          "Guest"
        ],
        "chunk_id": "112025-chunk-0003"
      }
    ]
  }
]
```

## Security Notes

- `VanBan.allowed_roles` expresses full-document access and is intentionally fail-closed.
- Prompt 3 must authorize retrieval with `DieuKhoan.allowed_roles` for chunk-level access.
- The Buoi 14 graph is isolated by `lab_session="buoi_14"` and was not updated.

**Status:** SUCCESS
