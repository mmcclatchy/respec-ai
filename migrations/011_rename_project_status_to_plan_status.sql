-- Migration 011: Rename project_status to plan_status in plans table
-- This aligns the final column name with the codebase refactoring

-- Plans table
ALTER TABLE plans
    RENAME COLUMN project_status TO plan_status;

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (11, 'Rename project_status to plan_status in plans table');
