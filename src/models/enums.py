from enum import Enum


class ProjectStatus(str, Enum):
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


class SpecStatus(str, Enum):
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
    SPEC_CRITIC = 'spec-critic'
    BUILD_CRITIC = 'build-critic'
    BUILD_REVIEWER = 'build-reviewer'
