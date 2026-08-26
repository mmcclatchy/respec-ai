import itertools
import re
from unittest.mock import patch

from src.mcp.tools.feedback_tools_unified import UnifiedFeedbackTools
from src.models.enums import CriticAgent, StepMode
from src.models.feedback import ReviewerResult
from src.platform.reviewer_mapping import MODE_TO_REVIEWER, resolve_active_reviewers
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
from src.platform.tui_adapters.claude_code import ClaudeCodeAdapter


CODING_STANDARDS_PATCH = 'src.platform.reviewer_mapping.has_coding_standards_file'

REVIEWER_AGENT_TOOLS_FACTORIES = {
    'automated-quality-checker': create_automated_quality_checker_agent_tools,
    'spec-alignment-reviewer': create_spec_alignment_reviewer_agent_tools,
    'code-quality-reviewer': create_code_quality_reviewer_agent_tools,
    'design-conformance-reviewer': create_design_conformance_reviewer_agent_tools,
    'frontend-reviewer': create_frontend_reviewer_agent_tools,
    'backend-api-reviewer': create_backend_api_reviewer_agent_tools,
    'database-reviewer': create_database_reviewer_agent_tools,
    'infrastructure-reviewer': create_infrastructure_reviewer_agent_tools,
    'coding-standards-reviewer': create_coding_standards_reviewer_agent_tools,
}


def _template_max_score(reviewer_name: str) -> int:
    agent_tools = REVIEWER_AGENT_TOOLS_FACTORIES[reviewer_name](ClaudeCodeAdapter())
    store_reviewer_result_call: str = getattr(agent_tools, 'store_reviewer_result')
    match = re.search(r'max_score=(\d+)', store_reviewer_result_call)
    assert match, f'{reviewer_name} agent template does not declare a literal max_score'
    return int(match.group(1))


def _every_resolvable_roster() -> list[list[str]]:
    step_mode_subsets = [
        combo for size in range(len(StepMode) + 1) for combo in itertools.combinations(StepMode, size)
    ]
    rosters = []
    for step_modes in step_mode_subsets:
        for has_skeleton_index in (True, False):
            for has_coding_standards in (True, False):
                with patch(CODING_STANDARDS_PATCH, return_value=has_coding_standards):
                    rosters.append(resolve_active_reviewers(set(step_modes), has_skeleton_index=has_skeleton_index))
    return rosters


class TestResolveActiveReviewers:
    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_empty_modes_returns_core(self, _mock: object) -> None:
        result = resolve_active_reviewers(set())
        assert result == [
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'code-quality-reviewer',
        ]

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_implementation_mode_returns_core_only(self, _mock: object) -> None:
        result = resolve_active_reviewers({StepMode.IMPLEMENTATION})
        assert result == [
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'code-quality-reviewer',
        ]

    def test_frontend_mode_activates_frontend_reviewer(self) -> None:
        result = resolve_active_reviewers({StepMode.FRONTEND})
        assert 'frontend-reviewer' in result
        assert 'automated-quality-checker' in result
        assert 'spec-alignment-reviewer' in result
        assert 'review-consolidator' not in result

    def test_api_mode_activates_backend_api_reviewer(self) -> None:
        result = resolve_active_reviewers({StepMode.API})
        assert 'backend-api-reviewer' in result

    def test_database_mode_activates_database_reviewer(self) -> None:
        result = resolve_active_reviewers({StepMode.DATABASE})
        assert 'database-reviewer' in result

    def test_infrastructure_mode_activates_infrastructure_reviewer(self) -> None:
        result = resolve_active_reviewers({StepMode.INFRASTRUCTURE})
        assert 'infrastructure-reviewer' in result

    def test_multiple_modes_activate_multiple_reviewers(self) -> None:
        result = resolve_active_reviewers({StepMode.FRONTEND, StepMode.DATABASE, StepMode.API})
        assert 'frontend-reviewer' in result
        assert 'backend-api-reviewer' in result
        assert 'database-reviewer' in result
        assert 'automated-quality-checker' in result
        assert 'spec-alignment-reviewer' in result
        assert 'review-consolidator' not in result

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_all_specialist_modes_activate_all_specialists(self, _mock: object) -> None:
        all_specialist_modes = {StepMode.FRONTEND, StepMode.API, StepMode.DATABASE, StepMode.INFRASTRUCTURE}
        result = resolve_active_reviewers(all_specialist_modes)
        assert len(result) == 7  # 3 core + 4 specialists

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_passthrough_modes_only_core(self, _mock: object) -> None:
        result = resolve_active_reviewers({StepMode.INTEGRATION, StepMode.TEST})
        assert result == [
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'code-quality-reviewer',
        ]

    def test_last_specialist_order_is_stable(self) -> None:
        result = resolve_active_reviewers({StepMode.FRONTEND, StepMode.DATABASE})
        assert result[-1] == 'database-reviewer'

    def test_core_reviewers_always_first(self) -> None:
        result = resolve_active_reviewers({StepMode.INFRASTRUCTURE})
        assert result[0] == 'automated-quality-checker'
        assert result[1] == 'spec-alignment-reviewer'

    @patch(CODING_STANDARDS_PATCH, return_value=True)
    def test_coding_standards_reviewer_included_when_file_exists(self, _mock: object) -> None:
        result = resolve_active_reviewers(set())
        assert 'coding-standards-reviewer' in result
        assert result[-1] == 'coding-standards-reviewer'

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_coding_standards_reviewer_excluded_when_no_file(self, _mock: object) -> None:
        result = resolve_active_reviewers(set())
        assert 'coding-standards-reviewer' not in result

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_design_conformance_reviewer_inactive_when_phase_has_no_skeleton_index(self, _mock: object) -> None:
        result = resolve_active_reviewers(set(), has_skeleton_index=False)
        assert 'design-conformance-reviewer' not in result

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_design_conformance_reviewer_active_when_phase_has_a_skeleton_index(self, _mock: object) -> None:
        result = resolve_active_reviewers(set(), has_skeleton_index=True)
        assert 'design-conformance-reviewer' in result


