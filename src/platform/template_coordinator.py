from typing import TYPE_CHECKING, Any

from .command_strategies import (
    CodeCommandStrategy,
    CommandStrategy,
    PatchCommandStrategy,
    PhaseCommandStrategy,
    PlanCommandStrategy,
    PlanConversationCommandStrategy,
    PlanRoadmapCommandStrategy,
    StandardsCommandStrategy,
    TaskCommandStrategy,
)
from .platform_selector import PlatformSelector, PlatformType
from .tool_enums import RespecAICommand

if TYPE_CHECKING:
    from .tui_adapters.base import TuiAdapter


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
            RespecAICommand.STANDARDS: StandardsCommandStrategy(),
        }

    def generate_command_template(
        self,
        command_name: str | RespecAICommand,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> str:
        if isinstance(command_name, str):
            try:
                command_name = RespecAICommand(command_name)
            except ValueError:
                raise ValueError(f'Unknown command template: {command_name}')

        command_enum = command_name
        if command_enum not in self._strategies:
            raise ValueError(f'Unknown command template: {command_enum.value}')

        strategy = self._strategies[command_enum]
        return strategy.generate_template(platform, tui_adapter, plans_dir=plans_dir)

    def validate_template_generation(self, command_name: str | RespecAICommand, platform: PlatformType) -> bool:
        if isinstance(command_name, str):
            command_name = RespecAICommand(command_name)

        command_enum = command_name
        return command_enum in self._strategies

    def get_available_commands(self) -> list[str]:
        return [cmd.value for cmd in self._strategies.keys()]
