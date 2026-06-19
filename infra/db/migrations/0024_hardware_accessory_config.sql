ALTER TABLE slides
ADD COLUMN IF NOT EXISTS accessory_config JSONB NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(accessory_config) = 'object');

ALTER TABLE hinges
ADD COLUMN IF NOT EXISTS accessory_config JSONB NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(accessory_config) = 'object');

COMMENT ON COLUMN slides.accessory_config IS 'Structured accessory bundle rules for required, optional, and conditional drawer hardware components.';
COMMENT ON COLUMN hinges.accessory_config IS 'Structured accessory bundle rules for required, optional, and conditional hinge components such as mounting plates.';
