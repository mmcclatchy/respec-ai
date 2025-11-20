from abc import ABC, abstractmethod
from collections import deque

from services.models.roadmap import Roadmap
from services.models.spec import TechnicalSpec
from services.utils.errors import LoopAlreadyExistsError, LoopNotFoundError, RoadmapNotFoundError, SpecNotFoundError
from services.utils.loop_state import LoopState, MCPResponse


class StateManager(ABC):
    # Loop Management
    @abstractmethod
    def add_loop(self, loop: LoopState, project_name: str) -> None: ...

    @abstractmethod
    def get_loop(self, loop_id: str) -> LoopState: ...

    @abstractmethod
    def get_loop_status(self, loop_id: str) -> MCPResponse: ...

    @abstractmethod
    def decide_loop_next_action(self, loop_id: str, current_score: int) -> MCPResponse: ...

    @abstractmethod
    def list_active_loops(self, project_name: str) -> list[MCPResponse]: ...

    @abstractmethod
    def get_objective_feedback(self, loop_id: str) -> MCPResponse: ...

    @abstractmethod
    def store_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse: ...

    # Roadmap Management
    @abstractmethod
    def store_roadmap(self, project_name: str, roadmap: Roadmap) -> str: ...

    @abstractmethod
    def get_roadmap(self, project_name: str) -> Roadmap: ...

    # Unified Spec Management (replaces InitialSpec + TechnicalSpec separation)
    @abstractmethod
    def store_spec(self, project_name: str, spec: TechnicalSpec) -> str: ...

    @abstractmethod
    def get_spec(self, project_name: str, spec_name: str) -> TechnicalSpec: ...

    @abstractmethod
    def list_specs(self, project_name: str) -> list[str]: ...

    @abstractmethod
    def delete_spec(self, project_name: str, spec_name: str) -> bool: ...

    # Loop-to-Spec Mapping (for temporary refinement sessions)
    @abstractmethod
    def link_loop_to_spec(self, loop_id: str, project_name: str, spec_name: str) -> None: ...

    @abstractmethod
    def get_spec_by_loop(self, loop_id: str) -> TechnicalSpec: ...

    @abstractmethod
    def update_spec_by_loop(self, loop_id: str, spec: TechnicalSpec) -> None: ...

    @abstractmethod
    def unlink_loop(self, loop_id: str) -> tuple[str, str] | None: ...


class Queue[T]:
    def __init__(self, maxlen: int) -> None:
        self._deque: deque[T] = deque(maxlen=maxlen)
        self.maxlen = maxlen

    def append(self, item: T) -> T | None:
        # Check if we're at capacity before adding
        dropped_item = None
        if len(self._deque) == self.maxlen:
            # Will be dropped when new item is added
            dropped_item = self._deque[0]

        self._deque.append(item)
        return dropped_item


