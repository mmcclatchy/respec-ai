"""The cooperative /respec-phase flow (docs/phase-cooperative/phase-2-cooperative-flow.md).

Agent side: B8 (the fixed four-section report), B20 (the architect always rehydrates and
decides newness by position) and B24 (no subagent touches the stage marker). The four
report headings, the `- result:` values and the `## User Input` heading are contract
strings: the orchestrator parses the report, and get_feedback writes the heading
(src/mcp/tools/feedback_tools_unified.py), so asserting them is deliberate (testing.md).

Orchestrator side: B4 and B8-B27 against the rendered phase command on every TUI. These
anchor on the twelve step numbers (template_contract.step_section), on block structure
(IF/ELIF/ELSE guards and their indentation), on reading order, and on the adapter-rendered
tool fields. The strings they match are contracts that something parses: the agents read
the `[round 0 | briefing]` feedback entry and the RP marks, get_feedback writes
`## Iteration `, bp-pipeline prints `BP_PIPELINE_COMPLETE. Output:`, the materializer emits
its JSON field names, frozen respec-code reads `- Read:` lines, and B10 counts happy-path
stops by the `TOUCHPOINT` heading token. `WAIT for`, `resume at Step` and `EXIT` are the
workflow grammar every command template shares. Prompt wording, option labels and display
text are never asserted, so rewording a prompt keeps this file green (manual check M6).

A multi-line tool field (an invocation, the resume text) that sits inside a block must be
indented as a unit when the template is built; substituted bare, its continuation lines
start at column 0 and end the enclosing block early.
"""

import re
from collections.abc import Callable
from functools import cache
from textwrap import dedent, indent

import pytest
from template_contract import REPORT_HEADINGS, WaitSite, template_contract

from src.models.enums import ShapeGate
from src.platform.adapters import get_platform_adapter
from src.platform.models import PhaseCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import (
    create_phase_architect_agent_tools,
    create_phase_command_tools,
    create_phase_critic_agent_tools,
)
from src.platform.templates.agents import generate_phase_architect_template, generate_phase_critic_template
from src.platform.templates.agents.phase_architect import technical_phase_template
from src.platform.templates.commands import generate_phase_command_template
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.utils.enums import LoopStatus


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')

STATUS_RESULT_LINE = '- result: complete | needs-user | failed'
ARCHITECT = 'respec-phase-architect'
CRITIC = 'respec-phase-critic'
AGENT_MODES = {ARCHITECT: 'explore | draft | revise', CRITIC: 'review'}


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


def _architect(tui: str) -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(_adapter(tui)))


def _critic(tui: str) -> str:
    return generate_phase_critic_template(create_phase_critic_agent_tools(_adapter(tui)))


_RENDERERS: dict[str, Callable[[str], str]] = {ARCHITECT: _architect, CRITIC: _critic}

_INVOCATION_INPUT = re.compile(r'^\s*-\s*(?P<name>\w+):', re.MULTILINE)


@cache
def _phase_command_tools(tui: str, platform: PlatformType = PlatformType.MARKDOWN) -> PhaseCommandTools:
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
def _phase_command(tui: str, platform: PlatformType = PlatformType.MARKDOWN) -> str:
    return generate_phase_command_template(_phase_command_tools(tui, platform))


def stage_marker_values_outside_the_example(template: str, embedded_example: str | None) -> dict[str, int]:
    # technical_phase_template always emits the default marker; B1 makes that line inert, so it is
    # the one tolerated occurrence (B24).
    allowed = embedded_example or ''
    extra = {gate.value: template.count(gate.value) - allowed.count(gate.value) for gate in ShapeGate}
    return {value: count for value, count in extra.items() if count}


def _embedded_example(agent: str) -> str | None:
    return indent(technical_phase_template, '  ') if agent == ARCHITECT else None


def _after_tasks(template: str) -> str:
    return template[template.index('TASKS:') :]


# ---------------------------------------------------------------------------
# B8 (agent half) - every subagent returns the fixed four-section report
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('agent', [ARCHITECT, CRITIC])
def test_every_phase_subagent_ends_with_the_four_report_sections_in_order(agent: str, tui: str) -> None:
    block = template_contract(_RENDERERS[agent](tui)).report_format()

    assert [line for line in block if line.startswith('## ')] == list(REPORT_HEADINGS)
    assert next(line for line in block if line) == REPORT_HEADINGS[0]


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('agent', [ARCHITECT, CRITIC])
def test_the_report_status_carries_the_result_the_orchestrator_branches_on(agent: str, tui: str) -> None:
    status = template_contract(_RENDERERS[agent](tui)).report_section('## Status')

    assert [line.split(':', 1)[0] for line in status] == ['- result', '- mode', '- persisted', '- detail']
    assert status[0] == STATUS_RESULT_LINE
    assert status[1] == f'- mode: {AGENT_MODES[agent]}'


@pytest.mark.parametrize('agent', [ARCHITECT, CRITIC])
def test_an_empty_report_section_is_written_as_a_single_none_bullet(agent: str) -> None:
    template = _RENDERERS[agent]('claude-code')

    assert template_contract(template).report_format()
    assert '`- None`' in template


@pytest.mark.parametrize('agent', [ARCHITECT, CRITIC])
def test_a_report_with_no_four_sections_is_not_mistaken_for_one(agent: str) -> None:
    template = _RENDERERS[agent]('claude-code')
    without_status = '\n'.join(line for line in template.split('\n') if line.strip() != '## Status')

    block = template_contract(without_status).report_format()

    assert [line for line in block if line.startswith('## ')] != list(REPORT_HEADINGS)


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize(
    ('agent', 'invocation_field'),
    [
        (ARCHITECT, 'invoke_architect_explore'),
        (ARCHITECT, 'invoke_architect_draft'),
        (ARCHITECT, 'invoke_architect_revise'),
        (CRITIC, 'invoke_critic_review'),
    ],
)
def test_every_input_the_orchestrator_passes_is_one_the_agent_declares(
    agent: str, invocation_field: str, tui: str
) -> None:
    # README "Agents and modes": the relay passes mode, IDs and config context (plus the critic's
    # review_round). An input the agent does not declare is dropped; one it declares but never
    # receives is read as empty.
    invocation = getattr(_phase_command_tools(tui), invocation_field)
    passed = {match.group('name') for match in _INVOCATION_INPUT.finditer(invocation)}

    contract = template_contract(_RENDERERS[agent](tui))
    declared = contract.declared_inputs('### Scalar Inputs') | contract.declared_inputs('### Grouped Markdown Inputs')

    assert passed == declared


# ---------------------------------------------------------------------------
# B20 (architect half) - a send-back is never lost
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_has_no_loop_status_gate_in_front_of_feedback(tui: str) -> None:
    template = _architect(tui)

    assert 'get_loop_status' not in template
    assert 'LOOP_STATUS' not in template


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize(
    'rehydration_call',
    [
        'mcp__respec-ai__get_document(doc_type="phase"',
        'mcp__respec-ai__get_feedback(',
        'mcp__respec-ai__get_previous_analysis(',
    ],
)
def test_every_architect_engagement_rehydrates_before_any_mode_work(tui: str, rehydration_call: str) -> None:
    tasks = _after_tasks(_architect(tui))
    first_mode_branch = tasks.index('IF phase_mode ==')

    guards = template_contract(tasks[:first_mode_branch]).guards_for(rehydration_call)

    assert () in guards, f'no unconditional {rehydration_call} before the first mode branch'


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_decides_what_is_new_by_user_input_position(tui: str) -> None:
    # The watermark is the highest `## User Input <i>` applied, kept in the notes slot: read
    # on every engagement and written on every engagement. A round number cannot serve,
    # because the guidance, the briefing answers and relayed questions all share round 0.
    tasks = template_contract(_after_tasks(_architect(tui)))

    assert '## User Input' in _architect(tui)
    assert () in tasks.guards_for('CALL mcp__respec-ai__get_previous_analysis(')
    assert () in tasks.guards_for('CALL mcp__respec-ai__store_current_analysis(')


