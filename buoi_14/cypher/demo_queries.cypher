// Query A - View the Buoi 14 graph.
MATCH (n {lab_session: "buoi_14"})-[r]->(m {lab_session: "buoi_14"})
RETURN n, r, m
LIMIT 100;

// Query B - Documents and their chunks/articles.
MATCH (v:VanBan {lab_session: "buoi_14"})
      -[:CONTAINS {lab_session: "buoi_14"}]->
      (d:DieuKhoan {lab_session: "buoi_14"})
RETURN v, d
LIMIT 50;

// Query C - Three consecutive chunks in one document.
MATCH path = (d1:DieuKhoan {lab_session: "buoi_14"})
             -[:NEXT {lab_session: "buoi_14"}]->
             (d2:DieuKhoan {lab_session: "buoi_14"})
             -[:NEXT {lab_session: "buoi_14"}]->
             (d3:DieuKhoan {lab_session: "buoi_14"})
WHERE d1.document_id = d2.document_id
  AND d2.document_id = d3.document_id
RETURN path
LIMIT 25;

// Query D - Only relationship types actually present in relationships.csv.
MATCH (source:VanBan {lab_session: "buoi_14"})-[r]->
      (target:VanBan {lab_session: "buoi_14"})
WHERE type(r) IN [
  "CAN_CU",
  "HOP_NHAT",
  "SUA_DOI_BO_SUNG",
  "THAY_THE",
  "VAN_BAN_BO_SUNG"
]
RETURN source, r, target
ORDER BY type(r), source.id;

// Query E - Session nodes with no relationships at all.
MATCH (n {lab_session: "buoi_14"})
WHERE NOT (n)--()
RETURN labels(n) AS labels, n.id AS id
ORDER BY labels, id;

// Quality check - DieuKhoan without its owning VanBan.
MATCH (d:DieuKhoan {lab_session: "buoi_14"})
WHERE NOT (:VanBan {lab_session: "buoi_14"})
          -[:CONTAINS {lab_session: "buoi_14"}]->(d)
RETURN count(d) AS orphan_dieu_khoan;