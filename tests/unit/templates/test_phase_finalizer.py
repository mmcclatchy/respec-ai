"""The phase finalizer (docs/phase-cooperative/phase-4-agent-ready-brief.md, Scope 6).

B10 follows tests/unit/templates/test_coder_split_phase9.py: the finalizer is generated on every
TUI, the phase command is granted it, and it is written under the runtime name the adapter's
invocation renders (codex renames every agent to respec-<x>-agent). B11 pins the shipped grant as
one equality, so a question tool, Edit, Bash, a resume tool or any store tool beyond
update_document fails it. The registration tests name the agent by its literal runtime name, never
by the enum, so an unregistered finalizer fails an assertion instead of collection.

The template tests anchor on structure: which call precedes which, which block encloses a call,
what the report block holds. The strings they match are contracts something else reads:
- the invocation inputs, which the orchestrator's invocation passes
- the FindingOwner and CitedPathKind values, which validate_document returns
- CONTENT_LOSS_WARNING and the review-target tags, imported as the template imports them: the
  server writes the first, the critic writes the second
- the implementation.md path, which the Write grant scopes and the architect writes too
"""

import json
import re
from fnmatch import fnmatch
from pathlib import Path

import pytest
from template_contract import template_contract

from src.models.document_validation import CONTENT_LOSS_WARNING, CitedPathKind, FindingOwner
from src.platform.adapters import get_platform_adapter
from src.platform.platform_selector import PlatformType
from src.platform.template_coordinator import TemplateCoordinator
from src.platform.template_generator import (
    _AGENT_NAMES,
    _get_agent_specs,
    _parse_command_spec,
    expected_agents_count,
)
from src.platform.template_helpers import (
    create_phase_architect_agent_tools,
    create_phase_command_tools,
    create_phase_finalizer_agent_tools,
)
from src.platform.templates.agents import generate_phase_architect_template, generate_phase_finalizer_template
from src.platform.templates.phase_contract_grammar import (
    ASK_USER_COMMAND_MARKER,
    BRIEF_REVIEW_TAG,
    BRIEF_SECTION_PLACEHOLDERS,
    DESIGN_REVIEW_TAG,
    IMPLEMENTATION_BRIEF_EXAMPLE,
    SUCCESS_CRITERION_PLACEHOLDER,
)
from src.platform.tool_enums import RespecAICommand
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import AgentSpec, TuiAdapter
from src.utils.phase_structure import ASK_USER_MARKER


FINALIZER = 'respec-phase-finalizer'
_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')

_IMPLEMENTATION_PLAN_WRITE_SCOPE = '.respec-ai/plans/*/phases/*/implementation.md'
_FINALIZER_MCP_TOOLS = frozenset(
    {
        'mcp__respec-ai__get_document',
        'mcp__respec-ai__update_document',
        'mcp__respec-ai__get_feedback',
        'mcp__respec-ai__get_previous_analysis',
        'mcp__respec-ai__validate_document',
    }
)

# Where each adapter's write_all puts an agent, keyed by the name its invocation renders.
_RUNTIME_ARTIFACTS = {
    'claude-code': ('respec-phase-finalizer', '.claude/agents/respec-phase-finalizer.md'),
    'opencode': ('respec-phase-finalizer', '.opencode/prompts/agents/respec-phase-finalizer.md'),
    'codex': ('respec-phase-finalizer-agent', '.codex/agents/respec-phase-finalizer-agent.toml'),
}


_KEY_MODE_VALIDATION = re.compile(r'mcp__respec-ai__validate_document\((?=[^)]*\bkey=)(?![^)]*\bcontent=)')
_IMPLEMENTATION_PLAN_PATH = re.compile(r'^IMPLEMENTATION_PLAN_PATH = `(?P<path>[^`]+)`$', re.MULTILINE)
_OWNED_PATH_KINDS = (CitedPathKind.GROUNDING, CitedPathKind.CREATE, CitedPathKind.MODIFY)


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


def _finalizer_spec(adapter: TuiAdapter) -> AgentSpec | None:
    return next((spec for spec in _get_agent_specs(adapter, PlatformType.MARKDOWN) if spec.name == FINALIZER), None)


