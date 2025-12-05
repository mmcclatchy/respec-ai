from typing import Any

from .command_strategies import (
    BuildCommandStrategy,
    CommandStrategy,
    PlanCommandStrategy,
    PlanConversationCommandStrategy,
    PlanRoadmapCommandStrategy,
    SpecCommandStrategy,
)
from .platform_selector import PlatformSelector, PlatformType
from .tool_enums import CommandTemplate
from .tool_registry import ToolRegistry


class TemplateCoordinator:
    def __init__(self) -> None:
        self.platform_selector = PlatformSelector()
        self.tool_registry = ToolRegistry()

        self._strategies: dict[CommandTemplate, CommandStrategy[Any]] = {
            CommandTemplate.PLAN: PlanCommandStrategy(self.tool_registry),
            CommandTemplate.SPEC: SpecCommandStrategy(self.tool_registry),
            CommandTemplate.BUILD: BuildCommandStrategy(self.tool_registry),
            CommandTemplate.ROADMAP: PlanRoadmapCommandStrategy(self.tool_registry),
            CommandTemplate.PLAN_CONVERSATION: PlanConversationCommandStrategy(self.tool_registry),
        }

    def generate_command_template(self, command_name: str | CommandTemplate, platform: PlatformType) -> str:
        if isinstance(command_name, str):
            try:
                command_name = CommandTemplate(command_name)
            except ValueError:
                raise ValueError(f'Unknown command template: {command_name}')

        command_enum = command_name
        if command_enum not in self._strategies:
            raise ValueError(f'Unknown command template: {command_enum.value}')

        strategy = self._strategies[command_enum]
        return strategy.generate_template(platform)

    def validate_template_generation(self, command_name: str | CommandTemplate, platform: PlatformType) -> bool:
        if isinstance(command_name, str):
            command_name = CommandTemplate(command_name)

        command_enum = command_name
        if command_enum not in self._strategies:
            return False

        strategy = self._strategies[command_enum]
        required_operations = strategy.get_required_operations()
        return self.tool_registry.validate_platform_support(platform, required_operations)

    def get_available_commands(self) -> list[str]:
        return [cmd.value for cmd in self._strategies.keys()]
