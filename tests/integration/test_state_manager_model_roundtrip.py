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

from typing import Callable

import pytest

from src.models.enums import PhaseStatus, PlanStatus, RoadmapStatus, ShapeGate
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
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
def postgres_manager(db_state_manager: PostgresStateManager) -> StateManager:
    return db_state_manager


@pytest.fixture(params=['inmemory_manager', 'db_state_manager'])
def state_manager(request: pytest.FixtureRequest) -> StateManager:
    """Parameterized fixture providing both StateManager implementations.

    Tests using this fixture will run twice - once with InMemoryStateManager
    and once with PostgresStateManager.
    """
    return request.getfixturevalue(request.param)


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
def sample_phase_with_design_shape() -> Phase:
    # Constructed directly (not via markdown_builder) so every design-shape field gets
    # a distinct, recognizable value -- this is the fixture B3 needs to catch a
    # transposed positional parameter in the postgres UPSERT (finding F13): a swap
    # surfaces as "field A came back holding field B's value," which only a
    # field-by-field equality assertion with distinct values can catch.
    return Phase(
        phase_name='design-layer-phase',
        objectives='Give the design layer a real owner (findings F1-F4)',
        scope='Module Layout, Skeleton Index, Collaboration And Wiring, Test List, Design Decisions',
        dependencies='Phase 1 bundle restructure',
        deliverables='Architect names concrete modules and seams; coder consumes them',
        module_layout='- src/auth/oauth_client.py — OAuth2 handshake and token exchange\n- src/auth/token_store.py — refresh token persistence',
        skeleton_index='- src/auth/oauth_client.py :: OAuthClient.exchange_code(code: str) -> TokenPair',
        collaboration_and_wiring='AuthService constructs OAuthClient and injects TokenStore at startup',
        test_list='- test_refresh_token_rotates_on_use\n- test_expired_token_triggers_reauth',
        open_design_decisions='OD-1: whether refresh tokens rotate on every use or only near expiry',
        settled_design_decisions='SD-1: use JWT with RS256 (source=architect) — rationale: supports key rotation',
        shape_gate=ShapeGate.SHAPE_PROPOSED,
        phase_status=PhaseStatus.IMPLEMENTATION_READY,
        iteration=2,
        version=1,
    )


