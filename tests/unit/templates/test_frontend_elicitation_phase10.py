"""Behaviors B1-B11 from docs/frontend-refactor/phase-10-frontend-elicitation.md.

B5 (round-trip on both state managers) is pinned in
tests/integration/test_state_manager_model_roundtrip.py via
sample_phase_with_design_shape.design_shape_additional, which carries a
`#### Design Research` block -- src/models/phase.py has zero code changes in this
phase, same placement argument phase 4 made for the UX Contract (decisions.md
"Design Source is a decision, not a field").

B10 (phase 8's local-bundle portability invariant) is a regression guard already
pinned in the phase 8 test suite; this phase must not need to touch it, so it is
not re-pinned here.

The command-side research gate (B6, B7, B9, B11 and B8's Step 16.5 wiring) was retired by
docs/phase-cooperative/phase-2-cooperative-flow.md: research approval now runs at the briefing
and design review, and its re-anchored tests (B12, B13, B15) live in
test_phase_cooperative_flow.py.
"""

from template_contract import template_contract

from src.platform.template_helpers import (
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
)
from src.platform.templates.agents import (
    generate_phase_architect_template,
    generate_phase_critic_template,
)
from src.platform.tui_adapters import ClaudeCodeAdapter


_adapter = ClaudeCodeAdapter()


def _architect_template() -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))


def _critic_template() -> str:
    tools = create_phase_critic_agent_tools(_adapter)
    return generate_phase_critic_template(tools)


# ---------------------------------------------------------------------------
# B1 / B2 - the architect's new decision classes, and the backend regression guard
# ---------------------------------------------------------------------------


def test_ui_phase_shape_output_requires_state_ownership_decomposition_and_provenance() -> None:
    template = _architect_template()

    assert 'state ownership' in template.lower()
    assert 'screen decomposition' in template.lower()
    assert 'component provenance' in template.lower()
    assert 'IF this phase delivers a user-facing UI' in template


def test_design_source_is_emitted_as_the_first_od_on_a_ui_phase() -> None:
    template = _architect_template()

    assert 'OD-001' in template
    assert 'Visual design source for this phase' in template
    assert 'upstream of' in template.lower()


def test_backend_only_phase_gets_none_of_the_new_frontend_machinery() -> None:
    # B2 is the regression guard: this phase must cost existing backend users nothing.
    # The UX Contract's own backend-only exemption ("A backend-only phase emits no
    # `#### UX Contract` at all") is the existing anchor this phase must extend, not
    # duplicate with a second, separately-drifting predicate.
    template = _architect_template()

    assert 'A backend-only phase' in template
    assert 'emits no `#### UX Contract` at all' in template
    assert 'gets none of this phase' in template.lower()


def test_collaboration_and_wiring_carries_the_state_ownership_map_on_ui_phases() -> None:
    template = _architect_template()

    assert 'state-ownership map' in template.lower()


def test_architect_does_not_add_a_component_inventory_section() -> None:
    # decisions.md "Frontend granularity is a setting on existing dials, not a new
    # mode" -- the Skeleton Index already carries components; a second list would drift.
    template = _architect_template()

    assert 'Do NOT add a component-inventory section' in template


# ---------------------------------------------------------------------------
# B3 / B4 - the critic
# ---------------------------------------------------------------------------


def test_critic_blocks_a_ui_phase_missing_any_of_the_three_decision_classes() -> None:
    conditions = template_contract(_critic_template()).blocker_conditions()

    assert 'missing-state-ownership-decision' in conditions
    assert 'undecided-screen-decomposition' in conditions
    assert 'missing-component-provenance-decision' in conditions


def test_critic_blocks_a_ui_phase_with_no_design_source_decision() -> None:
    conditions = template_contract(_critic_template()).blocker_conditions()

    assert 'missing-design-source-decision' in conditions


def test_critic_never_blocks_or_questions_on_research() -> None:
    # B4, re-anchored by phase-cooperative B17: declining research is a legitimate choice. A
    # critic finding about research coverage or a declined proposal converts the opt-in into
    # a mandate and defeats the entire cost design.
    contract = template_contract(_critic_template())
    findings = contract.blocker_conditions() | contract.judgment_findings()

    assert findings
    assert not any('design-research' in f or 'declined' in f or 'coverage' in f for f in findings)
    assert contract.report_section('## Research proposals') == ['- None']


def test_critic_decision_presence_checks_stay_inside_binding_scope() -> None:
    template = _critic_template()

    assert 'BINDING SCOPE' in template
    scope_start = template.index('BINDING SCOPE')
    scope_section = template[scope_start : scope_start + 2000]
    assert 'state ownership' in scope_section.lower() or 'Design Source' in scope_section
