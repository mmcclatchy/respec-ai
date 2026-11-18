"""Fixes to the brief agents' prompts after the phase 4 review (docs/phase-cooperative/phase-4-agent-ready-brief.md).

Each test pins a rule an agent follows when it restores, applies or checks a brief. The strings
matched are contracts: the finalizer's STEP 1 inputs, the review-target branches, the shared grammar
constants the brief is built from.
"""

import re
from functools import cache

import pytest
from template_contract import template_contract

from src.platform.template_helpers import (
    create_phase_critic_agent_tools,
    create_phase_finalizer_agent_tools,
)
from src.platform.templates.agents import generate_phase_critic_template, generate_phase_finalizer_template
from src.platform.templates.phase_contract_grammar import BRIEF_SECTION_PLACEHOLDERS, IMPLEMENTATION_BRIEF_EXAMPLE
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


@cache
def _finalizer(tui: str) -> str:
    return generate_phase_finalizer_template(create_phase_finalizer_agent_tools(_adapter(tui)))


@cache
def _brief_review(tui: str) -> str:
    template = generate_phase_critic_template(create_phase_critic_agent_tools(_adapter(tui)))
    return template_contract(template).condition_block('review_target', 'brief')


def _flat(text: str) -> str:
    return re.sub(r'\s+', ' ', text)


def _step(template: str, number: int) -> str:
    start = template.index(f'STEP {number}:')
    following = re.search(r'^STEP \d+:', template[start + 1 :], re.MULTILINE)
    return template[start : start + 1 + following.start()] if following else template[start:]


@pytest.mark.parametrize('tui', _TUIS)
def test_every_restore_reads_the_approved_copy_on_disk(tui: str) -> None:
    template = _finalizer(tui)
    retrieve = _step(template, 1)

    assert template_contract(template).declared_inputs('### Approved Copy Inputs') == {'phase_file_path'}
    assert re.search(r'^Read phase_file_path$', retrieve, re.MULTILINE)
    assert 'APPROVED_PHASE_MARKDOWN' in retrieve
    assert re.search(r'REVIEWED_PHASE_MARKDOWN = APPROVED_PHASE_MARKDOWN', retrieve)
    assert 'approved copy on disk' in _step(template, 7)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_approved_copy_never_replaces_the_append_only_success_criteria(tui: str) -> None:
    template = _finalizer(tui)
    flat_retrieve = _flat(_step(template, 1))

    assert 'except `### Success Criteria`, which comes from CURRENT_PHASE_MARKDOWN' in flat_retrieve
    assert 'Never restore `### Success Criteria` from the approved text' in _flat(_step(template, 7))


@pytest.mark.parametrize('tui', _TUIS)
def test_a_bracketed_path_is_checked_in_a_form_that_matches_the_literal_path(tui: str) -> None:
    finalizer_glob = next(line for line in _step(_finalizer(tui), 7).split('\n') if 'Glob(pattern=' in line)
    critic_check = _brief_review(tui)
    critic_glob = next(line for line in critic_check.split('\n') if 'Glob(pattern=' in line)

    assert '[[]' in finalizer_glob
    assert '[[]' in critic_glob
    assert '`[[]`' in _step(_finalizer(tui), 3)
    assert 'Glob matches files only' in _flat(critic_check)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_full_pass_applies_the_decisions_that_settle_brief_questions(tui: str) -> None:
    scope = _step(_finalizer(tui), 2)
    full_pass = scope[scope.index('IF none of') : scope.index('ELSE:')]

    assert 'SETTLED_DECISIONS' in full_pass
    assert 'supersedes=' in full_pass
    assert 'affects=' in full_pass
    assert "### Implementer's discretion" not in full_pass
    assert '### Escalate if' not in full_pass


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_review_searches_with_tools_the_critic_holds(tui: str) -> None:
    tools = create_phase_critic_agent_tools(_adapter(tui)).tools_yaml.lower()
    cold_start = _flat(_brief_review(tui))

    assert 'grep' not in cold_start.lower()
    assert 'bash' in cold_start.lower()
    assert 'bash' in tools


@pytest.mark.parametrize('tui', _TUIS)
def test_a_new_guardrail_number_clears_every_number_a_kept_step_still_cites(tui: str) -> None:
    rule = _flat(_step(_finalizer(tui), 4))

    assert 'in the phase document and in IMPLEMENTATION_PLAN_MARKDOWN' in rule
    assert 'dangling reference' in rule


@pytest.mark.parametrize('tui', _TUIS)
def test_the_skeleton_line_is_written_only_for_a_language_with_a_materializer(tui: str) -> None:
    rule = _flat(_step(_finalizer(tui), 5))

    assert 'No materializer is registered for this language' in rule
    assert 'add no skeleton line' in rule
    assert 'Create <path>' in rule
    assert 'a `create` item that exists is that skeleton' in IMPLEMENTATION_BRIEF_EXAMPLE
    assert 'language that has a materializer' in IMPLEMENTATION_BRIEF_EXAMPLE


def test_the_deviation_protocol_gives_the_line_format() -> None:
    assert 'DEV-<n> | Step <N> | expected:' in BRIEF_SECTION_PLACEHOLDERS['Guardrails']
    assert 'DEV-<n> | Step <N> | expected:' not in IMPLEMENTATION_BRIEF_EXAMPLE.split('## Deviations')[1]


@pytest.mark.parametrize('tui', _TUIS)
def test_a_decision_that_settles_a_criterion_target_is_applied_without_rewording_the_criterion(tui: str) -> None:
    finalizer = _flat(_step(_finalizer(tui), 4))

    assert 'append ` (target: <value>, SD-<n>)` to the end of that criterion' in finalizer
    assert '` (target: <value>, SD-<n>)` suffix' in _flat(_brief_review(tui))


@pytest.mark.parametrize('tui', _TUIS)
def test_a_step_verify_and_a_checklist_verify_are_the_test_command_in_every_agent(tui: str) -> None:
    commands = _flat(_step(_finalizer(tui), 6))
    critic = _flat(_brief_review(tui))

    assert 'Each `Verify` and Checklist `(verify: …)` command is the `[commands].test` value' in commands
    assert 'is one of these: the `[commands].test` value, in project_config_context_markdown' in critic
