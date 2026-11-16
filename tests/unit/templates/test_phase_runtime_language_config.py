"""Runtime language config reaches the architect on every TUI.

See docs/phase-cooperative/phase-1-language-neutral.md, behaviors B11-B12. These anchor on step
numbers, so they live outside the language-neutrality guard. Phase 2 re-anchored both: B11 on the
run setup (Step 3) and B12 on the briefing (the architect's explore mode and Step 6).
"""

import pytest

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_helpers import create_phase_architect_agent_tools
from src.platform.templates.agents import generate_phase_architect_template
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter
from tests.support.template_contract import template_contract


MODEL_OVERRIDES = {
    'reasoning': 'test-reasoning-model',
    'orchestration': 'test-orchestration-model',
    'coding': 'test-coding-model',
    'review': 'test-review-model',
}

TUIS = ('claude-code', 'opencode', 'codex')


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=MODEL_OVERRIDES)
    if tui == 'codex':
        return CodexAdapter(model_overrides=MODEL_OVERRIDES)
    return ClaudeCodeAdapter()


def _phase_command(tui: str) -> str:
    adapter = _adapter(tui)
    return TemplateCoordinator().generate_command_template(
        RespecAICommand.PHASE, PlatformType.MARKDOWN, plans_dir=adapter.plans_dir(), tui_adapter=adapter
    )


def _phase_architect(tui: str) -> str:
    adapter = _adapter(tui)
    return generate_phase_architect_template(create_phase_architect_agent_tools(adapter, plans_dir=adapter.plans_dir()))


@pytest.mark.parametrize('tui', TUIS)
def test_a_missing_verify_command_is_marked_for_the_user_instead_of_guessed(tui: str) -> None:
    # Deliberate string assertion (testing.md exception): phase 2's briefing scans for this marker
    # and phase 3's structural checks inherit it.
    architect = _phase_architect(tui)

    assert '(verify: ask user' in architect
    assert 'no_preference' in architect


def _explore_branch(architect: str) -> str:
    start = architect.find('IF phase_mode == "explore":')
    end = architect.find('ELIF phase_mode == "draft":', start)
    return architect[start:end] if start != -1 and end != -1 else ''


@pytest.mark.parametrize('tui', TUIS)
def test_explore_raises_a_missing_verify_command_as_a_briefing_decision(tui: str) -> None:
    # Phase 2 re-anchor of B12: the briefing is the first place the user is asked. The
    # option that ends the run names the file the user edits, never /respec-standards
    # (standards_command.py:16 forbids editing canonical TOML).
    explore = _explore_branch(_phase_architect(tui))

    assert 'no_preference' in explore
    assert '[commands].test' in explore
    assert '.respec-ai/config/standards/<language>.toml' in explore
    assert '(verify: ask user' in explore
    assert 'respec-standards' not in explore


@pytest.mark.parametrize('tui', TUIS)
def test_run_setup_gives_every_architect_route_language_notes_and_a_failed_lookup_never_stops_the_run(tui: str) -> None:
    # Phase 2 re-anchor of B11: Step 3 sets up the run before Step 4 routes, so every route that
    # reaches the architect carries the notes. Step 3 also holds the loop link's fail-closed
    # exits, so the no-EXIT rule covers only the language-guidance block.
    contract = template_contract(_phase_command(tui))
    setup = contract.step_section('3')
    start = setup.find('respec-ai language-guidance')
    end = setup.find('### Language Authoring Notes', start)

    assert start != -1 and end != -1
    assert 'EXIT' not in setup[start:end]
    assert contract.outcome_condition(setup, 'Language authoring notes unavailable').startswith('ELSE')


@pytest.mark.parametrize('tui', TUIS)
def test_choosing_to_configure_a_verify_command_first_ends_the_run_after_recording_the_choice(tui: str) -> None:
    # Phase 2 re-anchor of B12, orchestrator half: Option A of the briefing's missing-verify-command
    # decision (and of Design Source) needs work outside the run, so the briefing records the
    # answer and ends the run before any research or draft. `Option A` is the decision entry's
    # contract field (README "Decision entry (canonical)").
    template = _phase_command(tui)
    contract = template_contract(template)
    lines = template.split('\n')
    briefing = [index for index, step in enumerate(contract.line_steps()) if step and step.split('.')[0] == '6']

    endings = [
        index
        for index in briefing
        if 'EXIT' in lines[index] and any('option a' in guard.lower() for guard in contract.guards_at(index))
    ]

    assert endings, 'no briefing answer ends the run'
    assert [index for index in briefing if 'mcp__respec-ai__store_document(' in lines[index] and index < endings[0]]
