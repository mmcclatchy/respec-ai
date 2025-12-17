from typing import Any

from .command_strategies import (
    CodeCommandStrategy,
    CommandStrategy,
    PhaseCommandStrategy,
    PlanCommandStrategy,
    PlanConversationCommandStrategy,
    PlanRoadmapCommandStrategy,
    TaskCommandStrategy,
)
from .platform_selector import PlatformSelector, PlatformType
from .tool_enums import RespecAICommand
from .tool_registry import ToolRegistry


class TemplateCoordinator:
    def __init__(self) -> None:
        self.platform_selector = PlatformSelector()
        self.tool_registry = ToolRegistry()

        self._strategies: dict[RespecAICommand, CommandStrategy[Any]] = {
            RespecAICommand.PLAN: PlanCommandStrategy(self.tool_registry),
            RespecAICommand.PHASE: PhaseCommandStrategy(self.tool_registry),
            RespecAICommand.TASK: TaskCommandStrategy(self.tool_registry),
            RespecAICommand.CODE: CodeCommandStrategy(self.tool_registry),
            RespecAICommand.ROADMAP: PlanRoadmapCommandStrategy(self.tool_registry),
            RespecAICommand.PLAN_CONVERSATION: PlanConversationCommandStrategy(self.tool_registry),
        }

    def generate_command_template(self, command_name: str | RespecAICommand, platform: PlatformType) -> str:
        if isinstance(command_name, str):
            try:
                command_name = RespecAICommand(command_name)
            except ValueError:
                raise ValueError(f'Unknown command template: {command_name}')

        command_enum = command_name
        if command_enum not in self._strategies:
            raise ValueError(f'Unknown command template: {command_enum.value}')

        strategy = self._strategies[command_enum]
        return strategy.generate_template(platform)

    def validate_template_generation(self, command_name: str | RespecAICommand, platform: PlatformType) -> bool:
        if isinstance(command_name, str):
            command_name = RespecAICommand(command_name)

        command_enum = command_name
        if command_enum not in self._strategies:
            return False

        strategy = self._strategies[command_enum]
        required_operations = strategy.get_required_operations()
        return self.tool_registry.validate_platform_support(platform, required_operations)

    def get_available_commands(self) -> list[str]:
        return [cmd.value for cmd in self._strategies.keys()]
