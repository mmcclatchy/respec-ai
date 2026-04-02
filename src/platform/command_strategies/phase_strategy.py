from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PhaseCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_phase_command_tools
from src.platform.templates.commands import generate_phase_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class PhaseCommandStrategy(CommandStrategy[PhaseCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> PhaseCommandTools:
        adapter = get_platform_adapter(platform)
        platform_tools = [adapter.create_phase_tool, adapter.retrieve_phase_tool, adapter.update_phase_tool]
        return create_phase_command_tools(platform_tools, platform, plans_dir, tui_adapter)

    def get_template_func(self) -> Callable[[PhaseCommandTools], str]:
        return generate_phase_command_template
