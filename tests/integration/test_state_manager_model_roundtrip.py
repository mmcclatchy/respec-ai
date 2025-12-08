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
from src.models.build_plan import BuildPlan
from src.models.enums import BuildStatus, ProjectStatus, RoadmapStatus, SpecStatus
from src.utils.enums import LoopType
from src.models.plan_completion_report import PlanCompletionReport
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec
from src.utils.loop_state import LoopState
from src.utils.state_manager import InMemoryStateManager, StateManager
from src.utils.state_manager.postgres import PostgresStateManager


from src.utils.database_pool import db_pool
from src.mcp.tools.build_plan_tools import BuildPlanTools
from src.mcp.tools.plan_completion_report_tools import PlanCompletionReportTools


@pytest.fixture
def project_name() -> str:
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
                    'technical_specs, project_plans, loop_to_spec_mappings CASCADE'
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
                        'technical_specs, project_plans, loop_to_spec_mappings CASCADE'
                    )
            except Exception:
                pass
            finally:
                await db_pool.close()


@pytest.fixture
def sample_roadmap(markdown_builder: Callable) -> Roadmap:
    markdown = markdown_builder(
        Roadmap,
        project_name='Integration Test Roadmap',
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
        spec_count=3,
    )
    return Roadmap.parse_markdown(markdown)


@pytest.fixture
def sample_spec(markdown_builder: Callable) -> TechnicalSpec:
    markdown = markdown_builder(
        TechnicalSpec,
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
        spec_status=SpecStatus.IMPLEMENTATION_READY,
        iteration=2,
        version=1,
    )
    return TechnicalSpec.parse_markdown(markdown)


@pytest.fixture
def sample_project_plan(markdown_builder: Callable) -> ProjectPlan:
    markdown = markdown_builder(
        ProjectPlan,
        project_name='Enterprise Portal Modernization',
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
        documentation_standards='OpenAPI specs, Architecture decision records',
        project_status=ProjectStatus.ACTIVE,
    )
    return ProjectPlan.parse_markdown(markdown)


@pytest.fixture
def sample_build_plan(markdown_builder: Callable) -> BuildPlan:
    markdown = markdown_builder(
        BuildPlan,
        project_name='Microservices Platform',
        project_goal='Build scalable event-driven microservices platform',
        total_duration='9 months',
        team_size='7 backend engineers',
        primary_language='Python 3.11+',
        framework='FastAPI with async/await',
        database='PostgreSQL 16 with TimescaleDB',
        development_environment='Docker Compose for local, Kubernetes for staging',
        database_schema='Event sourcing with CQRS pattern',
        api_architecture='RESTful + GraphQL + gRPC for inter-service',
        frontend_architecture='React with TypeScript and React Query',
        core_features='Event processing, Real-time updates, Analytics dashboard',
        integration_points='Stripe payments, SendGrid email, Datadog monitoring',
        testing_strategy='Pytest with 90% coverage, Contract testing with Pact',
        code_standards='Black formatter, Ruff linter, MyPy strict mode',
        performance_requirements='10k req/s throughput, <50ms p99 latency',
        security_implementation='mTLS between services, RBAC, Secret rotation',
        build_status=BuildStatus.IN_PROGRESS,
    )
    return BuildPlan.parse_markdown(markdown)


@pytest.fixture
def sample_completion_report(markdown_builder: Callable) -> PlanCompletionReport:
    markdown = markdown_builder(
        PlanCompletionReport,
        report_title='Phase 1 Authentication Service Completion',
        final_plan_score='92',
        completion_summary='Successfully delivered authentication service with OAuth2 and MFA',
        achievements='Implemented all core features, Passed security audit, Deployed to production',
        remaining_work='Performance optimization, Additional OAuth providers',
        quality_assessment='High code quality, Good test coverage (89%), Well documented',
        recommendations='Monitor performance metrics, Schedule monthly security reviews',
        lessons_learned='Early security review saved time, Staging environment critical for testing',
    )
    return PlanCompletionReport.parse_markdown(markdown)


# ============================================================================
# Roadmap Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_roadmap_store_retrieve_preserves_all_fields(
    state_manager: StateManager, project_name: str, sample_roadmap: Roadmap
) -> None:
    """Verify storing and retrieving Roadmap preserves all field values."""
    # Store roadmap
    await state_manager.store_roadmap(project_name, sample_roadmap)

    # Retrieve roadmap
    retrieved = await state_manager.get_roadmap(project_name)

    # Compare all fields (exclude dynamic fields like id)
    original_data = sample_roadmap.model_dump(exclude={'id', 'specs'})
    retrieved_data = retrieved.model_dump(exclude={'id', 'specs'})

    assert original_data == retrieved_data, 'Roadmap round-trip changed field values'