@pytest.mark.parametrize('tui', _TUIS)
def test_every_architect_engagement_stores_its_complete_notes(tui: str) -> None:
    tasks = _after_tasks(_architect(tui))

    guards = template_contract(tasks).guards_for('CALL mcp__respec-ai__store_current_analysis(')

    assert () in guards, 'the notes store is conditional, so some engagement returns without its notes'


# ---------------------------------------------------------------------------
# B24 (agent half) - only the orchestrator writes the stage marker
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('agent', [ARCHITECT, CRITIC])
def test_no_phase_subagent_sets_tests_or_branches_on_a_stage_marker_value(agent: str, tui: str) -> None:
    template = _RENDERERS[agent](tui)

    assert stage_marker_values_outside_the_example(template, _embedded_example(agent)) == {}


@pytest.mark.parametrize('agent', [ARCHITECT, CRITIC])
def test_the_stage_marker_check_fires_on_an_instruction_that_sets_the_marker(agent: str) -> None:
    template = _RENDERERS[agent]('claude-code') + '\nSet `### Shape Gate` to `shape-proposed`.\n'

    assert stage_marker_values_outside_the_example(template, _embedded_example(agent)) == {'shape-proposed': 1}


# ---------------------------------------------------------------------------
# Orchestrator: shared structure readers
# ---------------------------------------------------------------------------

_STEPS = [str(number) for number in range(1, 13)]
_TOUCHPOINTS = ['6', '10', '11']
_SUBAGENT_STEPS = ['5', '6', '7', '8', '9', '10', '11']
_REENGAGEMENT_SITES = {'6': 'explore', '7': 'revise', '8': 'draft', '9': 'revise', '10': 'revise', '11': 'revise'}
_AGENT_MODES = {'explore', 'draft', 'revise', 'review'}

_EXIT = re.compile(r'\bEXIT\b')
_USER_DECISION = re.compile(r'source=user(?=\s)')
_PHASE_FILE_WRITE = re.compile(r'\bwrite\b.*\bPHASE_FILE_PATH\b', re.IGNORECASE)
_STORE_DOCUMENT = 'mcp__respec-ai__store_document('
_STORE_FEEDBACK = 'mcp__respec-ai__store_user_feedback('
_VALIDATE_DOCUMENT = 'mcp__respec-ai__validate_document('
_MATERIALIZE = 'respec-ai materialize-skeletons'
_RECORDS_ARCHITECT_ID = re.compile(r'\bARCHITECT_AGENT_ID\s*=(?!=)')
_ROUND_TAG = re.compile(r'\[round [^|\]<>]+ \| (?P<kind>briefing|review|sign-off|question)\]')
_CONDITION_HEADER = re.compile(r'^\s*(?:IF|ELIF|ELSE)\b')


def _names_step(number: str) -> re.Pattern[str]:
    return re.compile(rf'\bStep {number}\b(?!\.\d)')


def _architect_mode_set(mode: str) -> re.Pattern[str]:
    return re.compile(rf'\bARCHITECT_MODE\s*=\s*["\'`]?{mode}\b')


def _top_level(step: str | None) -> str | None:
    return step.split('.', 1)[0] if step else None


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip())


class _Command:
    def __init__(self, template: str) -> None:
        self.template = template
        self.contract = template_contract(template)
        self.lines = template.split('\n')
        self.steps = [_top_level(step) for step in self.contract.line_steps()]

    def section(self, step: str) -> str:
        return self.contract.step_section(step)

    def rows(self, step: str) -> list[int]:
        return [index for index, owner in enumerate(self.steps) if owner == step]

    def find(self, step: str, needle: str | re.Pattern[str]) -> list[int]:
        return [index for index in self.rows(step) if _matches(self.lines[index], needle)]

    def everywhere(self, needle: str | re.Pattern[str]) -> list[int]:
        return [index for index, line in enumerate(self.lines) if _matches(line, needle)]

    def sites(self, block: str, step: str) -> list[int]:
        return [index for index in self.contract.block_sites(block) if self.steps[index] == step]

    def guarded_by(self, index: int, needle: str) -> bool:
        return any(needle in guard for guard in self.contract.guards_at(index))


def _matches(line: str, needle: str | re.Pattern[str]) -> bool:
    return needle in line if isinstance(needle, str) else bool(needle.search(line))


def _decision_branch_body(text: str, value: str) -> str | None:
    try:
        return template_contract(text).decision_branch(value).body
    except ValueError:
        return None


def _chain_following(lines: list[str], index: int) -> str:
    base = _indentation(lines[index])
    chain: list[str] = []
    opened = False
    for line in lines[index + 1 :]:
        if not line.strip() or _indentation(line) > base:
            chain.append(line)
            continue
        header = _CONDITION_HEADER.match(line) if _indentation(line) == base else None
        if not header or (line.strip().startswith('IF') and opened):
            break
        opened = True
        chain.append(line)
    return '\n'.join(chain)


def _not_a_prohibition(line: str) -> bool:
    return 'never' not in line.lower()


def _without_frontmatter(text: str) -> str:
    if not text.startswith('---\n'):
        return text
    return text[text.index('\n---\n', 4) + len('\n---\n') :]


# ---------------------------------------------------------------------------
# Orchestrator: checkers shared by the real-template tests and their self-tests
# ---------------------------------------------------------------------------


def user_decisions_recorded_without_a_prompt(template: str) -> list[str]:
    """Every `source=user` decision line with no `WAIT for` above it in its own step (B9).

    `source=user-edit` (a hand-edit diff) also contains `source=user`, so a space must follow.
    """
    command = _Command(template)
    unprompted: list[str] = []
    for index, line in enumerate(command.lines):
        if not _USER_DECISION.search(line):
            continue
        step = command.steps[index]
        prompts = (
            [row for row in command.rows(step) if row < index and 'WAIT for' in command.lines[row]] if step else []
        )
        if not prompts:
            unprompted.append(line.strip())
    return unprompted


def unguarded_waits_outside_touchpoints(template: str) -> list[WaitSite]:
    contract = template_contract(template)
    touchpoints = set(contract.touchpoint_steps())
    return [site for site in contract.wait_sites() if site.top_level_step not in touchpoints and not site.guarded]


def research_dispatch_steps(template: str, dispatch: str) -> list[str | None]:
    command = _Command(template)
    return [command.steps[index] for index in command.contract.block_sites(dispatch)]


