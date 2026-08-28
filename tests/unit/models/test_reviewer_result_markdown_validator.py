import pytest

from src.models.enums import CriticAgent
from src.models.feedback import REVIEWER_EXECUTION_REPORT_MARKER, ReviewerResult
from src.platform.template_helpers import (
    create_automated_quality_checker_agent_tools,
    create_backend_api_reviewer_agent_tools,
    create_code_quality_reviewer_agent_tools,
    create_coding_standards_reviewer_agent_tools,
    create_database_reviewer_agent_tools,
    create_design_conformance_reviewer_agent_tools,
    create_frontend_reviewer_agent_tools,
    create_infrastructure_reviewer_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
)
from src.platform.templates.agents import (
    generate_automated_quality_checker_template,
    generate_backend_api_reviewer_template,
    generate_code_quality_reviewer_template,
    generate_coding_standards_reviewer_template,
    generate_database_reviewer_template,
    generate_design_conformance_reviewer_template,
    generate_frontend_reviewer_template,
    generate_infrastructure_reviewer_template,
    generate_spec_alignment_reviewer_template,
)
from src.platform.tui_adapters import ClaudeCodeAdapter
from tests.support.reviewer_feedback_example import extract_reviewer_feedback_markdown_example

_adapter = ClaudeCodeAdapter()

# B18: every reviewer template's example markdown must pass the structural validator. Each
# entry pairs the generator with a plausible score for that reviewer's max_score, so the
# example can be run through real ReviewerResult construction, not just the validator function.
_REVIEWER_TEMPLATES = {
    'automated-quality-checker': (
        generate_automated_quality_checker_template(create_automated_quality_checker_agent_tools(_adapter)),
        50,
    ),
    'spec-alignment-reviewer': (
        generate_spec_alignment_reviewer_template(create_spec_alignment_reviewer_agent_tools(_adapter)),
        50,
    ),
    'design-conformance-reviewer': (
        generate_design_conformance_reviewer_template(create_design_conformance_reviewer_agent_tools(_adapter)),
        50,
    ),
    'frontend-reviewer': (generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter)), 25),
    'backend-api-reviewer': (
        generate_backend_api_reviewer_template(create_backend_api_reviewer_agent_tools(_adapter)),
        25,
    ),
    'database-reviewer': (
        generate_database_reviewer_template(create_database_reviewer_agent_tools(_adapter)),
        25,
    ),
    'infrastructure-reviewer': (
        generate_infrastructure_reviewer_template(create_infrastructure_reviewer_agent_tools(_adapter)),
        25,
    ),
    'coding-standards-reviewer': (
        generate_coding_standards_reviewer_template(create_coding_standards_reviewer_agent_tools(_adapter)),
        25,
    ),
    'code-quality-reviewer': (
        generate_code_quality_reviewer_template(create_code_quality_reviewer_agent_tools(_adapter)),
        25,
    ),
}


class TestEveryReviewerTemplateExamplePassesTheMarkdownValidator:
    @pytest.mark.parametrize('reviewer_name', sorted(_REVIEWER_TEMPLATES))
    def test_example_markdown_constructs_a_valid_reviewer_result(self, reviewer_name: str) -> None:
        template, max_score = _REVIEWER_TEMPLATES[reviewer_name]
        example = extract_reviewer_feedback_markdown_example(template)
        # Placeholder tokens ({{TOTAL}}, {{X}}/{{Y}}, etc.) aren't valid ints -- fill them so the
        # example parses as a real score without changing heading structure, which is all this
        # validator (and this test) cares about.
        example = example.replace('{{TOTAL}}', str(max_score))

        result = ReviewerResult(
            loop_id='loop',
            review_iteration=1,
            reviewer_name=CriticAgent(reviewer_name),
            feedback_markdown=example,
            score=max_score,
            max_score=max_score,
            blockers=[],
            findings=[],
        )

        assert REVIEWER_EXECUTION_REPORT_MARKER in result.feedback_markdown


class TestReviewerResultMarkdownValidator:
    def _make(self, feedback_markdown: str) -> ReviewerResult:
        return ReviewerResult(
            loop_id='loop',
            review_iteration=1,
            reviewer_name=CriticAgent.AUTOMATED_QUALITY_CHECKER,
            feedback_markdown=feedback_markdown,
            score=50,
            max_score=50,
            blockers=[],
            findings=[],
        )

    def test_minimal_markdown_with_no_execution_report_is_valid(self) -> None:
        # Existing tests across the suite construct ReviewerResult with bare markdown like this
        # for unrelated purposes (scoring math, blocker validation) -- the structural validator
        # must not require every ReviewerResult to carry the full reviewer boilerplate. That
        # requirement belongs to real reviewer templates (see the class above), not every
        # fixture in the codebase.
        result = self._make('### Automated Quality Check (Score: 50/50)')
        assert result.feedback_markdown == '### Automated Quality Check (Score: 50/50)'

    def test_rejects_an_h1_heading(self) -> None:
        # B17
        with pytest.raises(ValueError, match='must not contain an H1 heading'):
            self._make('# Top Level\n### Automated Quality Check (Score: 50/50)')

    def test_rejects_an_h2_heading(self) -> None:
        # B17
        with pytest.raises(ValueError, match='must not contain an H2 heading'):
            self._make('## Section\n### Automated Quality Check (Score: 50/50)')

    def test_rejects_a_second_h3_heading(self) -> None:
        # B17
        with pytest.raises(ValueError, match='at most one H3 heading'):
            self._make('### First (Score: 50/50)\n### Second (Score: 0/50)')

    def test_rejects_execution_report_marker_in_prose(self) -> None:
        with pytest.raises(ValueError, match='must appear only as its own H4 heading'):
            self._make(
                '### Automated Quality Check (Score: 50/50)\n'
                'The Reviewer Execution Report (Non-Actionable) was clean this run.'
            )

    def test_rejects_execution_report_marker_at_the_wrong_heading_level(self) -> None:
        with pytest.raises(ValueError, match='must appear only as its own H4 heading'):
            self._make(
                f'### Automated Quality Check (Score: 50/50)\n##### {REVIEWER_EXECUTION_REPORT_MARKER}'
            )

    def test_rejects_a_level_five_heading_after_the_execution_report(self) -> None:
        # B17
        with pytest.raises(ValueError, match='heading of level 5 or deeper'):
            self._make(
                f'### Automated Quality Check (Score: 50/50)\n'
                f'#### {REVIEWER_EXECUTION_REPORT_MARKER}\n'
                '- Run Status: clean\n'
                '##### Seam Review\n'
                '#### Key Issues\n'
            )

    def test_allows_a_level_five_heading_before_the_execution_report(self) -> None:
        result = self._make(
            '### Coding Standards Review (Score: 50/50)\n'
            '#### Assessment Results\n'
            '##### imports (Score: 10/10)\n'
            f'#### {REVIEWER_EXECUTION_REPORT_MARKER}\n'
            '- Run Status: clean\n'
            '#### Key Issues\n'
            '#### Recommendations\n'
        )
        assert '##### imports' in result.feedback_markdown

    def test_allows_the_proper_execution_report_heading(self) -> None:
        result = self._make(
            f'### Automated Quality Check (Score: 50/50)\n#### {REVIEWER_EXECUTION_REPORT_MARKER}\n'
            '- Run Status: clean\n#### Key Issues\n#### Recommendations\n'
        )
        assert REVIEWER_EXECUTION_REPORT_MARKER in result.feedback_markdown
