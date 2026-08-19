// Constraints are scoped by label and lab_session so Buoi 14 remains isolated.
CREATE CONSTRAINT van_ban_session_id IF NOT EXISTS
FOR (v:VanBan)
REQUIRE (v.lab_session, v.id) IS UNIQUE;

CREATE CONSTRAINT dieu_khoan_session_id IF NOT EXISTS
FOR (d:DieuKhoan)
REQUIRE (d.lab_session, d.id) IS UNIQUE;

CREATE INDEX dieu_khoan_document_id IF NOT EXISTS
FOR (d:DieuKhoan)
ON (d.document_id);