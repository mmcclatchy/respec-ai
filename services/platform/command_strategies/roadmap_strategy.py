from collections.abc import Callable

from services.platform.command_strategies.base import CommandStrategy
from services.platform.models import PlanRoadmapCommandTools
from services.platform.platform_selector import PlatformType
from services.platform.template_helpers import create_roadmap_tools
from services.platform.tool_enums import AbstractOperation
from services.templates.commands import generate_roadmap_command_template


class PlanRoadmapCommandStrategy(CommandStrategy[PlanRoadmapCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [
            AbstractOperation.GET_PROJECT_PLAN_TOOL.value,
            AbstractOperation.UPDATE_PROJECT_PLAN_TOOL.value,
            AbstractOperation.CREATE_SPEC_TOOL.value,
            AbstractOperation.GET_SPEC_TOOL.value,
            AbstractOperation.UPDATE_SPEC_TOOL.value,
        ]

    def build_tools(self, platform: PlatformType) -> PlanRoadmapCommandTools:
        get_project_plan_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.GET_PROJECT_PLAN_TOOL.value, platform
        )
        update_project_plan_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.UPDATE_PROJECT_PLAN_TOOL.value, platform
        )
        create_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.CREATE_SPEC_TOOL.value, platform)
        get_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_SPEC_TOOL.value, platform)
        update_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform)

        platform_tools = [
            get_project_plan_tool,
            update_project_plan_tool,
            create_spec_tool,
            get_spec_tool,
            update_spec_tool,
        ]
        tools_yaml = create_roadmap_tools(platform_tools)

        return PlanRoadmapCommandTools(
            tools_yaml=tools_yaml,
            get_project_plan_tool=get_project_plan_tool,
            update_project_plan_tool=update_project_plan_tool,
            create_spec_tool=create_spec_tool,
            get_spec_tool=get_spec_tool,
            update_spec_tool=update_spec_tool,
        )

    def get_template_func(self) -> Callable[[PlanRoadmapCommandTools], str]:
        return generate_roadmap_command_template
