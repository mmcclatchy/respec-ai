"""Behaviors pinned for docs/frontend-refactor/phase-4-ux-contract.md.

B1/B2 (round-trip on both state managers) are pinned in
tests/integration/test_state_manager_model_roundtrip.py via
sample_phase_with_design_shape.design_shape_additional, since src/models/phase.py has
zero code changes in this phase -- see decisions.md "The UX Contract lives under
### Design Shape - Additional Sections". B3-B6 are pinned here against the generated
prompts.
"""

import pytest
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_helpers import (
    create_frontend_reviewer_agent_tools,
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
)
from src.platform.templates.agents import (
    generate_frontend_reviewer_template,
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


def test_design_shape_is_preserved_verbatim_so_the_ux_contract_survives_the_detail_act() -> None:
    # B3: the UX Contract lives inside `## Design Shape`, so the existing verbatim-
    # preservation guard for a settled shape gate already covers it without any new
    # instruction -- this is the property decisions.md's placement choice depends on.
    # This prose does not vary per adapter, so a single adapter is sufficient.
    template = generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))

    assert (
        'Preserve `## Design Shape` and `## Design Decisions` VERBATIM' in template
    ), 'Detail-act verbatim-preservation guard must cover the whole Design Shape H2, which is where the UX Contract lives'


def test_ux_contract_is_conditional_on_user_facing_ui_not_always_emitted() -> None:
    # B4: a backend-only phase must produce no UX Contract at all -- the instruction
    # must be conditional, never unconditional.
    template = generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))

    assert 'IF this phase delivers a user-facing UI' in template
    assert 'A backend-only phase' in template
    assert 'emits no `#### UX Contract` at all' in template


def test_critic_rejects_an_interaction_flow_with_no_observable_pass_condition() -> None:
    # B5: the automated half of the quality bar -- prose like "looks right" must be
    # rejected as a blocker whenever a UX Contract is present.
    tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40_000, phase_shape_soft_cap=10_000)
    template = generate_phase_critic_template(tools)

    assert 'ux-contract-flow-missing-pass-condition' in template_contract(template).blocker_conditions()
    assert 'the page looks right' in template.lower() or 'looks right' in template.lower()


def test_critic_rejects_a_route_index_entry_with_no_auth_requirement() -> None:
    tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40_000, phase_shape_soft_cap=10_000)
    template = generate_phase_critic_template(tools)

    assert 'ux-contract-route-missing-auth' in template_contract(template).blocker_conditions()


def test_ux_contract_blocker_rules_do_not_apply_when_no_contract_is_present() -> None:
    # The rules must be scoped to "when present" -- a backend-only phase must never
    # trip them.
    tools = create_phase_critic_agent_tools(_adapter, phase_length_soft_cap=40_000, phase_shape_soft_cap=10_000)
    template = generate_phase_critic_template(tools)

    assert 'does NOT apply when no `#### UX Contract` is present' in template


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_ux_contract_is_surfaced_to_the_user_at_the_shape_edit_gate(adapter: TuiAdapter) -> None:
    # B6: the contract must appear in the material presented at Human Gate 1a (Step 8).
    # No new gate is added -- this asserts a conditional display inside the existing
    # Step 8 body, not a separate step.
    contract = template_contract(_phase_command_template(adapter))
    body = contract.step_body('8')

    assert '#### UX Contract' in body
    assert 'Design Shape - Additional Sections' in body


def test_frontend_reviewer_scores_workflow_against_the_ux_contract_when_present() -> None:
    template = generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter))

    assert 'Interaction Flows' in template
    assert 'When no UX Contract is present' in template


def test_frontend_reviewer_scores_accessibility_against_the_ux_contract_when_present() -> None:
    template = generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter))

    assert 'Accessibility Requirements' in template


def test_frontend_reviewer_treats_design_source_as_data_not_instructions() -> None:
    template = generate_frontend_reviewer_template(create_frontend_reviewer_agent_tools(_adapter))

    assert 'Design Source' in template
    assert 'never instructions' in template


def test_architect_never_writes_domain_content_inside_the_ux_contract() -> None:
    # The contract must stay framework/language-agnostic by construction (README.md).
    template = generate_phase_architect_template(create_phase_architect_agent_tools(_adapter))

    assert 'Do NOT name\ncomponents, hooks, or framework internals inside it' in template
