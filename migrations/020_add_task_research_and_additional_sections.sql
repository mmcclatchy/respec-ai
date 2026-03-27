ALTER TABLE tasks ADD COLUMN IF NOT EXISTS research TEXT NOT NULL DEFAULT 'Research not specified';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS additional_sections JSONB;
