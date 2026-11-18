"""Phase 4 — the brief format the writing agents are shown, and the architect's half of it.

Behaviors B2, B3 and B4 of docs/phase-cooperative/phase-4-agent-ready-brief.md, and Scope 7: the
architect writes the design half of the brief in the shared forms and never what the finalizer
writes. Each runs against the
constants the agents are shown, never a copy kept here: the phase structure is parsed with the real
`Phase` parser, the implementation example goes through tests/support/plan_extraction.py, and B4 runs
the real structural checks on the example.
"""

import re
from functools import cache
from textwrap import indent

import pytest
from plan_extraction import (
    extract_checklist_items,
    extract_deferred_risks,
    extract_h2_names,
    extract_section,
    extract_steps,
)
from section_names import RETIRED_FIELDS, h2_collisions, mapped_h2_names, retired_section_mentions
from template_contract import template_contract

from src.models.document_validation import FindingOwner, StructuralCheck
from src.models.phase import Phase
from src.platform.template_helpers import (
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
    create_phase_finalizer_agent_tools,
)
from src.platform.templates.agents import (
    generate_phase_architect_template,
    generate_phase_critic_template,
    generate_phase_finalizer_template,
)
from src.platform.templates.agents.phase_architect import technical_phase_template
from src.platform.templates.phase_contract_grammar import (
    BRIEF_SECTION_PLACEHOLDERS,
    DESIGN_REVIEW_TAG,
    IMPLEMENTATION_BRIEF_EXAMPLE,
    SUCCESS_CRITERION_PLACEHOLDER,
)
from src.platform.tui_adapters import ClaudeCodeAdapter, CodexAdapter, OpenCodeAdapter
from src.platform.tui_adapters.base import TuiAdapter
from src.utils.phase_structure import check_implementation_structure


def shown_phase() -> Phase:
    return Phase.parse_markdown(technical_phase_template.replace('[phase-name-in-kebab-case]', 'brief-format'))


def test_the_phase_structure_agents_are_shown_holds_exactly_the_four_brief_sections() -> None:
    sections = shown_phase().additional_sections

    assert sections is not None
    assert tuple(sections) == Phase.BRIEF_SECTIONS
    assert {name: body.strip() for name, body in sections.items()} == {
        name: placeholder.strip() for name, placeholder in BRIEF_SECTION_PLACEHOLDERS.items()
    }


def test_the_phase_structure_agents_are_shown_teaches_no_retired_detail_field() -> None:
    shown = shown_phase()

    assert {field: getattr(shown, field) for field in RETIRED_FIELDS if getattr(shown, field) is not None} == {}


def test_no_h2_in_the_phase_structure_agents_are_shown_can_shadow_another() -> None:
    names = {*mapped_h2_names(), 'Metadata', *(shown_phase().additional_sections or {})}

    assert h2_collisions(names) == set()


def test_the_shadow_guard_flags_an_h2_whose_name_sits_inside_another() -> None:
    assert h2_collisions({'Design Shape', 'Design', 'Grounding'}) == {frozenset({'Design', 'Design Shape'})}


