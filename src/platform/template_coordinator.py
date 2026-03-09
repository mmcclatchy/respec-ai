from typing import Any

from .command_strategies import (
    CodeCommandStrategy,
    CommandStrategy,
    PatchCommandStrategy,
    PhaseCommandStrategy,
    PlanCommandStrategy,
    PlanConversationCommandStrategy,
    PlanRoadmapCommandStrategy,
    TaskCommandStrategy,
)
from .platform_selector import PlatformSelector, PlatformType
from .tool_enums import RespecAICommand


class TemplateCoordinator:
    def __init__(self) -> None:
        self.platform_selector = PlatformSelector()

        self._strategies: dict[RespecAICommand, CommandStrategy[Any]] = {
            RespecAICommand.PLAN: PlanCommandStrategy(),
            RespecAICommand.PHASE: PhaseCommandStrategy(),
            RespecAICommand.TASK: TaskCommandStrategy(),
            RespecAICommand.CODE: CodeCommandStrategy(),
            RespecAICommand.PATCH: PatchCommandStrategy(),
            RespecAICommand.ROADMAP: PlanRoadmapCommandStrategy(),
            RespecAICommand.PLAN_CONVERSATION: PlanConversationCommandStrategy(),
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
        return command_enum in self._strategies

    def get_available_commands(self) -> list[str]:
        return [cmd.value for cmd in self._strategies.keys()]
