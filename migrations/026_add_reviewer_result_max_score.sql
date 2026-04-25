ALTER TABLE reviewer_results
    ADD COLUMN IF NOT EXISTS max_score INTEGER;

WITH inferred_reviewer_scores AS (
    SELECT
        loop_id,
        review_iteration,
        reviewer_name,
        regexp_match(
            feedback_markdown,
            'Score[[:space:]]*:[[:space:]]*[0-9]+[[:space:]]*/[[:space:]]*([0-9]+)',
            'i'
        ) AS score_match
    FROM reviewer_results
    WHERE max_score IS NULL
)
UPDATE reviewer_results
SET max_score = CASE
    WHEN inferred_reviewer_scores.score_match IS NOT NULL
        AND (inferred_reviewer_scores.score_match)[1]::INTEGER > 0
        AND reviewer_results.score <= (inferred_reviewer_scores.score_match)[1]::INTEGER
        THEN (inferred_reviewer_scores.score_match)[1]::INTEGER
    ELSE 100
END
FROM inferred_reviewer_scores
WHERE reviewer_results.loop_id = inferred_reviewer_scores.loop_id
    AND reviewer_results.review_iteration = inferred_reviewer_scores.review_iteration
    AND reviewer_results.reviewer_name = inferred_reviewer_scores.reviewer_name
    AND reviewer_results.max_score IS NULL;

ALTER TABLE reviewer_results
    ALTER COLUMN max_score SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'reviewer_results_max_score_positive'
    ) THEN
        ALTER TABLE reviewer_results
            ADD CONSTRAINT reviewer_results_max_score_positive CHECK (max_score > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'reviewer_results_score_within_max_score'
    ) THEN
        ALTER TABLE reviewer_results
            ADD CONSTRAINT reviewer_results_score_within_max_score CHECK (score BETWEEN 0 AND max_score);
    END IF;
END $$;

INSERT INTO schema_migrations (version, description)
VALUES (26, 'Add max_score to reviewer results for bounded normalized consolidation')
ON CONFLICT DO NOTHING;
