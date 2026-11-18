"""Phase 4 — the review of the finalized brief (docs/phase-cooperative/phase-4-agent-ready-brief.md).

The critic's half of B13, and the critic side of Scope 8: the `review` branch splits on
`review_target`, the brief branch runs only its own checks and none of the design-review rules, and
each branch tags the stored feedback so the agent that repairs it can tell the two reviews apart.

The orchestrator's half (Scope 9): B12 (Step 10.7 finalizes and reviews the brief between design
approval and sign-off, with no prompt, repairing only through the finalizer, and no route into
Step 11 skips it), B13 (nothing after approval researches), B14 (every settled decision for an
answered OD or CQ carries affects=), B18's routing half for Step 10.7, and the sign-off additions.

These tests anchor on structure: the two `review_target` branches, read the way
test_phase_implementation_plan_gate._phase_mode_branch_body reads a `phase_mode` branch, and in the
command the step numbers, the IF/ELIF/ELSE blocks and the adapter-rendered invocation fields. The
strings they match are contracts something parses: the `[<Marker> - BLOCKING]` and
`[judgment] [<Marker>]` names are what template_contract reads, the review tags are what the
finalizer matches in get_feedback's output (both import them), REVIEWED_PHASE_SECTIONS is the list
the finalizer reproduces, the FindingOwner values and `structural_findings` are what
validate_document returns, `## Iteration ` is the heading get_feedback writes, and the SD keys are
what phase 3's segment parser reads.
"""

import re
from functools import cache

import pytest
from template_contract import template_contract

from src.models.document_validation import FindingOwner
from src.platform.adapters import get_platform_adapter
from src.platform.models import PhaseCommandTools
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import (
    create_phase_command_tools,
    create_phase_critic_agent_tools,
    create_phase_finalizer_agent_tools,
)
from src.platform.templates.agents import generate_phase_critic_template, generate_phase_finalizer_template
from src.platform.templates.commands import generate_phase_command_template
from src.platform.templates.phase_contract_grammar import (
    BRIEF_REVIEW_TAG,
    DESIGN_REVIEW_TAG,
    QUOTED_LINE_BREAK,
    REVIEWED_PHASE_SECTIONS,
)
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.utils.phase_structure import SD_KEYS


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')
_TARGETS = ('design', 'brief')
_TAGS = {'design': DESIGN_REVIEW_TAG, 'brief': BRIEF_REVIEW_TAG}

# The rules the user settles at design review (Scope 8 and B13). The brief review re-opens none of
# them: the finalizer never changes the sections they cover. Test List coverage moves to the
# structural test-not-in-any-step once every step is finalized.
DESIGN_REVIEW_RULES = frozenset(
    {
        'unjustified-seam',
        'under-surfaced-decision',
        'non-divergent-decision-options',
        'plan-constraint-violation',
        'implementation-plan-reference-not-applied',
        'ux-contract-flow-missing-pass-condition',
        'ux-contract-route-missing-auth',
        'missing-state-ownership-decision',
        'undecided-screen-decomposition',
        'missing-component-provenance-decision',
        'missing-design-source-decision',
        'test-list-entry-not-covered',
    }
)
BRIEF_REVIEW_MARKERS = frozenset({'grounding-path-invalid', 'step-file-verb-invalid', 'reviewed-section-changed'})

_ASSESSMENT_SUMMARY = re.compile(r'^\s*- \*\*Assessment Summary\*\*:\s*(?P<value>.*)$', re.MULTILINE)
_CONDITION = re.compile(r'^\s*(?:IF|ELIF)\b')


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


@cache
def _critic(tui: str) -> str:
    return generate_phase_critic_template(create_phase_critic_agent_tools(_adapter(tui)))


def review_branch(template: str, target: str) -> str:
    return template_contract(template).condition_block('review_target', target)


def rules_raised(text: str) -> set[str]:
    contract = template_contract(text)
    return contract.blocker_conditions() | contract.mechanical_findings() | contract.judgment_findings()


def _flat(text: str) -> str:
    return ' '.join(text.split())


# ---------------------------------------------------------------------------
# Checker self-tests
# ---------------------------------------------------------------------------

_CHAIN = """IF review_target == "design":
  [judgment] [Unjustified Seam] CQ-NNN: x
ELIF review_target == "brief":
  [mechanical] [Grounding Path Invalid - BLOCKING]: x
ELSE:
  fail
[judgment] [Plan Constraint Violation] CQ-NNN: after the chain"""


def test_the_branch_reader_stops_at_the_end_of_the_last_branch() -> None:
    assert rules_raised(review_branch(_CHAIN, 'brief')) == {'grounding-path-invalid'}
    assert rules_raised(review_branch(_CHAIN, 'design')) == {'unjustified-seam'}


def test_the_design_rule_check_fires_on_a_design_rule_inside_the_brief_branch() -> None:
    chain = _CHAIN.replace('x\nELSE', 'x\n  [judgment] [Unjustified Seam] CQ-NNN: y\nELSE')

    assert rules_raised(review_branch(chain, 'brief')) & DESIGN_REVIEW_RULES == {'unjustified-seam'}


def test_the_branch_reader_finds_nothing_when_a_branch_header_repeats() -> None:
    assert review_branch(_CHAIN + '\n' + _CHAIN, 'brief') == ''


