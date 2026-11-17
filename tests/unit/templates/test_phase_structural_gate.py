"""The structural gate and one owner per rule (docs/phase-cooperative/phase-3-structural-checks.md).

B15 pins the gate at the top of /respec-phase Step 9, on every TUI. B16 pins the agents: the
critic stops carrying the rules validate_document now owns, verifies only the paths the server
returns, and relays the implementation.md findings; both agents call validate_document and
declare it. Work item 8's architect self-check is pinned here too.

These tests anchor on structure: which call precedes which, which condition guards a block,
and which block contains a prompt. The strings they match are contracts something parses:
- the DocumentValidationResponse field names (`structural_findings`, `implementation_findings`,
  `paths_to_verify`) and the FindingOwner and CitedPathKind values are what the server returns
  and the templates branch on
- the finding-key formats are what drop_accepted_findings matches once the user accepts a
  finding, so each format is filled from a real finding and fed to it
- UNSTORABLE_DOCUMENT and CONTENT_LOSS_WARNING are server text, imported as the templates
  import them
- the `[<Marker> - BLOCKING]` names are what template_contract.blocker_conditions() reads
"""

import re
from functools import cache

import pytest
from template_contract import template_contract

from src.models.document_validation import (
    CONTENT_LOSS_WARNING,
    UNSTORABLE_DOCUMENT,
    CitedPathKind,
    FindingOwner,
    StructuralCheck,
    StructuralFinding,
)
from src.models.phase import Phase
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
from src.utils.phase_structure import drop_accepted_findings


_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')

_VALIDATE_DOCUMENT = 'mcp__respec-ai__validate_document'
_KEY_MODE_VALIDATION = re.compile(r'mcp__respec-ai__validate_document\((?=[^)]*\bkey=)(?![^)]*\bcontent=)')
_REVIEW_ROUND_INCREMENT = re.compile(r'\bREVIEW_ROUND\s*(?:\+=\s*1|=\s*REVIEW_ROUND\s*\+\s*1)\b')
_REPAIR_INCREMENT = re.compile(r'\bREPAIR_ROUNDS\s*(?:\+=\s*1|=\s*REPAIR_ROUNDS\s*\+\s*1)\b')
_BUDGET_LEFT = re.compile(r'\bREPAIR_ROUNDS\s*(?:<\s*2|<=\s*1)\b')
_REPAIR_RESET = re.compile(r'\bREPAIR_ROUNDS\s*=\s*0\b')
_ROUND_COUNTER_INCREMENT = re.compile(r'\b(?P<name>\w+_ROUNDS?)\s*\+=\s*1\b')
_ASSIGNMENT = re.compile(r'^\s*(?P<name>[A-Z][A-Z0-9_]*)\s*=(?!=)\s*(?P<value>.*)$')
_UNRESOLVED_RESET = re.compile(r'^\s*UNRESOLVED_CHECKS\s*=\s*\[\]\s*$')
_CONDITION = re.compile(r'^\s*(?:IF|ELIF)\b')
_NAMES_STEP_9 = re.compile(r'\bStep 9\b(?!\.\d)')
_LABEL = re.compile(r'"label":\s*"(?P<label>[^"]+)"')

# The finding key drop_accepted_findings matches: `<check> <subject>`, plus ` [<part>]` when part
# is set, followed in a recorded finding by ` — <detail>`.
_FINDING_FORMAT = re.compile(r'<check> <subject>(?: \[<part>\])? — <detail>')
_RELAYED_IMPLEMENTATION_FINDING = re.compile(
    r'\[mechanical\] \[Implementation Plan Structure Invalid - BLOCKING\]: <check> <subject>(?: \[<part>\])? — <detail>'
)

