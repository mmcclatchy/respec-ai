import pytest

from services.mcp.tools.loop_tools import LoopTools, loop_tools
from services.models.enums import CriticAgent
from services.models.feedback import CriticFeedback
from services.utils.enums import LoopStatus, LoopType
from services.utils.errors import LoopStateError, LoopValidationError
from services.utils.loop_state import LoopState, MCPResponse
from services.utils.state_manager import InMemoryStateManager


@pytest.fixture
def project_name() -> str:
    return 'test-project'


class TestLoopToolsMCP:
    def test_decide_loop_next_action_complete_decision(self, project_name: str) -> None:
        # Initialize a build_code loop (threshold 95%)
        init_result = loop_tools.initialize_refinement_loop(project_name, 'build_code')
        loop_id = init_result.id

        # High score should complete
        result = loop_tools.decide_loop_next_action(loop_id, 96)

        assert isinstance(result, MCPResponse)
        assert result.status == LoopStatus.COMPLETED

    def test_decide_loop_next_action_refine_decision(self, project_name: str) -> None:
        # Initialize a spec loop (threshold 85%)
        init_result = loop_tools.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        # Score below threshold should refine
        result = loop_tools.decide_loop_next_action(loop_id, 70)

        assert isinstance(result, MCPResponse)
        assert result.status == LoopStatus.REFINE

    def test_decide_loop_next_action_user_input_decision(self, project_name: str) -> None:
        # Initialize a plan loop
        init_result = loop_tools.initialize_refinement_loop(project_name, 'plan')
        loop_id = init_result.id

        # Add multiple low improvement scores to trigger stagnation
        loop_tools.decide_loop_next_action(loop_id, 60)
        loop_tools.decide_loop_next_action(loop_id, 61)
        loop_tools.decide_loop_next_action(loop_id, 62)

        # Should detect stagnation and request user input
        result = loop_tools.decide_loop_next_action(loop_id, 63)

        assert isinstance(result, MCPResponse)
        assert result.status == LoopStatus.USER_INPUT

    def test_decide_loop_next_action_invalid_loop_id(self) -> None:
        with pytest.raises(LoopStateError):
            loop_tools.decide_loop_next_action('nonexistent-loop-id', 80)

    def test_decide_loop_next_action_score_validation(self, project_name: str) -> None:
        init_result = loop_tools.initialize_refinement_loop(project_name, 'plan')
        loop_id = init_result.id

        # Test valid score ranges
        result = loop_tools.decide_loop_next_action(loop_id, 0)
        assert isinstance(result, MCPResponse)

        result = loop_tools.decide_loop_next_action(loop_id, 100)
        assert isinstance(result, MCPResponse)

        # Test invalid score ranges
        with pytest.raises(LoopValidationError):
            loop_tools.decide_loop_next_action(loop_id, -1)

        with pytest.raises(LoopValidationError):
            loop_tools.decide_loop_next_action(loop_id, 101)

    def test_decide_loop_next_action_checkpoint_frequency(self, project_name: str) -> None:
        # Initialize a plan loop to test checkpoint frequency
        init_result = loop_tools.initialize_refinement_loop(project_name, 'plan')
        loop_id = init_result.id

        # Add scores until we hit checkpoint frequency (5 for plan loops)
        for score in [60, 61, 62, 63, 64]:
            result = loop_tools.decide_loop_next_action(loop_id, score)

        # Should request user input at checkpoint frequency
        assert result.status == LoopStatus.USER_INPUT

    def test_initialize_refinement_loop_integration(self, project_name: str) -> None:
        result = loop_tools.initialize_refinement_loop(project_name, 'build_plan')

        assert isinstance(result, MCPResponse)
        assert result.status == LoopStatus.INITIALIZED
        assert len(result.id) > 0

    def test_get_loop_status_integration(self, project_name: str) -> None:
        init_result = loop_tools.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        status = loop_tools.get_loop_status(loop_id)

        assert isinstance(status, MCPResponse)
        assert status.id == loop_id
        assert status.status == LoopStatus.INITIALIZED

    def test_list_active_loops_integration(self, project_name: str) -> None:
        # Create multiple loops
        loop1 = loop_tools.initialize_refinement_loop(project_name, 'plan')
        loop2 = loop_tools.initialize_refinement_loop(project_name, 'spec')

        active_loops = loop_tools.list_active_loops(project_name)

        assert isinstance(active_loops, list)
        assert len(active_loops) >= 2

        loop_ids = [loop.id for loop in active_loops]
        assert loop1.id in loop_ids
        assert loop2.id in loop_ids


