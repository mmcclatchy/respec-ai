import pytest
from asyncpg.exceptions import CheckViolationError, UniqueViolationError

from src.models.enums import CriticAgent, PhaseStatus
from src.models.feedback import CriticFeedback
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