# Phase 3 work item 9: these rules moved into validate_document, so the critic raises none of them.
_MOVED_CRITIC_RULES = frozenset(
    {
        'malformed-decision-entry',
        'empty-test-list',
        'test-list-names-file-not-behavior',
        'skeleton-index-module-mismatch',
        'checklist-item-malformed',
        'step-without-verify-command',
    }
)
_KEPT_MECHANICAL_RULES = frozenset(
    {
        'research-path-invalid',
        'best-practices-reference-invalid',
        'implementation-plan-reference-invalid',
        'implementation-plan-missing',
        'implementation-plan-structure-invalid',
        'step-names-no-files',
        'verify-command-not-configured',
        'test-list-entry-not-covered',
        'ux-contract-flow-missing-pass-condition',
        'ux-contract-route-missing-auth',
        'missing-state-ownership-decision',
        'undecided-screen-decomposition',
        'missing-component-provenance-decision',
        'missing-design-source-decision',
    }
)
_EXISTENCE_MARKER_BY_KIND = {
    CitedPathKind.READ: 'Research Path Invalid',
    CitedPathKind.BEST_PRACTICES: 'Best-Practices Reference Invalid',
    CitedPathKind.CONSTRAINT: 'Implementation Plan Reference Invalid',
}
_CRITIC_READ_ONLY_GRANTS = frozenset(
    {
        'mcp__respec-ai__get_document',
        'mcp__respec-ai__get_feedback',
        'mcp__respec-ai__store_critic_feedback',
        _VALIDATE_DOCUMENT,
        'read',
        'glob',
        'grep',
        'bash',
    }
)
_FEEDBACK_NEWNESS = re.compile(r'feedback|NEW_USER_INPUTS|LATEST_BLOCKERS|changed', re.IGNORECASE)


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


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


@cache
def _critic(tui: str) -> str:
    return generate_phase_critic_template(create_phase_critic_agent_tools(_adapter(tui)))


@cache
def _architect(tui: str) -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(_adapter(tui)))


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip())


def _block_range(lines: list[str], index: int) -> range:
    end = index + 1
    for follow in range(index + 1, len(lines)):
        if lines[follow].strip() and _indentation(lines[follow]) <= _indentation(lines[index]):
            break
        end = follow + 1
    return range(index, end)


def _names(variable: str, text: str) -> bool:
    return bool(re.search(rf'\b{re.escape(variable)}\b', text))


def _owner_value(owner: FindingOwner) -> re.Pattern[str]:
    return re.compile(rf'["\'`]{owner.value}["\'`]')


class _Step9:
    def __init__(self, tui: str) -> None:
        self.tools = _command_tools(tui)
        self.adapter = _adapter(tui)
        self.contract = template_contract(_command(tui))
        self.lines = _command(tui).split('\n')
        steps = [step.split('.', 1)[0] if step else None for step in self.contract.line_steps()]
        self.rows = [index for index, step in enumerate(steps) if step == '9']

    def find(self, needle: re.Pattern[str]) -> list[int]:
        return [index for index in self.rows if needle.search(self.lines[index])]

    def critic_sites(self) -> list[int]:
        return [index for index in self.contract.block_sites(self.tools.invoke_critic_review) if index in self.rows]

    def revise_sites(self) -> list[int]:
        return [index for index in self.contract.block_sites(self.tools.invoke_architect_revise) if index in self.rows]

    def resume_sites(self) -> list[int]:
        return [index for index in self.contract.block_sites(self.tools.resume_architect) if index in self.rows]

    def findings_variable(self, owner: FindingOwner) -> str:
        names = {
            match.group('name')
            for index in self.rows
            if (match := _ASSIGNMENT.match(self.lines[index]))
            and 'structural_findings' in match.group('value')
            and _owner_value(owner).search(match.group('value'))
        }
        assert len(names) == 1, f'Step 9 does not split structural_findings by owner {owner.value}: {names}'
        return names.pop()

    def gate_guard(self) -> int:
        architect = self.findings_variable(FindingOwner.ARCHITECT)
        guards = [
            index
            for index in self.rows
            if _CONDITION.match(self.lines[index])
            and _names(architect, self.lines[index])
            and _BUDGET_LEFT.search(self.lines[index])
        ]
        assert len(guards) == 1, f'Step 9 has no single repair guard on {architect} and the budget: {guards}'
        return guards[0]

    def gate_block(self) -> range:
        return _block_range(self.lines, self.gate_guard())

    def leftovers_assignment(self) -> int:
        architect = self.findings_variable(FindingOwner.ARCHITECT)
        orchestrator = self.findings_variable(FindingOwner.ORCHESTRATOR)
        found = [
            index
            for index in self.rows
            if (match := _ASSIGNMENT.match(self.lines[index]))
            and _names(architect, self.contract.block_at(index))
            and _names(orchestrator, self.contract.block_at(index))
            and match.group('name') not in (architect, orchestrator)
        ]
        assert len(found) == 1, f'Step 9 never collects {architect} and {orchestrator} as leftovers: {found}'
        return found[0]

    def leftovers_variable(self) -> str:
        match = _ASSIGNMENT.match(self.lines[self.leftovers_assignment()])
        assert match
        return match.group('name')


