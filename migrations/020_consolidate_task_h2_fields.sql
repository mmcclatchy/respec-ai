-- Consolidate Task H3-level columns into H2-level columns.
-- Adds research column to capture ## Research section (previously silently dropped).

-- Step 1: Add new H2-level columns
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS identity TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS overview TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS implementation TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS quality TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS research TEXT;

-- Step 2: Migrate data
UPDATE tasks SET
  identity = '### Phase Path' || E'\n' || COALESCE(phase_path, ''),
  overview = '### Goal' || E'\n' || COALESCE(goal, '') || E'\n\n'
    || '### Acceptance Criteria' || E'\n' || COALESCE(acceptance_criteria, '') || E'\n\n'
    || '### Technology Stack Reference' || E'\n' || COALESCE(tech_stack_reference, ''),
  implementation = '### Checklist' || E'\n' || COALESCE(implementation_checklist, '') || E'\n\n'
    || '### Steps' || E'\n' || COALESCE(implementation_steps, ''),
  quality = '### Testing Strategy' || E'\n' || COALESCE(testing_strategy, ''),
  research = 'Research not specified';

-- Step 3: Set defaults
ALTER TABLE tasks ALTER COLUMN identity SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN identity SET DEFAULT 'Identity not specified';
ALTER TABLE tasks ALTER COLUMN overview SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN overview SET DEFAULT 'Overview not specified';
ALTER TABLE tasks ALTER COLUMN implementation SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN implementation SET DEFAULT 'Implementation not specified';
ALTER TABLE tasks ALTER COLUMN quality SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN quality SET DEFAULT 'Quality not specified';
ALTER TABLE tasks ALTER COLUMN research SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN research SET DEFAULT 'Research not specified';

-- Step 4: Drop old H3-level columns (keep phase_path as DB key)
ALTER TABLE tasks DROP COLUMN IF EXISTS goal;
ALTER TABLE tasks DROP COLUMN IF EXISTS acceptance_criteria;
ALTER TABLE tasks DROP COLUMN IF EXISTS tech_stack_reference;
ALTER TABLE tasks DROP COLUMN IF EXISTS implementation_checklist;
ALTER TABLE tasks DROP COLUMN IF EXISTS implementation_steps;
ALTER TABLE tasks DROP COLUMN IF EXISTS testing_strategy;