def stores_not_mirrored_to_the_phase_file(template: str) -> list[str]:
    """Orchestrator document stores after the start-of-run sync with no write of PHASE_FILE_PATH
    between them and the next store in the same step (B23)."""
    command = _Command(template)
    after_sync = [step for step in dict.fromkeys(command.steps) if step and step not in ('1', '2')]
    unmirrored: list[str] = []
    for step in after_sync:
        rows = command.rows(step)
        stores = command.find(step, _STORE_DOCUMENT)
        writes = command.find(step, _PHASE_FILE_WRITE)
        for position, store in enumerate(stores):
            bound = stores[position + 1] if position + 1 < len(stores) else rows[-1] + 1
            if not any(store < write < bound for write in writes):
                unmirrored.append(f'Step {step}: {command.lines[store].strip()}')
    return unmirrored


def reengagement_gaps(template: str, tools: PhaseCommandTools, step: str, mode: str) -> list[str]:
    command = _Command(template)
    fresh = command.sites(getattr(tools, f'invoke_architect_{mode}'), step)
    gaps = [] if fresh else [f'no fresh {mode} invocation']
    if not tools.resume_architect:
        return gaps + (
            ['SendMessage is named on a TUI that cannot resume a subagent'] if 'SendMessage' in template else []
        )
    resumes = command.sites(tools.resume_architect, step)
    if not resumes:
        return gaps + ['no resume of the recorded architect']
    first_resume = resumes[0]
    if not command.guarded_by(first_resume, 'ARCHITECT_AGENT_ID'):
        gaps.append('the resume does not depend on a recorded ARCHITECT_AGENT_ID')
    if not any(index > first_resume for index in fresh):
        gaps.append('no fresh invocation to fall back to after the resume')
    if not any(index < first_resume for index in command.find(step, _architect_mode_set(mode))):
        gaps.append(f'ARCHITECT_MODE is not set to {mode} before the resume')
    if fresh and not any(index > fresh[0] for index in command.find(step, _RECORDS_ARCHITECT_ID)):
        gaps.append('the agent ID a fresh invocation returns is not recorded')
    return gaps


def _reengagement_block(tools: PhaseCommandTools, mode: str) -> str:
    fresh = getattr(tools, f'invoke_architect_{mode}')
    if not tools.resume_architect:
        return f'ARCHITECT_MODE = "{mode}"\n{fresh}\n'
    return (
        f'ARCHITECT_MODE = "{mode}"\n'
        'IF ARCHITECT_AGENT_ID is set:\n'
        f'{indent(tools.resume_architect, "  ")}\n'
        'IF ARCHITECT_AGENT_ID is not set OR the resume is refused:\n'
        f'{indent(fresh, "  ")}\n'
        '  ARCHITECT_AGENT_ID = [the agent ID the invocation returns]\n'
    )


# ---------------------------------------------------------------------------
# Checker self-tests: each fires on a violation and accepts a shape the rewrite can emit
# ---------------------------------------------------------------------------


def test_the_decision_check_fires_on_a_decision_written_before_its_prompt() -> None:
    template = dedent("""\
    ### Step 6: Briefing (TOUCHPOINT)
    Ask OD-001.
    WAIT for the user response.
    ### Step 10: Design Review (TOUCHPOINT)
    - SD-002 | source=user | supersedes=CQ-001 | decision=keep | binding=yes
    WAIT for the user response.
    """)

    assert user_decisions_recorded_without_a_prompt(template) == [
        '- SD-002 | source=user | supersedes=CQ-001 | decision=keep | binding=yes'
    ]


def test_the_decision_check_accepts_answers_and_hand_edit_entries() -> None:
    template = dedent("""\
    ### Step 10: Design Review (TOUCHPOINT)
    - SD-003 | source=user-edit | section=Design Shape > Test List | decision=renamed | binding=yes
    FOR each OD in OPEN_DECISIONS:
      WAIT for the user response.
      - SD-004 | source=user | supersedes=OD-002 | decision=A | binding=yes
    """)

    assert user_decisions_recorded_without_a_prompt(template) == []


def test_the_touchpoint_check_fires_on_an_unguarded_prompt_off_the_happy_path() -> None:
    template = dedent("""\
    ### Step 6: Briefing (TOUCHPOINT)
    WAIT for the user response.
    ### Step 9: Critic Review and Automatic Repair
    Ask whether to keep repairing.
    WAIT for the user response.
    """)

    assert [site.step for site in unguarded_waits_outside_touchpoints(template)] == ['9']


def test_the_touchpoint_check_accepts_a_guarded_prompt_below_an_indented_invocation() -> None:
    explore = indent(_phase_command_tools('codex').invoke_architect_explore, '    ')
    template = (
        '### Step 4: Route on the Stage Marker\n'
        'IF SHAPE_GATE == "shape-settled":\n'
        f'{explore}\n'
        '  Ask whether to re-open the signed-off design.\n'
        '  WAIT for the user response.\n'
        '### Step 6: Briefing (TOUCHPOINT)\n'
        'WAIT for the user response.\n'
    )

    assert unguarded_waits_outside_touchpoints(template) == []


def test_an_unindented_multi_line_field_inside_a_condition_hides_the_condition() -> None:
    # Documents the indentation requirement in the module docstring: the field's continuation
    # lines end the IF block, so the prompt below them reads as unconditional.
    explore = _phase_command_tools('codex').invoke_architect_explore
    template = (
        '### Step 4: Route on the Stage Marker\n'
        'IF SHAPE_GATE == "shape-settled":\n'
        f'  {explore}\n'
        '  WAIT for the user response.\n'
    )

    assert [site.step for site in unguarded_waits_outside_touchpoints(template)] == ['4']


def test_the_dispatch_check_fires_on_a_second_dispatch_site() -> None:
    dispatch = _phase_command_tools('opencode').invoke_bp_pipeline
    template = (
        '### Step 6: Briefing (TOUCHPOINT)\n'
        'IF the user declined every proposal:\n'
        f'{indent(dispatch, "  ")}\n'
        '### Step 7: Run Approved Research\n'
        'FOR each item in RESEARCH_QUEUE:\n'
        f'{indent(dispatch, "  ")}\n'
    )

    assert research_dispatch_steps(template, dispatch) == ['6', '7']


@pytest.mark.parametrize('tui', _TUIS)
def test_the_dispatch_check_accepts_one_indented_dispatch_site(tui: str) -> None:
    dispatch = _phase_command_tools(tui).invoke_bp_pipeline
    template = f'### Step 7: Run Approved Research\nFOR each item in RESEARCH_QUEUE:\n{indent(dispatch, "  ")}\n'

    assert research_dispatch_steps(template, dispatch) == ['7']


def test_the_disk_mirror_check_fires_on_a_store_with_no_write_before_the_next_one() -> None:
    template = dedent("""\
    ### Step 2: Sync the Plan and Phase
    mcp__respec-ai__store_document(doc_type="phase", content=PHASE_MARKDOWN)
    ### Step 6: Briefing (TOUCHPOINT)
    mcp__respec-ai__store_document(doc_type="phase", content=WITH_SETTLED_DECISIONS)
    mcp__respec-ai__store_document(doc_type="phase", content=WITH_RESEARCH_MARKS)
    Write WITH_RESEARCH_MARKS to PHASE_FILE_PATH (Use Write tool).
    ### Step 8: Draft
    mcp__respec-ai__store_document(doc_type="phase", content=DRAFT)
    """)

    assert stores_not_mirrored_to_the_phase_file(template) == [
        'Step 6: mcp__respec-ai__store_document(doc_type="phase", content=WITH_SETTLED_DECISIONS)',
        'Step 8: mcp__respec-ai__store_document(doc_type="phase", content=DRAFT)',
    ]


