from collections.abc import Callable

from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import TaskCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_task_tools
from src.platform.templates.commands import generate_task_command_template
from src.platform.tool_enums import AbstractOperation


class TaskCommandStrategy(CommandStrategy[TaskCommandTools]):
    def get_required_operations(self) -> list[str]:
        return [
            AbstractOperation.GET_PHASE_TOOL,
            AbstractOperation.LIST_PHASE_TASKS_TOOL,
            AbstractOperation.CREATE_TASK_TOOL,
        ]

    def build_tools(self, platform: PlatformType) -> TaskCommandTools:
        get_phase_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.GET_PHASE_TOOL, platform)
        list_phase_tasks_tool = self.tool_registry.get_tool_for_platform(
            AbstractOperation.LIST_PHASE_TASKS_TOOL, platform
        )
        create_task_tool = self.tool_registry.get_tool_for_platform(AbstractOperation.CREATE_TASK_TOOL, platform)

        platform_tools = [
            get_phase_tool,
            list_phase_tasks_tool,
            create_task_tool,
        ]
        return create_task_tools(platform_tools, platform)

    def get_template_func(self) -> Callable[[TaskCommandTools], str]:
        return generate_task_command_template
