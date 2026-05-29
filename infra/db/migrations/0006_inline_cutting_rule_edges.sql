ALTER TABLE cutting_rule_rows
    ADD COLUMN IF NOT EXISTS edge_long_1 BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS edge_long_2 BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS edge_short_1 BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS edge_short_2 BOOLEAN NOT NULL DEFAULT false;

DO $$
BEGIN
    IF to_regclass('public.cutting_rule_row_edges') IS NOT NULL THEN
        UPDATE cutting_rule_rows crr
        SET edge_long_1 = COALESCE(edges.edge_long_1, false),
            edge_long_2 = COALESCE(edges.edge_long_2, false),
            edge_short_1 = COALESCE(edges.edge_short_1, false),
            edge_short_2 = COALESCE(edges.edge_short_2, false),
            updated_at = now()
        FROM (
            SELECT
                rule_row_id,
                bool_or(edge_position = 'long_edge_1' AND is_edged) AS edge_long_1,
                bool_or(edge_position = 'long_edge_2' AND is_edged) AS edge_long_2,
                bool_or(edge_position = 'short_edge_1' AND is_edged) AS edge_short_1,
                bool_or(edge_position = 'short_edge_2' AND is_edged) AS edge_short_2
            FROM cutting_rule_row_edges
            GROUP BY rule_row_id
        ) edges
        WHERE crr.id = edges.rule_row_id;
    END IF;
END;
$$;

DO $$
BEGIN
    IF to_regclass('public.cutting_rule_row_edges') IS NOT NULL THEN
        DROP TRIGGER IF EXISTS cutting_rule_row_edges_set_updated_at ON cutting_rule_row_edges;
    END IF;
END;
$$;

DROP INDEX IF EXISTS cutting_rule_row_edges_edged_idx;
DROP TABLE IF EXISTS cutting_rule_row_edges;

COMMENT ON COLUMN cutting_rule_rows.edge_long_1 IS 'Whether the first long edge of this generated cut row must be edged.';
COMMENT ON COLUMN cutting_rule_rows.edge_long_2 IS 'Whether the second long edge of this generated cut row must be edged.';
COMMENT ON COLUMN cutting_rule_rows.edge_short_1 IS 'Whether the first short edge of this generated cut row must be edged.';
COMMENT ON COLUMN cutting_rule_rows.edge_short_2 IS 'Whether the second short edge of this generated cut row must be edged.';
