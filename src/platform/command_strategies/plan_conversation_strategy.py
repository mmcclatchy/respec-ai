from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.command_strategies.base import CommandStrategy
from src.platform.platform_selector import PlatformType
from src.platform.templates.commands import generate_plan_conversation_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class PlanConversationCommandStrategy(CommandStrategy[None]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> None:
        return None

    def get_template_func(self) -> Callable[[None], str]:
        return generate_plan_conversation_command_template
