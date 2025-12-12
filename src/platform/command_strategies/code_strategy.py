from collections.abc import Callable

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import CodeCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_code_command_tools
from src.platform.templates.commands import generate_code_command_template
from src.platform.tool_enums import AbstractOperation


class CodeCommandStrategy(CommandStrategy[CodeCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [AbstractOperation.GET_PHASE_TOOL, AbstractOperation.COMMENT_PHASE_TOOL]

    def build_tools(self, platform: PlatformType) -> CodeCommandTools:
        get_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_PHASE_TOOL, platform)
        comment_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.COMMENT_PHASE_TOOL, platform)

        platform_tools = [get_phase_tool, comment_phase_tool]
        return create_code_command_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[CodeCommandTools], str]:
        return generate_code_command_template
