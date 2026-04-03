from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PlanConversationCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_plan_conversation_command_tools
from src.platform.templates.commands import generate_plan_conversation_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class PlanConversationCommandStrategy(CommandStrategy[PlanConversationCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> PlanConversationCommandTools:
        return create_plan_conversation_command_tools(tui_adapter)

    def get_template_func(self) -> Callable[[PlanConversationCommandTools], str]:
        return generate_plan_conversation_command_template
