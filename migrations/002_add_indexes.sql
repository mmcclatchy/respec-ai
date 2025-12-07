-- Loop States Indexes
CREATE INDEX idx_loop_states_project ON loop_states(project_name);
CREATE INDEX idx_loop_states_status ON loop_states(status);
CREATE INDEX idx_loop_states_created ON loop_states(created_at DESC);

-- Loop History (for bounded queue operations)
CREATE INDEX idx_loop_history_sequence ON loop_history(sequence_number DESC);

-- Technical Specs Indexes
CREATE INDEX idx_specs_project ON technical_specs(project_name);
CREATE INDEX idx_specs_status ON technical_specs(spec_status);
CREATE INDEX idx_specs_iteration ON technical_specs(iteration DESC);

-- Fuzzy spec name search (requires pg_trgm extension)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_specs_name_search ON technical_specs USING gin(spec_name gin_trgm_ops);

-- Project Plans
CREATE INDEX idx_plans_status ON project_plans(project_status);

-- Record migration
INSERT INTO schema_migrations (version, description) VALUES (2, 'Performance indexes');