# ---------------------------------------------------------------------------
# Scope 8 - one review mode, two targets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_takes_a_review_target_on_every_review_and_the_phase_file_only_on_the_brief(tui: str) -> None:
    contract = template_contract(_critic(tui))

    assert 'review_target' in contract.declared_inputs('### Scalar Inputs')
    assert 'phase_file_path' not in contract.declared_inputs('### Scalar Inputs')
    assert contract.declared_inputs('### Brief Review Inputs') == {'phase_file_path'}


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('target', _TARGETS)
def test_each_review_target_has_exactly_one_branch_of_checks(tui: str, target: str) -> None:
    body = review_branch(_critic(tui), target)

    assert body, f'no single `review_target == "{target}"` branch'
    assert rules_raised(body), f'the {target} branch raises no finding of its own'


@pytest.mark.parametrize('tui', _TUIS)
def test_an_unknown_review_target_fails_closed_after_the_two_branches(tui: str) -> None:
    lines = _critic(tui).split('\n')
    headers = [index for index, line in enumerate(lines) if re.match(r'^\s*ELIF review_target == "brief":', line)]
    assert len(headers) == 1
    indentation = len(lines[headers[0]]) - len(lines[headers[0]].lstrip())
    following = [
        index
        for index in range(headers[0] + 1, len(lines))
        if lines[index].strip() and len(lines[index]) - len(lines[index].lstrip()) <= indentation
    ]

    assert following and lines[following[0]].strip() == 'ELSE:'
    assert 'result: failed' in template_contract(_critic(tui)).block_at(following[0])


# ---------------------------------------------------------------------------
# B13 (critic half) - the brief review never re-opens design judgment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_review_raises_none_of_the_design_review_rules(tui: str) -> None:
    brief = review_branch(_critic(tui), 'brief')

    assert brief
    assert sorted(rules_raised(brief) & DESIGN_REVIEW_RULES) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_design_review_keeps_every_design_review_rule(tui: str) -> None:
    design = review_branch(_critic(tui), 'design')

    assert sorted(DESIGN_REVIEW_RULES - rules_raised(design)) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_review_raises_its_three_markers_as_mechanical_blockers_and_the_design_review_none(
    tui: str,
) -> None:
    template = _critic(tui)
    brief = template_contract(review_branch(template, 'brief'))

    assert sorted(BRIEF_REVIEW_MARKERS - brief.mechanical_findings()) == []
    assert sorted(BRIEF_REVIEW_MARKERS & rules_raised(review_branch(template, 'design'))) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_no_review_checks_that_a_step_names_its_files_any_more(tui: str) -> None:
    # implementation-step-files-missing (Scope 5) reports a step with no backticked path on both
    # targets, through the relayed implementation findings.
    assert 'step-names-no-files' not in rules_raised(_critic(tui))


# ---------------------------------------------------------------------------
# Scope 0 amendment 4 - the review target is in the stored feedback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_each_review_stores_its_target_tag_at_the_start_of_the_assessment_summary(tui: str) -> None:
    # get_feedback renders no detailed feedback and drops text before the H1, so the summary is
    # where the tag survives; it is the first line under each `## Iteration N - Score: X` heading.
    template = _critic(tui)
    summaries = [match.group('value') for match in _ASSESSMENT_SUMMARY.finditer(template)]

    assert summaries and all(value.startswith('[REVIEW_TAG] — ') for value in summaries)
    for target, tag in _TAGS.items():
        assigned = re.findall(r'^\s*REVIEW_TAG\s*=\s*"(?P<tag>[^"]*)"\s*$', review_branch(template, target), re.M)
        assert assigned == [tag], f'the {target} branch does not set REVIEW_TAG to the tag the finalizer reads'


# ---------------------------------------------------------------------------
# Scope 8 check 2 - the reviewed sections are unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_review_compares_the_sections_the_finalizer_reproduces_with_the_approved_file(tui: str) -> None:
    brief = review_branch(_critic(tui), 'brief')
    finalizer = generate_phase_finalizer_template(create_phase_finalizer_agent_tools(_adapter(tui)))

    assert re.search(r'\bRead\(phase_file_path\)', brief)
    assert REVIEWED_PHASE_SECTIONS in _flat(brief)
    assert REVIEWED_PHASE_SECTIONS in _flat(finalizer)


@pytest.mark.parametrize('tui', _TUIS)
def test_an_unreadable_approved_file_skips_the_comparison_and_never_reports_it_passed(tui: str) -> None:
    brief = review_branch(_critic(tui), 'brief')
    contract = template_contract(brief)
    lines = brief.split('\n')
    unreadable = [
        index
        for index, line in enumerate(lines)
        if _CONDITION.match(line) and 'phase_file_path' in line and re.search(r'\bfail', line, re.IGNORECASE)
    ]

    assert len(unreadable) == 1, 'no single branch for an approved file that cannot be read'
    block = contract.block_at(unreadable[0])
    assert re.search(r'\bskip', block, re.IGNORECASE)
    assert not re.search(r'-\s*BLOCKING\]', block)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_changed_section_is_quoted_on_one_line_in_the_form_the_finalizer_restores(tui: str) -> None:
    # get_feedback flattens a multi-line blocker and splits its nested bullets into blockers of
    # their own, so the quote stays on its line and both agents name the one line-break mark.
    brief = review_branch(_critic(tui), 'brief')
    finalizer = generate_phase_finalizer_template(create_phase_finalizer_agent_tools(_adapter(tui)))
    scope = _flat(finalizer[finalizer.index('STEP 2:') : finalizer.index('STEP 3:')])
    changed = [line for line in brief.split('\n') if '[Reviewed Section Changed - BLOCKING]' in line]
    mark = f'` {QUOTED_LINE_BREAK} `'

    assert changed and all(mark in line for line in changed)
    assert 'Reviewed Section Changed' in scope and mark in scope


