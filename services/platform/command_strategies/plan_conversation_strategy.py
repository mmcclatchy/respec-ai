from collections.abc import Callable

from services.platform.command_strategies.base import CommandStrategy
from services.platform.platform_selector import PlatformType
from services.platform.templates.commands import generate_plan_conversation_command_template


class PlanConversationCommandStrategy(CommandStrategy[None]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(self, platform: PlatformType) -> None:
        return None

    def get_template_func(self) -> Callable[[None], str]:
        return generate_plan_conversation_command_template
