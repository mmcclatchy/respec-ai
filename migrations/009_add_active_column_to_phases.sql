-- Add active column to phases table to support phase lifecycle management
-- When roadmaps are refined, old phases are marked inactive and new phases are stored as active

-- Add active column (default true for existing phases)
ALTER TABLE phases ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

-- Create index for faster active phase queries
CREATE INDEX IF NOT EXISTS idx_phases_active ON phases(project_name, active);

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (9, 'Add active column to phases table for lifecycle management');