# ---------------------------------------------------------------------------
# Orchestrator half: Step 10.7 and the sign-off additions (Scope 9)
# ---------------------------------------------------------------------------

_KEY_MODE_VALIDATION = re.compile(r'mcp__respec-ai__validate_document\((?=[^)]*\bkey=)(?![^)]*\bcontent=)')
_ASSIGNMENT = re.compile(r'^\s*(?P<name>[A-Z][A-Z0-9_]*)\s*=(?!=)\s*(?P<value>.*)$')
_REPAIR_INCREMENT = re.compile(r'\bREPAIR_ROUNDS\s*(?:\+=\s*1|=\s*REPAIR_ROUNDS\s*\+\s*1)\b')
_REVIEW_ROUND_INCREMENT = re.compile(r'\bREVIEW_ROUND\s*(?:\+=\s*1|=\s*REVIEW_ROUND\s*\+\s*1)\b')
_BUDGET_LEFT = re.compile(r'\bREPAIR_ROUNDS\s*(?:<\s*2|<=\s*1)\b')
_EXIT = re.compile(r'\bEXIT\b')
_USER_DECISION = re.compile(r'source=user(?=\s)')
_PHASE_FILE_WRITE = re.compile(r'\bwrite\b.*\bPHASE_FILE_PATH\b', re.IGNORECASE)
_NAMES_STEP_7 = re.compile(r'\bStep 7\b')
_NAMES_STEP_9 = re.compile(r'\bStep 9\b(?!\.\d)')
_NAMES_STEP_10 = re.compile(r'\bStep 10\b(?!\.\d)')
_ROUTE_INTO_SIGN_OFF = re.compile(r'\b(?:go|return|proceed|continue)\s+(?:on\s+)?to\s+Step 11\b(?!\.\d)', re.I)
_FINDING_FORMAT = re.compile(r'<check> <subject>(?: \[<part>\])? — <detail>')
_UNRESOLVED_RESET = re.compile(r'^\s*UNRESOLVED_CHECKS\s*=\s*\[\]\s*$')
_SD_WRITER = re.compile(r'"(?P<entry>- SD-NNN \|[^"]*)"')
_SETTLES_OD_OR_CQ = re.compile(r'^\[(?:OD|CQ)\b')


@cache
def _command_tools(tui: str) -> PhaseCommandTools:
    platform = PlatformType.MARKDOWN
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
def _command(tui: str) -> str:
    return generate_phase_command_template(_command_tools(tui))


def _within(step: str | None, number: str) -> bool:
    return step is not None and (step == number or step.startswith(f'{number}.'))


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip())


def _block_range(lines: list[str], index: int) -> range:
    end = index + 1
    for follow in range(index + 1, len(lines)):
        if lines[follow].strip() and _indentation(lines[follow]) <= _indentation(lines[index]):
            break
        end = follow + 1
    return range(index, end)


def _innermost_condition(lines: list[str], index: int) -> int:
    indentation = _indentation(lines[index])
    for above in range(index - 1, -1, -1):
        if lines[above].strip() and _indentation(lines[above]) < indentation and _CONDITION.match(lines[above]):
            return above
    raise AssertionError(f'no condition encloses: {lines[index].strip()}')


def _names(variable: str, text: str) -> bool:
    return bool(re.search(rf'\b{re.escape(variable)}\b', text))


def _owners_named(line: str) -> set[str]:
    return {owner.value for owner in FindingOwner if re.search(rf'["\'`]{owner.value}["\'`]', line)}


class _Command:
    def __init__(self, tui: str) -> None:
        self.tools = _command_tools(tui)
        self.template = _command(tui)
        self.contract = template_contract(self.template)
        self.lines = self.template.split('\n')
        self.steps = self.contract.line_steps()

    def rows(self, number: str) -> list[int]:
        return [index for index, step in enumerate(self.steps) if _within(step, number)]

    def find(self, number: str, needle: re.Pattern[str]) -> list[int]:
        return [index for index in self.rows(number) if needle.search(self.lines[index])]

    def sites(self, block: str, number: str) -> list[int]:
        rows = set(self.rows(number))
        return [index for index in self.contract.block_sites(block) if index in rows]

    def finalizer_sites(self, number: str) -> list[int]:
        return self.sites(self.tools.invoke_finalizer, number)

    def critic_sites(self, number: str) -> list[int]:
        reviews = (self.tools.invoke_critic_review, self.tools.invoke_critic_brief_review)
        return sorted(index for review in reviews for index in self.sites(review, number))

    def architect_sites(self, number: str) -> list[int]:
        fields = (
            self.tools.invoke_architect_explore,
            self.tools.invoke_architect_draft,
            self.tools.invoke_architect_revise,
            self.tools.resume_architect,
        )
        return sorted(index for field in fields for index in self.sites(field, number))


