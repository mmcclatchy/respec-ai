from abc import ABC, abstractmethod
from typing import ClassVar

from fastmcp.exceptions import ToolError

from src.models.base import MCPModel
from src.utils.enums import LoopStatus
from src.utils.loop_state import DocumentValidationResponse, MCPResponse
from src.utils.state_manager import StateManager


EXACTLY_ONE_INPUT = 'Pass exactly one of content or key'
NO_CONTENT_LOSS = 'No content loss detected.'


def content_loss_response(issues: list[str]) -> DocumentValidationResponse:
    if not issues:
        return DocumentValidationResponse(id='validate', status=LoopStatus.COMPLETED, message=NO_CONTENT_LOSS)

    message = '\n'.join([f'Content loss detected in {len(issues)} heading(s):', *[f'- {i}' for i in issues]])
    return DocumentValidationResponse(id='validate', status=LoopStatus.USER_INPUT, message=message)


class DocumentToolsInterface(ABC):
    document_model: ClassVar[type[MCPModel]]

    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def validate(
        self, content: str | None = None, key: str | None = None, implementation_markdown: str | None = None
    ) -> DocumentValidationResponse:
        if key is not None or implementation_markdown is not None:
            raise ToolError('key and implementation_markdown are supported only for phase documents')
        if not content:
            raise ToolError('content cannot be empty')

        return content_loss_response(self.document_model.find_content_loss(content))

    @abstractmethod
    async def store(self, key: str, content: str, allow_frozen_field_edits: bool = False) -> MCPResponse: ...

    @abstractmethod
    async def get(
        self, key: str | None = None, loop_id: str | None = None, include_phases: bool = True
    ) -> MCPResponse: ...

    @abstractmethod
    async def list(self, parent_key: str | None = None) -> MCPResponse: ...

    @abstractmethod
    async def update(self, key: str, content: str, allow_frozen_field_edits: bool = False) -> MCPResponse: ...

    @abstractmethod
    async def delete(self, key: str) -> MCPResponse: ...

    @abstractmethod
    async def link_loop(self, loop_id: str, key: str) -> MCPResponse: ...
