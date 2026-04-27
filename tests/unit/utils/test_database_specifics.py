from pathlib import Path

import pytest
from asyncpg.exceptions import CheckViolationError, UniqueViolationError

from src.models.enums import CriticAgent, PhaseStatus
from src.models.feedback import CriticFeedback, ReviewFinding, ReviewerResult
from src.models.phase import Phase
from src.utils.database_pool import db_pool
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState
from src.utils.state_manager import PostgresStateManager


class TestDatabaseCascadeDeletes:
    @pytest.mark.asyncio
    async def test_cascade_delete_on_objective_feedback(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.PHASE)
        await db_state_manager.add_loop(loop, 'test-project')
        await db_state_manager.store_objective_feedback(loop.id, 'Test feedback')

        async with db_pool.acquire() as conn:
            count_before = await conn.fetchval('SELECT COUNT(*) FROM objective_feedback WHERE loop_id = $1', loop.id)
            assert count_before == 1

        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM loop_states WHERE id = $1', loop.id)

        async with db_pool.acquire() as conn:
            count_after = await conn.fetchval('SELECT COUNT(*) FROM objective_feedback WHERE loop_id = $1', loop.id)
            assert count_after == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_on_loop_to_phase_mappings(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.PHASE)
        await db_state_manager.add_loop(loop, 'test-project')

        phase = Phase(
            phase_name='Test Phase',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            phase_status=PhaseStatus.DRAFT,
        )
        await db_state_manager.store_phase('test-project', phase)
        await db_state_manager.link_loop_to_phase(loop.id, 'test-project', phase.phase_name)

        async with db_pool.acquire() as conn:
            count_before = await conn.fetchval(
                'SELECT COUNT(*) FROM loop_to_phase_mappings WHERE loop_id = $1', loop.id
            )
            assert count_before == 1

        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM loop_states WHERE id = $1', loop.id)

        async with db_pool.acquire() as conn:
            count_after = await conn.fetchval('SELECT COUNT(*) FROM loop_to_phase_mappings WHERE loop_id = $1', loop.id)
            assert count_after == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_on_user_feedback_entries(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.PHASE)
        await db_state_manager.add_loop(loop, 'test-project')
        await db_state_manager.append_user_feedback(loop.id, 'user feedback')

        async with db_pool.acquire() as conn:
            count_before = await conn.fetchval('SELECT COUNT(*) FROM user_feedback_entries WHERE loop_id = $1', loop.id)
            assert count_before == 1

        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM loop_states WHERE id = $1', loop.id)

        async with db_pool.acquire() as conn:
            count_after = await conn.fetchval('SELECT COUNT(*) FROM user_feedback_entries WHERE loop_id = $1', loop.id)
            assert count_after == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_on_loop_analysis(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.ANALYST)
        await db_state_manager.add_loop(loop, 'test-project')
        await db_state_manager.upsert_loop_analysis(loop.id, 'analysis')

        async with db_pool.acquire() as conn:
            count_before = await conn.fetchval('SELECT COUNT(*) FROM loop_analysis WHERE loop_id = $1', loop.id)
            assert count_before == 1

        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM loop_states WHERE id = $1', loop.id)

        async with db_pool.acquire() as conn:
            count_after = await conn.fetchval('SELECT COUNT(*) FROM loop_analysis WHERE loop_id = $1', loop.id)
            assert count_after == 0


