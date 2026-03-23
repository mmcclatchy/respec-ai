"""State Manager Model Round-Trip Integration Tests.

Validates that storing and retrieving models through StateManager implementations
preserves data integrity. Tests are parameterized to run against both
InMemoryStateManager and PostgresStateManager to ensure compatibility.

These tests verify:
1. Store → Retrieve preserves all model fields
2. Both state manager implementations behave identically
3. Complex models with nested data serialize correctly
4. Dependency injection works properly with either implementation
"""

from typing import AsyncGenerator, Callable

import pytest

from src.models.enums import PhaseStatus, PlanStatus, RoadmapStatus
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.utils.database_pool import db_pool
from src.utils.enums import LoopType
from src.utils.loop_state import LoopState
from src.utils.state_manager import InMemoryStateManager, StateManager
from src.utils.state_manager.postgres import PostgresStateManager


@pytest.fixture
def plan_name() -> str:
    return 'test-integration-project'


@pytest.fixture
async def inmemory_manager() -> StateManager:
    return InMemoryStateManager(max_history_size=10)


@pytest.fixture
async def postgres_manager(check_database_available: bool) -> AsyncGenerator[StateManager, None]:
    if not check_database_available:
        pytest.skip(
            'PostgreSQL test database not available. '
            'Start with: docker-compose -f docker-compose.dev.yml up -d\n'
            'Or run with: pytest -k "not postgres" to skip database tests'
        )

    manager = PostgresStateManager(max_history_size=10)
    await manager.initialize()

    yield manager

    if db_pool._pool is not None:
        try:
            async with db_pool._pool.acquire() as conn:
                await conn.execute(
                    'TRUNCATE loop_states, loop_history, objective_feedback, roadmaps, '
                    'phases, plans, loop_to_phase_mappings CASCADE'
                )
        except Exception:
            pass
        finally:
            await db_pool.close()


@pytest.fixture(params=['inmemory', 'postgres'])
async def state_manager(
    request: pytest.FixtureRequest,
    check_database_available: bool,
    inmemory_manager: StateManager,
) -> AsyncGenerator[StateManager, None]:
    """Parameterized fixture providing both StateManager implementations.

    Tests using this fixture will run twice - once with InMemoryStateManager
    and once with PostgresStateManager.
    """
    if request.param == 'inmemory':
        yield inmemory_manager
    else:
        if not check_database_available:
            pytest.skip(
                'PostgreSQL test database not available. '
                'Start with: docker-compose -f docker-compose.dev.yml up -d\n'
                'Or run with: pytest -k "not postgres" to skip database tests'
            )

        manager = PostgresStateManager(max_history_size=10)
        await manager.initialize()

        yield manager

        if db_pool._pool is not None:
            try:
                async with db_pool._pool.acquire() as conn:
                    await conn.execute(
                        'TRUNCATE loop_states, loop_history, objective_feedback, roadmaps, '
                        'phases, plans, loop_to_phase_mappings CASCADE'
                    )
            except Exception:
                pass
            finally:
                await db_pool.close()


@pytest.fixture
def sample_roadmap(markdown_builder: Callable) -> Roadmap:
    markdown = markdown_builder(
        Roadmap,
        plan_name='Integration Test Roadmap',
        project_goal='Validate round-trip persistence',
        total_duration='12 weeks',
        team_size='6 engineers',
        roadmap_budget='$250,000',
        critical_path_analysis='Backend → Frontend → Integration',
        key_risks='Database migration complexity',
        mitigation_plans='Staged rollout with rollback capability',
        buffer_time='2 weeks contingency',
        development_resources='6 full-stack engineers',
        infrastructure_requirements='Kubernetes cluster with PostgreSQL',
        external_dependencies='Auth0 for authentication',
        quality_assurance_plan='Automated E2E tests with Playwright',
        technical_milestones='API complete, Frontend deployed',
        business_milestones='Beta launch, Public release',
        quality_gates='Test coverage >80%, Zero critical bugs',
        performance_targets='API response <100ms p95',
        roadmap_status=RoadmapStatus.IN_PROGRESS,
        phase_count=3,
    )
    return Roadmap.parse_markdown(markdown)


