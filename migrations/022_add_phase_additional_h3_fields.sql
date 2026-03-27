ALTER TABLE phases ADD COLUMN IF NOT EXISTS implementation_plan_references TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS system_design_additional TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS implementation_additional TEXT;
ALTER TABLE phases ADD COLUMN IF NOT EXISTS additional_details_additional TEXT;
