"""Phase 3 — deterministic structural checks on a phase document and its implementation.md.

Behaviors B1-B9, B12 (section-name overlap), B17 and B18 of
docs/phase-cooperative/phase-3-structural-checks.md. Each defect test feeds a document that is
clean except for one defect and asserts the exact findings by check, subject, part and owner.
Exact equality is deliberate: a false positive costs two architect repair rounds and a user prompt
(judgment call 1), so over-reporting must fail as loudly as under-reporting. `detail` wording is
never asserted; check IDs and finding keys are the contract prompts cite.
"""

import random
import re
from pathlib import Path

import pytest
from fastmcp import FastMCP

from src.mcp.tools.document_tools import register_document_tools
from src.models.document_validation import CitedPath, CitedPathKind, FindingOwner, StructuralCheck, StructuralFinding
from src.models.phase import Phase
from src.platform.templates.agents.phase_architect import implementation_plan_example
from src.utils.language_extensions import EXTENSION_TO_LANGUAGE
from src.utils.materializers import _MATERIALIZER_MAP
from src.utils.phase_structure import (
    check_implementation_structure,
    check_phase_structure,
    drop_accepted_findings,
    extract_cited_paths,
)
from src.utils.skeleton_generator import parse_skeleton_index, parse_test_list
from src.utils.skeleton_types import SkeletonIndexParseError
from tests.support.language_denylist import Hit, scan


C = StructuralCheck
ARCHITECT = FindingOwner.ARCHITECT
ORCHESTRATOR = FindingOwner.ORCHESTRATOR

Row = tuple[str, str, str, str]
ExpectedRow = tuple[StructuralCheck, str, str, FindingOwner]

RESEARCH_REQUIREMENTS = 'Additional Details > Research Requirements'
PLAN_REFERENCES = 'Additional Details > Implementation Plan References'

OVERVIEW = (
    '## Overview',
    '### Objectives',
    'Issue invoices for saved accounts.',
    '### Scope',
    'Invoices only.',
    '### Dependencies',
    'None.',
    '### Deliverables',
    'An invoicing service.',
)


def lines(*rows: str) -> str:
    return '\n'.join(rows)


def phase_markdown(fields: dict[str, str], extra_sections: tuple[tuple[str, str], ...] = ()) -> str:
    document = ['# Phase: sample-phase', '', *OVERVIEW]
    sections_by_h2: dict[str, list[tuple[str, str]]] = {}
    for field_name, content in fields.items():
        h2, h3 = Phase.HEADER_FIELD_MAPPING[field_name]
        sections_by_h2.setdefault(h2, []).append((h3, content))
    for h2, sections in sections_by_h2.items():
        document.append(f'## {h2}')
        for h3, content in sections:
            document.extend([f'### {h3}', content])
    for name, content in extra_sections:
        document.extend([f'## {name}', content])
    return '\n'.join(document) + '\n'


def parsed_phase(fields: dict[str, str], extra_sections: tuple[tuple[str, str], ...] = ()) -> Phase:
    return Phase.parse_markdown(phase_markdown(fields, extra_sections))


SD_001 = (
    '- SD-001 | source=user | supersedes=OD-001 | decision=Option A | rationale=simpler'
    ' | rejected=Option B | binding=yes'
)
RP_001 = (
    '- RP-001 | Which numbering scheme audits best? | informs: OD-002 | Technologies: ledgers;'
    ' Topics: numbering; Query: audit-friendly invoice numbers | tier: synthesis-only [approved]'
)
READ_LINE = '- Read: `.best-practices/invoice-numbering.md` — informs: OD-002 — Source: RP-001'

CLEAN_FIELDS: dict[str, str] = {
    'module_layout': lines(
        '- `src/accounts/` — owns account records',
        '  - `src/accounts/store.unit` — persistence',
        '- `src/billing.unit` — owns invoices',
    ),
    'skeleton_index': lines(
        '- `src/accounts/store.unit` :: AccountStore.save(account: Account) -> AccountId',
        '- `src/billing.unit` :: issue(order: Order) -> Invoice, async',
        '  - `src/billing.unit` — issues one invoice per order',
    ),
    'collaboration_and_wiring': 'Invoices calls AccountStore.save, per SD-001.',
    'test_list': lines(
        '- `tests/billing_check.unit::issues one invoice per order`',
        '- `tests/accounts_check.unit::saves a new account` — the happy path',
    ),
    'design_shape_additional': lines(
        '#### UX Contract',
        '##### Interaction Flows',
        '- FLOW-1: open an invoice → pay it — **Pass:** the invoice shows as paid',
    ),
    'open_design_decisions': lines(
        '- OD-002 | Invoice numbering',
        '  - Option A: Sequential — simple to audit',
        '  - Option B: Random — hides order volume',
        '  - Recommended: A — auditors expect gaps to mean something',
        '  - Affects: `src/billing.unit`, FLOW-1, RP-001',
    ),
    'settled_design_decisions': SD_001,
    'implementation_plan_references': '- Constraint: `plans/sample-plan.md` § "Billing"',
    'research_requirements': lines(RP_001, READ_LINE),
}

UX_FLOWS = (
    '#### UX Contract',
    '##### Interaction Flows',
    '- FLOW-1: open an invoice → pay it — **Pass:** the invoice shows as paid',
    '- FLOW-2: open a receipt → print it — **Pass:** the receipt prints',
)


def design(extra_sections: tuple[tuple[str, str], ...] = (), **overrides: str) -> Phase:
    fields = {**CLEAN_FIELDS, **overrides}
    return parsed_phase({name: content for name, content in fields.items() if content}, extra_sections)


def rows(findings: list[StructuralFinding]) -> list[Row]:
    return sorted((f.check.value, f.subject, f.part, f.owner.value) for f in findings)


def expected(*entries: ExpectedRow) -> list[Row]:
    return sorted((check.value, subject, part, owner.value) for check, subject, part, owner in entries)


def cited(paths: list[CitedPath]) -> list[tuple[str, str, str]]:
    return sorted((p.path, p.kind.value, p.cited_in) for p in paths)


IMPLEMENTATION_TITLE = '# Implementation Plan: sample-phase'
STEPS_SECTION = lines(
    '## Build Order',
    '### Steps',
    '#### Step 1: Account Store',
    '**Objective**: Persist accounts before anything bills them.',
    '',
    '#### Step 2: Invoices',
    '**Objective**: Issue invoices once accounts persist, per SD-001 and OD-002.',
)
POLICY_SECTION = lines(
    '## Policy',
    '### Execution Intent Policy',
    '- Mode: MVP',
    '',
    '### Deferred Risk Register',
    '- DR-001 | status=accepted | severity=P2 | scope=global | reason=Numbering audit deferred',
)
CHECKLIST_SECTION = lines(
    '## Checklist',
    '- [ ] Save accounts (Step 1) (verify: run-checks accounts)',
    '- [x] Issue invoices (Step 2) (verify: run-checks invoices)',
)
EMPTY_CHECKLIST_SECTION = lines('## Checklist', 'Nothing to verify yet.')
CLEAN_IMPLEMENTATION = lines(IMPLEMENTATION_TITLE, '', STEPS_SECTION, '', POLICY_SECTION, '', CHECKLIST_SECTION)

STEP_2_ITEM = '- [x] Issue invoices (Step 2) (verify: run-checks invoices)'
STEP_2_BLOCK_END = '**Objective**: Issue invoices once accounts persist, per SD-001 and OD-002.'


def implementation(replace: dict[str, str] | None = None) -> str:
    text = CLEAN_IMPLEMENTATION
    for old, new in (replace or {}).items():
        assert old in text, f'fixture anchor missing: {old!r}'
        text = text.replace(old, new)
    return text


def implementation_findings(markdown: str) -> list[Row]:
    return rows(check_implementation_structure(markdown, design()))


# --- clean baselines -------------------------------------------------------------------------


def test_a_clean_shaped_phase_reports_no_structural_findings() -> None:
    assert rows(check_phase_structure(design())) == []


def test_a_clean_implementation_plan_reports_no_findings() -> None:
    assert implementation_findings(CLEAN_IMPLEMENTATION) == []


# --- B1: seam paths against Module Layout ------------------------------------------------------


def test_a_seam_whose_path_is_not_in_module_layout_is_reported_naming_the_path() -> None:
    phase = design(
        skeleton_index=lines(
            CLEAN_FIELDS['skeleton_index'],
            '- `src/ledger.unit` :: Ledger.post(entry: Entry) -> Receipt',
        )
    )

    assert rows(check_phase_structure(phase)) == expected(
        (C.SEAM_PATH_NOT_IN_MODULE_LAYOUT, 'src/ledger.unit', '', ARCHITECT)
    )


def test_a_seam_under_a_module_layout_directory_entry_is_covered() -> None:
    phase = design(
        module_layout=lines('- `src/accounts/` — owns account records', '- `src/billing.unit` — owns invoices'),
        skeleton_index=lines(
            '- `src/accounts/deep/store.unit` :: AccountStore.save(account: Account) -> AccountId',
            '- `src/billing.unit` :: issue(order: Order) -> Invoice',
        ),
    )

    assert rows(check_phase_structure(phase)) == []


@pytest.mark.parametrize(
    ('layout_path', 'seam_path'),
    [('src/billing.unit', './src/billing.unit'), ('./src/billing.unit', 'src/billing.unit')],
    ids=['dot-slash-seam', 'dot-slash-layout'],
)
def test_a_leading_dot_slash_never_separates_a_seam_from_its_module_layout_entry(
    layout_path: str, seam_path: str
) -> None:
    phase = design(
        module_layout=f'- `{layout_path}` — owns invoices',
        skeleton_index=f'- `{seam_path}` :: issue(order: Order) -> Invoice',
    )

    assert rows(check_phase_structure(phase)) == []


def test_a_phase_with_no_skeleton_index_reports_nothing() -> None:
    phase = parsed_phase({'module_layout': '- `src/billing.unit` — owns invoices', 'test_list': '- None'})

    assert rows(check_phase_structure(phase)) == []