def _phase_accepting(quoted: str) -> Phase:
    accept = (
        f'- SD-002 | source=user | supersedes=unresolved-checks | decision=accept as-is: {quoted}'
        ' | rationale=accepted at design review | binding=yes'
    )
    shipped = Phase.parse_markdown(technical_phase_template.replace('[phase-name-in-kebab-case]', 'phase-1-gate'))
    return shipped.model_copy(update={'settled_design_decisions': accept})


def _filled(form: str, finding: StructuralFinding) -> str:
    return (
        form.replace('<check>', finding.check.value)
        .replace('<subject>', finding.subject)
        .replace('<part>', finding.part)
        .replace('<detail>', finding.detail)
    )


_FINDING_WITH_PART = StructuralFinding(
    check=StructuralCheck.DECISION_ENTRY_MALFORMED,
    location='Design Decisions > Open Design Decisions',
    subject='OD-002',
    part='Option B',
    owner=FindingOwner.ARCHITECT,
    detail='Add an Option B line with its trade-off.',
)
_FINDING_WITHOUT_PART = StructuralFinding(
    check=StructuralCheck.DANGLING_REFERENCE,
    location='Design Shape > Collaboration And Wiring',
    subject='OD-009',
    owner=FindingOwner.ARCHITECT,
    detail='Define OD-009 or remove this reference.',
)


def accepted_by_the_server(forms: list[str]) -> dict[str, bool]:
    """Each recorded-finding format, filled from a real finding, quoted in an accept-as-is SD.

    True when drop_accepted_findings drops the finding, so the user is never asked again (B17).
    """
    outcome: dict[str, bool] = {}
    for form in forms:
        finding = _FINDING_WITH_PART if '[<part>]' in form else _FINDING_WITHOUT_PART
        kept, _ = drop_accepted_findings([finding], _phase_accepting(_filled(form, finding)))
        outcome[form] = not kept
    return outcome


def unstorable_menu(section: str, prompt: str) -> tuple[list[str], list[str]]:
    """The option labels a prompt guarded by the unstorable line offers, and those that proceed.

    An option proceeds when the branch handling it leaves the validation loop with BREAK, which
    carries the edited text on to the store.
    """
    contract = template_contract(section)
    lines = section.split('\n')
    offered: list[str] = []
    for index, line in enumerate(lines):
        if prompt not in line or not any(UNSTORABLE_DOCUMENT in guard for guard in contract.guards_at(index)):
            continue
        offered.extend(match.group('label') for match in _LABEL.finditer(contract.block_at(index)))
    proceeding = [
        label
        for label in offered
        for index, line in enumerate(lines)
        if _CONDITION.match(line) and f'"{label}"' in line and re.search(r'\bBREAK\b', contract.block_at(index))
    ]
    return offered, proceeding


# ---------------------------------------------------------------------------
# Checker self-tests
# ---------------------------------------------------------------------------

_PROMPT = 'Use AskUserQuestion tool to present options:'


def _hand_edit_menu(unstorable_labels: list[str]) -> str:
    def options(labels: list[str]) -> str:
        return ',\n'.join(f'        {{"label": "{label}", "description": "x"}}' for label in labels)

    return '\n'.join(
        [
            'WHILE VALIDATION_RESULT.status != "completed":',
            f'  IF VALIDATION_RESULT.message contains "{UNSTORABLE_DOCUMENT}":',
            f'    {_PROMPT}',
            '      Options: [',
            options(unstorable_labels),
            '      ]',
            '    WAIT for the response.',
            '  ELSE:',
            f'    {_PROMPT}',
            '      Options: [',
            options(['Fix', 'Drop', 'Abort']),
            '      ]',
            '    WAIT for the response.',
            '  IF the user chose "Fix":',
            '    CONTINUE loop',
            '  ELIF the user chose "Drop":',
            '    BREAK',
            '  ELSE:',
            '    Go to Step 9.',
        ]
    )


def test_the_unstorable_menu_check_fires_on_an_option_that_proceeds_with_the_edit() -> None:
    section = _hand_edit_menu(['Fix', 'Drop', 'Abort'])

    assert unstorable_menu(section, _PROMPT) == (['Fix', 'Drop', 'Abort'], ['Drop'])


