from collections.abc import Callable

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import CodeCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_code_command_tools
from src.platform.templates.commands import generate_code_command_template


class CodeCommandStrategy(CommandStrategy[CodeCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(self, platform: PlatformType, plans_dir: str = '~/.claude/plans') -> CodeCommandTools:
        adapter = get_platform_adapter(platform)
        platform_tools = [adapter.retrieve_phase_tool, adapter.comment_phase_tool]
        return create_code_command_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[CodeCommandTools], str]:
        return generate_code_command_template
