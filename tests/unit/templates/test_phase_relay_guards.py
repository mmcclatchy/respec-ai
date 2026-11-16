"""Relay guards from docs/phase-cooperative/phase-2-cooperative-flow.md (B5, B6, B7).

Only the /respec-phase orchestrator talks to the user (phase-cooperative decisions.md,
"Only the orchestrator talks to the user"). B5 and B7 hold on day one, so each one also
feeds its checker a synthetic violation, proving the checker fires.
"""

import re
from dataclasses import replace

import pytest
from template_contract import template_contract

from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_generator import _commands_for_adapter, _get_agent_specs
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import AgentSpec, TuiAdapter


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_FORK_CONTEXT_LINE = re.compile(r'^context:\s*["\']?fork["\']?$')

_ALL_ADAPTERS = [
    ClaudeCodeAdapter(),
    CodexAdapter(model_overrides=_HERMETIC_MODELS),
    OpenCodeAdapter(model_overrides=_HERMETIC_MODELS),
]
_ALL_ADAPTER_IDS = ['claude-code', 'codex', 'opencode']
_ADAPTERS_WITH_A_QUESTION_TOOL = [_ALL_ADAPTERS[0], _ALL_ADAPTERS[2]]
_ADAPTERS_WITH_A_QUESTION_TOOL_IDS = ['claude-code', 'opencode']


def agents_granted_the_question_tool(specs: list[AgentSpec], question_tool: str | None) -> list[str]:
    if question_tool is None:
        return []
    return [
        spec.name
        for spec in specs
        if any(tool.split('(', 1)[0].strip().lower() == question_tool.lower() for tool in spec.tools)
    ]


def _frontmatter_lines(template: str) -> list[str] | None:
    lines = template.split('\n')
    if lines[0].strip() != '---':
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            return lines[1:index]
    return None


def sets_fork_context(template: str) -> bool:
    return any(_FORK_CONTEXT_LINE.match(line.strip()) for line in _frontmatter_lines(template) or [])


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('adapter', _ALL_ADAPTERS, ids=_ALL_ADAPTER_IDS)
def test_no_subagent_is_granted_the_tool_that_talks_to_the_user(adapter: TuiAdapter, platform: PlatformType) -> None:
    # B5 (F10): Claude Code strips AskUserQuestion from every subagent anyway, so a grant
    # would only invite a prompt that never reaches the user. codex has no question tool.
    specs = _get_agent_specs(adapter, platform)

    assert specs
    assert agents_granted_the_question_tool(specs, adapter.ask_user_question_tool_name) == []


@pytest.mark.parametrize('adapter', _ADAPTERS_WITH_A_QUESTION_TOOL, ids=_ADAPTERS_WITH_A_QUESTION_TOOL_IDS)
def test_question_tool_guard_fires_on_a_subagent_granted_the_question_tool(adapter: TuiAdapter) -> None:
    question_tool = adapter.ask_user_question_tool_name
    assert question_tool is not None
    architect = next(
        spec for spec in _get_agent_specs(adapter, PlatformType.MARKDOWN) if spec.name == 'respec-phase-architect'
    )
    violating = replace(architect, tools=[*architect.tools, question_tool])

    assert agents_granted_the_question_tool([architect], question_tool) == []
    assert agents_granted_the_question_tool([violating], question_tool) == ['respec-phase-architect']


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('adapter', _ADAPTERS_WITH_A_QUESTION_TOOL, ids=_ADAPTERS_WITH_A_QUESTION_TOOL_IDS)
def test_the_orchestrator_declares_the_question_tool_it_prompts_with(
    adapter: TuiAdapter, platform: PlatformType
) -> None:
    # B6 (F12): the orchestrator is the one party that talks to the user. opencode lists only
    # the declared tools in the command agent's tools block, so an undeclared question tool
    # there is at best unverified. codex has no question tool and prompts in chat.
    question_tool = adapter.ask_user_question_tool_name
    assert question_tool is not None
    template = TemplateCoordinator().generate_command_template(RespecAICommand.PHASE, platform, tui_adapter=adapter)

    assert adapter.selection_prompt_instruction in template
    assert question_tool.lower() in template_contract(template).declared_tools()


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('adapter', _ALL_ADAPTERS, ids=_ALL_ADAPTER_IDS)
def test_no_command_runs_as_a_fork_that_would_lose_the_user(adapter: TuiAdapter, platform: PlatformType) -> None:
    # B7 (F11): a forked command becomes a subagent and loses the user. Checked on the raw
    # generate_command_template output, because _parse_command_spec keeps only three
    # frontmatter keys and would hide a fork key from any check on the written files.
    coordinator = TemplateCoordinator()
    templates = {
        command.value: coordinator.generate_command_template(command, platform, tui_adapter=adapter)
        for command in _commands_for_adapter(adapter)
    }

    assert templates
    assert [name for name, template in templates.items() if _frontmatter_lines(template) is None] == []
    assert [name for name, template in templates.items() if sets_fork_context(template)] == []


def test_fork_guard_fires_on_a_command_whose_frontmatter_sets_fork_context() -> None:
    template = TemplateCoordinator().generate_command_template(
        RespecAICommand.PHASE, PlatformType.MARKDOWN, tui_adapter=ClaudeCodeAdapter()
    )
    violating = template.replace('---\n', '---\ncontext: fork\n', 1)

    assert not sets_fork_context(template)
    assert sets_fork_context(violating)