def test_the_disk_mirror_check_accepts_a_write_after_every_store() -> None:
    template = dedent("""\
    ### Step 8: Draft
    mcp__respec-ai__store_document(
      doc_type="phase",
      content=DRAFT  (with "### Shape Gate" set to "shape-proposed")
    )
    Write the stored markdown to PHASE_FILE_PATH (Use Write tool).
    """)

    assert stores_not_mirrored_to_the_phase_file(template) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_reengagement_check_accepts_a_resume_with_a_fresh_fallback(tui: str) -> None:
    tools = _phase_command_tools(tui)
    template = '### Step 10: Design Review (TOUCHPOINT)\n' + _reengagement_block(tools, 'revise')

    assert reengagement_gaps(template, tools, '10', 'revise') == []


def test_the_reengagement_check_fires_on_an_unconditional_resume_with_no_fallback() -> None:
    tools = _phase_command_tools('claude-code')
    template = f'### Step 10: Design Review (TOUCHPOINT)\nARCHITECT_MODE = "revise"\n{tools.resume_architect}\n'

    assert reengagement_gaps(template, tools, '10', 'revise') == [
        'no fresh revise invocation',
        'the resume does not depend on a recorded ARCHITECT_AGENT_ID',
        'no fresh invocation to fall back to after the resume',
    ]


@pytest.mark.parametrize('tui', ['opencode', 'codex'])
def test_the_reengagement_check_fires_on_a_resume_where_none_is_possible(tui: str) -> None:
    tools = _phase_command_tools(tui)
    template = (
        '### Step 10: Design Review (TOUCHPOINT)\n'
        + _reengagement_block(tools, 'revise')
        + 'Use SendMessage to resume the architect.\n'
    )

    assert reengagement_gaps(template, tools, '10', 'revise') == [
        'SendMessage is named on a TUI that cannot resume a subagent'
    ]


# ---------------------------------------------------------------------------
# The step map, the single loop and the run setup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_workflow_runs_in_the_twelve_documented_steps(tui: str) -> None:
    numbers = template_contract(_phase_command(tui)).step_numbers()

    assert [number for number in numbers if '.' not in number] == _STEPS


@pytest.mark.parametrize('tui', _TUIS)
def test_one_review_loop_and_every_agent_input_are_set_up_before_any_agent_runs(tui: str) -> None:
    # The agent invocations pass LOOP_ID, PROJECT_CONFIG_CONTEXT_MARKDOWN and REVIEW_ROUND
    # (PhaseCommandTools), so the run must set each one before Step 5 first invokes an agent.
    command = _Command(_phase_command(tui))

    assert {command.steps[index] for index in command.everywhere('initialize_refinement_loop(')} == {'3'}
    assert len(command.everywhere('initialize_refinement_loop(')) == 1
    assert command.find('3', 'link_loop_to_document(')
    for variable in ('LOOP_ID', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'):
        assert command.find('3', re.compile(rf'\b{variable}\s*=(?!=)')), f'Step 3 never sets {variable}'
    assert command.find('3', re.compile(r'\bREVIEW_ROUND\s*=\s*0\b'))


# ---------------------------------------------------------------------------
# B8 (orchestrator half) - a failed or malformed report ends the workflow
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_orchestrator_names_every_report_heading_and_result_it_parses(tui: str) -> None:
    template = _phase_command(tui)

    assert [heading for heading in REPORT_HEADINGS if heading not in template] == []
    assert 'needs-user' in template
    assert '"complete"' not in template


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', _SUBAGENT_STEPS)
def test_a_failed_subagent_report_ends_the_workflow_with_its_detail_shown(step: str, tui: str) -> None:
    section = _Command(_phase_command(tui)).section(step)

    failed = template_contract(section).decision_blocks('failed')

    assert failed, f'Step {step} never branches on a failed subagent report'
    assert [block for block in failed if not (_EXIT.search(block) and 'detail' in block)] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_every_mode_the_orchestrator_passes_is_one_the_agents_accept(tui: str) -> None:
    # The agents answer any other phase_mode with `result: failed` (README "Agents and modes").
    modes = set(re.findall(r'phase_mode:\s*([\w-]+)', _phase_command(tui)))

    assert _AGENT_MODES <= modes <= _AGENT_MODES | {'ARCHITECT_MODE'}


# ---------------------------------------------------------------------------
# B9 - a decision is recorded only from a user's answer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_a_decision_is_recorded_only_from_an_answer_to_a_blocking_prompt(tui: str) -> None:
    template = _phase_command(tui)
    command = _Command(template)

    recording_steps = {command.steps[index] for index in command.everywhere(_USER_DECISION)}

    assert set(_TOUCHPOINTS) <= recording_steps
    assert user_decisions_recorded_without_a_prompt(template) == []


# ---------------------------------------------------------------------------
# B10 / B11 - at most three touchpoints; every prompt blocks and resumes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_happy_path_stops_for_the_user_at_exactly_three_touchpoints(tui: str) -> None:
    # TOUCHPOINT is a contract string (testing.md exception): B10 counts happy-path stops by it.
    assert template_contract(_phase_command(tui)).touchpoint_steps() == _TOUCHPOINTS


@pytest.mark.parametrize('tui', _TUIS)
def test_every_prompt_off_the_happy_path_waits_only_under_its_trigger(tui: str) -> None:
    template = _phase_command(tui)
    contract = template_contract(template)
    touchpoints = set(contract.touchpoint_steps())

    off_path = [site for site in contract.wait_sites() if site.top_level_step not in touchpoints]

    assert touchpoints, 'no step is marked as a touchpoint'
    assert off_path, 'expected the phase-file choice and the re-open prompt off the happy path'
    assert unguarded_waits_outside_touchpoints(template) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_every_user_prompt_blocks_and_names_where_the_workflow_resumes(tui: str) -> None:
    # Re-anchors test_phase_shape_act_gate.py:86 over every step of the new map.
    prompt = _adapter(tui).selection_prompt_instruction
    contract = template_contract(_phase_command(tui))
    unbalanced: dict[str, tuple[int, int, int]] = {}
    for step in _STEPS:
        section = contract.step_section(step)
        waits, resumes = contract.wait_prompt_count(section), contract.resume_marker_count(section)
        prompts = section.count(prompt)
        if waits != resumes or prompts > waits:
            unbalanced[step] = (prompts, waits, resumes)

    silent_touchpoints = [step for step in _TOUCHPOINTS if not contract.wait_prompt_count(contract.step_section(step))]

    assert silent_touchpoints == []
    assert unbalanced == {}


def test_every_prompt_is_identically_shaped_on_every_tui() -> None:
    # Re-anchors test_phase_shape_act_gate.py:100.
    shapes = {}
    for tui in _TUIS:
        contract = template_contract(_phase_command(tui))
        shapes[tui] = {step: contract.wait_prompt_count(contract.step_section(step)) for step in _STEPS}

    assert all(shape[step] for shape in shapes.values() for step in _TOUCHPOINTS), shapes
    assert all(shape == shapes['claude-code'] for shape in shapes.values()), shapes


# ---------------------------------------------------------------------------
# B12 / B13 - research costs nothing unless approved; a declined proposal stays declined
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_research_is_dispatched_from_a_single_site_in_step_7(tui: str) -> None:
    # Re-anchors test_frontend_elicitation_phase10.py:155 (was :163 at a64f0dc).
    dispatch = _phase_command_tools(tui).invoke_bp_pipeline

    assert research_dispatch_steps(_phase_command(tui), dispatch) == ['7']


@pytest.mark.parametrize('tui', _TUIS)
def test_research_runs_only_for_proposals_the_user_approved(tui: str) -> None:
    # `[approved]` is a contract string: the orchestrator writes it on the RP line at a
    # touchpoint and Step 7 selects by it.
    command = _Command(_phase_command(tui))
    dispatch = command.sites(_phase_command_tools(tui).invoke_bp_pipeline, '7')

    assert dispatch, 'Step 7 never dispatches bp-pipeline'
    before = [index for index in command.rows('7') if index < dispatch[0]]
    assert any('[approved]' in command.lines[index] for index in before)
    skips = [index for index in before if 'RETURN_TO' in command.lines[index] and command.contract.guards_at(index)]
    assert skips, 'no conditional exit from Step 7 precedes the dispatch, so an empty queue still dispatches'


@pytest.mark.parametrize('tui', _TUIS)
def test_research_is_reached_only_after_the_user_answers_the_proposals(tui: str) -> None:
    command = _Command(_phase_command(tui))

    assert not command.find('5', _names_step('7')), 'explore goes straight to research'
    for step in ('6', '10'):
        waits = command.find(step, 'WAIT for')
        routes = command.find(step, _names_step('7'))
        assert waits and any(route > waits[0] for route in routes), f'Step {step} never sends approved research on'


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['6', '10'])
def test_every_research_answer_is_marked_so_a_declined_proposal_is_never_offered_again(step: str, tui: str) -> None:
    # Re-anchors test_frontend_elicitation_phase10.py:200 (was :208). The RP marks are
    # contract strings: an offer skips any line that already carries one.
    section = _Command(_phase_command(tui)).section(step)

    assert '[declined]' in section
    assert '[approved]' in section