def test_the_unstorable_menu_check_accepts_fix_and_abort_only() -> None:
    section = _hand_edit_menu(['Fix', 'Abort'])

    assert unstorable_menu(section, _PROMPT) == (['Fix', 'Abort'], [])


def test_the_acceptance_check_fires_on_a_format_the_server_does_not_match() -> None:
    assert accepted_by_the_server(['<check> <subject> [<part>] — <detail>', '<check> <subject> — <detail>']) == {
        '<check> <subject> [<part>] — <detail>': True,
        '<check> <subject> — <detail>': True,
    }
    assert accepted_by_the_server(['<check> <subject> — <detail> [<part>]', '<subject> <check> — <detail>']) == {
        '<check> <subject> — <detail> [<part>]': False,
        '<subject> <check> — <detail>': False,
    }


# ---------------------------------------------------------------------------
# B15 - the gate at the top of Step 9
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_stored_phase_is_validated_in_key_mode_at_the_top_of_step_9_before_the_critic(tui: str) -> None:
    step = _Step9(tui)
    validations = step.find(_KEY_MODE_VALIDATION)
    increments = step.find(_REVIEW_ROUND_INCREMENT)
    critics = step.critic_sites()

    assert validations, 'Step 9 never validates the stored phase in key mode'
    assert step.contract.guards_at(validations[0]) == (), 'the validation is conditional, so some entry skips it'
    assert increments and critics
    assert validations[0] < increments[0] < critics[0]
    # The README phase 3 probe greps the command for this field name.
    assert 'structural_findings' in step.contract.step_section('9')


@pytest.mark.parametrize('tui', _TUIS)
def test_a_failed_gate_validation_ends_the_run_before_any_agent_is_engaged(tui: str) -> None:
    # Key mode raises (phase not found, a store error, a server without key mode); every other
    # MCP call in Step 9 fails closed, so the gate must not leave the model to improvise.
    step = _Step9(tui)
    validation = step.find(_KEY_MODE_VALIDATION)[0]
    assigned = _ASSIGNMENT.match(step.lines[validation])
    assert assigned, 'the key-mode validation result is never named'
    failure_guards = [
        index
        for index in step.rows
        if validation < index < step.gate_guard()
        and _CONDITION.match(step.lines[index])
        and _names(assigned.group('name'), step.lines[index])
        and re.search(r'\bfail', step.lines[index], re.IGNORECASE)
    ]

    assert len(failure_guards) == 1, 'a failed key-mode validation has no fail-closed branch before the gate'
    block = step.contract.block_at(failure_guards[0])
    assert 'FAIL-CLOSED' in block
    assert block.rstrip().endswith('EXIT: Workflow terminated')
    engaged = step.critic_sites() + step.revise_sites() + step.resume_sites()
    assert not [index for index in engaged if index in _block_range(step.lines, failure_guards[0])]


@pytest.mark.parametrize('tui', _TUIS)
def test_architect_owned_findings_with_budget_left_go_back_to_the_architect_with_no_prompt(tui: str) -> None:
    step = _Step9(tui)
    block = step.gate_block()
    text = '\n'.join(step.lines[index] for index in block)
    revisions = [index for index in step.revise_sites() if index in block]

    assert step.find(_KEY_MODE_VALIDATION)[0] < block.start < step.critic_sites()[0]
    assert revisions, 'the repair branch does not re-engage the architect in revise'
    mode_set = [index for index in block if re.search(r'\bARCHITECT_MODE\s*=\s*"revise"', step.lines[index])]
    assert mode_set and mode_set[0] < revisions[0], 'ARCHITECT_MODE is not set to revise before the repair'
    assert 'WAIT for' not in text
    assert step.adapter.selection_prompt_instruction not in text
    assert not [index for index in step.critic_sites() if index in block]


