import json
from datetime import datetime

from asyncpg import Record

from src.models.enums import PhaseStatus, PlanStatus, RoadmapStatus
from src.models.feedback import CriticFeedback
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.utils.database_pool import db_pool
from src.utils.enums import LoopStatus, LoopType
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    PhaseNotFoundError,
    PlanNotFoundError,
    RoadmapNotFoundError,
)
from src.utils.loop_state import LoopState, MCPResponse

from .base import FROZEN_FIELD_DEFAULTS, FROZEN_PHASES_FIELDS, StateManager, logger, normalize_phase_name


class PostgresStateManager(StateManager):
    def __init__(self, max_history_size: int = 10) -> None:
        self._max_history_size = max_history_size
        self._initialized = False
        logger.info(f'PostgresStateManager initialized with max_history_size={max_history_size}')

    async def initialize(self) -> None:
        if self._initialized:
            return

        await db_pool.initialize()
        self._initialized = True
        logger.info('PostgresStateManager initialized')

    async def close(self) -> None:
        await db_pool.close()
        self._initialized = False

    def _row_to_phase(self, row: Record) -> Phase:
        additional_sections_data = None
        if row['additional_sections']:
            additional_sections_data = (
                json.loads(row['additional_sections'])
                if isinstance(row['additional_sections'], str)
                else row['additional_sections']
            )

        return Phase(
            id=str(row['id']),
            phase_name=row['phase_name'],
            objectives=row['objectives'],
            scope=row['scope'],
            dependencies=row['dependencies'],
            deliverables=row['deliverables'],
            architecture=row['architecture'],
            technology_stack=row['technology_stack'],
            functional_requirements=row['functional_requirements'],
            non_functional_requirements=row['non_functional_requirements'],
            development_plan=row['development_plan'],
            testing_strategy=row['testing_strategy'],
            research_requirements=row['research_requirements'],
            success_criteria=row['success_criteria'],
            integration_context=row['integration_context'],
            task_breakdown=row['task_breakdown'],
            additional_sections=additional_sections_data,
            iteration=row['iteration'],
            version=row['version'],
            phase_status=PhaseStatus(row['phase_status']),
        )

    def _row_to_task(self, row: Record) -> 'Task':
        active_value = row['active'] if row['active'] is not None else True
        return Task(
            id=row['id'],
            name=row['name'],
            phase_path=row['phase_path'],
            goal=row['goal'] or 'Goal not specified',
            acceptance_criteria=row['acceptance_criteria'] or 'Acceptance criteria not specified',
            tech_stack_reference=row['tech_stack_reference'] or 'Technology stack reference not specified',
            implementation_checklist=row['implementation_checklist'] or 'Implementation checklist not specified',
            implementation_steps=row['implementation_steps'] or 'Implementation steps not specified',
            testing_strategy=row['testing_strategy'] or 'Testing strategy not specified',
            status=row['status'] or 'pending',
            active=active_value,
            version=row['version'] or '1.0',
        )

    async def add_loop(self, loop: LoopState, plan_name: str) -> None:
        async with db_pool.acquire() as conn:
            existing = await conn.fetchval('SELECT id FROM loop_states WHERE id = $1', loop.id)

            if existing:
                raise LoopAlreadyExistsError(f'Loop already exists: {loop.id}')

            feedback_json = json.dumps([fb.model_dump(mode='json') for fb in loop.feedback_history])

            created_at = (
                datetime.fromisoformat(loop.created_at) if isinstance(loop.created_at, str) else loop.created_at
            )

            await conn.execute(
                """
                INSERT INTO loop_states (
                    id, plan_name, loop_type, status, current_score,
                    score_history, iteration, created_at, updated_at, feedback_history
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                loop.id,
                plan_name,
                loop.loop_type.value,
                loop.status.value,
                loop.current_score,
                loop.score_history,
                loop.iteration,
                created_at,
                loop.updated_at,
                feedback_json,
            )

        logger.info(f'Added loop {loop.id} to project {plan_name}')

    async def save_loop(self, loop_state: LoopState) -> None:
        feedback_json = json.dumps([fb.model_dump(mode='json') for fb in loop_state.feedback_history])
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE loop_states SET
                    status = $1, current_score = $2, score_history = $3,
                    iteration = $4, feedback_history = $5, updated_at = $6
                WHERE id = $7
                """,
                loop_state.status.value,
                loop_state.current_score,
                loop_state.score_history,
                loop_state.iteration,
                feedback_json,
                loop_state.updated_at,
                loop_state.id,
            )

    async def get_loop(self, loop_id: str) -> LoopState:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, loop_type, status, current_score, score_history,
                       iteration, created_at, updated_at, feedback_history
                FROM loop_states WHERE id = $1
                """,
                loop_id,
            )

            if not row:
                raise LoopNotFoundError(f'Loop not found: {loop_id}')

            feedback_data = (
                json.loads(row['feedback_history'])
                if isinstance(row['feedback_history'], str)
                else row['feedback_history']
            )
            feedback_list = [CriticFeedback.model_validate(fb) for fb in feedback_data]

            created_at_str = (
                row['created_at'].isoformat() if isinstance(row['created_at'], datetime) else row['created_at']
            )
            updated_at_dt = row['updated_at']

            return LoopState(
                id=row['id'],
                loop_type=LoopType(row['loop_type']),
                status=LoopStatus(row['status']),
                current_score=row['current_score'],
                score_history=list(row['score_history']),
                iteration=row['iteration'],
                created_at=created_at_str,
                updated_at=updated_at_dt,
                feedback_history=feedback_list,
            )

    async def get_loop_status(self, loop_id: str) -> MCPResponse:
        loop_state = await self.get_loop(loop_id)
        return loop_state.mcp_response

    async def decide_loop_next_action(self, loop_id: str) -> MCPResponse:
        loop_state = await self.get_loop(loop_id)

        if not loop_state.feedback_history:
            raise ValueError(
                f'No feedback available for loop {loop_id} - cannot make decision without quality assessment'
            )

        response = loop_state.decide_next_loop_action()
        await self.save_loop(loop_state)
        return response

    async def list_active_loops(self, plan_name: str) -> list[MCPResponse]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, status FROM loop_states WHERE plan_name = $1', plan_name)

        return [MCPResponse(id=row['id'], status=LoopStatus(row['status'])) for row in rows]

    async def get_objective_feedback(self, loop_id: str) -> MCPResponse:
        loop_state = await self.get_loop(loop_id)

        async with db_pool.acquire() as conn:
            feedback = await conn.fetchval('SELECT feedback FROM objective_feedback WHERE loop_id = $1', loop_id)

        return MCPResponse(
            id=loop_id, status=loop_state.status, message=feedback or 'No previous objective feedback found'
        )

    async def store_objective_feedback(self, loop_id: str, feedback: str) -> MCPResponse:
        loop_state = await self.get_loop(loop_id)

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO objective_feedback (loop_id, feedback)
                VALUES ($1, $2)
                ON CONFLICT (loop_id) DO UPDATE SET feedback = $2, stored_at = CURRENT_TIMESTAMP
                """,
                loop_id,
                feedback,
            )

        return MCPResponse(
            id=loop_id, status=loop_state.status, message=f'Objective feedback stored for loop {loop_id}'
        )

    async def store_roadmap(self, plan_name: str, roadmap: Roadmap) -> str:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO roadmaps (
                    plan_name, roadmap_title, project_goal, total_duration, team_size, roadmap_budget,
                    critical_path_analysis, key_risks, mitigation_plans, buffer_time,
                    development_resources, infrastructure_requirements, external_dependencies,
                    quality_assurance_plan, technical_milestones, business_milestones,
                    quality_gates, performance_targets, roadmap_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                ON CONFLICT (plan_name) DO UPDATE SET
                    roadmap_title = $2, project_goal = $3, total_duration = $4, team_size = $5, roadmap_budget = $6,
                    critical_path_analysis = $7, key_risks = $8, mitigation_plans = $9, buffer_time = $10,
                    development_resources = $11, infrastructure_requirements = $12, external_dependencies = $13,
                    quality_assurance_plan = $14, technical_milestones = $15, business_milestones = $16,
                    quality_gates = $17, performance_targets = $18, roadmap_status = $19,
                    updated_at = CURRENT_TIMESTAMP
                """,
                plan_name,
                roadmap.plan_name,
                roadmap.project_goal,
                roadmap.total_duration,
                roadmap.team_size,
                roadmap.roadmap_budget,
                roadmap.critical_path_analysis,
                roadmap.key_risks,
                roadmap.mitigation_plans,
                roadmap.buffer_time,
                roadmap.development_resources,
                roadmap.infrastructure_requirements,
                roadmap.external_dependencies,
                roadmap.quality_assurance_plan,
                roadmap.technical_milestones,
                roadmap.business_milestones,
                roadmap.quality_gates,
                roadmap.performance_targets,
                roadmap.roadmap_status.value,
            )

        return plan_name

    async def get_roadmap(self, plan_name: str) -> Roadmap:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM roadmaps WHERE plan_name = $1', plan_name)

            if not row:
                raise RoadmapNotFoundError(f'Roadmap not found for project: {plan_name}')

            return Roadmap(
                plan_name=row['roadmap_title'],
                project_goal=row['project_goal'],
                total_duration=row['total_duration'],
                team_size=row['team_size'],
                roadmap_budget=row['roadmap_budget'],
                critical_path_analysis=row['critical_path_analysis'],
                key_risks=row['key_risks'],
                mitigation_plans=row['mitigation_plans'],
                buffer_time=row['buffer_time'],
                development_resources=row['development_resources'],
                infrastructure_requirements=row['infrastructure_requirements'],
                external_dependencies=row['external_dependencies'],
                quality_assurance_plan=row['quality_assurance_plan'],
                technical_milestones=row['technical_milestones'],
                business_milestones=row['business_milestones'],
                quality_gates=row['quality_gates'],
                performance_targets=row['performance_targets'],
                roadmap_status=RoadmapStatus(row['roadmap_status']),
            )

    async def get_roadmap_phases(self, plan_name: str) -> list[Phase]:
        await self.get_roadmap(plan_name)

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM phases WHERE plan_name = $1 AND active = TRUE ORDER BY created_at', plan_name
            )

        return [self._row_to_phase(row) for row in rows]

    async def mark_phases_inactive(self, plan_name: str) -> int:
        """Mark all current active phases for a project as inactive.

        Returns the number of phases marked inactive.
        """
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE phases SET active = FALSE WHERE plan_name = $1 AND active = TRUE', plan_name
            )

        # Extract count from result string like "UPDATE 5"
        count = int(result.split()[-1]) if result else 0
        logger.info(f'mark_phases_inactive: Marked {count} phases as inactive for project {plan_name}')
        return count

    async def store_phase(self, plan_name: str, phase: Phase) -> str:
        normalized_name = normalize_phase_name(phase.phase_name)

        async with db_pool.acquire() as conn:
            existing = await conn.fetchrow(
                'SELECT iteration, version FROM phases WHERE plan_name = $1 AND phase_name = $2',
                plan_name,
                normalized_name,
            )

            if existing:
                phase.iteration = existing['iteration'] + 1
                phase.version = existing['version'] + 1

            additional_sections_json = json.dumps(phase.additional_sections) if phase.additional_sections else None

            await conn.execute(
                """
                INSERT INTO phases (
                    id, plan_name, phase_name, objectives, scope, dependencies, deliverables,
                    architecture, technology_stack, functional_requirements, non_functional_requirements,
                    development_plan, testing_strategy, research_requirements, success_criteria,
                    integration_context, task_breakdown, additional_sections, iteration, version, phase_status, active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                ON CONFLICT (plan_name, phase_name) DO UPDATE SET
                    id = $1, objectives = $4, scope = $5, dependencies = $6, deliverables = $7,
                    architecture = $8, technology_stack = $9,
                    functional_requirements = $10, non_functional_requirements = $11,
                    development_plan = $12, testing_strategy = $13, research_requirements = $14,
                    success_criteria = $15, integration_context = $16, task_breakdown = $17,
                    additional_sections = $18, iteration = $19, version = $20, phase_status = $21, active = $22,
                    updated_at = CURRENT_TIMESTAMP
                """,
                phase.id,
                plan_name,
                normalized_name,
                phase.objectives,
                phase.scope,
                phase.dependencies,
                phase.deliverables,
                phase.architecture,
                phase.technology_stack,
                phase.functional_requirements,
                phase.non_functional_requirements,
                phase.development_plan,
                phase.testing_strategy,
                phase.research_requirements,
                phase.success_criteria,
                phase.integration_context,
                phase.task_breakdown,
                additional_sections_json,
                phase.iteration,
                phase.version,
                phase.phase_status.value,
                True,  # Always store new phases as active
            )

        return phase.phase_name

    async def update_phase(self, plan_name: str, phase_name: str, updated_phase: Phase) -> str:
        existing_phase = await self.get_phase(plan_name, phase_name)
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

        await self.store_phase(plan_name, final_phase)

        return f'Updated phase "{phase_name}" to iteration {final_phase.iteration}, version {final_phase.version}'

    async def get_phase(self, plan_name: str, phase_name: str) -> Phase:
        normalized_name = normalize_phase_name(phase_name)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM phases WHERE plan_name = $1 AND phase_name = $2 AND active = TRUE',
                plan_name,
                normalized_name,
            )

            if not row:
                raise PhaseNotFoundError(f'Phase not found: {phase_name} in project {plan_name}')

            return self._row_to_phase(row)

    async def list_phases(self, plan_name: str) -> list[str]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT phase_name FROM phases WHERE plan_name = $1 AND active = TRUE', plan_name)

        return [row['phase_name'] for row in rows]

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
        normalized_name = normalize_phase_name(phase_name)

        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE phases SET active = FALSE WHERE plan_name = $1 AND phase_name = $2 AND active = TRUE',
                plan_name,
                normalized_name,
            )

        # Extract count from result string like "UPDATE 1"
        updated_count = int(result.split()[-1]) if result else 0
        if updated_count > 0:
            logger.info(f'delete_phase: Marked phase "{phase_name}" as inactive for project {plan_name}')
        return updated_count > 0

    async def link_loop_to_phase(self, loop_id: str, plan_name: str, phase_name: str) -> None:
        normalized_name = normalize_phase_name(phase_name)

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_to_phase_mappings (loop_id, plan_name, phase_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (loop_id) DO UPDATE SET
                    plan_name = $2, phase_name = $3, linked_at = CURRENT_TIMESTAMP
                """,
                loop_id,
                plan_name,
                normalized_name,
            )

    async def get_phase_by_loop(self, loop_id: str) -> Phase:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'SELECT plan_name, phase_name FROM loop_to_phase_mappings WHERE loop_id = $1', loop_id
            )

            if not mapping:
                raise LoopNotFoundError(f'Loop not linked to any phase: {loop_id}')

            return await self.get_phase(mapping['plan_name'], mapping['phase_name'])

    async def update_phase_by_loop(self, loop_id: str, phase: Phase) -> None:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'SELECT plan_name, phase_name FROM loop_to_phase_mappings WHERE loop_id = $1', loop_id
            )

            if not mapping:
                raise LoopNotFoundError(f'Loop not linked to any phase: {loop_id}')

            await self.update_phase(mapping['plan_name'], mapping['phase_name'], phase)

    async def unlink_loop(self, loop_id: str) -> tuple[str, str] | None:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'DELETE FROM loop_to_phase_mappings WHERE loop_id = $1 RETURNING plan_name, phase_name', loop_id
            )

            if not mapping:
                return None

            return (mapping['plan_name'], mapping['phase_name'])

    async def store_plan(self, plan_name: str, plan: Plan) -> str:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO plans (
                    plan_name, project_vision, project_mission, project_timeline, project_budget,
                    primary_objectives, success_metrics, key_performance_indicators,
                    included_features, excluded_features, project_assumptions, project_constraints,
                    project_sponsor, key_stakeholders, end_users,
                    work_breakdown, phases_overview, project_dependencies,
                    team_structure, technology_requirements, infrastructure_needs,
                    identified_risks, mitigation_strategies, contingency_plans,
                    quality_standards, testing_strategy, acceptance_criteria,
                    reporting_structure, meeting_schedule, documentation_standards,
                    plan_status, additional_sections
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32)
                ON CONFLICT (plan_name) DO UPDATE SET
                    project_vision = $2, project_mission = $3, project_timeline = $4, project_budget = $5,
                    primary_objectives = $6, success_metrics = $7, key_performance_indicators = $8,
                    included_features = $9, excluded_features = $10, project_assumptions = $11, project_constraints = $12,
                    project_sponsor = $13, key_stakeholders = $14, end_users = $15,
                    work_breakdown = $16, phases_overview = $17, project_dependencies = $18,
                    team_structure = $19, technology_requirements = $20, infrastructure_needs = $21,
                    identified_risks = $22, mitigation_strategies = $23, contingency_plans = $24,
                    quality_standards = $25, testing_strategy = $26, acceptance_criteria = $27,
                    reporting_structure = $28, meeting_schedule = $29, documentation_standards = $30,
                    plan_status = $31, additional_sections = $32, updated_at = CURRENT_TIMESTAMP
                """,
                plan_name,
                plan.project_vision,
                plan.project_mission,
                plan.project_timeline,
                plan.project_budget,
                plan.primary_objectives,
                plan.success_metrics,
                plan.key_performance_indicators,
                plan.included_features,
                plan.excluded_features,
                plan.project_assumptions,
                plan.project_constraints,
                plan.project_sponsor,
                plan.key_stakeholders,
                plan.end_users,
                plan.work_breakdown,
                plan.phases_overview,
                plan.project_dependencies,
                plan.team_structure,
                plan.technology_requirements,
                plan.infrastructure_needs,
                plan.identified_risks,
                plan.mitigation_strategies,
                plan.contingency_plans,
                plan.quality_standards,
                plan.testing_strategy,
                plan.acceptance_criteria,
                plan.reporting_structure,
                plan.meeting_schedule,
                plan.documentation_standards,
                plan.plan_status.value,
                json.dumps(plan.additional_sections) if plan.additional_sections else None,
            )

        return plan_name

    async def get_plan(self, plan_name: str) -> Plan:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM plans WHERE plan_name = $1', plan_name)

            if not row:
                raise PlanNotFoundError(f'Project plan not found for project: {plan_name}')

            additional_sections_data = None
            if row['additional_sections']:
                additional_sections_data = (
                    json.loads(row['additional_sections'])
                    if isinstance(row['additional_sections'], str)
                    else row['additional_sections']
                )

            return Plan(
                plan_name=row['plan_name'],
                project_vision=row['project_vision'],
                project_mission=row['project_mission'],
                project_timeline=row['project_timeline'],
                project_budget=row['project_budget'],
                primary_objectives=row['primary_objectives'],
                success_metrics=row['success_metrics'],
                key_performance_indicators=row['key_performance_indicators'],
                included_features=row['included_features'],
                excluded_features=row['excluded_features'],
                project_assumptions=row['project_assumptions'],
                project_constraints=row['project_constraints'],
                project_sponsor=row['project_sponsor'],
                key_stakeholders=row['key_stakeholders'],
                end_users=row['end_users'],
                work_breakdown=row['work_breakdown'],
                phases_overview=row['phases_overview'],
                project_dependencies=row['project_dependencies'],
                team_structure=row['team_structure'],
                technology_requirements=row['technology_requirements'],
                infrastructure_needs=row['infrastructure_needs'],
                identified_risks=row['identified_risks'],
                mitigation_strategies=row['mitigation_strategies'],
                contingency_plans=row['contingency_plans'],
                quality_standards=row['quality_standards'],
                testing_strategy=row['testing_strategy'],
                acceptance_criteria=row['acceptance_criteria'],
                reporting_structure=row['reporting_structure'],
                meeting_schedule=row['meeting_schedule'],
                documentation_standards=row['documentation_standards'],
                additional_sections=additional_sections_data,
                plan_status=PlanStatus(row['plan_status']),
            )

    async def list_plans(self) -> list[str]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT plan_name FROM plans')

        return [row['plan_name'] for row in rows]

    async def delete_plan(self, plan_name: str) -> bool:
        async with db_pool.acquire() as conn:
            exists = await conn.fetchval('SELECT 1 FROM plans WHERE plan_name = $1', plan_name)

            if not exists:
                raise PlanNotFoundError(f'Project plan not found for project: {plan_name}')

            await conn.execute('DELETE FROM plans WHERE plan_name = $1', plan_name)

        return True

    async def store_task(self, phase_path: str, task: 'Task') -> str:
        async with db_pool.acquire() as conn:
            existing = await conn.fetchrow(
                'SELECT name FROM tasks WHERE phase_path = $1 AND LOWER(name) = LOWER($2)',
                phase_path,
                task.name,
            )

            if existing:
                await conn.execute(
                    """
                    UPDATE tasks SET
                        id = $1, name = $2, goal = $3, acceptance_criteria = $4, tech_stack_reference = $5,
                        implementation_checklist = $6, implementation_steps = $7, testing_strategy = $8,
                        status = $9, active = $10, version = $11, updated_at = CURRENT_TIMESTAMP
                    WHERE phase_path = $12 AND LOWER(name) = LOWER($2)
                    """,
                    task.id,
                    task.name,
                    task.goal,
                    task.acceptance_criteria,
                    task.tech_stack_reference,
                    task.implementation_checklist,
                    task.implementation_steps,
                    task.testing_strategy,
                    task.status,
                    task.active,
                    task.version,
                    phase_path,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO tasks (
                        id, name, phase_path, goal, acceptance_criteria, tech_stack_reference,
                        implementation_checklist, implementation_steps, testing_strategy, status, active, version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    task.id,
                    task.name,
                    phase_path,
                    task.goal,
                    task.acceptance_criteria,
                    task.tech_stack_reference,
                    task.implementation_checklist,
                    task.implementation_steps,
                    task.testing_strategy,
                    task.status,
                    task.active,
                    task.version,
                )

        return task.name

    async def get_task(self, phase_path: str, task_name: str) -> 'Task':
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM tasks WHERE phase_path = $1 AND LOWER(name) = LOWER($2) AND active = TRUE',
                phase_path,
                task_name,
            )

            if not row:
                raise ValueError(f'Task not found: {task_name} in phase {phase_path}')

            return self._row_to_task(row)

    async def get_task_by_loop(self, loop_id: str) -> 'Task':
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'SELECT phase_path, task_name FROM loop_to_task_mappings WHERE loop_id = $1',
                loop_id,
            )

            if not mapping:
                raise LoopNotFoundError(f'Loop not linked to any task: {loop_id}')

            return await self.get_task(mapping['phase_path'], mapping['task_name'])

    async def update_task_by_loop(self, loop_id: str, task: 'Task') -> None:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'SELECT phase_path, task_name FROM loop_to_task_mappings WHERE loop_id = $1',
                loop_id,
            )

            if not mapping:
                raise LoopNotFoundError(f'Loop not linked to any task: {loop_id}')

            await self.store_task(mapping['phase_path'], task)

    async def list_tasks(self, phase_path: str) -> list[str]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT name FROM tasks WHERE phase_path = $1 AND active = TRUE', phase_path)

        return [row['name'] for row in rows]

    async def delete_task(self, phase_path: str, task_name: str) -> bool:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'DELETE FROM tasks WHERE phase_path = $1 AND LOWER(name) = LOWER($2)',
                phase_path,
                task_name,
            )

        return result != 'DELETE 0'

    async def mark_tasks_inactive(self, phase_path: str) -> int:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE tasks SET active = FALSE WHERE phase_path = $1 AND active = TRUE', phase_path
            )

        count = int(result.split()[-1]) if result else 0
        logger.info(f'mark_tasks_inactive: Marked {count} tasks as inactive for phase {phase_path}')
        return count

    async def get_tasks_for_phase(self, phase_path: str) -> list['Task']:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM tasks WHERE phase_path = $1 AND active = TRUE ORDER BY name', phase_path
            )

        return [self._row_to_task(row) for row in rows]

    async def link_loop_to_task(self, loop_id: str, phase_path: str, task_name: str) -> None:
        normalized_name = normalize_phase_name(task_name)
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_to_task_mappings (loop_id, phase_path, task_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (loop_id) DO UPDATE SET
                    phase_path = $2, task_name = $3
                """,
                loop_id,
                phase_path,
                normalized_name,
            )

    async def store_review_section(self, key: str, content: str) -> str:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO review_sections (key, content)
                VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET
                    content = $2, updated_at = CURRENT_TIMESTAMP
                """,
                key,
                content,
            )
        return f'Stored review section at {key}'

    async def get_review_section(self, key: str) -> str:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT content FROM review_sections WHERE key = $1',
                key,
            )
        if row is None:
            raise ValueError(f'Review section not found: {key}')
        return row['content']

    async def list_review_sections(self, parent_key: str) -> list[str]:
        prefix = parent_key + '/'
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT key FROM review_sections WHERE key LIKE $1 ORDER BY key',
                prefix + '%',
            )
        return [row['key'] for row in rows]