def routes_into_sign_off(template: str) -> list[str | None]:
    steps = template_contract(template).line_steps()
    return [
        step
        for line, step in zip(template.split('\n'), steps, strict=True)
        if _ROUTE_INTO_SIGN_OFF.search(line) and not _within(step, '11')
    ]


def research_reached(text: str, dispatch: str) -> list[str]:
    found = [line.strip() for line in text.split('\n') if _NAMES_STEP_7.search(line)]
    return found + (['bp-pipeline dispatch'] if template_contract(text).block_sites(dispatch) else [])


def _sd_segments(entry: str) -> list[tuple[str, str]]:
    # README "Segment rules": an SD line is split on ` | `; a segment holding `=` opens its key.
    fields: list[tuple[str, str]] = []
    for segment in entry.split(' | ')[1:]:
        key, separator, value = segment.partition('=')
        if separator:
            fields.append((key.strip(), value))
    return fields


def _settles_od_or_cq(entry: str) -> bool:
    return bool(_SETTLES_OD_OR_CQ.match(dict(_sd_segments(entry)).get('supersedes', '')))


def sd_writers_missing_affects(text: str) -> list[str]:
    faulty: list[str] = []
    for match in _SD_WRITER.finditer(text):
        entry = match.group('entry')
        if not _settles_od_or_cq(entry):
            continue
        fields = _sd_segments(entry)
        keys = [key for key, _ in fields]
        ordered = {'rejected', 'affects', 'binding'} <= set(keys) and (
            keys.index('rejected') < keys.index('affects') < keys.index('binding')
        )
        if not ordered or 'Affects' not in dict(fields)['affects'] or not set(keys) <= SD_KEYS:
            faulty.append(entry)
    return faulty


# ---------------------------------------------------------------------------
# Checker self-tests
# ---------------------------------------------------------------------------


def test_the_route_check_reports_an_approval_that_goes_straight_to_sign_off() -> None:
    template = (
        '#### Step 10.6: Act\n```text\nELSE:\n  Go to Step 11.\n```\n'
        '#### Step 10.7: Finalize\nGo to Step 11.\n'
        '### Step 11: Sign-off\nGo to Step 11.2. The sign-off (Step 11) and Steps 6.2, 10.2 and 11.1.\n'
    )

    assert routes_into_sign_off(template) == ['10.6', '10.7']


def test_the_research_check_fires_on_a_route_to_step_7_and_on_a_dispatch() -> None:
    dispatch = 'Invoke: bp-pipeline\nInput:\n  - MODE: codegen'

    assert research_reached('IF x:\n  Go to Step 7.', dispatch) == ['Go to Step 7.']
    assert research_reached(f'IF x:\n{dispatch}', dispatch) == ['bp-pipeline dispatch']
    assert research_reached('Go to Step 11.7. Go to Step 12.', dispatch) == []


def test_the_affects_check_fires_on_a_missing_or_misplaced_affects_and_ignores_accepted_checks() -> None:
    missing = 'Record "- SD-NNN | source=user | supersedes=[OD ID] | decision=[a] | rationale=[b] | rejected=[c] | binding=yes"'
    misplaced = (
        'Record "- SD-NNN | source=user | supersedes=[OD or CQ ID] | decision=[a] | affects=[its Affects line]'
        ' | rationale=[b] | rejected=[c] | binding=yes"'
    )
    accepted = (
        'Record "- SD-NNN | source=user | supersedes=unresolved-checks | decision=accept as-is: [f] | binding=yes"'
    )
    written = missing.replace(' | binding', " | affects=[the entry's Affects line, verbatim] | binding")

    assert len(sd_writers_missing_affects('\n'.join([missing, misplaced, accepted]))) == 2
    assert sd_writers_missing_affects(written) == []


# ---------------------------------------------------------------------------
# B12 - the brief is finalized and reviewed before sign-off, with no touchpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_is_finalized_after_design_approval_without_a_touchpoint_or_a_prompt(tui: str) -> None:
    contract = template_contract(_command(tui))

    assert '10.7' in contract.step_numbers(), 'no Step 10.7 finalizes the brief'
    body = contract.step_body('10.7')
    assert contract.wait_prompt_count(body) == 0
    assert _adapter(tui).selection_prompt_instruction not in body
    assert 'TOUCHPOINT' not in body and '10.7' not in contract.touchpoint_steps()


@pytest.mark.parametrize('tui', _TUIS)
def test_step_10_7_invokes_the_finalizer_then_the_brief_review_and_never_the_architect(tui: str) -> None:
    command = _Command(tui)
    finalizer = command.finalizer_sites('10.7')
    reviews = command.sites(command.tools.invoke_critic_brief_review, '10.7')

    gates = command.find('10.7', _KEY_MODE_VALIDATION)

    assert finalizer, 'Step 10.7 never invokes the finalizer'
    assert reviews, 'Step 10.7 never reviews the brief'
    assert gates and finalizer[0] < gates[0] < reviews[0], 'the brief is not checked between finalizing and review'
    assert command.architect_sites('10.7') == []
    assert command.sites(command.tools.invoke_critic_review, '10.7') == []


