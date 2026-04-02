from collections.abc import Callable
from typing import TYPE_CHECKING

from src.platform.adapters import get_platform_adapter
from src.platform.command_strategies.base import CommandStrategy
from src.platform.models import PlanRoadmapCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_roadmap_tools
from src.platform.templates.commands import generate_roadmap_command_template

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


class PlanRoadmapCommandStrategy(CommandStrategy[PlanRoadmapCommandTools]):
    def get_required_operations(self) -> list[str]:
        return []

    def build_tools(
        self,
        platform: PlatformType,
        tui_adapter: 'TuiAdapter',
        plans_dir: str = '',
    ) -> PlanRoadmapCommandTools:
        adapter = get_platform_adapter(platform)
        platform_tools = [
            adapter.retrieve_plan_tool,
            adapter.list_phases_tool,
        ]
        return create_roadmap_tools(platform_tools, platform, tui_adapter)

    def get_template_func(self) -> Callable[[PlanRoadmapCommandTools], str]:
        return generate_roadmap_command_template