def test_a_phase_with_no_design_layer_reports_nothing() -> None:
    assert rows(check_phase_structure(parsed_phase({}))) == []


# --- B2: Skeleton Index parity with the CLI parser ----------------------------------------------


def _first_extension(language: str) -> str:
    return next(extension for extension, owner in EXTENSION_TO_LANGUAGE.items() if owner == language)


SEAM_PATHS = [
    pytest.param('src/accounts', id='no-extension'),
    *(pytest.param(f'src/accounts{_first_extension(language)}', id=language) for language in sorted(_MATERIALIZER_MAP)),
]

SIGNATURE_LINES = [
    pytest.param('Accounts.register(attrs: Attrs) -> Account', id='meta-notation'),
    pytest.param('Accounts.register(attrs: Attrs) -> Account, internal, consequential', id='meta-notation-tagged'),
    pytest.param('function register(attrs) returns Account', id='native-syntax'),
    pytest.param('Accounts.valid?(user) -> boolean', id='question-mark-member'),
    pytest.param('Accounts.register!(attrs) -> {:ok, User}', id='bang-member'),
    pytest.param('Billing.Accounts.register(attrs: Attrs) -> Account', id='qualified-owner'),
]


def _cli_rejects(skeleton_index: str) -> bool:
    try:
        parse_skeleton_index(skeleton_index)
    except SkeletonIndexParseError:
        return True
    return False


SEAM_WRAPPINGS = [
    pytest.param(('', ''), id='unfenced'),
    pytest.param(('```text', '```'), id='backtick-fence'),
    pytest.param(('~~~', '~~~'), id='tilde-fence'),
]


@pytest.mark.parametrize('wrapping', SEAM_WRAPPINGS)
@pytest.mark.parametrize('path', SEAM_PATHS)
@pytest.mark.parametrize('signature', SIGNATURE_LINES)
def test_a_skeleton_index_signature_is_reported_exactly_when_the_cli_parser_would_reject_it(
    path: str, signature: str, wrapping: tuple[str, str]
) -> None:
    seam = f'- `{path}` :: {signature}'
    opener, closer = wrapping
    skeleton_index = lines(opener, seam, closer) if opener else seam
    phase = parsed_phase(
        {
            'module_layout': f'- `{path}` — owns accounts',
            'skeleton_index': skeleton_index,
            'test_list': '- `tests/accounts_check::registers a new account`',
        }
    )

    findings = rows(check_phase_structure(phase))

    if _cli_rejects(skeleton_index):
        assert findings == expected((C.SEAM_SIGNATURE_UNPARSEABLE, seam, '', ARCHITECT))
    else:
        assert findings == []


def test_a_fenced_seam_the_cli_reads_is_checked_against_module_layout() -> None:
    phase = design(
        skeleton_index=lines(
            CLEAN_FIELDS['skeleton_index'],
            '```text',
            '- `src/ledger.unit` :: Ledger.post(entry: Entry) -> Receipt',
            '```',
        )
    )

    assert rows(check_phase_structure(phase)) == expected(
        (C.SEAM_PATH_NOT_IN_MODULE_LAYOUT, 'src/ledger.unit', '', ARCHITECT)
    )


def test_fenced_skeleton_index_lines_the_cli_never_reads_report_nothing() -> None:
    phase = design(
        skeleton_index=lines(
            CLEAN_FIELDS['skeleton_index'],
            '```text',
            '- `src/billing.unit` — an example note',
            'prose that mentions a :: separator',
            '- src/billing.unit :: Invoices.void(invoice: Invoice) -> Receipt',
            '```',
        )
    )
    assert sum(len(entry.members) for entry in parse_skeleton_index(phase.skeleton_index or '')) == 2

    assert rows(check_phase_structure(phase)) == []


VALID_SEAM = '- `src/accounts` :: Accounts.find(id: AccountId) -> Account'


@pytest.mark.parametrize(
    'defective',
    [
        pytest.param('- `src/accounts` — Accounts.create(attrs) -> Account', id='backticked-path-without-signature'),
        pytest.param('- src/accounts :: Accounts.create(attrs) -> Account', id='unquoted-path-column-0'),
        pytest.param('  - src/accounts :: Accounts.create(attrs) -> Account', id='unquoted-path-indented'),
    ],
)
def test_a_seam_bullet_the_cli_silently_skips_is_reported(defective: str) -> None:
    assert parse_skeleton_index(defective) == ()
    phase = parsed_phase(
        {
            'module_layout': '- `src/accounts` — owns accounts',
            'skeleton_index': lines(VALID_SEAM, defective),
            'test_list': '- `tests/accounts_check::finds an account`',
        }
    )

    assert [(row[0], row[1].strip(), row[2], row[3]) for row in rows(check_phase_structure(phase))] == expected(
        (C.SEAM_ENTRY_MALFORMED, defective.strip(), '', ARCHITECT)
    )


def test_an_indented_signature_line_that_does_not_parse_is_reported() -> None:
    defective = '  - `src/accounts` :: function create(attrs) returns Account'
    phase = parsed_phase(
        {
            'module_layout': '- `src/accounts` — owns accounts',
            'skeleton_index': lines(VALID_SEAM, defective),
            'test_list': '- `tests/accounts_check::finds an account`',
        }
    )

    assert [(row[0], row[1].strip(), row[2], row[3]) for row in rows(check_phase_structure(phase))] == expected(
        (C.SEAM_SIGNATURE_UNPARSEABLE, defective.strip(), '', ARCHITECT)
    )


def test_an_empty_skeleton_index_marker_and_indented_notes_report_nothing() -> None:
    assert rows(check_phase_structure(design(skeleton_index='- None', test_list='- None'))) == []
    assert rows(check_phase_structure(design())) == []


@pytest.mark.parametrize(
    'garbage',
    ['- `` :: ', '- `src/accounts` :: ', '- `src/accounts` :: ()', '- `src/accounts` :: -> ->', '- ` :: `', '- `'],
)
def test_validation_never_raises_on_a_garbled_skeleton_index_line(garbage: str) -> None:
    phase = design(skeleton_index=lines(VALID_SEAM, garbage), module_layout='- `src/accounts` — owns accounts')

    assert isinstance(check_phase_structure(phase), list)


# --- B3: Test List entries ----------------------------------------------------------------------


@pytest.mark.parametrize(
    'defective',
    [
        pytest.param('- `tests/billing_check.unit`', id='no-behavior-separator'),
        pytest.param('- `tests/billing_check.unit::`', id='empty-behavior'),
        pytest.param('- `::issues one invoice per order`', id='empty-path'),
        pytest.param('- tests/billing_check.unit::issues one invoice per order', id='unquoted'),
        pytest.param('- `tests/billing_check.unit` :: issues one invoice per order', id='seam-shaped'),
        pytest.param(
            '- Behavior: `tests/billing_check.unit::issues one invoice per order`', id='span-not-opening-bullet'
        ),
    ],
)
def test_a_test_list_bullet_without_a_path_and_behavior_is_reported(defective: str) -> None:
    phase = design(test_list=lines('- `tests/accounts_check.unit::saves a new account`', defective))

    assert rows(check_phase_structure(phase)) == expected((C.TEST_ENTRY_WITHOUT_BEHAVIOR, defective, '', ARCHITECT))


def test_text_after_a_test_list_entry_is_allowed() -> None:
    phase = design(test_list='- `tests/billing_check.unit::issues one invoice per order` (the core seam, SD-001)')

    assert rows(check_phase_structure(phase)) == []


@pytest.mark.parametrize('test_list', ['- None', ''], ids=['none-marker', 'absent'])
def test_seams_with_an_empty_test_list_are_reported_once(test_list: str) -> None:
    assert rows(check_phase_structure(design(test_list=test_list))) == expected(
        (C.TEST_LIST_EMPTY, 'Test List', '', ARCHITECT)
    )


def test_a_test_list_holding_only_malformed_bullets_reports_only_the_bullets() -> None:
    defective = '- `tests/billing_check.unit`'

    assert rows(check_phase_structure(design(test_list=defective))) == expected(
        (C.TEST_ENTRY_WITHOUT_BEHAVIOR, defective, '', ARCHITECT)
    )


def test_a_test_list_holding_only_a_fenced_entry_the_cli_reads_is_not_empty() -> None:
    test_list = lines('```text', '- `tests/billing_check.unit::issues one invoice per order`', '```')
    assert parse_test_list(test_list)

    assert rows(check_phase_structure(design(test_list=test_list))) == []


def test_a_fenced_test_list_bullet_the_cli_never_reads_reports_nothing() -> None:
    phase = design(test_list=lines(CLEAN_FIELDS['test_list'], '```text', '- an example bullet, not an entry', '```'))

    assert rows(check_phase_structure(phase)) == []


# --- B4: Open Design Decision entries -----------------------------------------------------------


OD_ENTRY = '- OD-003 | Cache placement'
OPTION_A = '  - Option A: In front of the store — simple'
OPTION_B = '  - Option B: In the service — flexible'
OPTION_C = '  - Option C: At the edge — fastest reads'
RECOMMENDED = '  - Recommended: A — fewer moving parts'


