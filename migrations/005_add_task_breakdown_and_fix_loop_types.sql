-- Add task_breakdown column to technical_specs table
ALTER TABLE technical_specs ADD COLUMN task_breakdown TEXT;

-- Update loop_type CHECK constraint to use new loop type values
ALTER TABLE loop_states DROP CONSTRAINT valid_loop_type;
ALTER TABLE loop_states ADD CONSTRAINT valid_loop_type
    CHECK (loop_type IN ('plan', 'roadmap', 'phase', 'task', 'analyst'));
