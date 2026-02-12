from src.models.enums import StepMode


MODE_TO_REVIEWER: dict[StepMode, str] = {
    StepMode.FRONTEND: 'frontend-reviewer',
    StepMode.API: 'backend-api-reviewer',
    StepMode.DATABASE: 'database-reviewer',
    StepMode.INFRASTRUCTURE: 'infrastructure-reviewer',
}


def resolve_active_reviewers(step_modes: set[StepMode]) -> list[str]:
    reviewers = ['automated-quality-checker', 'spec-alignment-reviewer']
    for mode, reviewer in MODE_TO_REVIEWER.items():
        if mode in step_modes:
            reviewers.append(reviewer)
    reviewers.append('review-consolidator')
    return reviewers
