import pytest

from services.mcp.tools.loop_tools import loop_tools
from services.utils.enums import LoopStatus
from services.utils.errors import LoopStateError, LoopValidationError
from services.utils.loop_state import MCPResponse


@pytest.fixture
def project_name() -> str:
    return 'test-project'


class TestLoopToolsIntegration:
    def test_complete_mcp_tool_workflow_end_to_end(self, project_name: str) -> None:
        # Initialize loop
        init_result = loop_tools.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        assert init_result.status == LoopStatus.INITIALIZED

        # Simulate progressive score improvement
        scores = [70, 75, 80, 82, 85]
        for score in scores[:-1]:
            result = loop_tools.decide_loop_next_action(loop_id, score)
            assert result.status == LoopStatus.REFINE

        # Final score should complete the loop (spec threshold is 85)
        final_result = loop_tools.decide_loop_next_action(loop_id, scores[-1])
        assert final_result.status == LoopStatus.COMPLETED

    def test_realistic_score_progression_scenarios(self, project_name: str) -> None:
        # Test gradual improvement scenario
        loop1 = loop_tools.initialize_refinement_loop(project_name, 'plan')

        # Gradual improvement that should complete (plan threshold is 85)
        progression = [65, 70, 75, 80, 82, 85]
        for i, score in enumerate(progression):
            result = loop_tools.decide_loop_next_action(loop1.id, score)
            if i < len(progression) - 1:
                assert result.status == LoopStatus.REFINE
            else:
                assert result.status == LoopStatus.COMPLETED

    def test_stagnation_detection_in_full_context(self, project_name: str) -> None:
        loop_id = loop_tools.initialize_refinement_loop(project_name, 'build_plan').id

        # Create stagnation pattern
        stagnant_scores = [70, 71, 70, 71, 70]
        results = []

        for score in stagnant_scores:
            result = loop_tools.decide_loop_next_action(loop_id, score)
            results.append(result)

        # Should detect stagnation and request user input
        assert results[-1].status == LoopStatus.USER_INPUT

    def test_configuration_loading_from_environment(self, project_name: str) -> None:
        # Test different loop types use correct thresholds
        build_code_loop = loop_tools.initialize_refinement_loop(project_name, 'build_code')

        # Score just below build_code threshold (95%) should refine
        result = loop_tools.decide_loop_next_action(build_code_loop.id, 94)
        assert result.status == LoopStatus.REFINE

        # Score at threshold should complete
        result = loop_tools.decide_loop_next_action(build_code_loop.id, 95)
        assert result.status == LoopStatus.COMPLETED

    def test_error_recovery_scenarios(self, project_name: str) -> None:
        # Test invalid loop type
        with pytest.raises(LoopValidationError):
            loop_tools.initialize_refinement_loop(project_name, 'invalid_type')

        # Test operations on non-existent loop
        with pytest.raises(LoopStateError):
            loop_tools.decide_loop_next_action('non-existent-id', 80)

        with pytest.raises(LoopStateError):
            loop_tools.get_loop_status('non-existent-id')

        # Test score validation
        valid_loop = loop_tools.initialize_refinement_loop(project_name, 'plan')

        with pytest.raises(LoopValidationError):
            loop_tools.decide_loop_next_action(valid_loop.id, -1)

        with pytest.raises(LoopValidationError):
            loop_tools.decide_loop_next_action(valid_loop.id, 101)

    def test_concurrent_loop_management(self, project_name: str) -> None:
        # Create multiple loops
        loops = []
        for loop_type in ['plan', 'spec', 'build_plan', 'build_code']:
            loop = loop_tools.initialize_refinement_loop(project_name, loop_type)
            loops.append(loop)

        # Verify all loops are active
        active_loops = loop_tools.list_active_loops(project_name)
        assert len(active_loops) >= 4

        loop_ids = {loop.id for loop in active_loops}
        for loop in loops:
            assert loop.id in loop_ids

        # Test operations on each loop independently
        for i, loop in enumerate(loops):
            score = 60 + (i * 5)  # Different scores for each loop
            result = loop_tools.decide_loop_next_action(loop.id, score)
            assert isinstance(result, MCPResponse)
            assert result.id == loop.id

    def test_checkpoint_frequency_boundary_conditions(self, project_name: str) -> None:
        loop_id = loop_tools.initialize_refinement_loop(project_name, 'plan').id

        # Add scores up to checkpoint frequency
        for i in range(5):  # Plan loops have checkpoint_frequency = 5
            result = loop_tools.decide_loop_next_action(loop_id, 60 + i)

        # Should trigger user input at checkpoint frequency
        assert result.status == LoopStatus.USER_INPUT

    def test_cross_loop_independence(self, project_name: str) -> None:
        loop1 = loop_tools.initialize_refinement_loop(project_name, 'spec')
        loop2 = loop_tools.initialize_refinement_loop(project_name, 'plan')

        # Advance loop1 significantly
        for score in [70, 75, 80, 85]:
            loop_tools.decide_loop_next_action(loop1.id, score)

        # Loop2 should still be at initial state
        status2 = loop_tools.get_loop_status(loop2.id)
        assert status2.status == LoopStatus.INITIALIZED

        # Loop1 should be ready to complete
        result1 = loop_tools.decide_loop_next_action(loop1.id, 88)
        assert result1.status == LoopStatus.COMPLETED

        # Loop2 should still work independently
        result2 = loop_tools.decide_loop_next_action(loop2.id, 70)
        assert result2.status == LoopStatus.REFINE

    def test_score_history_preservation(self, project_name: str) -> None:
        loop_id = loop_tools.initialize_refinement_loop(project_name, 'spec').id

        scores = [65, 70, 75, 80]
        for score in scores:
            loop_tools.decide_loop_next_action(loop_id, score)

        # Verify loop maintains state correctly
        status = loop_tools.get_loop_status(loop_id)
        assert status.id == loop_id
        # Score history validation would depend on internal state access
        # For now, verify the loop continues to work correctly

        result = loop_tools.decide_loop_next_action(loop_id, 85)
        assert result.status == LoopStatus.COMPLETED