def _phase_command_tools_yaml(adapter: TuiAdapter) -> list[str]:
    platform_adapter = get_platform_adapter(PlatformType.MARKDOWN)
    tools = create_phase_command_tools(
        platform_adapter.create_phase_tool,
        platform_adapter.retrieve_phase_tool,
        platform_adapter.list_phases_tool,
        PlatformType.MARKDOWN,
        plans_dir=adapter.plans_dir(),
        tui_adapter=adapter,
    )
    return tools.tools_yaml.split(', ')


def _write_phase_workflow(adapter: TuiAdapter, project_path: Path) -> None:
    template = TemplateCoordinator().generate_command_template(
        RespecAICommand.PHASE, PlatformType.MARKDOWN, plans_dir=adapter.plans_dir(), tui_adapter=adapter
    )
    command = _parse_command_spec(RespecAICommand.PHASE, template, 'model')
    adapter.write_all(project_path, _get_agent_specs(adapter, PlatformType.MARKDOWN), [command])


# ---------------------------------------------------------------------------
# B10 - the orchestrator can dispatch the finalizer on every TUI
# ---------------------------------------------------------------------------


def test_the_finalizer_is_one_of_the_generated_agents() -> None:
    assert FINALIZER in _AGENT_NAMES


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_is_generated_for_every_tui(tui: str, platform: PlatformType) -> None:
    adapter = _adapter(tui)
    names = {spec.name for spec in _get_agent_specs(adapter, platform)}

    assert FINALIZER in names
    assert len(names) == expected_agents_count(adapter)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_phase_command_is_granted_the_finalizer(tui: str) -> None:
    assert f'Task({FINALIZER})' in _phase_command_tools_yaml(_adapter(tui))


def test_opencode_lets_the_phase_command_dispatch_the_finalizer(tmp_path: Path) -> None:
    # opencode turns a command's Task(...) grants into permission.task with '*': 'deny', so an
    # ungranted subagent cannot be dispatched at all.
    _write_phase_workflow(_adapter('opencode'), tmp_path)

    config = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))

    assert FINALIZER in config['agent']
    assert config['agent'][f'cmd-{RespecAICommand.PHASE.value}']['permission']['task'].get(FINALIZER) == 'allow'


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_is_written_under_the_name_its_invocation_renders(tui: str, tmp_path: Path) -> None:
    adapter = _adapter(tui)
    runtime_name, artifact = _RUNTIME_ARTIFACTS[tui]
    _write_phase_workflow(adapter, tmp_path)

    invocation = adapter.render_agent_invocation(FINALIZER, 'write the agent-ready brief', [])

    assert (tmp_path / artifact).is_file()
    assert runtime_name in invocation
    if tui == 'codex':
        assert f'name = "{runtime_name}"' in (tmp_path / artifact).read_text(encoding='utf-8')
        assert f'`{runtime_name}`' in invocation


# ---------------------------------------------------------------------------
# B11 - the finalizer holds only what its job needs
# ---------------------------------------------------------------------------


def test_on_claude_code_the_finalizer_holds_exactly_its_grant_with_the_write_path_scoped() -> None:
    # Only Claude Code keeps a path scope on a subagent's Write (decisions.md, F14), so the raw
    # string is compared here, parameter included.
    spec = _finalizer_spec(ClaudeCodeAdapter())

    assert spec is not None
    assert set(spec.tools) == _FINALIZER_MCP_TOOLS | {
        'Read',
        'Glob',
        'Grep',
        f'Write({_IMPLEMENTATION_PLAN_WRITE_SCOPE})',
    }


@pytest.mark.parametrize('tui', ['opencode', 'codex'])
def test_on_opencode_and_codex_the_finalizer_holds_exactly_its_grant(tui: str) -> None:
    spec = _finalizer_spec(_adapter(tui))

    assert spec is not None
    assert {tool.split('(', 1)[0].lower() for tool in spec.tools} == _FINALIZER_MCP_TOOLS | {
        'read',
        'glob',
        'grep',
        'write',
    }


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_is_never_granted_the_tool_that_talks_to_the_user(tui: str) -> None:
    adapter = _adapter(tui)
    spec = _finalizer_spec(adapter)
    question_tool = adapter.ask_user_question_tool_name

    assert spec is not None
    assert question_tool is None or question_tool.lower() not in {tool.lower() for tool in spec.tools}


