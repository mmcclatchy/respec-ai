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
from src.models.build_plan import BuildPlan
from src.models.enums import BuildStatus, ProjectStatus, RequirementsStatus, RoadmapStatus, SpecStatus
from src.models.feature_requirements import FeatureRequirements
from src.models.project_plan import ProjectPlan
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec


@pytest.fixture
def sample_roadmap_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        Roadmap,
        project_name='Test Project',
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
        spec_count=1,
    )


@pytest.fixture
def sample_spec_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        TechnicalSpec,
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
        spec_status=SpecStatus.DRAFT,
    )


@pytest.fixture
def sample_project_plan_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        ProjectPlan,
        project_name='Test Portal',
        project_vision='Transform user experience',
        project_mission='Deliver user-friendly portal',
        project_timeline='8 months',
        project_budget='$400,000',
        primary_objectives='Improve satisfaction',
        success_metrics='Score >4.5/5',
        key_performance_indicators='Daily active users',
        included_features='User dashboard',
        excluded_features='Legacy migration',
        project_assumptions='Infrastructure ready',
        project_constraints='99.9% uptime',
        project_sponsor='CTO Sarah Johnson',
        key_stakeholders='Customer Success team',
        end_users='5000+ active users',
        work_breakdown='Phase 1: Design',
        phases_overview='Discovery and research',
        project_dependencies='Design system',
        team_structure='1 Project Manager',
        technology_requirements='React.js frontend',
        infrastructure_needs='AWS instances',
        identified_risks='Timeline delays',
        mitigation_strategies='Regular reviews',
        contingency_plans='Simplified design',
        quality_standards='WCAG 2.1 AA',
        testing_strategy='Unit testing',
        documentation_standards='API documentation',
        project_status=ProjectStatus.ACTIVE,
    )


@pytest.fixture
def sample_build_plan_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        BuildPlan,
        project_name='Test Platform',
        project_goal='Build scalable platform',
        total_duration='6 months',
        team_size='5 developers',
        primary_language='Python',
        framework='FastAPI',
        database='PostgreSQL',
        development_environment='Docker-based development',
        database_schema='User tables',
        api_architecture='RESTful API',
        frontend_architecture='React SPA',
        core_features='User authentication',
        integration_points='Payment gateway',
        testing_strategy='Unit tests',
        code_standards='PEP 8',
        performance_requirements='Sub-2s page loads',
        security_implementation='HTTPS and JWT',
        build_status=BuildStatus.PLANNING,
    )


@pytest.fixture
def sample_feature_requirements_markdown(markdown_builder: Callable) -> str:
    return markdown_builder(
        FeatureRequirements,
        project_name='User Authentication',
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
        (TechnicalSpec, 'sample_spec_markdown'),
        (ProjectPlan, 'sample_project_plan_markdown'),
        (BuildPlan, 'sample_build_plan_markdown'),
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

    original_data = original.model_dump(exclude={'id', 'specs'})
    reparsed_data = reparsed.model_dump(exclude={'id', 'specs'})

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
