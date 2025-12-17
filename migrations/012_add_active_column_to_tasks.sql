-- Add active column to tasks table to support task lifecycle management
-- When task breakdowns are refined, old tasks are marked inactive and new tasks are stored as active

-- Add active column (default true for existing tasks)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

-- Create index for faster active task queries
CREATE INDEX IF NOT EXISTS idx_tasks_active ON tasks(phase_path, active);

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (12, 'Add active column to tasks table for lifecycle management');
