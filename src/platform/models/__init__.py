"""Pydantic models for platform configuration with fail-fast validation."""

from .code import (
    AutomatedQualityCheckerAgentTools,
    BackendApiReviewerAgentTools,
    CodeCommandTools,
    CodeQualityReviewerAgentTools,
    CodingStandardsReviewerAgentTools,
    CoderAgentTools,
    DatabaseReviewerAgentTools,
    FrontendReviewerAgentTools,
    InfrastructureReviewerAgentTools,
    SpecAlignmentReviewerAgentTools,
)
from .core import AgentToolsModel, CommandToolsModel, PlatformModel, ToolReference
from .patch import PatchCommandTools, PatchPlannerAgentTools
from .phase import PhaseArchitectAgentTools, PhaseCommandTools, PhaseCriticAgentTools
from ..platform_selector import PlatformType
from .plan import (
    AnalystCriticAgentTools,
    PlanAnalystAgentTools,
    PlanCommandTools,
    PlanConversationCommandTools,
    PlanCriticAgentTools,
    StandardsCommandTools,
)
from .project import (
    LanguageTooling,
    PlanPlatformChangeRequest,
    PlanSetupRequest,
    PlanSetupWithRecommendationRequest,
    PlatformRequest,
    PlatformRequirements,
    ProjectConfig,
    ProjectStack,
    ProjectToolingConfig,
    TemplateGenerationRequest,
)
from .roadmap import (
    CreatePhaseAgentTools,
    PlanRoadmapAgentTools,
    PlanRoadmapCommandTools,
    RoadmapAgentTools,
    RoadmapCriticAgentTools,
)
from .task import TaskCommandTools, TaskPlanCriticAgentTools, TaskPlannerAgentTools


__all__ = [
    'AgentToolsModel',
    'CommandToolsModel',
    'PlatformModel',
    'ProjectStack',
    'LanguageTooling',
    'ProjectToolingConfig',
    'PlatformRequest',
    'PlatformRequirements',
    'PlanSetupRequest',
    'PlanSetupWithRecommendationRequest',
    'PlanPlatformChangeRequest',
    'TemplateGenerationRequest',
    'ProjectConfig',
    'ToolReference',
    'PhaseCommandTools',
    'PlanCommandTools',
    'PlanConversationCommandTools',
    'StandardsCommandTools',
    'CodeCommandTools',
    'PatchCommandTools',
    'PlanRoadmapCommandTools',
    'TaskCommandTools',
    'PlanRoadmapAgentTools',
    'PhaseArchitectAgentTools',
    'PhaseCriticAgentTools',
    'CreatePhaseAgentTools',
    'CoderAgentTools',
    'AnalystCriticAgentTools',
    'PlanAnalystAgentTools',
    'PlanCriticAgentTools',
    'RoadmapAgentTools',
    'RoadmapCriticAgentTools',
    'AutomatedQualityCheckerAgentTools',
    'SpecAlignmentReviewerAgentTools',
    'CodeQualityReviewerAgentTools',
    'FrontendReviewerAgentTools',
    'BackendApiReviewerAgentTools',
    'DatabaseReviewerAgentTools',
    'InfrastructureReviewerAgentTools',
    'CodingStandardsReviewerAgentTools',
    'TaskPlannerAgentTools',
    'TaskPlanCriticAgentTools',
    'PatchPlannerAgentTools',
    'PlatformType',
]