@pytest.fixture
def sample_phase(markdown_builder: Callable) -> Phase:
    markdown = markdown_builder(
        Phase,
        phase_name='user-authentication-service',
        objectives='Implement secure OAuth2 authentication with MFA support',
        scope='User registration, login, logout, password reset, MFA enrollment',
        dependencies='PostgreSQL database, Redis cache, Email service',
        deliverables='Auth API service, Admin dashboard, User documentation',
        architecture='Microservice with JWT tokens and refresh token rotation',
        technology_stack='FastAPI, SQLAlchemy, Alembic, Redis, PostgreSQL',
        functional_requirements='Support email/password and OAuth providers (Google, GitHub)',
        non_functional_requirements='99.9% uptime, <200ms p95 latency, GDPR compliant',
        development_plan='Week 1: Database schema, Week 2: Auth endpoints, Week 3: MFA',
        testing_strategy='Unit tests with pytest, Integration tests, Security penetration testing',
        research_requirements='OWASP authentication best practices, JWT security patterns',
        success_criteria='All authentication flows work, Security audit passes',
        integration_context='Integrates with API gateway and user service',
        phase_status=PhaseStatus.IMPLEMENTATION_READY,
        iteration=2,
        version=1,
    )
    return Phase.parse_markdown(markdown)


@pytest.fixture
def sample_plan(markdown_builder: Callable) -> Plan:
    markdown = markdown_builder(
        Plan,
        plan_name='Enterprise Portal Modernization',
        project_vision='Transform legacy portal into modern cloud-native platform',
        project_mission='Deliver scalable, maintainable portal with improved UX',
        project_timeline='18 months',
        project_budget='$2.5M',
        primary_objectives='Migrate to microservices, Improve performance 10x',
        success_metrics='User satisfaction >4.5/5, Page load time <1s',
        key_performance_indicators='Daily active users, API response times, Error rates',
        included_features='User dashboard, Analytics, Reporting, Admin tools',
        excluded_features='Legacy system maintenance, Custom integrations',
        project_assumptions='Infrastructure team available, Cloud budget approved',
        project_constraints='Must maintain 99.9% uptime during migration',
        project_sponsor='VP Engineering Jane Smith',
        key_stakeholders='Product, Engineering, Customer Success, Security',
        end_users='50,000+ enterprise customers',
        work_breakdown='Phase 1: Backend, Phase 2: Frontend, Phase 3: Migration',
        phases_overview='Discovery (2mo), Development (12mo), Rollout (4mo)',
        project_dependencies='Design system library, CI/CD pipeline',
        team_structure='2 PMs, 8 Engineers, 2 QA, 1 DevOps',
        technology_requirements='Kubernetes, PostgreSQL, React, FastAPI',
        infrastructure_needs='3 Kubernetes clusters, CDN, Monitoring stack',
        identified_risks='Data migration errors, Performance degradation',
        mitigation_strategies='Staged rollout, Comprehensive testing, Rollback plan',
        contingency_plans='Extended timeline, Reduced scope, Additional resources',
        quality_standards='WCAG 2.1 AA, SOC 2 compliance',
        testing_strategy='Unit, Integration, E2E, Load testing',
        documentation_standards='OpenAPI phases, Architecture decision records',
        plan_status=PlanStatus.ACTIVE,
    )
    return Plan.parse_markdown(markdown)


@pytest.fixture
def sample_task(markdown_builder: Callable) -> Task:
    markdown = markdown_builder(
        Task,
        name='Implement User Authentication',
        phase_path='microservices-platform/phase-1-foundation',
        goal='Implement OAuth2 authentication with JWT tokens',
        acceptance_criteria='Users can register, login, and access protected endpoints',
        tech_stack_reference='FastAPI, Python 3.13+, JWT, OAuth2',
        implementation_steps="""#### Step 1: Setup OAuth2 Dependencies
Install required packages and configure OAuth2PasswordBearer.

#### Step 2: Implement JWT Token Handler
Create JWT token generation and validation logic.

#### Step 3: Create Auth Endpoints
Implement login and token refresh endpoints.""",
        testing_strategy='Unit tests for auth logic, integration tests for endpoints',
        status='in_progress',
        active='true',
        version='1.0',
    )
    return Task.parse_markdown(markdown)


# ============================================================================
# Roadmap Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_roadmap_store_retrieve_preserves_all_fields(
    state_manager: StateManager, plan_name: str, sample_roadmap: Roadmap
) -> None:
    """Verify storing and retrieving Roadmap preserves all field values."""
    # Store roadmap
    await state_manager.store_roadmap(plan_name, sample_roadmap)

    # Retrieve roadmap
    retrieved = await state_manager.get_roadmap(plan_name)

    # Compare all fields (exclude dynamic fields like id)
    original_data = sample_roadmap.model_dump(exclude={'id', 'phases'})
    retrieved_data = retrieved.model_dump(exclude={'id', 'phases'})

    assert original_data == retrieved_data, 'Roadmap round-trip changed field values'


