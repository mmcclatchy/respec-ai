from collections.abc import Callable

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PlanCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_plan_command_tools
from src.platform.templates.commands import generate_plan_command_template


class PlanCommandStrategy(CommandStrategy[PlanCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(self, platform: PlatformType) -> PlanCommandTools:
        adapter = get_platform_adapter(platform)
        platform_tools = [adapter.create_plan_tool, adapter.create_plan_completion_tool, adapter.retrieve_plan_tool]
        return create_plan_command_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[PlanCommandTools], str]:
        return generate_plan_command_template
