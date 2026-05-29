CREATE TABLE IF NOT EXISTS cutting_ruleset_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruleset_id      UUID NOT NULL REFERENCES cutting_rulesets(id) ON DELETE CASCADE,
    company_id      UUID REFERENCES companies(id) ON DELETE SET NULL,
    unit_config_id  UUID REFERENCES unit_configs(id) ON DELETE SET NULL,
    unit_type_key   TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived')),
    version         INTEGER NOT NULL CHECK (version > 0),
    is_default      BOOLEAN NOT NULL DEFAULT false,
    rows            JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(rows) = 'array'),
    snapshot_reason TEXT NOT NULL DEFAULT 'update',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cutting_ruleset_history_ruleset_created_idx
    ON cutting_ruleset_history(ruleset_id, created_at DESC);
