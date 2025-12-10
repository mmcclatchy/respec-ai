from collections.abc import Callable

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import CodeCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_code_command_tools
from src.platform.templates.commands import generate_code_command_template
from src.platform.tool_enums import AbstractOperation


class CodeCommandStrategy(CommandStrategy[CodeCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [AbstractOperation.GET_SPEC_TOOL.value, AbstractOperation.COMMENT_SPEC_TOOL.value]

    def build_tools(self, platform: PlatformType) -> CodeCommandTools:
        get_spec_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_SPEC_TOOL.value, platform)
        comment_spec_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.COMMENT_SPEC_TOOL.value, platform
        )

        platform_tools = [get_spec_tool, comment_spec_tool]
        tools_yaml = create_code_command_tools(platform_tools)

        return CodeCommandTools(
            tools_yaml=tools_yaml,
            get_spec_tool=get_spec_tool,
            comment_spec_tool=comment_spec_tool,
            platform=platform,
        )

    def get_template_func(self) -> Callable[[CodeCommandTools], str]:
        return generate_code_command_template
