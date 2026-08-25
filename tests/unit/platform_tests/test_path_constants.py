"""Tests for PathComponent StrEnum and helper methods."""

from pathlib import Path

from src.platform.path_constants import PathComponent


class TestPathComponentValues:
    def test_respec_ai_dir_value(self) -> None:
        assert PathComponent.RESPEC_AI_DIR == '.respec-ai'

    def test_plans_dir_value(self) -> None:
        assert PathComponent.PLANS_DIR == 'plans'

    def test_phases_dir_value(self) -> None:
        assert PathComponent.PHASES_DIR == 'phases'

    def test_plan_file_value(self) -> None:
        assert PathComponent.PROJECT_PLAN_FILE == 'plan.md'

    def test_completion_file_value(self) -> None:
        assert PathComponent.COMPLETION_FILE == 'project_completion.md'

class TestBuildPlanPath:
    def test_build_plan_path_with_plan_name(self) -> None:
        result = PathComponent.build_plan_path('my-project')
        assert result == '.respec-ai/plans/my-project/plan.md'

    def test_build_plan_path_without_plan_name(self) -> None:
        result = PathComponent.build_plan_path()
        assert result == '.respec-ai/plans/*/plan.md'

    def test_build_plan_path_with_none(self) -> None:
        result = PathComponent.build_plan_path(None)
        assert result == '.respec-ai/plans/*/plan.md'


class TestBuildPhasePath:
    def test_build_phase_path_with_both_names(self) -> None:
        result = PathComponent.build_phase_path('my-project', 'phase-1')
        assert result == '.respec-ai/plans/my-project/phases/phase-1/phase.md'

    def test_build_phase_path_with_project_only(self) -> None:
        result = PathComponent.build_phase_path('my-project')
        assert result == '.respec-ai/plans/my-project/phases/*/phase.md'

    def test_build_phase_path_with_no_names(self) -> None:
        result = PathComponent.build_phase_path()
        assert result == '.respec-ai/plans/*/phases/*/phase.md'

    def test_build_phase_path_with_none_project(self) -> None:
        result = PathComponent.build_phase_path(None, 'phase-1')
        assert result == '.respec-ai/plans/*/phases/phase-1/phase.md'

    def test_build_phase_path_with_none_phase(self) -> None:
        result = PathComponent.build_phase_path('my-project', None)
        assert result == '.respec-ai/plans/my-project/phases/*/phase.md'

    def test_build_phase_path_resolves_a_real_bundle_layout_directory(self, tmp_path: Path) -> None:
        bundle = tmp_path / '.respec-ai' / 'plans' / 'my-project' / 'phases' / 'phase-1'
        bundle.mkdir(parents=True)
        (bundle / 'phase.md').write_text('content', encoding='utf-8')

        relative = PathComponent.build_phase_path('my-project', 'phase-1')
        matches = list(tmp_path.glob(relative))

        assert matches == [bundle / 'phase.md']


class TestBuildResearchPath:
    def test_build_research_path_with_all_names(self) -> None:
        result = PathComponent.build_research_path('my-project', 'phase-1', 'neo4j-survey')
        assert result == '.respec-ai/plans/my-project/phases/phase-1/research/neo4j-survey.md'

    def test_build_research_path_with_phase_only(self) -> None:
        result = PathComponent.build_research_path('my-project', 'phase-1')
        assert result == '.respec-ai/plans/my-project/phases/phase-1/research/*.md'

    def test_build_research_path_with_no_names(self) -> None:
        result = PathComponent.build_research_path()
        assert result == '.respec-ai/plans/*/phases/*/research/*.md'


class TestBuildCompletionPath:
    def test_build_completion_path_with_plan_name(self) -> None:
        result = PathComponent.build_completion_path('my-project')
        assert result == '.respec-ai/plans/my-project/project_completion.md'

    def test_build_completion_path_without_plan_name(self) -> None:
        result = PathComponent.build_completion_path()
        assert result == '.respec-ai/plans/*/project_completion.md'

    def test_build_completion_path_with_none(self) -> None:
        result = PathComponent.build_completion_path(None)
        assert result == '.respec-ai/plans/*/project_completion.md'


class TestPathComponentIsString:
    def test_enum_members_are_strings(self) -> None:
        assert isinstance(PathComponent.RESPEC_AI_DIR, str)
        assert isinstance(PathComponent.PLANS_DIR, str)
        assert isinstance(PathComponent.PHASES_DIR, str)
        assert isinstance(PathComponent.PROJECT_PLAN_FILE, str)
        assert isinstance(PathComponent.COMPLETION_FILE, str)

    def test_can_use_in_f_strings(self) -> None:
        result = f'{PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}'
        assert result == '.respec-ai/plans'

    def test_can_concatenate_with_strings(self) -> None:
        result = PathComponent.RESPEC_AI_DIR + '/' + PathComponent.PLANS_DIR
        assert result == '.respec-ai/plans'
