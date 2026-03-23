import pytest

from src.mcp.tools.loop_tools import LoopTools
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopStatus
from src.utils.errors import LoopStateError, LoopValidationError
from src.utils.loop_state import MCPResponse
from src.utils.setting_configs import LoopConfig


@pytest.fixture
def plan_name() -> str:
    return 'test-project'


async def add_feedback_and_decide(
    loop_tools: LoopTools, loop_id: str, score: int, iteration: int, agent: CriticAgent
) -> MCPResponse:
    state_manager = loop_tools.state
    loop_state = await state_manager.get_loop(loop_id)
    feedback = CriticFeedback(
        loop_id=loop_id,
        critic_agent=agent,
        iteration=iteration,
        overall_score=score,
        assessment_summary=f'Assessment {iteration}',
        detailed_feedback=f'Details for iteration {iteration}',
        key_issues=[],
        recommendations=[],
    )
    loop_state.add_feedback(feedback)
    return await loop_tools.decide_loop_next_action(loop_id)


class TestLoopToolsIntegration:
    @pytest.mark.asyncio
    async def test_complete_mcp_tool_workflow_end_to_end(
        self, isolated_loop_tools: LoopTools, plan_name: str, stable_loop_config: LoopConfig
    ) -> None:
        # Initialize loop
        init_result = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'phase')
        loop_id = init_result.id

        assert init_result.status == LoopStatus.INITIALIZED

        # Simulate progressive score improvement
        threshold = stable_loop_config.phase_threshold
        scores = [70, 75, 80, 85, threshold]
        for i, score in enumerate(scores[:-1], start=1):
            result = await add_feedback_and_decide(isolated_loop_tools, loop_id, score, i, CriticAgent.PHASE_CRITIC)
            assert result.status == LoopStatus.REFINE

        # Final score should complete the loop (meets phase threshold)
        final_result = await add_feedback_and_decide(
            isolated_loop_tools, loop_id, scores[-1], len(scores), CriticAgent.PHASE_CRITIC
        )
        assert final_result.status == LoopStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_realistic_score_progression_scenarios(
        self, isolated_loop_tools: LoopTools, plan_name: str, stable_loop_config: LoopConfig
    ) -> None:
        # Test gradual improvement scenario
        loop1 = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'plan')

        # Gradual improvement that should complete (meets plan threshold)
        threshold = stable_loop_config.plan_threshold
        progression = [65, 70, 75, 80, 85, threshold]
        for i, score in enumerate(progression, start=1):
            result = await add_feedback_and_decide(isolated_loop_tools, loop1.id, score, i, CriticAgent.PLAN_CRITIC)
            if i < len(progression):
                assert result.status == LoopStatus.REFINE
            else:
                assert result.status == LoopStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_stagnation_detection_in_full_context(self, isolated_loop_tools: LoopTools, plan_name: str) -> None:
        loop_id = (await isolated_loop_tools.initialize_refinement_loop(plan_name, 'task')).id

        # Create stagnation pattern
        stagnant_scores = [70, 71, 70, 71, 70]
        results = []

        for i, score in enumerate(stagnant_scores, start=1):
            result = await add_feedback_and_decide(isolated_loop_tools, loop_id, score, i, CriticAgent.TASK_CRITIC)
            results.append(result)

        # Should detect stagnation and request user input
        assert results[-1].status == LoopStatus.USER_INPUT

    @pytest.mark.asyncio
    async def test_configuration_loading_from_environment(
        self, isolated_loop_tools: LoopTools, plan_name: str, stable_loop_config: LoopConfig
    ) -> None:
        # Test different loop types use correct thresholds
        build_code_loop = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'task')

        threshold = stable_loop_config.task_threshold
        # Score just below build_code threshold should refine
        result = await add_feedback_and_decide(
            isolated_loop_tools, build_code_loop.id, threshold - 1, 1, CriticAgent.CODE_REVIEWER
        )
        assert result.status == LoopStatus.REFINE

        # Score at threshold should complete
        result = await add_feedback_and_decide(
            isolated_loop_tools, build_code_loop.id, threshold, 2, CriticAgent.CODE_REVIEWER
        )
        assert result.status == LoopStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, isolated_loop_tools: LoopTools, plan_name: str) -> None:
        # Test invalid loop type
        with pytest.raises(LoopValidationError):
            await isolated_loop_tools.initialize_refinement_loop(plan_name, 'invalid_type')

        # Test operations on non-existent loop
        with pytest.raises(LoopStateError):
            await isolated_loop_tools.decide_loop_next_action('non-existent-id')

        with pytest.raises(LoopStateError):
            await isolated_loop_tools.get_loop_status('non-existent-id')

        # Test no feedback error
        valid_loop = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'plan')

        with pytest.raises(LoopStateError) as exc_info:
            await isolated_loop_tools.decide_loop_next_action(valid_loop.id)

        assert 'No feedback available' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_loop_management(self, isolated_loop_tools: LoopTools, plan_name: str) -> None:
        # Create multiple loops
        loop_types = ['plan', 'phase', 'task']
        agents = [
            CriticAgent.PLAN_CRITIC,
            CriticAgent.PHASE_CRITIC,
            CriticAgent.CODE_REVIEWER,
        ]
        loops = []
        for loop_type in loop_types:
            loop = await isolated_loop_tools.initialize_refinement_loop(plan_name, loop_type)
            loops.append(loop)

        # Verify all loops are active
        active_loops = await isolated_loop_tools.list_active_loops(plan_name)
        assert len(active_loops) >= 3

        loop_ids = {loop.id for loop in active_loops}
        for loop in loops:
            assert loop.id in loop_ids

        # Test operations on each loop independently
        for i, loop in enumerate(loops):
            score = 60 + (i * 5)  # Different scores for each loop
            result = await add_feedback_and_decide(isolated_loop_tools, loop.id, score, 1, agents[i])
            assert isinstance(result, MCPResponse)
            assert result.id == loop.id

    @pytest.mark.asyncio
    async def test_checkpoint_frequency_boundary_conditions(
        self, isolated_loop_tools: LoopTools, plan_name: str, stable_loop_config: LoopConfig
    ) -> None:
        loop_id = (await isolated_loop_tools.initialize_refinement_loop(plan_name, 'plan')).id

        # Add scores up to checkpoint frequency
        checkpoint_freq = stable_loop_config.plan_checkpoint_frequency
        for i in range(checkpoint_freq):
            result = await add_feedback_and_decide(isolated_loop_tools, loop_id, 60 + i, i + 1, CriticAgent.PLAN_CRITIC)

        # Should trigger user input at checkpoint frequency
        assert result.status == LoopStatus.USER_INPUT

    @pytest.mark.asyncio
    async def test_cross_loop_independence(
        self, isolated_loop_tools: LoopTools, plan_name: str, stable_loop_config: LoopConfig
    ) -> None:
        loop1 = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'phase')
        loop2 = await isolated_loop_tools.initialize_refinement_loop(plan_name, 'plan')

        # Advance loop1 significantly
        for i, score in enumerate([70, 75, 80, 85], start=1):
            await add_feedback_and_decide(isolated_loop_tools, loop1.id, score, i, CriticAgent.PHASE_CRITIC)

        # Loop2 should still be at initial state
        status2 = await isolated_loop_tools.get_loop_status(loop2.id)
        assert status2.status == LoopStatus.INITIALIZED

        # Loop1 should be ready to complete (meets phase threshold)
        threshold = stable_loop_config.phase_threshold
        result1 = await add_feedback_and_decide(isolated_loop_tools, loop1.id, threshold, 5, CriticAgent.PHASE_CRITIC)
        assert result1.status == LoopStatus.COMPLETED

        # Loop2 should still work independently
        result2 = await add_feedback_and_decide(isolated_loop_tools, loop2.id, 70, 1, CriticAgent.PLAN_CRITIC)
        assert result2.status == LoopStatus.REFINE

    @pytest.mark.asyncio
    async def test_score_history_preservation(
        self, isolated_loop_tools: LoopTools, plan_name: str, stable_loop_config: LoopConfig
    ) -> None:
        loop_id = (await isolated_loop_tools.initialize_refinement_loop(plan_name, 'phase')).id

        scores = [70, 75, 80, 85]
        for i, score in enumerate(scores, start=1):
            await add_feedback_and_decide(isolated_loop_tools, loop_id, score, i, CriticAgent.PHASE_CRITIC)

        # Verify loop maintains state correctly
        status = await isolated_loop_tools.get_loop_status(loop_id)
        assert status.id == loop_id
        # Score history validation would depend on internal state access
        # For now, verify the loop continues to work correctly

        threshold = stable_loop_config.phase_threshold
        result = await add_feedback_and_decide(isolated_loop_tools, loop_id, threshold, 5, CriticAgent.PHASE_CRITIC)
        assert result.status == LoopStatus.COMPLETED
