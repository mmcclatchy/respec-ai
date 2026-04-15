CREATE TABLE IF NOT EXISTS user_feedback_entries (
    id BIGSERIAL PRIMARY KEY,
    loop_id VARCHAR(8) NOT NULL REFERENCES loop_states(id) ON DELETE CASCADE,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_entries_loop_time
    ON user_feedback_entries(loop_id, created_at, id);

CREATE TABLE IF NOT EXISTS loop_analysis (
    loop_id VARCHAR(8) PRIMARY KEY REFERENCES loop_states(id) ON DELETE CASCADE,
    analysis TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version, description)
VALUES (23, 'Add unified feedback persistence tables (user_feedback_entries, loop_analysis)')
ON CONFLICT DO NOTHING;
