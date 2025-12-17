from abc import ABC, abstractmethod

from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class DocumentToolsInterface(ABC):
    def __init__(self, state: StateManager) -> None:
        self.state = state

    @abstractmethod
    async def store(self, key: str, content: str) -> MCPResponse: ...

    @abstractmethod
    async def get(self, key: str | None = None, loop_id: str | None = None) -> MCPResponse: ...

    @abstractmethod
    async def list(self, parent_key: str | None = None) -> MCPResponse: ...

    @abstractmethod
    async def update(self, key: str, content: str) -> MCPResponse: ...

    @abstractmethod
    async def delete(self, key: str) -> MCPResponse: ...

    @abstractmethod
    async def link_loop(self, loop_id: str, key: str) -> MCPResponse: ...
