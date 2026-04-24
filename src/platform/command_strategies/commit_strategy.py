from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import CommitCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_commit_command_tools
from src.platform.templates.commands import generate_commit_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class CommitCommandStrategy(CommandStrategy[CommitCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> CommitCommandTools:
        return create_commit_command_tools(tui_adapter)

    def get_template_func(self) -> Callable[[CommitCommandTools], str]:
        return generate_commit_command_template
