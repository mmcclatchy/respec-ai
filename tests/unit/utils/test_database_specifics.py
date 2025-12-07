import pytest

from src.models.enums import SpecStatus
from src.models.feedback import CriticFeedback
from src.models.spec import TechnicalSpec
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState
from src.utils.state_manager import PostgresStateManager


from src.utils.database_pool import db_pool
from src.models.enums import CriticAgent
from asyncpg.exceptions import UniqueViolationError
from asyncpg.exceptions import CheckViolationError


class TestDatabaseCascadeDeletes:
    @pytest.mark.asyncio
    async def test_cascade_delete_on_loop_history(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.SPEC)
        await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            count_before = await conn.fetchval('SELECT COUNT(*) FROM loop_history WHERE loop_id = $1', loop.id)
            assert count_before == 1

        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM loop_states WHERE id = $1', loop.id)

        async with db_pool.acquire() as conn:
            count_after = await conn.fetchval('SELECT COUNT(*) FROM loop_history WHERE loop_id = $1', loop.id)
            assert count_after == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_on_objective_feedback(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.SPEC)
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
    async def test_cascade_delete_on_loop_to_spec_mappings(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.SPEC)
        await db_state_manager.add_loop(loop, 'test-project')

        spec = TechnicalSpec(
            phase_name='Test Spec',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            spec_status=SpecStatus.DRAFT,
        )
        await db_state_manager.store_spec('test-project', spec)
        await db_state_manager.link_loop_to_spec(loop.id, 'test-project', spec.phase_name)

        async with db_pool.acquire() as conn:
            count_before = await conn.fetchval('SELECT COUNT(*) FROM loop_to_spec_mappings WHERE loop_id = $1', loop.id)
            assert count_before == 1

        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM loop_states WHERE id = $1', loop.id)

        async with db_pool.acquire() as conn:
            count_after = await conn.fetchval('SELECT COUNT(*) FROM loop_to_spec_mappings WHERE loop_id = $1', loop.id)
            assert count_after == 0


class TestDatabaseJSONBSerialization:
    @pytest.mark.asyncio
    async def test_critic_feedback_jsonb_roundtrip(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.SPEC)
        feedback1 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=85,
            assessment_summary='Good progress',
            detailed_feedback='Well structured with clear objectives but missing some details',
            key_issues=['Missing details'],
            recommendations=['Add more context'],
        )
        feedback2 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.SPEC_CRITIC,
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
    async def test_spec_additional_sections_jsonb_roundtrip(self, db_state_manager: PostgresStateManager) -> None:
        spec = TechnicalSpec(
            phase_name='Test Spec',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            spec_status=SpecStatus.DRAFT,
            additional_sections={'custom_field': 'custom value', 'notes': 'note1, note2'},
        )

        await db_state_manager.store_spec('test-project', spec)
        retrieved_spec = await db_state_manager.get_spec('test-project', spec.phase_name)

        assert retrieved_spec.additional_sections == {'custom_field': 'custom value', 'notes': 'note1, note2'}
        assert retrieved_spec.additional_sections['custom_field'] == 'custom value'
        assert retrieved_spec.additional_sections['notes'] == 'note1, note2'


class TestDatabaseConstraints:
    @pytest.mark.asyncio
    async def test_unique_constraint_on_project_spec_name(self, db_state_manager: PostgresStateManager) -> None:
        spec = TechnicalSpec(
            phase_name='Test Spec',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            spec_status=SpecStatus.DRAFT,
        )

        await db_state_manager.store_spec('test-project', spec)

        async with db_pool.acquire() as conn:
            with pytest.raises(UniqueViolationError):
                await conn.execute(
                    """
                    INSERT INTO technical_specs (
                        id, project_name, spec_name, phase_name, objectives, scope,
                        dependencies, deliverables, spec_status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    'testid01',
                    'test-project',
                    'test-spec',
                    'Test Spec',
                    'Objectives',
                    'Scope',
                    'Dependencies',
                    'Deliverables',
                    'draft',
                )

    @pytest.mark.asyncio
    async def test_check_constraint_on_loop_score(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.SPEC)
        await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            with pytest.raises(CheckViolationError):
                await conn.execute('UPDATE loop_states SET current_score = 150 WHERE id = $1', loop.id)

    @pytest.mark.asyncio
    async def test_check_constraint_on_loop_iteration(self, db_state_manager: PostgresStateManager) -> None:
        loop = LoopState(loop_type=LoopType.SPEC)
        await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            with pytest.raises(CheckViolationError):
                await conn.execute('UPDATE loop_states SET iteration = 0 WHERE id = $1', loop.id)


class TestDatabaseTransactions:
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, db_state_manager: PostgresStateManager) -> None:
        spec = TechnicalSpec(
            phase_name='Test Spec',
            objectives='Objectives',
            scope='Scope',
            dependencies='Dependencies',
            deliverables='Deliverables',
            spec_status=SpecStatus.DRAFT,
        )

        await db_state_manager.store_spec('test-project', spec)

        try:
            async with db_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        'UPDATE technical_specs SET objectives = $1 WHERE project_name = $2 AND spec_name = $3',
                        'Updated objectives',
                        'test-project',
                        'test-spec',
                    )
                    raise RuntimeError('Simulated error')
        except RuntimeError:
            pass

        retrieved_spec = await db_state_manager.get_spec('test-project', spec.phase_name)
        assert retrieved_spec.objectives == 'Objectives'


class TestDatabaseBoundedQueue:
    @pytest.mark.asyncio
    async def test_bounded_queue_enforcement(self, db_state_manager: PostgresStateManager) -> None:
        loops = [LoopState(loop_type=LoopType.PLAN) for _ in range(5)]

        for loop in loops:
            await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM loop_history')
            assert count == 3

    @pytest.mark.asyncio
    async def test_bounded_queue_keeps_latest_entries(self, db_state_manager: PostgresStateManager) -> None:
        loops = [LoopState(loop_type=LoopType.PLAN) for _ in range(5)]

        for loop in loops:
            await db_state_manager.add_loop(loop, 'test-project')

        async with db_pool.acquire() as conn:
            loop_ids = await conn.fetch('SELECT loop_id FROM loop_history ORDER BY sequence_number ASC')
            loop_ids_list = [row['loop_id'] for row in loop_ids]

        assert len(loop_ids_list) == 3
        assert loop_ids_list[0] == loops[2].id
        assert loop_ids_list[1] == loops[3].id
        assert loop_ids_list[2] == loops[4].id