@pytest.mark.asyncio
async def test_roadmap_multiple_updates_preserve_latest(
    state_manager: StateManager, project_name: str, sample_roadmap: Roadmap
) -> None:
    """Verify updating roadmap multiple times preserves latest version."""
    # Store initial roadmap
    await state_manager.store_roadmap(project_name, sample_roadmap)

    # Update roadmap with new values
    updated_roadmap = sample_roadmap.model_copy(
        update={
            'roadmap_status': RoadmapStatus.COMPLETED,
            'project_goal': 'Updated project goal for completion',
        }
    )
    await state_manager.store_roadmap(project_name, updated_roadmap)

    # Retrieve and verify latest
    retrieved = await state_manager.get_roadmap(project_name)

    assert retrieved.roadmap_status == RoadmapStatus.COMPLETED
    assert retrieved.project_goal == 'Updated project goal for completion'


# ============================================================================
# TechnicalSpec Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_spec_store_retrieve_preserves_all_fields(
    state_manager: StateManager, project_name: str, sample_spec: TechnicalSpec
) -> None:
    """Verify storing and retrieving TechnicalSpec preserves all field values."""
    # Store spec
    spec_name = await state_manager.store_spec(project_name, sample_spec)

    # Retrieve spec
    retrieved = await state_manager.get_spec(project_name, spec_name)

    # Compare all fields
    original_data = sample_spec.model_dump(exclude={'id'})
    retrieved_data = retrieved.model_dump(exclude={'id'})

    assert original_data == retrieved_data, 'TechnicalSpec round-trip changed field values'


@pytest.mark.asyncio
async def test_spec_frozen_fields_preserved_on_update(
    state_manager: StateManager, project_name: str, sample_spec: TechnicalSpec
) -> None:
    """Verify frozen fields (objectives, scope, dependencies, deliverables) are preserved."""
    # Store original spec
    spec_name = await state_manager.store_spec(project_name, sample_spec)

    # Create updated spec with attempted changes to frozen fields
    updated_spec = sample_spec.model_copy(
        update={
            'objectives': 'CHANGED - should not persist',
            'scope': 'CHANGED - should not persist',
            'architecture': 'Updated architecture - should persist',
        }
    )

    await state_manager.update_spec(project_name, spec_name, updated_spec)

    # Retrieve and verify frozen fields unchanged
    retrieved = await state_manager.get_spec(project_name, spec_name)

    assert retrieved.objectives == sample_spec.objectives, 'Frozen field "objectives" was modified'
    assert retrieved.scope == sample_spec.scope, 'Frozen field "scope" was modified'
    assert retrieved.architecture == 'Updated architecture - should persist'


@pytest.mark.asyncio
async def test_spec_iteration_and_version_auto_increment(
    state_manager: StateManager, project_name: str, sample_spec: TechnicalSpec
) -> None:
    """Verify iteration and version auto-increment on duplicate spec names."""
    # Store spec twice with same name
    await state_manager.store_spec(project_name, sample_spec)

    # Store again with same phase_name
    duplicate_spec = sample_spec.model_copy()
    await state_manager.store_spec(project_name, duplicate_spec)

    # Retrieve - should have incremented iteration/version
    retrieved = await state_manager.get_spec(project_name, sample_spec.phase_name)

    assert retrieved.iteration > sample_spec.iteration or retrieved.version > sample_spec.version


# ============================================================================
# ProjectPlan Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_project_plan_store_retrieve_preserves_all_fields(
    state_manager: StateManager, sample_project_plan: ProjectPlan
) -> None:
    """Verify storing and retrieving ProjectPlan preserves all 31 string fields."""
    project_name = sample_project_plan.project_name

    # Store project plan
    await state_manager.store_project_plan(project_name, sample_project_plan)

    # Retrieve project plan
    retrieved = await state_manager.get_project_plan(project_name)

    # Compare all fields
    original_data = sample_project_plan.model_dump()
    retrieved_data = retrieved.model_dump()

    assert original_data == retrieved_data, 'ProjectPlan round-trip changed field values'


@pytest.mark.asyncio
async def test_project_plan_update_overwrites_completely(
    state_manager: StateManager, sample_project_plan: ProjectPlan
) -> None:
    """Verify updating ProjectPlan replaces all fields."""
    project_name = sample_project_plan.project_name

    # Store original
    await state_manager.store_project_plan(project_name, sample_project_plan)

    # Create updated version with different values
    updated_plan = sample_project_plan.model_copy()
    updated_plan.project_status = ProjectStatus.COMPLETED
    updated_plan.project_budget = '$3M'
    updated_plan.team_structure = '3 PMs, 12 Engineers'

    await state_manager.store_project_plan(project_name, updated_plan)

    # Retrieve and verify updates
    retrieved = await state_manager.get_project_plan(project_name)

    assert retrieved.project_status == ProjectStatus.COMPLETED
    assert retrieved.project_budget == '$3M'
    assert retrieved.team_structure == '3 PMs, 12 Engineers'


