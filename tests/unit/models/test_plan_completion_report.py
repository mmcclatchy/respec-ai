import pytest
from src.models.plan_completion_report import (
    AnalystLoopStatus,
    PlanCompletionReport,
    PlanCompletionStatus,
    UserDecision,
)


class TestPlanCompletionReport:
    def test_default_initialization(self) -> None:
        report = PlanCompletionReport()

        assert report.report_title == 'Strategic Plan Output'
        assert report.final_plan_score == '0'
        assert report.plan_completion_status == PlanCompletionStatus.USER_ACCEPTED
        assert report.user_decision == UserDecision.ACCEPT_PLAN
        assert report.final_analyst_score == '0'
        assert report.analyst_completion_status == AnalystLoopStatus.COMPLETED
        assert report.analyst_loop_result == AnalystLoopStatus.COMPLETED

    def test_custom_initialization(self) -> None:
        report = PlanCompletionReport(
            report_title='Custom Report',
            final_plan_score='85',
            user_decision=UserDecision.REFINE_PLAN,
            final_analyst_score='92',
            strategic_plan_document='# Custom Plan\nContent here',
            structured_objectives='Custom objectives',
            analyst_loop_id='test-loop-123',
            completion_timestamp='2025-01-15T10:30:00Z',
        )

        assert report.report_title == 'Custom Report'
        assert report.final_plan_score == '85'
        assert report.user_decision == UserDecision.REFINE_PLAN
        assert report.final_analyst_score == '92'
        assert report.strategic_plan_document == '# Custom Plan\nContent here'
        assert report.structured_objectives == 'Custom objectives'
        assert report.analyst_loop_id == 'test-loop-123'
        assert report.completion_timestamp == '2025-01-15T10:30:00Z'

    def test_build_markdown_default(self) -> None:
        report = PlanCompletionReport()
        markdown = report.build_markdown()

        assert '# Strategic Plan Output' in markdown
        assert '## Plan Quality' in markdown
        assert '### Final Plan Score\n0%' in markdown
        assert '### Plan Completion Status\nUser-accepted (human-driven decision)' in markdown
        assert '### User Decision\naccept_plan' in markdown
        assert '## Analyst Validation' in markdown
        assert '### Final Analyst Score\n0%' in markdown
        assert '## Strategic Plan Document' in markdown
        assert '## Structured Objectives' in markdown
        assert '## Next Steps' in markdown
        assert '## Metadata' in markdown

    def test_build_markdown_custom(self) -> None:
        report = PlanCompletionReport(
            report_title='Test Completion Report',
            final_plan_score='88',
            final_analyst_score='91',
            strategic_plan_document='# Test Plan\nDetailed content here',
            structured_objectives='1. Objective A\n2. Objective B',
            analyst_loop_id='loop-456',
            completion_timestamp='2025-01-15T15:45:00Z',
        )

        markdown = report.build_markdown()

        assert '# Test Completion Report' in markdown
        assert '### Final Plan Score\n88%' in markdown
        assert '### Final Analyst Score\n91%' in markdown
        assert '# Test Plan\nDetailed content here' in markdown
        assert '1. Objective A\n2. Objective B' in markdown
        assert 'loop-456' in markdown
        assert '2025-01-15T15:45:00Z' in markdown

    def test_header_field_mapping(self) -> None:
        mapping = PlanCompletionReport.HEADER_FIELD_MAPPING

        # Test key fields are mapped
        assert 'final_plan_score' in mapping
        assert 'final_analyst_score' in mapping
        assert 'strategic_plan_document' in mapping
        assert 'structured_objectives' in mapping
        assert 'analyst_loop_id' in mapping
        assert 'completion_timestamp' in mapping

        # Test hierarchical structure
        assert mapping['final_plan_score'] == ('Plan Quality', 'Final Plan Score')
        assert mapping['final_analyst_score'] == ('Analyst Validation', 'Final Analyst Score')
        assert mapping['strategic_plan_document'] == ('Strategic Plan Document',)
        assert mapping['analyst_loop_id'] == ('Metadata', 'Analyst Loop ID')

    def test_title_pattern_and_field(self) -> None:
        assert PlanCompletionReport.TITLE_PATTERN == '# Strategic Plan Output'
        assert PlanCompletionReport.TITLE_FIELD == 'report_title'

    def test_status_enums(self) -> None:
        assert PlanCompletionStatus.USER_ACCEPTED == 'User-accepted (human-driven decision)'
        assert UserDecision.CONTINUE_CONVERSATION == 'continue_conversation'
        assert UserDecision.REFINE_PLAN == 'refine_plan'
        assert UserDecision.ACCEPT_PLAN == 'accept_plan'
        assert AnalystLoopStatus.REFINE == 'refine'
        assert AnalystLoopStatus.USER_INPUT == 'user_input'
        assert AnalystLoopStatus.COMPLETED == 'completed'

    def test_template_variable_placeholders(self) -> None:
        report = PlanCompletionReport(
            final_plan_score='${QUALITY_SCORE}',
            user_decision='${USER_DECISION}',
            final_analyst_score='${ANALYST_SCORE}',
            strategic_plan_document='${CURRENT_PLAN}',
            structured_objectives='${STRUCTURED_OBJECTIVES}',
            analyst_loop_id='${ANALYST_LOOP_ID}',
        )

        markdown = report.build_markdown()

        # Verify placeholders are preserved in output
        assert '${QUALITY_SCORE}%' in markdown
        assert '${USER_DECISION}' in markdown
        assert '${ANALYST_SCORE}%' in markdown
        assert '${CURRENT_PLAN}' in markdown
        assert '${STRUCTURED_OBJECTIVES}' in markdown
        assert '${ANALYST_LOOP_ID}' in markdown

    def test_markdown_structure_completeness(self) -> None:
        report = PlanCompletionReport()
        markdown = report.build_markdown()

        expected_sections = [
            '# Strategic Plan Output',
            '## Plan Quality',
            '### Final Plan Score',
            '### Plan Completion Status',
            '### User Decision',
            '## Analyst Validation',
            '### Final Analyst Score',
            '### Analyst Completion Status',
            '### Analyst Loop Result',
            '## Strategic Plan Document',
            '## Structured Objectives',
            '## Next Steps',
            '## Metadata',
            '### Analyst Loop ID',
            '### Timestamp',
        ]

        for section in expected_sections:
            assert section in markdown, f'Missing section: {section}'

    def test_validation_with_invalid_types(self) -> None:
        # Invalid score values should now raise validation errors
        with pytest.raises(ValueError, match='Score must be a valid integer or template variable'):
            PlanCompletionReport(final_plan_score='not_a_number', final_analyst_score='also_not_a_number')

        # But valid scores should still work
        report = PlanCompletionReport(final_plan_score='85', final_analyst_score='92')

        assert report.final_plan_score == '85'
        assert report.final_analyst_score == '92'

    def test_empty_string_fields(self) -> None:
        report = PlanCompletionReport(
            strategic_plan_document='', structured_objectives='', analyst_loop_id='', completion_timestamp=''
        )

        markdown = report.build_markdown()

        # Should generate markdown even with empty fields
        assert '# Strategic Plan Output' in markdown
        assert '## Strategic Plan Document\n\n' in markdown
        assert '## Structured Objectives\n\n' in markdown

    def test_score_validation(self) -> None:
        # Valid scores should work
        report = PlanCompletionReport(final_plan_score='75', final_analyst_score='88')
        assert report.final_plan_score == '75'
        assert report.final_analyst_score == '88'

        # Template variables should work
        report = PlanCompletionReport(final_plan_score='${SCORE}', final_analyst_score='${ANALYST_SCORE}')
        assert report.final_plan_score == '${SCORE}'
        assert report.final_analyst_score == '${ANALYST_SCORE}'

        # Edge case values should work
        report = PlanCompletionReport(final_plan_score='0', final_analyst_score='100')
        assert report.final_plan_score == '0'
        assert report.final_analyst_score == '100'

        # Invalid scores should raise errors
        with pytest.raises(ValueError, match='Score must be between 0 and 100'):
            PlanCompletionReport(final_plan_score='150')

        with pytest.raises(ValueError, match='Score must be between 0 and 100'):
            PlanCompletionReport(final_analyst_score='-10')

    def test_user_decision_validation(self) -> None:
        # Valid decisions should work
        report = PlanCompletionReport(user_decision=UserDecision.ACCEPT_PLAN)
        assert report.user_decision == UserDecision.ACCEPT_PLAN

        # Template variables should work
        report = PlanCompletionReport(user_decision='${USER_DECISION}')
        assert report.user_decision == '${USER_DECISION}'

        # Invalid decisions should raise errors
        with pytest.raises(ValueError, match='User decision must be one of'):
            PlanCompletionReport(user_decision='invalid_decision')

    def test_analyst_status_validation(self) -> None:
        # Valid statuses should work
        report = PlanCompletionReport(analyst_completion_status=AnalystLoopStatus.COMPLETED)
        assert report.analyst_completion_status == AnalystLoopStatus.COMPLETED

        # Template variables should work
        report = PlanCompletionReport(analyst_loop_result='${ANALYST_STATUS}')
        assert report.analyst_loop_result == '${ANALYST_STATUS}'

        # Invalid statuses should raise errors
        with pytest.raises(ValueError, match='Analyst status must be one of'):
            PlanCompletionReport(analyst_completion_status='invalid_status')
