-- This migration fixes databases that were created with the duplicate phase_name column
-- in 001_initial_schema.sql (lines 69-70 had duplicate phase_name definitions)

-- If the table was created with duplicate columns, PostgreSQL would have failed,
-- so this is a safety migration in case the schema was partially applied

-- Nothing to do here since PostgreSQL doesn't allow duplicate column names
-- and would have failed table creation. This file exists to document the fix.

-- The fix was applied directly to 001_initial_schema.sql by removing the duplicate:
-- BEFORE: phase_name VARCHAR(255) NOT NULL, phase_name TEXT NOT NULL,
-- AFTER:  phase_name TEXT NOT NULL,

-- To apply the fix to an existing database:
-- 1. Stop the containers: docker-compose -f docker-compose.dev.yml down
-- 2. Remove the volume: docker volume rm respec-ai_respec_ai_dev_data
-- 3. Restart: docker-compose -f docker-compose.dev.yml up -d
