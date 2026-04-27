import logging
from collections import deque
from typing import Generic, TypeVar

from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.models.feedback import ReviewerResult
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    PhaseNotFoundError,
    PlanNotFoundError,
    RoadmapNotFoundError,
)
from src.utils.loop_state import LoopState, MCPResponse

from .base import FROZEN_FIELD_DEFAULTS, FROZEN_PHASES_FIELDS, StateManager, logger, normalize_phase_name


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
        self._user_feedback_entries: dict[str, list[str]] = {}
        self._loop_analysis: dict[str, str] = {}
        self._roadmaps: dict[str, Roadmap] = {}
        self._plans: dict[str, Plan] = {}  # plan_name -> Plan

        # UNIFIED phase storage (single source of truth)
        self._phases: dict[str, dict[str, Phase]] = {}  # plan_name -> {phase_name -> Phase}
        self._inactive_phases: dict[str, dict[str, Phase]] = {}  # plan_name -> {phase_name -> Phase}

        # Temporary loop-to-phase mapping (for active refinement sessions)
        self._loop_to_phase: dict[str, tuple[str, str]] = {}  # loop_id -> (plan_name, phase_name)

        # Task storage (phase_path -> {task_name -> Task})
        self._tasks: dict[str, dict[str, Task]] = {}
        self._inactive_tasks: dict[str, dict[str, Task]] = {}  # phase_path -> {task_name -> Task}

        # Temporary loop-to-task mapping (for task refinement sessions)
        self._loop_to_task: dict[str, tuple[str, str]] = {}  # loop_id -> (phase_path, task_name)

        # Loop-to-plan mapping (for cascading delete)
        self._loop_to_plan: dict[str, str] = {}  # loop_id -> plan_name

        # Review section storage (hierarchical key -> raw markdown)
        self._review_sections: dict[str, str] = {}
        # Structured reviewer results ((loop_id, review_iteration, reviewer_name) -> ReviewerResult)
        self._reviewer_results: dict[tuple[str, int, str], ReviewerResult] = {}

        logger.info(f'InMemoryStateManager initialized with max_history_size={max_history_size}')

    def _cleanup_loop_references(self, loop_id: str) -> None:
        self._active_loops.pop(loop_id, None)
        self._loop_to_plan.pop(loop_id, None)
        self._loop_to_phase.pop(loop_id, None)
        self._loop_to_task.pop(loop_id, None)
        self._objective_feedback.pop(loop_id, None)
        self._user_feedback_entries.pop(loop_id, None)
        self._loop_analysis.pop(loop_id, None)
        reviewer_result_keys = [k for k in self._reviewer_results if k[0] == loop_id]
        for key in reviewer_result_keys:
            self._reviewer_results.pop(key, None)

    def _log_state(self) -> None:
        logger.debug(
            f'State:\n'
            f'  active_loops={len(self._active_loops)}\n'
            f'  roadmaps={len(self._roadmaps)}\n'
            f'  plans={len(self._plans)}\n'
            f'  projects_with_phases={len(self._phases)}\n'
            f'  tasks={len(self._tasks)}\n'
            f'  review_sections={len(self._review_sections)}\n'
            f'  reviewer_results={len(self._reviewer_results)}\n'
            f'  loop_to_phase_mappings={len(self._loop_to_phase)}\n'
            f'  loop_to_plan_mappings={len(self._loop_to_plan)}\n'
            f'  objective_feedback={len(self._objective_feedback)}'
        )

    def _log_state_snapshot(self, method_name: str, stage: str) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return

        phases_dict = {proj: list(phases.keys()) for proj, phases in self._phases.items()}
        inactive_phases_dict = {proj: list(phases.keys()) for proj, phases in self._inactive_phases.items()}
        tasks_dict = {phase_path: list(tasks.keys()) for phase_path, tasks in self._tasks.items()}
        inactive_tasks_dict = {phase_path: list(tasks.keys()) for phase_path, tasks in self._inactive_tasks.items()}
        logger.debug(
            f'{method_name} [{stage}] - State snapshot:\n'
            f'  active_loops={list(self._active_loops.keys())}\n'
            f'  roadmaps={list(self._roadmaps.keys())}\n'
            f'  plans={list(self._plans.keys())}\n'
            f'  phases_by_project={phases_dict}\n'
            f'  inactive_phases_by_project={inactive_phases_dict}\n'
            f'  tasks_by_phase={tasks_dict}\n'
            f'  inactive_tasks_by_phase={inactive_tasks_dict}\n'
            f'  review_sections={list(self._review_sections.keys())}\n'
            f'  reviewer_results={list(self._reviewer_results.keys())}\n'
            f'  loop_to_phase={dict(self._loop_to_phase)}\n'
            f'  loop_to_task={dict(self._loop_to_task)}\n'
            f'  loop_to_plan={dict(self._loop_to_plan)}\n'
            f'  objective_feedback_loops={list(self._objective_feedback.keys())}'
        )

    async def add_loop(self, loop: LoopState, plan_name: str) -> None:
        self._log_state_snapshot('add_loop', 'ENTRY')
        logger.info(f'add_loop: loop_id={loop.id}, plan_name={plan_name}')
        if loop.id in self._active_loops:
            logger.error(f'add_loop failed: Loop already exists: {loop.id}')
            raise LoopAlreadyExistsError(f'Loop already exists: {loop.id}')
        self._active_loops[loop.id] = loop
        self._loop_to_plan[loop.id] = plan_name
        dropped_loop_id = self._loop_history.append(loop.id)
        if dropped_loop_id:
            logger.info(f'add_loop: Dropped oldest loop from history: {dropped_loop_id}')
            self._cleanup_loop_references(dropped_loop_id)
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

    async def save_loop(self, loop_state: LoopState) -> None:
        if loop_state.id not in self._active_loops:
            raise LoopNotFoundError(f'Loop not found: {loop_state.id}')
        self._active_loops[loop_state.id] = loop_state

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
        logger.info(f'decide_loop_next_action: loop_id={loop_id}')
        loop_state = await self.get_loop(loop_id)

        if not loop_state.feedback_history:
            raise ValueError(
                f'No feedback available for loop {loop_id} - cannot make decision without quality assessment'
            )

        response = loop_state.decide_next_loop_action()
        logger.info(f'decide_loop_next_action: decision={response.status}')
        self._log_state_snapshot('decide_loop_next_action', 'EXIT')
        return response

    async def list_active_loops(self, plan_name: str) -> list[MCPResponse]:
        self._log_state_snapshot('list_active_loops', 'ENTRY')
        logger.debug(f'list_active_loops: plan_name={plan_name}')
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

    async def append_user_feedback(self, loop_id: str, feedback_markdown: str) -> None:
        await self.get_loop(loop_id)
        if loop_id not in self._user_feedback_entries:
            self._user_feedback_entries[loop_id] = []
        self._user_feedback_entries[loop_id].append(feedback_markdown)

    async def list_user_feedback(self, loop_id: str) -> list[str]:
        await self.get_loop(loop_id)
        return list(self._user_feedback_entries.get(loop_id, []))

    async def upsert_loop_analysis(self, loop_id: str, analysis: str) -> None:
        await self.get_loop(loop_id)
        self._loop_analysis[loop_id] = analysis

    async def get_loop_analysis(self, loop_id: str) -> str | None:
        await self.get_loop(loop_id)
        return self._loop_analysis.get(loop_id)

    async def store_roadmap(self, plan_name: str, roadmap: Roadmap) -> str:
        self._log_state_snapshot('store_roadmap', 'ENTRY')
        logger.info(f'store_roadmap: plan_name={plan_name}, roadmap_title={roadmap.plan_name}')
        self._roadmaps[plan_name] = roadmap

        self._log_state()
        self._log_state_snapshot('store_roadmap', 'EXIT')
        return plan_name

    async def get_roadmap(self, plan_name: str) -> Roadmap:
        self._log_state_snapshot('get_roadmap', 'ENTRY')
        logger.debug(f'get_roadmap: plan_name={plan_name}')
        if plan_name not in self._roadmaps:
            logger.error(f'get_roadmap failed: Roadmap not found for project: {plan_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {plan_name}')
        roadmap = self._roadmaps[plan_name]
        logger.debug(f'get_roadmap: Found roadmap {roadmap.plan_name}')
        self._log_state_snapshot('get_roadmap', 'EXIT')
        return roadmap

    async def get_roadmap_phases(self, plan_name: str) -> list[Phase]:
        self._log_state_snapshot('get_roadmap_phases', 'ENTRY')
        logger.debug(f'get_roadmap_phases: plan_name={plan_name}')

        if plan_name not in self._roadmaps:
            logger.error(f'get_roadmap_phases failed: Roadmap not found for project: {plan_name}')
            raise RoadmapNotFoundError(f'Roadmap not found for project: {plan_name}')

        phases = list(self._phases.get(plan_name, {}).values())
        logger.debug(f'get_roadmap_phases: Found {len(phases)} phases for project {plan_name}')
        self._log_state_snapshot('get_roadmap_phases', 'EXIT')
        return phases

    async def mark_phases_inactive(self, plan_name: str) -> int:
        """Mark all current active phases for a project as inactive.

        Returns the number of phases marked inactive.
        """
        logger.info(f'mark_phases_inactive: plan_name={plan_name}')

        if plan_name not in self._phases:
            logger.debug(f'mark_phases_inactive: No active phases found for project {plan_name}')
            return 0

        # Move all active phases to inactive
        if plan_name not in self._inactive_phases:
            self._inactive_phases[plan_name] = {}

        active_phases = self._phases[plan_name]
        count = len(active_phases)

        # Move each active phase to inactive (overwrites any existing inactive with same name)
        for phase_name, phase in active_phases.items():
            self._inactive_phases[plan_name][phase_name] = phase
            logger.debug(f'mark_phases_inactive: Moved phase "{phase_name}" to inactive')

        # Clear active phases for this project
        self._phases[plan_name] = {}

        logger.info(f'mark_phases_inactive: Marked {count} phases as inactive for project {plan_name}')
        return count

    # Unified Phase Management (single source of truth)
    async def store_phase(self, plan_name: str, phase: Phase) -> str:
        self._log_state_snapshot('store_phase', 'ENTRY')
        logger.info(
            f'store_phase: plan_name={plan_name}, '
            f'phase_name={phase.phase_name}, '
            f'iteration={phase.iteration}, '
            f'version={phase.version}'
        )

        # Store in unified phase storage - initialize project storage if needed
        if plan_name not in self._phases:
            self._phases[plan_name] = {}

        # Normalize phase name for consistent storage
        normalized_name = normalize_phase_name(phase.phase_name)
        logger.debug(f'store_phase: Normalized "{phase.phase_name}" -> "{normalized_name}"')

        # Auto-increment iteration and version if phase already exists
        # Does NOT preserve frozen fields - this is a full replacement
        is_update = normalized_name in self._phases[plan_name]
        if is_update:
            existing_phase = self._phases[plan_name][normalized_name]
            existing_data = existing_phase.model_dump()
            new_data = phase.model_dump()

            # Only increment iteration and version, NO frozen field preservation
            phase = Phase(
                **{
                    **new_data,
                    'iteration': existing_data['iteration'] + 1,
                    'version': existing_data['version'] + 1,
                }
            )
            logger.info(
                f'store_phase: Updating existing phase - '
                f'iteration: {existing_data["iteration"]} -> {phase.iteration}, '
                f'version: {existing_data["version"]} -> {phase.version}, '
                f'full replacement (no frozen field preservation)'
            )

        self._phases[plan_name][normalized_name] = phase

        self._log_state()
        logger.info(f'store_phase: Successfully stored phase {phase.phase_name} for project {plan_name}')
        self._log_state_snapshot('store_phase', 'EXIT')
        return phase.phase_name

    async def update_phase(self, plan_name: str, phase_name: str, updated_phase: Phase) -> str:
        self._log_state_snapshot('update_phase', 'ENTRY')
        logger.info(
            f'update_phase: plan_name={plan_name}, '
            f'phase_name={phase_name}, '
            f'updated_iteration={updated_phase.iteration}, '
            f'updated_version={updated_phase.version}'
        )

        # Get existing phase to preserve frozen fields
        existing_phase = await self.get_phase(plan_name, phase_name)

        # Normalize phase name for storage
        normalized_name = normalize_phase_name(phase_name)

        # Create new phase with preserved frozen fields and incremented iteration/version
        existing_data = existing_phase.model_dump()
        new_data = updated_phase.model_dump()

        frozen_fields = {
            field: existing_data[field]
            for field in FROZEN_PHASES_FIELDS
            if existing_data[field] != FROZEN_FIELD_DEFAULTS[field]
        }

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

        # Store the updated phase
        self._phases[plan_name][normalized_name] = final_phase

        self._log_state()
        logger.info(f'update_phase: Successfully updated phase {phase_name} for project {plan_name}')
        self._log_state_snapshot('update_phase', 'EXIT')
        return f'Updated phase "{phase_name}" to iteration {final_phase.iteration}, version {final_phase.version}'

    async def get_phase(self, plan_name: str, phase_name: str) -> Phase:
        self._log_state_snapshot('get_phase', 'ENTRY')
        logger.debug(f'get_phase: plan_name={plan_name}, phase_name={phase_name}')

        # Normalize phase name for lookup
        normalized_name = normalize_phase_name(phase_name)
        logger.debug(f'get_phase: Normalized "{phase_name}" -> "{normalized_name}"')

        if plan_name not in self._phases or normalized_name not in self._phases[plan_name]:
            logger.error(
                f'get_phase failed: Phase not found: {phase_name} (normalized: {normalized_name}) '
                f'in project {plan_name}'
            )
            raise PhaseNotFoundError(f'Phase not found: {phase_name} in project {plan_name}')

        phase = self._phases[plan_name][normalized_name]
        logger.debug(
            f'get_phase: Retrieved phase using normalized name "{normalized_name}" (iteration={phase.iteration}, version={phase.version})'
        )
        self._log_state_snapshot('get_phase', 'EXIT')
        return phase

    async def list_phases(self, plan_name: str) -> list[str]:
        self._log_state_snapshot('list_phases', 'ENTRY')
        logger.debug(f'list_phases: plan_name={plan_name}')

        if plan_name not in self._phases:
            logger.debug(f'list_phases: No phases found for project: {plan_name}')
            self._log_state_snapshot('list_phases', 'EXIT')
            return []

        phase_names = list(self._phases[plan_name].keys())
        logger.debug(f'list_phases: Found {len(phase_names)} phases: {phase_names}')
        self._log_state_snapshot('list_phases', 'EXIT')
        return phase_names

    async def resolve_phase_name(self, plan_name: str, partial_name: str) -> tuple[str | None, list[str]]:
        all_phases = await self.list_phases(plan_name)

        if not all_phases:
            return (None, [])

        normalized_partial = normalize_phase_name(partial_name)

        if normalized_partial in all_phases:
            return (normalized_partial, [normalized_partial])

        matches = [phase for phase in all_phases if normalized_partial in phase]
        canonical = matches[0] if len(matches) == 1 else None

        return (canonical, matches)

    async def delete_phase(self, plan_name: str, phase_name: str) -> bool:
        """Mark a specific phase as inactive (soft delete).

        This maintains backward compatibility while using the inactive flag approach.
        """
        self._log_state_snapshot('delete_phase', 'ENTRY')
        logger.info(f'delete_phase: plan_name={plan_name}, phase_name={phase_name}')

        normalized_name = normalize_phase_name(phase_name)
        logger.debug(f'delete_phase: Normalized "{phase_name}" -> "{normalized_name}"')

        if plan_name not in self._phases or normalized_name not in self._phases[plan_name]:
            logger.warning(
                f'delete_phase: Phase not found: {phase_name} (normalized: {normalized_name}) in project {plan_name}'
            )
            self._log_state_snapshot('delete_phase', 'EXIT')
            return False

        # Move to inactive instead of deleting
        if plan_name not in self._inactive_phases:
            self._inactive_phases[plan_name] = {}

        phase = self._phases[plan_name][normalized_name]
        self._inactive_phases[plan_name][normalized_name] = phase
        del self._phases[plan_name][normalized_name]

        logger.info(f'delete_phase: Marked {phase_name} (normalized: {normalized_name}) as inactive')

        self._log_state()
        self._log_state_snapshot('delete_phase', 'EXIT')
        return True

    # Loop-to-Phase Mapping (for temporary refinement sessions)
    async def link_loop_to_phase(self, loop_id: str, plan_name: str, phase_name: str) -> None:
        self._log_state_snapshot('link_loop_to_phase', 'ENTRY')
        logger.info(f'link_loop_to_phase: loop_id={loop_id}, plan_name={plan_name}, phase_name={phase_name}')

        # Normalize phase name for consistent linking
        normalized_name = normalize_phase_name(phase_name)
        logger.debug(f'link_loop_to_phase: Normalized "{phase_name}" -> "{normalized_name}"')

        self._loop_to_phase[loop_id] = (plan_name, normalized_name)
        logger.info(f'Linked loop {loop_id} to phase {normalized_name} in project {plan_name}')
        self._log_state()
        self._log_state_snapshot('link_loop_to_phase', 'EXIT')

    async def get_phase_by_loop(self, loop_id: str) -> Phase:
        self._log_state_snapshot('get_phase_by_loop', 'ENTRY')
        logger.debug(f'get_phase_by_loop: loop_id={loop_id}')
        if loop_id not in self._loop_to_phase:
            logger.error(f'get_phase_by_loop failed: Loop not linked to any phase: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any phase: {loop_id}')
        plan_name, phase_name = self._loop_to_phase[loop_id]
        logger.debug(f'get_phase_by_loop: Loop {loop_id} linked to phase {phase_name} in project {plan_name}')
        self._log_state_snapshot('get_phase_by_loop', 'EXIT')
        return await self.get_phase(plan_name, phase_name)

    async def update_phase_by_loop(self, loop_id: str, phase: Phase) -> None:
        self._log_state_snapshot('update_phase_by_loop', 'ENTRY')
        logger.info(f'update_phase_by_loop: loop_id={loop_id}, phase_name={phase.phase_name}')
        if loop_id not in self._loop_to_phase:
            logger.error(f'update_phase_by_loop failed: Loop not linked to any phase: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any phase: {loop_id}')
        plan_name, phase_name = self._loop_to_phase[loop_id]
        logger.debug(f'update_phase_by_loop: Updating phase {phase_name} in project {plan_name}')
        await self.update_phase(plan_name, phase_name, phase)
        self._log_state_snapshot('update_phase_by_loop', 'EXIT')

    async def unlink_loop(self, loop_id: str) -> tuple[str, str] | None:
        self._log_state_snapshot('unlink_loop', 'ENTRY')
        logger.info(f'unlink_loop: loop_id={loop_id}')
        result = self._loop_to_phase.pop(loop_id, None)
        if result:
            plan_name, phase_name = result
            logger.info(f'unlink_loop: Unlinked loop {loop_id} from phase {phase_name} in project {plan_name}')
        else:
            logger.warning(f'unlink_loop: Loop {loop_id} was not linked to any phase')
        self._log_state()
        self._log_state_snapshot('unlink_loop', 'EXIT')
        return result

    # Plan Plan Management
    async def store_plan(self, plan_name: str, plan: Plan) -> str:
        self._log_state_snapshot('store_plan', 'ENTRY')
        logger.info(f'store_plan: plan_name={plan_name}')
        self._plans[plan_name] = plan
        self._log_state()
        self._log_state_snapshot('store_plan', 'EXIT')
        return plan_name

    async def get_plan(self, plan_name: str) -> Plan:
        self._log_state_snapshot('get_plan', 'ENTRY')
        logger.debug(f'get_plan: plan_name={plan_name}')
        if plan_name not in self._plans:
            logger.error(f'get_plan failed: Plan plan not found for project: {plan_name}')
            raise PlanNotFoundError(f'Project plan not found for project: {plan_name}')
        plan = self._plans[plan_name]
        logger.debug(f'get_plan: Found project plan for {plan_name}')
        self._log_state_snapshot('get_plan', 'EXIT')
        return plan

    async def list_plans(self) -> list[str]:
        self._log_state_snapshot('list_plans', 'ENTRY')
        logger.debug('list_plans: Listing all project plans')
        plan_names = list(self._plans.keys())
        logger.debug(f'list_plans: Found {len(plan_names)} project plans: {plan_names}')
        self._log_state_snapshot('list_plans', 'EXIT')
        return plan_names

    async def delete_plan(self, plan_name: str) -> bool:
        self._log_state_snapshot('delete_plan', 'ENTRY')
        logger.info(f'delete_plan: plan_name={plan_name}')
        if plan_name not in self._plans:
            logger.error(f'delete_plan failed: Plan plan not found for project: {plan_name}')
            raise PlanNotFoundError(f'Project plan not found for project: {plan_name}')

        loop_ids_to_remove = [lid for lid, pn in self._loop_to_plan.items() if pn == plan_name]
        for lid in loop_ids_to_remove:
            self._cleanup_loop_references(lid)

        task_paths = [p for p in self._tasks if p.startswith(f'{plan_name}/')]
        for path in task_paths:
            del self._tasks[path]
        inactive_task_paths = [p for p in self._inactive_tasks if p.startswith(f'{plan_name}/')]
        for path in inactive_task_paths:
            del self._inactive_tasks[path]

        review_keys = [k for k in self._review_sections if k.startswith(f'{plan_name}/')]
        for k in review_keys:
            del self._review_sections[k]

        self._phases.pop(plan_name, None)
        self._inactive_phases.pop(plan_name, None)
        self._roadmaps.pop(plan_name, None)
        del self._plans[plan_name]

        logger.info(f'delete_plan: Deleted plan and all related data for {plan_name}')
        self._log_state()
        self._log_state_snapshot('delete_plan', 'EXIT')
        return True

    async def store_task(self, phase_path: str, task: Task) -> str:
        self._log_state_snapshot('store_task', 'ENTRY')
        logger.info(f'store_task: phase_path={phase_path}, task_name={task.name}, version={task.version}')

        if phase_path not in self._tasks:
            self._tasks[phase_path] = {}

        normalized_name = normalize_phase_name(task.name)
        logger.debug(f'store_task: Normalized "{task.name}" -> "{normalized_name}"')

        self._tasks[phase_path][normalized_name] = task

        logger.info(f'store_task: Successfully stored task {task.name} for phase {phase_path}')
        self._log_state()
        self._log_state_snapshot('store_task', 'EXIT')
        return task.name

    async def get_task(self, phase_path: str, task_name: str) -> Task:
        self._log_state_snapshot('get_task', 'ENTRY')
        logger.debug(f'get_task: phase_path={phase_path}, task_name={task_name}')

        normalized_name = normalize_phase_name(task_name)
        logger.debug(f'get_task: Normalized "{task_name}" -> "{normalized_name}"')

        if phase_path not in self._tasks or normalized_name not in self._tasks[phase_path]:
            logger.error(
                f'get_task failed: Task not found: {task_name} (normalized: {normalized_name}) in phase {phase_path}'
            )
            raise ValueError(f'Task not found: {task_name} in phase {phase_path}')

        task = self._tasks[phase_path][normalized_name]
        logger.debug(f'get_task: Retrieved task {normalized_name} (version={task.version})')
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

        normalized_name = normalize_phase_name(task_name)
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

    async def mark_tasks_inactive(self, phase_path: str) -> int:
        self._log_state_snapshot('mark_tasks_inactive', 'ENTRY')
        logger.info(f'mark_tasks_inactive: phase_path={phase_path}')

        if phase_path not in self._tasks:
            logger.debug(f'mark_tasks_inactive: No active tasks found for phase {phase_path}')
            self._log_state_snapshot('mark_tasks_inactive', 'EXIT')
            return 0

        if phase_path not in self._inactive_tasks:
            self._inactive_tasks[phase_path] = {}

        active_tasks = self._tasks[phase_path]
        count = len(active_tasks)

        for task_name, task in active_tasks.items():
            self._inactive_tasks[phase_path][task_name] = task
            logger.debug(f'mark_tasks_inactive: Moved task "{task_name}" to inactive')

        self._tasks[phase_path] = {}

        logger.info(f'mark_tasks_inactive: Marked {count} tasks as inactive for phase {phase_path}')
        self._log_state()
        self._log_state_snapshot('mark_tasks_inactive', 'EXIT')
        return count

    async def get_tasks_for_phase(self, phase_path: str) -> list[Task]:
        self._log_state_snapshot('get_tasks_for_phase', 'ENTRY')
        logger.debug(f'get_tasks_for_phase: phase_path={phase_path}')

        if phase_path not in self._tasks:
            logger.debug(f'get_tasks_for_phase: No tasks found for phase: {phase_path}')
            self._log_state_snapshot('get_tasks_for_phase', 'EXIT')
            return []

        tasks = list(self._tasks[phase_path].values())
        # Sort alphabetically by name (e.g., task-1, task-1a, task-1b, task-2)
        sorted_tasks = sorted(tasks, key=lambda t: t.name)
        logger.debug(f'get_tasks_for_phase: Found {len(tasks)} tasks')
        self._log_state_snapshot('get_tasks_for_phase', 'EXIT')
        return sorted_tasks

    async def link_loop_to_task(self, loop_id: str, phase_path: str, task_name: str) -> None:
        self._log_state_snapshot('link_loop_to_task', 'ENTRY')
        logger.info(f'link_loop_to_task: loop_id={loop_id}, phase_path={phase_path}, task_name={task_name}')

        normalized_name = normalize_phase_name(task_name)
        logger.debug(f'link_loop_to_task: Normalized "{task_name}" -> "{normalized_name}"')

        self._loop_to_task[loop_id] = (phase_path, normalized_name)
        logger.info(f'Linked loop {loop_id} to task {normalized_name} in phase {phase_path}')
        self._log_state()
        self._log_state_snapshot('link_loop_to_task', 'EXIT')

    async def get_task_by_loop(self, loop_id: str) -> Task:
        self._log_state_snapshot('get_task_by_loop', 'ENTRY')
        logger.debug(f'get_task_by_loop: loop_id={loop_id}')

        if loop_id not in self._loop_to_task:
            logger.info(f'get_task_by_loop: Loop not linked to any task: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any task: {loop_id}')

        phase_path, task_name = self._loop_to_task[loop_id]
        logger.debug(f'get_task_by_loop: Loop {loop_id} linked to task {task_name} in phase {phase_path}')
        self._log_state_snapshot('get_task_by_loop', 'EXIT')
        return await self.get_task(phase_path, task_name)

    async def update_task_by_loop(self, loop_id: str, task: Task) -> None:
        self._log_state_snapshot('update_task_by_loop', 'ENTRY')
        logger.info(f'update_task_by_loop: loop_id={loop_id}, task_name={task.name}')

        if loop_id not in self._loop_to_task:
            logger.info(f'update_task_by_loop: Loop not linked to any task: {loop_id}')
            raise LoopNotFoundError(f'Loop not linked to any task: {loop_id}')

        phase_path, task_name = self._loop_to_task[loop_id]
        logger.debug(f'update_task_by_loop: Updating task {task_name} in phase {phase_path}')
        await self.store_task(phase_path, task)
        self._log_state_snapshot('update_task_by_loop', 'EXIT')

    async def store_review_section(self, key: str, content: str) -> str:
        self._review_sections[key] = content
        logger.info(f'store_review_section: Stored review section at {key}')
        return f'Stored review section at {key}'

    async def get_review_section(self, key: str) -> str:
        if key not in self._review_sections:
            raise ValueError(f'Review section not found: {key}')
        return self._review_sections[key]

    async def list_review_sections(self, parent_key: str) -> list[str]:
        prefix = parent_key + '/'
        return sorted(k for k in self._review_sections if k.startswith(prefix))

    async def upsert_reviewer_result(self, reviewer_result: ReviewerResult) -> None:
        await self.get_loop(reviewer_result.loop_id)
        key = (
            reviewer_result.loop_id,
            reviewer_result.review_iteration,
            reviewer_result.reviewer_name.value,
        )
        self._reviewer_results[key] = reviewer_result

    async def list_reviewer_results(self, loop_id: str, review_iteration: int) -> list[ReviewerResult]:
        await self.get_loop(loop_id)
        return [
            result
            for (stored_loop_id, stored_iteration, _), result in self._reviewer_results.items()
            if stored_loop_id == loop_id and stored_iteration == review_iteration
        ]

    async def list_latest_reviewer_results(
        self,
        loop_id: str,
        review_iteration: int,
        reviewer_names: list[str],
    ) -> list[ReviewerResult]:
        await self.get_loop(loop_id)
        reviewer_roster = set(reviewer_names)
        latest_by_reviewer: dict[str, ReviewerResult] = {}
        for (stored_loop_id, stored_iteration, reviewer_name), result in self._reviewer_results.items():
            if stored_loop_id != loop_id:
                continue
            if stored_iteration > review_iteration:
                continue
            if reviewer_name not in reviewer_roster:
                continue
            current = latest_by_reviewer.get(reviewer_name)
            if current is None or stored_iteration > current.review_iteration:
                latest_by_reviewer[reviewer_name] = result

        return [latest_by_reviewer[name] for name in sorted(latest_by_reviewer)]
