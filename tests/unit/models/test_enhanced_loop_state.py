from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.utils.enums import LoopStatus, LoopType
from src.utils.loop_state import LoopState


class TestEnhancedLoopState:
    def test_loop_state_has_feedback_history_field(self) -> None:
        loop_state = LoopState(loop_type=LoopType.PHASE)

        assert hasattr(loop_state, 'feedback_history')
        assert loop_state.feedback_history == []

    def test_add_feedback_stores_feedback_and_updates_score(self) -> None:
        loop_state = LoopState(loop_type=LoopType.PHASE)

        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.PHASE_CRITIC,
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
        loop_state = LoopState(loop_type=LoopType.PHASE)

        # Add 7 feedback items
        for i in range(7):
            feedback = CriticFeedback(
                loop_id=loop_state.id,
                critic_agent=CriticAgent.PHASE_CRITIC,
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
        loop_state = LoopState(loop_type=LoopType.PHASE)

        recent_feedback = loop_state.get_recent_feedback()
        assert recent_feedback == []

    def test_updated_at_field_is_automatically_managed(self) -> None:
        loop_state = LoopState(loop_type=LoopType.PHASE)

        assert hasattr(loop_state, 'updated_at')
        initial_updated_at = loop_state.updated_at

        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.PHASE_CRITIC,
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
        loop_state = LoopState(loop_type=LoopType.PHASE)

        assert loop_state.iteration == 1

        loop_state.add_score(85)
        assert loop_state.current_score == 85
        assert loop_state.score_history == [85]

        response = loop_state.decide_next_loop_action()
        assert response.id == loop_state.id

    def test_review_consolidator_blocker_prevents_completion(self) -> None:
        loop_state = LoopState(loop_type=LoopType.TASK)
        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.REVIEW_CONSOLIDATOR,
            iteration=1,
            overall_score=96,
            assessment_summary='Strong score with blocker',
            detailed_feedback='Found critical issue [BLOCKING] in changed file.',
            key_issues=['Critical blocker remains'],
            recommendations=['Fix blocker'],
        )
        loop_state.add_feedback(feedback)

        response = loop_state.decide_next_loop_action()
        assert response.status == LoopStatus.REFINE

    def test_coding_standards_blocker_prevents_completion(self) -> None:
        loop_state = LoopState(loop_type=LoopType.TASK)
        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.CODING_STANDARDS_REVIEWER,
            iteration=1,
            overall_score=97,
            assessment_summary='Standards review raised a P0',
            detailed_feedback='Violations include [Severity:P0] secret handling issue.',
            key_issues=['P0 standards issue'],
            recommendations=['Resolve P0 issue'],
        )
        loop_state.add_feedback(feedback)

        response = loop_state.decide_next_loop_action()
        assert response.status == LoopStatus.REFINE

    def test_high_score_without_blockers_still_completes(self) -> None:
        loop_state = LoopState(loop_type=LoopType.TASK)
        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.REVIEW_CONSOLIDATOR,
            iteration=1,
            overall_score=96,
            assessment_summary='High quality and no blockers',
            detailed_feedback='No blocking findings remain.',
            key_issues=[],
            recommendations=[],
        )
        loop_state.add_feedback(feedback)

        response = loop_state.decide_next_loop_action()
        assert response.status == LoopStatus.COMPLETED

    def test_blocker_with_checkpoint_returns_user_input(self) -> None:
        loop_state = LoopState(loop_type=LoopType.TASK)
        for i in range(1, 6):
            feedback = CriticFeedback(
                loop_id=loop_state.id,
                critic_agent=CriticAgent.REVIEW_CONSOLIDATOR,
                iteration=i,
                overall_score=98,
                assessment_summary=f'Iteration {i} with blocker',
                detailed_feedback='Blocking condition persists: [BLOCKING]',
                key_issues=['Blocking issue still active'],
                recommendations=['Resolve blocker'],
            )
            loop_state.add_feedback(feedback)

        response = loop_state.decide_next_loop_action()
        assert response.status == LoopStatus.USER_INPUT

    def test_non_review_critic_uses_existing_completion_behavior(self) -> None:
        loop_state = LoopState(loop_type=LoopType.TASK)
        feedback = CriticFeedback(
            loop_id=loop_state.id,
            critic_agent=CriticAgent.PHASE_CRITIC,
            iteration=1,
            overall_score=97,
            assessment_summary='High score from non-review critic',
            detailed_feedback='Contains [BLOCKING] marker but from non-gated critic.',
            key_issues=[],
            recommendations=[],
        )
        loop_state.add_feedback(feedback)

        response = loop_state.decide_next_loop_action()
        assert response.status == LoopStatus.COMPLETED
