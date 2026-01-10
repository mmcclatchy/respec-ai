from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, Protocol, TypeVar

from src.platform.platform_selector import PlatformType


T = TypeVar('T')


class CommandStrategyProtocol(Protocol):
    def get_required_operations(self) -> list[str]: ...
    def generate_template(self, platform: PlatformType) -> str: ...


class CommandStrategy(ABC, Generic[T]):
    @abstractmethod
    def get_required_operations(self) -> list[str]:
        pass

    @abstractmethod
    def build_tools(self, platform: PlatformType) -> T:
        pass

    @abstractmethod
    def get_template_func(self) -> Callable[[T], str]:
        pass

    def generate_template(self, platform: PlatformType) -> str:
        tools = self.build_tools(platform)
        template_func = self.get_template_func()
        return template_func(tools)
