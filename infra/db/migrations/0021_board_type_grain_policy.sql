ALTER TABLE board_types
ADD COLUMN IF NOT EXISTS grain_policy TEXT NOT NULL DEFAULT 'required';

ALTER TABLE board_types
DROP CONSTRAINT IF EXISTS board_types_grain_policy_check;

ALTER TABLE board_types
ADD CONSTRAINT board_types_grain_policy_check
CHECK (grain_policy IN ('none', 'optional', 'required'));

COMMENT ON COLUMN board_types.grain_policy IS
    'Controls whether workshop grain direction applies to this board type: none, optional, or required.';
