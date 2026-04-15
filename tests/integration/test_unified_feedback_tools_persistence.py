import pytest

from src.mcp.tools.feedback_tools_unified import UnifiedFeedbackTools
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState
from src.utils.state_manager import InMemoryStateManager


@pytest.mark.asyncio
async def test_unified_feedback_persists_across_tool_instances() -> None:
    state = InMemoryStateManager(max_history_size=10)
    loop = LoopState(loop_type=LoopType.ANALYST)
    await state.add_loop(loop, 'test-plan')

    loop.add_feedback(
        CriticFeedback(
            loop_id=loop.id,
            critic_agent=CriticAgent.ANALYST_CRITIC,
            iteration=1,
            overall_score=81,
            assessment_summary='Analyst assessment',
            detailed_feedback='Good trajectory',
            key_issues=[],
            recommendations=[],
        )
    )
    await state.save_loop(loop)

    writer = UnifiedFeedbackTools(state)
    await writer.store_user_feedback(loop.id, 'user feedback A')
    await writer.store_current_analysis(loop.id, 'analysis A')

    reader = UnifiedFeedbackTools(state)
    feedback = await reader.get_feedback(loop.id, count=1)
    analysis = await reader.get_previous_analysis(loop.id)

    assert 'Analyst assessment' in feedback.message
    assert 'user feedback A' in feedback.message
    assert 'analysis A' in analysis.message
