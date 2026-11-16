"""Runtime language config reaches the architect on every TUI.

See docs/phase-cooperative/phase-1-language-neutral.md, behaviors B11-B12. These anchor on step
numbers that phase 2 renumbers, so they live outside the language-neutrality guard; phase 2
re-anchors both here.
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
def test_architect_receives_language_authoring_notes_and_a_failed_lookup_never_stops_the_workflow(tui: str) -> None:
    # Deliberate string assertions (testing.md exception): the CLI parses the subcommand name, and
    # the architect's prompt names this heading as where its per-language rules arrive.
    contract = template_contract(_phase_command(tui))
    body = contract.step_body('4.5')

    assert 'respec-ai language-guidance' in body
    assert '### Language Authoring Notes' in body
    assert 'EXIT:' not in body
    assert contract.outcome_condition(body, 'Language authoring notes unavailable').startswith('ELSE')


@pytest.mark.parametrize('tui', TUIS)
def test_a_missing_verify_command_is_marked_for_the_user_instead_of_guessed(tui: str) -> None:
    # Deliberate string assertion (testing.md exception): phase 2's briefing scans for this marker
    # and phase 3's structural checks inherit it.
    architect = _phase_architect(tui)

    assert '(verify: ask user' in architect
    assert 'no_preference' in architect