# ---------------------------------------------------------------------------
# Scope 6 - the template
# ---------------------------------------------------------------------------


def _finalizer(tui: str) -> str:
    return generate_phase_finalizer_template(create_phase_finalizer_agent_tools(_adapter(tui)))


def _tasks(template: str) -> str:
    return template[template.index('TASKS:') :] if 'TASKS:' in template else ''


def _call_lines(lines: list[str], tool_call: str) -> list[int]:
    prefix = tool_call.split('(', 1)[0] + '('
    return [index for index, line in enumerate(lines) if line.lstrip().startswith(f'CALL {prefix}')]


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_takes_the_ids_and_the_config_context_and_no_mode(tui: str) -> None:
    # README "Agents and modes": the finalizer has one job, so the orchestrator passes no phase_mode.
    contract = template_contract(_finalizer(tui))

    assert contract.declared_inputs('### Scalar Inputs') == {'loop_id', 'plan_name', 'phase_name'}
    assert contract.declared_inputs('### Grouped Markdown Inputs') == {'project_config_context_markdown'}


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_uses_every_mcp_tool_it_holds_and_invokes_nothing_else(tui: str) -> None:
    # Always invoked fresh: a resume tool, a question tool or a shell named here would be invoked
    # without a grant. The body is read without the frontmatter, whose tools line names every grant.
    template = _finalizer(tui)
    invoked = template_contract(template.split('\n---\n', 1)[1]).invoked_tools()

    assert {tool for tool in invoked if tool.startswith('mcp__')} == _FINALIZER_MCP_TOOLS
    assert sorted(invoked - template_contract(template).declared_tools()) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_is_shown_the_shared_brief_forms_never_its_own_copy(tui: str) -> None:
    # Scope 4 "Sharing": the forms come from phase_contract_grammar, so the finalizer, the architect
    # and the structural checks (B4) cannot drift apart. block_sites ignores the fence indentation.
    contract = template_contract(_finalizer(tui))
    shown = [IMPLEMENTATION_BRIEF_EXAMPLE, SUCCESS_CRITERION_PLACEHOLDER, *BRIEF_SECTION_PLACEHOLDERS.values()]

    assert [form for form in shown if not contract.block_sites(form)] == []
    assert [name for name in BRIEF_SECTION_PLACEHOLDERS if not contract.block_sites(f'## {name}')] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_rehydrates_from_mcp_and_the_disk_before_choosing_its_scope(tui: str) -> None:
    tasks = _tasks(_finalizer(tui))
    tools = create_phase_finalizer_agent_tools(_adapter(tui))
    scope_choice = re.search(r'^STEP \d+: Choose the Scope', tasks, re.MULTILINE)

    assert scope_choice
    before = template_contract(tasks[: scope_choice.start()])
    for call in (tools.get_document, tools.get_feedback, tools.get_analysis):
        assert () in before.guards_for(f'CALL {call.split("(", 1)[0]}('), f'no unconditional {call}'
    assert re.search(r'^Read IMPLEMENTATION_PLAN_PATH\b', tasks[: scope_choice.start()], re.MULTILINE)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_writes_both_files_before_validating_them_and_reporting(tui: str) -> None:
    tasks = _tasks(_finalizer(tui))
    lines = tasks.split('\n')
    tools = create_phase_finalizer_agent_tools(_adapter(tui))
    stores = _call_lines(lines, tools.update_document)
    plan_writes = [
        index for index, line in enumerate(lines) if re.match(r'^\s*Write IMPLEMENTATION_PLAN_MARKDOWN\b', line)
    ]
    validations = [
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith('CALL ')
        and _KEY_MODE_VALIDATION.search(line)
        and 'implementation_markdown={IMPLEMENTATION_PLAN_MARKDOWN}' in line
    ]
    reports = [index for index, line in enumerate(lines) if re.match(r'^STEP \d+: Return the Report', line)]

    assert stores and plan_writes and validations and reports
    assert stores[0] < validations[0] and plan_writes[0] < validations[0] < reports[0]