@pytest.mark.asyncio
async def test_roadmap_multiple_updates_preserve_latest(
    state_manager: StateManager, plan_name: str, sample_roadmap: Roadmap
) -> None:
    """Verify updating roadmap multiple times preserves latest version."""
    # Store initial roadmap
    await state_manager.store_roadmap(plan_name, sample_roadmap)

    # Update roadmap with new values
    updated_roadmap = sample_roadmap.model_copy(
        update={
            'roadmap_status': RoadmapStatus.COMPLETED,
            'project_goal': 'Updated project goal for completion',
        }
    )
    await state_manager.store_roadmap(plan_name, updated_roadmap)

    # Retrieve and verify latest
    retrieved = await state_manager.get_roadmap(plan_name)

    assert retrieved.roadmap_status == RoadmapStatus.COMPLETED
    assert retrieved.project_goal == 'Updated project goal for completion'


# ============================================================================
# Phase Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_phase_store_retrieve_preserves_all_fields(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    """Verify storing and retrieving Phase preserves all field values."""
    # Store phase
    phase_name = await state_manager.store_phase(plan_name, sample_phase)

    # Retrieve phase
    retrieved = await state_manager.get_phase(plan_name, phase_name)

    # Compare all fields
    original_data = sample_phase.model_dump(exclude={'id'})
    retrieved_data = retrieved.model_dump(exclude={'id'})

    assert original_data == retrieved_data, 'Phase round-trip changed field values'


