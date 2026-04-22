CREATE TABLE IF NOT EXISTS reviewer_results (
    loop_id VARCHAR(8) NOT NULL REFERENCES loop_states(id) ON DELETE CASCADE,
    review_iteration INTEGER NOT NULL CHECK (review_iteration >= 1),
    reviewer_name VARCHAR(64) NOT NULL,
    feedback_markdown TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    blockers JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (loop_id, review_iteration, reviewer_name)
);

CREATE INDEX IF NOT EXISTS idx_reviewer_results_loop_iteration
    ON reviewer_results(loop_id, review_iteration);

CREATE TABLE IF NOT EXISTS review_findings (
    id BIGSERIAL PRIMARY KEY,
    loop_id VARCHAR(8) NOT NULL,
    review_iteration INTEGER NOT NULL,
    reviewer_name VARCHAR(64) NOT NULL,
    priority VARCHAR(2) NOT NULL CHECK (priority IN ('P0', 'P1', 'P2', 'P3')),
    feedback TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (loop_id, review_iteration, reviewer_name)
        REFERENCES reviewer_results(loop_id, review_iteration, reviewer_name)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_review_findings_loop_iteration
    ON review_findings(loop_id, review_iteration, reviewer_name, sort_order);

INSERT INTO schema_migrations (version, description)
VALUES (24, 'Add reviewer result and finding tables for deterministic consolidation')
ON CONFLICT DO NOTHING;