@pytest.mark.parametrize('tui', _TUIS)
def test_every_brief_repair_spends_the_shared_budget_on_the_finalizer(tui: str) -> None:
    command = _Command(tui)
    increments = command.find('10.7', _REPAIR_INCREMENT)
    finalizer = command.finalizer_sites('10.7')

    assert len(increments) >= 3, 'the gate, refine and user_input do not each repair'
    for increment in increments:
        guard = _innermost_condition(command.lines, increment)
        block = _block_range(command.lines, guard)
        assert _BUDGET_LEFT.search(command.lines[guard]), 'a repair runs without budget left'
        assert [index for index in finalizer if increment < index and index in block], 'a repair is not the finalizer'


@pytest.mark.parametrize('tui', _TUIS)
def test_step_10_7_starts_a_fresh_budget_and_puts_the_approved_design_on_disk_before_the_finalizer(tui: str) -> None:
    # The critic's reviewed-sections check compares the finalized document with this disk copy, so
    # a re-entry at the top would rewrite it with the finalized brief and reset the budget.
    command = _Command(tui)
    rows = command.rows('10.7')
    finalizer = command.finalizer_sites('10.7')
    resets = [rf'^\s*{name}\s*=\s*(?:0|\[\])\s*$' for name in ('REPAIR_ROUNDS', 'STRUCTURAL_LEFTOVERS')]
    resets.append(_UNRESOLVED_RESET.pattern)

    assert finalizer
    for reset in resets:
        found = command.find('10.7', re.compile(reset))
        assert found and all(index < finalizer[0] and not command.contract.guards_at(index) for index in found)
    reads = command.find('10.7', re.compile(r'get_document\('))
    writes = command.find('10.7', _PHASE_FILE_WRITE)
    assert reads and writes and reads[0] < writes[0] < finalizer[0]
    assert [index for index in rows[1:] if re.search(r'\bStep 10\.7\b', command.lines[index])] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_step_10_7_clears_the_brief_questions_only_on_a_full_pass_and_keeps_the_first_summary_otherwise(
    tui: str,
) -> None:
    command = _Command(tui)
    finalizer = command.finalizer_sites('10.7')[0]
    clears = command.find('10.7', re.compile(r'^\s*BRIEF_QUESTIONS\s*=\s*\[\]\s*$'))
    summaries = command.find('10.7', re.compile(r'^\s*BRIEF_SUMMARY\s*='))

    assert len(clears) == 1 and clears[0] < finalizer
    assert 'FULL_PASS' in command.lines[_innermost_condition(command.lines, clears[0])]
    assert len(summaries) == 1 and summaries[0] > finalizer
    guard = command.lines[_innermost_condition(command.lines, summaries[0])]
    assert 'FULL_PASS' in guard and 'BRIEF_SUMMARY is none' in guard


@pytest.mark.parametrize('tui', _TUIS)
def test_the_finalized_brief_is_on_disk_before_the_sign_off_prompt_and_after_every_sign_off_pass(tui: str) -> None:
    command = _Command(tui)
    waits = [index for index in command.rows('11.1') if 'WAIT for' in command.lines[index]]
    reads = command.find('11.1', re.compile(r'get_document\('))
    writes = command.find('11.1', _PHASE_FILE_WRITE)
    mirrors = command.find('11.1', re.compile(r'^\s*LAST_WRITTEN_PHASE_MARKDOWN\s*=\s*PHASE_MARKDOWN\s*$'))

    assert reads and writes and waits and reads[0] < writes[0] < waits[0]
    assert mirrors and writes[0] < mirrors[0] < waits[0]
    for site in command.finalizer_sites('11.1'):
        after = [index for index in writes if index > site]
        assert after, 'a finalizer pass at sign-off is not followed by a disk write'
        assert not [index for index in waits if site < index < after[0]]
        assert any(site < index for index in mirrors)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_missing_plan_at_step_10_7_reaches_the_one_time_rebuild_before_the_finalizer(tui: str) -> None:
    command = _Command(tui)
    finalizer = command.finalizer_sites('10.7')[0]
    checks = [
        index
        for index in command.rows('10.7')
        if _CONDITION.match(command.lines[index]) and 'IMPLEMENTATION_PLAN_PATH' in command.lines[index]
    ]

    assert len(checks) == 1 and checks[0] < finalizer
    text = '\n'.join(command.lines[index] for index in _block_range(command.lines, checks[0]))
    assert re.search(r'Go to Step 11\.3\b', text)
    assert command.architect_sites('10.7') == []