@pytest.mark.parametrize(
    ('entry', 'subject', 'part'),
    [
        pytest.param(['- OD-003 | ', OPTION_A, OPTION_B, RECOMMENDED], 'OD-003', 'title', id='empty-title'),
        pytest.param(
            ['- OD-003 | title: ', OPTION_A, OPTION_B, RECOMMENDED], 'OD-003', 'title', id='empty-prefixed-title'
        ),
        pytest.param([OD_ENTRY, OPTION_B, RECOMMENDED], 'OD-003', 'Option A', id='no-option-a'),
        pytest.param([OD_ENTRY, OPTION_A, RECOMMENDED], 'OD-003', 'Option B', id='no-option-b'),
        pytest.param([OD_ENTRY, OPTION_A, '  - Option B:', RECOMMENDED], 'OD-003', 'Option B', id='empty-option-b'),
        pytest.param(
            [OD_ENTRY, OPTION_A, OPTION_B, OPTION_C, '  - Option D: Nowhere — no cache', RECOMMENDED],
            'OD-003',
            'Option D',
            id='fourth-option',
        ),
        pytest.param(
            [OD_ENTRY, OPTION_A, OPTION_B, '  - Option A: Beside the store — odd', RECOMMENDED],
            'OD-003',
            'Option A',
            id='repeated-letter',
        ),
        pytest.param([OD_ENTRY, OPTION_A, OPTION_B], 'OD-003', 'Recommended', id='no-recommended'),
        pytest.param(
            [OD_ENTRY, OPTION_A, OPTION_B, '  - Recommended: C — fastest'],
            'OD-003',
            'Recommended',
            id='recommends-absent-option',
        ),
        pytest.param(
            [OD_ENTRY, OPTION_A, OPTION_B, '  - Recommended: Option C — fastest'],
            'OD-003',
            'Recommended',
            id='recommends-absent-prefixed-option',
        ),
        pytest.param(
            [
                '- OD-003 | Cache placement | Option A: In front — simple | Option B: In the service — flexible'
                ' | Recommended: A — fewer moving parts'
            ],
            'OD-003',
            'single-line form',
            id='retired-single-line-form',
        ),
        pytest.param(
            ['- Should the cache sit in front of the store?', OD_ENTRY, OPTION_A, OPTION_B, RECOMMENDED],
            '- Should the cache sit in front of the store?',
            'entry line',
            id='bullet-that-is-not-an-entry',
        ),
    ],
)
def test_an_open_decision_entry_defect_is_reported_once_naming_the_part(
    entry: list[str], subject: str, part: str
) -> None:
    phase = design(open_design_decisions=lines(*entry))

    assert rows(check_phase_structure(phase)) == expected((C.DECISION_ENTRY_MALFORMED, subject, part, ARCHITECT))


@pytest.mark.parametrize(
    'entry',
    [
        pytest.param([OD_ENTRY, OPTION_A, OPTION_B, RECOMMENDED], id='canonical'),
        pytest.param([OD_ENTRY, OPTION_A, OPTION_B, OPTION_C, '  - Recommended: C — fastest'], id='with-option-c'),
        pytest.param(['- OD-003 | title: Cache placement', OPTION_A, OPTION_B, RECOMMENDED], id='title-prefix'),
        pytest.param(
            [
                OD_ENTRY,
                OPTION_A,
                OPTION_B,
                RECOMMENDED,
                '  - Affects: `src/billing.unit`, SD-001, FLOW-1, RP-001',
                '  - Notes: measured under load',
            ],
            id='extra-sub-lines',
        ),
        pytest.param([OD_ENTRY, OPTION_A, OPTION_B, '  - Recommended: Option B — flexible'], id='option-prefix'),
        pytest.param([OD_ENTRY, OPTION_A, OPTION_B, '  - Recommended: B. Flexible'], id='trailing-punctuation'),
        pytest.param(
            [
                OD_ENTRY,
                '  - **Option A**: In front of the store — simple',
                '  - **Option B:** In the service — flexible',
                '  - **Recommended**: A — fewer moving parts',
            ],
            id='bold-labels',
        ),
        pytest.param(['- None'], id='none-marker'),
    ],
)
def test_a_canonical_open_decision_entry_passes(entry: list[str]) -> None:
    assert rows(check_phase_structure(design(open_design_decisions=lines(*entry)))) == []


# --- B5: Settled Design Decision entries --------------------------------------------------------

IMPLEMENTATION_SD_WITHOUT_REASON = (
    '- SD-### | source=implementation | supersedes=Invoices.issue(order: Order) -> Invoice'
)


@pytest.mark.parametrize(
    ('entry', 'subject', 'part', 'owner'),
    [
        pytest.param(
            '- SD-002 | source=user | supersedes=OD-004 | decision=Option A | rationale=simpler | binding=yes',
            'SD-002',
            'rejected',
            ORCHESTRATOR,
            id='user-settling-an-od-without-rejected',
        ),
        pytest.param(
            '- SD-002 | source=user | supersedes=CQ-007 | decision=keep as designed | rationale=fine | binding=yes',
            'SD-002',
            'rejected',
            ORCHESTRATOR,
            id='user-settling-a-cq-without-rejected',
        ),
        pytest.param(
            '- SD-002 | source=user | decision=keep existing signature at src/billing.unit | binding=yes',
            'SD-002',
            'rationale',
            ORCHESTRATOR,
            id='user-without-rationale',
        ),
        pytest.param(
            '- SD-002 | source=user-edit | section=Design Shape > Module Layout | decision=added the ledger module',
            'SD-002',
            'binding',
            ORCHESTRATOR,
            id='user-edit-without-binding',
        ),
        pytest.param(
            '- SD-002 | source=materializer | decision=unmaterialized at src/billing.unit | binding=yes',
            'SD-002',
            'rationale',
            ORCHESTRATOR,
            id='materializer-without-rationale',
        ),
        pytest.param(
            '- SD-002 | source=architect | rationale=carried forward | binding=yes',
            'SD-002',
            'decision',
            ARCHITECT,
            id='architect-without-decision',
        ),
        pytest.param(
            '- SD-002 | source=architect | decision=Sequential | rationale= | binding=yes',
            'SD-002',
            'rationale',
            ARCHITECT,
            id='architect-with-empty-rationale',
        ),
        pytest.param(
            IMPLEMENTATION_SD_WITHOUT_REASON,
            IMPLEMENTATION_SD_WITHOUT_REASON,
            'reason',
            ORCHESTRATOR,
            id='unnumbered-implementation-without-reason',
        ),
        pytest.param(
            '- SD-002 | source=robot | decision=Sequential | rationale=simpler | binding=yes',
            'SD-002',
            'source',
            ARCHITECT,
            id='unknown-source',
        ),
        pytest.param(
            '- SD-002 | decision=Sequential | rationale=simpler | binding=yes',
            'SD-002',
            'source',
            ARCHITECT,
            id='missing-source',
        ),
    ],
)
def test_a_settled_entry_missing_a_field_its_source_requires_is_reported_naming_the_field(
    entry: str, subject: str, part: str, owner: FindingOwner
) -> None:
    phase = design(settled_design_decisions=lines(SD_001, entry))

    assert rows(check_phase_structure(phase)) == expected((C.SETTLED_ENTRY_MALFORMED, subject, part, owner))


ACCEPT_QUOTING_AN_SD_LINE = (
    '- SD-002 | source=user | supersedes=unresolved-checks | decision=accept as-is:'
    ' settled-entry-malformed - SD-### | source=implementation | supersedes=OD-004 [reason] — add reason=;'
    ' decision-entry-malformed OD-002 [Option B] — add an Option B line'
    ' | rationale=accepted at design review | binding=yes'
)


@pytest.mark.parametrize(
    'entry',
    [
        pytest.param(
            '- SD-### | source=implementation | supersedes=Invoices.issue(order: Order | Draft) -> Invoice | Receipt'
            ' | reason=drafts are billed too',
            id='frozen-code-protocol-change-with-a-bar-in-supersedes',
        ),
        pytest.param(
            '- SD-### | source=implementation | supersedes=Invoices.void | reason=never needed',
            id='frozen-code-dropped-member',
        ),
        pytest.param(
            '- SD-002 | source=materializer | decision=unmaterialized at src/billing.unit'
            ' | rationale=no materializer is registered for this language | binding=yes',
            id='materializer',
        ),
        pytest.param(
            '- SD-4 | source=user-menu | supersedes=OD-4 | decision=Sequential'
            ' | rationale=accepted recommended default | binding=yes',
            id='legacy-user-menu-answer',
        ),
        pytest.param(
            '- SD-### | source=user-menu | decision=keep existing signature at src/billing.unit'
            " | rationale=matches what's already implemented | binding=yes",
            id='legacy-user-menu-sign-off',
        ),
        pytest.param(
            '- SD-### | source=user-edit | section=Design Shape > Module Layout | decision=added the ledger module'
            ' | binding=yes',
            id='legacy-unnumbered-user-edit',
        ),
        pytest.param(
            '- SD-002 | source=user-edit | section=Design Shape > Module Layout | decision=added the ledger module'
            ' | binding=yes',
            id='user-edit',
        ),
        pytest.param(
            '- SD-### | source=user-override | decision=proceed despite critic findings | rationale=deadline'
            ' | binding=yes',
            id='legacy-user-override',
        ),
        pytest.param(
            '- SD-002 | source=user | decision=keep existing signature at src/billing.unit'
            ' | rationale=matches what is already implemented | binding=yes',
            id='user-sign-off-answer-settling-no-id',
        ),
        pytest.param(
            '- SD-002 | source=architect | decision=Sequential | rationale=carried forward | binding=yes',
            id='architect',
        ),
        pytest.param(ACCEPT_QUOTING_AN_SD_LINE, id='accept-as-is-quoting-an-sd-line'),
    ],
)
def test_a_settled_entry_any_writer_produces_today_passes(entry: str) -> None:
    assert rows(check_phase_structure(design(settled_design_decisions=lines(SD_001, entry)))) == []


# --- B6: ID integrity ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('overrides', 'subject'),
    [
        pytest.param({'collaboration_and_wiring': 'Invoices calls AccountStore, per OD-009.'}, 'OD-009', id='od'),
        pytest.param({'collaboration_and_wiring': 'Invoices calls AccountStore, per SD-005.'}, 'SD-005', id='sd'),
        pytest.param({'collaboration_and_wiring': 'Invoices calls AccountStore, per CQ-002.'}, 'CQ-002', id='cq'),
        pytest.param({'collaboration_and_wiring': 'Invoices calls AccountStore, per FLOW-3.'}, 'FLOW-3', id='flow'),
        pytest.param({'collaboration_and_wiring': 'Invoices calls AccountStore, per RP-004.'}, 'RP-004', id='rp'),
        pytest.param(
            {
                'open_design_decisions': lines(
                    OD_ENTRY, OPTION_A, OPTION_B, RECOMMENDED, '  - Affects: `src/billing.unit`, OD-009'
                )
            },
            'OD-009',
            id='affects-line',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    '#### UX Contract',
                    '- FLOW-1: open an invoice → pay it — **Pass:** the invoice shows as paid',
                    '```text',
                    '- FLOW-2: an example flow inside a fence defines nothing',
                    '```',
                ),
                'collaboration_and_wiring': 'Invoices follows FLOW-2.',
            },
            'FLOW-2',
            id='definition-inside-a-fence',
        ),
    ],
)
def test_a_reference_to_an_undefined_id_is_reported(overrides: dict[str, str], subject: str) -> None:
    assert rows(check_phase_structure(design(**overrides))) == expected((C.DANGLING_REFERENCE, subject, '', ARCHITECT))


