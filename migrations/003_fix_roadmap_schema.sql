-- Fix roadmap schema to separate project key from roadmap title

-- Add roadmap_title column to store the Roadmap model's project_name field
ALTER TABLE roadmaps ADD COLUMN roadmap_title TEXT;

-- Copy existing project_name values to roadmap_title for any existing data
UPDATE roadmaps SET roadmap_title = project_name;

-- Make roadmap_title NOT NULL
ALTER TABLE roadmaps ALTER COLUMN roadmap_title SET NOT NULL;

-- Record migration
INSERT INTO schema_migrations (version, description) VALUES (3, 'Separate project key from roadmap title');
