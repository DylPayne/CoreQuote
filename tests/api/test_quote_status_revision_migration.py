from pathlib import Path


MIGRATION_0016 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0016_quote_status_revisions.sql"
MIGRATION_0026 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0026_quote_hardware_catalog_snapshot.sql"
MIGRATION_0027 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0027_slide_runner_profile_metadata.sql"


def test_quote_status_revision_migration_adds_visible_quote_metadata():
    sql = MIGRATION_0016.read_text()

    assert "ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft'" in sql
    assert "ADD COLUMN IF NOT EXISTS quote_number TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1" in sql
    assert "ADD COLUMN IF NOT EXISTS previous_revision_id UUID REFERENCES quotes(id) ON DELETE SET NULL" in sql
    assert "quotes_status_chk" in sql
    assert "'draft', 'ready', 'sent', 'accepted', 'rejected', 'revised', 'expired'" in sql
    assert "quotes_company_project_number_revision_idx" in sql
    assert "sqlite" not in sql.lower()


def test_quote_status_revision_migration_backfills_project_quote_numbers():
    sql = MIGRATION_0016.read_text()

    assert "row_number() OVER" in sql
    assert "PARTITION BY company_id, project_id" in sql
    assert "'Q-' || lpad(ranked.quote_index::text, 3, '0')" in sql
    assert "ALTER COLUMN quote_number SET NOT NULL" in sql


def test_quote_hardware_catalog_snapshot_migration_adds_internal_freeze_payload():
    sql = MIGRATION_0026.read_text()

    assert "ADD COLUMN IF NOT EXISTS hardware_catalog_snapshot JSONB" in sql
    assert "quotes_hardware_catalog_snapshot_object_chk" in sql
    assert "jsonb_typeof(hardware_catalog_snapshot) = 'object'" in sql
    assert "old quotes" not in sql.lower()
    assert "sqlite" not in sql.lower()


def test_slide_runner_profile_migration_adds_mount_and_range_metadata():
    sql = MIGRATION_0027.read_text()

    assert "ADD COLUMN IF NOT EXISTS mount_type TEXT NOT NULL DEFAULT 'side_mount'" in sql
    assert "CHECK (mount_type IN ('side_mount', 'undermount', 'metal_system', 'custom'))" in sql
    assert "ADD COLUMN IF NOT EXISTS product_family TEXT NOT NULL DEFAULT ''" in sql
    assert "ADD COLUMN IF NOT EXISTS required_depth_mm INTEGER NOT NULL DEFAULT 0" in sql
    assert "ADD COLUMN IF NOT EXISTS drawer_depth_deduction_mm INTEGER NOT NULL DEFAULT 0" in sql
    assert "ADD COLUMN IF NOT EXISTS box_width_deduction_mm INTEGER NOT NULL DEFAULT 0" in sql
    assert "CHECK (drawer_system_kind IN ('conventional', 'metal', 'custom'))" in sql
    assert "sqlite" not in sql.lower()