@pytest.fixture
def sample_plan(markdown_builder: Callable) -> Plan:
    markdown = markdown_builder(
        Plan,
        plan_name='Enterprise Portal Modernization',
        executive_summary='### Vision\nTransform legacy portal into modern cloud-native platform\n\n### Mission\nDeliver scalable, maintainable portal with improved UX\n\n### Timeline\n18 months\n\n### Budget\n$2.5M',
        business_objectives='### Primary Objectives\nMigrate to microservices, Improve performance 10x\n\n### Success Metrics\nUser satisfaction >4.5/5, Page load time <1s\n\n### Key Performance Indicators\nDaily active users, API response times, Error rates',
        plan_scope='### Included Features\nUser dashboard, Analytics, Reporting, Admin tools\n\n### Anti-Requirements\nLegacy system maintenance, Custom integrations\n\n### Assumptions\nInfrastructure team available, Cloud budget approved\n\n### Constraints\nMust maintain 99.9% uptime during migration',
        stakeholders='### Plan Sponsor\nVP Engineering Jane Smith\n\n### Key Stakeholders\nProduct, Engineering, Customer Success, Security\n\n### End Users\n50,000+ enterprise customers',
        architecture_direction='### Architecture Overview\nKubernetes microservices with API gateway\n\n### Data Flow\nClient → API Gateway → Services → PostgreSQL',
        technology_decisions='### Chosen Technologies\nKubernetes, PostgreSQL, React, FastAPI\n\n### Rejected Technologies\nMonolith approach rejected for scalability',
        plan_structure='### Work Breakdown\nPhase 1: Backend, Phase 2: Frontend, Phase 3: Migration\n\n### Phases Overview\nDiscovery (2mo), Development (12mo), Rollout (4mo)\n\n### Dependencies\nDesign system library, CI/CD pipeline',
        resource_requirements='### Team Structure\n2 PMs, 8 Engineers, 2 QA, 1 DevOps\n\n### Technology Requirements\nKubernetes, PostgreSQL, React, FastAPI\n\n### Infrastructure Needs\n3 Kubernetes clusters, CDN, Monitoring stack',
        risk_management='### Identified Risks\nData migration errors, Performance degradation\n\n### Mitigation Strategies\nStaged rollout, Comprehensive testing, Rollback plan\n\n### Contingency Plans\nExtended timeline, Reduced scope, Additional resources',
        quality_assurance='### Quality Bar\nWCAG 2.1 AA, SOC 2 compliance\n\n### Testing Strategy\nUnit, Integration, E2E, Load testing\n\n### Acceptance Criteria\nAll tests pass, Performance targets met',
        plan_status=PlanStatus.ACTIVE,
    )
    return Plan.parse_markdown(markdown)


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
async def test_store_phase_preserves_frozen_fields(
    state_manager: StateManager, plan_name: str, sample_phase: Phase
) -> None:
    # Finding F10: store_phase is the terminal call of the store_document ->
    # PhaseTools.store -> store_phase path the live phase workflow actually uses, so it
    # must preserve frozen fields the same way update_phase already does. This test
    # previously asserted the opposite (full replacement) -- that was the bug, not the
    # spec; see docs/phase-refactor/findings.md F10.
    phase_name = await state_manager.store_phase(plan_name, sample_phase)

    updated_phase = sample_phase.model_copy(
        update={
            'objectives': 'UPDATED objectives - should NOT persist',
            'scope': 'UPDATED scope - should NOT persist',
            'architecture': 'Updated architecture - should persist',
        }
    )

    await state_manager.store_phase(plan_name, updated_phase)

    retrieved = await state_manager.get_phase(plan_name, phase_name)

    assert retrieved.objectives == sample_phase.objectives, 'store_phase must preserve frozen objectives'
    assert retrieved.scope == sample_phase.scope, 'store_phase must preserve frozen scope'
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
async def test_design_shape_fields_survive_store_and_retrieve(
    state_manager: StateManager, plan_name: str, sample_phase_with_design_shape: Phase
) -> None:
    # B1/B3 (docs/phase-refactor/phase-2-design-layer.md): every Design Shape / Design
    # Decisions field must round-trip intact on both backends. Field-by-field equality
    # with distinct values per field is what catches a transposed positional parameter
    # in the postgres UPSERT (finding F13) -- a swap surfaces as "field A came back
    # holding field B's value."
    phase_name = await state_manager.store_phase(plan_name, sample_phase_with_design_shape)

    retrieved = await state_manager.get_phase(plan_name, phase_name)

    original_data = sample_phase_with_design_shape.model_dump(exclude={'id'})
    retrieved_data = retrieved.model_dump(exclude={'id'})

    assert original_data == retrieved_data, 'Design Shape fields did not survive store/retrieve intact'


@pytest.mark.asyncio
async def test_design_shape_fields_survive_alongside_frozen_field_preservation(
    state_manager: StateManager, plan_name: str, sample_phase_with_design_shape: Phase
) -> None:
    # B4: adding the design-layer columns must not disturb frozen-field preservation
    # (findings F10/F12) -- an agent write that touches design-shape fields should
    # still leave roadmap-seeded objectives/scope/dependencies/deliverables untouched.
    phase_name = await state_manager.store_phase(plan_name, sample_phase_with_design_shape)

    agent_revision = sample_phase_with_design_shape.model_copy(
        update={
            'objectives': 'CHANGED by agent - should not persist',
            'module_layout': '- src/auth/oauth_client.py — revised after critic feedback',
        }
    )
    await state_manager.store_phase(plan_name, agent_revision)

    retrieved = await state_manager.get_phase(plan_name, phase_name)

    assert retrieved.objectives == sample_phase_with_design_shape.objectives
    assert retrieved.module_layout == '- src/auth/oauth_client.py — revised after critic feedback'


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
    updated_plan.executive_summary = '### Vision\nUpdated vision\n\n### Budget\n$3M'
    updated_plan.resource_requirements = '### Team Structure\n3 PMs, 12 Engineers'

    await state_manager.store_plan(plan_name, updated_plan)

    # Retrieve and verify updates
    retrieved = await state_manager.get_plan(plan_name)

    assert retrieved.plan_status == PlanStatus.COMPLETED
    assert '$3M' in retrieved.executive_summary
    assert '3 PMs, 12 Engineers' in retrieved.resource_requirements


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
