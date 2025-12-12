import json
from datetime import datetime

from asyncpg import Connection

from src.models.enums import PhaseStatus, ProjectStatus, RoadmapStatus
from src.models.feedback import CriticFeedback
from src.models.phase import Phase
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.utils.database_pool import db_pool
from src.utils.enums import LoopStatus, LoopType
from src.utils.errors import (
    LoopAlreadyExistsError,
    LoopNotFoundError,
    ProjectPlanNotFoundError,
    RoadmapNotFoundError,
    SpecNotFoundError,
)
from src.utils.loop_state import LoopState, MCPResponse

from .base import FROZEN_SPEC_FIELDS, StateManager, logger, normalize_phase_name


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

    def _row_to_spec(self, row: dict) -> Phase:
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

    def _row_to_task(self, row: dict) -> 'Task':
        return Task(
            id=str(row['id']),
            name=row['name'],
            phase_path=row['phase_path'],
            description=row['description'],
            acceptance_criteria=row['acceptance_criteria'],
            mode=row['mode'],
            sequence=row['sequence'],
            dependencies=list(row['dependencies']) if row['dependencies'] else [],
            estimated_complexity=row['estimated_complexity'],
            implementation_notes=row['implementation_notes'],
            test_strategy=row['test_strategy'],
            status=row['status'],
            iteration=row['iteration'],
            version=row['version'],
        )

    async def _enforce_loop_history_limit(self, conn: Connection) -> None:
        await conn.execute(
            """
            DELETE FROM loop_states
            WHERE id IN (
                SELECT loop_id FROM loop_history
                ORDER BY sequence_number DESC
                OFFSET $1
            )
            """,
            self._max_history_size,
        )

    async def add_loop(self, loop: LoopState, project_name: str) -> None:
        async with db_pool.acquire() as conn:
            existing = await conn.fetchval('SELECT id FROM loop_states WHERE id = $1', loop.id)

            if existing:
                raise LoopAlreadyExistsError(f'Loop already exists: {loop.id}')

            feedback_json = json.dumps([fb.model_dump(mode='json') for fb in loop.feedback_history])

            created_at = (
                datetime.fromisoformat(loop.created_at) if isinstance(loop.created_at, str) else loop.created_at
            )

            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO loop_states (
                        id, project_name, loop_type, status, current_score,
                        score_history, iteration, created_at, updated_at, feedback_history
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    loop.id,
                    project_name,
                    loop.loop_type.value,
                    loop.status.value,
                    loop.current_score,
                    loop.score_history,
                    loop.iteration,
                    created_at,
                    loop.updated_at,
                    feedback_json,
                )

                await conn.execute('INSERT INTO loop_history (loop_id) VALUES ($1)', loop.id)
                await self._enforce_loop_history_limit(conn)

        logger.info(f'Added loop {loop.id} to project {project_name}')

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

        # Retrieve latest score from stored critic feedback
        if not loop_state.feedback_history:
            raise ValueError(
                f'No feedback available for loop {loop_id} - cannot make decision without quality assessment'
            )

        latest_feedback = loop_state.feedback_history[-1]
        current_score = latest_feedback.overall_score

        loop_state.add_score(current_score)
        response = loop_state.decide_next_loop_action()

        async with db_pool.acquire() as conn:
            await conn.execute(
                'UPDATE loop_states SET current_score = $1, score_history = $2, status = $3 WHERE id = $4',
                loop_state.current_score,
                loop_state.score_history,
                loop_state.status.value,
                loop_id,
            )

        return response

    async def list_active_loops(self, project_name: str) -> list[MCPResponse]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, status FROM loop_states WHERE project_name = $1', project_name)

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

    async def store_roadmap(self, project_name: str, roadmap: Roadmap) -> str:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO roadmaps (
                    project_name, roadmap_title, project_goal, total_duration, team_size, roadmap_budget,
                    critical_path_analysis, key_risks, mitigation_plans, buffer_time,
                    development_resources, infrastructure_requirements, external_dependencies,
                    quality_assurance_plan, technical_milestones, business_milestones,
                    quality_gates, performance_targets, roadmap_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                ON CONFLICT (project_name) DO UPDATE SET
                    roadmap_title = $2, project_goal = $3, total_duration = $4, team_size = $5, roadmap_budget = $6,
                    critical_path_analysis = $7, key_risks = $8, mitigation_plans = $9, buffer_time = $10,
                    development_resources = $11, infrastructure_requirements = $12, external_dependencies = $13,
                    quality_assurance_plan = $14, technical_milestones = $15, business_milestones = $16,
                    quality_gates = $17, performance_targets = $18, roadmap_status = $19,
                    updated_at = CURRENT_TIMESTAMP
                """,
                project_name,
                roadmap.project_name,
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

        return project_name

    async def get_roadmap(self, project_name: str) -> Roadmap:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM roadmaps WHERE project_name = $1', project_name)

            if not row:
                raise RoadmapNotFoundError(f'Roadmap not found for project: {project_name}')

            return Roadmap(
                project_name=row['roadmap_title'],
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

    async def get_roadmap_specs(self, project_name: str) -> list[Phase]:
        await self.get_roadmap(project_name)

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM technical_specs WHERE project_name = $1 ORDER BY created_at', project_name
            )

        return [self._row_to_spec(row) for row in rows]

    async def store_spec(self, project_name: str, spec: Phase) -> str:
        normalized_name = normalize_phase_name(spec.phase_name)

        async with db_pool.acquire() as conn:
            existing = await conn.fetchrow(
                'SELECT iteration, version FROM technical_specs WHERE project_name = $1 AND phase_name = $2',
                project_name,
                normalized_name,
            )

            if existing:
                spec.iteration = existing['iteration'] + 1
                spec.version = existing['version'] + 1

            additional_sections_json = json.dumps(spec.additional_sections) if spec.additional_sections else None

            await conn.execute(
                """
                INSERT INTO technical_specs (
                    id, project_name, phase_name, objectives, scope, dependencies, deliverables,
                    architecture, technology_stack, functional_requirements, non_functional_requirements,
                    development_plan, testing_strategy, research_requirements, success_criteria,
                    integration_context, task_breakdown, additional_sections, iteration, version, phase_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                ON CONFLICT (project_name, phase_name) DO UPDATE SET
                    id = $1, architecture = $8, technology_stack = $9,
                    functional_requirements = $10, non_functional_requirements = $11,
                    development_plan = $12, testing_strategy = $13, research_requirements = $14,
                    success_criteria = $15, integration_context = $16, task_breakdown = $17,
                    additional_sections = $18, iteration = $19, version = $20, phase_status = $21,
                    updated_at = CURRENT_TIMESTAMP
                """,
                spec.id,
                project_name,
                normalized_name,
                spec.objectives,
                spec.scope,
                spec.dependencies,
                spec.deliverables,
                spec.architecture,
                spec.technology_stack,
                spec.functional_requirements,
                spec.non_functional_requirements,
                spec.development_plan,
                spec.testing_strategy,
                spec.research_requirements,
                spec.success_criteria,
                spec.integration_context,
                spec.task_breakdown,
                additional_sections_json,
                spec.iteration,
                spec.version,
                spec.phase_status.value,
            )

        return spec.phase_name

    async def update_spec(self, project_name: str, phase_name: str, updated_spec: Phase) -> str:
        existing_spec = await self.get_spec(project_name, phase_name)
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

        await self.store_spec(project_name, final_spec)

        return f'Updated spec "{phase_name}" to iteration {final_spec.iteration}, version {final_spec.version}'

    async def get_spec(self, project_name: str, phase_name: str) -> Phase:
        normalized_name = normalize_phase_name(phase_name)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM technical_specs WHERE project_name = $1 AND phase_name = $2',
                project_name,
                normalized_name,
            )

            if not row:
                raise SpecNotFoundError(f'Spec not found: {phase_name} in project {project_name}')

            return self._row_to_spec(row)

    async def list_specs(self, project_name: str) -> list[str]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT phase_name FROM technical_specs WHERE project_name = $1', project_name)

        return [row['phase_name'] for row in rows]

    async def resolve_phase_name(self, project_name: str, partial_name: str) -> tuple[str | None, list[str]]:
        all_specs = await self.list_specs(project_name)

        if not all_specs:
            return (None, [])

        normalized_partial = normalize_phase_name(partial_name)

        if normalized_partial in all_specs:
            return (normalized_partial, [normalized_partial])

        matches = [spec for spec in all_specs if normalized_partial in spec]
        canonical = matches[0] if len(matches) == 1 else None

        return (canonical, matches)

    async def delete_spec(self, project_name: str, phase_name: str) -> bool:
        normalized_name = normalize_phase_name(phase_name)

        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'DELETE FROM technical_specs WHERE project_name = $1 AND phase_name = $2', project_name, normalized_name
            )

        deleted_count = int(result.split()[-1])
        return deleted_count > 0

    async def link_loop_to_spec(self, loop_id: str, project_name: str, phase_name: str) -> None:
        normalized_name = normalize_phase_name(phase_name)

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO loop_to_spec_mappings (loop_id, project_name, phase_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (loop_id) DO UPDATE SET
                    project_name = $2, phase_name = $3, linked_at = CURRENT_TIMESTAMP
                """,
                loop_id,
                project_name,
                normalized_name,
            )

    async def get_spec_by_loop(self, loop_id: str) -> Phase:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'SELECT project_name, phase_name FROM loop_to_spec_mappings WHERE loop_id = $1', loop_id
            )

            if not mapping:
                raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')

            return await self.get_spec(mapping['project_name'], mapping['phase_name'])

    async def update_spec_by_loop(self, loop_id: str, spec: Phase) -> None:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow('SELECT project_name FROM loop_to_spec_mappings WHERE loop_id = $1', loop_id)

            if not mapping:
                raise LoopNotFoundError(f'Loop not linked to any spec: {loop_id}')

            await self.store_spec(mapping['project_name'], spec)

    async def unlink_loop(self, loop_id: str) -> tuple[str, str] | None:
        async with db_pool.acquire() as conn:
            mapping = await conn.fetchrow(
                'DELETE FROM loop_to_spec_mappings WHERE loop_id = $1 RETURNING project_name, phase_name', loop_id
            )

            if not mapping:
                return None

            return (mapping['project_name'], mapping['phase_name'])

    async def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> str:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO project_plans (
                    project_name, project_vision, project_mission, project_timeline, project_budget,
                    primary_objectives, success_metrics, key_performance_indicators,
                    included_features, excluded_features, project_assumptions, project_constraints,
                    project_sponsor, key_stakeholders, end_users,
                    work_breakdown, phases_overview, project_dependencies,
                    team_structure, technology_requirements, infrastructure_needs,
                    identified_risks, mitigation_strategies, contingency_plans,
                    quality_standards, testing_strategy, acceptance_criteria,
                    reporting_structure, meeting_schedule, documentation_standards,
                    project_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31)
                ON CONFLICT (project_name) DO UPDATE SET
                    project_vision = $2, project_mission = $3, project_timeline = $4, project_budget = $5,
                    primary_objectives = $6, success_metrics = $7, key_performance_indicators = $8,
                    included_features = $9, excluded_features = $10, project_assumptions = $11, project_constraints = $12,
                    project_sponsor = $13, key_stakeholders = $14, end_users = $15,
                    work_breakdown = $16, phases_overview = $17, project_dependencies = $18,
                    team_structure = $19, technology_requirements = $20, infrastructure_needs = $21,
                    identified_risks = $22, mitigation_strategies = $23, contingency_plans = $24,
                    quality_standards = $25, testing_strategy = $26, acceptance_criteria = $27,
                    reporting_structure = $28, meeting_schedule = $29, documentation_standards = $30,
                    project_status = $31, updated_at = CURRENT_TIMESTAMP
                """,
                project_name,
                project_plan.project_vision,
                project_plan.project_mission,
                project_plan.project_timeline,
                project_plan.project_budget,
                project_plan.primary_objectives,
                project_plan.success_metrics,
                project_plan.key_performance_indicators,
                project_plan.included_features,
                project_plan.excluded_features,
                project_plan.project_assumptions,
                project_plan.project_constraints,
                project_plan.project_sponsor,
                project_plan.key_stakeholders,
                project_plan.end_users,
                project_plan.work_breakdown,
                project_plan.phases_overview,
                project_plan.project_dependencies,
                project_plan.team_structure,
                project_plan.technology_requirements,
                project_plan.infrastructure_needs,
                project_plan.identified_risks,
                project_plan.mitigation_strategies,
                project_plan.contingency_plans,
                project_plan.quality_standards,
                project_plan.testing_strategy,
                project_plan.acceptance_criteria,
                project_plan.reporting_structure,
                project_plan.meeting_schedule,
                project_plan.documentation_standards,
                project_plan.project_status.value,
            )

        return project_name

    async def get_project_plan(self, project_name: str) -> ProjectPlan:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM project_plans WHERE project_name = $1', project_name)

            if not row:
                raise ProjectPlanNotFoundError(f'Project plan not found for project: {project_name}')

            return ProjectPlan(
                project_name=row['project_name'],
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
                project_status=ProjectStatus(row['project_status']),
            )

    async def list_project_plans(self) -> list[str]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT project_name FROM project_plans')

        return [row['project_name'] for row in rows]

    async def delete_project_plan(self, project_name: str) -> bool:
        async with db_pool.acquire() as conn:
            exists = await conn.fetchval('SELECT 1 FROM project_plans WHERE project_name = $1', project_name)

            if not exists:
                raise ProjectPlanNotFoundError(f'Project plan not found for project: {project_name}')

            await conn.execute('DELETE FROM project_plans WHERE project_name = $1', project_name)

        return True

    async def store_phase(self, project_name: str, phase: Phase) -> str:
        return await self.store_spec(project_name, phase)

    async def get_phase(self, project_name: str, phase_name: str) -> Phase:
        spec = await self.get_spec(project_name, phase_name)
        if spec is None:
            raise ValueError(f'Phase not found: {phase_name} in project {project_name}')
        return spec

    async def get_phase_by_loop(self, loop_id: str) -> Phase:
        spec = await self.get_spec_by_loop(loop_id)
        if spec is None:
            raise ValueError(f'No phase linked to loop: {loop_id}')
        return spec

    async def update_phase(self, project_name: str, phase_name: str, updated_phase: Phase) -> str:
        return await self.update_spec(project_name, phase_name, updated_phase)

    async def update_phase_by_loop(self, loop_id: str, phase: Phase) -> None:
        await self.update_spec_by_loop(loop_id, phase)

    async def list_phases(self, project_name: str) -> list[str]:
        return await self.list_specs(project_name)

    async def delete_phase(self, project_name: str, phase_name: str) -> bool:
        return await self.delete_spec(project_name, phase_name)

    async def link_loop_to_phase(self, loop_id: str, project_name: str, phase_name: str) -> None:
        await self.link_loop_to_spec(loop_id, project_name, phase_name)

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
                        id = $1, name = $2, description = $3, acceptance_criteria = $4, mode = $5,
                        sequence = $6, dependencies = $7, estimated_complexity = $8,
                        implementation_notes = $9, test_strategy = $10, status = $11,
                        iteration = $12, version = $13, updated_at = CURRENT_TIMESTAMP
                    WHERE phase_path = $14 AND LOWER(name) = LOWER($2)
                    """,
                    task.id,
                    task.name,
                    task.description,
                    task.acceptance_criteria,
                    task.mode,
                    task.sequence,
                    task.dependencies,
                    task.estimated_complexity,
                    task.implementation_notes,
                    task.test_strategy,
                    task.status,
                    task.iteration,
                    task.version,
                    phase_path,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO tasks (
                        id, name, phase_path, description, acceptance_criteria, mode,
                        sequence, dependencies, estimated_complexity, implementation_notes,
                        test_strategy, status, iteration, version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """,
                    task.id,
                    task.name,
                    phase_path,
                    task.description,
                    task.acceptance_criteria,
                    task.mode,
                    task.sequence,
                    task.dependencies,
                    task.estimated_complexity,
                    task.implementation_notes,
                    task.test_strategy,
                    task.status,
                    task.iteration,
                    task.version,
                )

        return task.name

    async def get_task(self, phase_path: str, task_name: str) -> 'Task':
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM tasks WHERE phase_path = $1 AND LOWER(name) = LOWER($2)',
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
            rows = await conn.fetch('SELECT name FROM tasks WHERE phase_path = $1', phase_path)

        return [row['name'] for row in rows]

    async def delete_task(self, phase_path: str, task_name: str) -> bool:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'DELETE FROM tasks WHERE phase_path = $1 AND LOWER(name) = LOWER($2)',
                phase_path,
                task_name,
            )

        return result != 'DELETE 0'

    async def link_loop_to_task(self, loop_id: str, phase_path: str, task_name: str) -> None:
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
                task_name,
            )

    async def store_document(self, doc_type: str, path: str, content: str) -> str:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')

    async def get_document(self, doc_type: str, path: str) -> str:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')

    async def get_document_by_loop(self, loop_id: str) -> tuple[str, str]:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')

    async def update_document(self, doc_type: str, path: str, content: str) -> str:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')

    async def list_documents(self, doc_type: str, parent_path: str | None = None) -> list[str]:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')

    async def delete_document(self, doc_type: str, path: str) -> bool:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')

    async def link_loop_to_document(self, loop_id: str, doc_type: str, path: str) -> None:
        raise NotImplementedError('PostgreSQL Document storage not yet implemented. Use InMemoryStateManager instead.')
