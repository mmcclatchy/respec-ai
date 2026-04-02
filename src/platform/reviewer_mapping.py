from pathlib import Path

from src.models.enums import StepMode


MODE_TO_REVIEWER: dict[StepMode, str] = {
    StepMode.FRONTEND: 'frontend-reviewer',
    StepMode.API: 'backend-api-reviewer',
    StepMode.DATABASE: 'database-reviewer',
    StepMode.INFRASTRUCTURE: 'infrastructure-reviewer',
}


def has_coding_standards_file() -> bool:
    standards_file = Path.cwd() / 'CLAUDE.md'

    if not standards_file.exists():
        return False

    try:
        content = standards_file.read_text()
        return bool(content.strip())
    except Exception:
        return False


def resolve_active_reviewers(step_modes: set[StepMode]) -> list[str]:
    reviewers = ['automated-quality-checker', 'spec-alignment-reviewer', 'code-quality-reviewer']

    for mode, reviewer in MODE_TO_REVIEWER.items():
        if mode in step_modes:
            reviewers.append(reviewer)

    if has_coding_standards_file():
        reviewers.append('coding-standards-reviewer')

    reviewers.append('review-consolidator')
    return reviewers
