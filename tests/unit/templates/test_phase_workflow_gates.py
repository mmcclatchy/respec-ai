"""Behavior: every tool the phase workflow invokes is declared in its allowed-tools list.

See docs/phase-refactor/findings.md F20 and docs/phase-cooperative/findings.md F12. The loop's
user_input route is pinned in test_phase_cooperative_flow.py (B18).
"""

import pytest
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_adapters.opencode import OpenCodeAdapter


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
