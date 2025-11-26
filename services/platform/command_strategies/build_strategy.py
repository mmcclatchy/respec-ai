from collections.abc import Callable

from services.platform.command_strategies.base import CommandStrategy
from services.platform.models import BuildCommandTools
from services.platform.platform_selector import PlatformType
from services.platform.template_helpers import create_build_command_tools
from services.platform.tool_enums import AbstractOperation


from services.platform.templates.commands import generate_build_command_template


class BuildCommandStrategy(CommandStrategy[BuildCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [AbstractOperation.GET_SPEC_TOOL.value, AbstractOperation.COMMENT_SPEC_TOOL.value]

    def build_tools(self, platform: PlatformType) -> BuildCommandTools:
        get_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_SPEC_TOOL.value, platform)
        comment_spec_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.COMMENT_SPEC_TOOL.value, platform
        )

        platform_tools = [get_spec_tool, comment_spec_tool]
        tools_yaml = create_build_command_tools(platform_tools)

        return BuildCommandTools(
            tools_yaml=tools_yaml,
            get_spec_tool=get_spec_tool,
            comment_spec_tool=comment_spec_tool,
        )

    def get_template_func(self) -> Callable[[BuildCommandTools], str]:
        return generate_build_command_template