@pytest.mark.parametrize('tui', _TUIS)
def test_every_finalizer_store_is_checked_for_the_content_loss_warning(tui: str) -> None:
    tasks = _tasks(_finalizer(tui))
    lines = tasks.split('\n')
    calls = [index for index, line in enumerate(lines) if line.lstrip().startswith('CALL ')]
    stores = _call_lines(lines, create_phase_finalizer_agent_tools(_adapter(tui)).update_document)

    assert stores
    for store in stores:
        following = [index for index in calls if index > store]
        bound = following[0] if following else len(lines)
        assert [index for index in range(store, bound) if CONTENT_LOSS_WARNING in lines[index]], (
            f'no content-loss check after: {lines[store].strip()}'
        )


@pytest.mark.parametrize('tui', _TUIS)
def test_the_self_check_routes_each_finding_by_its_owner(tui: str) -> None:
    # Scope 5: its own findings it fixes, an architect finding is drift it restores, and an
    # orchestrator finding names lines it carries forward unchanged.
    tasks = _tasks(_finalizer(tui))
    contract = template_contract(tasks)
    lines = tasks.split('\n')
    validations = [index for index, line in enumerate(lines) if _KEY_MODE_VALIDATION.search(line)]

    assert validations
    loop = next((index for index in range(validations[0], -1, -1) if lines[index].strip().startswith('REPEAT')), None)
    assert loop is not None
    body = contract.block_at(loop)
    assert [owner.value for owner in FindingOwner if f'"{owner.value}"' not in body] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_self_check_globs_the_paths_to_verify_of_the_kinds_the_finalizer_cites(tui: str) -> None:
    tasks = _tasks(_finalizer(tui))
    contract = template_contract(tasks)
    lines = tasks.split('\n')
    globs = [index for index, line in enumerate(lines) if re.search(r'\bGlob\(', line)]
    in_loop = [index for index in globs if any('paths_to_verify' in outer for outer in contract.enclosing_at(index))]

    assert in_loop
    loop_header = next(outer for outer in contract.enclosing_at(in_loop[0]) if 'paths_to_verify' in outer)
    assert [kind.value for kind in _OWNED_PATH_KINDS if f'"{kind.value}"' not in loop_header] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_writes_the_implementation_plan_the_architect_writes_inside_its_grant(tui: str) -> None:
    match = _IMPLEMENTATION_PLAN_PATH.search(_finalizer(tui))
    architect = generate_phase_architect_template(create_phase_architect_agent_tools(_adapter(tui)))

    assert match
    path = match.group('path')
    assert fnmatch(
        path.replace('{PLAN_NAME}', 'plan').replace('{PHASE_NAME}', 'phase'), _IMPLEMENTATION_PLAN_WRITE_SCOPE
    )
    assert path in architect


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_tells_brief_reviews_from_design_reviews_by_the_critics_tag(tui: str) -> None:
    # Scope 0 amendment 4: get_feedback is otherwise untagged (F31), so a design review's blockers,
    # which are the architect's, would read as the finalizer's.
    template = _finalizer(tui)

    assert BRIEF_REVIEW_TAG in template
    assert DESIGN_REVIEW_TAG in template


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_writes_phase_1s_marker_for_a_language_with_no_command(tui: str) -> None:
    # The checks pass any command opening with phase 1's marker, and the architect writes the same
    # text in a Checklist item, so the critic reads both as one answer to one question.
    architect = generate_phase_architect_template(create_phase_architect_agent_tools(_adapter(tui)))

    assert ASK_USER_COMMAND_MARKER.startswith(ASK_USER_MARKER)
    assert ASK_USER_COMMAND_MARKER in architect
    assert ASK_USER_COMMAND_MARKER in _finalizer(tui)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_never_proposes_research_after_the_design_is_approved(tui: str) -> None:
    contract = template_contract(_finalizer(tui))

    assert contract.report_format()
    assert contract.report_section('## Research proposals') == ['- None']


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalizer_asks_through_canonical_decision_entries(tui: str) -> None:
    entry = template_contract(_finalizer(tui)).report_section('## Decisions needed')

    assert entry
    assert entry[0].startswith('- OD-NNN | ')
    assert [line.split(':', 1)[0] for line in entry[1:]] == [
        '- Option A',
        '- Option B',
        '- Recommended',
        '- Affects',
    ]
