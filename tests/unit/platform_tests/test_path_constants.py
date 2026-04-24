"""Tests for PathComponent StrEnum and helper methods."""

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

    def test_tasks_dir_value(self) -> None:
        assert PathComponent.TASKS_DIR == 'tasks'


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
        assert result == '.respec-ai/plans/my-project/phases/phase-1.md'

    def test_build_phase_path_with_project_only(self) -> None:
        result = PathComponent.build_phase_path('my-project')
        assert result == '.respec-ai/plans/my-project/phases/*.md'

    def test_build_phase_path_with_no_names(self) -> None:
        result = PathComponent.build_phase_path()
        assert result == '.respec-ai/plans/*/phases/*.md'

    def test_build_phase_path_with_none_project(self) -> None:
        result = PathComponent.build_phase_path(None, 'phase-1')
        assert result == '.respec-ai/plans/*/phases/phase-1.md'

    def test_build_phase_path_with_none_phase(self) -> None:
        result = PathComponent.build_phase_path('my-project', None)
        assert result == '.respec-ai/plans/my-project/phases/*.md'


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


class TestBuildTaskPath:
    def test_build_task_path_with_all_names(self) -> None:
        result = PathComponent.build_task_path('my-project', 'phase-1', 'task-1')
        assert result == '.respec-ai/plans/my-project/phases/phase-1/tasks/task-1.md'

    def test_build_task_path_with_phase_only(self) -> None:
        result = PathComponent.build_task_path('my-project', 'phase-1')
        assert result == '.respec-ai/plans/my-project/phases/phase-1/tasks/*.md'

    def test_build_task_path_with_no_names(self) -> None:
        result = PathComponent.build_task_path()
        assert result == '.respec-ai/plans/*/phases/*/tasks/*.md'


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
