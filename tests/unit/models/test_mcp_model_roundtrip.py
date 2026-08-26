"""Universal round-trip tests for all MCPModel subclasses.

These tests validate that parse → build → parse cycles preserve data integrity
for ANY MCPModel, regardless of field names or structure. Tests automatically
work when models change (add/remove/rename fields) without requiring updates.

Uses dynamic fixture generation (markdown_builder from conftest.py) to minimize
maintenance burden. When model structure changes, fixtures auto-adapt.
"""

import typing
from enum import Enum
from typing import Any, Callable, ClassVar, Type

import pytest

from src.models.base import MCPModel
from src.models.enums import PhaseStatus, PlanStatus, RequirementsStatus, RoadmapStatus
from src.models.feature_requirements import FeatureRequirements
from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap


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


_ROUND_TRIP_SENTINEL = '- round-trip sentinel content'
_INT_SENTINEL = 7

_TITLE_VALUES: dict[str, str] = {
    'phase_name': 'round-trip-probe',
    'plan_name': 'Round Trip Probe',
}


def _unwrap_optional(annotation: Any) -> Any:
    non_none = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
    return non_none[0] if non_none else annotation


def _probe_value(model_class: Type[MCPModel], field_name: str) -> Any:
    """A value distinguishable from the field's default, or None if the type can't carry one."""
    field_info = model_class.model_fields[field_name]
    base_type = _unwrap_optional(field_info.annotation)

    if base_type is str:
        return _ROUND_TRIP_SENTINEL
    if base_type is int:
        return _INT_SENTINEL
    if isinstance(base_type, type) and issubclass(base_type, Enum):
        # A member differing from the default, so a dropped field cannot pass by coincidence
        return next((member for member in base_type if member != field_info.default), None)
    return None


@pytest.mark.parametrize('model_class', [Roadmap, Phase, Plan, FeatureRequirements])
def test_every_mapped_field_survives_build_then_parse(model_class: Type[MCPModel]) -> None:
    """Every mapped field must survive build_markdown() -> parse_markdown().

    Distinct from the idempotency test above, which starts from markdown: a field that
    parse_markdown never populates is already None on the first parse, so parse -> build ->
    parse compares None to None and passes. Starting from a populated model is what catches
    a field whose extracted value is routed to a name that is not a model field.
    """
    title_field = model_class.TITLE_FIELD
    title_value = _TITLE_VALUES.get(title_field, 'round-trip-probe')

    lost_fields = []
    exercised = 0
    for field_name in model_class.HEADER_FIELD_MAPPING:
        if field_name == title_field or field_name not in model_class.model_fields:
            continue
        probe = _probe_value(model_class, field_name)
        if probe is None:
            continue
        exercised += 1
        instance = model_class(**{title_field: title_value, field_name: probe})
        reparsed = model_class.parse_markdown(instance.build_markdown())
        if getattr(reparsed, field_name, None) != probe:
            lost_fields.append(field_name)

    assert not lost_fields, (
        f'{model_class.__name__} lost these mapped fields on build -> parse: {lost_fields}. '
        'The extracted value is likely being stored under a name that is not a model field.'
    )
    assert exercised, f'{model_class.__name__} exercised no mapped fields; the probe builder is broken'


class _ListFieldProbeModel(MCPModel):
    """Exercises the list-extraction branch, which no shipped model currently reaches.

    Every mapped field on Phase/Plan/Roadmap/FeatureRequirements is scalar, so without this
    the list branch of parse_markdown would be unreachable and therefore untested.
    """

    TITLE_PATTERN: ClassVar[str] = '# Probe:'
    TITLE_FIELD: ClassVar[str] = 'probe_name'
    HEADER_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        'probe_items': ('Probe Section', 'Probe Items'),
    }

    probe_name: str = ''
    probe_items: list[str] | None = None

    def build_markdown(self) -> str:
        items = '\n'.join(f'- {item}' for item in self.probe_items or [])
        return f'# Probe: {self.probe_name}\n\n## Probe Section\n\n### Probe Items\n\n{items}\n'


def test_list_typed_mapped_field_round_trips_as_a_list() -> None:
    original = _ListFieldProbeModel(probe_name='probe', probe_items=['first item', 'second item'])

    reparsed = _ListFieldProbeModel.parse_markdown(original.build_markdown())

    assert reparsed.probe_items == ['first item', 'second item']


def test_scalar_field_named_like_a_list_is_not_routed_to_the_list_extractor() -> None:
    """Routing keys on the declared type, never on the field name.

    `Phase.test_list` is a str field whose name ends in `_list`; a name-based rule extracted
    it as a list and stored it under `test`, which is not a model field, so Pydantic dropped
    it and the section was silently lost on every store.
    """
    original = Phase(phase_name='probe', test_list='- `tests/unit/test_a.py::test_behavior`')

    reparsed = Phase.parse_markdown(original.build_markdown())

    assert reparsed.test_list == '- `tests/unit/test_a.py::test_behavior`'


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
