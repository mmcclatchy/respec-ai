import logging
import re
from abc import ABC, abstractmethod
from typing import TypeVar

from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec
from src.utils.loop_state import LoopState, MCPResponse


logger = logging.getLogger('state_manager')

T = TypeVar('T')

FROZEN_SPEC_FIELDS = ('objectives', 'scope', 'dependencies', 'deliverables')


def normalize_spec_name(spec_name: str) -> str:
    """
    Normalize spec name to lowercase-kebab-case for consistent storage/retrieval.

    Examples:
        "Phase 1 - Foundation" -> "phase-1-foundation"
        "phase-1-foundation" -> "phase-1-foundation"
        "PHASE_1_FOUNDATION" -> "phase-1-foundation"

    Args:
        spec_name: Original spec name from user or markdown title

    Returns:
        Normalized kebab-case spec name
    """

    # Convert to lowercase
    normalized = spec_name.lower()
    # Replace spaces and underscores with hyphens
    normalized = re.sub(r'[\s_]+', '-', normalized)
    # Remove any characters that aren't alphanumeric or hyphens
    normalized = re.sub(r'[^a-z0-9-]', '', normalized)
    # Collapse multiple hyphens
    normalized = re.sub(r'-+', '-', normalized)
    # Strip leading/trailing hyphens
    normalized = normalized.strip('-')
    return normalized


class StateManager(ABC):
    # Loop Management
    @abstractmethod
    async def add_loop(self, loop: LoopState, project_name: str) -> None: ...

    @abstractmethod
    async def get_loop(self, loop_id: str) -> LoopState: ...

    @abstractmethod
    async def get_loop_status(self, loop_id: str) -> MCPResponse: ...

    @abstractmethod
    async def decide_loop_next_action(self, loop_id: str, current_score: int) -> MCPResponse: ...

    @abstractmethod
    async def list_active_loops(self, project_name: str) -> list[MCPResponse]: ...

    @abstractmethod
    async def get_objective_feedback(self, loop_id: str) -> MCPResponse: ...

    @abstractmethod
    async def store_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse: ...

    # Roadmap Management
    @abstractmethod
    async def store_roadmap(self, project_name: str, roadmap: Roadmap) -> str: ...

    @abstractmethod
    async def get_roadmap(self, project_name: str) -> Roadmap: ...

    @abstractmethod
    async def get_roadmap_specs(self, project_name: str) -> list[TechnicalSpec]: ...

    # Unified Spec Management (replaces InitialSpec + TechnicalSpec separation)
    @abstractmethod
    async def store_spec(self, project_name: str, spec: TechnicalSpec) -> str: ...

    @abstractmethod
    async def update_spec(self, project_name: str, spec_name: str, updated_spec: TechnicalSpec) -> str:
        """
        MUST not mutate the following fields:
            - objectives
            - scope
            - dependencies
            - deliverables
        """
        ...

    @abstractmethod
    async def get_spec(self, project_name: str, spec_name: str) -> TechnicalSpec: ...

    @abstractmethod
    async def list_specs(self, project_name: str) -> list[str]: ...

    @abstractmethod
    async def resolve_spec_name(self, project_name: str, partial_name: str) -> tuple[str | None, list[str]]: ...

    @abstractmethod
    async def delete_spec(self, project_name: str, spec_name: str) -> bool: ...

    # Loop-to-Spec Mapping (for temporary refinement sessions)
    @abstractmethod
    async def link_loop_to_spec(self, loop_id: str, project_name: str, spec_name: str) -> None: ...

    @abstractmethod
    async def get_spec_by_loop(self, loop_id: str) -> TechnicalSpec: ...

    @abstractmethod
    async def update_spec_by_loop(self, loop_id: str, spec: TechnicalSpec) -> None: ...

    @abstractmethod
    async def unlink_loop(self, loop_id: str) -> tuple[str, str] | None: ...

    # Project Plan Management
    @abstractmethod
    async def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> str: ...

    @abstractmethod
    async def get_project_plan(self, project_name: str) -> ProjectPlan: ...

    @abstractmethod
    async def list_project_plans(self) -> list[str]: ...

    @abstractmethod
    async def delete_project_plan(self, project_name: str) -> bool: ...
