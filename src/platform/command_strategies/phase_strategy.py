from collections.abc import Callable

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PhaseCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_phase_command_tools
from src.platform.templates.commands import generate_phase_command_template
from src.platform.tool_enums import AbstractOperation


class PhaseCommandStrategy(CommandStrategy[PhaseCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [
            AbstractOperation.CREATE_PHASE_TOOL,
            AbstractOperation.GET_PHASE_TOOL,
            AbstractOperation.UPDATE_PHASE_TOOL,
        ]

    def build_tools(self, platform: PlatformType) -> PhaseCommandTools:
        create_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.CREATE_PHASE_TOOL, platform)
        get_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_PHASE_TOOL, platform)
        update_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_PHASE_TOOL, platform)

        platform_tools = [create_phase_tool, get_phase_tool, update_phase_tool]
        return create_phase_command_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[PhaseCommandTools], str]:
        return generate_phase_command_template