# ============================================================================
# BuildPlan Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_build_plan_store_retrieve_preserves_all_fields(
    state_manager: StateManager, sample_build_plan: BuildPlan
) -> None:
    """Verify storing and retrieving BuildPlan preserves all field values."""
    # Create loop for build plan
    loop = LoopState(loop_type=LoopType.BUILD_PLAN)
    await state_manager.add_loop(loop, 'test-project')

    # Store build plan (build plans use loop_id as key)

    tools = BuildPlanTools(state_manager)
    await tools.store_build_plan(loop.id, sample_build_plan)

    # Retrieve build plan
    retrieved = await tools.get_build_plan_data(loop.id)

    # Compare all fields
    original_data = sample_build_plan.model_dump()
    retrieved_data = retrieved.model_dump()

    assert original_data == retrieved_data, 'BuildPlan round-trip changed field values'


# ============================================================================
# PlanCompletionReport Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_completion_report_store_retrieve_preserves_all_fields(
    state_manager: StateManager, sample_completion_report: PlanCompletionReport
) -> None:
    """Verify storing and retrieving PlanCompletionReport preserves all field values."""
    # Create loop for completion report
    loop = LoopState(loop_type=LoopType.PLAN)
    await state_manager.add_loop(loop, 'test-project')

    # Store completion report (uses loop_id and project_path)

    tools = PlanCompletionReportTools(state_manager)
    await tools.create_completion_report('/tmp/test', sample_completion_report, loop.id)

    # Retrieve completion report
    retrieved = await tools.get_completion_report_data('/tmp/test', loop.id)

    # Compare all fields
    original_data = sample_completion_report.model_dump()
    retrieved_data = retrieved.model_dump()

    assert original_data == retrieved_data, 'PlanCompletionReport round-trip changed field values'


# ============================================================================
# Cross-Implementation Consistency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_both_implementations_produce_identical_results(
    inmemory_manager: StateManager,
    postgres_manager: StateManager,
    project_name: str,
    sample_roadmap: Roadmap,
) -> None:
    """Verify InMemory and Postgres implementations produce identical results."""
    # Store in both managers
    await inmemory_manager.store_roadmap(project_name, sample_roadmap)
    await postgres_manager.store_roadmap(project_name, sample_roadmap)

    # Retrieve from both
    inmemory_result = await inmemory_manager.get_roadmap(project_name)
    postgres_result = await postgres_manager.get_roadmap(project_name)

    # Compare results
    inmemory_data = inmemory_result.model_dump(exclude={'id', 'specs'})
    postgres_data = postgres_result.model_dump(exclude={'id', 'specs'})

    assert inmemory_data == postgres_data, 'InMemory and Postgres implementations differ'


# ============================================================================
# Loop-to-Spec Mapping Round-Trip Tests
# ============================================================================


@pytest.mark.asyncio
async def test_loop_spec_mapping_preserves_spec_data(
    state_manager: StateManager, project_name: str, sample_spec: TechnicalSpec
) -> None:
    """Verify loop-to-spec mapping preserves spec data through refinement cycle."""
    # Store spec
    spec_name = await state_manager.store_spec(project_name, sample_spec)

    # Create loop and link to spec
    loop = LoopState(loop_type=LoopType.SPEC)
    await state_manager.add_loop(loop, project_name)
    await state_manager.link_loop_to_spec(loop.id, project_name, spec_name)

    # Retrieve spec via loop
    retrieved = await state_manager.get_spec_by_loop(loop.id)

    # Compare
    original_data = sample_spec.model_dump(exclude={'id'})
    retrieved_data = retrieved.model_dump(exclude={'id'})

    assert original_data == retrieved_data, 'Loop-to-spec mapping altered spec data'


@pytest.mark.asyncio
async def test_update_spec_by_loop_preserves_frozen_fields(
    state_manager: StateManager, project_name: str, sample_spec: TechnicalSpec
) -> None:
    """Verify updating spec via loop also preserves frozen fields.

    Note: update_spec_by_loop calls store_spec internally, which preserves frozen fields
    on conflict/update operations. This matches update_spec behavior.
    """
    # Store spec and link to loop
    spec_name = await state_manager.store_spec(project_name, sample_spec)

    loop = LoopState(loop_type=LoopType.SPEC)
    await state_manager.add_loop(loop, project_name)
    await state_manager.link_loop_to_spec(loop.id, project_name, spec_name)

    # Create updated spec with attempted frozen field changes
    updated_spec = sample_spec.model_copy(
        update={
            'objectives': 'CHANGED objectives - should not persist',
            'testing_strategy': 'Updated testing strategy - should persist',
        }
    )

    await state_manager.update_spec_by_loop(loop.id, updated_spec)

    # Retrieve via loop
    retrieved = await state_manager.get_spec_by_loop(loop.id)

    # Verify frozen field unchanged, flexible field updated
    assert retrieved.objectives == sample_spec.objectives
    assert retrieved.testing_strategy == 'Updated testing strategy - should persist'
