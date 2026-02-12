from src.models.enums import StepMode
from src.platform.reviewer_mapping import MODE_TO_REVIEWER, resolve_active_reviewers


class TestResolveActiveReviewers:
    def test_empty_modes_returns_core_plus_consolidator(self) -> None:
        result = resolve_active_reviewers(set())
        assert result == ['automated-quality-checker', 'spec-alignment-reviewer', 'review-consolidator']

    def test_implementation_mode_returns_core_only(self) -> None:
        result = resolve_active_reviewers({StepMode.IMPLEMENTATION})
        assert result == ['automated-quality-checker', 'spec-alignment-reviewer', 'review-consolidator']

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

    def test_all_specialist_modes_activate_all_specialists(self) -> None:
        all_specialist_modes = {StepMode.FRONTEND, StepMode.API, StepMode.DATABASE, StepMode.INFRASTRUCTURE}
        result = resolve_active_reviewers(all_specialist_modes)
        assert len(result) == 7  # 2 core + 4 specialists + consolidator

    def test_passthrough_modes_only_core(self) -> None:
        result = resolve_active_reviewers({StepMode.INTEGRATION, StepMode.TEST})
        assert result == ['automated-quality-checker', 'spec-alignment-reviewer', 'review-consolidator']

    def test_consolidator_always_last(self) -> None:
        result = resolve_active_reviewers({StepMode.FRONTEND, StepMode.DATABASE})
        assert result[-1] == 'review-consolidator'

    def test_core_reviewers_always_first(self) -> None:
        result = resolve_active_reviewers({StepMode.INFRASTRUCTURE})
        assert result[0] == 'automated-quality-checker'
        assert result[1] == 'spec-alignment-reviewer'


class TestModeToReviewerMapping:
    def test_mapping_covers_all_specialist_modes(self) -> None:
        specialist_modes = {StepMode.FRONTEND, StepMode.API, StepMode.DATABASE, StepMode.INFRASTRUCTURE}
        assert set(MODE_TO_REVIEWER.keys()) == specialist_modes

    def test_mapping_values_are_reviewer_slugs(self) -> None:
        for reviewer in MODE_TO_REVIEWER.values():
            assert '-reviewer' in reviewer or '-api-reviewer' in reviewer
