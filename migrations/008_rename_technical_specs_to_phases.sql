-- Rename technical_specs table to phases
ALTER TABLE IF EXISTS technical_specs RENAME TO phases;

-- Add unique constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'phases_project_name_phase_name_key'
    ) THEN
        ALTER TABLE phases ADD CONSTRAINT phases_project_name_phase_name_key UNIQUE (project_name, phase_name);
    END IF;
END $$;

-- Rename the loop mapping table and its foreign key
ALTER TABLE IF EXISTS loop_to_spec_mappings RENAME TO loop_to_phase_mappings;

-- Update loop_type constraint to match current LoopType enum
ALTER TABLE loop_states DROP CONSTRAINT IF EXISTS valid_loop_type;
ALTER TABLE loop_states ADD CONSTRAINT valid_loop_type
    CHECK (loop_type IN ('plan', 'roadmap', 'phase', 'task', 'analyst'));

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (8, 'Rename technical_specs to phases and update terminology');