# ---------------------------------------------------------------------------
# B14 / B15 / B16 / B17 - research dispatch is runnable, optional, validated and bounded
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_research_dispatch_names_bp_pipeline_exactly_and_nothing_unrunnable(tui: str) -> None:
    template = _phase_command(tui)

    assert research_dispatch_steps(template, _phase_command_tools(tui).invoke_bp_pipeline)
    assert re.findall(r'Task\(bp\)|Skill\(bp\)|\$bp\b|respec-bp-pipeline', template) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_orchestrator_states_bp_pipeline_as_its_one_external_agent_before_any_step(tui: str) -> None:
    # F18: the shared Claude Code guardrail forbids any agent that is not a respec agent, so the
    # phase-local exception has to follow it.
    guardrail = _adapter(tui).subagent_invocation_guardrail
    body = _without_frontmatter(template_contract(_phase_command(tui)).preamble())

    assert guardrail in body
    assert 'bp-pipeline' in body[body.index(guardrail) + len(guardrail) :]


@pytest.mark.parametrize('tui', _TUIS)
def test_the_run_checks_bp_availability_once_and_never_ends_on_its_failure(tui: str) -> None:
    # Re-anchors test_frontend_elicitation_phase10.py:176 (was :184).
    command = _Command(_phase_command(tui))
    preflight = command.find('3', _phase_command_tools(tui).bp_preflight_command)

    assert preflight, 'Step 3 never runs the bp preflight'
    assert command.find('3', re.compile(r'\bBP_AVAILABLE\s*=(?!=)'))
    assert not _EXIT.search(_chain_following(command.lines, preflight[0]))
    assert [index for index in command.everywhere(_EXIT) if command.guarded_by(index, 'BP_AVAILABLE')] == []


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['6', '10'])
def test_proposals_are_offered_according_to_bp_availability(step: str, tui: str) -> None:
    assert 'BP_AVAILABLE' in _Command(_phase_command(tui)).section(step)


@pytest.mark.parametrize('tui', _TUIS)
def test_research_is_skipped_without_a_dispatch_when_bp_is_unavailable(tui: str) -> None:
    command = _Command(_phase_command(tui))
    dispatch = command.sites(_phase_command_tools(tui).invoke_bp_pipeline, '7')

    assert dispatch, 'Step 7 never dispatches bp-pipeline'
    skips = [
        index
        for index in command.find('7', 'RETURN_TO')
        if index < dispatch[0] and command.guarded_by(index, 'BP_AVAILABLE')
    ]
    assert skips


@pytest.mark.parametrize('tui', _TUIS)
def test_only_research_that_bp_pipeline_reports_complete_becomes_a_read_line(tui: str) -> None:
    # `BP_PIPELINE_COMPLETE. Output:` is bp-pipeline's completion signal and `- Read:` is the
    # line frozen respec-code reads (README "Research recording"); both are parsed.
    command = _Command(_phase_command(tui))
    dispatch = command.sites(_phase_command_tools(tui).invoke_bp_pipeline, '7')

    assert dispatch, 'Step 7 never dispatches bp-pipeline'
    recorded = [index for index in command.find('7', '- Read:') if index > dispatch[0]]
    assert recorded, 'Step 7 records no research after dispatching it'
    assert [index for index in command.find('7', 'BP_PIPELINE_COMPLETE. Output:') if index < recorded[0]]
    validation = range(dispatch[0], recorded[0])
    assert not [index for index in validation if _EXIT.search(command.lines[index])], 'a failed item ends the run'


@pytest.mark.parametrize('tui', _TUIS)
def test_research_dispatch_is_bounded_and_web_research_runs_one_at_a_time(tui: str) -> None:
    # Re-anchors test_command_templates.py:359 (was :353). F17: a web-research run writes
    # bp-pipeline's fixed /tmp search files, so two at once overwrite each other's results.
    section = _Command(_phase_command(tui)).section('7')

    assert 'synthesis-only' in section and 'web-research' in section
    assert re.search(r'\bMAX_ACTIVE_BP_WORKERS\s*=\s*3\b', section)
    assert re.search(r'\bMAX_ACTIVE_WEB_RESEARCH_WORKERS\s*=\s*1\b', section)


@pytest.mark.parametrize('tui', _TUIS)
def test_nothing_in_the_orchestrator_makes_research_mandatory(tui: str) -> None:
    template = _phase_command(tui)

    removed = ('post_synthesis', 'AUTO_API_PROMPTS', 'Synthesize:', 'validation_mode')

    assert [mechanism for mechanism in removed if mechanism in template] == []


# ---------------------------------------------------------------------------
# B4 (orchestrator half) / B18 - every draft is reviewed; mechanical findings are repaired
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_every_critic_review_is_stored_under_the_next_review_round(tui: str) -> None:
    # `## Iteration ` is the header get_feedback writes for each critic entry, so the check that
    # this round's review was stored reads it.
    command = _Command(_phase_command(tui))
    reviews = command.contract.block_sites(_phase_command_tools(tui).invoke_critic_review)

    assert reviews and {command.steps[index] for index in reviews} == {'9'}
    increments = command.find('9', re.compile(r'\bREVIEW_ROUND\s*(?:\+=\s*1|=\s*REVIEW_ROUND\s*\+\s*1)\b'))
    assert increments and increments[0] < reviews[0]
    assert [index for index in command.find('9', '## Iteration ') if index > reviews[0]]


