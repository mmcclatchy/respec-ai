-- Consolidate 28 H3-level plan columns into 10 H2-level columns.
--
-- The Plan model now enforces H2 headers as its schema boundary.
-- Each H2 section is one field that captures all sub-header content.
-- This prevents silent data loss when agents add custom H3 subsections.

-- Step 1: Add new H2-level columns
ALTER TABLE plans ADD COLUMN IF NOT EXISTS executive_summary TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS business_objectives TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS plan_scope TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS stakeholders TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS architecture_direction TEXT;
-- technology_decisions already exists, will be repurposed in-place
ALTER TABLE plans ADD COLUMN IF NOT EXISTS plan_structure TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS resource_requirements TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS risk_management TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS quality_assurance TEXT;

-- Step 2: Migrate data — combine H3 columns with headers into H2 blobs
UPDATE plans SET
  executive_summary = '### Vision' || E'\n' || COALESCE(project_vision, '') || E'\n\n'
    || '### Mission' || E'\n' || COALESCE(project_mission, '') || E'\n\n'
    || '### Timeline' || E'\n' || COALESCE(project_timeline, '') || E'\n\n'
    || '### Budget' || E'\n' || COALESCE(project_budget, ''),
  business_objectives = '### Primary Objectives' || E'\n' || COALESCE(primary_objectives, '') || E'\n\n'
    || '### Success Metrics' || E'\n' || COALESCE(success_metrics, '') || E'\n\n'
    || '### Key Performance Indicators' || E'\n' || COALESCE(key_performance_indicators, ''),
  plan_scope = '### Included Features' || E'\n' || COALESCE(included_features, '') || E'\n\n'
    || '### Anti-Requirements' || E'\n' || COALESCE(anti_requirements, '') || E'\n\n'
    || '### Assumptions' || E'\n' || COALESCE(project_assumptions, '') || E'\n\n'
    || '### Constraints' || E'\n' || COALESCE(project_constraints, ''),
  stakeholders = '### Plan Sponsor' || E'\n' || COALESCE(project_sponsor, '') || E'\n\n'
    || '### Key Stakeholders' || E'\n' || COALESCE(key_stakeholders, '') || E'\n\n'
    || '### End Users' || E'\n' || COALESCE(end_users, ''),
  architecture_direction = '### Architecture Overview' || E'\n' || COALESCE(architecture_overview, '') || E'\n\n'
    || '### Data Flow' || E'\n' || COALESCE(data_flow, ''),
  technology_decisions = '### Chosen Technologies' || E'\n' || COALESCE(technology_decisions, '') || E'\n\n'
    || '### Rejected Technologies' || E'\n' || COALESCE(technology_rejections, ''),
  plan_structure = '### Work Breakdown' || E'\n' || COALESCE(work_breakdown, '') || E'\n\n'
    || '### Phases Overview' || E'\n' || COALESCE(phases_overview, '') || E'\n\n'
    || '### Dependencies' || E'\n' || COALESCE(project_dependencies, ''),
  resource_requirements = '### Team Structure' || E'\n' || COALESCE(team_structure, '') || E'\n\n'
    || '### Technology Requirements' || E'\n' || COALESCE(technology_requirements, '') || E'\n\n'
    || '### Infrastructure Needs' || E'\n' || COALESCE(infrastructure_needs, ''),
  risk_management = '### Identified Risks' || E'\n' || COALESCE(identified_risks, '') || E'\n\n'
    || '### Mitigation Strategies' || E'\n' || COALESCE(mitigation_strategies, '') || E'\n\n'
    || '### Contingency Plans' || E'\n' || COALESCE(contingency_plans, ''),
  quality_assurance = '### Quality Bar' || E'\n' || COALESCE(quality_bar, '') || E'\n\n'
    || '### Testing Strategy' || E'\n' || COALESCE(testing_strategy, '') || E'\n\n'
    || '### Acceptance Criteria' || E'\n' || COALESCE(acceptance_criteria, '');

