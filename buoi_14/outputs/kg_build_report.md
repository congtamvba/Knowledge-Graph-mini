# Mini Knowledge Graph Build Report

- **Status:** LOADED
- **Lab session:** `buoi_14`
- **Write strategy:** parameterized `MERGE`; no global delete query exists in the loader.

## Validated Input

- VanBan source rows: **15**.
- DieuKhoan/chunk rows: **1242**.
- Source document relationships: **8**.
- Relationship endpoints missing from metadata: **0**.
- Source files were read only.

## Planned Counts

| Type | Count |
|---|---:|
| `VanBan` | 15 |
| `DieuKhoan` | 1242 |
| `CONTAINS` | 1242 |
| `NEXT` | 1227 |
| `SUA_DOI_BO_SUNG` | 1 |
| `CAN_CU` | 4 |
| `VAN_BAN_BO_SUNG` | 1 |
| `THAY_THE` | 1 |
| `HOP_NHAT` | 1 |

## Actual Neo4j Counts

### Nodes

- `DieuKhoan`: **1242**
- `VanBan`: **15**

### Relationships

- `CAN_CU`: **4**
- `CONTAINS`: **1242**
- `HOP_NHAT`: **1**
- `NEXT`: **1227**
- `SUA_DOI_BO_SUNG`: **1**
- `THAY_THE`: **1**
- `VAN_BAN_BO_SUNG`: **1**

## Quality Checks

- DieuKhoan without CONTAINS: **0**.
- Isolated session nodes: **0**.
