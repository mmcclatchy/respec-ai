-- Drop the Task workflow's tables. Task removal (v2 Phase 6): implementation.md
-- (Phase 5) now owns build ordering, so the tasks table and its loop mapping are
-- dropped rather than orphaned, per precedent at 017_drop_loop_history_table.sql.
-- On-disk Task markdown files are derived artifacts, fully regenerable by
-- re-running the phase workflow -- no data migration is required for them.
DROP TABLE IF EXISTS loop_to_task_mappings;
DROP TABLE IF EXISTS tasks;

-- LoopType.TASK no longer exists in the application layer; tighten the CHECK
-- constraint to match, so a stray 'task' loop can never be written again.
ALTER TABLE loop_states DROP CONSTRAINT IF EXISTS valid_loop_type;
ALTER TABLE loop_states ADD CONSTRAINT valid_loop_type
    CHECK (loop_type IN ('plan', 'roadmap', 'phase', 'analyst'));
