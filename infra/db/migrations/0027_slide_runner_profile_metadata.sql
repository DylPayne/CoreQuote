DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname
    INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'slides'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%drawer_system_kind%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE slides DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE slides
ADD CONSTRAINT slides_drawer_system_kind_check
CHECK (drawer_system_kind IN ('conventional', 'metal', 'custom'));

ALTER TABLE slides
ADD COLUMN IF NOT EXISTS mount_type TEXT NOT NULL DEFAULT 'side_mount'
    CHECK (mount_type IN ('side_mount', 'undermount', 'metal_system', 'custom')),
ADD COLUMN IF NOT EXISTS product_family TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS required_depth_mm INTEGER NOT NULL DEFAULT 0 CHECK (required_depth_mm >= 0),
ADD COLUMN IF NOT EXISTS drawer_depth_deduction_mm INTEGER NOT NULL DEFAULT 0 CHECK (drawer_depth_deduction_mm >= 0),
ADD COLUMN IF NOT EXISTS box_width_deduction_mm INTEGER NOT NULL DEFAULT 0 CHECK (box_width_deduction_mm >= 0);

COMMENT ON COLUMN slides.mount_type IS 'How the runner or drawer system mounts: side_mount, undermount, metal_system, or custom.';
COMMENT ON COLUMN slides.product_family IS 'User-facing drawer runner or drawer system product range shared by length-specific slide rows.';
COMMENT ON COLUMN slides.required_depth_mm IS 'Minimum internal carcass depth required by this runner or drawer system.';
COMMENT ON COLUMN slides.drawer_depth_deduction_mm IS 'Default deduction from nominal length to drawer box depth when range-created.';
COMMENT ON COLUMN slides.box_width_deduction_mm IS 'Total drawer-box width deduction used for runner fitting, especially undermount systems.';
COMMENT ON COLUMN slides.drawer_system_kind IS 'conventional for timber drawer boxes, metal for configurable supplied drawer-side systems, custom for advanced runner setups.';
