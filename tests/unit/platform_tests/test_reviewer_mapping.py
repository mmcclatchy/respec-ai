from unittest.mock import patch

from src.models.enums import StepMode
from src.platform.reviewer_mapping import MODE_TO_REVIEWER, resolve_active_reviewers


CODING_STANDARDS_PATCH = 'src.platform.reviewer_mapping.has_coding_standards_file'


class TestResolveActiveReviewers:
    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_empty_modes_returns_core_plus_consolidator(self, _mock: object) -> None:
        result = resolve_active_reviewers(set())
        assert result == [
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'code-quality-reviewer',
            'review-consolidator',
        ]

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_implementation_mode_returns_core_only(self, _mock: object) -> None:
        result = resolve_active_reviewers({StepMode.IMPLEMENTATION})
        assert result == [
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'code-quality-reviewer',
            'review-consolidator',
        ]

    def test_frontend_mode_activates_frontend_reviewer(self) -> None:
        result = resolve_active_reviewers({StepMode.FRONTEND})
        assert 'frontend-reviewer' in result
        assert 'automated-quality-checker' in result
        assert 'spec-alignment-reviewer' in result
        assert 'review-consolidator' in result

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
        assert 'review-consolidator' in result

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_all_specialist_modes_activate_all_specialists(self, _mock: object) -> None:
        all_specialist_modes = {StepMode.FRONTEND, StepMode.API, StepMode.DATABASE, StepMode.INFRASTRUCTURE}
        result = resolve_active_reviewers(all_specialist_modes)
        assert len(result) == 8  # 3 core + 4 specialists + consolidator

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_passthrough_modes_only_core(self, _mock: object) -> None:
        result = resolve_active_reviewers({StepMode.INTEGRATION, StepMode.TEST})
        assert result == [
            'automated-quality-checker',
            'spec-alignment-reviewer',
            'code-quality-reviewer',
            'review-consolidator',
        ]

    def test_consolidator_always_last(self) -> None:
        result = resolve_active_reviewers({StepMode.FRONTEND, StepMode.DATABASE})
        assert result[-1] == 'review-consolidator'

    def test_core_reviewers_always_first(self) -> None:
        result = resolve_active_reviewers({StepMode.INFRASTRUCTURE})
        assert result[0] == 'automated-quality-checker'
        assert result[1] == 'spec-alignment-reviewer'

    @patch(CODING_STANDARDS_PATCH, return_value=True)
    def test_coding_standards_reviewer_included_when_file_exists(self, _mock: object) -> None:
        result = resolve_active_reviewers(set())
        assert 'coding-standards-reviewer' in result
        assert result[-1] == 'review-consolidator'
        assert result.index('coding-standards-reviewer') < result.index('review-consolidator')

    @patch(CODING_STANDARDS_PATCH, return_value=False)
    def test_coding_standards_reviewer_excluded_when_no_file(self, _mock: object) -> None:
        result = resolve_active_reviewers(set())
        assert 'coding-standards-reviewer' not in result


class TestModeToReviewerMapping:
    def test_mapping_covers_all_specialist_modes(self) -> None:
        specialist_modes = {StepMode.FRONTEND, StepMode.API, StepMode.DATABASE, StepMode.INFRASTRUCTURE}
        assert set(MODE_TO_REVIEWER.keys()) == specialist_modes

    def test_mapping_values_are_reviewer_slugs(self) -> None:
        for reviewer in MODE_TO_REVIEWER.values():
            assert '-reviewer' in reviewer or '-api-reviewer' in reviewer
