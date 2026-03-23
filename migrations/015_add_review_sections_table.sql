CREATE TABLE review_sections (
    key VARCHAR(512) PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_review_sections_key_prefix ON review_sections USING btree (key varchar_pattern_ops);

INSERT INTO schema_migrations (version, description) VALUES (15, 'Add review_sections table for code review storage');
