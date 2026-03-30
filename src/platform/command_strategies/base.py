from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from src.platform.platform_selector import PlatformType

if TYPE_CHECKING:
    from src.platform.tui_adapters.base import TuiAdapter


T = TypeVar('T')


class CommandStrategyProtocol(Protocol):
    def get_required_operations(self) -> list[str]: ...
    def generate_template(self, platform: PlatformType) -> str: ...


class CommandStrategy(ABC, Generic[T]):
    @abstractmethod
    def get_required_operations(self) -> list[str]:
        pass

    @abstractmethod
    def build_tools(
        self,
        platform: PlatformType,
        plans_dir: str = '~/.claude/plans',
        tui_adapter: 'TuiAdapter | None' = None,
    ) -> T:
        pass

    @abstractmethod
    def get_template_func(self) -> Callable[[T], str]:
        pass

    def generate_template(
        self,
        platform: PlatformType,
        plans_dir: str = '~/.claude/plans',
        tui_adapter: 'TuiAdapter | None' = None,
    ) -> str:
        tools = self.build_tools(platform, plans_dir=plans_dir, tui_adapter=tui_adapter)
        template_func = self.get_template_func()
        return template_func(tools)
