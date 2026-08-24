"""Behaviors B1-B5 from docs/phase-refactor/phase-5-implementation-plan.md.

implementation.md is a plain bundle file, not a DocumentType, so it cannot be produced
by executing a Pydantic model's build_markdown() the way phase.md can (testing.md:
templates are prompts and resist ordinary behavioral testing). B1 and B5 instead pin
the *format contract* by running the real extraction algorithm (tests/support/
plan_extraction.py, mirroring code_command.py's `#### Step N:` scanner and the DR-###
format shared with task_planner.py) against phase_architect.py's own
`implementation_plan_example` constant -- the actual text shown to the agent, not a
copy maintained separately in this test. B2-B4 pin the prompt
structure via tests/support/template_contract.py, per testing.md's guidance for
generated templates.
"""

import re

import pytest
from plan_extraction import extract_deferred_risks, extract_steps
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_helpers import create_phase_architect_agent_tools
from src.platform.templates.agents import generate_phase_architect_template
from src.platform.templates.agents.phase_architect import implementation_plan_example
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter

_ADAPTERS = [ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter()]

def _phase_architect_template(adapter: TuiAdapter) -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(adapter))


_MODE_BRANCH_HEADER = re.compile(r'^(?P<indent>[ \t]*)(?:IF|ELIF)\s+phase_mode\s*==\s*"(?P<mode>[^"]+)"', re.IGNORECASE)


def _phase_mode_branch_body(template: str, mode: str) -> str:
    # phase_mode branches aren't "_DECISION"-suffixed, so template_contract's
    # decision_branch() (scoped to that naming convention) doesn't apply here.
    lines = template.split('\n')
    for i, line in enumerate(lines):
        header = _MODE_BRANCH_HEADER.match(line)
        if not header or header.group('mode').lower() != mode.lower():
            continue
        indent = len(header.group('indent'))
        body_lines = []
        for follow_line in lines[i + 1 :]:
            sibling = _MODE_BRANCH_HEADER.match(follow_line)
            is_else = re.match(r'^[ \t]{0,%d}ELSE\s*:' % indent, follow_line)
            if (sibling and len(sibling.group('indent')) <= indent) or is_else:
                break
            body_lines.append(follow_line)
        return '\n'.join(body_lines)
    raise ValueError(f'No phase_mode branch found for {mode!r}')


def test_generated_plan_steps_are_readable_by_the_coding_workflow_scanner() -> None:
    # B1: `#### Step N:` is parsed by code_command.py:315 and patch_command.py's
    # equivalent scanner, so the exact heading format is the contract, not prose. Runs
    # against phase_architect.py's own `implementation_plan_example` constant -- the
    # actual text the agent is shown -- not a copy hand-maintained in this test, so a
    # rewording of the real example that broke the format would fail here.
    assert extract_steps(implementation_plan_example) == ['1', '2']


def test_deferred_risks_are_recorded_in_the_stable_dr_id_format() -> None:
    # B5: the coding workflow needs stable DR-### ids, not prose about deferred risk.
    assert extract_deferred_risks(implementation_plan_example) == ['DR-001']


def test_delivery_intent_has_exactly_one_source_of_truth_in_the_generated_phase() -> None:
    # B2: anti-regression for the defect this phase removes. Two homes for delivery
    # intent (Phase's Delivery Intent Override + Task's Execution Intent Policy) forced
    # the three-level precedence chain at code_command.py:406-465. The Phase side must
    # be gone; Execution Intent Policy now belongs solely to implementation.md.
    # ClaudeCodeAdapter only, per precedent in test_phase_design_layer.py -- rendering
    # the architect agent template directly (not via the full command coordinator)
    # requires per-adapter model config that isn't set up for every adapter in tests.
    template = _phase_architect_template(ClaudeCodeAdapter())

    assert 'Delivery Intent Override' not in template


def test_implementation_plan_mode_carries_forward_every_referenced_constraint() -> None:
    # B3: migrated from task_planner.py:199-208's carry-forward mandate. Presence in the
    # plan is what's asserted, not which section it lands in (that's an implementation
    # choice, per phase-5-implementation-plan.md).
    body = _phase_mode_branch_body(_phase_architect_template(ClaudeCodeAdapter()), 'implementation-plan')

    assert 'IMPL_PLAN_CONSTRAINTS' in body
    assert 'CARRY-FORWARD' in body.upper()


@pytest.mark.parametrize('adapter', _ADAPTERS)
def test_implementation_plan_gate_blocks_and_alterations_are_persisted(adapter: TuiAdapter) -> None:
    # B4: the gate must block for a response and route alterations back into
    # regeneration via the same feedback mechanism the shape act already proved out.
    coordinator = TemplateCoordinator()
    template = coordinator.generate_command_template(RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=adapter)
    contract = template_contract(template)

    body = contract.step_body('12.6')
    waits = contract.wait_prompt_count(body)
    resumes = contract.resume_marker_count(body)

    assert waits >= 1
    assert waits == resumes
    assert 'store_user_feedback' in body

    proceed_condition = contract.outcome_condition(body, 'Proceed to Step 13')
    assert 'Looks right' in proceed_condition or 'proceed' in proceed_condition.lower()
