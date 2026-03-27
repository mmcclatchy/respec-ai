"""Universal round-trip tests for all MCPModel subclasses.

These tests validate that parse → build → parse cycles preserve data integrity
for ANY MCPModel, regardless of field names or structure. Tests automatically
work when models change (add/remove/rename fields) without requiring updates.

Uses dynamic fixture generation (markdown_builder from conftest.py) to minimize
maintenance burden. When model structure changes, fixtures auto-adapt.
"""

from typing import Callable, Type

import pytest

from src.models.base import MCPModel
from src.models.enums import PhaseStatus, PlanStatus, RequirementsStatus, RoadmapStatus
from src.models.feature_requirements import FeatureRequirements
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.models.task import Task


@pytest.fixture
def sample_roadmap_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        Roadmap,
        plan_name='Test Plan',
        project_goal='Build a test system',
        total_duration='8 weeks',
        team_size='4 developers',
        roadmap_budget='$100,000',
        critical_path_analysis='Sequential phases',
        key_risks='Technical complexity',
        mitigation_plans='Incremental delivery',
        buffer_time='1 week',
        development_resources='4 developers',
        infrastructure_requirements='Cloud hosting',
        external_dependencies='None',
        quality_assurance_plan='Automated testing',
        technical_milestones='MVP delivery',
        business_milestones='User acceptance',
        quality_gates='All tests pass',
        performance_targets='Fast response',
        roadmap_status=RoadmapStatus.DRAFT,
        phase_count=1,
    )


@pytest.fixture
def sample_phase_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        Phase,
        phase_name='test-phase',
        objectives='Implement authentication',
        scope='Login and logout',
        dependencies='User database',
        deliverables='Auth service',
        architecture='Microservice architecture',
        technology_stack='Python FastAPI',
        functional_requirements='User login with email',
        non_functional_requirements='Response time < 200ms',
        development_plan='Phase 1: Backend',
        testing_strategy='Unit tests',
        research_requirements='JWT best practices',
        success_criteria='100% test coverage',
        integration_context='Connects to user service',
        phase_status=PhaseStatus.DRAFT,
    )


@pytest.fixture
def sample_plan_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        Plan,
        plan_name='Test Portal',
        executive_summary='### Vision\nTransform user experience\n\n### Mission\nDeliver user-friendly portal\n\n### Timeline\n8 months\n\n### Budget\n$400,000',
        business_objectives='### Primary Objectives\nImprove satisfaction\n\n### Success Metrics\nScore >4.5/5\n\n### Key Performance Indicators\nDaily active users',
        plan_scope='### Included Features\nUser dashboard\n\n### Anti-Requirements\nLegacy migration\n\n### Assumptions\nInfrastructure ready\n\n### Constraints\n99.9% uptime',
        stakeholders='### Plan Sponsor\nCTO Sarah Johnson\n\n### Key Stakeholders\nCustomer Success team\n\n### End Users\n5000+ active users',
        architecture_direction='### Architecture Overview\nReact SPA frontend\n\n### Data Flow\nClient → API → DB',
        technology_decisions='### Chosen Technologies\nReact.js frontend\n\n### Rejected Technologies\nNone',
        plan_structure='### Work Breakdown\nPhase 1: Design\n\n### Phases Overview\nDiscovery and research\n\n### Dependencies\nDesign system',
        resource_requirements='### Team Structure\n1 Plan Manager\n\n### Technology Requirements\nReact.js frontend\n\n### Infrastructure Needs\nAWS instances',
        risk_management='### Identified Risks\nTimeline delays\n\n### Mitigation Strategies\nRegular reviews\n\n### Contingency Plans\nSimplified design',
        quality_assurance='### Quality Bar\nWCAG 2.1 AA\n\n### Testing Strategy\nUnit testing\n\n### Acceptance Criteria\nAll tests pass',
        plan_status=PlanStatus.ACTIVE,
    )


@pytest.fixture
def sample_task_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        Task,
        name='task-1-auth',
        phase_path='test-platform/phase-1-foundation',
        goal='Implement OAuth2 authentication with JWT tokens',
        acceptance_criteria='Users can register, login, and access protected endpoints',
        tech_stack_reference='FastAPI, Python 3.13+, JWT, OAuth2',
        implementation_checklist='- [ ] Setup OAuth2\n- [ ] Create endpoints\n- [ ] Add tests',
        implementation_steps='#### Step 1: Setup\nInstall packages and configure OAuth2',
        testing_strategy='Unit tests for auth logic, integration tests for endpoints',
        research='Documents successfully read:\n- `.best-practices/jwt-best-practices.md`',
        status='pending',
        active='true',
        version='1.0',
    )


@pytest.fixture
def sample_feature_requirements_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        FeatureRequirements,
        plan_name='User Authentication',
        feature_description='Secure login system',
        problem_statement='Users need secure authentication',
        target_users='All application users',
        business_value='Improve security',
        user_stories='As a user I can login',
        acceptance_criteria='Login succeeds',
        user_experience_goals='Seamless login flow',
        functional_requirements='Email/password login',
        non_functional_requirements='Response < 200ms',
        integration_requirements='OAuth integration',
        user_metrics='Login success rate',
        performance_metrics='Response time',
        technical_metrics='API uptime',
        must_have_features='Login and logout',
        should_have_features='Password reset',
        could_have_features='Social login',
        wont_have_features='Biometric auth',
        requirements_status=RequirementsStatus.DRAFT,
    )


@pytest.mark.parametrize(
    'model_class,fixture_name',
    [
        (Roadmap, 'sample_roadmap_markdown'),
        (Phase, 'sample_phase_markdown'),
        (Plan, 'sample_plan_markdown'),
        (Task, 'sample_task_markdown'),
        (FeatureRequirements, 'sample_feature_requirements_markdown'),
    ],
)
def test_mcp_model_round_trip_idempotency(
    model_class: Type[MCPModel], fixture_name: str, request: pytest.FixtureRequest
) -> None:
    """Universal test: parse → build → parse preserves ALL fields for ANY MCPModel.

    This test automatically works for all MCPModel subclasses without requiring
    updates when fields are added, removed, or renamed. Uses model_dump() to
    compare all fields dynamically.
    """
    sample_markdown = request.getfixturevalue(fixture_name)

    original = model_class.parse_markdown(sample_markdown)
    rebuilt_markdown = original.build_markdown()
    reparsed = model_class.parse_markdown(rebuilt_markdown)

    original_data = original.model_dump(exclude={'id', 'phases'})
    reparsed_data = reparsed.model_dump(exclude={'id', 'phases'})

    assert original_data == reparsed_data, f'{model_class.__name__} round-trip changed field values'


def test_markdown_stabilization_after_first_round_trip(sample_roadmap_markdown: str) -> None:
    """Verify markdown output stabilizes after first round-trip.

    The first build may normalize formatting, but subsequent builds should
    produce identical output (character-for-character).
    """
    first_parse = Roadmap.parse_markdown(sample_roadmap_markdown)
    first_build = first_parse.build_markdown()

    second_parse = Roadmap.parse_markdown(first_build)
    second_build = second_parse.build_markdown()

    assert first_build == second_build, 'Markdown format should stabilize after first round-trip'
