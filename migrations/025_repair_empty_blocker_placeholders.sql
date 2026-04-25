WITH repaired AS (
    SELECT
        loop_states.id,
        jsonb_agg(
            CASE
                WHEN jsonb_typeof(feedback_item.item->'blockers') = 'array' THEN
                    jsonb_set(
                        feedback_item.item,
                        '{blockers}',
                        COALESCE(
                            (
                                SELECT jsonb_agg(blocker.value)
                                FROM jsonb_array_elements(feedback_item.item->'blockers') AS blocker(value)
                                WHERE NOT (
                                    jsonb_typeof(blocker.value) = 'string'
                                    AND (
                                        regexp_replace(blocker.value #>> '{}', '[[:space:]]+', '', 'g') = ''
                                        OR lower(trim(both ' .:-' FROM blocker.value #>> '{}')) IN (
                                            'none',
                                            'none identified',
                                            'none provided',
                                            'no blockers',
                                            'no active blockers',
                                            'n/a',
                                            'na'
                                        )
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                ELSE feedback_item.item
            END
            ORDER BY feedback_item.ordinality
        ) AS feedback_history
    FROM loop_states
    CROSS JOIN LATERAL jsonb_array_elements(loop_states.feedback_history) WITH ORDINALITY AS feedback_item(item, ordinality)
    GROUP BY loop_states.id
)
UPDATE loop_states
SET
    feedback_history = repaired.feedback_history,
    updated_at = CURRENT_TIMESTAMP
FROM repaired
WHERE loop_states.id = repaired.id
  AND loop_states.feedback_history IS DISTINCT FROM repaired.feedback_history;

WITH repaired_reviewer_results AS (
    SELECT
        loop_id,
        review_iteration,
        reviewer_name,
        COALESCE(
            (
                SELECT jsonb_agg(blocker.value)
                FROM jsonb_array_elements(reviewer_results.blockers) AS blocker(value)
                WHERE NOT (
                    jsonb_typeof(blocker.value) = 'string'
                    AND (
                        regexp_replace(blocker.value #>> '{}', '[[:space:]]+', '', 'g') = ''
                        OR lower(trim(both ' .:-' FROM blocker.value #>> '{}')) IN (
                            'none',
                            'none identified',
                            'none provided',
                            'no blockers',
                            'no active blockers',
                            'n/a',
                            'na'
                        )
                    )
                )
            ),
            '[]'::jsonb
        ) AS blockers
    FROM reviewer_results
    WHERE jsonb_typeof(blockers) = 'array'
)
UPDATE reviewer_results
SET
    blockers = repaired_reviewer_results.blockers,
    updated_at = CURRENT_TIMESTAMP
FROM repaired_reviewer_results
WHERE reviewer_results.loop_id = repaired_reviewer_results.loop_id
  AND reviewer_results.review_iteration = repaired_reviewer_results.review_iteration
  AND reviewer_results.reviewer_name = repaired_reviewer_results.reviewer_name
  AND reviewer_results.blockers IS DISTINCT FROM repaired_reviewer_results.blockers;

INSERT INTO schema_migrations (version, description)
VALUES (25, 'Repair empty blocker placeholder entries in feedback histories and reviewer results')
ON CONFLICT DO NOTHING;