@pytest.mark.parametrize('tui', _TUIS)
def test_the_repair_resumes_the_recorded_architect_only_where_the_tui_can(tui: str) -> None:
    step = _Step9(tui)
    block = step.gate_block()
    text = '\n'.join(step.lines[index] for index in block)
    revisions = [index for index in step.revise_sites() if index in block]

    if not step.tools.resume_architect:
        assert 'SendMessage' not in text
        return
    resumes = [index for index in step.resume_sites() if index in block]
    assert resumes, 'Claude Code repairs with a fresh architect instead of resuming the recorded one'
    assert any('ARCHITECT_AGENT_ID' in guard for guard in step.contract.guards_at(resumes[0]))
    assert [index for index in revisions if index > resumes[0]], 'no fresh revise to fall back to'


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_never_reviews_a_failing_draft_while_repairs_remain(tui: str) -> None:
    step = _Step9(tui)
    block = step.gate_block()
    revisions = [index for index in step.revise_sites() if index in block]

    assert revisions
    after_repair = [index for index in block if index > revisions[-1] and step.lines[index].strip()]
    assert after_repair and _NAMES_STEP_9.search(step.lines[after_repair[-1]]), (
        'the repair does not return to the top of Step 9 for a fresh validation'
    )


@pytest.mark.parametrize('tui', _TUIS)
def test_structural_repairs_spend_the_same_two_round_budget_as_critic_repairs(tui: str) -> None:
    step = _Step9(tui)
    block = step.gate_block()
    section = step.contract.step_section('9')
    revisions = [index for index in step.revise_sites() if index in block]

    increments = [index for index in block if _REPAIR_INCREMENT.search(step.lines[index])]
    assert increments and revisions and increments[0] < revisions[0]
    for status in ('refine', 'user_input'):
        assert [body for body in template_contract(section).decision_blocks(status) if _BUDGET_LEFT.search(body)]
    assert not step.find(_REPAIR_RESET), 'Step 9 resets the budget, so a failing draft repairs forever'
    assert {match.group('name') for match in _ROUND_COUNTER_INCREMENT.finditer(section)} <= {
        'REPAIR_ROUNDS',
        'REVIEW_ROUND',
    }


@pytest.mark.parametrize('tui', _TUIS)
def test_orchestrator_owned_findings_never_spend_a_repair_round(tui: str) -> None:
    step = _Step9(tui)
    orchestrator = step.findings_variable(FindingOwner.ORCHESTRATOR)

    assert not _names(orchestrator, step.lines[step.gate_guard()])


@pytest.mark.parametrize('tui', _TUIS)
def test_leftover_and_orchestrator_findings_reach_the_unresolved_checks_even_after_a_clean_review(tui: str) -> None:
    step = _Step9(tui)
    collected = step.leftovers_assignment()
    leftovers = step.leftovers_variable()
    section = template_contract(step.contract.step_section('9'))

    assert step.contract.guards_at(collected) == (), 'leftovers are collected on some paths only'
    assert step.gate_block().stop <= collected < step.critic_sites()[0]
    assignments = [
        index
        for index in step.rows
        if re.match(r'^\s*UNRESOLVED_CHECKS\s*=(?!=)', step.lines[index])
        and not _UNRESOLVED_RESET.match(step.lines[index])
    ]
    assert assignments and [index for index in assignments if not _names(leftovers, step.lines[index])] == []
    assert not [index for index in step.find(_UNRESOLVED_RESET) if index > collected]
    for status in ('completed', 'refine', 'user_input'):
        blocks = section.decision_blocks(status)
        assert [block for block in blocks if re.search(rf'UNRESOLVED_CHECKS\s*=(?!=).*\b{leftovers}\b', block)], (
            f'the {status} branch drops the structural leftovers'
        )


@pytest.mark.parametrize('tui', _TUIS)
def test_structural_leftovers_are_written_as_the_finding_key_an_accepted_answer_suppresses(tui: str) -> None:
    step = _Step9(tui)
    forms = _FINDING_FORMAT.findall(step.contract.block_at(step.leftovers_assignment()))

    assert {'[<part>]' in form for form in forms} == {True, False}, f'both finding forms are needed: {forms}'
    assert accepted_by_the_server(forms) == dict.fromkeys(forms, True)


@pytest.mark.parametrize('tui', _TUIS)
def test_every_leftover_quoted_on_the_one_accept_line_stays_accepted(tui: str) -> None:
    # The server reads only an accept SD's own line, which is why Step 10.2 records every
    # finding on that line: a finding wrapped onto a continuation line is asked again.
    step = _Step9(tui)
    forms = _FINDING_FORMAT.findall(step.contract.block_at(step.leftovers_assignment()))
    findings = [_FINDING_WITH_PART if '[<part>]' in form else _FINDING_WITHOUT_PART for form in forms]
    quoted = [_filled(form, finding) for form, finding in zip(forms, findings, strict=True)]

    one_line, _ = drop_accepted_findings(findings, _phase_accepting('; '.join(quoted)))
    wrapped, _ = drop_accepted_findings(findings, _phase_accepting('\n  - '.join(quoted)))

    assert len(findings) == 2 and one_line == []
    assert wrapped == findings[1:]


