from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState


class TestEnhancedLoopState:
    def test_loop_state_has_feedback_history_field(self) -> None:
        loop_state = LoopState(loop_type=LoopType.SPEC)

        assert hasattr(loop_state, 'feedback_history')
        assert loop_state.feedback_history == []

    def test_add_feedback_stores_feedback_and_updates_score(self) -> None:
        loop_state = LoopState(loop_type=LoopType.SPEC)

        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=80,
            assessment_summary='Good specification with room for improvement',
            detailed_feedback='The specification covers requirements but needs security details.',
            key_issues=['Missing security requirements'],
            recommendations=['Add security details'],
        )

        loop_state.add_feedback(feedback)

        assert len(loop_state.feedback_history) == 1
        assert loop_state.feedback_history[0] == feedback
        assert loop_state.current_score == 80

    def test_get_recent_feedback_returns_limited_feedback(self) -> None:
        loop_state = LoopState(loop_type=LoopType.SPEC)

        # Add 7 feedback items
        for i in range(7):
            feedback = CriticFeedback(
                loop_id=loop_state.id,
                critic_agent=CriticAgent.SPEC_CRITIC,
                iteration=i + 1,
                overall_score=70,
                assessment_summary=f'Assessment {i}',
                detailed_feedback=f'Detailed analysis for iteration {i}',
                key_issues=[],
                recommendations=[],
            )
            loop_state.add_feedback(feedback)

        # Should return only the last 5 by default
        recent_feedback = loop_state.get_recent_feedback()
        assert len(recent_feedback) == 5
        assert recent_feedback[-1].iteration == 7  # Most recent
        assert recent_feedback[0].iteration == 3  # 5th from end

        # Should return only the last 3 when specified
        recent_feedback_3 = loop_state.get_recent_feedback(count=3)
        assert len(recent_feedback_3) == 3
        assert recent_feedback_3[-1].iteration == 7  # Most recent
        assert recent_feedback_3[0].iteration == 5  # 3rd from end

    def test_get_recent_feedback_with_empty_history_returns_empty_list(self) -> None:
        loop_state = LoopState(loop_type=LoopType.SPEC)

        recent_feedback = loop_state.get_recent_feedback()
        assert recent_feedback == []

    def test_updated_at_field_is_automatically_managed(self) -> None:
        loop_state = LoopState(loop_type=LoopType.SPEC)

        assert hasattr(loop_state, 'updated_at')
        initial_updated_at = loop_state.updated_at

        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=70,
            assessment_summary='Test assessment',
            detailed_feedback='Test detailed feedback for timestamp verification',
            key_issues=[],
            recommendations=[],
        )

        loop_state.add_feedback(feedback)

        assert loop_state.updated_at > initial_updated_at

    def test_existing_loop_state_functionality_remains_intact(self) -> None:
        loop_state = LoopState(loop_type=LoopType.SPEC)

        # Test existing functionality still works
        assert loop_state.is_first_iteration()
        assert loop_state.iteration == 1

        loop_state.increment_iteration()
        assert loop_state.iteration == 2
        assert not loop_state.is_first_iteration()

        loop_state.add_score(85)
        assert loop_state.current_score == 85
        assert loop_state.score_history == [85]

        # Test decision logic still works
        response = loop_state.decide_next_loop_action()
        assert response.id == loop_state.id