-- Step 3: Set NOT NULL and defaults on new columns
ALTER TABLE plans ALTER COLUMN executive_summary SET NOT NULL;
ALTER TABLE plans ALTER COLUMN executive_summary SET DEFAULT 'Executive Summary not specified';
ALTER TABLE plans ALTER COLUMN business_objectives SET NOT NULL;
ALTER TABLE plans ALTER COLUMN business_objectives SET DEFAULT 'Business Objectives not specified';
ALTER TABLE plans ALTER COLUMN plan_scope SET NOT NULL;
ALTER TABLE plans ALTER COLUMN plan_scope SET DEFAULT 'Plan Scope not specified';
ALTER TABLE plans ALTER COLUMN stakeholders SET NOT NULL;
ALTER TABLE plans ALTER COLUMN stakeholders SET DEFAULT 'Stakeholders not specified';
ALTER TABLE plans ALTER COLUMN architecture_direction SET NOT NULL;
ALTER TABLE plans ALTER COLUMN architecture_direction SET DEFAULT 'Architecture Direction not specified';
ALTER TABLE plans ALTER COLUMN plan_structure SET NOT NULL;
ALTER TABLE plans ALTER COLUMN plan_structure SET DEFAULT 'Plan Structure not specified';
ALTER TABLE plans ALTER COLUMN resource_requirements SET NOT NULL;
ALTER TABLE plans ALTER COLUMN resource_requirements SET DEFAULT 'Resource Requirements not specified';
ALTER TABLE plans ALTER COLUMN risk_management SET NOT NULL;
ALTER TABLE plans ALTER COLUMN risk_management SET DEFAULT 'Risk Management not specified';
ALTER TABLE plans ALTER COLUMN quality_assurance SET NOT NULL;
ALTER TABLE plans ALTER COLUMN quality_assurance SET DEFAULT 'Quality Assurance not specified';

-- Step 4: Drop old H3-level columns
ALTER TABLE plans DROP COLUMN IF EXISTS project_vision;
ALTER TABLE plans DROP COLUMN IF EXISTS project_mission;
ALTER TABLE plans DROP COLUMN IF EXISTS project_timeline;
ALTER TABLE plans DROP COLUMN IF EXISTS project_budget;
ALTER TABLE plans DROP COLUMN IF EXISTS primary_objectives;
ALTER TABLE plans DROP COLUMN IF EXISTS success_metrics;
ALTER TABLE plans DROP COLUMN IF EXISTS key_performance_indicators;
ALTER TABLE plans DROP COLUMN IF EXISTS included_features;
ALTER TABLE plans DROP COLUMN IF EXISTS anti_requirements;
ALTER TABLE plans DROP COLUMN IF EXISTS project_assumptions;
ALTER TABLE plans DROP COLUMN IF EXISTS project_constraints;
ALTER TABLE plans DROP COLUMN IF EXISTS project_sponsor;
ALTER TABLE plans DROP COLUMN IF EXISTS key_stakeholders;
ALTER TABLE plans DROP COLUMN IF EXISTS end_users;
ALTER TABLE plans DROP COLUMN IF EXISTS architecture_overview;
ALTER TABLE plans DROP COLUMN IF EXISTS data_flow;
ALTER TABLE plans DROP COLUMN IF EXISTS technology_rejections;
ALTER TABLE plans DROP COLUMN IF EXISTS work_breakdown;
ALTER TABLE plans DROP COLUMN IF EXISTS phases_overview;
ALTER TABLE plans DROP COLUMN IF EXISTS project_dependencies;
ALTER TABLE plans DROP COLUMN IF EXISTS team_structure;
ALTER TABLE plans DROP COLUMN IF EXISTS technology_requirements;
ALTER TABLE plans DROP COLUMN IF EXISTS infrastructure_needs;
ALTER TABLE plans DROP COLUMN IF EXISTS identified_risks;
ALTER TABLE plans DROP COLUMN IF EXISTS mitigation_strategies;
ALTER TABLE plans DROP COLUMN IF EXISTS contingency_plans;
ALTER TABLE plans DROP COLUMN IF EXISTS quality_bar;
ALTER TABLE plans DROP COLUMN IF EXISTS testing_strategy;
ALTER TABLE plans DROP COLUMN IF EXISTS acceptance_criteria;
