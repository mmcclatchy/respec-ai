-- Migration 010: Rename project_name to plan_name across all tables
-- This aligns the database schema with the codebase refactoring

-- Loop States table
ALTER TABLE loop_states
    RENAME COLUMN project_name TO plan_name;

-- Roadmaps table
ALTER TABLE roadmaps
    RENAME COLUMN project_name TO plan_name;

-- Phases table (formerly technical_specs)
ALTER TABLE phases
    RENAME COLUMN project_name TO plan_name;

-- Drop old FK constraint on loop_to_phase_mappings
ALTER TABLE loop_to_phase_mappings
    DROP CONSTRAINT IF EXISTS loop_to_phase_mappings_project_name_phase_name_fkey;

-- Loop-to-Phase Mappings table (formerly loop_to_spec_mappings)
ALTER TABLE loop_to_phase_mappings
    RENAME COLUMN project_name TO plan_name;

-- Recreate FK constraint with new column name
ALTER TABLE loop_to_phase_mappings
    ADD CONSTRAINT loop_to_phase_mappings_plan_name_phase_name_fkey
    FOREIGN KEY (plan_name, phase_name)
    REFERENCES phases(plan_name, phase_name)
    ON DELETE CASCADE;

-- Project Plans table needs to be renamed to just "plans"
ALTER TABLE project_plans RENAME TO plans;

-- Rename the primary key column in plans table
ALTER TABLE plans
    RENAME COLUMN project_name TO plan_name;

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (10, 'Rename project_name to plan_name across all tables');