@pytest.mark.parametrize('tui', _TUIS)
def test_answering_the_unresolved_checks_clears_them_so_no_return_to_design_review_asks_again(tui: str) -> None:
    # Sign-off's "Go back to design review" re-enters Step 10 without passing Step 9, which is
    # the only other place UNRESOLVED_CHECKS is reset.
    contract = template_contract(_command(tui))
    lines = _command(tui).split('\n')
    rows = [index for index, step in enumerate(contract.line_steps()) if step == '10.2']
    guards = [index for index in rows if re.match(r'^\s*IF UNRESOLVED_CHECKS is not empty:', lines[index])]
    assert len(guards) == 1, f'Step 10.2 has no single unresolved-checks block: {guards}'
    block = _block_range(lines, guards[0])
    body_indentation = _indentation(lines[guards[0] + 1])
    answers = [
        index
        for index in block
        if 'supersedes=unresolved-checks' in lines[index] or re.match(r'^\s*UNRESOLVED_DIRECTION\s*=', lines[index])
    ]

    resets = [
        index
        for index in block
        if _UNRESOLVED_RESET.match(lines[index]) and _indentation(lines[index]) == body_indentation
    ]

    assert len(answers) == 2, f'Step 10.2 records no accept and no direction: {answers}'
    assert resets and resets[-1] > max(answers), 'answering the unresolved checks never clears them'


@pytest.mark.parametrize('tui', _TUIS)
def test_an_edit_that_cannot_be_stored_offers_only_fix_and_retry_or_abort(tui: str) -> None:
    section = template_contract(_command(tui)).step_section('10.5')

    offered, proceeding = unstorable_menu(section, _adapter(tui).selection_prompt_instruction)

    assert len(offered) == 2, f'an unstorable edit has two exits, not {offered}'
    assert proceeding == []


# ---------------------------------------------------------------------------
# B16 - one owner per rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_raises_none_of_the_rules_validate_document_now_owns(tui: str) -> None:
    contract = template_contract(_critic(tui))
    raised = contract.blocker_conditions() | contract.mechanical_findings()

    assert sorted(_MOVED_CRITIC_RULES & raised) == []
    assert sorted(_KEPT_MECHANICAL_RULES - contract.mechanical_findings()) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_checks_existence_only_for_paths_to_verify_choosing_the_marker_by_kind(tui: str) -> None:
    template = _critic(tui)
    contract = template_contract(template)
    lines = template.split('\n')

    for kind, marker in _EXISTENCE_MARKER_BY_KIND.items():
        raised = [
            index for index, line in enumerate(lines) if f'`{kind.value}`' in line and f'[{marker} - BLOCKING]' in line
        ]
        assert raised, f'no {marker} finding is raised for a missing `{kind.value}` path'
        assert all(any('paths_to_verify' in outer for outer in contract.enclosing_at(index)) for index in raised)
    globs = [index for index, line in enumerate(lines) if re.search(r'\bGlob\(', line)]
    assert globs
    assert [
        index for index in globs if not any('paths_to_verify' in outer for outer in contract.enclosing_at(index))
    ] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_relays_every_implementation_finding_as_a_mechanical_blocker(tui: str) -> None:
    template = _critic(tui)
    contract = template_contract(template)
    lines = template.split('\n')
    relays = [index for index, line in enumerate(lines) if _RELAYED_IMPLEMENTATION_FINDING.search(line)]
    forms = [match.group(0) for line in lines if (match := _RELAYED_IMPLEMENTATION_FINDING.search(line))]

    assert {'[<part>]' in form for form in forms} == {True, False}, f'both relay forms are needed: {forms}'
    assert all(any('implementation_findings' in outer for outer in contract.enclosing_at(index)) for index in relays)
    assert accepted_by_the_server(forms) == dict.fromkeys(forms, True)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_validates_the_implementation_plan_it_read(tui: str) -> None:
    # `CALL <tool>` is the agent templates' invocation grammar; a tool merely listed under
    # Retrieved Context is not a call.
    lines = _critic(tui).split('\n')
    reads = [index for index, line in enumerate(lines) if re.search(r'\bRead\(IMPLEMENTATION_PLAN_PATH\)', line)]
    validations = [
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith('CALL ')
        and _KEY_MODE_VALIDATION.search(line)
        and 'implementation_markdown=' in line
    ]

    assert reads and validations and reads[0] < validations[0]


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_never_raises_a_structural_finding_itself(tui: str) -> None:
    mentions = [line.strip() for line in _critic(tui).split('\n') if 'structural_findings' in line]

    assert mentions, 'the critic is never told that the gate owns structural_findings'
    assert [line for line in mentions if not re.search(r'\b(?:never|not)\b', line, re.IGNORECASE)] == []


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('agent', ['architect', 'critic'])
def test_the_phase_agents_call_validate_document_and_only_mcp_tools_they_declare(agent: str, tui: str) -> None:
    contract = template_contract(_architect(tui) if agent == 'architect' else _critic(tui))
    invoked = {tool for tool in contract.invoked_tools() if tool.startswith('mcp__')}

    assert _VALIDATE_DOCUMENT in invoked
    assert sorted(invoked - contract.declared_tools()) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_critic_stays_read_only_and_gains_only_validate_document(tui: str) -> None:
    declared = template_contract(_critic(tui)).declared_tools()

    assert _VALIDATE_DOCUMENT in declared
    assert sorted(declared - _CRITIC_READ_ONLY_GRANTS) == []