@pytest.mark.asyncio
async def test_phase_store_replaces_frozen_fields(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    """Verify store_phase performs full replacement including frozen fields."""
    # Store original phase
    phase_name = await state_manager.store_phase(plan_name, sample_phase)

    # Create updated phase with changes to frozen fields
    updated_phase = sample_phase.model_copy(
        update={
            'objectives': 'UPDATED objectives - should persist',
            'scope': 'UPDATED scope - should persist',
            'architecture': 'Updated architecture - should persist',
        }
    )

    await state_manager.store_phase(plan_name, updated_phase)

    # Retrieve and verify ALL fields updated (full replacement)
    retrieved = await state_manager.get_phase(plan_name, phase_name)

    assert retrieved.objectives == 'UPDATED objectives - should persist', 'store_phase should replace frozen fields'
    assert retrieved.scope == 'UPDATED scope - should persist', 'store_phase should replace frozen fields'
    assert retrieved.architecture == 'Updated architecture - should persist'


@pytest.mark.asyncio
async def test_phase_frozen_fields_preserved_on_update(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    """Verify frozen fields (objectives, scope, dependencies, deliverables) are preserved."""
    # Store original phase
    phase_name = await state_manager.store_phase(plan_name, sample_phase)

    # Create updated phase with attempted changes to frozen fields
    updated_phase = sample_phase.model_copy(
        update={
            'objectives': 'CHANGED - should not persist',
            'scope': 'CHANGED - should not persist',
            'architecture': 'Updated architecture - should persist',
        }
    )

    await state_manager.update_phase(plan_name, phase_name, updated_phase)

    # Retrieve and verify frozen fields unchanged
    retrieved = await state_manager.get_phase(plan_name, phase_name)

    assert retrieved.objectives == sample_phase.objectives, 'Frozen field "objectives" was modified'
    assert retrieved.scope == sample_phase.scope, 'Frozen field "scope" was modified'
    assert retrieved.architecture == 'Updated architecture - should persist'


@pytest.mark.asyncio
async def test_phase_iteration_and_version_auto_increment(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    """Verify iteration and version auto-increment on duplicate phase names."""
    # Store phase twice with same name
    await state_manager.store_phase(plan_name, sample_phase)

    # Store again with same phase_name
    duplicate_phase = sample_phase.model_copy()
    await state_manager.store_phase(plan_name, duplicate_phase)

    # Retrieve - should have incremented iteration/version
    retrieved = await state_manager.get_phase(plan_name, sample_phase.phase_name)

    assert retrieved.iteration > sample_phase.iteration or retrieved.version > sample_phase.version


# ============================================================================
# Plan Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_plan_store_retrieve_preserves_all_fields(state_manager: StateManager, sample_plan: Plan) -> None:
    plan_name = sample_plan.plan_name

    # Store project plan
    await state_manager.store_plan(plan_name, sample_plan)

    # Retrieve project plan
    retrieved = await state_manager.get_plan(plan_name)

    # Compare all fields
    original_data = sample_plan.model_dump()
    retrieved_data = retrieved.model_dump()

    assert original_data == retrieved_data, 'Plan round-trip changed field values'


@pytest.mark.asyncio
async def test_plan_update_overwrites_completely(state_manager: StateManager, sample_plan: Plan) -> None:
    plan_name = sample_plan.plan_name

    # Store original
    await state_manager.store_plan(plan_name, sample_plan)

    # Create updated version with different values
    updated_plan = sample_plan.model_copy()
    updated_plan.plan_status = PlanStatus.COMPLETED
    updated_plan.project_budget = '$3M'
    updated_plan.team_structure = '3 PMs, 12 Engineers'

    await state_manager.store_plan(plan_name, updated_plan)

    # Retrieve and verify updates
    retrieved = await state_manager.get_plan(plan_name)

    assert retrieved.plan_status == PlanStatus.COMPLETED
    assert retrieved.project_budget == '$3M'
    assert retrieved.team_structure == '3 PMs, 12 Engineers'


# ============================================================================
# Task Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_task_store_retrieve_preserves_all_fields(state_manager: StateManager, sample_task: Task) -> None:
    # Store task using phase_path
    phase_path = sample_task.phase_path
    await state_manager.store_task(phase_path, sample_task)

    # Retrieve task
    retrieved = await state_manager.get_task(phase_path, sample_task.name)

    # Compare all fields
    original_data = sample_task.model_dump()
    retrieved_data = retrieved.model_dump()

    assert original_data == retrieved_data, 'Task round-trip changed field values'


# ============================================================================
# Cross-Implementation Consistency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_both_implementations_produce_identical_results(
    inmemory_manager: StateManager,
    postgres_manager: StateManager,
    plan_name: str,
    sample_roadmap: Roadmap,
) -> None:
    """Verify InMemory and Postgres implementations produce identical results."""
    # Store in both managers
    await inmemory_manager.store_roadmap(plan_name, sample_roadmap)
    await postgres_manager.store_roadmap(plan_name, sample_roadmap)

    # Retrieve from both
    inmemory_result = await inmemory_manager.get_roadmap(plan_name)
    postgres_result = await postgres_manager.get_roadmap(plan_name)

    # Compare results
    inmemory_data = inmemory_result.model_dump(exclude={'id', 'phases'})
    postgres_data = postgres_result.model_dump(exclude={'id', 'phases'})

    assert inmemory_data == postgres_data, 'InMemory and Postgres implementations differ'


# ============================================================================
# Loop-to-Phase Mapping Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_loop_phase_mapping_preserves_phase_data(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    """Verify loop-to-phase mapping preserves phase data through refinement cycle."""
    # Store phase
    phase_name = await state_manager.store_phase(plan_name, sample_phase)

    # Create loop and link to phase
    loop = LoopState(loop_type=LoopType.PHASE)
    await state_manager.add_loop(loop, plan_name)
    await state_manager.link_loop_to_phase(loop.id, plan_name, phase_name)

    # Retrieve phase via loop
    retrieved = await state_manager.get_phase_by_loop(loop.id)

    # Compare
    original_data = sample_phase.model_dump(exclude={'id'})
    retrieved_data = retrieved.model_dump(exclude={'id'})

    assert original_data == retrieved_data, 'Loop-to-phase mapping altered phase data'


@pytest.mark.asyncio
async def test_update_phase_by_loop_preserves_frozen_fields(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    """Verify updating phase via loop also preserves frozen fields.

    Note: update_phase_by_loop calls update_phase internally, which preserves frozen fields
    during refinement iterations. This is the expected behavior for loop-based updates.
    """
    # Store phase and link to loop
    phase_name = await state_manager.store_phase(plan_name, sample_phase)

    loop = LoopState(loop_type=LoopType.PHASE)
    await state_manager.add_loop(loop, plan_name)
    await state_manager.link_loop_to_phase(loop.id, plan_name, phase_name)

    # Create updated phase with attempted frozen field changes
    updated_phase = sample_phase.model_copy(
        update={
            'objectives': 'CHANGED objectives - should not persist',
            'testing_strategy': 'Updated testing strategy - should persist',
        }
    )

    await state_manager.update_phase_by_loop(loop.id, updated_phase)

    # Retrieve via loop
    retrieved = await state_manager.get_phase_by_loop(loop.id)

    # Verify frozen field unchanged, flexible field updated
    assert retrieved.objectives == sample_phase.objectives
    assert retrieved.testing_strategy == 'Updated testing strategy - should persist'
