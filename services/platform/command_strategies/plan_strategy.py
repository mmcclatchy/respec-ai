from collections.abc import Callable

from services.platform.command_strategies.base import CommandStrategy
from services.platform.models import PlanCommandTools
from services.platform.platform_selector import PlatformType
from services.platform.template_helpers import create_plan_command_tools
from services.platform.tool_enums import AbstractOperation


from services.platform.templates.commands import generate_plan_command_template


class PlanCommandStrategy(CommandStrategy[PlanCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [
            AbstractOperation.CREATE_PROJECT_EXTERNAL.value,
            AbstractOperation.CREATE_PROJECT_COMPLETION_EXTERNAL.value,
            AbstractOperation.GET_PROJECT_PLAN_TOOL.value,
        ]

    def build_tools(self, platform: PlatformType) -> PlanCommandTools:
        create_project_external = self.tool_registry.get_tool_for_platform(
            AbstractOperation.CREATE_PROJECT_EXTERNAL.value, platform
        )
        create_project_completion_external = self.tool_registry.get_tool_for_platform(
            AbstractOperation.CREATE_PROJECT_COMPLETION_EXTERNAL.value, platform
        )
        get_project_plan_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.GET_PROJECT_PLAN_TOOL.value, platform
        )

        platform_tools = [create_project_external, create_project_completion_external, get_project_plan_tool]
        tools_yaml = create_plan_command_tools(platform_tools)

        return PlanCommandTools(
            tools_yaml=tools_yaml,
            create_project_external=create_project_external,
            create_project_completion_external=create_project_completion_external,
            get_project_plan_tool=get_project_plan_tool,
            platform=platform,
        )

    def get_template_func(self) -> Callable[[PlanCommandTools], str]:
        return generate_plan_command_template
