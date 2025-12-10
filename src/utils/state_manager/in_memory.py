from collections import deque
from typing import Generic, TypeVar

from src.models.phase import Phase
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    ProjectPlanNotFoundError,
    RoadmapNotFoundError,
    SpecNotFoundError,
)
from src.utils.loop_state import LoopState, MCPResponse

from .base import FROZEN_SPEC_FIELDS, StateManager, logger, normalize_spec_name


T = TypeVar('T')


class Queue(Generic[T]):
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
        self._specs: dict[str, dict[str, Phase]] = {}  # project_name -> {spec_name -> Phase}

        # Temporary loop-to-spec mapping (for active refinement sessions)
        self._loop_to_spec: dict[str, tuple[str, str]] = {}  # loop_id -> (project_name, spec_name)

        # Generic document storage (for Phase, Task, CompletionReport with hierarchical paths)
        self._documents: dict[str, str] = {}  # "doc_type/path" -> markdown_content

        # Temporary loop-to-document mapping (for generic document refinement sessions)
        self._loop_to_document: dict[str, tuple[str, str]] = {}  # loop_id -> (doc_type, path)

        # Task storage (phase_path -> {task_name -> Task})
        self._tasks: dict[str, dict[str, Task]] = {}

        # Temporary loop-to-task mapping (for task refinement sessions)
        self._loop_to_task: dict[str, tuple[str, str]] = {}  # loop_id -> (phase_path, task_name)

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

    async def add_loop(self, loop: LoopState, project_name: str) -> None:
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

    async def get_loop(self, loop_id: str) -> LoopState:
        self._log_state_snapshot('get_loop', 'ENTRY')
        logger.debug(f'get_loop: loop_id={loop_id}')
        if loop_id in self._active_loops:
            logger.debug(f'get_loop: Found loop {loop_id}')
            self._log_state_snapshot('get_loop', 'EXIT')
            return self._active_loops[loop_id]
        logger.error(f'get_loop failed: Loop not found: {loop_id}')
        raise LoopNotFoundError(f'Loop not found: {loop_id}')

    async def get_loop_status(self, loop_id: str) -> MCPResponse:
        self._log_state_snapshot('get_loop_status', 'ENTRY')
        logger.debug(f'get_loop_status: loop_id={loop_id}')
        loop_state = await self.get_loop(loop_id)
        response = loop_state.mcp_response
        logger.debug(f'get_loop_status: status={response.status}')
        self._log_state_snapshot('get_loop_status', 'EXIT')
        return response

    async def decide_loop_next_action(self, loop_id: str) -> MCPResponse:
        self._log_state_snapshot('decide_loop_next_action', 'ENTRY')
        logger.info(f'decide_loop_next_action: loop_id={loop_id} (retrieving score from feedback internally)')
        loop_state = await self.get_loop(loop_id)

        # Retrieve latest score from stored critic feedback
        if not loop_state.feedback_history:
            raise ValueError(
                f'No feedback available for loop {loop_id} - cannot make decision without quality assessment'
            )

        latest_feedback = loop_state.feedback_history[-1]
        current_score = latest_feedback.overall_score
        logger.info(
            f'decide_loop_next_action: extracted score {current_score} from latest feedback (iteration {latest_feedback.iteration})'
        )

        loop_state.add_score(current_score)
        response = loop_state.decide_next_loop_action()
        logger.info(f'decide_loop_next_action: decision={response.status}, message={response.message[:100]}')
        self._log_state_snapshot('decide_loop_next_action', 'EXIT')
        return response

    async def list_active_loops(self, project_name: str) -> list[MCPResponse]:
        self._log_state_snapshot('list_active_loops', 'ENTRY')
        logger.debug(f'list_active_loops: project_name={project_name}')
        loops = [loop.mcp_response for loop in self._active_loops.values()]
        logger.debug(f'list_active_loops: Found {len(loops)} active loops')
        self._log_state_snapshot('list_active_loops', 'EXIT')
        return loops

    async def get_objective_feedback(self, loop_id: str) -> MCPResponse:
        self._log_state_snapshot('get_objective_feedback', 'ENTRY')
        logger.debug(f'get_objective_feedback: loop_id={loop_id}')
        loop_state = await self.get_loop(loop_id)
        feedback = self._objective_feedback.get(loop_id, '')
        has_feedback = bool(feedback)
        logger.debug(f'get_objective_feedback: has_feedback={has_feedback}')
        self._log_state_snapshot('get_objective_feedback', 'EXIT')
        return MCPResponse(
            id=loop_id, status=loop_state.status, message=feedback or 'No previous objective feedback found'
        )

    async def store_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse:
        self._log_state_snapshot('store_objective_feedback', 'ENTRY')
        logger.info(f'store_objective_feedback: loop_id={loop_id}, feedback_length={len(feedback)}')
        logger.debug(f'store_objective_feedback: feedback_preview={feedback[:200]}...')
        loop_state = await self.get_loop(loop_id)
        self._objective_feedback[loop_id] = feedback
        self._log_state()
        self._log_state_snapshot('store_objective_feedback', 'EXIT')
        return MCPResponse(
            id=loop_id, status=loop_state.status, message=f'Objective feedback stored for loop {loop_id}'
        )

    async def store_roadmap(self, project_name: str, roadmap: Roadmap) -> str:
        self._log_state_snapshot('store_roadmap', 'ENTRY')
        logger.info(f'store_roadmap: project_name={project_name}, roadmap_title={roadmap.project_name}')
        self._roadmaps[project_name] = roadmap

        self._log_state()
        self._log_state_snapshot('store_roadmap', 'EXIT')
        return project_name

    async def get_roadmap(self, project_name: str) -> Roadmap:
        self._log_state_snapshot('get_roadmap', 'ENTRY')
        logger.debug(f'get_roadmap: project_name={project_name}')
        if project_name not in self._roadmaps:
            logger.error(f'get_roadmap failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')
        roadmap = self._roadmaps[project_name]
        logger.debug(f'get_roadmap: Found roadmap {roadmap.project_name}')
        self._log_state_snapshot('get_roadmap', 'EXIT')
        return roadmap

    async def get_roadmap_specs(self, project_name: str) -> list[Phase]:
        self._log_state_snapshot('get_roadmap_specs', 'ENTRY')
        logger.debug(f'get_roadmap_specs: project_name={project_name}')

        if project_name not in self._roadmaps:
            logger.error(f'get_roadmap_specs failed: Roadmap not found for project: {project_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

        specs = list(self._specs.get(project_name, {}).values())
        logger.debug(f'get_roadmap_specs: Found {len(specs)} specs for project {project_name}')
        self._log_state_snapshot('get_roadmap_specs', 'EXIT')
        return specs

    # Unified Spec Management (single source of truth)
    async def store_spec(self, project_name: str, spec: Phase) -> str:
        self._log_state_snapshot('store_spec', 'ENTRY')
        logger.info(
            f'store_spec: project_name={project_name}, '
            f'spec_name={spec.phase_name}, '
            f'iteration={spec.iteration}, '
            f'version={spec.version}'
        )

        # Store in unified spec storage - initialize project storage if needed
        if project_name not in self._specs:
            self._specs[project_name] = {}

        # Normalize spec name for consistent storage
        normalized_name = normalize_spec_name(spec.phase_name)
        logger.debug(f'store_spec: Normalized "{spec.phase_name}" -> "{normalized_name}"')

        # Auto-increment iteration and version if spec already exists
        # Also preserve frozen fields (objectives, scope, dependencies, deliverables)
        is_update = normalized_name in self._specs[project_name]
        if is_update:
            existing_spec = self._specs[project_name][normalized_name]
            existing_data = existing_spec.model_dump()
            new_data = spec.model_dump()

            frozen_fields = {field: existing_data[field] for field in FROZEN_SPEC_FIELDS}

            spec = Phase(
                **{
                    **new_data,
                    **frozen_fields,
                    'iteration': existing_data['iteration'] + 1,
                    'version': existing_data['version'] + 1,
                }
            )
            logger.info(
                f'store_spec: Updating existing spec - '
                f'iteration: {existing_data["iteration"]} -> {spec.iteration}, '
                f'version: {existing_data["version"]} -> {spec.version}, '
                f'frozen fields preserved'
            )

        self._specs[project_name][normalized_name] = spec

        self._log_state()
        logger.info(f'store_spec: Successfully stored spec {spec.phase_name} for project {project_name}')
        self._log_state_snapshot('store_spec', 'EXIT')
        return spec.phase_name

    async def update_spec(self, project_name: str, spec_name: str, updated_spec: Phase) -> str:
        self._log_state_snapshot('update_spec', 'ENTRY')
        logger.info(
            f'update_spec: project_name={project_name}, '
            f'spec_name={spec_name}, '
            f'updated_iteration={updated_spec.iteration}, '
            f'updated_version={updated_spec.version}'
        )

        # Get existing spec to preserve frozen fields
        existing_spec = await self.get_spec(project_name, spec_name)

        # Normalize spec name for storage
        normalized_name = normalize_spec_name(spec_name)

        # Create new spec with preserved frozen fields and incremented iteration/version
        existing_data = existing_spec.model_dump()
        new_data = updated_spec.model_dump()

        frozen_fields = {field: existing_data[field] for field in FROZEN_SPEC_FIELDS}

        final_spec = Phase(
            **{
                **new_data,
                **frozen_fields,
                'iteration': existing_data['iteration'] + 1,
                'version': existing_data['version'] + 1,
            }
        )

        logger.info(
            f'update_spec: Preserved frozen fields, '
            f'iteration: {existing_data["iteration"]} -> {final_spec.iteration}, '
            f'version: {existing_data["version"]} -> {final_spec.version}'
        )

        # Store the updated spec
        self._specs[project_name][normalized_name] = final_spec

        self._log_state()
        logger.info(f'update_spec: Successfully updated spec {spec_name} for project {project_name}')
        self._log_state_snapshot('update_spec', 'EXIT')
        return f'Updated spec "{spec_name}" to iteration {final_spec.iteration}, version {final_spec.version}'

    async def get_spec(self, project_name: str, spec_name: str) -> Phase:
        self._log_state_snapshot('get_spec', 'ENTRY')
        logger.debug(f'get_spec: project_name={project_name}, spec_name={spec_name}')

        # Normalize spec name for lookup
        normalized_name = normalize_spec_name(spec_name)
        logger.debug(f'get_spec: Normalized "{spec_name}" -> "{normalized_name}"')

        if project_name not in self._specs or normalized_name not in self._specs[project_name]:
            logger.error(
                f'get_spec failed: Spec not found: {spec_name} (normalized: {normalized_name}) '
                f'in project {project_name}'
            )
            raise SpecNotFoundError(f'Spec not found: {spec_name} in project {project_name}')

        spec = self._specs[project_name][normalized_name]
        logger.debug(
            f'get_spec: Retrieved spec using normalized name "{normalized_name}" (iteration={spec.iteration}, version={spec.version})'
        )
        self._log_state_snapshot('get_spec', 'EXIT')
        return spec

    async def list_specs(self, project_name: str) -> list[str]:
        self._log_state_snapshot('list_specs', 'ENTRY')
        logger.debug(f'list_specs: project_name={project_name}')

        if project_name not in self._specs:
            logger.debug(f'list_specs: No specs found for project: {project_name}')
            self._log_state_snapshot('list_specs', 'EXIT')
            return []

        spec_names = list(self._specs[project_name].keys())
        logger.debug(f'list_specs: Found {len(spec_names)} specs: {spec_names}')
        self._log_state_snapshot('list_specs', 'EXIT')
        return spec_names

    async def resolve_spec_name(self, project_name: str, partial_name: str) -> tuple[str | None, list[str]]:
        self._log_state_snapshot('resolve_spec_name', 'ENTRY')
        logger.debug(f'resolve_spec_name: project_name={project_name}, partial_name={partial_name}')

        # Get all specs for project
        all_specs = await self.list_specs(project_name)

        if not all_specs:
            logger.warning(f'No specs found in project {project_name}')
            return (None, [])

        # Normalize partial name for comparison
        normalized_partial = normalize_spec_name(partial_name)

        # Try exact match first
        if normalized_partial in all_specs:
            logger.info(f'Exact match found: {normalized_partial}')
            return (normalized_partial, [normalized_partial])

        # Fuzzy match: partial contains
        matches = [spec for spec in all_specs if normalized_partial in spec]

        logger.info(f'Found {len(matches)} matches for "{partial_name}": {matches}')

        canonical = matches[0] if len(matches) == 1 else None
        self._log_state_snapshot('resolve_spec_name', 'EXIT')
        return (canonical, matches)

    async def delete_spec(self, project_name: str, spec_name: str) -> bool:
        self._log_state_snapshot('delete_spec', 'ENTRY')
        logger.info(f'delete_spec: project_name={project_name}, spec_name={spec_name}')

        # Normalize spec name for deletion
        normalized_name = normalize_spec_name(spec_name)
        logger.debug(f'delete_spec: Normalized "{spec_name}" -> "{normalized_name}"')

        if project_name not in self._specs or normalized_name not in self._specs[project_name]:
            logger.warning(
                f'delete_spec: Spec not found: {spec_name} (normalized: {normalized_name}) in project {project_name}'
            )
            self._log_state_snapshot('delete_spec', 'EXIT')
            return False

        # Remove from specs storage
        del self._specs[project_name][normalized_name]
        logger.info(f'delete_spec: Removed {spec_name} using normalized name "{normalized_name}" from specs storage')

        self._log_state()
        self._log_state_snapshot('delete_spec', 'EXIT')
        return True

    # Loop-to-Spec Mapping (for temporary refinement sessions)
    async def link_loop_to_spec(self, loop_id: str, project_name: str, spec_name: str) -> None:
        self._log_state_snapshot('link_loop_to_spec', 'ENTRY')
        logger.info(f'link_loop_to_spec: loop_id={loop_id}, project_name={project_name}, spec_name={spec_name}')

        # Normalize spec name for consistent linking
        normalized_name = normalize_spec_name(spec_name)
        logger.debug(f'link_loop_to_spec: Normalized "{spec_name}" -> "{normalized_name}"')

        self._loop_to_spec[loop_id] = (project_name, normalized_name)
        logger.info(f'Linked loop {loop_id} to spec {normalized_name} in project {project_name}')
        self._log_state()
        self._log_state_snapshot('link_loop_to_spec', 'EXIT')

    async def get_spec_by_loop(self, loop_id: str) -> Phase:
        self._log_state_snapshot('get_spec_by_loop', 'ENTRY')
        logger.debug(f'get_spec_by_loop: loop_id={loop_id}')
        if loop_id not in self._loop_to_spec:
            logger.error(f'get_spec_by_loop failed: Loop not linked to any spec: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')
        project_name, spec_name = self._loop_to_spec[loop_id]
        logger.debug(f'get_spec_by_loop: Loop {loop_id} linked to spec {spec_name} in project {project_name}')
        self._log_state_snapshot('get_spec_by_loop', 'EXIT')
        return await self.get_spec(project_name, spec_name)

    async def update_spec_by_loop(self, loop_id: str, spec: Phase) -> None:
        self._log_state_snapshot('update_spec_by_loop', 'ENTRY')
        logger.info(f'update_spec_by_loop: loop_id={loop_id}, spec_name={spec.phase_name}')
        if loop_id not in self._loop_to_spec:
            logger.error(f'update_spec_by_loop failed: Loop not linked to any spec: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')
        project_name, spec_name = self._loop_to_spec[loop_id]
        logger.debug(f'update_spec_by_loop: Updating spec {spec_name} in project {project_name}')
        await self.store_spec(project_name, spec)
        self._log_state_snapshot('update_spec_by_loop', 'EXIT')

    async def unlink_loop(self, loop_id: str) -> tuple[str, str] | None:
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
    async def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> str:
        self._log_state_snapshot('store_project_plan', 'ENTRY')
        logger.info(f'store_project_plan: project_name={project_name}')
        self._project_plans[project_name] = project_plan
        self._log_state()
        self._log_state_snapshot('store_project_plan', 'EXIT')
        return project_name

    async def get_project_plan(self, project_name: str) -> ProjectPlan:
        self._log_state_snapshot('get_project_plan', 'ENTRY')
        logger.debug(f'get_project_plan: project_name={project_name}')
        if project_name not in self._project_plans:
            logger.error(f'get_project_plan failed: Project plan not found for project: {project_name}')
            raise ProjectPlanNotFoundError(f'Project plan not found for project: {project_name}')
        project_plan = self._project_plans[project_name]
        logger.debug(f'get_project_plan: Found project plan for {project_name}')
        self._log_state_snapshot('get_project_plan', 'EXIT')
        return project_plan

    async def list_project_plans(self) -> list[str]:
        self._log_state_snapshot('list_project_plans', 'ENTRY')
        logger.debug('list_project_plans: Listing all project plans')
        plan_names = list(self._project_plans.keys())
        logger.debug(f'list_project_plans: Found {len(plan_names)} project plans: {plan_names}')
        self._log_state_snapshot('list_project_plans', 'EXIT')
        return plan_names

    async def delete_project_plan(self, project_name: str) -> bool:
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

    async def store_document(self, doc_type: str, path: str, content: str) -> str:
        self._log_state_snapshot('store_document', 'ENTRY')
        logger.info(f'store_document: doc_type={doc_type}, path={path}, content_length={len(content)}')

        key = f'{doc_type}/{path}'
        self._documents[key] = content

        logger.info(f'store_document: Stored {doc_type} document at {path}')
        self._log_state()
        self._log_state_snapshot('store_document', 'EXIT')
        return f'Stored {doc_type} document at {path}'

    async def get_document(self, doc_type: str, path: str) -> str:
        self._log_state_snapshot('get_document', 'ENTRY')
        logger.debug(f'get_document: doc_type={doc_type}, path={path}')

        key = f'{doc_type}/{path}'
        if key not in self._documents:
            logger.error(f'get_document failed: Document not found: {key}')
            raise ValueError(f'Document not found: {doc_type} at {path}')

        content = self._documents[key]
        logger.debug(f'get_document: Retrieved {doc_type} document at {path}, content_length={len(content)}')
        self._log_state_snapshot('get_document', 'EXIT')
        return content

    async def get_document_by_loop(self, loop_id: str) -> tuple[str, str]:
        self._log_state_snapshot('get_document_by_loop', 'ENTRY')
        logger.debug(f'get_document_by_loop: loop_id={loop_id}')

        if loop_id not in self._loop_to_document:
            logger.error(f'get_document_by_loop failed: Loop not linked to any document: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any document: {loop_id}')

        doc_type, path = self._loop_to_document[loop_id]
        content = await self.get_document(doc_type, path)

        logger.debug(f'get_document_by_loop: Found {doc_type} document at {path} for loop {loop_id}')
        self._log_state_snapshot('get_document_by_loop', 'EXIT')
        return (doc_type, content)

    async def list_documents(self, doc_type: str, parent_path: str | None = None) -> list[str]:
        self._log_state_snapshot('list_documents', 'ENTRY')
        logger.debug(f'list_documents: doc_type={doc_type}, parent_path={parent_path}')

        matching_paths = []
        prefix = f'{doc_type}/'

        for key in self._documents.keys():
            if not key.startswith(prefix):
                continue

            path = key[len(prefix) :]

            if parent_path:
                if path.startswith(f'{parent_path}/'):
                    matching_paths.append(path)
            else:
                matching_paths.append(path)

        logger.debug(f'list_documents: Found {len(matching_paths)} {doc_type} documents')
        self._log_state_snapshot('list_documents', 'EXIT')
        return matching_paths

    async def update_document(self, doc_type: str, path: str, content: str) -> str:
        self._log_state_snapshot('update_document', 'ENTRY')
        logger.info(f'update_document: doc_type={doc_type}, path={path}, content_length={len(content)}')

        key = f'{doc_type}/{path}'
        if key not in self._documents:
            logger.error(f'update_document failed: Document not found: {key}')
            raise ValueError(f'Document not found: {doc_type} at {path}')

        self._documents[key] = content
        logger.info(f'update_document: Updated {doc_type} document at {path}')
        self._log_state()
        self._log_state_snapshot('update_document', 'EXIT')
        return f'Updated {doc_type} document at {path}'

    async def delete_document(self, doc_type: str, path: str) -> bool:
        self._log_state_snapshot('delete_document', 'ENTRY')
        logger.info(f'delete_document: doc_type={doc_type}, path={path}')

        key = f'{doc_type}/{path}'
        if key not in self._documents:
            logger.warning(f'delete_document: Document not found: {key}')
            self._log_state_snapshot('delete_document', 'EXIT')
            return False

        del self._documents[key]
        logger.info(f'delete_document: Deleted {doc_type} document at {path}')
        self._log_state()
        self._log_state_snapshot('delete_document', 'EXIT')
        return True

    async def link_loop_to_document(self, loop_id: str, doc_type: str, path: str) -> None:
        self._log_state_snapshot('link_loop_to_document', 'ENTRY')
        logger.info(f'link_loop_to_document: loop_id={loop_id}, doc_type={doc_type}, path={path}')

        self._loop_to_document[loop_id] = (doc_type, path)
        logger.info(f'Linked loop {loop_id} to {doc_type} document at {path}')
        self._log_state()
        self._log_state_snapshot('link_loop_to_document', 'EXIT')

    async def store_phase(self, project_name: str, phase: Phase) -> str:
        self._log_state_snapshot('store_phase', 'ENTRY')
        logger.info(
            f'store_phase: project_name={project_name}, '
            f'phase_name={phase.phase_name}, '
            f'iteration={phase.iteration}, '
            f'version={phase.version}'
        )

        if project_name not in self._specs:
            self._specs[project_name] = {}

        normalized_name = normalize_spec_name(phase.phase_name)
        logger.debug(f'store_phase: Normalized "{phase.phase_name}" -> "{normalized_name}"')

        is_update = normalized_name in self._specs[project_name]
        if is_update:
            existing_spec = self._specs[project_name][normalized_name]
            existing_data = existing_spec.model_dump()
            new_data = phase.model_dump()

            frozen_fields = {field: existing_data[field] for field in FROZEN_SPEC_FIELDS}

            phase = Phase(
                **{
                    **new_data,
                    **frozen_fields,
                    'iteration': existing_data['iteration'] + 1,
                    'version': existing_data['version'] + 1,
                }
            )
            logger.info(
                f'store_phase: Updating existing phase - '
                f'iteration: {existing_data["iteration"]} -> {phase.iteration}, '
                f'version: {existing_data["version"]} -> {phase.version}, '
                f'frozen fields preserved'
            )

        self._specs[project_name][normalized_name] = phase

        self._log_state()
        logger.info(f'store_phase: Successfully stored phase {phase.phase_name} for project {project_name}')
        self._log_state_snapshot('store_phase', 'EXIT')
        return phase.phase_name

    async def update_phase(self, project_name: str, phase_name: str, updated_phase: Phase) -> str:
        self._log_state_snapshot('update_phase', 'ENTRY')
        logger.info(
            f'update_phase: project_name={project_name}, '
            f'phase_name={phase_name}, '
            f'updated_iteration={updated_phase.iteration}, '
            f'updated_version={updated_phase.version}'
        )

        existing_phase = await self.get_phase(project_name, phase_name)
        normalized_name = normalize_spec_name(phase_name)

        existing_data = existing_phase.model_dump()
        new_data = updated_phase.model_dump()

        frozen_fields = {field: existing_data[field] for field in FROZEN_SPEC_FIELDS}

        final_phase = Phase(
            **{
                **new_data,
                **frozen_fields,
                'iteration': existing_data['iteration'] + 1,
                'version': existing_data['version'] + 1,
            }
        )

        logger.info(
            f'update_phase: Preserved frozen fields, '
            f'iteration: {existing_data["iteration"]} -> {final_phase.iteration}, '
            f'version: {existing_data["version"]} -> {final_phase.version}'
        )

        self._specs[project_name][normalized_name] = final_phase

        self._log_state()
        logger.info(f'update_phase: Successfully updated phase {phase_name} for project {project_name}')
        self._log_state_snapshot('update_phase', 'EXIT')
        return f'Updated phase "{phase_name}" to iteration {final_phase.iteration}, version {final_phase.version}'

    async def get_phase(self, project_name: str, phase_name: str) -> Phase:
        self._log_state_snapshot('get_phase', 'ENTRY')
        logger.debug(f'get_phase: project_name={project_name}, phase_name={phase_name}')

        normalized_name = normalize_spec_name(phase_name)
        logger.debug(f'get_phase: Normalized "{phase_name}" -> "{normalized_name}"')

        if project_name not in self._specs or normalized_name not in self._specs[project_name]:
            logger.error(
                f'get_phase failed: Phase not found: {phase_name} (normalized: {normalized_name}) '
                f'in project {project_name}'
            )
            raise SpecNotFoundError(f'Phase not found: {phase_name} in project {project_name}')

        phase = self._specs[project_name][normalized_name]
        logger.debug(
            f'get_phase: Retrieved phase using normalized name "{normalized_name}" (iteration={phase.iteration}, version={phase.version})'
        )
        self._log_state_snapshot('get_phase', 'EXIT')
        return phase

    async def list_phases(self, project_name: str) -> list[str]:
        self._log_state_snapshot('list_phases', 'ENTRY')
        logger.debug(f'list_phases: project_name={project_name}')

        if project_name not in self._specs:
            logger.debug(f'list_phases: No phases found for project: {project_name}')
            self._log_state_snapshot('list_phases', 'EXIT')
            return []

        phase_names = list(self._specs[project_name].keys())
        logger.debug(f'list_phases: Found {len(phase_names)} phases: {phase_names}')
        self._log_state_snapshot('list_phases', 'EXIT')
        return phase_names

    async def resolve_phase_name(self, project_name: str, partial_name: str) -> tuple[str | None, list[str]]:
        self._log_state_snapshot('resolve_phase_name', 'ENTRY')
        logger.debug(f'resolve_phase_name: project_name={project_name}, partial_name={partial_name}')

        all_phases = await self.list_phases(project_name)

        if not all_phases:
            logger.warning(f'No phases found in project {project_name}')
            return (None, [])

        normalized_partial = normalize_spec_name(partial_name)

        if normalized_partial in all_phases:
            logger.info(f'Exact match found: {normalized_partial}')
            return (normalized_partial, [normalized_partial])

        matches = [phase for phase in all_phases if normalized_partial in phase]

        logger.info(f'Found {len(matches)} matches for "{partial_name}": {matches}')

        canonical = matches[0] if len(matches) == 1 else None
        self._log_state_snapshot('resolve_phase_name', 'EXIT')
        return (canonical, matches)

    async def delete_phase(self, project_name: str, phase_name: str) -> bool:
        self._log_state_snapshot('delete_phase', 'ENTRY')
        logger.info(f'delete_phase: project_name={project_name}, phase_name={phase_name}')

        normalized_name = normalize_spec_name(phase_name)
        logger.debug(f'delete_phase: Normalized "{phase_name}" -> "{normalized_name}"')

        if project_name not in self._specs or normalized_name not in self._specs[project_name]:
            logger.warning(
                f'delete_phase: Phase not found: {phase_name} (normalized: {normalized_name}) in project {project_name}'
            )
            self._log_state_snapshot('delete_phase', 'EXIT')
            return False

        del self._specs[project_name][normalized_name]
        logger.info(f'delete_phase: Removed {phase_name} using normalized name "{normalized_name}" from phase storage')

        self._log_state()
        self._log_state_snapshot('delete_phase', 'EXIT')
        return True

    async def link_loop_to_phase(self, loop_id: str, project_name: str, phase_name: str) -> None:
        self._log_state_snapshot('link_loop_to_phase', 'ENTRY')
        logger.info(f'link_loop_to_phase: loop_id={loop_id}, project_name={project_name}, phase_name={phase_name}')

        normalized_name = normalize_spec_name(phase_name)
        logger.debug(f'link_loop_to_phase: Normalized "{phase_name}" -> "{normalized_name}"')

        self._loop_to_spec[loop_id] = (project_name, normalized_name)
        logger.info(f'Linked loop {loop_id} to phase {normalized_name} in project {project_name}')
        self._log_state()
        self._log_state_snapshot('link_loop_to_phase', 'EXIT')

    async def get_phase_by_loop(self, loop_id: str) -> Phase:
        self._log_state_snapshot('get_phase_by_loop', 'ENTRY')
        logger.debug(f'get_phase_by_loop: loop_id={loop_id}')
        if loop_id not in self._loop_to_spec:
            logger.error(f'get_phase_by_loop failed: Loop not linked to any phase: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any phase: {loop_id}')
        project_name, phase_name = self._loop_to_spec[loop_id]
        logger.debug(f'get_phase_by_loop: Loop {loop_id} linked to phase {phase_name} in project {project_name}')
        self._log_state_snapshot('get_phase_by_loop', 'EXIT')
        return await self.get_phase(project_name, phase_name)

    async def update_phase_by_loop(self, loop_id: str, phase: Phase) -> None:
        self._log_state_snapshot('update_phase_by_loop', 'ENTRY')
        logger.info(f'update_phase_by_loop: loop_id={loop_id}, phase_name={phase.phase_name}')
        if loop_id not in self._loop_to_spec:
            logger.error(f'update_phase_by_loop failed: Loop not linked to any phase: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any phase: {loop_id}')
        project_name, phase_name = self._loop_to_spec[loop_id]
        logger.debug(f'update_phase_by_loop: Updating phase {phase_name} in project {project_name}')
        await self.store_phase(project_name, phase)
        self._log_state_snapshot('update_phase_by_loop', 'EXIT')

    async def store_task(self, phase_path: str, task: Task) -> str:
        self._log_state_snapshot('store_task', 'ENTRY')
        logger.info(f'store_task: phase_path={phase_path}, task_name={task.name}, iteration={task.iteration}')

        if phase_path not in self._tasks:
            self._tasks[phase_path] = {}

        normalized_name = normalize_spec_name(task.name)
        logger.debug(f'store_task: Normalized "{task.name}" -> "{normalized_name}"')

        self._tasks[phase_path][normalized_name] = task

        logger.info(f'store_task: Successfully stored task {task.name} for phase {phase_path}')
        self._log_state()
        self._log_state_snapshot('store_task', 'EXIT')
        return task.name

    async def get_task(self, phase_path: str, task_name: str) -> Task:
        self._log_state_snapshot('get_task', 'ENTRY')
        logger.debug(f'get_task: phase_path={phase_path}, task_name={task_name}')

        normalized_name = normalize_spec_name(task_name)
        logger.debug(f'get_task: Normalized "{task_name}" -> "{normalized_name}"')

        if phase_path not in self._tasks or normalized_name not in self._tasks[phase_path]:
            logger.error(
                f'get_task failed: Task not found: {task_name} (normalized: {normalized_name}) in phase {phase_path}'
            )
            raise ValueError(f'Task not found: {task_name} in phase {phase_path}')

        task = self._tasks[phase_path][normalized_name]
        logger.debug(f'get_task: Retrieved task {normalized_name} (iteration={task.iteration}, version={task.version})')
        self._log_state_snapshot('get_task', 'EXIT')
        return task

    async def list_tasks(self, phase_path: str) -> list[str]:
        self._log_state_snapshot('list_tasks', 'ENTRY')
        logger.debug(f'list_tasks: phase_path={phase_path}')

        if phase_path not in self._tasks:
            logger.debug(f'list_tasks: No tasks found for phase: {phase_path}')
            self._log_state_snapshot('list_tasks', 'EXIT')
            return []

        task_names = list(self._tasks[phase_path].keys())
        logger.debug(f'list_tasks: Found {len(task_names)} tasks: {task_names}')
        self._log_state_snapshot('list_tasks', 'EXIT')
        return task_names

    async def delete_task(self, phase_path: str, task_name: str) -> bool:
        self._log_state_snapshot('delete_task', 'ENTRY')
        logger.info(f'delete_task: phase_path={phase_path}, task_name={task_name}')

        normalized_name = normalize_spec_name(task_name)
        logger.debug(f'delete_task: Normalized "{task_name}" -> "{normalized_name}"')

        if phase_path not in self._tasks or normalized_name not in self._tasks[phase_path]:
            logger.warning(
                f'delete_task: Task not found: {task_name} (normalized: {normalized_name}) in phase {phase_path}'
            )
            self._log_state_snapshot('delete_task', 'EXIT')
            return False

        del self._tasks[phase_path][normalized_name]
        logger.info(f'delete_task: Removed {task_name} using normalized name "{normalized_name}" from task storage')

        self._log_state()
        self._log_state_snapshot('delete_task', 'EXIT')
        return True

    async def link_loop_to_task(self, loop_id: str, phase_path: str, task_name: str) -> None:
        self._log_state_snapshot('link_loop_to_task', 'ENTRY')
        logger.info(f'link_loop_to_task: loop_id={loop_id}, phase_path={phase_path}, task_name={task_name}')

        normalized_name = normalize_spec_name(task_name)
        logger.debug(f'link_loop_to_task: Normalized "{task_name}" -> "{normalized_name}"')

        self._loop_to_task[loop_id] = (phase_path, normalized_name)
        logger.info(f'Linked loop {loop_id} to task {normalized_name} in phase {phase_path}')
        self._log_state()
        self._log_state_snapshot('link_loop_to_task', 'EXIT')

    async def get_task_by_loop(self, loop_id: str) -> Task:
        self._log_state_snapshot('get_task_by_loop', 'ENTRY')
        logger.debug(f'get_task_by_loop: loop_id={loop_id}')

        if loop_id not in self._loop_to_task:
            logger.error(f'get_task_by_loop failed: Loop not linked to any task: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any task: {loop_id}')

        phase_path, task_name = self._loop_to_task[loop_id]
        logger.debug(f'get_task_by_loop: Loop {loop_id} linked to task {task_name} in phase {phase_path}')
        self._log_state_snapshot('get_task_by_loop', 'EXIT')
        return await self.get_task(phase_path, task_name)

    async def update_task_by_loop(self, loop_id: str, task: Task) -> None:
        self._log_state_snapshot('update_task_by_loop', 'ENTRY')
        logger.info(f'update_task_by_loop: loop_id={loop_id}, task_name={task.name}')

        if loop_id not in self._loop_to_task:
            logger.error(f'update_task_by_loop failed: Loop not linked to any task: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any task: {loop_id}')

        phase_path, task_name = self._loop_to_task[loop_id]
        logger.debug(f'update_task_by_loop: Updating task {task_name} in phase {phase_path}')
        await self.store_task(phase_path, task)
        self._log_state_snapshot('update_task_by_loop', 'EXIT')
