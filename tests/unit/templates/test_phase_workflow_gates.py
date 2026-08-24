"""Behaviors: the phase workflow blocks for the user on USER_INPUT, and every tool it
invokes is declared in its allowed-tools list.

See docs/phase-refactor/findings.md F5, F6, F20.
"""

import pytest
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter


@pytest.mark.parametrize('adapter', [ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter()])
def test_workflow_waits_for_the_user_when_the_loop_requests_input(adapter: TuiAdapter) -> None:
    coordinator = TemplateCoordinator()
    template = coordinator.generate_command_template(RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=adapter)

    branch = template_contract(template).decision_branch('user_input')

    assert branch.blocks_for_user_response()
    assert branch.persists_user_feedback()


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('adapter', [ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter()])
def test_every_tool_the_phase_command_invokes_is_declared_in_its_allowed_tools(
    adapter: TuiAdapter, platform: PlatformType
) -> None:
    # Scoped to respec-phase only (finding F20's call site) and to tools this codebase
    # owns via RespecAITool/BuiltInToolCapability. A pre-existing diagnostic run showed
    # several other commands and one third-party platform-adapter tool reference
    # (mcp__linear-server__get_document, used by sync_plan_instructions, which the phase
    # command's own tools now declare) with similar gaps; widening this test to every
    # command is out of Phase 0's scope (see README.md "Do not expand a phase's scope").
    # Parametrized over PlatformType too: the plan-retrieval tool declared alongside the
    # phase-scoped ones is looked up per platform, and each platform's adapter renders
    # its own sync-instruction tool name independently -- nothing guarantees they agree.
    coordinator = TemplateCoordinator()
    template = coordinator.generate_command_template(RespecAICommand.PHASE, platform, tui_adapter=adapter)

    contract = template_contract(template)

    assert contract.invoked_tools() <= contract.declared_tools()


@pytest.mark.parametrize('adapter', [ClaudeCodeAdapter(), CodexAdapter(), OpenCodeAdapter()])
def test_shape_act_and_detail_act_use_separate_loops_and_declare_their_phase_mode(adapter: TuiAdapter) -> None:
    # Phase 3, decisions.md: the shape act (Step 4-12) and detail act (Step 13-19) are
    # two decoupled MCP refinement loops, never the same loop_id, so Phase.version
    # tracking (finding F22) for the joint gate never sees detail-act writes. Each
    # architect/critic invocation must declare which act it's running as, per the
    # phase2_mode/validation_mode scalar-input precedent (AGENT_DEVELOPMENT_GUIDELINES.md).
    coordinator = TemplateCoordinator()
    template = coordinator.generate_command_template(RespecAICommand.PHASE, PlatformType.LINEAR, tui_adapter=adapter)

    assert 'SHAPE_LOOP_ID' in template
    assert template.count('phase_mode: shape') == 2  # architect (Step 5) + critic (Step 10)
    assert template.count('phase_mode: detail') == 2  # architect + critic, detail act
