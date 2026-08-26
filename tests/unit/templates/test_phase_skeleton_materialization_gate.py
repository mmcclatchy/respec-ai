"""Behavior B7 from docs/phase-refactor/phase-4-skeletons.md: skeletons are written only
from a design the user approved and the critic passed.

Skeleton generation itself is executable (tests/unit/utils/test_skeleton_generator.py,
tests/unit/cli/commands/test_materialize_skeletons.py) and pins the create-only
guarantee directly. The template is prose, so this file pins the sequencing contract
per testing.md: would a reworded but behaviorally-identical rewrite of Steps 11/11.5
still pass? These do; a version that let materialization run before the gate, or that
skipped it on the refine/user_input path, would not.
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
def test_skeletons_are_not_materialized_before_the_joint_gate_passes(adapter: TuiAdapter) -> None:
    template = _phase_template(adapter)
    contract = template_contract(template)

    materialize_call_index = template.index('materialize-skeletons')
    step_11_5_header_index = template.index('### Step 11.5')
    assert materialize_call_index > step_11_5_header_index

    for step_number in ('5', '6', '7', '8', '9', '10'):
        assert 'materialize-skeletons' not in contract.step_body(step_number)


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_both_step_11_success_paths_route_into_skeleton_materialization(adapter: TuiAdapter) -> None:
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('11')

    completed_condition = contract.outcome_condition(body, 'Proceed to Step 11.5')
    assert 'completed' in completed_condition

    override_condition = contract.outcome_condition(body, 'source=user-override')
    assert 'Override' in override_condition
    assert 'Proceed to Step 11.5' in body[body.index('source=user-override') :]


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_a_critic_refine_or_user_input_outcome_never_reaches_skeleton_materialization(
    adapter: TuiAdapter,
) -> None:
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('11')

    return_condition = contract.outcome_condition(body, 'Return to Step 5')
    assert 'materialize-skeletons' not in return_condition


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_skeleton_conflicts_block_for_a_user_reconciliation_choice(adapter: TuiAdapter) -> None:
    contract = template_contract(_phase_template(adapter))
    body = contract.step_body('11.5')

    assert 'WAIT for' in body
    assert 'Merge' in body
    assert 'Keep the existing signature' in body
    assert 'Accept the design change' in body


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_unmaterialized_and_unintrospectable_paths_are_displayed_and_recorded(adapter: TuiAdapter) -> None:
    # B7: silent skip is its own bug (README.md) -- a path the materializer could not
    # write, or could not safely reconcile, must reach the user and the design record,
    # not just the CLI JSON.
    body = template_contract(_phase_template(adapter)).step_body('11.5')

    assert 'unmaterialized_paths' in body
    assert 'unintrospectable_paths' in body
    assert 'source=materializer' in body
