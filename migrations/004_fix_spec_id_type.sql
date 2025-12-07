-- Fix spec ID to use model's generated ID instead of database auto-increment

-- Drop the existing serial column and recreate as VARCHAR
ALTER TABLE technical_specs DROP CONSTRAINT technical_specs_pkey;
ALTER TABLE technical_specs DROP COLUMN id;
ALTER TABLE technical_specs ADD COLUMN id VARCHAR(8) PRIMARY KEY;

-- Record migration
INSERT INTO schema_migrations (version, description) VALUES (4, 'Change spec ID from SERIAL to VARCHAR for model-generated IDs');