@pytest.mark.parametrize(
    'overrides',
    [
        pytest.param({'collaboration_and_wiring': 'Invoices calls AccountStore, per OD-001.'}, id='settled-od'),
        pytest.param(
            {
                'collaboration_and_wiring': 'Invoices calls AccountStore, per CQ-004.',
                'settled_design_decisions': lines(
                    SD_001,
                    '- SD-002 | source=user | supersedes=CQ-004 | decision=keep as designed | rationale=fine'
                    ' | rejected=the critic alternative | binding=yes',
                ),
            },
            id='settled-cq',
        ),
        pytest.param(
            {
                'open_design_decisions': lines(OD_ENTRY, OPTION_A, OPTION_B, RECOMMENDED),
                'collaboration_and_wiring': 'Invoices calls AccountStore, per OD-3.',
            },
            id='short-reference-to-padded-definition',
        ),
        pytest.param(
            {
                'open_design_decisions': lines('- OD-3 | Cache placement', OPTION_A, OPTION_B, RECOMMENDED),
                'collaboration_and_wiring': 'Invoices calls AccountStore, per OD-003.',
            },
            id='padded-reference-to-short-definition',
        ),
        pytest.param(
            {'collaboration_and_wiring': lines('Invoices calls AccountStore.', '```text', 'see OD-099', '```')},
            id='reference-inside-a-fence',
        ),
        pytest.param(
            {
                'settled_design_decisions': (
                    '- SD-001 | source=user | supersedes=OD-001 | decision=Option A | rationale=simpler than OD-077'
                    ' | rejected=Option B | binding=yes'
                )
            },
            id='reference-inside-an-sd-entry',
        ),
        pytest.param(
            {'research_requirements': lines(RP_001.replace('informs: OD-002', 'informs: OD-088'), READ_LINE)},
            id='reference-inside-a-research-requirements-line',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    *UX_FLOWS,
                    '##### Accessibility Requirements',
                    '- Keyboard paths:',
                    '  - FLOW-1: completes with Tab and Enter only',
                    '  - FLOW-2: completes with Tab and Enter only',
                )
            },
            id='flow-sub-bullets-under-another-subsection',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    *UX_FLOWS,
                    '##### Breakpoints',
                    '- `narrow` (`320px`): one column',
                    '  - FLOW-1 must complete at this width',
                )
            },
            id='flow-led-breakpoint-note',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    *UX_FLOWS, '##### Accessibility Requirements', '- FLOW-1: keyboard only'
                )
            },
            id='column-0-flow-bullet-under-another-subsection',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    *UX_FLOWS, '- More flows:', '  - FLOW-3: export a statement — **Pass:** a file downloads'
                ),
                'collaboration_and_wiring': 'Invoices calls AccountStore.save, per SD-001, then FLOW-3.',
            },
            id='indented-flow-definition-still-resolves',
        ),
    ],
)
def test_a_reference_that_resolves_is_not_reported(overrides: dict[str, str]) -> None:
    assert rows(check_phase_structure(design(**overrides))) == []


SD_002_ARCHITECT = '- SD-002 | source=architect | decision=Sequential | rationale=carried forward | binding=yes'


@pytest.mark.parametrize(
    ('overrides', 'subject', 'owner'),
    [
        pytest.param(
            {
                'open_design_decisions': lines(
                    OD_ENTRY,
                    OPTION_A,
                    OPTION_B,
                    RECOMMENDED,
                    '- OD-003 | Cache size',
                    OPTION_A,
                    OPTION_B,
                    RECOMMENDED,
                )
            },
            'OD-003',
            ARCHITECT,
            id='od',
        ),
        pytest.param(
            {
                'open_design_decisions': lines(
                    '- OD-3 | Cache placement',
                    OPTION_A,
                    OPTION_B,
                    RECOMMENDED,
                    '- OD-003 | Cache size',
                    OPTION_A,
                    OPTION_B,
                    RECOMMENDED,
                )
            },
            'OD-003',
            ARCHITECT,
            id='od-numbers-compare-as-integers',
        ),
        pytest.param(
            {'settled_design_decisions': lines(SD_001, SD_002_ARCHITECT, SD_002_ARCHITECT)},
            'SD-002',
            ARCHITECT,
            id='sd-second-written-by-architect',
        ),
        pytest.param(
            {
                'settled_design_decisions': lines(
                    SD_001,
                    SD_002_ARCHITECT,
                    '- SD-002 | source=user | decision=keep existing signature at src/billing.unit'
                    ' | rationale=matches what is already implemented | binding=yes',
                )
            },
            'SD-002',
            ORCHESTRATOR,
            id='sd-second-written-by-user',
        ),
        pytest.param(
            {'research_requirements': lines(RP_001, READ_LINE, RP_001.replace('audits best', 'reads best'))},
            'RP-001',
            ORCHESTRATOR,
            id='rp',
        ),
        pytest.param(
            {'research_requirements': lines(RP_001, READ_LINE, '- [approved] ' + RP_001.removeprefix('- '))},
            'RP-001',
            ORCHESTRATOR,
            id='rp-with-its-mark-first',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    *UX_FLOWS,
                    '- FLOW-2: open a statement → export it — **Pass:** a file downloads',
                    '##### Accessibility Requirements',
                    '- Keyboard paths: FLOW-1',
                )
            },
            'FLOW-2',
            ARCHITECT,
            id='flow-within-interaction-flows',
        ),
        pytest.param(
            {
                'design_shape_additional': lines(
                    '#### UX Contract',
                    '- FLOW-1: open an invoice → pay it — **Pass:** the invoice shows as paid',
                    '- FLOW-1: open a receipt → print it — **Pass:** the receipt prints',
                )
            },
            'FLOW-1',
            ARCHITECT,
            id='flow',
        ),
    ],
)
def test_an_id_defined_twice_is_reported_at_the_second_definition(
    overrides: dict[str, str], subject: str, owner: FindingOwner
) -> None:
    assert rows(check_phase_structure(design(**overrides))) == expected((C.DUPLICATE_ID, subject, '', owner))


RP_002_MODULE_ONLY = (
    '- RP-002 | Which invoice layout prints best? | informs: `src/billing.unit` | Technologies: printing;'
    ' Topics: layout; Query: printable invoice layout | tier: synthesis-only [approved]'
)


@pytest.mark.parametrize(
    'research_requirements',
    [
        pytest.param(
            lines(
                RP_001.replace('informs: OD-002', 'informs: `src/accounts/`'),
                '- Read: `.best-practices/store-layout.md` — informs: `src/accounts/` — Source: RP-001',
            ),
            id='module-only-informs',
        ),
        pytest.param(
            lines(
                RP_001.replace('informs: OD-002', 'informs: `src/accounts/`'),
                '- Read: `.best-practices/store-layout.md` — informs: — Source: RP-001',
            ),
            id='empty-informs',
        ),
        pytest.param(
            lines(
                RP_001,
                '- Read: `.best-practices/invoice-numbering.md` — informs: OD-002 — Source: in-kb',
                '  - Applied: Step 2 per RP-001',
            ),
            id='applied-line-naming-the-rp',
        ),
        pytest.param(
            lines(
                RP_001,
                RP_002_MODULE_ONLY,
                READ_LINE,
                '- Read: `.best-practices/invoice-numbering.md` — informs: `src/billing.unit` — Source: RP-002',
            ),
            id='dedupe-line-for-a-dropped-rp',
        ),
    ],
)
def test_research_lines_that_only_name_an_rp_never_define_it_twice(research_requirements: str) -> None:
    assert rows(check_phase_structure(design(research_requirements=research_requirements))) == []


def test_a_reference_to_an_rp_named_only_as_a_read_line_source_resolves() -> None:
    phase = design(
        research_requirements=lines(RP_001, '- Read: `.best-practices/ledger.md` — informs: OD-002 — Source: RP-007'),
        collaboration_and_wiring='Invoices calls AccountStore.save, per SD-001 and RP-007.',
    )

    assert rows(check_phase_structure(phase)) == []


def test_unnumbered_settled_entries_are_never_duplicates() -> None:
    frozen = '- SD-### | source=implementation | supersedes=Invoices.void | reason=never needed'

    assert rows(check_phase_structure(design(settled_design_decisions=lines(SD_001, frozen, frozen)))) == []


@pytest.mark.parametrize('settled_id', ['OD-002', 'OD-2'], ids=['same-form', 'numbers-compare-as-integers'])
def test_an_open_decision_that_a_settled_entry_supersedes_is_reported_as_still_open(settled_id: str) -> None:
    phase = design(
        settled_design_decisions=lines(
            SD_001,
            f'- SD-002 | source=user | supersedes={settled_id} | decision=Sequential | rationale=simpler'
            ' | rejected=Random | binding=yes',
        )
    )

    assert rows(check_phase_structure(phase)) == expected((C.SETTLED_DECISION_STILL_OPEN, 'OD-002', '', ARCHITECT))


# --- B7: cited paths for host verification ------------------------------------------------------


CITING_FIELDS: dict[str, str] = {
    'architecture': 'Layered per `.best-practices/layering.md` and (.best-practices/invoice-numbering.md) only',
    'implementation_plan_references': lines(
        'Pre-resolved decisions that MUST be honored.',
        '- Constraint: `plans/sample-plan.md` § "Billing"',
        '- Constraint: `plans/sample-plan.md § "Ledger"`',
    ),
    'research_requirements': lines(
        RP_001,
        READ_LINE,
        '  - Read: docs/ledger-notes.md — informs: OD-002 — Source: in-kb',
    ),
}

