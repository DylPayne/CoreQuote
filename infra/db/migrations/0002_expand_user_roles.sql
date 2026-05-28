ALTER TABLE users
    DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE users
    ADD CONSTRAINT users_role_check
    CHECK (role IN (
        'owner',
        'admin',
        'manager',
        'estimator',
        'production',
        'viewer',
        'member'
    ));

COMMENT ON COLUMN users.role IS
    'Company-level role used by the API permission matrix. member is retained as a legacy estimator-like role.';