@pytest.mark.parametrize('tui', _TUIS)
def test_every_review_decision_compares_against_a_real_loop_status(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('9')

    compared = set(re.findall(r'\bREVIEW_DECISION\s*==\s*"([^"]+)"', section))

    assert {'completed', 'refine', 'user_input'} <= compared
    assert compared <= {status.value for status in LoopStatus}


@pytest.mark.parametrize('tui', _TUIS)
def test_a_clean_review_goes_on_to_design_review(tui: str) -> None:
    body = _decision_branch_body(_Command(_phase_command(tui)).section('9'), 'completed')

    assert body is not None and _names_step('10').search(body)


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('status', ['refine', 'user_input'])
def test_open_mechanical_findings_get_two_silent_repairs_then_reach_the_user(status: str, tui: str) -> None:
    body = _decision_branch_body(_Command(_phase_command(tui)).section('9'), status)

    assert body is not None, f'Step 9 has no {status} branch of its own'
    assert re.search(r'\bREPAIR_ROUNDS\s*(?:<\s*2|<=\s*1)\b', body)
    assert re.search(r'\bREPAIR_ROUNDS\s*(?:\+=\s*1|=\s*REPAIR_ROUNDS\s*\+\s*1)\b', body)
    assert _names_step('9').search(body), 'the repair does not return to the critic'
    assert 'UNRESOLVED_CHECKS' in body and _names_step('10').search(body)


@pytest.mark.parametrize('tui', _TUIS)
def test_an_unknown_review_decision_ends_the_workflow(tui: str) -> None:
    lines = _Command(_phase_command(tui)).section('9').split('\n')
    headers = [index for index, line in enumerate(lines) if re.match(r'^\s*(?:IF|ELIF)\s+REVIEW_DECISION\b', line)]

    assert headers, 'Step 9 never branches on REVIEW_DECISION'
    chain = _chain_following(lines, headers[-1]).split('\n')
    closing = [index for index, line in enumerate(chain) if re.match(r'^\s*ELSE\b', line)]
    assert closing and _EXIT.search('\n'.join(chain[closing[-1] :]))


@pytest.mark.parametrize('tui', _TUIS)
def test_the_user_is_not_prompted_while_the_critic_reviews_and_the_architect_repairs(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('9')

    assert section and 'WAIT for' not in section


@pytest.mark.parametrize('tui', _TUIS)
def test_spent_repairs_reach_a_design_review_that_blocks_and_persists_the_answer(tui: str) -> None:
    # Re-anchors test_phase_workflow_gates.py:19: the user_input branch itself neither prompts
    # nor stores, so the test follows its route.
    command = _Command(_phase_command(tui))
    body = _decision_branch_body(command.section('9'), 'user_input')

    assert body is not None and _names_step('10').search(body)
    assert 'WAIT for' in command.section('10')
    assert _STORE_FEEDBACK in command.section('10')


@pytest.mark.parametrize('tui', _TUIS)
def test_repair_rounds_start_at_zero_and_reset_whenever_design_review_sends_work_back(tui: str) -> None:
    command = _Command(_phase_command(tui))
    reset = re.compile(r'\bREPAIR_ROUNDS\s*=\s*0\b')

    assert command.find('3', reset)
    assert command.find('10', reset)


@pytest.mark.parametrize('tui', _TUIS)
def test_accepting_the_unresolved_checks_is_recorded_as_the_users_decision(tui: str) -> None:
    # `supersedes=unresolved-checks` is a reserved token the critic reads, so the accepted
    # findings are never raised again.
    command = _Command(_phase_command(tui))

    accepted = command.find('10', 'supersedes=unresolved-checks')

    assert accepted and all(_USER_DECISION.search(command.lines[index]) for index in accepted)


# ---------------------------------------------------------------------------
# B19 / B20 / B21 - critic questions, send-backs, and re-engaging the architect
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_open_questions_are_asked_at_design_review_and_settled_before_sign_off_writes(tui: str) -> None:
    command = _Command(_phase_command(tui))
    materialize = command.find('11', _MATERIALIZE)

    assert re.search(r'\bCQ', command.section('10')) and re.search(r'\bOD', command.section('10'))
    assert materialize, 'sign-off never materializes the skeletons'
    for kind in (r'\bCQ', r'\bOD'):
        asked = command.find('11', re.compile(kind))
        assert asked and asked[0] < materialize[0], f'{kind} is not settled before the sign-off writes'


@pytest.mark.parametrize('tui', _TUIS)
def test_the_run_guidance_reaches_the_agents_as_the_round_zero_briefing_entry(tui: str) -> None:
    # `[round 0 | briefing]` is a contract string: both agents read the run's guidance from
    # the feedback entry with this tag.
    command = _Command(_phase_command(tui))
    tag = command.find('3', '[round 0 | briefing]')
    stores = command.find('3', _STORE_FEEDBACK)

    assert tag and stores and tag[0] <= stores[-1]
    assert command.find('3', 'WORKFLOW_GUIDANCE_MARKDOWN')


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['6', '7', '10'])
def test_direction_is_stored_before_the_architect_is_re_engaged(step: str, tui: str) -> None:
    tools = _phase_command_tools(tui)
    command = _Command(_phase_command(tui))
    fresh = [getattr(tools, f'invoke_architect_{mode}') for mode in ('explore', 'draft', 'revise')]
    sites = (
        command.sites(tools.resume_architect, step)
        if tools.resume_architect
        else sorted(index for invocation in fresh for index in command.sites(invocation, step))
    )
    stores = command.find(step, _STORE_FEEDBACK)

    assert sites, f'Step {step} never re-engages the architect'
    unstored = [site for previous, site in zip([-1, *sites], sites) if not any(previous < s < site for s in stores)]
    assert unstored == []


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize(('step', 'kinds'), [('6', ('question',)), ('7', ('review',)), ('10', ('review', 'question'))])
def test_every_stored_direction_carries_a_round_tag(step: str, kinds: tuple[str, ...], tui: str) -> None:
    tags = {match.group('kind') for match in _ROUND_TAG.finditer(_Command(_phase_command(tui)).section(step))}

    assert set(kinds) <= tags


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize(('step', 'mode'), sorted(_REENGAGEMENT_SITES.items()))
def test_the_architect_is_re_engaged_at_every_site_on_every_tui(step: str, mode: str, tui: str) -> None:
    assert reengagement_gaps(_phase_command(tui), _phase_command_tools(tui), step, mode) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_first_engagement_is_always_a_fresh_explore(tui: str) -> None:
    command = _Command(_phase_command(tui))

    assert command.sites(_phase_command_tools(tui).invoke_architect_explore, '5')
    assert 'SendMessage' not in command.section('5')


def test_claude_code_records_the_first_architect_so_later_steps_can_resume_it() -> None:
    command = _Command(_phase_command('claude-code'))
    explore = command.sites(_phase_command_tools('claude-code').invoke_architect_explore, '5')

    assert explore and [index for index in command.find('5', _RECORDS_ARCHITECT_ID) if index > explore[0]]


# ---------------------------------------------------------------------------
# B22 / B24 - the stage marker routes a re-run, and only the orchestrator writes it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_a_rerun_routes_on_the_stage_marker(tui: str) -> None:
    command = _Command(_phase_command(tui))

    def route_guards(target: str) -> list[tuple[str, ...]]:
        return [command.contract.guards_at(index) for index in command.find('4', _names_step(target))]

    to_explore, to_review = route_guards('5'), route_guards('9')

    assert all(gate.value in command.section('4') for gate in ShapeGate)
    assert any(any('unshaped' in guard for guard in guards) for guards in to_explore)
    assert not any(any('shape-' in guard for guard in guards) for guards in to_explore)
    assert any(any('shape-proposed' in guard for guard in guards) for guards in to_review)
    assert any(any('shape-amended' in guard for guard in guards) for guards in to_review)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_signed_off_phase_is_reopened_only_on_request_and_marked_amended_first(tui: str) -> None:
    command = _Command(_phase_command(tui))
    asked = [index for index in command.find('4', 'WAIT for') if command.guarded_by(index, 'shape-settled')]

    assert asked, 'the re-open prompt is not limited to a signed-off phase'
    stores = [index for index in command.find('4', _STORE_DOCUMENT) if index > asked[0]]
    assert stores
    assert [index for index in command.find('4', 'shape-amended') if asked[0] < index < stores[0]]
    reopened = [
        index
        for index in command.find('4', _names_step('9'))
        if index > stores[0] and command.guarded_by(index, 'shape-settled')
    ]
    assert reopened


@pytest.mark.parametrize('tui', _TUIS)
def test_the_first_draft_is_marked_proposed_by_the_orchestrator(tui: str) -> None:
    command = _Command(_phase_command(tui))
    draft = command.sites(_phase_command_tools(tui).invoke_architect_draft, '8')

    assert draft, 'Step 8 never drafts'
    assert [index for index in command.find('8', 'shape-proposed') if index > draft[0]]
    assert [index for index in command.find('8', _STORE_DOCUMENT) if index > draft[0]]


@pytest.mark.parametrize('tui', _TUIS)
def test_only_sign_off_marks_the_design_settled(tui: str) -> None:
    command = _Command(_phase_command(tui))

    naming = {command.steps[index] for index in command.everywhere(ShapeGate.SHAPE_SETTLED.value)}

    assert '11' in naming
    assert naming <= {None, '4', '11', '12'}


@pytest.mark.parametrize('tui', _TUIS)
def test_sign_off_checks_the_plan_materializes_marks_settled_mirrors_then_commits(tui: str) -> None:
    command = _Command(_phase_command(tui))
    plan_checks = [
        index
        for index in command.find('11', _EXIT)
        if command.guarded_by(index, 'IMPLEMENTATION_PLAN_PATH') or command.guarded_by(index, 'implementation.md')
    ]
    materialize = command.find('11', _MATERIALIZE)

    assert plan_checks and materialize and plan_checks[0] < materialize[0]
    settled = [index for index in command.find('11', ShapeGate.SHAPE_SETTLED.value) if index > materialize[0]]
    assert settled, 'the phase is not marked settled after materialization'
    assert [index for index in command.find('11', _EXIT) if materialize[0] < index < settled[0]], (
        'a failed materialization does not stop the phase from being marked settled'
    )
    mirrored = [index for index in command.find('11', _PHASE_FILE_WRITE) if index > settled[0]]
    commits = [index for index in command.find('11', 'git commit') if _not_a_prohibition(command.lines[index])]
    assert mirrored and commits and mirrored[0] < commits[0]


# ---------------------------------------------------------------------------
# B23 - nothing the orchestrator stores is lost to the start-of-run sync
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('platform', list(PlatformType))
@pytest.mark.parametrize('tui', _TUIS)
def test_every_orchestrator_store_is_mirrored_to_the_phase_file(tui: str, platform: PlatformType) -> None:
    template = _phase_command(tui, platform)
    command = _Command(template)

    storing_steps = {command.steps[index] for index in command.everywhere(_STORE_DOCUMENT)}

    assert {'4', '6', '7', '8', '10', '11'} <= storing_steps
    assert stores_not_mirrored_to_the_phase_file(template) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_draft_is_on_disk_before_every_design_review(tui: str) -> None:
    command = _Command(_phase_command(tui))
    waits = command.find('10', 'WAIT for')
    writes = command.find('10', _PHASE_FILE_WRITE)

    assert waits and writes and writes[0] < waits[0]


# ---------------------------------------------------------------------------
# B25 / B26 / B27 - hand edits, skeletons and the commit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_a_hand_edit_is_validated_diffed_and_stored_with_the_marker_restored(tui: str) -> None:
    # Re-anchors test_phase_shape_act_gate.py:71 on Step 10. `### Shape Gate` is the heading
    # the parser reads the marker from.
    command = _Command(_phase_command(tui))
    validated = command.find('10', _VALIDATE_DOCUMENT)
    diffed = command.find('10', 'source=user-edit')
    stored = command.find('10', _phase_command_tools(tui).store_document_user_edit.strip())

    assert validated and diffed and stored
    assert validated[0] < diffed[0] < stored[0]
    assert [index for index in command.find('10', '### Shape Gate') if validated[0] < index < stored[0]]
    assert [index for index in command.find('10', _names_step('9')) if index > stored[0]]


@pytest.mark.parametrize('tui', _TUIS)
def test_skeletons_materialize_only_at_sign_off(tui: str) -> None:
    # Re-anchors test_phase_skeleton_materialization_gate.py:33/:46/:59.
    command = _Command(_phase_command(tui))
    runs = command.everywhere(_MATERIALIZE)

    assert '11' in command.contract.touchpoint_steps()
    assert runs and {command.steps[index] for index in runs} == {'11'}
    waits = command.find('11', 'WAIT for')
    assert waits and waits[0] < runs[0]


@pytest.mark.parametrize('tui', _TUIS)
def test_a_skeleton_conflict_prompt_appears_only_for_an_existing_file_and_resumes_sign_off(tui: str) -> None:
    # Re-anchors test_phase_skeleton_materialization_gate.py:70. `reconciliation_needed` is the
    # materializer's JSON field for target files that already exist.
    command = _Command(_phase_command(tui))
    runs = command.find('11', _MATERIALIZE)

    assert runs, 'sign-off never materializes the skeletons'
    conflicts = [index for index in command.find('11', 'WAIT for') if index > runs[0]]
    assert conflicts
    unconditional = [
        index
        for index in conflicts
        if not any('reconciliation_needed' in line for line in command.contract.enclosing_at(index))
    ]
    assert unconditional == []
    unresumed = [
        index
        for index in conflicts
        if not any('resume at Step 11' in line for line in command.lines[index : index + 4])
    ]
    assert unresumed == []


@pytest.mark.parametrize('tui', _TUIS)
def test_unmaterialized_and_unintrospectable_paths_are_shown_and_recorded(tui: str) -> None:
    # Re-anchors test_phase_skeleton_materialization_gate.py:81. The path lists are the
    # materializer's JSON fields; user-menu and user-override are retired SD sources.
    template = _phase_command(tui)
    section = _Command(template).section('11')

    assert 'unmaterialized_paths' in section and 'unintrospectable_paths' in section
    assert re.findall(r'source=user-(?:menu|override)', template) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_a_commit_runs_only_on_the_users_word_and_never_bypasses_hooks(tui: str) -> None:
    template = _phase_command(tui)
    command = _Command(template)
    commits = [index for index in command.everywhere('git commit') if _not_a_prohibition(command.lines[index])]
    waits = command.find('11', 'WAIT for')

    assert '--no-verify' not in template
    assert commits and {command.steps[index] for index in commits} == {'11'}
    assert waits and all(command.contract.guards_at(index) and index > waits[0] for index in commits)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_commit_stages_exactly_the_files_this_run_wrote(tui: str) -> None:
    command = _Command(_phase_command(tui))

    staging = [command.lines[i] for i in command.everywhere('git add') if _not_a_prohibition(command.lines[i])]
    staged = ' '.join(staging)

    assert staging and all('git add --' in line for line in staging)
    assert all(path in staged for path in ('PHASE_FILE_PATH', 'IMPLEMENTATION_PLAN_PATH', 'WRITTEN_PATHS'))
    assert 'SCRATCH' not in staged


# ---------------------------------------------------------------------------
# Step 12 - store on the platform, then hand off
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_run_stores_to_the_platform_before_its_completion_contract_and_hands_off(tui: str) -> None:
    # Re-anchors test_command_templates.py:658 (was :652). The completion contract heading is
    # asserted verbatim by test_command_templates.py:672.
    tools = _phase_command_tools(tui)
    command = _Command(_phase_command(tui))
    stored = command.find('12', tools.create_phase_tool)
    contract = command.find('12', 'Completion contract')

    assert stored and contract and stored[0] < contract[0]
    assert tools.code_command_invocation.strip() in command.section('12')
    assert 'Automatic Task Generation' not in command.template


# ---------------------------------------------------------------------------
# Fixes after review: accept-all re-engagement, CQ filter, free-text asks, exit rule
# ---------------------------------------------------------------------------

_ACCEPT_ALL = 'IF the user chose "Accept the recommended default for all remaining":'
_FREE_TEXT_ASK = re.compile(r'^\s*Ask the user for it in one message\.', re.MULTILINE)


def _accept_all_branch(section: str) -> str:
    start = section.index(_ACCEPT_ALL)
    return section[start : section.index('BREAK', start)]


def _lines_with(section: str, needle: str) -> list[str]:
    return [line for line in section.split('\n') if needle in line]


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['10', '11'])
def test_accepting_every_default_still_sends_a_design_changing_critic_answer_back(step: str, tui: str) -> None:
    section = _Command(_phase_command(tui)).section(step)
    branch = _accept_all_branch(section)

    assert 'DESIGN_CHANGE_SD_IDS.append' in branch
    assert 'Option B' in branch


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['10', '11'])
def test_a_design_changing_answer_is_queued_under_a_user_sd_and_sent_in_the_feedback(step: str, tui: str) -> None:
    section = _Command(_phase_command(tui)).section(step)
    appends = _lines_with(section, 'DESIGN_CHANGE_SD_IDS.append')
    send_back = section[section.index('IF DESIGN_CHANGE_SD_IDS is not empty') :]

    assert len(appends) == 2
    assert (
        'USER_FEEDBACK_MARKDOWN' in send_back
        and 'DESIGN_CHANGE_SD_IDS' in send_back.split('USER_FEEDBACK_MARKDOWN', 1)[1]
    )
    assert 'DESIGN_CHANGE_SD_IDS = []' in send_back
    lines = section.split('\n')
    for index, line in enumerate(lines):
        if 'DESIGN_CHANGE_SD_IDS.append' in line:
            preceding = lines[max(0, index - 4) : index]
            assert any('Record "- SD-NNN | source=user | supersedes=[OD or CQ ID]' in earlier for earlier in preceding)


