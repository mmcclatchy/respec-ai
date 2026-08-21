"""Path constants for respec-ai file system organization."""

from enum import StrEnum


class PathComponent(StrEnum):
    RESPEC_AI_DIR = '.respec-ai'
    PLANS_DIR = 'plans'
    PHASES_DIR = 'phases'
    TASKS_DIR = 'tasks'
    RESEARCH_DIR = 'research'
    PROJECT_PLAN_FILE = 'plan.md'
    PHASE_FILE = 'phase.md'
    COMPLETION_FILE = 'project_completion.md'

    @classmethod
    def build_plan_path(cls, plan_name: str | None = None) -> str:
        if plan_name:
            return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{plan_name}/{cls.PROJECT_PLAN_FILE}'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/*/{cls.PROJECT_PLAN_FILE}'

    @classmethod
    def build_phase_path(cls, plan_name: str | None = None, phase_name: str | None = None) -> str:
        proj = plan_name or '*'
        phase = phase_name or '*'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{proj}/{cls.PHASES_DIR}/{phase}/{cls.PHASE_FILE}'

    @classmethod
    def build_research_path(
        cls,
        plan_name: str | None = None,
        phase_name: str | None = None,
        research_name: str | None = None,
    ) -> str:
        plan = plan_name or '*'
        phase = phase_name or '*'
        research = f'{research_name}.md' if research_name else '*.md'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{plan}/{cls.PHASES_DIR}/{phase}/{cls.RESEARCH_DIR}/{research}'

    @classmethod
    def build_task_path(
        cls,
        plan_name: str | None = None,
        phase_name: str | None = None,
        task_name: str | None = None,
    ) -> str:
        """Build path to task file.

        Tasks are stored under their parent phase directory.
        """
        plan = plan_name or '*'
        phase = phase_name or '*'
        task = f'{task_name}.md' if task_name else '*.md'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{plan}/{cls.PHASES_DIR}/{phase}/{cls.TASKS_DIR}/{task}'

    @classmethod
    def build_completion_path(cls, plan_name: str | None = None) -> str:
        if plan_name:
            return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{plan_name}/{cls.COMPLETION_FILE}'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/*/{cls.COMPLETION_FILE}'