class InMemoryStateManager(StateManager):
    def __init__(self, max_history_size: int = 10) -> None:
        self._active_loops: dict[str, LoopState] = {}
        self._loop_history: Queue[str] = Queue(maxlen=max_history_size)
        self._objective_feedback: dict[str, str] = {}
        self._roadmaps: dict[str, Roadmap] = {}

        # UNIFIED spec storage (single source of truth)
        self._specs: dict[str, dict[str, TechnicalSpec]] = {}  # project_name -> {spec_name -> TechnicalSpec}

        # Temporary loop-to-spec mapping (for active refinement sessions)
        self._loop_to_spec: dict[str, tuple[str, str]] = {}  # loop_id -> (project_name, spec_name)

    def add_loop(self, loop: LoopState, project_name: str) -> None:
        if loop.id in self._active_loops:
            raise LoopAlreadyExistsError(f'Loop already exists: {loop.id}')
        self._active_loops[loop.id] = loop
        dropped_loop_id = self._loop_history.append(loop.id)
        if dropped_loop_id:
            self._active_loops.pop(dropped_loop_id)

    def get_loop(self, loop_id: str) -> LoopState:
        if loop_id in self._active_loops:
            return self._active_loops[loop_id]
        raise LoopNotFoundError(f'Loop not found: {loop_id}')

    def get_loop_status(self, loop_id: str) -> MCPResponse:
        loop_state = self.get_loop(loop_id)
        return loop_state.mcp_response

    def decide_loop_next_action(self, loop_id: str, current_score: int) -> MCPResponse:
        loop_state = self.get_loop(loop_id)
        loop_state.add_score(current_score)
        return loop_state.decide_next_loop_action()

    def list_active_loops(self, project_name: str) -> list[MCPResponse]:
        return [loop.mcp_response for loop in self._active_loops.values()]

    def get_objective_feedback(self, loop_id: str) -> MCPResponse:
        loop_state = self.get_loop(loop_id)
        feedback = self._objective_feedback.get(loop_id, '')
        return MCPResponse(
            id=loop_id, status=loop_state.status, message=feedback or 'No previous objective feedback found'
        )

    def store_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse:
        loop_state = self.get_loop(loop_id)
        self._objective_feedback[loop_id] = feedback
        return MCPResponse(
            id=loop_id, status=loop_state.status, message=f'Objective feedback stored for loop {loop_id}'
        )

    def store_roadmap(self, project_name: str, roadmap: Roadmap) -> str:
        self._roadmaps[project_name] = roadmap
        return project_name

    def get_roadmap(self, project_name: str) -> Roadmap:
        if project_name not in self._roadmaps:
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')
        return self._roadmaps[project_name]

    # Unified Spec Management (single source of truth)
    def store_spec(self, project_name: str, spec: TechnicalSpec) -> str:
        if project_name not in self._roadmaps:
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        # Store in unified spec storage
        if project_name not in self._specs:
            self._specs[project_name] = {}

        # Auto-increment iteration and version if spec already exists
        if spec.phase_name in self._specs[project_name]:
            existing_spec = self._specs[project_name][spec.phase_name]
            spec.iteration = existing_spec.iteration + 1
            spec.version = existing_spec.version + 1

        self._specs[project_name][spec.phase_name] = spec

        # Add spec to roadmap if not already there (for roadmap listings)
        roadmap = self._roadmaps[project_name]
        roadmap.add_spec(spec)

        return spec.phase_name

    def get_spec(self, project_name: str, spec_name: str) -> TechnicalSpec:
        if project_name not in self._roadmaps:
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        if project_name not in self._specs or spec_name not in self._specs[project_name]:
            raise SpecNotFoundError(f'Spec not found: {spec_name}')

        return self._specs[project_name][spec_name]

    def list_specs(self, project_name: str) -> list[str]:
        if project_name not in self._roadmaps:
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')
        roadmap = self._roadmaps[project_name]
        return [spec.phase_name for spec in roadmap.specs]

    def delete_spec(self, project_name: str, spec_name: str) -> bool:
        if project_name not in self._roadmaps:
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        # Remove from specs storage
        removed_from_specs = False
        if project_name in self._specs and spec_name in self._specs[project_name]:
            del self._specs[project_name][spec_name]
            removed_from_specs = True

        # Remove from roadmap
        roadmap = self._roadmaps[project_name]
        for i, spec in enumerate(roadmap.specs):
            if spec.phase_name == spec_name:
                roadmap.specs.pop(i)
                roadmap.spec_count = len(roadmap.specs)
                return True

        return removed_from_specs

    # Loop-to-Spec Mapping (for temporary refinement sessions)
    def link_loop_to_spec(self, loop_id: str, project_name: str, spec_name: str) -> None:
        if project_name not in self._specs or spec_name not in self._specs[project_name]:
            raise SpecNotFoundError(f'Cannot link loop to non-existent spec: {spec_name}')
        self._loop_to_spec[loop_id] = (project_name, spec_name)

    def get_spec_by_loop(self, loop_id: str) -> TechnicalSpec:
        if loop_id not in self._loop_to_spec:
            raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')
        project_name, spec_name = self._loop_to_spec[loop_id]
        return self.get_spec(project_name, spec_name)

    def update_spec_by_loop(self, loop_id: str, spec: TechnicalSpec) -> None:
        if loop_id not in self._loop_to_spec:
            raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')
        project_name, spec_name = self._loop_to_spec[loop_id]
        self.store_spec(project_name, spec)

    def unlink_loop(self, loop_id: str) -> tuple[str, str] | None:
        return self._loop_to_spec.pop(loop_id, None)