@pytest.mark.parametrize('tui', _TUIS)
def test_every_route_from_sign_off_back_into_step_9_starts_a_fresh_repair_budget(tui: str) -> None:
    command = _Command(tui)
    routes = [index for index in command.rows('11') if _NAMES_STEP_9.search(command.lines[index])]
    resets = command.find('11', re.compile(r'^\s*REPAIR_ROUNDS\s*=\s*0\s*$'))

    assert routes
    for route in routes:
        block = _innermost_condition(command.lines, route)
        assert any(block < reset < route for reset in resets), command.lines[route].strip()


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['10.7', '11'])
def test_a_failed_brief_gate_validation_ends_the_run_before_any_agent_is_engaged(step: str, tui: str) -> None:
    # The same fail-closed branch phase 3 gives Step 9's gate
    # (test_phase_structural_gate.test_a_failed_gate_validation_ends_the_run_before_any_agent_is_engaged).
    command = _Command(tui)
    validations = command.find(step, _KEY_MODE_VALIDATION)
    assert len(validations) == 1, f'Step {step} does not run the key-mode gate exactly once: {validations}'
    assigned = _ASSIGNMENT.match(command.lines[validations[0]])
    assert assigned, 'the key-mode validation result is never named'
    readers = [
        index
        for index in command.rows(step)
        if index > validations[0] and _names(assigned.group(1), command.lines[index])
    ]
    failure_guards = [
        index
        for index in readers
        if _CONDITION.match(command.lines[index]) and re.search(r'\bfail', command.lines[index], re.IGNORECASE)
    ]

    assert len(failure_guards) == 1, 'a failed key-mode validation has no fail-closed branch'
    assert failure_guards[0] == readers[0], 'the result is read before a failed call is handled'
    block = command.contract.block_at(failure_guards[0])
    assert 'FAIL-CLOSED' in block
    assert block.rstrip().endswith('EXIT: Workflow terminated')
    engaged = command.finalizer_sites(step) + command.critic_sites(step) + command.architect_sites(step)
    assert not [index for index in engaged if index in _block_range(command.lines, failure_guards[0])]


@pytest.mark.parametrize('tui', _TUIS)
def test_design_approval_goes_to_the_brief_and_no_route_into_sign_off_skips_it(tui: str) -> None:
    command = _Command(tui)
    approvals = command.find('10.6', re.compile(r'\bStep 10\.7\b'))

    assert approvals, "Step 10.6's approval does not go to Step 10.7"
    guard = command.contract.guards_at(approvals[0])
    assert guard and (guard[0].startswith('ELSE') or 'Approve the design' in guard[0])
    assert set(routes_into_sign_off(command.template)) == {'10.7'}


# ---------------------------------------------------------------------------
# B18 (routing half, Step 10.7) and the brief review's decisions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_gate_repairs_architect_and_finalizer_findings_through_the_finalizer(tui: str) -> None:
    # An architect finding here is drift in a section the finalizer reproduces, so the finalizer
    # restores it; orchestrator findings sit on lines no repair round may change.
    command = _Command(tui)
    splits = {
        match.group('name'): _owners_named(command.lines[index])
        for index in command.rows('10.7')
        if (match := _ASSIGNMENT.match(command.lines[index])) and 'structural_findings' in match.group('value')
    }
    assert sorted(sorted(owners) for owners in splits.values()) == [['architect', 'finalizer'], ['orchestrator']]
    repairable = next(name for name, owners in splits.items() if 'finalizer' in owners)
    left = next(name for name, owners in splits.items() if owners == {'orchestrator'})
    guards = [
        index
        for index in command.rows('10.7')
        if _CONDITION.match(command.lines[index])
        and _names(repairable, command.lines[index])
        and _BUDGET_LEFT.search(command.lines[index])
    ]

    assert len(guards) == 1, f'Step 10.7 has no single repair guard on {repairable} and the budget'
    assert not _names(left, command.lines[guards[0]])
    assert [index for index in command.finalizer_sites('10.7') if index in _block_range(command.lines, guards[0])]


@pytest.mark.parametrize('tui', _TUIS)
def test_brief_leftovers_are_written_as_the_finding_key_step_9_writes(tui: str) -> None:
    # Step 9's form is the one test_phase_structural_gate feeds to drop_accepted_findings, so an
    # accept-as-is answer at sign-off suppresses these too.
    command = _Command(tui)

    def leftovers(step: str) -> list[int]:
        return [
            index
            for index in command.rows(step)
            if (match := _ASSIGNMENT.match(command.lines[index]))
            and match.group('name') == 'STRUCTURAL_LEFTOVERS'
            and _FINDING_FORMAT.search(command.contract.block_at(index))
        ]

    brief, design = leftovers('10.7'), leftovers('9')
    assert len(brief) == 1 and len(design) == 1
    assert command.contract.guards_at(brief[0]) == (), 'leftovers are collected on some paths only'
    forms = set(_FINDING_FORMAT.findall(command.contract.block_at(brief[0])))
    assert forms == set(_FINDING_FORMAT.findall(command.contract.block_at(design[0])))
    assert {'[<part>]' in form for form in forms} == {True, False}


@pytest.mark.parametrize('tui', _TUIS)
def test_the_brief_review_is_counted_persisted_and_decided_like_the_design_review(tui: str) -> None:
    command = _Command(tui)
    reviews = command.sites(command.tools.invoke_critic_brief_review, '10.7')
    assert reviews, 'Step 10.7 never reviews the brief'
    increments = command.find('10.7', _REVIEW_ROUND_INCREMENT)
    stored = [index for index in command.find('10.7', re.compile('## Iteration ')) if index > reviews[0]]
    decided = command.find('10.7', re.compile(r'decide_loop_next_action\('))

    assert increments and increments[0] < reviews[0]
    assert stored and decided and reviews[0] < stored[0] < decided[0]
    persistence = [
        index
        for index in command.find('10.7', re.compile(r'Do NOT call decide_loop_next_action'))
        if reviews[0] < index < decided[0]
    ]
    assert len(persistence) == 3, "phase 2's three fail-closed persistence checks are not all kept"


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('status', ['refine', 'user_input'])
def test_open_brief_findings_get_the_remaining_repairs_then_reach_sign_off_as_unresolved_checks(
    status: str, tui: str
) -> None:
    command = _Command(tui)
    assert '10.7' in command.contract.step_numbers()
    blocks = [
        block
        for block in template_contract(command.contract.step_body('10.7')).decision_blocks(status)
        if 'REVIEW_DECISION' in block.split('\n', 1)[0]
    ]

    assert len(blocks) == 1, f'Step 10.7 has no {status} branch of its own'
    block = template_contract(blocks[0])
    assert _BUDGET_LEFT.search(blocks[0]) and _REPAIR_INCREMENT.search(blocks[0])
    assert block.block_sites(command.tools.invoke_finalizer)
    assert re.search(r'UNRESOLVED_CHECKS\s*=(?!=).*\bSTRUCTURAL_LEFTOVERS\b', blocks[0])
    assert _ROUTE_INTO_SIGN_OFF.search(blocks[0])


