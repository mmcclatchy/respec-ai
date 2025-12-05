from collections.abc import Callable

from src.platform.command_strategies.base import CommandStrategy
from src.platform.platform_selector import PlatformType
from src.platform.templates.commands import generate_plan_conversation_command_template


class PlanConversationCommandStrategy(CommandStrategy[None]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(self, platform: PlatformType) -> None:
        return None

    def get_template_func(self) -> Callable[[None], str]:
        return generate_plan_conversation_command_template
