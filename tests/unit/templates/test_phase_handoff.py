"""Phase 4 B15 — the TUI-tiered handoff (docs/phase-cooperative/phase-4-agent-ready-brief.md, Scope 10).

Every TUI gets the portable core: both brief paths and the respec-code alternative. A TUI that
declares a delegation instruction (adapter.brief_handoff_extension) also gets it, and no other TUI
shows any of it (memory: TUI capability tiering).

These tests anchor on the Step 4 and Step 12 sections (template_contract) and on adapter-rendered
values: code_command_invocation and brief_handoff_extension are matched as blocks. PHASE_FILE_PATH
and IMPLEMENTATION_PLAN_PATH are the orchestrator's runtime variables that the handoff names.
"""

import re
from functools import cache

import pytest
from template_contract import template_contract

from src.platform.adapters import get_platform_adapter
from src.platform.models import PhaseCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import create_phase_command_tools
from src.platform.templates.commands import generate_phase_command_template
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')
_NAMES_STEP_12 = re.compile(r'\bStep 12\b(?!\.\d)')


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


@cache
def _tools(tui: str, platform: PlatformType) -> PhaseCommandTools:
    platform_adapter = get_platform_adapter(platform)
    adapter = _adapter(tui)
    return create_phase_command_tools(
        platform_adapter.create_phase_tool,
        platform_adapter.retrieve_phase_tool,
        platform_adapter.list_phases_tool,
        platform,
        plans_dir=adapter.plans_dir(),
        tui_adapter=adapter,
    )


@cache
def _command(tui: str, platform: PlatformType) -> str:
    return generate_phase_command_template(_tools(tui, platform))


def _handoff(tui: str, platform: PlatformType) -> str:
    return template_contract(_command(tui, platform)).step_section('12.3')


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('tui', _TUIS)
def test_every_tui_hands_off_both_brief_paths_and_the_respec_code_alternative(tui: str, platform: PlatformType) -> None:
    handoff = _handoff(tui, platform)

    assert handoff, 'Step 12 has no handoff sub-step'
    assert [
        name for name in ('PHASE_FILE_PATH', 'IMPLEMENTATION_PLAN_PATH') if not re.search(rf'\b{name}\b', handoff)
    ] == []
    assert _tools(tui, platform).code_command_invocation.strip() in handoff


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('tui', _TUIS)
def test_the_delegation_instruction_is_shown_exactly_where_the_tui_provides_one(
    tui: str, platform: PlatformType
) -> None:
    extension = _adapter(tui).brief_handoff_extension
    reference = ClaudeCodeAdapter().brief_handoff_extension
    assert reference, 'Claude Code declares no delegation instruction'

    if extension is None:
        rendered = {line.strip() for line in _command(tui, platform).split('\n') if line.strip()}
        assert [line for line in reference.split('\n') if line.strip() in rendered] == []
    else:
        assert template_contract(_handoff(tui, platform)).block_sites(extension)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_signed_off_phase_shows_the_handoff_through_step_12_without_reopening(tui: str) -> None:
    command = _command(tui, PlatformType.MARKDOWN)
    contract = template_contract(command)
    lines = command.split('\n')
    steps = contract.line_steps()
    routes = [index for index, line in enumerate(lines) if steps[index] == '4' and _NAMES_STEP_12.search(line)]

    assert routes, "Step 4's handoff choice does not reach Step 12"
    for route in routes:
        guards = contract.guards_at(route)
        assert any('shape-settled' in guard for guard in guards)
        assert not any('"Re-open the design"' in guard for guard in guards)
