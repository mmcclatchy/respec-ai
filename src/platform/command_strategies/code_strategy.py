from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import CodeCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_code_command_tools
from src.platform.templates.commands import generate_code_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class CodeCommandStrategy(CommandStrategy[CodeCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> CodeCommandTools:
        adapter = get_platform_adapter(platform)
        return create_code_command_tools(
            adapter.retrieve_phase_tool,
            adapter.comment_phase_tool,
            platform,
            tui_adapter,
        )

    def get_template_func(self) -> Callable[[CodeCommandTools], str]:
        return generate_code_command_template
