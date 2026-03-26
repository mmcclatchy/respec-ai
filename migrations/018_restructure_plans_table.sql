-- Restructure plans table to remove unused Communication Plan fields and add
-- Architecture Direction and Technology Decisions fields that downstream agents consume.
--
-- Removed: reporting_structure, meeting_schedule, documentation_standards
-- Renamed: excluded_features → anti_requirements, quality_standards → quality_bar
-- Added: architecture_overview, data_flow, technology_decisions, technology_rejections

ALTER TABLE plans RENAME COLUMN excluded_features TO anti_requirements;
ALTER TABLE plans RENAME COLUMN quality_standards TO quality_bar;

ALTER TABLE plans ADD COLUMN IF NOT EXISTS architecture_overview TEXT NOT NULL DEFAULT 'Architecture Overview not specified';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS data_flow TEXT NOT NULL DEFAULT 'Data Flow not specified';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS technology_decisions TEXT NOT NULL DEFAULT 'Technology Decisions not specified';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS technology_rejections TEXT NOT NULL DEFAULT 'Technology Rejections not specified';

ALTER TABLE plans DROP COLUMN IF EXISTS reporting_structure;
ALTER TABLE plans DROP COLUMN IF EXISTS meeting_schedule;
ALTER TABLE plans DROP COLUMN IF EXISTS documentation_standards;

INSERT INTO schema_migrations (version, description) VALUES (18, 'Restructure plans table: add architecture/technology fields, remove communication plan fields') ON CONFLICT DO NOTHING;
