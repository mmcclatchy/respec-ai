"""Path constants for respec-ai file system organization."""

from enum import StrEnum


class PathComponent(StrEnum):
    RESPEC_AI_DIR = '.respec-ai'
    PLANS_DIR = 'plans'
    PHASES_DIR = 'phases'
    PROJECT_PLAN_FILE = 'project_plan.md'
    COMPLETION_FILE = 'project_completion.md'

    @classmethod
    def build_plan_path(cls, project_name: str | None = None) -> str:
        if project_name:
            return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{project_name}/{cls.PROJECT_PLAN_FILE}'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/*/{cls.PROJECT_PLAN_FILE}'

    @classmethod
    def build_phase_path(cls, project_name: str | None = None, phase_name: str | None = None) -> str:
        proj = project_name or '*'
        phase = f'{phase_name}.md' if phase_name else '*.md'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{proj}/{cls.PHASES_DIR}/{phase}'

    @classmethod
    def build_completion_path(cls, project_name: str | None = None) -> str:
        if project_name:
            return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/{project_name}/{cls.COMPLETION_FILE}'
        return f'{cls.RESPEC_AI_DIR}/{cls.PLANS_DIR}/*/{cls.COMPLETION_FILE}'
