import logging
from abc import ABC, abstractmethod
from collections import deque

from services.models.project_plan import ProjectPlan
from services.models.roadmap import Roadmap
from services.models.spec import TechnicalSpec
from services.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    ProjectPlanNotFoundError,
    RoadmapNotFoundError,
    SpecNotFoundError,
)
from services.utils.loop_state import LoopState, MCPResponse


logger = logging.getLogger('state_manager')


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

    # Project Plan Management
    @abstractmethod
    def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> str: ...

    @abstractmethod
    def get_project_plan(self, project_name: str) -> ProjectPlan: ...

    @abstractmethod
    def list_project_plans(self) -> list[str]: ...

    @abstractmethod
    def delete_project_plan(self, project_name: str) -> bool: ...


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
        self._project_plans: dict[str, ProjectPlan] = {}  # project_name -> ProjectPlan

        # UNIFIED spec storage (single source of truth)
        self._specs: dict[str, dict[str, TechnicalSpec]] = {}  # project_name -> {spec_name -> TechnicalSpec}

        # Temporary loop-to-spec mapping (for active refinement sessions)
        self._loop_to_spec: dict[str, tuple[str, str]] = {}  # loop_id -> (project_name, spec_name)

        logger.info(f'InMemoryStateManager initialized with max_history_size={max_history_size}')

    def _log_state(self) -> None:
        logger.debug(
            f'State:\n'
            f'  active_loops={len(self._active_loops)}\n'
            f'  roadmaps={len(self._roadmaps)}\n'
            f'  project_plans={len(self._project_plans)}\n'
            f'  projects_with_specs={len(self._specs)}\n'
            f'  loop_to_spec_mappings={len(self._loop_to_spec)}\n'
            f'  objective_feedback={len(self._objective_feedback)}'
        )

    def _log_state_snapshot(self, method_name: str, stage: str) -> None:
        specs_dict = {proj: list(specs.keys()) for proj, specs in self._specs.items()}
        logger.debug(
            f'{method_name} [{stage}] - State snapshot:\n'
            f'  active_loops={list(self._active_loops.keys())}\n'
            f'  roadmaps={list(self._roadmaps.keys())}\n'
            f'  project_plans={list(self._project_plans.keys())}\n'
            f'  specs_by_project={specs_dict}\n'
            f'  loop_to_spec={dict(self._loop_to_spec)}\n'
            f'  objective_feedback_loops={list(self._objective_feedback.keys())}'
        )

    def add_loop(self, loop: LoopState, project_name: str) -> None:
        self._log_state_snapshot('add_loop', 'ENTRY')
        logger.info(f'add_loop: loop_id={loop.id}, project_name={project_name}')
        if loop.id in self._active_loops:
            logger.error(f'add_loop failed: Loop already exists: {loop.id}')
            raise LoopAlreadyExistsError(f'Loop already exists: {loop.id}')
        self._active_loops[loop.id] = loop
        dropped_loop_id = self._loop_history.append(loop.id)
        if dropped_loop_id:
            logger.info(f'add_loop: Dropped oldest loop from history: {dropped_loop_id}')
            self._active_loops.pop(dropped_loop_id)
        self._log_state()
        self._log_state_snapshot('add_loop', 'EXIT')

    def get_loop(self, loop_id: str) -> LoopState:
        self._log_state_snapshot('get_loop', 'ENTRY')
        logger.debug(f'get_loop: loop_id={loop_id}')
        if loop_id in self._active_loops:
            logger.debug(f'get_loop: Found loop {loop_id}')
            self._log_state_snapshot('get_loop', 'EXIT')
            return self._active_loops[loop_id]
        logger.error(f'get_loop failed: Loop not found: {loop_id}')
        raise LoopNotFoundError(f'Loop not found: {loop_id}')

    def get_loop_status(self, loop_id: str) -> MCPResponse:
        self._log_state_snapshot('get_loop_status', 'ENTRY')
        logger.debug(f'get_loop_status: loop_id={loop_id}')
        loop_state = self.get_loop(loop_id)
        response = loop_state.mcp_response
        logger.debug(f'get_loop_status: status={response.status}')
        self._log_state_snapshot('get_loop_status', 'EXIT')
        return response

    def decide_loop_next_action(self, loop_id: str, current_score: int) -> MCPResponse:
        self._log_state_snapshot('decide_loop_next_action', 'ENTRY')
        logger.info(f'decide_loop_next_action: loop_id={loop_id}, current_score={current_score}')
        loop_state = self.get_loop(loop_id)
        loop_state.add_score(current_score)
        response = loop_state.decide_next_loop_action()
        logger.info(f'decide_loop_next_action: decision={response.status}, message={response.message[:100]}')
        self._log_state_snapshot('decide_loop_next_action', 'EXIT')
        return response

    def list_active_loops(self, project_name: str) -> list[MCPResponse]:
        self._log_state_snapshot('list_active_loops', 'ENTRY')
        logger.debug(f'list_active_loops: project_name={project_name}')
        loops = [loop.mcp_response for loop in self._active_loops.values()]
        logger.debug(f'list_active_loops: Found {len(loops)} active loops')
        self._log_state_snapshot('list_active_loops', 'EXIT')
        return loops

    def get_objective_feedback(self, loop_id: str) -> MCPResponse:
        self._log_state_snapshot('get_objective_feedback', 'ENTRY')
        logger.debug(f'get_objective_feedback: loop_id={loop_id}')
        loop_state = self.get_loop(loop_id)
        feedback = self._objective_feedback.get(loop_id, '')
        has_feedback = bool(feedback)
        logger.debug(f'get_objective_feedback: has_feedback={has_feedback}')
        self._log_state_snapshot('get_objective_feedback', 'EXIT')
        return MCPResponse(
            id=loop_id, status=loop_state.status, message=feedback or 'No previous objective feedback found'
        )

    def store_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse:
        self._log_state_snapshot('store_objective_feedback', 'ENTRY')
        logger.info(f'store_objective_feedback: loop_id={loop_id}, feedback_length={len(feedback)}')
        logger.debug(f'store_objective_feedback: feedback_preview={feedback[:200]}...')
        loop_state = self.get_loop(loop_id)
        self._objective_feedback[loop_id] = feedback
        self._log_state()
        self._log_state_snapshot('store_objective_feedback', 'EXIT')
        return MCPResponse(
            id=loop_id, status=loop_state.status, message=f'Objective feedback stored for loop {loop_id}'
        )

    def store_roadmap(self, project_name: str, roadmap: Roadmap) -> str:
        self._log_state_snapshot('store_roadmap', 'ENTRY')
        logger.info(
            f'store_roadmap: project_name={project_name}, '
            f'roadmap_title={roadmap.project_name}, '
            f'spec_count={roadmap.spec_count}'
        )
        self._roadmaps[project_name] = roadmap
        self._log_state()
        self._log_state_snapshot('store_roadmap', 'EXIT')
        return project_name

    def get_roadmap(self, project_name: str) -> Roadmap:
        self._log_state_snapshot('get_roadmap', 'ENTRY')
        logger.debug(f'get_roadmap: project_name={project_name}')
        if project_name not in self._roadmaps:
            logger.error(f'get_roadmap failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')
        roadmap = self._roadmaps[project_name]
        logger.debug(f'get_roadmap: Found roadmap {roadmap.project_name} with {roadmap.spec_count} specs')
        self._log_state_snapshot('get_roadmap', 'EXIT')
        return roadmap

    # Unified Spec Management (single source of truth)
    def store_spec(self, project_name: str, spec: TechnicalSpec) -> str:
        self._log_state_snapshot('store_spec', 'ENTRY')
        logger.info(
            f'store_spec: project_name={project_name}, '
            f'spec_name={spec.phase_name}, '
            f'iteration={spec.iteration}, '
            f'version={spec.version}'
        )
        if project_name not in self._roadmaps:
            logger.error(f'store_spec failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        # Store in unified spec storage
        if project_name not in self._specs:
            self._specs[project_name] = {}

        # Auto-increment iteration and version if spec already exists
        is_update = spec.phase_name in self._specs[project_name]
        if is_update:
            existing_spec = self._specs[project_name][spec.phase_name]
            old_iteration = existing_spec.iteration
            old_version = existing_spec.version
            spec.iteration = existing_spec.iteration + 1
            spec.version = existing_spec.version + 1
            logger.info(
                f'store_spec: Updating existing spec - '
                f'iteration: {old_iteration} -> {spec.iteration}, '
                f'version: {old_version} -> {spec.version}'
            )

        self._specs[project_name][spec.phase_name] = spec

        # Add spec to roadmap if not already there (for roadmap listings)
        roadmap = self._roadmaps[project_name]
        roadmap.add_spec(spec)

        self._log_state()
        logger.info(f'store_spec: Successfully stored spec {spec.phase_name} for project {project_name}')
        self._log_state_snapshot('store_spec', 'EXIT')
        return spec.phase_name

    def get_spec(self, project_name: str, spec_name: str) -> TechnicalSpec:
        self._log_state_snapshot('get_spec', 'ENTRY')
        logger.debug(f'get_spec: project_name={project_name}, spec_name={spec_name}')
        if project_name not in self._roadmaps:
            logger.error(f'get_spec failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        if project_name not in self._specs or spec_name not in self._specs[project_name]:
            logger.error(f'get_spec failed: Spec not found: {spec_name} in project {project_name}')
            raise SpecNotFoundError(f'Spec not found: {spec_name}')

        spec = self._specs[project_name][spec_name]
        logger.debug(f'get_spec: Found spec {spec_name} (iteration={spec.iteration}, version={spec.version})')
        self._log_state_snapshot('get_spec', 'EXIT')
        return spec

    def list_specs(self, project_name: str) -> list[str]:
        self._log_state_snapshot('list_specs', 'ENTRY')
        logger.debug(f'list_specs: project_name={project_name}')

        if project_name not in self._roadmaps:
            logger.error(f'list_specs failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        if project_name not in self._specs:
            logger.debug(f'list_specs: No specs found for project: {project_name}')
            self._log_state_snapshot('list_specs', 'EXIT')
            return []

        spec_names = list(self._specs[project_name].keys())
        logger.debug(f'list_specs: Found {len(spec_names)} specs: {spec_names}')
        self._log_state_snapshot('list_specs', 'EXIT')
        return spec_names

    def delete_spec(self, project_name: str, spec_name: str) -> bool:
        self._log_state_snapshot('delete_spec', 'ENTRY')
        logger.info(f'delete_spec: project_name={project_name}, spec_name={spec_name}')
        if project_name not in self._roadmaps:
            logger.error(f'delete_spec failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        # Remove from specs storage
        removed_from_specs = False
        if project_name in self._specs and spec_name in self._specs[project_name]:
            del self._specs[project_name][spec_name]
            removed_from_specs = True
            logger.info(f'delete_spec: Removed {spec_name} from specs storage')

        # Remove from roadmap
        roadmap = self._roadmaps[project_name]
        for i, spec in enumerate(roadmap.specs):
            if spec.phase_name == spec_name:
                roadmap.specs.pop(i)
                roadmap.spec_count = len(roadmap.specs)
                logger.info(f'delete_spec: Removed {spec_name} from roadmap (new count: {roadmap.spec_count})')
                self._log_state()
                self._log_state_snapshot('delete_spec', 'EXIT')
                return True

        logger.warning(f'delete_spec: Spec {spec_name} not found in roadmap, removed_from_specs={removed_from_specs}')
        self._log_state()
        self._log_state_snapshot('delete_spec', 'EXIT')
        return removed_from_specs

    # Loop-to-Spec Mapping (for temporary refinement sessions)
    def link_loop_to_spec(self, loop_id: str, project_name: str, spec_name: str) -> None:
        self._log_state_snapshot('link_loop_to_spec', 'ENTRY')
        logger.info(f'link_loop_to_spec: loop_id={loop_id}, project_name={project_name}, spec_name={spec_name}')
        if project_name not in self._specs or spec_name not in self._specs[project_name]:
            logger.error(f'link_loop_to_spec failed: Cannot link loop to non-existent spec: {spec_name}')
            raise SpecNotFoundError(f'Cannot link loop to non-existent spec: {spec_name}')
        self._loop_to_spec[loop_id] = (project_name, spec_name)
        self._log_state()
        self._log_state_snapshot('link_loop_to_spec', 'EXIT')

    def get_spec_by_loop(self, loop_id: str) -> TechnicalSpec:
        self._log_state_snapshot('get_spec_by_loop', 'ENTRY')
        logger.debug(f'get_spec_by_loop: loop_id={loop_id}')
        if loop_id not in self._loop_to_spec:
            logger.error(f'get_spec_by_loop failed: Loop not linked to any spec: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')
        project_name, spec_name = self._loop_to_spec[loop_id]
        logger.debug(f'get_spec_by_loop: Loop {loop_id} linked to spec {spec_name} in project {project_name}')
        self._log_state_snapshot('get_spec_by_loop', 'EXIT')
        return self.get_spec(project_name, spec_name)

    def update_spec_by_loop(self, loop_id: str, spec: TechnicalSpec) -> None:
        self._log_state_snapshot('update_spec_by_loop', 'ENTRY')
        logger.info(f'update_spec_by_loop: loop_id={loop_id}, spec_name={spec.phase_name}')
        if loop_id not in self._loop_to_spec:
            logger.error(f'update_spec_by_loop failed: Loop not linked to any spec: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')
        project_name, spec_name = self._loop_to_spec[loop_id]
        logger.debug(f'update_spec_by_loop: Updating spec {spec_name} in project {project_name}')
        self.store_spec(project_name, spec)
        self._log_state_snapshot('update_spec_by_loop', 'EXIT')

    def unlink_loop(self, loop_id: str) -> tuple[str, str] | None:
        self._log_state_snapshot('unlink_loop', 'ENTRY')
        logger.info(f'unlink_loop: loop_id={loop_id}')
        result = self._loop_to_spec.pop(loop_id, None)
        if result:
            project_name, spec_name = result
            logger.info(f'unlink_loop: Unlinked loop {loop_id} from spec {spec_name} in project {project_name}')
        else:
            logger.warning(f'unlink_loop: Loop {loop_id} was not linked to any spec')
        self._log_state()
        self._log_state_snapshot('unlink_loop', 'EXIT')
        return result

    # Project Plan Management
    def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> str:
        self._log_state_snapshot('store_project_plan', 'ENTRY')
        logger.info(f'store_project_plan: project_name={project_name}')
        self._project_plans[project_name] = project_plan
        self._log_state()
        self._log_state_snapshot('store_project_plan', 'EXIT')
        return project_name

    def get_project_plan(self, project_name: str) -> ProjectPlan:
        self._log_state_snapshot('get_project_plan', 'ENTRY')
        logger.debug(f'get_project_plan: project_name={project_name}')
        if project_name not in self._project_plans:
            logger.error(f'get_project_plan failed: Project plan not found for project: {project_name}')
            raise ProjectPlanNotFoundError(f'Project plan not found for project: {project_name}')
        project_plan = self._project_plans[project_name]
        logger.debug(f'get_project_plan: Found project plan for {project_name}')
        self._log_state_snapshot('get_project_plan', 'EXIT')
        return project_plan

    def list_project_plans(self) -> list[str]:
        self._log_state_snapshot('list_project_plans', 'ENTRY')
        logger.debug('list_project_plans: Listing all project plans')
        plan_names = list(self._project_plans.keys())
        logger.debug(f'list_project_plans: Found {len(plan_names)} project plans: {plan_names}')
        self._log_state_snapshot('list_project_plans', 'EXIT')
        return plan_names

    def delete_project_plan(self, project_name: str) -> bool:
        self._log_state_snapshot('delete_project_plan', 'ENTRY')
        logger.info(f'delete_project_plan: project_name={project_name}')
        if project_name not in self._project_plans:
            logger.error(f'delete_project_plan failed: Project plan not found for project: {project_name}')
            raise ProjectPlanNotFoundError(f'Project plan not found for project: {project_name}')
        del self._project_plans[project_name]
        logger.info(f'delete_project_plan: Deleted project plan for {project_name}')
        self._log_state()
        self._log_state_snapshot('delete_project_plan', 'EXIT')
        return True
