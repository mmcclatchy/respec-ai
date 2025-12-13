import logging
import re
from abc import ABC, abstractmethod
from typing import TypeVar

from src.models.phase import Phase
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.utils.loop_state import LoopState, MCPResponse


logger = logging.getLogger('state_manager')

T = TypeVar('T')

FROZEN_PHASES_FIELDS = ('objectives', 'scope', 'dependencies', 'deliverables')


def normalize_phase_name(phase_name: str) -> str:
    """
    Normalize phase name to lowercase-kebab-case for consistent storage/retrieval.

    Examples:
        "Phase 1 - Foundation" -> "phase-1-foundation"
        "phase-1-foundation" -> "phase-1-foundation"
        "PHASE_1_FOUNDATION" -> "phase-1-foundation"

    Args:
        phase_name: Original phase name from user or markdown title

    Returns:
        Normalized kebab-case phase name
    """

    # Convert to lowercase
    normalized = phase_name.lower()
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
    async def decide_loop_next_action(self, loop_id: str) -> MCPResponse: ...

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
    async def get_roadmap_phases(self, project_name: str) -> list[Phase]: ...

    @abstractmethod
    async def mark_phases_inactive(self, project_name: str) -> int: ...

    # Unified Phase Management (replaces InitialSpec + Phase separation)
    @abstractmethod
    async def store_phase(self, project_name: str, phase: Phase) -> str: ...

    @abstractmethod
    async def update_phase(self, project_name: str, phase_name: str, updated_phase: Phase) -> str:
        """
        MUST not mutate the following fields:
            - objectives
            - scope
            - dependencies
            - deliverables
        """
        ...

    @abstractmethod
    async def get_phase(self, project_name: str, phase_name: str) -> Phase: ...

    @abstractmethod
    async def list_phases(self, project_name: str) -> list[str]: ...

    # Loop-to-Spec Mapping (for temporary refinement sessions)
    @abstractmethod
    async def link_loop_to_phase(self, loop_id: str, project_name: str, phase_name: str) -> None: ...

    @abstractmethod
    async def get_phase_by_loop(self, loop_id: str) -> Phase: ...

    @abstractmethod
    async def update_phase_by_loop(self, loop_id: str, phase: Phase) -> None: ...

    @abstractmethod
    async def unlink_loop(self, loop_id: str) -> tuple[str, str] | None: ...

    @abstractmethod
    async def resolve_phase_name(self, project_name: str, partial_name: str) -> tuple[str | None, list[str]]: ...

    @abstractmethod
    async def delete_phase(self, project_name: str, phase_name: str) -> bool:
        """Mark a specific phase as inactive (soft delete).

        This maintains backward compatibility while using the inactive flag approach.
        Returns True if phase was found and marked inactive, False otherwise.
        """
        ...

    # Task Management
    @abstractmethod
    async def store_task(self, phase_path: str, task: Task) -> str: ...

    @abstractmethod
    async def get_task(self, phase_path: str, task_name: str) -> Task: ...

    @abstractmethod
    async def list_tasks(self, phase_path: str) -> list[str]: ...

    @abstractmethod
    async def delete_task(self, phase_path: str, task_name: str) -> bool: ...

    @abstractmethod
    async def link_loop_to_task(self, loop_id: str, phase_path: str, task_name: str) -> None: ...

    @abstractmethod
    async def get_task_by_loop(self, loop_id: str) -> Task: ...

    @abstractmethod
    async def update_task_by_loop(self, loop_id: str, task: Task) -> None: ...

    # Project Plan Management
    @abstractmethod
    async def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> str: ...

    @abstractmethod
    async def get_project_plan(self, project_name: str) -> ProjectPlan: ...

    @abstractmethod
    async def list_project_plans(self) -> list[str]: ...

    @abstractmethod
    async def delete_project_plan(self, project_name: str) -> bool: ...

    # Generic Document Management (for Phase, Task, CompletionReport)
    @abstractmethod
    async def store_document(self, doc_type: str, path: str, content: str) -> str: ...

    @abstractmethod
    async def get_document(self, doc_type: str, path: str) -> str: ...

    @abstractmethod
    async def get_document_by_loop(self, loop_id: str) -> tuple[str, str]:
        """
        Get document by loop_id.

        Returns:
            Tuple of (doc_type, content_markdown)
        """
        ...

    @abstractmethod
    async def list_documents(self, doc_type: str, parent_path: str | None = None) -> list[str]: ...

    @abstractmethod
    async def update_document(self, doc_type: str, path: str, content: str) -> str: ...

    @abstractmethod
    async def delete_document(self, doc_type: str, path: str) -> bool: ...

    @abstractmethod
    async def link_loop_to_document(self, loop_id: str, doc_type: str, path: str) -> None: ...
