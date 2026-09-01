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
"""

import pytest
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_helpers import (
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
)
from src.platform.templates.agents import (
    generate_phase_architect_template,
    generate_phase_critic_template,
)
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter

_ADAPTERS = [ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter()]
_adapter = ClaudeCodeAdapter()


def _phase_command_template(adapter: TuiAdapter) -> str:
    return TemplateCoordinator().generate_command_template(
        RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=adapter
    )


def _architect_template() -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))


def _critic_template() -> str:
    tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40_000, phase_shape_soft_cap=10_000)
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


def test_design_research_records_kb_cache_hits_and_gaps_on_ui_phases() -> None:
    template = _architect_template()

    assert '#### Design Research' in template
    assert 'Gap:' in template
    assert 'is a statement, not a request' in template


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


def test_critic_never_blocks_or_deducts_on_design_research() -> None:
    # B4: declining research is a legitimate choice. A critic that penalizes it
    # converts the opt-in into a mandate and defeats the entire cost design -- the
    # quietest way this phase could fail, per decisions.md.
    template = _critic_template()

    assert 'Design Research' in template
    assert 'never' in template.lower()
    conditions = template_contract(template).blocker_conditions()
    assert not any('design-research' in c for c in conditions)


def test_critic_decision_presence_checks_stay_inside_binding_scope() -> None:
    template = _critic_template()

    assert 'BINDING SCOPE' in template
    scope_start = template.index('BINDING SCOPE')
    scope_section = template[scope_start : scope_start + 2000]
    assert 'state ownership' in scope_section.lower() or 'Design Source' in scope_section


# ---------------------------------------------------------------------------
# B6 / B7 / B9 / B11 - Step 5.5, the research gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_step_5_5_renders_and_blocks_for_a_response_on_every_tui(adapter: TuiAdapter) -> None:
    contract = template_contract(_phase_command_template(adapter))
    body = contract.step_body('5.5')

    assert 'multiSelect: true' in body
    assert 'WAIT for' in body


def test_declining_research_at_step_5_5_invokes_bp_zero_times() -> None:
    # B6: the cost invariant is absolute -- the "None" path must never reach Task(bp).
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('5.5')

    none_branch_start = body.index('IF selection is "None"')
    proceed_marker = body.index('Proceed to Step 6', none_branch_start)
    none_branch = body[none_branch_start:proceed_marker]

    assert 'Task(bp)' not in none_branch


def test_step_5_5_skips_silently_when_no_offerable_gaps_exist() -> None:
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('5.5')

    assert 'OFFERABLE_GAPS is empty' in body
    condition = contract.outcome_condition(body, 'Proceed to Step 6.')
    assert 'OFFERABLE_GAPS' in condition or 'None' in condition


def test_step_5_5_degrades_when_bp_is_unavailable_rather_than_terminating() -> None:
    # B9: Step 5.5 asked for optional enrichment, not a dependency -- unlike Step
    # 16.5, unavailability (not malformed bp output -- that stays a shared hard EXIT
    # per decisions.md) must never hard-exit here.
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('5.5')

    preflight_start = body.index('Preflight bp tool availability')
    proceed_marker = body.index('Launch bp Tasks IN PARALLEL', preflight_start)
    preflight_branch = body[preflight_start:proceed_marker]

    assert 'notice' in preflight_branch.lower()
    assert 'EXIT' not in preflight_branch
    assert 'Proceed to Step 6' in preflight_branch


def test_step_16_5_still_hard_exits_when_bp_is_unavailable() -> None:
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('16.5')

    assert 'EXIT' in body
    assert 'bp skill unavailable' in body


def test_step_5_5_idempotence_is_by_state_not_position() -> None:
    # B11: Step 11's refine path returns to Step 5, so Step 5.5 re-runs on every
    # shape iteration. A researched gap becomes a Read: entry; a declined gap is
    # marked [declined]; only a genuinely new gap reappears.
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('5.5')

    assert 'NOT marked [declined]' in body
    assert '[declined]' in body


def test_shape_act_refine_path_returns_to_step_5_so_step_5_5_always_reruns() -> None:
    template = _phase_command_template(_adapter)

    assert 'Return to Step 5' in template


# ---------------------------------------------------------------------------
# B8 - downstream wiring into Step 16.5
# ---------------------------------------------------------------------------


def test_step_16_5_seeds_existing_read_paths_from_design_research() -> None:
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('16.5')

    assert 'Design Research' in body
    assert 'EXISTING_READ_PATHS' in body


def test_step_16_5_emits_shape_act_sourced_paths_into_research_requirements() -> None:
    contract = template_contract(_phase_command_template(_adapter))
    body = contract.step_body('16.5')

    assert 'Source: shape-act' in body
