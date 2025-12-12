from collections.abc import Callable

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PlanRoadmapCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_roadmap_tools
from src.platform.templates.commands import generate_roadmap_command_template
from src.platform.tool_enums import AbstractOperation


class PlanRoadmapCommandStrategy(CommandStrategy[PlanRoadmapCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [
            AbstractOperation.GET_PROJECT_PLAN_TOOL,
            AbstractOperation.UPDATE_PROJECT_PLAN_TOOL,
            AbstractOperation.CREATE_PHASE_TOOL,
            AbstractOperation.GET_PHASE_TOOL,
            AbstractOperation.UPDATE_PHASE_TOOL,
            AbstractOperation.LIST_PROJECT_PHASES_TOOL,
        ]

    def build_tools(self, platform: PlatformType) -> PlanRoadmapCommandTools:
        get_project_plan_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.GET_PROJECT_PLAN_TOOL, platform
        )
        update_project_plan_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.UPDATE_PROJECT_PLAN_TOOL, platform
        )
        create_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.CREATE_PHASE_TOOL, platform)
        get_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_PHASE_TOOL, platform)
        update_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_PHASE_TOOL, platform)
        list_project_phases_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.LIST_PROJECT_PHASES_TOOL, platform
        )

        platform_tools = [
            get_project_plan_tool,
            update_project_plan_tool,
            create_phase_tool,
            get_phase_tool,
            update_phase_tool,
            list_project_phases_tool,
        ]
        return create_roadmap_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[PlanRoadmapCommandTools], str]:
        return generate_roadmap_command_template
