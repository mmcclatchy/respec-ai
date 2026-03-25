-- Add additional_sections column to plans table
-- Mirrors the existing additional_sections column on phases (001_initial_schema.sql:89)
-- Stores unmapped H2 sections as JSON key-value pairs

ALTER TABLE plans ADD COLUMN IF NOT EXISTS additional_sections JSONB DEFAULT '{}';

INSERT INTO schema_migrations (version, description) VALUES (16, 'Add additional_sections column to plans table') ON CONFLICT DO NOTHING;