@pytest.mark.parametrize('tui', _TUIS)
def test_a_clean_brief_review_goes_to_sign_off_and_an_unknown_decision_ends_the_run(tui: str) -> None:
    command = _Command(tui)
    assert '10.7' in command.contract.step_numbers()
    body = command.contract.step_body('10.7')
    completed = [block for block in template_contract(body).decision_blocks('completed') if 'REVIEW_DECISION' in block]
    lines = body.split('\n')
    headers = [index for index, line in enumerate(lines) if re.match(r'^\s*(?:IF|ELIF)\s+\w*REVIEW_DECISION\b', line)]

    assert len(completed) == 1 and _ROUTE_INTO_SIGN_OFF.search(completed[0])
    assert re.search(r'UNRESOLVED_CHECKS\s*=(?!=).*\bSTRUCTURAL_LEFTOVERS\b', completed[0])
    assert headers
    closing = [
        index
        for index in range(headers[-1] + 1, len(lines))
        if lines[index].strip() and _indentation(lines[index]) <= _indentation(lines[headers[-1]])
    ]
    assert closing and lines[closing[0]].strip() == 'ELSE:'
    assert _EXIT.search(template_contract(body).block_at(closing[0]))


# ---------------------------------------------------------------------------
# Sign-off additions (Scope 9, Step 11)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_sign_off_asks_the_brief_questions_apart_and_never_sends_an_answer_to_the_architect(tui: str) -> None:
    command = _Command(tui)
    loops = command.find('11', re.compile(r'^\s*FOR each entry in BRIEF_QUESTIONS\b'))
    remaining = [index for index in command.rows('11') if re.match(r'^\s*REMAINING\s*=', command.lines[index])]

    assert len(loops) == 1, 'sign-off does not ask the brief questions in a loop of their own'
    block = _block_range(command.lines, loops[0])
    text = '\n'.join(command.lines[index] for index in block)
    assert 'WAIT for' in text and 'DESIGN_CHANGE_SD_IDS' not in text
    assert not [index for index in command.architect_sites('11') if index in block]
    assert remaining and 'BRIEF_QUESTIONS' not in command.contract.block_at(remaining[0])
    assert remaining[0] < loops[0]


@pytest.mark.parametrize('tui', _TUIS)
def test_sign_off_applies_the_answers_with_one_finalizer_pass_and_one_gate_and_no_second_review(tui: str) -> None:
    command = _Command(tui)
    finalizer = command.finalizer_sites('11')
    gates = command.find('11', _KEY_MODE_VALIDATION)

    assert len(finalizer) == 1 and len(gates) == 1 and finalizer[0] < gates[0]
    guards = command.contract.guards_at(finalizer[0])
    assert guards, 'the finalizer runs again even when no answer was recorded'
    assert command.contract.guards_at(gates[0]) == guards
    assert command.critic_sites('11') == []
    block = _block_range(command.lines, _innermost_condition(command.lines, finalizer[0]))
    gate_name = _ASSIGNMENT.match(command.lines[gates[0]])
    assert gate_name
    found = [
        index
        for index in block
        if re.match(r'^\s*UNRESOLVED_CHECKS\s*=(?!=)', command.lines[index])
        and _names(gate_name.group(1), command.contract.block_at(index))
    ]
    waits = [index for index in block if index > gates[0] and 'WAIT for' in command.lines[index]]
    assert found and waits
    assert all(any('UNRESOLVED_CHECKS' in guard for guard in command.contract.guards_at(index)) for index in waits)


@pytest.mark.parametrize('tui', _TUIS)
def test_every_unresolved_checks_decision_at_sign_off_is_recorded_or_returns_to_design_review(tui: str) -> None:
    command = _Command(tui)
    guards = [
        index
        for index in command.rows('11')
        if re.match(r'^\s*IF UNRESOLVED_CHECKS is not empty:', command.lines[index])
    ]

    assert len(guards) == 2, "sign-off does not offer the brief's checks and the once-more gate's checks"
    for guard in guards:
        block = _block_range(command.lines, guard)
        text = '\n'.join(command.lines[index] for index in block)
        accepts = [index for index in block if 'supersedes=unresolved-checks' in command.lines[index]]
        returns = [index for index in block if _NAMES_STEP_10.search(command.lines[index])]
        resets = [index for index in block if _UNRESOLVED_RESET.match(command.lines[index])]
        assert text.count('WAIT for') == 1
        assert accepts and all(_USER_DECISION.search(command.lines[index]) for index in accepts)
        assert returns and resets
        assert all(any(reset < route for reset in resets) for route in returns), 'design review asks them again'
        assert any(reset > accepts[-1] for reset in resets)