class TestLoopFeedbackIntegration:
    @pytest.fixture
    def state_manager(self) -> InMemoryStateManager:
        return InMemoryStateManager(max_history_size=5)

    @pytest.fixture
    def loop_tools_instance(self, state_manager: InMemoryStateManager) -> LoopTools:
        return LoopTools(state_manager)

    @pytest.fixture
    def sample_loop(self, state_manager: InMemoryStateManager, project_name: str) -> LoopState:
        loop_state = LoopState(loop_type=LoopType.SPEC)
        state_manager.add_loop(loop_state, project_name)
        return loop_state

    def test_get_loop_feedback_summary_no_feedback(self, loop_tools_instance: LoopTools, project_name: str) -> None:
        # Initialize a loop
        init_result = loop_tools_instance.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        # Get feedback summary for loop with no feedback
        result = loop_tools_instance.get_loop_feedback_summary(loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert 'No feedback available' in result.message
        assert 'ready for first assessment' in result.message

    def test_get_loop_feedback_summary_with_feedback(
        self, loop_tools_instance: LoopTools, state_manager: InMemoryStateManager, project_name: str
    ) -> None:
        # Initialize a loop
        init_result = loop_tools_instance.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        # Add some feedback to the loop
        loop_state = state_manager.get_loop(loop_id)

        feedback1 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=70,
            assessment_summary='Initial assessment needs improvement',
            detailed_feedback='The specification lacks detail in several areas.',
            key_issues=['Missing security requirements'],
            recommendations=['Add security section'],
        )
        loop_state.add_feedback(feedback1)

        feedback2 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=2,
            overall_score=80,
            assessment_summary='Improved specification with good coverage',
            detailed_feedback='The specification now covers most requirements.',
            key_issues=['Minor formatting issues'],
            recommendations=['Improve formatting'],
        )
        loop_state.add_feedback(feedback2)

        # Get feedback summary
        result = loop_tools_instance.get_loop_feedback_summary(loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert '2 total assessments' in result.message
        assert 'current score 80' in result.message
        assert 'trend: improving' in result.message
        assert 'Initial assessment' in result.message
        assert 'Improved specification' in result.message

    def test_get_loop_improvement_analysis_insufficient_feedback(
        self, loop_tools_instance: LoopTools, project_name: str
    ) -> None:
        # Initialize a loop
        init_result = loop_tools_instance.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        # Try to get improvement analysis with no feedback
        result = loop_tools_instance.get_loop_improvement_analysis(loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert 'Insufficient feedback history' in result.message
        assert 'need at least 2 assessments' in result.message

    def test_get_loop_improvement_analysis_with_history(
        self, loop_tools_instance: LoopTools, state_manager: InMemoryStateManager, project_name: str
    ) -> None:
        # Initialize a loop
        init_result = loop_tools_instance.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        # Add feedback with improvement
        loop_state = state_manager.get_loop(loop_id)

        feedback1 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=60,
            assessment_summary='Initial poor assessment',
            detailed_feedback='Many issues identified.',
            key_issues=['Missing architecture', 'No security details'],
            recommendations=['Add architecture section', 'Add security'],
        )
        loop_state.add_feedback(feedback1)

        feedback2 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=2,
            overall_score=75,
            assessment_summary='Improved but still needs work',
            detailed_feedback='Architecture added but security still missing.',
            key_issues=['Different issue this time'],
            recommendations=['Add comprehensive security section'],
        )
        loop_state.add_feedback(feedback2)

        feedback3 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=3,
            overall_score=85,
            assessment_summary='Good specification with minor issues',
            detailed_feedback='Security added, minor issues remain.',
            key_issues=['Minor formatting'],
            recommendations=['Fix formatting'],
        )
        loop_state.add_feedback(feedback3)

        # Get improvement analysis
        result = loop_tools_instance.get_loop_improvement_analysis(loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert 'improving trend' in result.message
        assert 'avg: +12.5 points' in result.message
        assert 'last change: +10 points' in result.message
        assert 'No recurring issues' in result.message  # No issues appear twice

    def test_get_loop_improvement_analysis_with_recurring_issues(
        self, loop_tools_instance: LoopTools, state_manager: InMemoryStateManager, project_name: str
    ) -> None:
        # Initialize a loop
        init_result = loop_tools_instance.initialize_refinement_loop(project_name, 'spec')
        loop_id = init_result.id

        # Add feedback with recurring issues
        loop_state = state_manager.get_loop(loop_id)

        feedback1 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=60,
            assessment_summary='Poor assessment',
            detailed_feedback='Many issues.',
            key_issues=['Missing security', 'Poor formatting'],
            recommendations=['Add security', 'Fix formatting'],
        )
        loop_state.add_feedback(feedback1)

        feedback2 = CriticFeedback(
            loop_id=loop_id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=2,
            overall_score=65,
            assessment_summary='Minor improvement',
            detailed_feedback='Some issues remain.',
            key_issues=['Missing security', 'Unclear architecture'],
            recommendations=['Add security details', 'Clarify architecture'],
        )
        loop_state.add_feedback(feedback2)

        # Get improvement analysis
        result = loop_tools_instance.get_loop_improvement_analysis(loop_id)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert 'improving trend' in result.message
        assert 'Recurring issues: Missing security' in result.message

    def test_feedback_integration_nonexistent_loop(self, loop_tools_instance: LoopTools) -> None:
        # Test error handling for nonexistent loop
        with pytest.raises(LoopStateError):
            loop_tools_instance.get_loop_feedback_summary('nonexistent-loop')

        with pytest.raises(LoopStateError):
            loop_tools_instance.get_loop_improvement_analysis('nonexistent-loop')
