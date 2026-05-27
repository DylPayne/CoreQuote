CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE OR REPLACE FUNCTION corequote_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS companies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS companies_set_updated_at ON companies;
CREATE TRIGGER companies_set_updated_at
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    email          CITEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'member'
                   CHECK (role IN ('owner', 'admin', 'member')),
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS users_company_id_idx ON users(company_id);

DROP TRIGGER IF EXISTS users_set_updated_at ON users;
CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS auth_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE,
    expires_at    TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS auth_sessions_user_id_idx ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS auth_sessions_active_idx
    ON auth_sessions(token_hash, expires_at)
    WHERE revoked_at IS NULL;

DO $$
BEGIN
    IF to_regclass('public.projects') IS NOT NULL THEN
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS projects_company_id_idx ON projects(company_id);
    END IF;

    IF to_regclass('public.board_types') IS NOT NULL THEN
        ALTER TABLE board_types ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS board_types_company_id_idx ON board_types(company_id);
    END IF;

    IF to_regclass('public.slides') IS NOT NULL THEN
        ALTER TABLE slides ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS slides_company_id_idx ON slides(company_id);
    END IF;

    IF to_regclass('public.hinges') IS NOT NULL THEN
        ALTER TABLE hinges ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS hinges_company_id_idx ON hinges(company_id);
    END IF;

    IF to_regclass('public.handles') IS NOT NULL THEN
        ALTER TABLE handles ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS handles_company_id_idx ON handles(company_id);
    END IF;

    IF to_regclass('public.extra_categories') IS NOT NULL THEN
        ALTER TABLE extra_categories ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS extra_categories_company_id_idx ON extra_categories(company_id);
    END IF;

    IF to_regclass('public.extras') IS NOT NULL THEN
        ALTER TABLE extras ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS extras_company_id_idx ON extras(company_id);
    END IF;

    IF to_regclass('public.price_lists') IS NOT NULL THEN
        ALTER TABLE price_lists ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE RESTRICT;
        CREATE INDEX IF NOT EXISTS price_lists_company_id_idx ON price_lists(company_id);
    END IF;
END;
$$;

COMMENT ON TABLE companies IS 'Tenant root. Every user belongs to one company, and company-owned data must be scoped by company_id.';
COMMENT ON TABLE users IS 'Application users. Email is globally unique and each user belongs to exactly one company.';
COMMENT ON TABLE auth_sessions IS 'Opaque bearer-token sessions. Store token hashes only; return the raw token only on register/login.';
