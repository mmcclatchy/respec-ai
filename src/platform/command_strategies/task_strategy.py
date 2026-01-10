from collections.abc import Callable

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import TaskCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_task_tools
from src.platform.templates.commands import generate_task_command_template


class TaskCommandStrategy(CommandStrategy[TaskCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(self, platform: PlatformType) -> TaskCommandTools:
        adapter = get_platform_adapter(platform)
        platform_tools = [
            adapter.retrieve_phase_tool,
            adapter.list_tasks_tool,
            adapter.create_task_tool,
        ]
        return create_task_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[TaskCommandTools], str]:
        return generate_task_command_template
