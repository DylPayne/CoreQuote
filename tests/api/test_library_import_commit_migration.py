from pathlib import Path


MIGRATION_0018 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0018_library_import_audit.sql"


def test_library_import_commit_migration_adds_audit_tables():
    sql = MIGRATION_0018.read_text()

    assert "CREATE TABLE IF NOT EXISTS library_import_batches" in sql
    assert "CREATE TABLE IF NOT EXISTS library_import_rows" in sql
    assert "user_id" in sql
    assert "content_sha256" in sql
    assert "payload" in sql
    assert "problems" in sql
    assert "JSONB" in sql
    assert "failed_count" in sql
    assert "sqlite" not in sql.lower()
