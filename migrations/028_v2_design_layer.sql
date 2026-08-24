-- Phase 2 (v2 design layer): additive only. Gives the design layer a home in the
-- Phase document -- Module Layout, Skeleton Index, Collaboration And Wiring, Test
-- List, Design Decisions -- and drops the unused task_breakdown column (the field is
-- removed from the model; DocumentType.TASK_BREAKDOWN, the Task workflow, and its
-- tables are unrelated and out of scope until Phase 6).
ALTER TABLE phases ADD COLUMN IF NOT EXISTS module_layout TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS skeleton_index TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS collaboration_and_wiring TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS test_list TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS design_shape_additional TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS open_design_decisions TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS settled_design_decisions TEXT;

ALTER TABLE phases ADD COLUMN IF NOT EXISTS shape_gate VARCHAR(50) NOT NULL DEFAULT 'unshaped';
ALTER TABLE phases ADD CONSTRAINT valid_shape_gate
    CHECK (shape_gate IN ('unshaped', 'shape-proposed', 'shape-settled', 'shape-amended'));

ALTER TABLE phases DROP COLUMN IF EXISTS task_breakdown;
