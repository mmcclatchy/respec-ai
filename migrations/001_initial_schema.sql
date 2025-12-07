-- Migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Loop States (22 abstract methods require this)
CREATE TABLE loop_states (
    id VARCHAR(8) PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    loop_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    current_score INTEGER NOT NULL DEFAULT 0 CHECK (current_score BETWEEN 0 AND 100),
    score_history INTEGER[] NOT NULL DEFAULT '{}',
    iteration INTEGER NOT NULL DEFAULT 1 CHECK (iteration >= 1),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    feedback_history JSONB NOT NULL DEFAULT '[]',

    CONSTRAINT valid_loop_type CHECK (loop_type IN ('plan', 'roadmap', 'spec', 'build_plan', 'build_code', 'analyst')),
    CONSTRAINT valid_status CHECK (status IN ('initialized', 'in_progress', 'completed', 'user_input', 'refine'))
);

-- Loop History Queue (bounded to max_history_size)
CREATE TABLE loop_history (
    loop_id VARCHAR(8) PRIMARY KEY REFERENCES loop_states(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sequence_number SERIAL
);

-- Objective Feedback
CREATE TABLE objective_feedback (
    loop_id VARCHAR(8) PRIMARY KEY REFERENCES loop_states(id) ON DELETE CASCADE,
    feedback TEXT NOT NULL,
    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roadmaps (all 16 string fields from Roadmap model)
CREATE TABLE roadmaps (
    project_name VARCHAR(255) PRIMARY KEY,
    project_goal TEXT NOT NULL,
    total_duration TEXT NOT NULL,
    team_size TEXT NOT NULL,
    roadmap_budget TEXT NOT NULL,
    critical_path_analysis TEXT NOT NULL,
    key_risks TEXT NOT NULL,
    mitigation_plans TEXT NOT NULL,
    buffer_time TEXT NOT NULL,
    development_resources TEXT NOT NULL,
    infrastructure_requirements TEXT NOT NULL,
    external_dependencies TEXT NOT NULL,
    quality_assurance_plan TEXT NOT NULL,
    technical_milestones TEXT NOT NULL,
    business_milestones TEXT NOT NULL,
    quality_gates TEXT NOT NULL,
    performance_targets TEXT NOT NULL,
    roadmap_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_roadmap_status CHECK (roadmap_status IN ('draft', 'in-review', 'approved', 'in-progress', 'completed', 'blocked'))
);

-- Technical Specs (with frozen fields: objectives, scope, dependencies, deliverables)
CREATE TABLE technical_specs (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    spec_name VARCHAR(255) NOT NULL,
    phase_name TEXT NOT NULL,

    -- Frozen fields (NEVER updated after iteration 0)
    objectives TEXT NOT NULL,
    scope TEXT NOT NULL,
    dependencies TEXT NOT NULL,
    deliverables TEXT NOT NULL,

    -- Optional flexible fields
    architecture TEXT,
    technology_stack TEXT,
    functional_requirements TEXT,
    non_functional_requirements TEXT,
    development_plan TEXT,
    testing_strategy TEXT,
    research_requirements TEXT,
    success_criteria TEXT,
    integration_context TEXT,

    -- Flexible storage
    additional_sections JSONB DEFAULT '{}',

    -- State tracking
    iteration INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    spec_status VARCHAR(50) NOT NULL DEFAULT 'draft',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(project_name, spec_name),
    CONSTRAINT valid_spec_status CHECK (spec_status IN ('draft', 'in-review', 'approved', 'implementation-ready', 'in-development', 'completed'))
);

-- Project Plans (all 31 string fields from ProjectPlan model)
CREATE TABLE project_plans (
    project_name VARCHAR(255) PRIMARY KEY,

    -- Executive Summary
    project_vision TEXT NOT NULL,
    project_mission TEXT NOT NULL,
    project_timeline TEXT NOT NULL,
    project_budget TEXT NOT NULL,

    -- Business Objectives
    primary_objectives TEXT NOT NULL,
    success_metrics TEXT NOT NULL,
    key_performance_indicators TEXT NOT NULL,

    -- Project Scope
    included_features TEXT NOT NULL,
    excluded_features TEXT NOT NULL,
    project_assumptions TEXT NOT NULL,
    project_constraints TEXT NOT NULL,

    -- Stakeholders
    project_sponsor TEXT NOT NULL,
    key_stakeholders TEXT NOT NULL,
    end_users TEXT NOT NULL,

    -- Project Structure
    work_breakdown TEXT NOT NULL,
    phases_overview TEXT NOT NULL,
    project_dependencies TEXT NOT NULL,

    -- Resource Requirements
    team_structure TEXT NOT NULL,
    technology_requirements TEXT NOT NULL,
    infrastructure_needs TEXT NOT NULL,

    -- Risk Management
    identified_risks TEXT NOT NULL,
    mitigation_strategies TEXT NOT NULL,
    contingency_plans TEXT NOT NULL,

    -- Quality Assurance
    quality_standards TEXT NOT NULL,
    testing_strategy TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,

    -- Communication Plan
    reporting_structure TEXT NOT NULL,
    meeting_schedule TEXT NOT NULL,
    documentation_standards TEXT NOT NULL,

    -- Metadata
    project_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_project_status CHECK (project_status IN ('draft', 'in-review', 'approved', 'active', 'completed', 'cancelled'))
);

-- Loop-to-Spec Mapping (temporary refinement sessions)
CREATE TABLE loop_to_spec_mappings (
    loop_id VARCHAR(8) PRIMARY KEY REFERENCES loop_states(id) ON DELETE CASCADE,
    project_name VARCHAR(255) NOT NULL,
    spec_name VARCHAR(255) NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_name, spec_name) REFERENCES technical_specs(project_name, spec_name) ON DELETE CASCADE
);

-- Record migration
INSERT INTO schema_migrations (version, description) VALUES (1, 'Initial schema - all core tables');