# B3. These string assertions are the contract, not prose: frozen respec-code scans each
# "#### Step N:" in "## Build Order > ### Steps" (code_command.py:291), the coder reads "## Checklist"
# in full and maps each "(Step N)" item to its work (coder_contracts.py:139), and the reviewers map
# findings to DR-NNN lines from "## Policy" (code_command.py:498, spec_alignment_reviewer.py:119).
# A reworded example breaks those readers (testing.md, "Where a string assertion is still legitimate").
def test_the_implementation_example_stays_readable_by_the_frozen_coding_workflow() -> None:
    steps = extract_steps(extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Build Order', 'Steps'))
    items = extract_checklist_items(extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Checklist'))

    assert steps == ['1', '2', '3']
    assert extract_steps(IMPLEMENTATION_BRIEF_EXAMPLE) == steps
    assert items
    assert all(item.steps and item.verify for item in items)
    assert {step for item in items for step in item.steps} == set(steps)
    assert extract_deferred_risks(extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Policy')) == ['DR-001']


def test_the_implementation_example_adds_the_brief_sections_beside_the_frozen_ones() -> None:
    assert extract_h2_names(IMPLEMENTATION_BRIEF_EXAMPLE) == [
        'Start here',
        'Build Order',
        'Policy',
        'Checklist',
        'Exit criteria',
        'Deviations',
    ]


# B4. The fixture phase defines exactly what the example cites, and nothing more: SD-1, T-1 to T-4,
# SC-2, G-1, G-2 and the three Skeleton Index paths its steps create. Defining more would make the
# checks report the extra IDs; defining less would make them report dangling references.
EXAMPLE_PHASE = """# Phase: brief-format

## Overview
### Objectives
Answer repeated queries quickly.
### Scope
The query path, its cache and the result list.
### Dependencies
None.
### Deliverables
A cached query path that renders its results.

## Design Shape
### Skeleton Index
- `<path to the repository query module>` :: Repository.query(query: Query) -> Rows
- `<path to the cache module>` :: QueryCache.get(query: Query) -> Rows
- `<path to the result list component>` :: ResultList.render(rows: Rows) -> View
### Test List
- `<path to the query test file>::returns the rows a query matches` — T-1
- `<path to the query test file>::returns no rows for an unmatched query` — T-2
- `<path to the cache test file>::serves a repeated query from the cache` — T-3
- `<path to the result list test file>::renders one item per row` — T-4

## Design Decisions
### Settled Design Decisions
- SD-001 | source=user | supersedes=OD-001 | decision=Option A | rationale=simpler | rejected=Option B | binding=yes

## Additional Details
### Success Criteria
- SC-2: results render as a list — measure: T-4 passes

## Guardrails
- G-1: a query never returns rows it does not match
- G-2: a cache miss falls through to the repository
"""


def test_the_checks_report_exactly_the_placeholder_commands_of_the_implementation_example() -> None:
    steps = extract_steps(extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Build Order', 'Steps'))
    items = [
        line.strip()
        for line in extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Checklist').splitlines()
        if line.startswith('- [ ]')
    ]
    exit_commands = re.findall(r'`([^`]+)`', extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Exit criteria'))
    assert len(steps) == len(items) == 3
    assert len(exit_commands) == 1

    findings = check_implementation_structure(IMPLEMENTATION_BRIEF_EXAMPLE, Phase.parse_markdown(EXAMPLE_PHASE))

    assert sorted((f.check, f.subject, f.part, f.owner) for f in findings) == sorted(
        [
            *(
                (StructuralCheck.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', FindingOwner.ARCHITECT)
                for item in items
            ),
            *(
                (StructuralCheck.IMPLEMENTATION_COMMAND_PLACEHOLDER, f'Step {step}', 'Verify', FindingOwner.FINALIZER)
                for step in steps
            ),
            *(
                (StructuralCheck.IMPLEMENTATION_COMMAND_PLACEHOLDER, 'Exit criteria', command, FindingOwner.FINALIZER)
                for command in exit_commands
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Scope 7 - the architect writes the design half of the brief, and nothing the finalizer owns
# ---------------------------------------------------------------------------

_HERMETIC_MODELS = {'reasoning': 'model', 'orchestration': 'model', 'coding': 'model', 'review': 'model'}
_TUIS = ('claude-code', 'opencode', 'codex')

_ARCHITECT_BRIEF_SECTION = 'Delegation Bounds'
FINALIZER_SECTIONS = tuple(name for name in Phase.BRIEF_SECTIONS if name != _ARCHITECT_BRIEF_SECTION)
FINALIZER_PLAN_SECTIONS = ('Start here', 'Exit criteria', 'Deviations')
DRAFT_FIELDS = ('Goal', 'Files', 'Depends on')
STEP_FIELDS = tuple(
    re.findall(r'^- \*\*([^*]+):\*\*', extract_section(IMPLEMENTATION_BRIEF_EXAMPLE, 'Build Order', 'Steps'), re.M)[:7]
)
FINALIZE_FIELDS = tuple(field for field in STEP_FIELDS if field not in DRAFT_FIELDS)
# The finalizer reads these four lists from the architect's notes (its STEP 1 and STEP 3).
EXPLORATION_PATH_LISTS = 'build-on, leave-alone, exemplar and convention'


def _adapter(tui: str) -> TuiAdapter:
    if tui == 'opencode':
        return OpenCodeAdapter(model_overrides=_HERMETIC_MODELS)
    if tui == 'codex':
        return CodexAdapter(model_overrides=_HERMETIC_MODELS)
    return ClaudeCodeAdapter()


@cache
def _architect(tui: str) -> str:
    return generate_phase_architect_template(create_phase_architect_agent_tools(_adapter(tui)))


def _mode_branch(tui: str, mode: str) -> str:
    return template_contract(_architect(tui)).condition_block('phase_mode', mode)


def _without_embedded_examples(template: str) -> str:
    return template.replace(indent(technical_phase_template, '  '), '').replace(
        indent(IMPLEMENTATION_BRIEF_EXAMPLE, '  '), ''
    )


def _flat(text: str) -> str:
    return ' '.join(text.split())


def test_the_step_fields_are_read_from_the_example_the_agents_are_shown() -> None:
    assert len(STEP_FIELDS) == 7 and STEP_FIELDS[0] == 'Goal'
    assert set(DRAFT_FIELDS) < set(STEP_FIELDS) and len(FINALIZE_FIELDS) == 4


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_drafts_each_step_with_exactly_the_three_draft_fields(tui: str) -> None:
    draft, revise = _mode_branch(tui, 'draft'), _mode_branch(tui, 'revise')

    assert draft and revise
    assert [field for field in DRAFT_FIELDS if f'**{field}:**' not in draft] == []
    assert [field for field in FINALIZE_FIELDS if f'**{field}:**' in draft or f'**{field}:**' in revise] == []
    assert '**Objective**' not in _architect(tui) and '**Actions**' not in _architect(tui)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_writes_the_design_half_of_the_brief_in_the_shared_forms(tui: str) -> None:
    # Contract strings, not prose: each is a form the structural checks parse (the Delegation Bounds
    # H2, the Design Narrative H4, the SC entry, the Test List ID and the seam citation).
    draft = _flat(_mode_branch(tui, 'draft'))

    assert f'## {_ARCHITECT_BRIEF_SECTION}' in draft
    assert '#### Design Narrative' in draft
    assert _flat(SUCCESS_CRITERION_PLACEHOLDER) in draft
    assert '— T-<n>' in draft
    assert '`<path>` :: <Owner>.<member>' in draft


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_is_told_never_to_write_what_the_finalizer_writes(tui: str) -> None:
    lines = _without_embedded_examples(_architect(tui)).split('\n')

    for name in (*FINALIZER_SECTIONS, *FINALIZER_PLAN_SECTIONS):
        mentions = [line.strip() for line in lines if f'## {name}' in line]
        assert mentions, f'the architect is never told about ## {name}'
        assert [line for line in mentions if not re.search(r'\b(?:never|remove)\b', line, re.IGNORECASE)] == []


@pytest.mark.parametrize('tui', _TUIS)
def test_a_revise_on_a_finalized_document_removes_the_finalizer_sections(tui: str) -> None:
    # The finalizer then does a full pass after the next approval (Scope 6, STEP 2). The trigger is
    # the sections themselves, never the stage marker (phase 2 B24).
    revise = _mode_branch(tui, 'revise')
    contract = template_contract(revise)
    lines = revise.split('\n')
    guards = [
        index
        for index, line in enumerate(lines)
        if re.match(r'^\s*(?:IF|ELIF)\b', line) and all(f'## {name}' in line for name in FINALIZER_SECTIONS)
    ]

    assert len(guards) == 1, 'revise has no single branch for a document that holds the finalizer sections'
    assert re.search(r'\bremove\b', contract.block_at(guards[0]), re.IGNORECASE)


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architects_notes_carry_the_four_path_lists_the_finalizer_reads(tui: str) -> None:
    template = _architect(tui)
    store = create_phase_architect_agent_tools(_adapter(tui)).store_analysis
    notes = template[template.index(f'CALL {store}') : template.index('STEP 5:')]
    finalizer = generate_phase_finalizer_template(create_phase_finalizer_agent_tools(_adapter(tui)))

    assert EXPLORATION_PATH_LISTS in _flat(_mode_branch(tui, 'explore'))
    assert EXPLORATION_PATH_LISTS in _flat(notes)
    assert EXPLORATION_PATH_LISTS in _flat(finalizer)


# Scope 7 and Scope 8: no phase prompt teaches or checks a retired detail section. The names come
# from the model's own mapping for the retired fields.
def test_the_retired_section_scan_fires_on_a_retired_name_and_spares_the_plan_heading() -> None:
    assert retired_section_mentions('Reference these targets in Testing Strategy and NFRs.') == {
        'Testing Strategy',
        'NFR',
    }
    assert retired_section_mentions('Read the "## Architecture Direction" section.') == set()


@pytest.mark.parametrize('tui', _TUIS)
@pytest.mark.parametrize('agent', ['architect', 'critic', 'finalizer'])
def test_no_phase_agent_teaches_or_checks_a_retired_detail_section(agent: str, tui: str) -> None:
    adapter = _adapter(tui)
    rendered = {
        'architect': lambda: _architect(tui),
        'critic': lambda: generate_phase_critic_template(create_phase_critic_agent_tools(adapter)),
        'finalizer': lambda: generate_phase_finalizer_template(create_phase_finalizer_agent_tools(adapter)),
    }[agent]()

    assert sorted(retired_section_mentions(_without_embedded_examples(rendered))) == []


@pytest.mark.parametrize('tui', _TUIS)
def test_the_architect_acts_only_on_critic_findings_from_a_design_review(tui: str) -> None:
    # After "go back to design review" from sign-off, the latest critic entry is the brief
    # review's, whose findings are the finalizer's. The tag is the first line under each entry's
    # `## Iteration N - Score: X` heading (README "Critic findings").
    assignments = [
        line
        for line in _architect(tui).split('\n')
        if re.match(r'^\s*-?\s*(?:LATEST_BLOCKERS|LATEST_KEY_ISSUES)\s*=', line)
    ]

    assert assignments and all(DESIGN_REVIEW_TAG in line for line in assignments), assignments
