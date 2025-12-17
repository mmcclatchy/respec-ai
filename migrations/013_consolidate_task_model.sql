-- Consolidate TaskBreakdown and Task models into unified Task model
-- New Task model has: name, phase_path, goal, acceptance_criteria, tech_stack_reference,
-- implementation_steps, testing_strategy, status, active, version

-- Add new columns
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT 'Goal not specified';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS tech_stack_reference TEXT NOT NULL DEFAULT 'Technology stack reference not specified';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS implementation_steps TEXT NOT NULL DEFAULT 'Implementation steps not specified';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS testing_strategy TEXT NOT NULL DEFAULT 'Testing strategy not specified';

-- Migrate data from old columns to new columns
UPDATE tasks SET goal = description WHERE description IS NOT NULL AND description != 'Description not specified';
UPDATE tasks SET implementation_steps = implementation_notes WHERE implementation_notes IS NOT NULL;
UPDATE tasks SET testing_strategy = test_strategy WHERE test_strategy IS NOT NULL;

-- Convert version from INTEGER to TEXT
ALTER TABLE tasks ALTER COLUMN version TYPE TEXT USING version::TEXT;
ALTER TABLE tasks ALTER COLUMN version SET DEFAULT '1.0';

-- Drop obsolete columns
ALTER TABLE tasks DROP COLUMN IF EXISTS description;
ALTER TABLE tasks DROP COLUMN IF EXISTS mode;
ALTER TABLE tasks DROP COLUMN IF EXISTS sequence;
ALTER TABLE tasks DROP COLUMN IF EXISTS dependencies;
ALTER TABLE tasks DROP COLUMN IF EXISTS estimated_complexity;
ALTER TABLE tasks DROP COLUMN IF EXISTS implementation_notes;
ALTER TABLE tasks DROP COLUMN IF EXISTS test_strategy;
ALTER TABLE tasks DROP COLUMN IF EXISTS iteration;

-- Drop obsolete constraints (if they exist)
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS valid_mode;
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS valid_complexity;

-- Drop task_breakdowns table if it exists
DROP TABLE IF EXISTS loop_to_task_breakdown_mappings CASCADE;
DROP TABLE IF EXISTS task_breakdowns CASCADE;

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (13, 'Consolidate TaskBreakdown and Task into unified Task model');
