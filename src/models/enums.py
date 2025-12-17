from enum import Enum


class PlanStatus(str, Enum):
    DRAFT = 'draft'
    IN_REVIEW = 'in-review'
    APPROVED = 'approved'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class RequirementsStatus(str, Enum):
    DRAFT = 'draft'
    IN_REVIEW = 'in-review'
    APPROVED = 'approved'
    IMPLEMENTATION_READY = 'implementation-ready'
    COMPLETED = 'completed'


class RoadmapStatus(str, Enum):
    DRAFT = 'draft'
    IN_REVIEW = 'in-review'
    APPROVED = 'approved'
    IN_PROGRESS = 'in-progress'
    COMPLETED = 'completed'
    BLOCKED = 'blocked'


class PhaseStatus(str, Enum):
    DRAFT = 'draft'
    IN_REVIEW = 'in-review'
    APPROVED = 'approved'
    IMPLEMENTATION_READY = 'implementation-ready'
    IN_DEVELOPMENT = 'in-development'
    COMPLETED = 'completed'


class BuildStatus(str, Enum):
    PLANNING = 'planning'
    IN_PROGRESS = 'in-progress'
    TESTING = 'testing'
    CODE_REVIEW = 'code-review'
    COMPLETED = 'completed'
    BLOCKED = 'blocked'


class FSSDCriteria(str, Enum):
    CLARITY = 'clarity'
    COMPLETENESS = 'completeness'
    CONSISTENCY = 'consistency'
    FEASIBILITY = 'feasibility'
    TESTABILITY = 'testability'
    MAINTAINABILITY = 'maintainability'
    SCALABILITY = 'scalability'
    SECURITY = 'security'
    PERFORMANCE = 'performance'
    USABILITY = 'usability'
    DOCUMENTATION = 'documentation'
    INTEGRATION = 'integration'


class CriticAgent(str, Enum):
    PLAN_CRITIC = 'plan-critic'
    ANALYST_CRITIC = 'analyst-critic'
    ROADMAP_CRITIC = 'roadmap-critic'
    PHASE_CRITIC = 'phase-critic'
    TASK_CRITIC = 'task-critic'
    TASK_REVIEWER = 'task-reviewer'


class DocumentType(str, Enum):
    PLAN = 'plan'
    ROADMAP = 'roadmap'
    PHASE = 'phase'
    TASK = 'task'
    TASK_BREAKDOWN = 'task_breakdown'  # Deprecated: use TASK (kept for backwards compat)
    COMPLETION_REPORT = 'completion_report'

    @property
    def quoted(self) -> str:
        return f'"{self.value}"'