@pytest.mark.parametrize('tui', _TUIS)
def test_step_10_asks_only_the_critic_questions_no_decision_has_settled(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('10')
    line = next(line for line in section.split('\n') if line.startswith('QUESTIONS ='))
    block = section[section.index(line) :].split('NEW_PROPOSALS', 1)[0]

    assert 'no SD' in block and 'supersedes' in block


@pytest.mark.parametrize('tui', _TUIS)
def test_every_materializer_outcome_sd_names_the_materializer_as_its_source(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('11')
    outcomes = [
        line
        for line in _lines_with(section, 'MATERIALIZATION_SDS.append')
        if any(word in line for word in ('unmaterialized', 'unintrospectable', 'unresolved signature', 'merge skipped'))
    ]
    user_lines = [line for line in _lines_with(section, 'MATERIALIZATION_SDS.append') if 'source=user' in line]

    assert len(outcomes) == 4
    assert all('source=materializer' in line for line in outcomes)
    assert all('CONFLICT' in line for line in user_lines) and len(user_lines) == 3


@pytest.mark.parametrize('tui', _TUIS)
def test_an_edited_research_proposal_asks_for_the_edit_before_rewriting_it(tui: str) -> None:
    command = _Command(_phase_command(tui))
    rewrite = command.find('6', "Rewrite the RP line's")
    asks = [index for index in command.find('6', _FREE_TEXT_ASK) if rewrite and index < rewrite[0]]

    assert rewrite and asks
    assert any('WAIT for' in line for line in command.lines[asks[-1] : rewrite[0]])
    assert any('resume at Step 6.3' in line for line in command.lines[asks[-1] : rewrite[0]])


@pytest.mark.parametrize('tui', _TUIS)
def test_a_supplied_verify_command_is_asked_for_and_recorded_verbatim(tui: str) -> None:
    command = _Command(_phase_command(tui))
    section = command.section('6')
    start = section.index('Supply the command now')
    branch = section[start:].split('#### Step 6.3', 1)[0]

    assert 'Ask the user for it in one message' in branch
    assert 'WAIT for' in branch and 'resume at Step 6.2' in branch
    assert 'verbatim' in branch


@pytest.mark.parametrize('tui', _TUIS)
def test_the_briefing_exit_follows_the_recorded_sd_not_the_click(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('6')
    guard = next(line for line in section.split('\n') if line.startswith('IF ') and 'Design Source' in line)

    assert 'SD' in guard and 'recorded' in guard
    assert 'the user chose' not in guard


@pytest.mark.parametrize('tui', _TUIS)
def test_accepting_every_briefing_default_never_ends_the_run_without_an_explicit_choice(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('6')
    branch = _accept_all_branch(section)

    assert 'ASK_ON_ITS_OWN.append' in branch, 'accept-all records a run-ending recommendation without asking'
    assert 'FOR each OD in ASK_ON_ITS_OWN:' in section
    held_back = section[section.index('FOR each OD in ASK_ON_ITS_OWN:') :].split('#### Step 6.3', 1)[0]
    guard = branch.split('ASK_ON_ITS_OWN.append', 1)[0].rsplit('\n', 2)[-2]
    assert guard.lstrip().startswith('IF ') and 'Design Source' in guard and 'verify command' in guard
    assert 'WAIT for' in held_back and 'resume at Step 6.2' in held_back
    assert 'Accept the recommended default for all remaining' not in held_back
    assert 'Record "- SD-NNN | source=user | supersedes=[OD ID]' in held_back


@pytest.mark.parametrize('tui', _TUIS)
def test_the_accept_all_option_is_promised_only_for_open_decision_and_question_prompts(tui: str) -> None:
    template = _phase_command(tui)
    rule = template[template.index('**Prompts.**') :].split('\n\n', 1)[0]

    assert re.search(r'\bOD\b', rule) and re.search(r'\bCQ\b', rule)
    assert 'Every decision prompt' not in rule


@pytest.mark.parametrize('tui', _TUIS)
def test_a_deduplicated_research_proposal_gets_a_read_line_pointing_at_its_twin(tui: str) -> None:
    section = _Command(_phase_command(tui)).section('7')

    assert 'DEDUPED' in section
    assert (
        'FOR each' in section[section.index('DEDUPED') :] and 'DEDUPED' in section.split('NEW_READ_LINES.append(')[-2]
    )
