from collections.abc import Callable

from services.platform.command_strategies.base import CommandStrategy
from services.platform.models import SpecCommandTools
from services.platform.platform_selector import PlatformType
from services.platform.template_helpers import create_spec_command_tools
from services.platform.tool_enums import AbstractOperation


from services.platform.templates.commands import generate_spec_command_template


class SpecCommandStrategy(CommandStrategy[SpecCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [
            AbstractOperation.CREATE_SPEC_TOOL.value,
            AbstractOperation.GET_SPEC_TOOL.value,
            AbstractOperation.UPDATE_SPEC_TOOL.value,
        ]

    def build_tools(self, platform: PlatformType) -> SpecCommandTools:
        create_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.CREATE_SPEC_TOOL.value, platform)
        get_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_SPEC_TOOL.value, platform)
        update_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform)

        platform_tools = [create_spec_tool, get_spec_tool, update_spec_tool]
        tools_yaml = create_spec_command_tools(platform_tools)

        return SpecCommandTools(
            tools_yaml=tools_yaml,
            create_spec_tool=create_spec_tool,
            get_spec_tool=get_spec_tool,
            update_spec_tool=update_spec_tool,
        )

    def get_template_func(self) -> Callable[[SpecCommandTools], str]:
        return generate_spec_command_template