CITED_IN_CITING_FIELDS = sorted(
    [
        ('.best-practices/invoice-numbering.md', CitedPathKind.READ.value, RESEARCH_REQUIREMENTS),
        ('docs/ledger-notes.md', CitedPathKind.READ.value, RESEARCH_REQUIREMENTS),
        ('plans/sample-plan.md', CitedPathKind.CONSTRAINT.value, PLAN_REFERENCES),
        ('.best-practices/layering.md', CitedPathKind.BEST_PRACTICES.value, 'System Design > Architecture'),
        ('.best-practices/invoice-numbering.md', CitedPathKind.BEST_PRACTICES.value, 'System Design > Architecture'),
    ]
)


def test_read_constraint_and_best_practices_paths_are_returned_once_each_with_kind_and_place() -> None:
    assert cited(extract_cited_paths(parsed_phase(CITING_FIELDS))) == CITED_IN_CITING_FIELDS


def test_a_best_practices_path_on_a_read_line_is_returned_once_as_read() -> None:
    phase = parsed_phase({'research_requirements': READ_LINE})

    assert cited(extract_cited_paths(phase)) == [
        ('.best-practices/invoice-numbering.md', CitedPathKind.READ.value, RESEARCH_REQUIREMENTS)
    ]


def test_a_best_practices_mention_in_an_additional_section_is_returned_with_that_section() -> None:
    phase = parsed_phase({}, extra_sections=(('Guardrails', 'Follow `.best-practices/guardrails.md` always.'),))

    assert cited(extract_cited_paths(phase)) == [
        ('.best-practices/guardrails.md', CitedPathKind.BEST_PRACTICES.value, 'Guardrails')
    ]


def test_cited_paths_are_the_same_whether_or_not_the_files_exist_where_the_check_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    phase = parsed_phase(CITING_FIELDS)

    without_files = cited(extract_cited_paths(phase))
    for path, _, _ in CITED_IN_CITING_FIELDS:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text('cited\n')
    with_files = cited(extract_cited_paths(phase))

    assert without_files == with_files == CITED_IN_CITING_FIELDS


# --- B8: implementation.md structure ------------------------------------------------------------


ASK_USER_MARKER = (
    'ask user — no test command configured for examplelang;'
    ' set [commands].test in .respec-ai/config/standards/examplelang.toml'
)