class TestModeToReviewerMapping:
    def test_mapping_covers_all_specialist_modes(self) -> None:
        specialist_modes = {StepMode.FRONTEND, StepMode.API, StepMode.DATABASE, StepMode.INFRASTRUCTURE}
        assert set(MODE_TO_REVIEWER.keys()) == specialist_modes

    def test_mapping_values_are_reviewer_slugs(self) -> None:
        for reviewer in MODE_TO_REVIEWER.values():
            assert '-reviewer' in reviewer or '-api-reviewer' in reviewer


class TestEveryRosterableReviewerIsRegistered:
    """B1-B3: no reviewer resolve_active_reviewers() can return may be unregistered.

    Sweeps every step-mode/skeleton-index/coding-standards combination `resolve_active_reviewers()`
    can produce, so a future reviewer added to the roster without matching registration fails here
    instead of at runtime (the class of bug behind F1).
    """

    def test_every_rostered_reviewer_name_parses_to_a_critic_agent(self) -> None:
        for roster in _every_resolvable_roster():
            for reviewer_name in roster:
                assert CriticAgent(reviewer_name) is not None

    def test_every_rostered_reviewer_max_score_matches_its_agent_template(self) -> None:
        tools = UnifiedFeedbackTools(state=None)  # type: ignore[arg-type]
        checked: set[str] = set()
        for roster in _every_resolvable_roster():
            for reviewer_name in roster:
                if reviewer_name in checked:
                    continue
                checked.add(reviewer_name)
                configured_max_score = tools._reviewer_max_scores.get(CriticAgent(reviewer_name))
                assert configured_max_score is not None, f'{reviewer_name} missing from _reviewer_max_scores'
                assert configured_max_score == _template_max_score(reviewer_name)

    def test_every_phase1_roster_resolves_a_weight_without_raising(self) -> None:
        tools = UnifiedFeedbackTools(state=None)  # type: ignore[arg-type]
        for roster in _every_resolvable_roster():
            phase1_roster = [name for name in roster if name != 'coding-standards-reviewer']
            if not phase1_roster:
                continue
            active_results = [
                ReviewerResult(
                    loop_id='loop',
                    review_iteration=1,
                    reviewer_name=CriticAgent(name),
                    feedback_markdown='### result',
                    score=1,
                    max_score=1,
                )
                for name in phase1_roster
            ]
            tools._phase1_weights_for_results(active_results)