# ---------------------------------------------------------------------------
# Work item 8 - the architect's structural self-check
# ---------------------------------------------------------------------------


def _tasks(template: str) -> str:
    return template[template.index('TASKS:') :]


@pytest.mark.parametrize('tui', _TUIS)
def test_draft_and_revise_validate_after_persisting_the_design_and_implementation_plan(tui: str) -> None:
    tasks = _tasks(_architect(tui))
    lines = tasks.split('\n')
    update = create_phase_architect_agent_tools(_adapter(tui)).update_document.split('(', 1)[0] + '('
    persists = [index for index, line in enumerate(lines) if line.lstrip().startswith(f'CALL {update}')]
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

    assert persists and plan_writes and validations and reports
    assert persists[0] < validations[0] and plan_writes[0] < validations[0] < reports[0]


@pytest.mark.parametrize('tui', _TUIS)
def test_a_revise_with_no_new_feedback_still_runs_the_structural_self_check(tui: str) -> None:
    # A gate repair round re-engages the architect with mode and IDs only, so its get_feedback
    # holds nothing new; the self-check is its whole job.
    tasks = _tasks(_architect(tui))
    contract = template_contract(tasks)
    lines = tasks.split('\n')
    validations = [
        index
        for index, line in enumerate(lines)
        if line.lstrip().startswith('CALL ') and _KEY_MODE_VALIDATION.search(line)
    ]

    assert validations
    guards = contract.guards_at(validations[0])
    assert guards, 'explore validates too, though it writes no design'
    assert [guard for guard in guards if 'phase_mode' not in guard or _FEEDBACK_NEWNESS.search(guard)] == []
    assert all(mode in ' '.join(guards) for mode in ('draft', 'revise'))
    assert 'explore' not in ' '.join(guards)


@pytest.mark.parametrize('tui', _TUIS)
def test_every_architect_write_is_checked_for_the_content_loss_warning(tui: str) -> None:
    tasks = _tasks(_architect(tui))
    lines = tasks.split('\n')
    update = create_phase_architect_agent_tools(_adapter(tui)).update_document.split('(', 1)[0] + '('
    calls = [index for index, line in enumerate(lines) if line.lstrip().startswith('CALL ')]
    writes = [index for index in calls if lines[index].lstrip().startswith(f'CALL {update}')]

    assert writes
    for write in writes:
        following = [index for index in calls if index > write]
        bound = following[0] if following else len(lines)
        assert [index for index in range(write, bound) if CONTENT_LOSS_WARNING in lines[index]], (
            f'no content-loss check after: {lines[write].strip()}'
        )


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_globs_every_path_to_verify(tui: str) -> None:
    tasks = _tasks(_architect(tui))
    contract = template_contract(tasks)
    lines = tasks.split('\n')

    globs = [index for index, line in enumerate(lines) if re.search(r'\bGlob\(', line)]

    assert [index for index in globs if any('paths_to_verify' in outer for outer in contract.enclosing_at(index))]
