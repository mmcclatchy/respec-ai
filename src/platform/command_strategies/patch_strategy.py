from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PatchCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_patch_command_tools
from src.platform.templates.commands import generate_patch_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class PatchCommandStrategy(CommandStrategy[PatchCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        plans_dir: str = '~/.claude/plans',
        tui_adapter: 'TuiAdapter | None' = None,
    ) -> PatchCommandTools:
        adapter = get_platform_adapter(platform)
        platform_tools = [adapter.retrieve_phase_tool, adapter.comment_phase_tool]
        return create_patch_command_tools(platform_tools, platform, plans_dir=plans_dir, tui_adapter=tui_adapter)

    def get_template_func(self) -> Callable[[PatchCommandTools], str]:
        return generate_patch_command_template
