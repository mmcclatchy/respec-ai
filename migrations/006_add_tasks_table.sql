-- Tasks table for storing Task model instances
CREATE TABLE tasks (
    id VARCHAR(8) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phase_path TEXT NOT NULL,

    -- Definition
    description TEXT NOT NULL DEFAULT 'Description not specified',
    acceptance_criteria TEXT NOT NULL DEFAULT 'Acceptance criteria not specified',
    mode VARCHAR(50) NOT NULL DEFAULT 'implementation',

    -- Sequencing
    sequence INTEGER NOT NULL DEFAULT 1,
    dependencies TEXT[] NOT NULL DEFAULT '{}',
    estimated_complexity VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- Implementation
    implementation_notes TEXT,
    test_strategy TEXT,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Metadata
    iteration INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(phase_path, name),

    CONSTRAINT valid_mode CHECK (mode IN ('database', 'api', 'integration', 'test', 'implementation')),
    CONSTRAINT valid_complexity CHECK (estimated_complexity IN ('low', 'medium', 'high')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed'))
);

-- Loop to Task mappings (similar to loop_to_spec_mappings)
CREATE TABLE loop_to_task_mappings (
    loop_id VARCHAR(8) PRIMARY KEY REFERENCES loop_states(id) ON DELETE CASCADE,
    phase_path TEXT NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (phase_path, task_name) REFERENCES tasks(phase_path, name) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_tasks_phase_path ON tasks(phase_path);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_name_search ON tasks USING gin (name gin_trgm_ops);