class TestDatabaseJSONBSerialization:
    @pytest.mark.asyncio
    async def test_critic_feedback_jsonb_roundtrip(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.PHASE)
        feedback1 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.PHASE_CRITIC,
            iteration=1,
            overall_score=85,
            assessment_summary='Good progress',
            detailed_feedback='Well structured with clear objectives but missing some details',
            key_issues=['Missing details'],
            blockers=['Missing required section: Testing Strategy'],
            recommendations=['Add more context'],
        )
        feedback2 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.PHASE_CRITIC,
            iteration=2,
            overall_score=90,
            assessment_summary='Excellent work',
            detailed_feedback='Comprehensive and well documented',
            key_issues=[],
            recommendations=[],
        )

        loop.feedback_history.append(feedback1)
        loop.feedback_history.append(feedback2)

        await db_state_manager.add_loop(loop, 'test-project')
        retrieved_loop = await db_state_manager.get_loop(loop.id)

        assert len(retrieved_loop.feedback_history) == 2
        assert retrieved_loop.feedback_history[0] == feedback1
        assert retrieved_loop.feedback_history[1] == feedback2
        assert retrieved_loop.feedback_history[0].overall_score == 85
        assert retrieved_loop.feedback_history[0].assessment_summary == 'Good progress'
        assert retrieved_loop.feedback_history[0].key_issues == ['Missing details']
        assert retrieved_loop.feedback_history[0].blockers == ['Missing required section: Testing Strategy']

    @pytest.mark.asyncio
    async def test_phase_additional_sections_jsonb_roundtrip(self, db_state_manager: PostgresStateManager) -> None:
        phase = Phase(
            phase_name='Test Phase',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            phase_status=PhaseStatus.DRAFT,
            additional_sections={'custom_field': 'custom value', 'notes': 'note1, note2'},
        )

        await db_state_manager.store_phase('test-project', phase)
        retrieved_phase = await db_state_manager.get_phase('test-project', phase.phase_name)

        assert retrieved_phase.additional_sections == {'custom_field': 'custom value', 'notes': 'note1, note2'}
        assert retrieved_phase.additional_sections is not None
        assert retrieved_phase.additional_sections['custom_field'] == 'custom value'
        assert retrieved_phase.additional_sections['notes'] == 'note1, note2'

    @pytest.mark.asyncio
    async def test_empty_blocker_placeholder_migration_repairs_persisted_feedback_json(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop_id = 'badblk01'
        bad_feedback_json = """
        [
          {
            "loop_id": "badblk01",
            "critic_agent": "task-critic",
            "iteration": 1,
            "overall_score": 100,
            "assessment_summary": "Ready with no blockers.",
            "detailed_feedback": "Ready.",
            "key_issues": [],
            "blockers": ["None."],
            "recommendations": [],
            "timestamp": "2026-04-24T23:34:22.546225"
          }
        ]
        """

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_states (
                    id, plan_name, loop_type, status, current_score,
                    score_history, iteration, created_at, updated_at, feedback_history
                ) VALUES (
                    $1, 'test-project', 'task', 'refine', 100,
                    ARRAY[100]::integer[], 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, $2::jsonb
                )
                """,
                loop_id,
                bad_feedback_json,
            )
            migration_sql = Path('migrations/025_repair_empty_blocker_placeholders.sql').read_text()
            await conn.execute(migration_sql)
            blockers = await conn.fetchval(
                "SELECT feedback_history->0->'blockers' FROM loop_states WHERE id = $1",
                loop_id,
            )

        assert blockers == '[]'
        repaired_loop = await db_state_manager.get_loop(loop_id)
        assert repaired_loop.feedback_history[0].blockers == []

    @pytest.mark.asyncio
    async def test_empty_blocker_migration_repairs_blank_persisted_feedback_json(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop_id = 'blankfb1'
        bad_feedback_json = """
        [
          {
            "loop_id": "blankfb1",
            "critic_agent": "task-critic",
            "iteration": 1,
            "overall_score": 100,
            "assessment_summary": "Ready with a blank blocker row.",
            "detailed_feedback": "Ready.",
            "key_issues": [],
            "blockers": ["   "],
            "recommendations": [],
            "timestamp": "2026-04-24T23:34:22.546225"
          }
        ]
        """

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_states (
                    id, plan_name, loop_type, status, current_score,
                    score_history, iteration, created_at, updated_at, feedback_history
                ) VALUES (
                    $1, 'test-project', 'task', 'refine', 100,
                    ARRAY[100]::integer[], 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, $2::jsonb
                )
                """,
                loop_id,
                bad_feedback_json,
            )
            migration_sql = Path('migrations/025_repair_empty_blocker_placeholders.sql').read_text()
            await conn.execute(migration_sql)
            blockers = await conn.fetchval(
                "SELECT feedback_history->0->'blockers' FROM loop_states WHERE id = $1",
                loop_id,
            )

        assert blockers == '[]'
        repaired_loop = await db_state_manager.get_loop(loop_id)
        assert repaired_loop.feedback_history[0].blockers == []

    @pytest.mark.asyncio
    async def test_empty_blocker_migration_preserves_real_blockers_in_mixed_feedback_json(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop_id = 'mixedfb1'
        mixed_feedback_json = """
        [
          {
            "loop_id": "mixedfb1",
            "critic_agent": "task-critic",
            "iteration": 1,
            "overall_score": 100,
            "assessment_summary": "Mixed blocker data.",
            "detailed_feedback": "Ready.",
            "key_issues": [],
            "blockers": [" ", "Real blocker"],
            "recommendations": [],
            "timestamp": "2026-04-24T23:34:22.546225"
          }
        ]
        """

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_states (
                    id, plan_name, loop_type, status, current_score,
                    score_history, iteration, created_at, updated_at, feedback_history
                ) VALUES (
                    $1, 'test-project', 'task', 'refine', 100,
                    ARRAY[100]::integer[], 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, $2::jsonb
                )
                """,
                loop_id,
                mixed_feedback_json,
            )
            migration_sql = Path('migrations/025_repair_empty_blocker_placeholders.sql').read_text()
            await conn.execute(migration_sql)

        repaired_loop = await db_state_manager.get_loop(loop_id)
        assert repaired_loop.feedback_history[0].blockers == ['Real blocker']

    @pytest.mark.asyncio
    async def test_empty_blocker_placeholder_migration_repairs_reviewer_result_blockers(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop_id = 'revblk01'

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_states (
                    id, plan_name, loop_type, status, current_score,
                    score_history, iteration, created_at, updated_at, feedback_history
                ) VALUES (
                    $1, 'test-project', 'task', 'refine', 100,
                    ARRAY[100]::integer[], 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '[]'::jsonb
                )
                """,
                loop_id,
            )
            await conn.execute(
                """
                INSERT INTO reviewer_results (
                    loop_id, review_iteration, reviewer_name, feedback_markdown,
                    score, max_score, blockers
                )
                VALUES (
                    $1, 1, 'code-quality-reviewer', '### Code Quality (Score: 25/25)',
                    25, 25, '["None."]'::jsonb
                )
                """,
                loop_id,
            )
            migration_sql = Path('migrations/025_repair_empty_blocker_placeholders.sql').read_text()
            await conn.execute(migration_sql)
            blockers = await conn.fetchval(
                """
                SELECT blockers
                FROM reviewer_results
                WHERE loop_id = $1
                    AND review_iteration = 1
                    AND reviewer_name = 'code-quality-reviewer'
                """,
                loop_id,
            )

        assert blockers == '[]'

    @pytest.mark.asyncio
    async def test_empty_blocker_migration_repairs_blank_reviewer_result_blockers(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop_id = 'blankrv1'

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_states (
                    id, plan_name, loop_type, status, current_score,
                    score_history, iteration, created_at, updated_at, feedback_history
                ) VALUES (
                    $1, 'test-project', 'task', 'refine', 100,
                    ARRAY[100]::integer[], 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '[]'::jsonb
                )
                """,
                loop_id,
            )
            await conn.execute(
                """
                INSERT INTO reviewer_results (
                    loop_id, review_iteration, reviewer_name, feedback_markdown,
                    score, max_score, blockers
                )
                VALUES (
                    $1, 1, 'code-quality-reviewer', '### Code Quality (Score: 25/25)',
                    25, 25, '["   "]'::jsonb
                )
                """,
                loop_id,
            )
            migration_sql = Path('migrations/025_repair_empty_blocker_placeholders.sql').read_text()
            await conn.execute(migration_sql)
            blockers = await conn.fetchval(
                """
                SELECT blockers
                FROM reviewer_results
                WHERE loop_id = $1
                    AND review_iteration = 1
                    AND reviewer_name = 'code-quality-reviewer'
                """,
                loop_id,
            )

        assert blockers == '[]'

    @pytest.mark.asyncio
    async def test_reviewer_result_max_score_migration_infers_legacy_denominators(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop_id = 'mig02601'
        migration_sql = Path('migrations/026_add_reviewer_result_max_score.sql').read_text()

        async def restore_schema() -> None:
            async with db_pool.acquire() as conn:
                await conn.execute('DELETE FROM loop_states WHERE id = $1', loop_id)
                await conn.execute(
                    """
                    UPDATE reviewer_results
                    SET max_score = 100
                    WHERE max_score IS NULL
                    """
                )
                await conn.execute(
                    """
                    ALTER TABLE reviewer_results
                        ALTER COLUMN max_score SET NOT NULL
                    """
                )
                await conn.execute(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'reviewer_results_score_within_max_score'
                        ) THEN
                            ALTER TABLE reviewer_results
                                ADD CONSTRAINT reviewer_results_score_within_max_score
                                CHECK (score BETWEEN 0 AND max_score);
                        END IF;
                    END $$;
                    """
                )

        try:
            async with db_pool.acquire() as conn:
                await conn.execute('DELETE FROM loop_states WHERE id = $1', loop_id)
                await conn.execute(
                    'ALTER TABLE reviewer_results DROP CONSTRAINT IF EXISTS reviewer_results_score_within_max_score'
                )
                await conn.execute('ALTER TABLE reviewer_results ALTER COLUMN max_score DROP NOT NULL')
                await conn.execute(
                    """
                    INSERT INTO loop_states (
                        id, plan_name, loop_type, status, current_score,
                        score_history, iteration, created_at, updated_at, feedback_history
                    ) VALUES (
                        $1, 'test-project', 'task', 'refine', 90,
                        ARRAY[90]::integer[], 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '[]'::jsonb
                    )
                    """,
                    loop_id,
                )
                await conn.executemany(
                    """
                    INSERT INTO reviewer_results (
                        loop_id, review_iteration, reviewer_name, feedback_markdown,
                        score, blockers
                    )
                    VALUES ($1, 1, $2, $3, $4, '[]'::jsonb)
                    """,
                    [
                        (
                            loop_id,
                            'automated-quality-checker',
                            '### Automated Quality Check\nScore: 50/50\nNo failures.',
                            50,
                        ),
                        (
                            loop_id,
                            'spec-alignment-reviewer',
                            '### Spec Alignment Review\nScore: 45/50\nLegacy normalized row.',
                            90,
                        ),
                        (
                            loop_id,
                            'code-quality-reviewer',
                            '### Code Quality Review\nNo bounded denominator in this legacy row.',
                            88,
                        ),
                    ],
                )

                await conn.execute(migration_sql)
                rows = await conn.fetch(
                    """
                    SELECT reviewer_name, score, max_score
                    FROM reviewer_results
                    WHERE loop_id = $1
                    ORDER BY reviewer_name
                    """,
                    loop_id,
                )
                violating_rows = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM reviewer_results
                    WHERE loop_id = $1
                        AND score NOT BETWEEN 0 AND max_score
                    """,
                    loop_id,
                )

            max_scores = {row['reviewer_name']: row['max_score'] for row in rows}
            assert max_scores == {
                'automated-quality-checker': 50,
                'code-quality-reviewer': 100,
                'spec-alignment-reviewer': 100,
            }
            assert violating_rows == 0
        finally:
            await restore_schema()


class TestReviewerResultStateManager:
    @pytest.mark.asyncio
    async def test_postgres_lists_latest_reviewer_results_at_or_before_iteration(
        self, db_state_manager: PostgresStateManager
    ) -> None:
        loop = LoopState(loop_type=LoopType.TASK)
        await db_state_manager.add_loop(loop, 'test-project')

        for iteration, score in [(1, 20), (2, 24), (4, 10)]:
            await db_state_manager.upsert_reviewer_result(
                ReviewerResult(
                    loop_id=loop.id,
                    review_iteration=iteration,
                    reviewer_name=CriticAgent.CODE_QUALITY_REVIEWER,
                    feedback_markdown=f'### Code Quality (Score: {score}/25)',
                    score=score,
                    max_score=25,
                    blockers=[],
                    findings=[
                        ReviewFinding(
                            priority='P3',
                            feedback=f'Iteration {iteration} advisory in src/main.py:10',
                        )
                    ],
                )
            )

        latest_results = await db_state_manager.list_latest_reviewer_results(
            loop.id,
            3,
            ['code-quality-reviewer'],
        )

        assert len(latest_results) == 1
        latest = latest_results[0]
        assert latest.review_iteration == 2
        assert latest.score == 24
        assert latest.findings[0].feedback == 'Iteration 2 advisory in src/main.py:10'


class TestDatabaseConstraints:
    @pytest.mark.asyncio
    async def test_unique_constraint_on_project_phase_name(self, db_state_manager: PostgresStateManager) -> None:
        phase = Phase(
            phase_name='test-phase',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            phase_status=PhaseStatus.DRAFT,
        )

        await db_state_manager.store_phase('test-project', phase)

        async with db_pool.acquire() as conn:
            with pytest.raises(UniqueViolationError):
                await conn.execute(
                    """
                    INSERT INTO phases (
                        id, plan_name, phase_name, objectives, scope,
                        dependencies, deliverables, phase_status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    'testid01',
                    'test-project',
                    'test-phase',
                    'Objectives',
                    'Scope',
                    'Dependencies',
                    'Deliverables',
                    'draft',
                )

    @pytest.mark.asyncio
    async def test_check_constraint_on_loop_score(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.PHASE)
        await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            with pytest.raises(CheckViolationError):
                await conn.execute('UPDATE loop_states SET current_score = 150 WHERE id = $1', loop.id)

    @pytest.mark.asyncio
    async def test_check_constraint_on_loop_iteration(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.PHASE)
        await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            with pytest.raises(CheckViolationError):
                await conn.execute('UPDATE loop_states SET iteration = 0 WHERE id = $1', loop.id)


class TestDatabaseTransactions:
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, db_state_manager: PostgresStateManager) -> None:
        phase = Phase(
            phase_name='Test Phase',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            phase_status=PhaseStatus.DRAFT,
        )

        await db_state_manager.store_phase('test-project', phase)

        try:
            async with db_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        'UPDATE phases SET objectives = $1 WHERE plan_name = $2 AND phase_name = $3',
                        'Updated objectives',
                        'test-project',
                        'test-phase',
                    )
                    raise RuntimeError('Simulated error')
        except RuntimeError:
            pass

        retrieved_phase = await db_state_manager.get_phase('test-project', phase.phase_name)
        assert retrieved_phase.objectives == 'Objectives'
