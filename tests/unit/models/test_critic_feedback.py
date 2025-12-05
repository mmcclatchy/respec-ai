from datetime import datetime

import pytest
from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback


class TestCriticFeedback:
    def test_critic_feedback_creation_with_all_fields(self) -> None:
        feedback = CriticFeedback(
            loop_id='test-loop-123',
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=3,
            overall_score=85,
            assessment_summary='Good technical specification with minor improvements needed',
            detailed_feedback='The specification covers all major requirements and provides clear implementation guidance. Architecture decisions are well-documented.',
            key_issues=['Missing error handling section', 'Authentication flow needs clarification'],
            recommendations=[
                'Add comprehensive error handling patterns',
                'Provide detailed authentication sequence diagrams',
            ],
        )

        assert feedback.loop_id == 'test-loop-123'
        assert feedback.critic_agent == CriticAgent.SPEC_CRITIC
        assert feedback.iteration == 3
        assert feedback.overall_score == 85
        assert feedback.assessment_summary == 'Good technical specification with minor improvements needed'
        assert (
            feedback.detailed_feedback
            == 'The specification covers all major requirements and provides clear implementation guidance. Architecture decisions are well-documented.'
        )
        assert feedback.key_issues == ['Missing error handling section', 'Authentication flow needs clarification']
        assert feedback.recommendations == [
            'Add comprehensive error handling patterns',
            'Provide detailed authentication sequence diagrams',
        ]
        assert isinstance(feedback.timestamp, datetime)

    def test_quality_score_property_returns_overall_score(self) -> None:
        feedback = CriticFeedback(
            loop_id='test-loop',
            critic_agent=CriticAgent.SPEC_CRITIC,
            iteration=1,
            overall_score=92,
            assessment_summary='Test assessment',
            detailed_feedback='Test detailed feedback',
            key_issues=[],
            recommendations=[],
        )

        # quality_score property should return the overall_score for compatibility
        assert feedback.quality_score == 92

    def test_overall_score_validation_ensures_valid_range(self) -> None:
        # Test score too high
        with pytest.raises(ValueError, match='Overall score must be between 0 and 100'):
            CriticFeedback(
                loop_id='test-loop',
                critic_agent=CriticAgent.SPEC_CRITIC,
                iteration=1,
                overall_score=150,  # Invalid: > 100
                assessment_summary='Test assessment',
                detailed_feedback='Test detailed feedback',
                key_issues=[],
                recommendations=[],
            )

        # Test score too low
        with pytest.raises(ValueError, match='Overall score must be between 0 and 100'):
            CriticFeedback(
                loop_id='test-loop',
                critic_agent=CriticAgent.SPEC_CRITIC,
                iteration=1,
                overall_score=-5,  # Invalid: < 0
                assessment_summary='Test assessment',
                detailed_feedback='Test detailed feedback',
                key_issues=[],
                recommendations=[],
            )

    def test_critic_feedback_with_empty_lists(self) -> None:
        feedback = CriticFeedback(
            loop_id='test-loop',
            critic_agent=CriticAgent.ANALYST_CRITIC,
            iteration=1,
            overall_score=75,
            assessment_summary='Test assessment',
            detailed_feedback='Test detailed feedback',
            key_issues=[],
            recommendations=[],
        )

        assert feedback.key_issues == []
        assert feedback.recommendations == []
        assert feedback.quality_score == 75

    def test_parse_markdown_creates_valid_feedback(self) -> None:
        markdown = """# Critic Feedback: SPEC-CRITIC

## Assessment Summary
- **Loop ID**: test-loop-789
- **Iteration**: 2
- **Overall Score**: 88
- **Assessment Summary**: Comprehensive specification with solid architecture and clear implementation path.

## Analysis

The specification demonstrates thorough understanding of requirements and provides detailed implementation guidance. Security considerations are well-addressed.

## Issues and Recommendations

### Key Issues

- Missing performance benchmarks
- API versioning strategy unclear

### Recommendations

- Add performance requirements section
- Define API versioning strategy
- Include monitoring and alerting specifications

## Metadata
- **Critic**: SPEC-CRITIC
- **Timestamp**: 2024-01-15T14:30:00Z
- **Status**: completed
"""

        feedback = CriticFeedback.parse_markdown(markdown)

        assert feedback.loop_id == 'test-loop-789'
        assert feedback.critic_agent == CriticAgent.SPEC_CRITIC
        assert feedback.iteration == 2
        assert feedback.overall_score == 88
        assert (
            feedback.assessment_summary
            == 'Comprehensive specification with solid architecture and clear implementation path.'
        )
        assert 'Security considerations are well-addressed' in feedback.detailed_feedback
        assert len(feedback.key_issues) == 2
        assert 'Missing performance benchmarks' in feedback.key_issues
        assert 'API versioning strategy unclear' in feedback.key_issues
        assert len(feedback.recommendations) == 3
        assert 'Add performance requirements section' in feedback.recommendations

    def test_parse_markdown_with_score_fraction_format(self) -> None:
        markdown = """# Critic Feedback: ROADMAP-CRITIC

## Assessment Summary
- **Loop ID**: test-loop-roadmap
- **Iteration**: 2
- **Overall Score**: 42/100
- **Assessment Summary**: Roadmap needs significant improvements in phase scoping and dependencies.

## Analysis

The roadmap provides a foundation but requires refinement in several critical areas including phase boundaries and dependency mapping.

## Issues and Recommendations

### Key Issues

- Phase scoping too broad in Phase 1
- Missing dependency documentation

### Recommendations

- Break Phase 1 into smaller deliverables
- Add explicit dependency tree

## Metadata
- **Critic**: ROADMAP-CRITIC
- **Timestamp**: 2024-01-15T14:30:00Z
- **Status**: completed
"""

        feedback = CriticFeedback.parse_markdown(markdown)

        assert feedback.loop_id == 'test-loop-roadmap'
        assert feedback.critic_agent == CriticAgent.ROADMAP_CRITIC
        assert feedback.iteration == 2
        assert feedback.overall_score == 42
        assert (
            feedback.assessment_summary == 'Roadmap needs significant improvements in phase scoping and dependencies.'
        )
        assert 'requires refinement in several critical areas' in feedback.detailed_feedback
        assert len(feedback.key_issues) == 2
        assert 'Phase scoping too broad in Phase 1' in feedback.key_issues
        assert len(feedback.recommendations) == 2
        assert 'Break Phase 1 into smaller deliverables' in feedback.recommendations

    def test_build_markdown_creates_valid_template(self) -> None:
        feedback = CriticFeedback(
            loop_id='test-loop-456',
            critic_agent=CriticAgent.ANALYST_CRITIC,
            iteration=1,
            overall_score=78,
            assessment_summary='Good analysis with room for improvement',
            detailed_feedback='The analysis covers key aspects but could be more comprehensive in certain areas.',
            key_issues=['Missing data validation', 'Insufficient error handling'],
            recommendations=['Add comprehensive data validation', 'Implement proper error handling patterns'],
        )

        markdown = feedback.build_markdown()

        assert '# Critic Feedback: ANALYST-CRITIC' in markdown
        assert '## Assessment Summary' in markdown
        assert '- **Loop ID**: test-loop-456' in markdown
        assert '- **Overall Score**: 78' in markdown
        assert '- **Assessment Summary**: Good analysis with room for improvement' in markdown
        assert '## Analysis' in markdown
        assert '## Issues and Recommendations' in markdown
        assert '### Key Issues' in markdown
        assert '- Missing data validation' in markdown
        assert '### Recommendations' in markdown
        assert '- Add comprehensive data validation' in markdown

    def test_round_trip_parse_and_build_markdown(self) -> None:
        original_feedback = CriticFeedback(
            loop_id='round-trip-test',
            critic_agent=CriticAgent.BUILD_CRITIC,
            iteration=3,
            overall_score=91,
            assessment_summary='Excellent build implementation',
            detailed_feedback='The build process is well-structured and follows best practices.',
            key_issues=['Minor optimization opportunity'],
            recommendations=['Consider parallel build steps'],
        )

        # Build markdown, then parse it back
        markdown = original_feedback.build_markdown()
        parsed_feedback = CriticFeedback.parse_markdown(markdown)

        # Should match original (except timestamp)
        assert parsed_feedback.loop_id == original_feedback.loop_id
        assert parsed_feedback.critic_agent == original_feedback.critic_agent
        assert parsed_feedback.iteration == original_feedback.iteration
        assert parsed_feedback.overall_score == original_feedback.overall_score
        assert parsed_feedback.assessment_summary == original_feedback.assessment_summary
        assert parsed_feedback.key_issues == original_feedback.key_issues
        assert parsed_feedback.recommendations == original_feedback.recommendations

    def test_parse_markdown_with_unknown_critic_defaults_to_analyst(self) -> None:
        markdown = """# Critic Feedback: UNKNOWN

## Assessment Summary
- **Loop ID**: test-loop-123
- **Iteration**: 1
- **Overall Score**: 85
- **Assessment Summary**: Test feedback

## Analysis

Test analysis content.

## Issues and Recommendations

### Key Issues

- Test issue

### Recommendations

- Test recommendation

## Metadata
- **Critic**: UNKNOWN
- **Timestamp**: 2024-01-15T14:30:00Z
- **Status**: completed
"""

        feedback = CriticFeedback.parse_markdown(markdown)

        # Should default to ANALYST_CRITIC for unknown types
        assert feedback.critic_agent == CriticAgent.ANALYST_CRITIC
        assert feedback.loop_id == 'test-loop-123'
