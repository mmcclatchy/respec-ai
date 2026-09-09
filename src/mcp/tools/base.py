from abc import ABC, abstractmethod
from typing import ClassVar

from src.models.base import MCPModel
from src.models.phase import Phase
from src.utils.enums import LoopStatus
from src.utils.errors import PhaseNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager
from src.utils.state_manager.base import FROZEN_DISCARD_WARNING, FROZEN_FIELD_DEFAULTS, FROZEN_PHASES_FIELDS


def with_discard_warning(message: str, discarded: list[str]) -> str:
    if not discarded:
        return message

    return (
        f'{message}\n'
        f'{FROZEN_DISCARD_WARNING} ({", ".join(discarded)}). '
        f'These fields are set once at iteration 0 and preserved thereafter; '
        f'the stored phase still holds its previous values for them.'
    )


class DocumentToolsInterface(ABC):
    document_model: ClassVar[type[MCPModel]]

    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def discarded_frozen_fields(
        self, plan_name: str, phase: Phase, allow_frozen_field_edits: bool = False
    ) -> list[str]:
        """Report which frozen Overview fields a pending write will not change.

        The state managers preserve frozen fields silently and still return success, so
        without this the caller cannot tell a stored edit from a discarded one (F1b).
        Probes the LIVE phase because that is exactly the row store_phase preserves from.
        """
        if allow_frozen_field_edits:
            return []

        try:
            existing = await self.state.get_phase(plan_name, phase.phase_name)
        except PhaseNotFoundError:
            return []

        existing_data = existing.model_dump()
        incoming = phase.model_dump()

        return [
            field
            for field in FROZEN_PHASES_FIELDS
            if existing_data[field] != FROZEN_FIELD_DEFAULTS[field] and incoming[field] != existing_data[field]
        ]

    async def validate(self, content: str) -> MCPResponse:
        issues = self.document_model.find_content_loss(content)
        if not issues:
            return MCPResponse(id='validate', status=LoopStatus.COMPLETED, message='No content loss detected.')

        message = '\n'.join([f'Content loss detected in {len(issues)} heading(s):', *[f'- {i}' for i in issues]])
        return MCPResponse(id='validate', status=LoopStatus.USER_INPUT, message=message)

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