@pytest.mark.parametrize('tui', _TUIS)
def test_a_plan_missing_at_sign_off_is_rebuilt_once_through_the_design_review_then_fails_closed(tui: str) -> None:
    command = _Command(tui)
    checks = [
        index
        for index in command.rows('11')
        if _CONDITION.match(command.lines[index])
        and 'IMPLEMENTATION_PLAN_PATH' in command.lines[index]
        and not command.contract.guards_at(index)
    ]
    assert len(checks) == 1
    block = _block_range(command.lines, checks[0])
    revisions = [index for index in command.sites(command.tools.invoke_architect_revise, '11') if index in block]
    routes = [index for index in block if _NAMES_STEP_9.search(command.lines[index])]

    assert revisions and routes and revisions[-1] < routes[-1], 'the rebuilt plan does not go back through Step 9'
    exits = [index for index in block if index < revisions[0] and _EXIT.search(command.lines[index])]
    assert len(exits) == 1, 'a second miss does not fail closed before the architect is engaged again'
    flag_guard = command.lines[_innermost_condition(command.lines, exits[0])]
    flags = set(re.findall(r'\b[A-Z][A-Z0-9_]{3,}\b', flag_guard)) - {'IF', 'IMPLEMENTATION_PLAN_PATH'}
    assert len(flags) == 1, f'the second miss is not keyed on one flag: {flag_guard.strip()}'
    flag = flags.pop()
    assert [index for index in block if re.match(rf'^\s*{flag}\s*=\s*true\b', command.lines[index])]
    assert command.find('3', re.compile(rf'^\s*{flag}\s*=\s*false\b'))


# ---------------------------------------------------------------------------
# B13 (orchestrator half) - nothing after design approval researches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['10.7', '11', '12'])
def test_nothing_after_design_approval_researches_or_routes_to_research(step: str, tui: str) -> None:
    contract = template_contract(_command(tui))

    assert step in contract.step_numbers()
    text = contract.step_body(step) if step == '10.7' else contract.step_section(step)
    assert research_reached(text, _command_tools(tui).invoke_bp_pipeline) == []


# ---------------------------------------------------------------------------
# B14 - every settled decision for an answered OD or CQ records what it binds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('step', ['6', '10', '11'])
def test_every_decision_that_settles_an_od_or_cq_records_what_it_affects(step: str, tui: str) -> None:
    # `affects=` is a contract string (testing.md, "Where a string assertion is still legitimate"):
    # the finalizer applies an SD to what it names, and phase 3's segment parser reads it as a known
    # key (SD_KEYS), so it must follow `rejected=` and copy the settled entry's Affects line.
    section = template_contract(_command(tui)).step_section(step)
    writers = [match.group('entry') for match in _SD_WRITER.finditer(section)]

    assert [entry for entry in writers if _settles_od_or_cq(entry)], f'Step {step} settles no OD or CQ'
    assert sd_writers_missing_affects(section) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_no_decision_that_settles_no_od_or_cq_records_an_affects_line(tui: str) -> None:
    writers = [match.group('entry') for match in _SD_WRITER.finditer(_command(tui))]

    assert [entry for entry in writers if not _settles_od_or_cq(entry)]
    assert [entry for entry in writers if not _settles_od_or_cq(entry) and 'affects' in dict(_sd_segments(entry))] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_a_hand_edit_made_at_sign_off_is_reviewed_before_any_sign_off_choice_acts(tui: str) -> None:
    # The finalized brief is on disk at sign-off, so the user can edit it there, and Step 11.5's
    # final write would overwrite that edit. Like Step 10.4, the disk is compared before any choice
    # acts. "I edited phase.md myself" is the Step 10.4 label Step 10.5 routes to Step 9.
    command = _Command(tui)
    choice = command.find('11.2', re.compile(r'^\s*SIGN_OFF_CHOICE\s*='))
    reads = command.find('11.2', re.compile(r'^\s*DISK_MARKDOWN\s*=\s*Read PHASE_FILE_PATH'))
    guards = [
        index
        for index in command.rows('11.2')
        if _CONDITION.match(command.lines[index])
        and 'DISK_MARKDOWN' in command.lines[index]
        and 'LAST_WRITTEN_PHASE_MARKDOWN' in command.lines[index]
    ]
    acts = [
        index
        for index in command.rows('11.2')
        if _CONDITION.match(command.lines[index]) and 'SIGN_OFF_CHOICE' in command.lines[index]
    ]

    assert choice and reads and acts
    assert len(guards) == 1, 'sign-off never compares the disk with what this run last wrote'
    assert choice[0] < reads[0] < guards[0] < min(acts)
    block = '\n'.join(command.lines[index] for index in _block_range(command.lines, guards[0]))
    assert re.search(r'Go to Step 10\.5\b', block)
    assert re.search(r'^\s*REVIEW_CHOICE\s*=\s*"I edited phase\.md myself"\s*$', block, re.MULTILINE)
    assert re.search(r'^\s*REPAIR_ROUNDS\s*=\s*0\s*$', block, re.MULTILINE)
