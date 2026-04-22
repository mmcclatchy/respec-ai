import pytest
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.feedback_tools_unified import UnifiedFeedbackTools
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def plan_name() -> str:
    return 'test-plan'


class TestUnifiedFeedbackToolsMemoryBoundaries:
    @pytest.mark.asyncio
    async def test_user_feedback_persists_via_state_manager_across_tool_instances(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(loop, plan_name)

        writer = UnifiedFeedbackTools(state)
        await writer.store_user_feedback(loop.id, 'user feedback 1')
        await writer.store_user_feedback(loop.id, 'user feedback 2')
        await writer.store_user_feedback(loop.id, 'user feedback 3')

        # New tool instance must read from manager-backed storage, not local caches.
        reader = UnifiedFeedbackTools(state)
        response = await reader.get_feedback(loop.id, count=1)

        assert 'No feedback available' not in response.message
        assert '## User Input 1' in response.message
        assert 'user feedback 1' in response.message
        assert '## User Input 3' in response.message
        assert 'user feedback 3' in response.message

    @pytest.mark.asyncio
    async def test_get_feedback_count_applies_only_to_critic_feedback(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(loop, plan_name)

        feedback1 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.PLAN_CRITIC,
            iteration=1,
            overall_score=70,
            assessment_summary='Assessment 1',
            detailed_feedback='Details 1',
            key_issues=[],
            recommendations=[],
        )
        feedback2 = CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.PLAN_CRITIC,
            iteration=2,
            overall_score=75,
            assessment_summary='Assessment 2',
            detailed_feedback='Details 2',
            key_issues=[],
            recommendations=[],
        )
        loop.add_feedback(feedback1)
        loop.add_feedback(feedback2)
        await state.save_loop(loop)

        tools = UnifiedFeedbackTools(state)
        await tools.store_user_feedback(loop.id, 'user feedback 1')
        await tools.store_user_feedback(loop.id, 'user feedback 2')

        response = await tools.get_feedback(loop.id, count=1)

        assert 'Assessment 2' in response.message
        assert 'Assessment 1' not in response.message
        assert 'user feedback 1' in response.message
        assert 'user feedback 2' in response.message

    @pytest.mark.asyncio
    async def test_analysis_upsert_and_retrieve_via_state_manager(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.ANALYST)
        await state.add_loop(loop, plan_name)

        tools = UnifiedFeedbackTools(state)
        await tools.store_current_analysis(loop.id, 'analysis v1')
        await tools.store_current_analysis(loop.id, 'analysis v2')

        result = await tools.get_previous_analysis(loop.id)
        assert 'analysis v2' in result.message
        assert 'analysis v1' not in result.message

    @pytest.mark.asyncio
    async def test_stale_loop_lookup_returns_resource_error(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=1)
        tools = UnifiedFeedbackTools(state)

        stale_loop = LoopState(loop_type=LoopType.PLAN)
        await state.add_loop(stale_loop, plan_name)
        await tools.store_user_feedback(stale_loop.id, 'stale feedback')
        await tools.store_current_analysis(stale_loop.id, 'stale analysis')

        # Adding a second loop evicts stale_loop from active state manager history.
        await state.add_loop(LoopState(loop_type=LoopType.PHASE), plan_name)

        with pytest.raises(ResourceError, match='Loop does not exist'):
            await tools.get_feedback(stale_loop.id, count=1)


class TestDeterministicReviewConsolidation:
    @pytest.mark.asyncio
    async def test_store_reviewer_result_and_consolidate_phase1(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='automated-quality-checker',
            feedback_markdown='### Automated Quality Check (Score: 45/50)',
            score=90,
            blockers=[],
            findings=[{'priority': 'P2', 'feedback': 'Minor lint issue in src/main.py:10'}],
        )
        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='spec-alignment-reviewer',
            feedback_markdown='### Spec Alignment (Score: 47/50)',
            score=94,
            blockers=[],
            findings=[{'priority': 'P1', 'feedback': 'Acceptance criterion AC-3 partially implemented'}],
        )
        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='code-quality-reviewer',
            feedback_markdown='### Code Quality (Adjustment: -1)',
            score=88,
            blockers=[],
            findings=[],
        )

        consolidate_response = await tools.consolidate_review_cycle(
            loop_id=loop.id,
            review_iteration=1,
            active_reviewers=[
                'automated-quality-checker',
                'spec-alignment-reviewer',
                'code-quality-reviewer',
            ],
        )

        assert consolidate_response.current_score > 0
        feedback = await tools.get_feedback(loop.id, count=1)
        assert 'Consolidated 3 reviewer result(s) for iteration 1.' in feedback.message
        assert '[Severity:P1]' in feedback.message
        assert '[Severity:P2]' in feedback.message

    @pytest.mark.asyncio
    async def test_consolidate_requires_all_active_reviewers(self, plan_name: str) -> None:
        state = InMemoryStateManager(max_history_size=10)
        loop = LoopState(loop_type=LoopType.TASK)
        await state.add_loop(loop, plan_name)
        tools = UnifiedFeedbackTools(state)

        await tools.store_reviewer_result(
            loop_id=loop.id,
            review_iteration=1,
            reviewer_name='coding-standards-reviewer',
            feedback_markdown='### Coding Standards Review (Adjustment: -2)',
            score=82,
            blockers=[],
            findings=[],
        )

        with pytest.raises(ToolError, match='missing reviewer submissions'):
            await tools.consolidate_review_cycle(
                loop_id=loop.id,
                review_iteration=1,
                active_reviewers=['coding-standards-reviewer', 'code-quality-reviewer'],
            )
