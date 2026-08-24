"""Behaviors B4, B7-B10 from docs/phase-refactor/phase-3-human-gate.md.

The shape act's own joint gate (Step 11) is compound-conditioned prose, not Python, so
these assert structure via tests/support/template_contract.py rather than string
literals - the discriminating question from testing.md: would a reworded but
behaviorally-identical rewrite of Step 11 still pass? These do; a version that dropped
either half of the AND, or let the critic override survive unrecorded, would not.
"""

import pytest
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter

_ADAPTERS = [ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter()]


def _phase_template(adapter: TuiAdapter) -> str:
    return TemplateCoordinator().generate_command_template(
        RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=adapter
    )


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_shape_act_does_not_close_until_user_approves_and_critic_passes(adapter: TuiAdapter) -> None:
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('11')

    condition = contract.outcome_condition(body, 'Proceed to Step 12')

    assert 'APPROVED_VERSION' in condition
    assert 'CURRENT_VERSION' in condition
    assert 'completed' in condition


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_design_changed_after_approval_requires_reapproval(adapter: TuiAdapter) -> None:
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('11')

    condition = contract.outcome_condition(body, 'Return to Step 8')

    assert 'APPROVED_VERSION' in condition
    assert 'CURRENT_VERSION' in condition
    assert '!=' in condition


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_user_can_override_critic_findings_and_the_override_is_recorded(adapter: TuiAdapter) -> None:
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('11')

    condition = contract.outcome_condition(body, 'source=user-override')

    assert 'Override' in condition


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_a_user_hand_edit_is_validated_diffed_and_stored_not_silently_discarded(adapter: TuiAdapter) -> None:
    # B4: the edit gate's contract for getting a hand edit into stored state. What
    # actually happens to file contents can't be executed here (testing.md: templates
    # are prompts) - this pins that Step 9 runs validate_document before storing, diffs
    # per-heading into a recorded decision, and stores through the frozen-field gate
    # exception rather than silently accepting or silently rejecting the edit.
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('9')

    assert 'validate_document' in body or 'CONTENT_TO_VALIDATE' in body
    assert 'source=user-edit' in body
    assert 'allow_frozen_field_edits=true' in body


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_every_shape_act_user_prompt_blocks_for_a_response(adapter: TuiAdapter) -> None:
    # B10: every user-facing prompt in Steps 4-12 blocks and can be answered, on every
    # TUI. wait_prompt_count == resume_marker_count per step means no prompt was left
    # dangling without a documented resume point.
    contract = template_contract(_phase_template(adapter))

    for step in ('6', '7', '8', '9', '11'):
        body = contract.step_body(step)
        waits = contract.wait_prompt_count(body)
        resumes = contract.resume_marker_count(body)
        assert waits >= 1, f'Step {step} has no WAIT for a user prompt'
        assert waits == resumes, f'Step {step} has {waits} WAIT(s) but {resumes} resume marker(s)'


def test_every_shape_act_prompt_renders_identically_shaped_across_every_tui() -> None:
    # The abstraction (finding F18: Codex has no AskUserQuestion) only earns its keep if
    # every TUI gets the same number of blocking prompts in the same steps.
    counts_by_adapter = {}
    for adapter in _ADAPTERS:
        contract = template_contract(_phase_template(adapter))
        counts_by_adapter[adapter.__class__.__name__] = {
            step: contract.wait_prompt_count(contract.step_body(step)) for step in ('6', '7', '8', '9', '11')
        }

    values = list(counts_by_adapter.values())
    assert all(v == values[0] for v in values), counts_by_adapter
