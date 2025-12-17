-- Migration: Add implementation_checklist column to tasks table
-- This adds a prioritized, actionable checklist with verification methods for the coding agent

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS implementation_checklist TEXT NOT NULL DEFAULT 'Implementation checklist not specified';
