CREATE INDEX IF NOT EXISTS idx_reviewer_results_latest_by_reviewer
    ON reviewer_results(loop_id, reviewer_name, review_iteration DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_phase_lower_name_active
    ON tasks(phase_path, lower(name)) WHERE active = TRUE;

INSERT INTO schema_migrations (version, description)
VALUES (27, 'Add reviewer latest-result and active task lookup indexes')
ON CONFLICT DO NOTHING;