@pytest.mark.parametrize(
    'command',
    [
        pytest.param('', id='empty'),
        pytest.param('TODO', id='todo'),
        pytest.param('todo: pick a command', id='todo-lowercase'),
        pytest.param('[TODO] pick a command', id='todo-bracketed'),
        pytest.param('no_preference', id='no-preference'),
        pytest.param('<the test command>', id='angle-placeholder'),
        pytest.param('[the test command]', id='square-placeholder'),
    ],
)
def test_a_checklist_item_whose_verify_command_is_missing_or_a_placeholder_is_reported(command: str) -> None:
    item = f'- [x] Issue invoices (Step 2) (verify: {command})'

    assert implementation_findings(implementation({STEP_2_ITEM: item})) == expected(
        (C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', ARCHITECT)
    )


def test_a_checklist_item_with_no_verify_group_is_reported() -> None:
    item = '- [x] Issue invoices (Step 2)'

    assert implementation_findings(implementation({STEP_2_ITEM: item})) == expected(
        (C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', ARCHITECT)
    )


def test_a_checklist_item_naming_no_step_is_reported() -> None:
    item = '- [ ] Update the changelog (verify: run-checks docs)'

    assert implementation_findings(implementation({STEP_2_ITEM: lines(STEP_2_ITEM, item)})) == expected(
        (C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'step', ARCHITECT)
    )


def test_a_checklist_item_naming_an_unknown_step_is_reported() -> None:
    item = '- [ ] Archive invoices (Step 9) (verify: run-checks archive)'

    assert implementation_findings(implementation({STEP_2_ITEM: lines(STEP_2_ITEM, item)})) == expected(
        (C.DANGLING_REFERENCE, 'Step 9', '', ARCHITECT)
    )


def test_an_implementation_plan_reference_to_an_undefined_phase_id_is_reported() -> None:
    markdown = implementation({STEP_2_BLOCK_END: STEP_2_BLOCK_END.replace('OD-002', 'OD-042')})

    assert implementation_findings(markdown) == expected((C.DANGLING_REFERENCE, 'OD-042', '', ARCHITECT))


@pytest.mark.parametrize(
    'heading',
    ['#### Step three: Reports', '#### Step 3 Reports', '#### Step 3:', '#### Reports'],
)
def test_a_step_heading_frozen_readers_would_skip_is_reported(heading: str) -> None:
    markdown = implementation({STEP_2_BLOCK_END: lines(STEP_2_BLOCK_END, '', heading, 'Render the report.')})

    assert implementation_findings(markdown) == expected(
        (C.IMPLEMENTATION_STEP_HEADING_MALFORMED, heading, '', ARCHITECT)
    )


def test_a_step_number_defined_twice_is_reported() -> None:
    markdown = implementation({STEP_2_BLOCK_END: lines(STEP_2_BLOCK_END, '', '#### Step 2: Invoices Again')})

    assert implementation_findings(markdown) == expected((C.DUPLICATE_ID, 'Step 2', '', ARCHITECT))


def test_a_step_no_checklist_item_verifies_is_reported() -> None:
    markdown = implementation({STEP_2_BLOCK_END: lines(STEP_2_BLOCK_END, '', '#### Step 3: Reports')})

    assert implementation_findings(markdown) == expected((C.IMPLEMENTATION_STEP_UNVERIFIED, 'Step 3', '', ARCHITECT))


def test_a_plan_with_no_steps_is_reported() -> None:
    steps = lines('## Build Order', '### Steps', 'Steps follow once the design settles.')
    markdown = lines(IMPLEMENTATION_TITLE, steps, POLICY_SECTION, EMPTY_CHECKLIST_SECTION)

    assert implementation_findings(markdown) == expected((C.IMPLEMENTATION_NO_STEPS, 'Steps', '', ARCHITECT))


@pytest.mark.parametrize(
    ('markdown', 'part'),
    [
        pytest.param(
            lines(
                IMPLEMENTATION_TITLE,
                '## Build Order',
                '### Staging',
                'Accounts before invoices.',
                POLICY_SECTION,
                EMPTY_CHECKLIST_SECTION,
            ),
            'Build Order > Steps',
            id='steps',
        ),
        pytest.param(
            lines(IMPLEMENTATION_TITLE, POLICY_SECTION, EMPTY_CHECKLIST_SECTION),
            'Build Order > Steps',
            id='build-order',
        ),
        pytest.param(lines(IMPLEMENTATION_TITLE, STEPS_SECTION, POLICY_SECTION), 'Checklist', id='checklist'),
        pytest.param(lines(IMPLEMENTATION_TITLE, STEPS_SECTION, CHECKLIST_SECTION), 'Policy', id='policy'),
    ],
)
def test_a_missing_required_implementation_section_is_reported_naming_it(markdown: str, part: str) -> None:
    assert implementation_findings(markdown) == expected(
        (C.IMPLEMENTATION_SECTION_MISSING, 'implementation.md', part, ARCHITECT)
    )


@pytest.mark.parametrize(
    'item',
    [
        pytest.param(f'- [x] Issue invoices (Step 2) (verify: {ASK_USER_MARKER})', id='ask-user-marker'),
        pytest.param(
            '- [x] Issue invoices (Step 2) (verify: run-checks invoices) (verify: run-checks invoice-screens)',
            id='one-group-per-language',
        ),
        pytest.param(
            f'- [x] Issue invoices (Step 2) (verify: run-checks invoices) (verify: {ASK_USER_MARKER})',
            id='command-and-marker',
        ),
        pytest.param('- [X] Issue invoices (Step 2) (verify: run-checks (fast) invoices)', id='nested-parentheses'),
    ],
)
def test_a_checklist_item_with_a_sanctioned_verify_value_passes(item: str) -> None:
    assert implementation_findings(implementation({STEP_2_ITEM: item})) == []


def test_a_fenced_heading_under_steps_is_neither_a_step_nor_malformed() -> None:
    markdown = implementation(
        {STEP_2_BLOCK_END: lines(STEP_2_BLOCK_END, '```text', '#### Not a step', '- [ ] not an item', '```')}
    )

    assert implementation_findings(markdown) == []


def test_the_taught_implementation_plan_passes_once_its_verify_placeholders_are_concrete_commands() -> None:
    concrete = re.sub(r'\(verify: <[^>]*>\)', '(verify: run-checks all)', implementation_plan_example)
    assert concrete != implementation_plan_example

    assert rows(check_implementation_structure(concrete, design())) == []


def test_the_taught_implementation_plan_with_its_placeholders_left_in_is_reported_on_every_item() -> None:
    placeholder_items = [line for line in implementation_plan_example.splitlines() if '(verify: <' in line]
    assert len(placeholder_items) == 3

    assert rows(check_implementation_structure(implementation_plan_example, design())) == expected(
        *((C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', ARCHITECT) for item in placeholder_items)
    )


# --- B9: zero language bias in what the checks report -------------------------------------------


def _with_extension(extension: str) -> Phase:
    return parsed_phase(
        {
            'module_layout': f'- `src/billing{extension}` — owns invoices',
            'skeleton_index': lines(
                f'- `src/billing{extension}` :: Invoices.issue(order: Order) -> Invoice',
                f'- `src/ledger{extension}` :: Ledger.post(entry: Entry) -> Receipt',
                f'- `src/billing{extension}` :: function issue(order) returns Invoice',
                f'- `src/billing{extension}` — issues invoices',
            ),
            'test_list': lines(
                f'- `tests/billing_check{extension}::issues one invoice per order`',
                f'- `tests/billing_check{extension}`',
            ),
        }
    )


@pytest.mark.parametrize('extension', ['', '.qzx', '.zzq'], ids=['none', 'synthetic-a', 'synthetic-b'])
def test_findings_never_depend_on_a_path_extension(extension: str) -> None:
    found = [
        (check, subject.replace(extension, '') if extension else subject, part, owner)
        for check, subject, part, owner in rows(check_phase_structure(_with_extension(extension)))
    ]

    assert found == expected(
        (C.SEAM_PATH_NOT_IN_MODULE_LAYOUT, 'src/ledger', '', ARCHITECT),
        (C.SEAM_SIGNATURE_UNPARSEABLE, '- `src/billing` :: function issue(order) returns Invoice', '', ARCHITECT),
        (C.SEAM_ENTRY_MALFORMED, '- `src/billing` — issues invoices', '', ARCHITECT),
        (C.TEST_ENTRY_WITHOUT_BEHAVIOR, '- `tests/billing_check`', '', ARCHITECT),
    )


CORPUS_PHASE_FIELDS: dict[str, str] = {
    **CLEAN_FIELDS,
    'module_layout': '- `src/billing` — owns invoices',
    'skeleton_index': lines(
        '- `src/billing` :: Invoices.issue(order: Order) -> Invoice',
        '- `src/ledger` :: Ledger.post(entry: Entry) -> Receipt',
        '- `src/billing` — issues invoices',
        '- `src/billing` :: Accounts.valid?(user) -> boolean',
        '- `src/billing` :: Accounts.register!(attrs) -> {:ok, User}',
        '* `src/billing` :: Invoices.void(invoice: Invoice) -> Receipt',
    ),
    'test_list': lines(
        '- `tests/billing_check::issues one invoice per order`',
        '- `tests/billing_check`',
        '* `tests/billing_check::voids an invoice`',
    ),
    'collaboration_and_wiring': 'Invoices calls the ledger, per OD-009.',
    'open_design_decisions': lines(
        '- OD-002 | Invoice numbering',
        '  - Option A: Sequential — simple to audit',
        '  - Recommended: A — auditable',
        '- OD-002 | Invoice numbering again',
        OPTION_A,
        OPTION_B,
        RECOMMENDED,
    ),
    'settled_design_decisions': lines(
        SD_001,
        '- SD-003 | source=user | supersedes=OD-002 | decision=Sequential | rationale=simpler | rejected=Random'
        ' | binding=yes',
        '- SD-004 | source=architect | decision=Sequential | binding=yes',
    ),
}
CORPUS_PHASE_SECTIONS = (('Implementation Notes', 'Notes that shadow the implementation section.'),)
CORPUS_EMPTY_TEST_LIST_FIELDS = {**CLEAN_FIELDS, 'test_list': '- None'}
CORPUS_IMPLEMENTATIONS = (
    implementation(
        {
            STEP_2_BLOCK_END: lines(
                STEP_2_BLOCK_END,
                '',
                '#### Step three: Reports',
                '',
                '#### Step 2: Invoices Again',
                '',
                '#### Step 4: Archive',
            ),
            STEP_2_ITEM: lines(
                STEP_2_ITEM,
                '- [ ] Update the changelog (verify: run-checks docs)',
                '- [ ] Archive invoices (Step 9) (verify: run-checks archive)',
                '- [ ] Tidy accounts (Step 1) (verify: TODO)',
            ),
            POLICY_SECTION: '',
        }
    ),
    lines(
        IMPLEMENTATION_TITLE,
        '## Build Order',
        '### Steps',
        'Steps follow once the design settles.',
        POLICY_SECTION,
        EMPTY_CHECKLIST_SECTION,
    ),
)


def biased_details(findings: list[StructuralFinding]) -> list[tuple[str, list[Hit]]]:
    return [(finding.detail, hits) for finding in findings if (hits := scan(finding.detail))]


def test_the_findings_corpus_triggers_every_check_and_every_detail_is_a_language_neutral_line() -> None:
    corpus_phase = parsed_phase(CORPUS_PHASE_FIELDS, CORPUS_PHASE_SECTIONS)
    corpus_text = '\n'.join(
        [
            phase_markdown(CORPUS_PHASE_FIELDS, CORPUS_PHASE_SECTIONS),
            phase_markdown(CORPUS_EMPTY_TEST_LIST_FIELDS),
            *CORPUS_IMPLEMENTATIONS,
        ]
    )
    assert scan(corpus_text) == [], 'the corpus itself must be language-neutral'

    findings = [
        *check_phase_structure(corpus_phase),
        *check_phase_structure(parsed_phase(CORPUS_EMPTY_TEST_LIST_FIELDS)),
        *(
            finding
            for markdown in CORPUS_IMPLEMENTATIONS
            for finding in check_implementation_structure(markdown, corpus_phase)
        ),
    ]

    assert {finding.check for finding in findings} == set(StructuralCheck)
    assert all(finding.detail.strip() and '\n' not in finding.detail for finding in findings)
    assert biased_details(findings) == []


def test_the_finding_detail_guard_fires_on_a_biased_detail() -> None:
    biased = StructuralFinding(
        check=C.SEAM_ENTRY_MALFORMED,
        location='Design Shape > Skeleton Index',
        subject='- `src/billing` — issues invoices',
        owner=ARCHITECT,
        detail='Rewrite the entry as a pytest fixture in a .py file.',
    )

    assert biased_details([biased])


async def test_the_published_validate_document_description_names_no_language() -> None:
    mcp = FastMCP('validate-document-description-probe')
    register_document_tools(mcp)
    tools = await mcp.list_tools()
    description = next(tool.description for tool in tools if tool.name == 'validate_document')

    assert description
    assert scan(description) == []


# --- B12 (structural half): unmapped H2 names that overlap another H2 name -----------------------


@pytest.mark.parametrize(
    ('extra_sections', 'subjects'),
    [
        pytest.param((('System', 'Shadowing notes.'),), ['System'], id='contained-in-a-mapped-name'),
        pytest.param((('Implementation Notes', 'Notes.'),), ['Implementation Notes'], id='contains-a-mapped-name'),
        pytest.param((('Meta', 'Notes.'),), ['Meta'], id='contained-in-metadata'),
        pytest.param(
            (('Guardrails', 'Rule one.'), ('Guardrails Extra', 'Rule two.')),
            ['Guardrails', 'Guardrails Extra'],
            id='two-additional-sections-shorter-first',
        ),
        pytest.param(
            (('Guardrails Extra', 'Rule two.'), ('Guardrails', 'Rule one.')),
            ['Guardrails', 'Guardrails Extra'],
            id='two-additional-sections-longer-first',
        ),
    ],
)
def test_an_additional_section_whose_name_overlaps_another_h2_name_is_reported(
    extra_sections: tuple[tuple[str, str], ...], subjects: list[str]
) -> None:
    assert rows(check_phase_structure(design(extra_sections=extra_sections))) == expected(
        *((C.SECTION_NAME_OVERLAP, subject, '', ARCHITECT) for subject in subjects)
    )


def test_additional_sections_with_distinct_names_pass() -> None:
    extra_sections = tuple(
        (name, 'Content.')
        for name in ('Guardrails', 'Delegation Bounds', 'Behaviors & Acceptance', 'Grounding', 'Evolution Log')
    )

    assert rows(check_phase_structure(design(extra_sections=extra_sections))) == []


# --- B17: an accepted finding stays accepted ----------------------------------------------------


def finding(check: StructuralCheck, subject: str, part: str = '', owner: FindingOwner = ARCHITECT) -> StructuralFinding:
    return StructuralFinding(
        check=check, location='Design Decisions', subject=subject, part=part, owner=owner, detail='Fix it.'
    )


OPTION_B_FINDING = finding(C.DECISION_ENTRY_MALFORMED, 'OD-002', 'Option B')
OPTION_A_FINDING = finding(C.DECISION_ENTRY_MALFORMED, 'OD-002', 'Option A')


def _accept(quoted: str, source: str = 'user', supersedes: str = 'unresolved-checks') -> str:
    return (
        f'- SD-002 | source={source} | supersedes={supersedes} | decision=accept as-is: {quoted}'
        ' | rationale=accepted at design review | binding=yes'
    )


def test_a_finding_the_user_accepted_as_is_is_dropped_and_recorded() -> None:
    phase = design(
        settled_design_decisions=lines(
            SD_001, _accept('decision-entry-malformed OD-002 [Option B] — add an Option B line')
        )
    )

    assert drop_accepted_findings([OPTION_B_FINDING], phase) == (
        [],
        ['accepted: decision-entry-malformed OD-002 [Option B]'],
    )


def test_an_accepted_implementation_finding_is_dropped_and_recorded() -> None:
    item_finding = finding(
        C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, '- [ ] Tidy accounts (Step 1) (verify: TODO)', 'verify'
    )
    phase = design(
        settled_design_decisions=lines(
            SD_001,
            _accept(
                'implementation-checklist-item-malformed - [ ] Tidy accounts (Step 1) (verify: TODO) [verify]'
                ' — supply the command'
            ),
        )
    )

    assert drop_accepted_findings([item_finding], phase) == (
        [],
        ['accepted: implementation-checklist-item-malformed - [ ] Tidy accounts (Step 1) (verify: TODO) [verify]'],
    )


@pytest.mark.parametrize(
    'settled',
    [
        pytest.param(SD_001, id='no-accept-entry'),
        pytest.param(
            lines(SD_001, _accept('decision-entry-malformed OD-002 [Option B] — x', source='architect')),
            id='architect-entry-quoting-it',
        ),
        pytest.param(
            lines(SD_001, _accept('decision-entry-malformed OD-002 [Option B] — x', source='materializer')),
            id='materializer-entry-quoting-it',
        ),
        pytest.param(
            lines(SD_001, _accept('decision-entry-malformed OD-002 [Option B] — x', source='user-menu')),
            id='legacy-user-menu-entry-quoting-it',
        ),
        pytest.param(
            lines(
                SD_001,
                '- SD-002 | source=user | supersedes=OD-004 | decision=decision-entry-malformed OD-002 [Option B]'
                ' | rationale=y | rejected=z | binding=yes',
            ),
            id='user-entry-settling-something-else',
        ),
    ],
)
def test_a_finding_no_user_accept_entry_quotes_is_still_reported(settled: str) -> None:
    assert drop_accepted_findings([OPTION_B_FINDING], design(settled_design_decisions=settled)) == (
        [OPTION_B_FINDING],
        [],
    )


def test_accepting_one_part_of_a_subject_never_hides_a_different_part() -> None:
    phase = design(settled_design_decisions=lines(SD_001, _accept('decision-entry-malformed OD-002 [Option A] — x')))

    assert drop_accepted_findings([OPTION_A_FINDING, OPTION_B_FINDING], phase) == (
        [OPTION_B_FINDING],
        ['accepted: decision-entry-malformed OD-002 [Option A]'],
    )


def test_an_accepted_finding_whose_subject_is_itself_a_settled_entry_line_stays_dropped() -> None:
    sd_line = '- SD-### | source=implementation | supersedes=Invoices.void'
    sd_finding = finding(C.SETTLED_ENTRY_MALFORMED, sd_line, 'reason', ORCHESTRATOR)
    phase = design(
        settled_design_decisions=lines(
            SD_001, sd_line, _accept(f'settled-entry-malformed {sd_line} [reason] — add reason= to the entry')
        )
    )

    assert drop_accepted_findings([sd_finding], phase) == (
        [],
        [f'accepted: settled-entry-malformed {sd_line} [reason]'],
    )


# --- B18: ownership is computed, not guessed ----------------------------------------------------


@pytest.mark.parametrize(
    ('entry', 'part', 'owner'),
    [
        pytest.param('- SD-002 | source=user | decision=x | binding=yes', 'rationale', ORCHESTRATOR, id='user'),
        pytest.param(
            '- SD-002 | source=user-edit | section=Design Shape > Test List | binding=yes',
            'decision',
            ORCHESTRATOR,
            id='user-edit',
        ),
        pytest.param(
            '- SD-002 | source=user-menu | decision=x | binding=yes', 'rationale', ORCHESTRATOR, id='user-menu'
        ),
        pytest.param(
            '- SD-002 | source=user-override | decision=x | binding=yes', 'rationale', ORCHESTRATOR, id='user-override'
        ),
        pytest.param(
            '- SD-002 | source=materializer | decision=x | binding=yes', 'rationale', ORCHESTRATOR, id='materializer'
        ),
        pytest.param(
            '- SD-002 | source=implementation | supersedes=Invoices.void', 'reason', ORCHESTRATOR, id='implementation'
        ),
        pytest.param('- SD-002 | source=architect | decision=x | binding=yes', 'rationale', ARCHITECT, id='architect'),
        pytest.param(
            '- SD-002 | source=robot | decision=x | rationale=y | binding=yes', 'source', ARCHITECT, id='unknown'
        ),
        pytest.param('- SD-002 | decision=x | rationale=y | binding=yes', 'source', ARCHITECT, id='missing'),
    ],
)
def test_a_finding_on_a_settled_entry_belongs_to_whoever_writes_that_entry(
    entry: str, part: str, owner: FindingOwner
) -> None:
    phase = design(settled_design_decisions=lines(SD_001, entry))

    assert rows(check_phase_structure(phase)) == expected((C.SETTLED_ENTRY_MALFORMED, 'SD-002', part, owner))


def test_a_finding_on_a_research_requirements_line_belongs_to_the_orchestrator() -> None:
    phase = design(research_requirements=lines(RP_001, READ_LINE, RP_001))

    assert rows(check_phase_structure(phase)) == expected((C.DUPLICATE_ID, 'RP-001', '', ORCHESTRATOR))


# --- Readings beyond the tables (work item 2, "Subjects and parts where the tables are silent") ---


def test_a_module_layout_directory_written_without_a_trailing_slash_still_covers_its_files() -> None:
    phase = design(
        module_layout=lines('- `src/accounts` — owns account records', '- `src/billing.unit` — owns invoices')
    )

    assert rows(check_phase_structure(phase)) == []


def test_a_module_layout_with_no_readable_path_reports_no_seam_paths() -> None:
    phase = design(module_layout='Accounts and billing live under the source root.')

    assert rows(check_phase_structure(phase)) == []


def test_a_supersedes_value_quoted_inside_a_decision_settles_nothing() -> None:
    quoting = _accept('settled-entry-malformed - SD-### | source=implementation | supersedes=OD-002 [reason] — x')
    phase = design(settled_design_decisions=lines(SD_001, quoting))

    assert rows(check_phase_structure(phase)) == []


def test_an_unclosed_fence_in_one_section_never_hides_definitions_in_another() -> None:
    phase = design(test_list=lines(CLEAN_FIELDS['test_list'], '```text', 'an example its author never closed'))

    assert rows(check_phase_structure(phase)) == []


def test_an_unclosed_fence_in_one_section_never_hides_references_in_another() -> None:
    phase = design(
        architecture=lines('Layered.', '```text', 'an example its author never closed'),
        collaboration_and_wiring='Invoices calls AccountStore, per OD-099.',
    )

    assert rows(check_phase_structure(phase)) == expected((C.DANGLING_REFERENCE, 'OD-099', '', ARCHITECT))


@pytest.mark.parametrize(
    'opener',
    [pytest.param('```x``` notes', id='backticks-after-the-run'), pytest.param('```a`b', id='backtick-in-the-info')],
)
def test_a_line_that_cannot_open_a_fence_hides_no_definition(opener: str) -> None:
    phase = design(
        open_design_decisions=lines(opener, CLEAN_FIELDS['open_design_decisions']),
        collaboration_and_wiring='Invoices calls AccountStore.save, per SD-001 and OD-002.',
    )

    assert rows(check_phase_structure(phase)) == []


def test_a_line_that_cannot_open_a_fence_hides_no_reference() -> None:
    phase = design(collaboration_and_wiring=lines('```x``` is inline code', 'Invoices follows OD-777.'))

    assert rows(check_phase_structure(phase)) == expected((C.DANGLING_REFERENCE, 'OD-777', '', ARCHITECT))


def test_a_line_that_cannot_open_a_fence_hides_no_module_layout_entry() -> None:
    phase = design(
        module_layout=lines(
            '- `src/accounts/` — owns account records', '```tree``` view', '- `src/billing.unit` — owns invoices'
        )
    )

    assert rows(check_phase_structure(phase)) == []


def test_a_line_that_cannot_open_a_fence_hides_no_test_list_bullet() -> None:
    defective = '- not a test entry'
    phase = design(test_list=lines('```x```', defective, CLEAN_FIELDS['test_list']))

    assert rows(check_phase_structure(phase)) == expected((C.TEST_ENTRY_WITHOUT_BEHAVIOR, defective, '', ARCHITECT))


def test_a_fence_opened_inside_a_list_item_still_hides_its_lines() -> None:
    phase = design(
        collaboration_and_wiring=lines(
            'Invoices calls AccountStore.save, per SD-001.', '- An example:', '    ```text', '    see OD-777', '    ```'
        )
    )

    assert rows(check_phase_structure(phase)) == []


def test_a_reference_anywhere_in_settled_design_decisions_is_never_reported() -> None:
    phase = design(settled_design_decisions=lines(SD_001, 'Settled after the OD-077 review.'))

    assert rows(check_phase_structure(phase)) == []


def test_a_best_practices_path_in_settled_design_decisions_is_never_returned() -> None:
    accept = _accept(
        '[mechanical] [Research Path Invalid - BLOCKING]: Path `.best-practices/session-cookies.md` does not exist'
    )
    architect_entry = (
        '- SD-003 | source=architect | decision=layer per .best-practices/layering.md | rationale=house style'
        ' | binding=yes'
    )
    phase = parsed_phase({'settled_design_decisions': lines(SD_001, accept, architect_entry)})

    assert cited(extract_cited_paths(phase)) == []


def test_a_constraint_path_under_best_practices_is_returned_once_as_a_constraint() -> None:
    phase = parsed_phase({'implementation_plan_references': '- Constraint: `.best-practices/layering.md` § "Rules"'})

    assert cited(extract_cited_paths(phase)) == [
        ('.best-practices/layering.md', CitedPathKind.CONSTRAINT.value, PLAN_REFERENCES)
    ]


def test_a_reference_in_the_frozen_overview_is_never_reported() -> None:
    markdown = phase_markdown(CLEAN_FIELDS).replace(
        'Issue invoices for saved accounts.', 'Issue invoices for saved accounts, per OD-077.'
    )
    assert 'OD-077' in markdown

    assert rows(check_phase_structure(Phase.parse_markdown(markdown))) == []


def test_a_section_whose_name_overlaps_reports_the_overlap_but_nothing_it_copied() -> None:
    phase = design(
        settled_design_decisions=SD_001.replace('rationale=simpler', 'rationale=simpler than OD-077'),
        extra_sections=(('Decisions', 'Notes on the decisions.'),),
    )
    assert 'OD-077' in (phase.additional_sections or {}).get('Decisions', '')

    assert rows(check_phase_structure(phase)) == expected((C.SECTION_NAME_OVERLAP, 'Decisions', '', ARCHITECT))


@pytest.mark.parametrize(
    ('check', 'subject', 'accepted_subject'),
    [
        pytest.param(C.DANGLING_REFERENCE, 'OD-1', 'OD-12', id='longer-id'),
        pytest.param(C.SEAM_PATH_NOT_IN_MODULE_LAYOUT, 'src/ledger', 'src/ledger.unit', id='longer-path'),
    ],
)
def test_accepting_a_finding_never_hides_one_whose_key_is_a_prefix_of_the_accepted_key(
    check: StructuralCheck, subject: str, accepted_subject: str
) -> None:
    unaccepted = finding(check, subject)
    phase = design(settled_design_decisions=lines(SD_001, _accept(f'{check.value} {accepted_subject} — x')))

    assert drop_accepted_findings([unaccepted], phase) == ([unaccepted], [])


def test_a_checklist_item_whose_verify_group_never_closes_is_reported() -> None:
    item = '- [x] Issue invoices (Step 2) (verify: run-checks invoices'

    assert implementation_findings(implementation({STEP_2_ITEM: item})) == expected(
        (C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', ARCHITECT)
    )


def test_a_malformed_step_heading_that_carries_a_number_is_not_also_a_dangling_step() -> None:
    markdown = implementation(
        {
            STEP_2_BLOCK_END: lines(STEP_2_BLOCK_END, '', '#### Step 3 Reports'),
            STEP_2_ITEM: lines(STEP_2_ITEM, '- [ ] Render reports (Step 3) (verify: run-checks reports)'),
        }
    )

    assert implementation_findings(markdown) == expected(
        (C.IMPLEMENTATION_STEP_HEADING_MALFORMED, '#### Step 3 Reports', '', ARCHITECT)
    )


def test_steps_holding_only_malformed_headings_report_only_the_headings() -> None:
    steps = lines('## Build Order', '### Steps', '#### Step one: Accounts')
    markdown = lines(IMPLEMENTATION_TITLE, steps, POLICY_SECTION, EMPTY_CHECKLIST_SECTION)

    assert implementation_findings(markdown) == expected(
        (C.IMPLEMENTATION_STEP_HEADING_MALFORMED, '#### Step one: Accounts', '', ARCHITECT)
    )


@pytest.mark.parametrize(
    ('architecture', 'mentions'),
    [
        pytest.param('See .best-practices/layering.md, then build.', ['.best-practices/layering.md'], id='punctuation'),
        pytest.param('See docs/.best-practices/layering.md first.', [], id='under-another-directory'),
        pytest.param('See .best-practices/layering.mdz first.', [], id='longer-suffix'),
        pytest.param(lines('Layered.', '```text', 'cat .best-practices/layering.md', '```'), [], id='fenced'),
    ],
)
def test_a_best_practices_mention_is_a_delimited_run_ending_in_the_markdown_suffix(
    architecture: str, mentions: list[str]
) -> None:
    phase = parsed_phase({'architecture': architecture})

    assert cited(extract_cited_paths(phase)) == sorted(
        (mention, CitedPathKind.BEST_PRACTICES.value, 'System Design > Architecture') for mention in mentions
    )


# --- Robustness: no input makes a check raise --------------------------------------------------


TEXT_FIELDS = tuple(name for name, header_path in Phase.HEADER_FIELD_MAPPING.items() if header_path[0] != 'Metadata')
LONG_DIGITS = '9' * 5000
LINE_SEPARATOR = chr(0x2028)
NAME_FRAGMENTS = (
    'Design',
    'Shape',
    'Meta',
    ' ',
    '|',
    '`',
    '#',
    'Implementation',
    'é',
    '日本',
    '\U0001f600',
    'Notes',
    '',
    '\t',
)
LINE_FRAGMENTS = (
    *NAME_FRAGMENTS,
    '- ',
    '  - ',
    '* ',
    '+ ',
    '```',
    '~~~',
    '````',
    ' :: ',
    '::',
    ' | ',
    '|',
    'OD-',
    'SD-',
    'SD-###',
    'CQ-',
    'RP-',
    'FLOW-',
    '1',
    '003',
    LONG_DIGITS,
    'source=',
    'supersedes=',
    'decision=',
    'rationale=',
    'binding=',
    'user',
    'implementation',
    'unresolved-checks',
    '(verify:',
    '(Step ',
    '(',
    ')',
    '[',
    ']',
    '<',
    '>',
    '#### Step ',
    '## ',
    '### ',
    '- [ ] ',
    '- [x] ',
    'None',
    'Option A:',
    'Option D:',
    'Recommended:',
    'title:',
    'Read: ',
    'Constraint: ',
    '§',
    '.best-practices/',
    '.md',
    ' — ',
    '\r',
    LINE_SEPARATOR,
    '\x85',
    '\x00',
    'TODO',
    'ask user',
)


def _garbled_text(rng: random.Random) -> str:
    return '\n'.join(
        ''.join(rng.choice(LINE_FRAGMENTS) for _ in range(rng.randint(0, 14))) for _ in range(rng.randint(0, 30))
    )


def _garbled_phase(rng: random.Random) -> Phase:
    sections = {
        ''.join(rng.choice(NAME_FRAGMENTS) for _ in range(rng.randint(0, 3))): _garbled_text(rng) for _ in range(4)
    }
    return Phase.model_validate(
        {'phase_name': 'garbled', **{name: _garbled_text(rng) for name in TEXT_FIELDS}, 'additional_sections': sections}
    )


def _assert_one_line_findings(findings: list[StructuralFinding]) -> None:
    for each in findings:
        assert each.detail.strip()
        assert '\n' not in each.detail
        assert '\n' not in each.subject


def _run_every_check(phase: Phase, markdown: str) -> None:
    structural = check_phase_structure(phase)
    implementation_side = check_implementation_structure(markdown, phase)
    paths = extract_cited_paths(phase)
    kept, accepted = drop_accepted_findings([*structural, *implementation_side], phase)

    _assert_one_line_findings([*structural, *implementation_side])
    assert all(isinstance(path, CitedPath) for path in paths)
    assert len(kept) + len(accepted) == len(structural) + len(implementation_side)


@pytest.mark.parametrize('seed', range(80))
def test_no_garbled_document_makes_a_check_raise(seed: int) -> None:
    rng = random.Random(seed)

    _run_every_check(_garbled_phase(rng), _garbled_text(rng))


EXTREME_PHASE_FIELDS = [
    pytest.param({'collaboration_and_wiring': f'per OD-{LONG_DIGITS} and SD-{LONG_DIGITS}'}, id='long-id-references'),
    pytest.param(
        {
            'open_design_decisions': lines(
                f'- OD-{LONG_DIGITS} | Huge', OPTION_A, OPTION_B, RECOMMENDED, f'- OD-0{LONG_DIGITS} | Again'
            )
        },
        id='long-id-definitions',
    ),
    pytest.param(
        {'settled_design_decisions': f'- SD-{LONG_DIGITS} | source=user | supersedes=OD-{LONG_DIGITS} | decision=x'},
        id='long-id-settled-entry',
    ),
    pytest.param({'skeleton_index': '- `' + 'a' * 200_000 + '` :: ' + 'b' * 200_000}, id='huge-seam-line'),
    pytest.param({'skeleton_index': '- `src/x` :: a(' + ') ' * 100_000}, id='many-closing-parentheses'),
    pytest.param(
        {'module_layout': ' ' * 200_000, 'skeleton_index': '- ' + ' ' * 200_000 + ' :: x'}, id='whitespace-runs'
    ),
    pytest.param({'test_list': '- `' + ':' * 200_000 + '`'}, id='colon-run'),
    pytest.param({'open_design_decisions': lines(OD_ENTRY, *(['  - Option A: x'] * 20_000))}, id='many-options'),
    pytest.param({'open_design_decisions': '- OD-1 | ' + '| Option A:' * 50_000}, id='bar-run'),
    pytest.param({'collaboration_and_wiring': lines('```', '~~~', '````', 'OD-404', '`' * 3)}, id='interleaved-fences'),
    pytest.param(
        {'architecture': ('.best-practices/' + 'x' * 100) * 2_000 + ' .best-practices/' + '.md' * 50_000},
        id='mention-runs',
    ),
    pytest.param({'research_requirements': '- Read: ' + '`' * 100_001}, id='backtick-run'),
    pytest.param({'implementation_plan_references': '- Constraint: `' + '§' * 100_000 + '`'}, id='qualifier-run'),
    pytest.param(
        {'design_shape_additional': lines(f'- FLOW-{LONG_DIGITS}: x', f'- FLOW-{LONG_DIGITS}: y')}, id='long-flow-ids'
    ),
]
EXTREME_PLANS = [
    pytest.param('', id='empty'),
    pytest.param('#' * 100_000, id='hash-run'),
    pytest.param(
        lines('## Build Order', '### Steps', f'#### Step {LONG_DIGITS}: Huge', f'#### Step 0{LONG_DIGITS}: Again'),
        id='long-step-numbers',
    ),
    pytest.param(
        lines('## Checklist', f'- [ ] x (Step {LONG_DIGITS}) (verify: ' + '(' * 100_000), id='unclosed-nesting'
    ),
    pytest.param(lines('## Checklist', '- [ ] x (Step 1) ' + '(verify: a) ' * 20_000), id='many-verify-groups'),
    pytest.param(lines('## Checklist', '- [ ] x (Step 1) (verify:' + ')' * 100_000), id='closing-run'),
    pytest.param(lines('## Checklist', '- [ ] x (Step 1) (verify: <' + ' ' * 200_000 + 'x'), id='unclosed-placeholder'),
    pytest.param(lines('```', '## Checklist', '- [ ] not an item'), id='unclosed-fence'),
    pytest.param('## ' + ' ' * 200_000 + '#', id='whitespace-heading'),
]


@pytest.mark.parametrize('fields', EXTREME_PHASE_FIELDS)
def test_no_extreme_phase_section_makes_a_check_raise(fields: dict[str, str]) -> None:
    _run_every_check(Phase.model_validate({'phase_name': 'extreme', **fields}), CLEAN_IMPLEMENTATION)


@pytest.mark.parametrize('markdown', EXTREME_PLANS)
def test_no_extreme_implementation_plan_makes_a_check_raise(markdown: str) -> None:
    _run_every_check(design(), markdown)


@pytest.mark.parametrize(
    'subject',
    ['(.*)+[a-z]?\\', '- [ ] (Step 1) (verify: TODO)', '$^|\\1', ''],
    ids=['regex-metacharacters', 'checklist-item', 'anchors-and-backreference', 'empty'],
)
def test_dropping_accepted_findings_treats_a_key_as_plain_text(subject: str) -> None:
    quoted = finding(C.DANGLING_REFERENCE, subject)
    other = finding(C.DANGLING_REFERENCE, 'OD-9')
    phase = design(settled_design_decisions=lines(SD_001, _accept(f'dangling-reference {subject} — x')))

    assert drop_accepted_findings([quoted, other], phase) == ([other], [f'accepted: dangling-reference {subject}'])
