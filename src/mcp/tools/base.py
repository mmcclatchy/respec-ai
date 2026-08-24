from abc import ABC, abstractmethod
from typing import ClassVar

from src.models.base import MCPModel
from src.utils.enums import LoopStatus
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class DocumentToolsInterface(ABC):
    document_model: ClassVar[type[MCPModel]]

    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def validate(self, content: str) -> MCPResponse:
        issues = self.document_model.find_content_loss(content)
        if not issues:
            return MCPResponse(id='validate', status=LoopStatus.COMPLETED, message='No content loss detected.')

        message = '\n'.join([f'Content loss detected in {len(issues)} heading(s):', *[f'- {i}' for i in issues]])
        return MCPResponse(id='validate', status=LoopStatus.USER_INPUT, message=message)

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
