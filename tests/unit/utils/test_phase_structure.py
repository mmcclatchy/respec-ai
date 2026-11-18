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
from collections.abc import Callable
from pathlib import Path

import pytest
from fastmcp import FastMCP

from src.mcp.tools.document_tools import register_document_tools
from src.models.document_validation import CitedPath, CitedPathKind, FindingOwner, StructuralCheck, StructuralFinding
from src.models.enums import ShapeGate
from src.models.phase import Phase
from src.platform.templates.phase_contract_grammar import BRIEF_SECTION_PLACEHOLDERS, IMPLEMENTATION_BRIEF_EXAMPLE
from src.utils.language_extensions import EXTENSION_TO_LANGUAGE
from src.utils.materializers import _MATERIALIZER_MAP
from src.utils.phase_structure import (
    check_implementation_structure,
    check_phase_structure,
    drop_accepted_findings,
    extract_cited_paths,
    extract_implementation_paths,
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


DELEGATION_BOUNDS = lines(
    '### Out of scope',
    '- Refunds and credit notes.',
    "### Implementer's discretion",
    '- Internal names inside the billing module.',
    '### Escalate if',
    '- An invoice would be issued for an account that is not saved.',
)


def phase_markdown(
    fields: dict[str, str], extra_sections: tuple[tuple[str, str], ...] = (), delegation_bounds: bool = True
) -> str:
    document = ['# Phase: sample-phase', '', *OVERVIEW]
    # Ahead of the typed sections, so an unclosed fence in one of them cannot swallow it.
    if delegation_bounds and all(name != 'Delegation Bounds' for name, _ in extra_sections):
        document.extend(['## Delegation Bounds', DELEGATION_BOUNDS])
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


def parsed_phase(
    fields: dict[str, str], extra_sections: tuple[tuple[str, str], ...] = (), delegation_bounds: bool = True
) -> Phase:
    return Phase.parse_markdown(phase_markdown(fields, extra_sections, delegation_bounds))


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
        '- `tests/billing_check.unit::issues one invoice per order` — T-1',
        '- `tests/accounts_check.unit::saves a new account` — the happy path — T-2',
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


def design(extra_sections: tuple[tuple[str, str], ...] = (), delegation_bounds: bool = True, **overrides: str) -> Phase:
    fields = {**CLEAN_FIELDS, **overrides}
    return parsed_phase(
        {name: content for name, content in fields.items() if content}, extra_sections, delegation_bounds
    )


def rows(findings: list[StructuralFinding]) -> list[Row]:
    return sorted((f.check.value, f.subject, f.part, f.owner.value) for f in findings)


def expected(*entries: ExpectedRow) -> list[Row]:
    return sorted((check.value, subject, part, owner.value) for check, subject, part, owner in entries)


def cited(paths: list[CitedPath]) -> list[tuple[str, str, str]]:
    return sorted((p.path, p.kind.value, p.cited_in) for p in paths)


IMPLEMENTATION_TITLE = '# Implementation Plan: sample-phase'
STEP_2_GOAL = '- **Goal:** Issue invoices once accounts persist, per SD-001 and OD-002.'
STEP_2_BLOCK_END = '- **Depends on:** Step 1'
STEPS_SECTION = lines(
    '## Build Order',
    '### Steps',
    '#### Step 1: Account Store',
    '- **Goal:** Persist accounts before anything bills them.',
    '- **Files:** create `src/accounts/store.unit`',
    '- **Depends on:** none',
    '',
    '#### Step 2: Invoices',
    STEP_2_GOAL,
    '- **Files:** create `src/billing.unit`',
    STEP_2_BLOCK_END,
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
STEP_3_DRAFT = lines(
    '#### Step 3: Reports',
    '- **Goal:** Report on issued invoices.',
    '- **Files:** create `src/reports.unit`',
    '- **Depends on:** Step 2',
)


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
            'test_list': '- `tests/accounts_check::registers a new account` — T-1',
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
            'test_list': '- `tests/accounts_check::finds an account` — T-1',
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
            'test_list': '- `tests/accounts_check::finds an account` — T-1',
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
    phase = design(test_list=lines('- `tests/accounts_check.unit::saves a new account` — T-1', defective))

    assert rows(check_phase_structure(phase)) == expected((C.TEST_ENTRY_WITHOUT_BEHAVIOR, defective, '', ARCHITECT))


def test_text_after_a_test_list_entry_is_allowed() -> None:
    phase = design(test_list='- `tests/billing_check.unit::issues one invoice per order` (the core seam, SD-001) — T-1')

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
    test_list = lines('```text', '- `tests/billing_check.unit::issues one invoice per order` — T-1', '```')
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
    markdown = implementation({STEP_2_GOAL: STEP_2_GOAL.replace('OD-002', 'OD-042')})

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
    markdown = implementation({STEP_2_BLOCK_END: lines(STEP_2_BLOCK_END, '', STEP_3_DRAFT)})

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


# Phase 4 re-pointed both taught-example tests to brief_phase(), which defines the T, SC and G IDs and
# the Skeleton Index paths the example cites; against design() the brief checks would report those as
# dangling. The example's step Verify and Exit criteria commands are placeholders too, so making it
# concrete replaces every [commands] placeholder, and leaving them in is reported on each of them.
def test_the_taught_implementation_plan_passes_once_its_verify_placeholders_are_concrete_commands() -> None:
    assert BRIEF_IMPLEMENTATION != IMPLEMENTATION_BRIEF_EXAMPLE

    assert rows(check_implementation_structure(BRIEF_IMPLEMENTATION, brief_phase())) == []


def test_the_taught_implementation_plan_with_its_placeholders_left_in_is_reported_on_every_item() -> None:
    placeholder_items = [line for line in IMPLEMENTATION_BRIEF_EXAMPLE.splitlines() if '(verify: <' in line]
    placeholder_verify_steps = re.findall(r'^#### Step ([0-9]+):', IMPLEMENTATION_BRIEF_EXAMPLE, flags=re.MULTILINE)
    exit_commands = ['<each [commands] value that verifies the whole phase>']
    assert len(placeholder_items) == len(placeholder_verify_steps) == 3
    assert f'`{exit_commands[0]}`' in IMPLEMENTATION_BRIEF_EXAMPLE

    assert rows(check_implementation_structure(IMPLEMENTATION_BRIEF_EXAMPLE, brief_phase())) == expected(
        *((C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', ARCHITECT) for item in placeholder_items),
        *(
            (C.IMPLEMENTATION_COMMAND_PLACEHOLDER, f'Step {step}', 'Verify', FINALIZER)
            for step in placeholder_verify_steps
        ),
        *((C.IMPLEMENTATION_COMMAND_PLACEHOLDER, 'Exit criteria', command, FINALIZER) for command in exit_commands),
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
                f'- `tests/billing_check{extension}::issues one invoice per order` — T-1',
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
        '- `tests/billing_check::refunds an invoice` — T-7',
    ),
    'success_criteria': '- Invoices issue within a day',
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
CORPUS_PHASE_SECTIONS = (
    ('Implementation Notes', 'Notes that shadow the implementation section.'),
    ('Grounding', lines('### Build on', '- `src/billing` — extend: issue invoices — informs: Step 1')),
)
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
    lines(
        IMPLEMENTATION_TITLE,
        '## Build Order',
        '### Steps',
        '#### Step 1: Invoices',
        '- **Goal:** Issue invoices.',
        '- **Context:** SD-001',
        '- **Files:** create the billing module',
        '- **Depends on:** Step 9',
        '- **Tests to turn green:** none — checked by hand',
        '- **Verify:** `TODO`',
        '- **Done when:** an invoice is issued.',
        POLICY_SECTION,
        '## Checklist',
        '- [ ] Issue invoices (Step 1) (verify: run-checks invoices)',
        '## Deviations',
        '- None',
    ),
)


def biased_details(findings: list[StructuralFinding]) -> list[tuple[str, list[Hit]]]:
    return [(finding.detail, hits) for finding in findings if (hits := scan(finding.detail))]


def test_the_findings_corpus_triggers_every_check_and_every_detail_is_a_language_neutral_line() -> None:
    corpus_phase = parsed_phase(CORPUS_PHASE_FIELDS, CORPUS_PHASE_SECTIONS)
    corpus_text = '\n'.join(
        [
            phase_markdown(CORPUS_PHASE_FIELDS, CORPUS_PHASE_SECTIONS),
            phase_markdown(CORPUS_EMPTY_TEST_LIST_FIELDS, delegation_bounds=False),
            *CORPUS_IMPLEMENTATIONS,
        ]
    )
    assert scan(corpus_text) == [], 'the corpus itself must be language-neutral'

    findings = [
        *check_phase_structure(corpus_phase),
        *check_phase_structure(parsed_phase(CORPUS_EMPTY_TEST_LIST_FIELDS, delegation_bounds=False)),
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
            (('Rollout', 'Rule one.'), ('Rollout Notes', 'Rule two.')),
            ['Rollout', 'Rollout Notes'],
            id='two-additional-sections-shorter-first',
        ),
        pytest.param(
            (('Rollout Notes', 'Rule two.'), ('Rollout', 'Rule one.')),
            ['Rollout', 'Rollout Notes'],
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


BRIEF_SECTIONS_HOLDING_NONE: dict[str, str] = {
    'Grounding': lines(
        '### Build on',
        '- None',
        '### Leave alone',
        '- None',
        '### Exemplars',
        '- None',
        '### Conventions',
        '- None',
        '### Research to read',
        '- `.best-practices/invoice-numbering.md` — informs: OD-002',
    ),
    'Delegation Bounds': DELEGATION_BOUNDS,
    'Behaviors & Acceptance': lines(
        '- Objective: issue invoices for saved accounts → tests: T-1, T-2', '### Not covered by tests', '- None'
    ),
    'Guardrails': lines(
        '### Invariants',
        '- None',
        '### Error policy',
        '- None',
        '### Security and performance',
        '- None',
        '### Deviation protocol',
        '- None',
    ),
}


def test_additional_sections_with_distinct_names_pass() -> None:
    extra_sections = (*BRIEF_SECTIONS_HOLDING_NONE.items(), ('Evolution Log', 'Content.'))

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
    'Grounding',
    'Guardrails',
    'Delegation Bounds',
    'Behaviors & Acceptance',
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
    '- **Goal:** ',
    '- **Context:** ',
    '- **Files:** ',
    '- **Depends on:** ',
    '- **Tests to turn green:** ',
    '- **Verify:** ',
    '- **Done when:** ',
    'create ',
    'modify ',
    ';',
    'Step 1',
    'T-',
    'SC-',
    'G-',
    'affects=',
    'measure:',
    '## Start here',
    '## Exit criteria',
    '## Deviations',
    '### Research to read',
    '### Out of scope',
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
    paths = [*extract_cited_paths(phase), *extract_implementation_paths(markdown)]
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


def _dependency_chain(count: int, closes: bool) -> str:
    last = 1 if closes else count + 1
    steps = (
        lines(
            f'#### Step {number}: Step {number}',
            '- **Goal:** g',
            f'- **Files:** create `p{number}`',
            f'- **Depends on:** Step {number + 1 if number < count else last}',
        )
        for number in range(1, count + 1)
    )
    return lines('## Build Order', '### Steps', *steps)


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
    pytest.param(_dependency_chain(3_000, closes=True), id='long-dependency-cycle'),
    pytest.param(_dependency_chain(3_000, closes=False), id='long-dependency-chain'),
    pytest.param(
        lines('## Build Order', '### Steps', '#### Step 1: Wide', '- **Depends on:** ' + 'Step 1, ' * 20_000),
        id='wide-dependency-list',
    ),
    pytest.param(
        lines('## Build Order', '### Steps', '#### Step 1: Odd', '- **Verify:** `<a' + ' b' * 100_000 + '`'),
        id='unclosed-angle-token',
    ),
    pytest.param(
        lines('## Build Order', '### Steps', '#### Step 1: Odd', '- **Files:** ' + 'create `x`; ' * 20_000),
        id='many-files',
    ),
    pytest.param(lines('## Exit criteria', '`' * 100_001), id='exit-criteria-backtick-run'),
]


MALFORMED_BRIEF_PLANS = [
    pytest.param(
        lines('## Build Order', '### Steps', '#### Step two: Cache', '- **Goal:** g', '- **Depends on:** Step 1'),
        C.IMPLEMENTATION_STEP_HEADING_MALFORMED,
        id='non-integer-step-number',
    ),
    pytest.param(
        lines('## Build Order', '### Steps', '#### Step 1: Cache', '#### Step 2: List'),
        C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE,
        id='steps-with-no-fields',
    ),
    pytest.param(
        lines('## Start here', '- Read the brief.', '## Build Order', '### Steps', '#### Step 1: Cache'),
        C.IMPLEMENTATION_FINALIZE_SECTION_MISSING,
        id='finalize-sections-missing',
    ),
    pytest.param(
        lines('## Build Order', '### Steps', '#### Step 1: Cache', '- **Depends on:** Step 1, Step one, Step'),
        C.IMPLEMENTATION_DEPENDENCY_INVALID,
        id='garbled-dependencies',
    ),
]


@pytest.mark.parametrize(('markdown', 'check'), MALFORMED_BRIEF_PLANS)
def test_a_malformed_brief_is_reported_as_a_finding_never_raised(markdown: str, check: StructuralCheck) -> None:
    findings = check_implementation_structure(markdown, brief_phase())

    _assert_one_line_findings(findings)
    assert check in {finding.check for finding in findings}


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


# --- Phase 4: the brief checks (docs/phase-cooperative/phase-4-agent-ready-brief.md, Scope 5) ----
#
# Two baselines, each asserted clean. The design-review stage is design() with CLEAN_IMPLEMENTATION:
# Delegation Bounds present, the finalizer's sections absent, draft-only steps. The finalized brief
# is brief_phase() with BRIEF_IMPLEMENTATION: the brief sections the agents are shown, verbatim, the
# definitions they cite, and the implementation example with its placeholder commands made concrete.

FINALIZER = FindingOwner.FINALIZER
LocatedRow = tuple[str, str, str, str, str]

BRIEF_SD_001 = (
    '- SD-001 | source=user | supersedes=OD-001 | decision=Option A | rationale=simpler | rejected=Option B'
    ' | affects=Step 1, G-1 | binding=yes'
)
BRIEF_SD_002 = (
    '- SD-002 | source=user | supersedes=CQ-001 | decision=Option B | rationale=cheaper reads'
    ' | rejected=Option A | affects=Step 2 | binding=yes'
)
RP_002 = (
    '- RP-002 | Which cache policy suits repeated queries? | informs: SD-2 | Technologies: caching;'
    ' Topics: invalidation; Query: a cache in front of a repository | tier: synthesis-only [approved]'
)
BRIEF_READ_LINE = '- Read: `.best-practices/<file>.md` — informs: SD-2 — Source: RP-002'
BRIEF_FIELDS: dict[str, str] = {
    'module_layout': lines(
        '- `<path to the repository query module>` — owns queries',
        '- `<path to the cache module>` — owns cached results',
        '- `<path to the result list component>` — owns the result list',
    ),
    'skeleton_index': lines(
        '- `<path to the repository query module>` :: Repository.query(query: Query) -> Rows',
        '- `<path to the cache module>` :: QueryCache.get(query: Query) -> Rows',
        '- `<path to the result list component>` :: ResultList.render(rows: Rows) -> View',
    ),
    'collaboration_and_wiring': 'The service asks QueryCache.get, which falls back to Repository.query, per SD-001.',
    'test_list': lines(
        '- `<path to the query test file>::returns the rows a query matches` — T-1',
        '- `<path to the query test file>::returns no rows for an unmatched query` — T-2',
        '- `<path to the cache test file>::serves a repeated query from the cache` — T-3',
        '- `<path to the result list test file>::renders one item per row` — T-4',
    ),
    'design_shape_additional': lines('#### Design Narrative', 'A cache sits in front of the repository query path.'),
    'settled_design_decisions': lines(BRIEF_SD_001, BRIEF_SD_002),
    'research_requirements': lines(RP_002, BRIEF_READ_LINE),
    'success_criteria': lines(
        '- SC-1: a query returns exactly the rows it matches — measure: T-1 and T-2 pass',
        '- SC-2: results render as a list — measure: T-4 passes',
        '- SC-3: a repeated query never reaches the repository — measure: T-3 passes',
    ),
}
GROUNDING = BRIEF_SECTION_PLACEHOLDERS['Grounding']
BOUNDS = BRIEF_SECTION_PLACEHOLDERS['Delegation Bounds']
BEHAVIORS = BRIEF_SECTION_PLACEHOLDERS['Behaviors & Acceptance']
GUARDRAILS = BRIEF_SECTION_PLACEHOLDERS['Guardrails']
FINALIZER_SECTIONS_ABSENT = {'Grounding': '', 'Behaviors & Acceptance': '', 'Guardrails': ''}


def brief_markdown(sections: dict[str, str] | None = None, **overrides: str) -> str:
    fields = {**BRIEF_FIELDS, **overrides}
    brief = {**BRIEF_SECTION_PLACEHOLDERS, **(sections or {})}
    return phase_markdown(
        {name: content for name, content in fields.items() if content},
        tuple((name, body) for name, body in brief.items() if body),
        delegation_bounds=False,
    )


def brief_phase(sections: dict[str, str] | None = None, **overrides: str) -> Phase:
    return Phase.parse_markdown(brief_markdown(sections, **overrides))


def with_h3(markdown: str, h3: str, body: str) -> str:
    return _replace_h3(markdown, h3, [f'### {h3}', *body.splitlines()])


def without_h3(markdown: str, h3: str) -> str:
    return _replace_h3(markdown, h3, [])


def _replace_h3(markdown: str, h3: str, replacement: list[str]) -> str:
    heading = f'### {h3}'
    assert heading in markdown.splitlines(), f'fixture anchor missing: {heading!r}'
    kept: list[str] = []
    in_target = False
    for line in markdown.splitlines():
        if line.startswith(('## ', '### ')):
            in_target = line == heading
            if in_target:
                kept.extend(replacement)
                continue
        if not in_target:
            kept.append(line)
    return '\n'.join(kept) + '\n'


def without_h2(markdown: str, *names: str) -> str:
    headings = {f'## {name}' for name in names}
    assert headings <= set(markdown.splitlines()), f'fixture anchor missing: {headings!r}'
    kept: list[str] = []
    dropping = False
    for line in markdown.splitlines():
        if line.startswith('## '):
            dropping = line in headings
        if not dropping:
            kept.append(line)
    return '\n'.join(kept) + '\n'


BRIEF_IMPLEMENTATION = re.sub(r'<[^<>]*\[commands\][^<>]*>', 'run-checks all', IMPLEMENTATION_BRIEF_EXAMPLE)
STEP_3_END = '- **Done when:** T-4 passes.'
STEP_3_ITEM = '- [ ] Implement the result list (Step 3) (verify: run-checks all)'
STEP_2_ITEM_BRIEF = '- [ ] Add the cache layer (Step 2) (verify: run-checks all)'
STEP_2_VERIFY = '- **Tests to turn green:** T-3\n- **Verify:** `run-checks all`'
STEP_2_DEPENDS = '- **Depends on:** Step 1\n- **Tests to turn green:** T-3'
STEP_3_DEPENDS = '- **Depends on:** Step 1\n- **Tests to turn green:** T-4'
EXIT_COMMAND_LINE = '- `run-checks all` passes'
EXPORT_PATH = '<path to the export module>'
EXPORT_GOAL = '- **Goal:** Results export to a file.'
EXPORT_FILES = f'- **Files:** create `{EXPORT_PATH}`'
DRAFT_STEP_FIELDS = (EXPORT_GOAL, EXPORT_FILES, '- **Depends on:** Step 1')
FINALIZED_STEP_FIELDS = (
    EXPORT_GOAL,
    '- **Context:** SD-1',
    EXPORT_FILES,
    '- **Depends on:** Step 1',
    '- **Tests to turn green:** none — the export is checked by hand',
    '- **Verify:** `run-checks all`',
    '- **Done when:** an export holds one row per result.',
)
EVICTION_ENTRY = '- `<path to the cache test file>::evicts a stale entry`'
OPEN_OD_003 = lines('- OD-003 | Cache size', OPTION_A, OPTION_B, RECOMMENDED)


def brief_plan(replace: dict[str, str] | None = None) -> str:
    text = BRIEF_IMPLEMENTATION
    for old, new in (replace or {}).items():
        assert text.count(old) == 1, f'fixture anchor must occur once: {old!r}'
        text = text.replace(old, new)
    return text


def with_step(number: int, *fields: str) -> dict[str, str]:
    return {
        STEP_3_END: lines(STEP_3_END, '', f'#### Step {number}: Export', *fields),
        STEP_3_ITEM: lines(STEP_3_ITEM, f'- [ ] Export the results (Step {number}) (verify: run-checks all)'),
    }


def step_2_verify(value: str) -> dict[str, str]:
    return {STEP_2_VERIFY: f'- **Tests to turn green:** T-3\n- **Verify:** {value}'}


def brief_findings(markdown: str = BRIEF_IMPLEMENTATION, phase: Phase | None = None) -> list[Row]:
    return rows(check_implementation_structure(markdown, phase or brief_phase()))


def located(findings: list[StructuralFinding]) -> list[LocatedRow]:
    return sorted((f.check.value, f.location, f.subject, f.part, f.owner.value) for f in findings)


def test_the_finalized_brief_baseline_reports_no_findings() -> None:
    assert '[commands]' not in BRIEF_IMPLEMENTATION
    phase = brief_phase()

    assert rows(check_phase_structure(phase)) == []
    assert rows(check_implementation_structure(BRIEF_IMPLEMENTATION, phase)) == []


def test_a_document_holding_no_brief_section_reports_no_brief_finding_during_design_review() -> None:
    design_review = design()
    assert set(design_review.additional_sections or {}) == {'Delegation Bounds'}

    assert rows(check_phase_structure(parsed_phase({}, delegation_bounds=False))) == []
    assert rows(check_phase_structure(design_review)) == []
    assert implementation_findings(CLEAN_IMPLEMENTATION) == []


# --- Phase 4, B5: a partially written brief is a structural finding, never content loss ----------


@pytest.mark.parametrize(
    ('sections', 'expected_rows'),
    [
        pytest.param(
            {'Delegation Bounds': ''},
            [(C.DELEGATION_BOUNDS_INCOMPLETE, 'Delegation Bounds', '', ARCHITECT)],
            id='delegation-bounds-absent',
        ),
        pytest.param(
            {'Delegation Bounds': without_h3(BOUNDS, 'Escalate if')},
            [(C.DELEGATION_BOUNDS_INCOMPLETE, 'Delegation Bounds', 'Escalate if', ARCHITECT)],
            id='delegation-bounds-subsection-missing',
        ),
        pytest.param(
            {'Delegation Bounds': with_h3(BOUNDS, 'Out of scope', '')},
            [(C.DELEGATION_BOUNDS_INCOMPLETE, 'Delegation Bounds', 'Out of scope', ARCHITECT)],
            id='delegation-bounds-subsection-empty',
        ),
        pytest.param(
            {'Grounding': '', 'Guardrails': ''},
            [
                (C.BRIEF_SECTION_INCOMPLETE, 'Grounding', '', FINALIZER),
                (C.BRIEF_SECTION_INCOMPLETE, 'Guardrails', '', FINALIZER),
            ],
            id='one-finalizer-section-present',
        ),
        pytest.param(
            {'Behaviors & Acceptance': ''},
            [(C.BRIEF_SECTION_INCOMPLETE, 'Behaviors & Acceptance', '', FINALIZER)],
            id='two-finalizer-sections-present',
        ),
        pytest.param(
            {'Guardrails': without_h3(GUARDRAILS, 'Deviation protocol')},
            [(C.BRIEF_SECTION_INCOMPLETE, 'Guardrails', 'Deviation protocol', FINALIZER)],
            id='finalizer-subsection-missing',
        ),
        pytest.param(
            {'Grounding': with_h3(GROUNDING, 'Leave alone', '')},
            [(C.BRIEF_SECTION_INCOMPLETE, 'Grounding', 'Leave alone', FINALIZER)],
            id='finalizer-subsection-empty',
        ),
        pytest.param(
            {'Behaviors & Acceptance': without_h3(BEHAVIORS, 'Not covered by tests')},
            [(C.BRIEF_SECTION_INCOMPLETE, 'Behaviors & Acceptance', 'Not covered by tests', FINALIZER)],
            id='traceability-subsection-missing',
        ),
    ],
)
def test_a_partially_written_brief_is_a_structural_finding_never_content_loss(
    sections: dict[str, str], expected_rows: list[ExpectedRow]
) -> None:
    markdown = brief_markdown(sections)

    assert Phase.find_content_loss(markdown) == []
    assert rows(check_phase_structure(Phase.parse_markdown(markdown))) == expected(*expected_rows)


def test_an_empty_brief_subsection_holding_exactly_none_passes() -> None:
    sections = {
        'Grounding': with_h3(GROUNDING, 'Leave alone', '- None'),
        'Delegation Bounds': with_h3(BOUNDS, 'Escalate if', '- None'),
        'Behaviors & Acceptance': with_h3(BEHAVIORS, 'Not covered by tests', '- None'),
        'Guardrails': with_h3(GUARDRAILS, 'Security and performance', '- None'),
    }

    assert rows(check_phase_structure(brief_phase(sections))) == []


# --- Phase 4, B7 (phase.md): every ID resolves and every contract item has an owner ---------------


@pytest.mark.parametrize(
    ('entry', 'expected_row'),
    [
        pytest.param(EVICTION_ENTRY, (C.TEST_ENTRY_WITHOUT_ID, EVICTION_ENTRY, '', ARCHITECT), id='no-id'),
        pytest.param(
            f'{EVICTION_ENTRY} — not numbered yet',
            (C.TEST_ENTRY_WITHOUT_ID, f'{EVICTION_ENTRY} — not numbered yet', '', ARCHITECT),
            id='trailing-text-but-no-id',
        ),
        pytest.param(
            '- `<path to the cache test file>::evicts a stale entry — T-5`',
            (C.TEST_ENTRY_WITHOUT_ID, '- `<path to the cache test file>::evicts a stale entry — T-5`', '', ARCHITECT),
            id='id-inside-the-backticks',
        ),
        pytest.param(f'{EVICTION_ENTRY} — T-3', (C.DUPLICATE_ID, 'T-3', '', ARCHITECT), id='duplicate-id'),
        pytest.param(f'{EVICTION_ENTRY} — T-03', (C.DUPLICATE_ID, 'T-03', '', ARCHITECT), id='duplicate-padded-id'),
    ],
)
def test_a_test_list_entry_without_one_unique_trailing_id_is_reported(entry: str, expected_row: ExpectedRow) -> None:
    phase = brief_phase(test_list=lines(BRIEF_FIELDS['test_list'], entry))

    assert rows(check_phase_structure(phase)) == expected(expected_row)


@pytest.mark.parametrize(
    'entry',
    [
        pytest.param('- `tests/billing_check.unit::issues one invoice per order` — T-1', id='id-only'),
        pytest.param(
            '- `tests/billing_check.unit::issues one invoice per order` — the core seam, SD-001 — T-12',
            id='text-then-id',
        ),
    ],
)
def test_a_trailing_test_id_sits_outside_what_the_test_list_check_and_the_cli_read(entry: str) -> None:
    unnumbered = entry.rsplit(' — T-', 1)[0]

    assert parse_test_list(entry) == parse_test_list(unnumbered)
    assert rows(check_phase_structure(design(test_list=entry))) == []


def test_a_test_id_inside_the_backticks_would_become_part_of_the_test_name() -> None:
    entry = '- `tests/billing_check.unit::issues one invoice per order`'

    assert parse_test_list(entry.replace('order`', 'order — T-1`')) != parse_test_list(entry)


@pytest.mark.parametrize(
    ('success_criteria', 'expected_row'),
    [
        pytest.param(
            BRIEF_FIELDS['success_criteria'].replace(' — measure: T-3 passes', ''),
            (C.SUCCESS_CRITERION_MALFORMED, 'SC-3', 'measure', FINALIZER),
            id='no-measure',
        ),
        pytest.param(
            lines(BRIEF_FIELDS['success_criteria'], '- Results appear within a second — measure: timed by hand'),
            (
                C.SUCCESS_CRITERION_MALFORMED,
                '- Results appear within a second — measure: timed by hand',
                'id',
                FINALIZER,
            ),
            id='no-id',
        ),
        pytest.param(
            lines(BRIEF_FIELDS['success_criteria'], '- SC-2: results render again — measure: T-4 passes'),
            (C.DUPLICATE_ID, 'SC-2', '', FINALIZER),
            id='duplicate-id',
        ),
    ],
)
def test_a_success_criterion_that_is_not_one_sc_entry_with_a_measure_is_reported(
    success_criteria: str, expected_row: ExpectedRow
) -> None:
    assert rows(check_phase_structure(brief_phase(success_criteria=success_criteria))) == expected(expected_row)


def test_success_criteria_are_held_to_the_sc_form_only_once_a_finalizer_section_exists() -> None:
    success_criteria = lines(
        BRIEF_FIELDS['success_criteria'].replace(' — measure: T-3 passes', ''),
        '- Results appear within a second — measure: timed by hand',
    )

    assert rows(check_phase_structure(brief_phase(FINALIZER_SECTIONS_ABSENT, success_criteria=success_criteria))) == []


def test_an_id_a_guardrail_defines_twice_is_reported_at_the_second_definition() -> None:
    guardrails = GUARDRAILS.replace(
        '### Error policy', '- G-1: a cached row never outlives its source\n### Error policy'
    )

    assert rows(check_phase_structure(brief_phase({'Guardrails': guardrails}))) == expected(
        (C.DUPLICATE_ID, 'G-1', '', FINALIZER)
    )


@pytest.mark.parametrize(
    ('sections', 'overrides', 'subject', 'owner'),
    [
        pytest.param(
            {'Guardrails': GUARDRAILS.replace('(target: SC-3)', '(target: SC-9)')},
            {},
            'SC-9',
            FINALIZER,
            id='guardrails',
        ),
        pytest.param(
            {'Behaviors & Acceptance': BEHAVIORS.replace('tests: T-4', 'tests: T-9')},
            {},
            'T-9',
            FINALIZER,
            id='behaviors-and-acceptance',
        ),
        pytest.param(
            {'Grounding': GROUNDING.replace('informs: SD-2, Step 3', 'informs: G-9, Step 3')},
            {},
            'G-9',
            FINALIZER,
            id='grounding',
        ),
        pytest.param(
            {'Delegation Bounds': BOUNDS + '\n- T-9 cannot pass without a schema change.'},
            {},
            'T-9',
            ARCHITECT,
            id='delegation-bounds',
        ),
        pytest.param(
            {},
            {'open_design_decisions': lines(OPEN_OD_003, '  - Affects: `<path to the cache module>`, G-9')},
            'G-9',
            ARCHITECT,
            id='open-decision-affects-line',
        ),
        pytest.param(
            {},
            {'success_criteria': BRIEF_FIELDS['success_criteria'].replace('T-4 passes', 'T-9 passes')},
            'T-9',
            FINALIZER,
            id='success-criteria',
        ),
    ],
)
def test_a_test_criterion_or_guardrail_reference_to_nothing_is_reported_where_it_is_written(
    sections: dict[str, str], overrides: dict[str, str], subject: str, owner: FindingOwner
) -> None:
    assert rows(check_phase_structure(brief_phase(sections, **overrides))) == expected(
        (C.DANGLING_REFERENCE, subject, '', owner)
    )


@pytest.mark.parametrize(
    ('sections', 'overrides'),
    [
        pytest.param(
            {},
            {'collaboration_and_wiring': 'The cache serves repeated lookups, per SD-001, T-9, SC-9, G-9 and Step 9.'},
            id='outside-the-scanned-sections',
        ),
        pytest.param(
            {},
            {
                'settled_design_decisions': lines(
                    BRIEF_SD_001,
                    BRIEF_SD_002,
                    '- SD-003 | source=user | supersedes=OD-004 | decision=Option A | rationale=fewer parts'
                    ' | rejected=Option B | affects=T-9, SC-9, G-9, Step 9 | binding=yes',
                    '- SD-### | source=implementation | supersedes=Search.QueryCache.get'
                    ' | reason=the cache moved into the repository',
                )
            },
            id='inside-settled-entries',
        ),
        pytest.param(
            {'Behaviors & Acceptance': BEHAVIORS.replace('tests: T-4', 'tests: T-04')},
            {},
            id='numbers-compare-as-integers',
        ),
    ],
)
def test_an_id_outside_the_scanned_sections_or_inside_a_settled_entry_is_never_a_reference(
    sections: dict[str, str], overrides: dict[str, str]
) -> None:
    phase = brief_phase(sections, **overrides)

    assert rows(check_phase_structure(phase)) == []
    assert rows(check_implementation_structure(BRIEF_IMPLEMENTATION, phase)) == []


def test_an_affects_segment_never_hides_an_empty_rejected_value() -> None:
    # If affects is not a known SD key, its segment is appended to the rejected value before it, and
    # the missing rejected value goes unreported.
    entry = (
        '- SD-003 | source=user | supersedes=OD-004 | decision=Option A | rationale=simpler | rejected='
        ' | affects=Step 1 | binding=yes'
    )
    phase = brief_phase(settled_design_decisions=lines(BRIEF_SD_001, BRIEF_SD_002, entry))

    assert rows(check_phase_structure(phase)) == expected(
        (C.SETTLED_ENTRY_MALFORMED, 'SD-003', 'rejected', ORCHESTRATOR)
    )


# --- Phase 4, B8: the two research copies never disagree once Grounding exists --------------------


@pytest.mark.parametrize(
    ('sections', 'overrides', 'subject'),
    [
        pytest.param(
            {'Grounding': GROUNDING + '\n- `.best-practices/extra.md` — informs: Step 2'},
            {},
            '.best-practices/extra.md',
            id='only-in-research-to-read',
        ),
        pytest.param(
            {},
            {
                'research_requirements': lines(
                    RP_002,
                    BRIEF_READ_LINE,
                    '- Read: `.best-practices/approved-later.md` — informs: SD-2 — Source: in-kb',
                )
            },
            '.best-practices/approved-later.md',
            id='only-in-the-ledger',
        ),
    ],
)
def test_a_research_path_in_only_one_of_the_two_copies_is_reported(
    sections: dict[str, str], overrides: dict[str, str], subject: str
) -> None:
    assert rows(check_phase_structure(brief_phase(sections, **overrides))) == expected(
        (C.RESEARCH_COPIES_DISAGREE, subject, '', FINALIZER)
    )


@pytest.mark.parametrize(
    ('sections', 'overrides'),
    [
        pytest.param(
            FINALIZER_SECTIONS_ABSENT,
            {
                'research_requirements': lines(
                    RP_002,
                    BRIEF_READ_LINE,
                    '- Read: `.best-practices/approved-later.md` — informs: SD-2 — Source: in-kb',
                )
            },
            id='no-grounding-yet',
        ),
        pytest.param(
            {'Grounding': with_h3(GROUNDING, 'Research to read', '- None')},
            {'research_requirements': RP_002},
            id='both-empty',
        ),
    ],
)
def test_the_research_copies_agree_when_grounding_is_absent_or_both_are_empty(
    sections: dict[str, str], overrides: dict[str, str]
) -> None:
    assert rows(check_phase_structure(brief_phase(sections, **overrides))) == []


# --- Phase 4, B6 and B7 (implementation.md): every step is executable from a cold start ----------


@pytest.mark.parametrize(
    ('fields', 'expected_rows'),
    [
        pytest.param(
            DRAFT_STEP_FIELDS[:2],
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Depends on', ARCHITECT)],
            id='draft-step-missing-a-field',
        ),
        pytest.param(
            tuple(field for field in FINALIZED_STEP_FIELDS if not field.startswith('- **Verify:**')),
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Verify', FINALIZER)],
            id='finalized-step-missing-a-finalize-field',
        ),
        pytest.param(
            FINALIZED_STEP_FIELDS[1:],
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Goal', ARCHITECT)],
            id='finalized-step-missing-a-draft-field',
        ),
        pytest.param(
            (*DRAFT_STEP_FIELDS, '- **Verify:** `run-checks all`'),
            [
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Context', FINALIZER),
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Tests to turn green', FINALIZER),
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Done when', FINALIZER),
            ],
            id='draft-step-with-one-finalize-field',
        ),
        # The part names the first label, in written order, that stands where the order puts another.
        pytest.param(
            (EXPORT_FILES, EXPORT_GOAL, '- **Depends on:** Step 1'),
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Files', ARCHITECT)],
            id='draft-fields-out-of-order',
        ),
        pytest.param(
            (
                EXPORT_GOAL,
                EXPORT_FILES,
                '- **Context:** SD-1',
                *FINALIZED_STEP_FIELDS[3:],
            ),
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Context', FINALIZER)],
            id='context-after-files-names-the-finalize-field',
        ),
        pytest.param(
            (
                EXPORT_GOAL,
                EXPORT_FILES,
                '- **Depends on:** Step 1',
                '- **Context:** SD-1',
                *FINALIZED_STEP_FIELDS[4:],
            ),
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Context', FINALIZER)],
            id='context-after-depends-on-names-the-finalize-field',
        ),
        pytest.param(
            (
                FINALIZED_STEP_FIELDS[2],
                FINALIZED_STEP_FIELDS[0],
                *FINALIZED_STEP_FIELDS[1:2],
                *FINALIZED_STEP_FIELDS[3:],
            ),
            [(C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Files', ARCHITECT)],
            id='draft-labels-out-of-order-stay-architect',
        ),
        pytest.param(
            (),
            [
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Goal', ARCHITECT),
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Files', ARCHITECT),
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Depends on', ARCHITECT),
            ],
            id='no-fields',
        ),
        pytest.param(
            ('Export the results to a file.',),
            [
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Goal', ARCHITECT),
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Files', ARCHITECT),
                (C.IMPLEMENTATION_STEP_FIELDS_INCOMPLETE, 'Step 4', 'Depends on', ARCHITECT),
            ],
            id='prose-instead-of-fields',
        ),
    ],
)
def test_a_step_holding_neither_the_draft_fields_nor_all_seven_in_order_is_reported(
    fields: tuple[str, ...], expected_rows: list[ExpectedRow]
) -> None:
    assert brief_findings(brief_plan(with_step(4, *fields))) == expected(*expected_rows)


@pytest.mark.parametrize(
    'fields', [pytest.param(DRAFT_STEP_FIELDS, id='draft'), pytest.param(FINALIZED_STEP_FIELDS, id='finalized')]
)
def test_a_draft_or_finalized_step_beside_finalized_steps_passes(fields: tuple[str, ...]) -> None:
    assert brief_findings(brief_plan(with_step(4, *fields))) == []


def test_a_step_whose_files_name_no_backticked_path_is_reported() -> None:
    fields = (EXPORT_GOAL, '- **Files:** create the export module', '- **Depends on:** Step 1')

    assert brief_findings(brief_plan(with_step(4, *fields))) == expected(
        (C.IMPLEMENTATION_STEP_FILES_MISSING, 'Step 4', 'Files', ARCHITECT)
    )


@pytest.mark.parametrize(
    ('replace', 'expected_row'),
    [
        pytest.param(
            with_step(4, EXPORT_GOAL, EXPORT_FILES, '- **Depends on:** Step 9'),
            (C.IMPLEMENTATION_DEPENDENCY_INVALID, 'Step 4', 'Step 9', ARCHITECT),
            id='missing-step',
        ),
        pytest.param(
            with_step(4, EXPORT_GOAL, EXPORT_FILES, '- **Depends on:** Step 1, Step 4'),
            (C.IMPLEMENTATION_DEPENDENCY_INVALID, 'Step 4', 'Step 4', ARCHITECT),
            id='itself',
        ),
        pytest.param(
            {
                STEP_2_DEPENDS: STEP_2_DEPENDS.replace('Step 1', 'Step 1, Step 3'),
                STEP_3_DEPENDS: STEP_3_DEPENDS.replace('Step 1', 'Step 1, Step 2'),
            },
            (C.IMPLEMENTATION_DEPENDENCY_INVALID, 'Step 2', 'cycle', ARCHITECT),
            id='cycle',
        ),
    ],
)
def test_a_dependency_on_a_missing_step_on_itself_or_in_a_cycle_is_reported(
    replace: dict[str, str], expected_row: ExpectedRow
) -> None:
    assert brief_findings(brief_plan(replace)) == expected(expected_row)


def test_dependencies_that_converge_without_a_cycle_pass() -> None:
    plan = brief_plan({STEP_3_DEPENDS: STEP_3_DEPENDS.replace('Step 1', 'Step 1, Step 2')})

    assert brief_findings(plan) == []


def test_step_numbers_that_are_not_contiguous_from_one_are_reported() -> None:
    assert brief_findings(brief_plan(with_step(5, *DRAFT_STEP_FIELDS))) == expected(
        (C.IMPLEMENTATION_STEPS_NOT_CONTIGUOUS, 'Steps', '', ARCHITECT)
    )


@pytest.mark.parametrize('subsection', ['Execution Intent Policy', 'Deferred Risk Register'])
def test_a_policy_section_missing_one_of_its_subsections_is_reported(subsection: str) -> None:
    assert brief_findings(without_h3(BRIEF_IMPLEMENTATION, subsection)) == expected(
        (C.IMPLEMENTATION_SECTION_MISSING, 'implementation.md', f'Policy > {subsection}', ARCHITECT)
    )


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('', id='empty'),
        pytest.param('run-checks all', id='not-backticked'),
        pytest.param('` `', id='blank-command'),
        pytest.param('`TODO`', id='todo'),
        pytest.param('`todo: pick a command`', id='todo-lowercase'),
        pytest.param('`[TODO] pick a command`', id='todo-bracketed'),
        pytest.param('`no_preference`', id='no-preference'),
        pytest.param('`<the test command>`', id='angle-placeholder'),
        pytest.param('`run-checks <suite>`', id='angle-token-inside-a-command'),
        pytest.param('`[the test command]`', id='square-placeholder'),
        pytest.param('`run-checks all` `<the command of the second language>`', id='one-placeholder-among-commands'),
    ],
)
def test_a_step_verify_without_a_usable_command_is_reported(value: str) -> None:
    assert brief_findings(brief_plan(step_2_verify(value))) == expected(
        (C.IMPLEMENTATION_COMMAND_PLACEHOLDER, 'Step 2', 'Verify', FINALIZER)
    )


@pytest.mark.parametrize(
    'value',
    [
        pytest.param('`run-checks all < cases.txt > results.txt`', id='shell-redirection'),
        pytest.param(ASK_USER_MARKER, id='ask-user-marker'),
        pytest.param(f'`{ASK_USER_MARKER}`', id='backticked-ask-user-marker'),
        pytest.param(f'`run-checks all`; {ASK_USER_MARKER}', id='command-and-marker'),
        pytest.param('`run-checks all` `run-checks screens`', id='one-command-per-language'),
    ],
)
def test_a_step_verify_holding_commands_or_the_ask_user_marker_passes(value: str) -> None:
    assert brief_findings(brief_plan(step_2_verify(value))) == []


@pytest.mark.parametrize(
    'command',
    [
        '<the whole-phase check command>',
        'TODO',
        'no_preference',
        '[the whole-phase check command]',
        'run-checks <suite>',
    ],
)
def test_a_placeholder_exit_criteria_command_is_reported(command: str) -> None:
    plan = brief_plan({EXIT_COMMAND_LINE: f'- `{command}` passes'})

    assert brief_findings(plan) == expected((C.IMPLEMENTATION_COMMAND_PLACEHOLDER, 'Exit criteria', command, FINALIZER))


@pytest.mark.parametrize(
    'exit_lines',
    [
        pytest.param('- `run-checks all < cases.txt > results.txt` passes', id='shell-redirection'),
        pytest.param(f'- `{ASK_USER_MARKER}` passes', id='ask-user-marker'),
        pytest.param(lines(EXIT_COMMAND_LINE, '- `run-checks lint` passes'), id='two-commands'),
    ],
)
def test_exit_criteria_holding_commands_or_the_ask_user_marker_pass(exit_lines: str) -> None:
    assert brief_findings(brief_plan({EXIT_COMMAND_LINE: exit_lines})) == []


def test_a_checklist_verify_group_holding_a_placeholder_token_is_reported() -> None:
    item = '- [ ] Add the cache layer (Step 2) (verify: run-checks <suite>)'

    assert brief_findings(brief_plan({STEP_2_ITEM_BRIEF: item})) == expected(
        (C.IMPLEMENTATION_CHECKLIST_ITEM_MALFORMED, item, 'verify', ARCHITECT)
    )


def test_a_checklist_verify_group_holding_shell_redirection_passes() -> None:
    item = '- [ ] Add the cache layer (Step 2) (verify: run-checks all < cases.txt > results.txt)'

    assert brief_findings(brief_plan({STEP_2_ITEM_BRIEF: item})) == []


@pytest.mark.parametrize(
    ('markdown', 'expected_rows'),
    [
        pytest.param(
            without_h2(BRIEF_IMPLEMENTATION, 'Exit criteria'),
            [(C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Exit criteria', '', FINALIZER)],
            id='exit-criteria-missing',
        ),
        pytest.param(
            without_h2(BRIEF_IMPLEMENTATION, 'Deviations'),
            [(C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Deviations', '', FINALIZER)],
            id='deviations-missing',
        ),
        pytest.param(
            without_h2(BRIEF_IMPLEMENTATION, 'Start here'),
            [(C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Start here', '', FINALIZER)],
            id='start-here-missing',
        ),
        pytest.param(
            without_h3(BRIEF_IMPLEMENTATION, 'First action'),
            [(C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Start here', 'First action', FINALIZER)],
            id='start-here-subsection-missing',
        ),
        pytest.param(
            brief_plan({EXIT_COMMAND_LINE: '- every check command passes'}),
            [(C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Exit criteria', 'command', FINALIZER)],
            id='exit-criteria-without-a-command',
        ),
        pytest.param(
            without_h2(BRIEF_IMPLEMENTATION, 'Start here', 'Exit criteria', 'Deviations'),
            [
                (C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Start here', '', FINALIZER),
                (C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Exit criteria', '', FINALIZER),
                (C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Deviations', '', FINALIZER),
            ],
            id='finalized-steps-without-any',
        ),
    ],
)
def test_a_finalize_section_missing_beside_finalized_content_is_reported(
    markdown: str, expected_rows: list[ExpectedRow]
) -> None:
    assert brief_findings(markdown) == expected(*expected_rows)


def test_a_finalize_section_beside_draft_only_steps_needs_the_other_two() -> None:
    markdown = lines(CLEAN_IMPLEMENTATION, '', '## Deviations', '- None')

    assert implementation_findings(markdown) == expected(
        (C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Start here', '', FINALIZER),
        (C.IMPLEMENTATION_FINALIZE_SECTION_MISSING, 'Exit criteria', '', FINALIZER),
    )


@pytest.mark.parametrize(
    ('replace', 'subject'),
    [
        pytest.param({'- **Context:** SD-1, G-2, ': '- **Context:** SD-1, G-9, '}, 'G-9', id='guardrail-in-context'),
        pytest.param({'- **Context:** SC-2, ': '- **Context:** SC-9, '}, 'SC-9', id='criterion-in-context'),
        pytest.param(
            {'- **Tests to turn green:** T-3': '- **Tests to turn green:** T-3, T-9'}, 'T-9', id='tests-to-turn-green'
        ),
    ],
)
def test_an_id_a_step_cites_that_the_phase_never_defines_is_reported(replace: dict[str, str], subject: str) -> None:
    assert brief_findings(brief_plan(replace)) == expected((C.DANGLING_REFERENCE, subject, '', FINALIZER))


@pytest.mark.parametrize(
    ('sections', 'overrides', 'owner'),
    [
        pytest.param(
            {'Grounding': GROUNDING.replace('informs: Step 2, Step 3', 'informs: Step 2, Step 9')},
            {},
            FINALIZER,
            id='grounding',
        ),
        pytest.param(
            {'Delegation Bounds': BOUNDS + '\n- Step 9 would need a second cache.'},
            {},
            ARCHITECT,
            id='delegation-bounds',
        ),
        pytest.param(
            {},
            {'open_design_decisions': lines(OPEN_OD_003, '  - Affects: `<path to the cache module>`, Step 9')},
            ARCHITECT,
            id='open-decision-affects-line',
        ),
    ],
)
def test_a_step_the_phase_document_names_but_the_plan_lacks_is_reported_with_the_plan(
    sections: dict[str, str], overrides: dict[str, str], owner: FindingOwner
) -> None:
    phase = brief_phase(sections, **overrides)

    assert rows(check_phase_structure(phase)) == []
    assert brief_findings(phase=phase) == expected((C.DANGLING_REFERENCE, 'Step 9', '', owner))


def test_a_skeleton_index_path_no_step_names_in_its_files_is_reported() -> None:
    phase = brief_phase(
        module_layout=lines(BRIEF_FIELDS['module_layout'], f'- `{EXPORT_PATH}` — owns exports'),
        skeleton_index=lines(
            BRIEF_FIELDS['skeleton_index'], f'- `{EXPORT_PATH}` :: Exporter.write(rows: Rows) -> Report'
        ),
    )
    cited_only_in_context = brief_plan(
        {'- **Context:** SC-2, ': f'- **Context:** SC-2, `{EXPORT_PATH}` :: Exporter.write, '}
    )

    assert brief_findings(cited_only_in_context, phase) == expected(
        (C.SEAM_PATH_NOT_IN_ANY_STEP, EXPORT_PATH, '', ARCHITECT)
    )


@pytest.mark.parametrize(
    ('skeleton_path', 'files_path'),
    [
        ('<path to the cache module>', './<path to the cache module>'),
        ('./<path to the cache module>', '<path to the cache module>'),
    ],
    ids=['dot-slash-in-files', 'dot-slash-in-skeleton-index'],
)
def test_a_leading_dot_slash_never_separates_a_seam_from_the_step_that_creates_it(
    skeleton_path: str, files_path: str
) -> None:
    phase = brief_phase(
        skeleton_index=BRIEF_FIELDS['skeleton_index'].replace('`<path to the cache module>`', f'`{skeleton_path}`')
    )
    plan = brief_plan({'create `<path to the cache module>`': f'create `{files_path}`'})

    assert brief_findings(plan, phase) == []


def test_a_test_no_step_turns_green_is_reported_once_every_step_is_finalized() -> None:
    phase = brief_phase(test_list=lines(BRIEF_FIELDS['test_list'], f'{EVICTION_ENTRY} — T-5'))

    assert brief_findings(phase=phase) == expected((C.TEST_NOT_IN_ANY_STEP, 'T-5', '', FINALIZER))


def test_a_re_opened_phase_with_a_draft_step_beside_finalized_ones_reports_nothing() -> None:
    markdown = brief_markdown(test_list=lines(BRIEF_FIELDS['test_list'], f'{EVICTION_ENTRY} — T-5'))
    phase = Phase.parse_markdown(lines(markdown, '## Metadata', '### Shape Gate', 'shape-amended'))
    deviation = '- DEV-1 | Step 2 | expected: a cache module | found: a cache package | action: kept within discretion'
    plan = brief_plan({**with_step(4, *DRAFT_STEP_FIELDS), '## Deviations\n- None': f'## Deviations\n{deviation}'})
    assert phase.shape_gate == ShapeGate.SHAPE_AMENDED

    assert rows(check_phase_structure(phase)) == []
    assert brief_findings(plan, phase) == []


# Deviations lines are the implementers' record, which no agent may edit (Scope 3), so an ID they cite
# is never a reference: a finding on one would have no fix its owner is permitted to make.
def test_an_id_a_deviation_line_cites_is_never_a_reference() -> None:
    deviation = '- DEV-1 | Step 2 | expected: a cache per SD-9 | found: CQ-3 still open | action: escalated'

    assert brief_findings(brief_plan({'## Deviations\n- None': f'## Deviations\n{deviation}'})) == []


# --- Phase 4, B18 (ownership half): the owner is computed from the location ----------------------


@pytest.mark.parametrize(
    ('sections', 'owner'),
    [
        pytest.param(
            {'Grounding': GROUNDING.replace('informs: SD-2, Step 3', 'informs: OD-042, Step 3')},
            FINALIZER,
            id='grounding',
        ),
        pytest.param(
            {'Behaviors & Acceptance': BEHAVIORS + '\n- OD-042 is verified by hand.'},
            FINALIZER,
            id='behaviors-and-acceptance',
        ),
        pytest.param({'Guardrails': GUARDRAILS + '\n- Per OD-042.'}, FINALIZER, id='guardrails'),
        pytest.param({'Delegation Bounds': BOUNDS + '\n- Stop if OD-042 reopens.'}, ARCHITECT, id='delegation-bounds'),
    ],
)
def test_a_phase_3_finding_inside_a_finalizer_section_belongs_to_the_finalizer(
    sections: dict[str, str], owner: FindingOwner
) -> None:
    assert rows(check_phase_structure(brief_phase(sections))) == expected((C.DANGLING_REFERENCE, 'OD-042', '', owner))


def test_a_section_whose_name_only_begins_like_a_finalizer_section_stays_the_architects() -> None:
    phase = design(extra_sections=(('Grounding Notes', 'Revisit OD-042 after launch.'),))

    assert rows(check_phase_structure(phase)) == expected((C.DANGLING_REFERENCE, 'OD-042', '', ARCHITECT))


LOCATED_FINDINGS = [
    pytest.param(
        lambda: check_phase_structure(brief_phase({'Delegation Bounds': ''})),
        ('delegation-bounds-incomplete', 'Delegation Bounds', 'Delegation Bounds', '', 'architect'),
        id='delegation-bounds-absent',
    ),
    pytest.param(
        lambda: check_phase_structure(brief_phase({'Delegation Bounds': without_h3(BOUNDS, 'Escalate if')})),
        (
            'delegation-bounds-incomplete',
            'Delegation Bounds > Escalate if',
            'Delegation Bounds',
            'Escalate if',
            'architect',
        ),
        id='delegation-bounds-subsection',
    ),
    pytest.param(
        lambda: check_phase_structure(brief_phase({'Grounding': ''})),
        ('brief-section-incomplete', 'Grounding', 'Grounding', '', 'finalizer'),
        id='finalizer-section-missing',
    ),
    pytest.param(
        lambda: check_phase_structure(brief_phase({'Guardrails': without_h3(GUARDRAILS, 'Deviation protocol')})),
        (
            'brief-section-incomplete',
            'Guardrails > Deviation protocol',
            'Guardrails',
            'Deviation protocol',
            'finalizer',
        ),
        id='finalizer-subsection',
    ),
    pytest.param(
        lambda: check_phase_structure(brief_phase(test_list=lines(BRIEF_FIELDS['test_list'], EVICTION_ENTRY))),
        ('test-entry-without-id', 'Design Shape > Test List', EVICTION_ENTRY, '', 'architect'),
        id='test-entry-without-id',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase(test_list=lines(BRIEF_FIELDS['test_list'], f'{EVICTION_ENTRY} — T-3'))
        ),
        ('duplicate-id', 'Design Shape > Test List', 'T-3', '', 'architect'),
        id='duplicate-test-id',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase(success_criteria=BRIEF_FIELDS['success_criteria'].replace(' — measure: T-3 passes', ''))
        ),
        ('success-criterion-malformed', 'Additional Details > Success Criteria', 'SC-3', 'measure', 'finalizer'),
        id='success-criterion-malformed',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase(success_criteria=lines(BRIEF_FIELDS['success_criteria'], '- SC-2: again — measure: T-4 passes'))
        ),
        ('duplicate-id', 'Additional Details > Success Criteria', 'SC-2', '', 'finalizer'),
        id='duplicate-criterion-id',
    ),
    pytest.param(
        lambda: check_phase_structure(design(success_criteria='- SC-1: first\n- SC-1: again')),
        ('duplicate-id', 'Additional Details > Success Criteria', 'SC-1', '', 'architect'),
        id='duplicate-criterion-id-before-finalize',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase(success_criteria=lines(BRIEF_FIELDS['success_criteria'], '- SC-9: more — measure: T-9 passes'))
        ),
        ('dangling-reference', 'Additional Details > Success Criteria', 'T-9', '', 'finalizer'),
        id='dangling-test-in-finalized-success-criteria',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase({'Guardrails': GUARDRAILS.replace('### Error policy', '- G-1: again\n### Error policy')})
        ),
        ('duplicate-id', 'Guardrails', 'G-1', '', 'finalizer'),
        id='duplicate-guardrail-id',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase({'Behaviors & Acceptance': BEHAVIORS.replace('tests: T-4', 'tests: T-9')})
        ),
        ('dangling-reference', 'Behaviors & Acceptance', 'T-9', '', 'finalizer'),
        id='dangling-test-in-behaviors',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase({'Grounding': GROUNDING.replace('informs: SD-2, Step 3', 'informs: OD-042, Step 3')})
        ),
        ('dangling-reference', 'Grounding', 'OD-042', '', 'finalizer'),
        id='phase-3-family-in-grounding',
    ),
    pytest.param(
        lambda: check_phase_structure(design(extra_sections=(('Grounding Notes', 'Revisit OD-042.'),))),
        ('dangling-reference', 'Grounding Notes', 'OD-042', '', 'architect'),
        id='section-named-like-grounding',
    ),
    pytest.param(
        lambda: check_phase_structure(
            brief_phase({'Grounding': GROUNDING + '\n- `.best-practices/extra.md` — informs: Step 2'})
        ),
        ('research-copies-disagree', 'Grounding > Research to read', '.best-practices/extra.md', '', 'finalizer'),
        id='research-copies-disagree',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            without_h3(BRIEF_IMPLEMENTATION, 'Deferred Risk Register'), brief_phase()
        ),
        (
            'implementation-section-missing',
            'implementation.md > Policy',
            'implementation.md',
            'Policy > Deferred Risk Register',
            'architect',
        ),
        id='policy-subsection-missing',
    ),
    pytest.param(
        lambda: check_implementation_structure(brief_plan(with_step(5, *DRAFT_STEP_FIELDS)), brief_phase()),
        ('implementation-steps-not-contiguous', 'implementation.md > Build Order > Steps', 'Steps', '', 'architect'),
        id='steps-not-contiguous',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({STEP_2_VERIFY: '- **Tests to turn green:** T-3'}), brief_phase()
        ),
        (
            'implementation-step-fields-incomplete',
            'implementation.md > Step 2 > Verify',
            'Step 2',
            'Verify',
            'finalizer',
        ),
        id='finalize-field-missing',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({'- **Goal:** A repeated query is served from a cache in front of the repository.\n': ''}),
            brief_phase(),
        ),
        ('implementation-step-fields-incomplete', 'implementation.md > Step 2 > Goal', 'Step 2', 'Goal', 'architect'),
        id='draft-field-missing',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan(with_step(4, EXPORT_GOAL, '- **Files:** create the export module', '- **Depends on:** Step 1')),
            brief_phase(),
        ),
        ('implementation-step-files-missing', 'implementation.md > Step 4 > Files', 'Step 4', 'Files', 'architect'),
        id='files-missing',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan(with_step(4, EXPORT_GOAL, EXPORT_FILES, '- **Depends on:** Step 9')), brief_phase()
        ),
        (
            'implementation-dependency-invalid',
            'implementation.md > Step 4 > Depends on',
            'Step 4',
            'Step 9',
            'architect',
        ),
        id='dependency-on-a-missing-step',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan(
                {
                    STEP_2_DEPENDS: STEP_2_DEPENDS.replace('Step 1', 'Step 1, Step 3'),
                    STEP_3_DEPENDS: STEP_3_DEPENDS.replace('Step 1', 'Step 1, Step 2'),
                }
            ),
            brief_phase(),
        ),
        (
            'implementation-dependency-invalid',
            'implementation.md > Step 2 > Depends on',
            'Step 2',
            'cycle',
            'architect',
        ),
        id='dependency-cycle',
    ),
    pytest.param(
        lambda: check_implementation_structure(brief_plan(step_2_verify('`TODO`')), brief_phase()),
        ('implementation-command-placeholder', 'implementation.md > Step 2 > Verify', 'Step 2', 'Verify', 'finalizer'),
        id='verify-placeholder',
    ),
    pytest.param(
        lambda: check_implementation_structure(brief_plan({EXIT_COMMAND_LINE: '- `TODO` passes'}), brief_phase()),
        (
            'implementation-command-placeholder',
            'implementation.md > Exit criteria',
            'Exit criteria',
            'TODO',
            'finalizer',
        ),
        id='exit-criteria-placeholder',
    ),
    pytest.param(
        lambda: check_implementation_structure(without_h2(BRIEF_IMPLEMENTATION, 'Deviations'), brief_phase()),
        ('implementation-finalize-section-missing', 'implementation.md > Deviations', 'Deviations', '', 'finalizer'),
        id='finalize-section-missing',
    ),
    pytest.param(
        lambda: check_implementation_structure(without_h3(BRIEF_IMPLEMENTATION, 'First action'), brief_phase()),
        (
            'implementation-finalize-section-missing',
            'implementation.md > Start here > First action',
            'Start here',
            'First action',
            'finalizer',
        ),
        id='start-here-subsection-missing',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({EXIT_COMMAND_LINE: '- every check command passes'}), brief_phase()
        ),
        (
            'implementation-finalize-section-missing',
            'implementation.md > Exit criteria',
            'Exit criteria',
            'command',
            'finalizer',
        ),
        id='exit-criteria-without-a-command',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({'- **Context:** SD-1, G-2, ': '- **Context:** SD-1, G-9, '}), brief_phase()
        ),
        ('dangling-reference', 'implementation.md > Step 2 > Context', 'G-9', '', 'finalizer'),
        id='dangling-in-context',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({'- **Tests to turn green:** T-3': '- **Tests to turn green:** T-3, T-9'}), brief_phase()
        ),
        ('dangling-reference', 'implementation.md > Step 2 > Tests to turn green', 'T-9', '', 'finalizer'),
        id='dangling-in-tests-to-turn-green',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan(
                {'- **Goal:** Query results render as a list.': '- **Goal:** Query results render as a list, per SD-9.'}
            ),
            brief_phase(),
        ),
        ('dangling-reference', 'implementation.md > Step 3 > Goal', 'SD-9', '', 'architect'),
        id='phase-3-family-in-a-draft-field',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({'- **Context:** SD-1, G-1, ': '- **Context:** SD-9, G-1, '}), brief_phase()
        ),
        ('dangling-reference', 'implementation.md > Step 1 > Context', 'SD-9', '', 'finalizer'),
        id='phase-3-family-in-a-finalize-field',
    ),
    pytest.param(
        lambda: check_implementation_structure(brief_plan({'Guardrails; SD-1;': 'Guardrails; SD-9;'}), brief_phase()),
        ('dangling-reference', 'implementation.md > Start here > Required reading', 'SD-9', '', 'finalizer'),
        id='phase-3-family-in-start-here',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({'every SC-n holds as its measure states': 'every SC-n holds as its measure states, per SD-9'}),
            brief_phase(),
        ),
        ('dangling-reference', 'implementation.md > Exit criteria', 'SD-9', '', 'finalizer'),
        id='phase-3-family-in-exit-criteria',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({'before anything builds on it.': 'before anything builds on it, per SD-9.'}), brief_phase()
        ),
        ('dangling-reference', 'implementation.md > Build Order > Staging', 'SD-9', '', 'architect'),
        id='phase-3-family-in-staging',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            BRIEF_IMPLEMENTATION,
            brief_phase({'Grounding': GROUNDING.replace('informs: Step 2, Step 3', 'informs: Step 2, Step 9')}),
        ),
        ('dangling-reference', 'Grounding', 'Step 9', '', 'finalizer'),
        id='step-in-grounding',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            BRIEF_IMPLEMENTATION,
            brief_phase(open_design_decisions=lines(OPEN_OD_003, '  - Affects: `<path to the cache module>`, Step 9')),
        ),
        ('dangling-reference', 'Design Decisions > Open Design Decisions', 'Step 9', '', 'architect'),
        id='step-on-an-open-decision',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            BRIEF_IMPLEMENTATION,
            brief_phase(
                module_layout=lines(BRIEF_FIELDS['module_layout'], f'- `{EXPORT_PATH}` — owns exports'),
                skeleton_index=lines(
                    BRIEF_FIELDS['skeleton_index'], f'- `{EXPORT_PATH}` :: Exporter.write(rows: Rows) -> Report'
                ),
            ),
        ),
        ('seam-path-not-in-any-step', 'implementation.md > Build Order > Steps', EXPORT_PATH, '', 'architect'),
        id='seam-path-not-in-any-step',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            BRIEF_IMPLEMENTATION, brief_phase(test_list=lines(BRIEF_FIELDS['test_list'], f'{EVICTION_ENTRY} — T-5'))
        ),
        (
            'test-not-in-any-step',
            'implementation.md > Build Order > Steps > Tests to turn green',
            'T-5',
            '',
            'finalizer',
        ),
        id='test-not-in-any-step',
    ),
    pytest.param(
        lambda: check_implementation_structure(
            brief_plan({STEP_2_ITEM_BRIEF: '- [ ] Add the cache layer (Step 2) (verify: TODO)'}), brief_phase()
        ),
        (
            'implementation-checklist-item-malformed',
            'implementation.md > Checklist',
            '- [ ] Add the cache layer (Step 2) (verify: TODO)',
            'verify',
            'architect',
        ),
        id='checklist-placeholder',
    ),
]


@pytest.mark.parametrize(('findings_of', 'row'), LOCATED_FINDINGS)
def test_every_finding_is_located_where_its_owner_is_computed_from(
    findings_of: Callable[[], list[StructuralFinding]], row: LocatedRow
) -> None:
    assert located(findings_of()) == [row]


# --- Phase 4, Scope 5 "Cited paths": paths the host verifies ------------------------------------


GROUNDING_WITH_PATHS = lines(
    '### Build on',
    '- `src/query/service.unit` — extend: route queries through the cache — informs: Step 1',
    '### Leave alone',
    '- `src/query/legacy.unit` — other teams still call it',
    '### Exemplars',
    '- `src/orders/cache.unit` — imitate for read-through caching — informs: Step 2',
    '### Conventions',
    '- `docs/contributing.md` — governs naming and layout',
    '### Research to read',
    '- `.best-practices/<file>.md` — informs: SD-2, Step 2 — Source: RP-002',
)


def test_grounding_paths_are_returned_for_the_host_to_verify_with_their_subsection() -> None:
    paths = extract_cited_paths(brief_phase({'Grounding': GROUNDING_WITH_PATHS}))

    assert cited([path for path in paths if path.kind == CitedPathKind.GROUNDING]) == sorted(
        [
            ('src/query/service.unit', CitedPathKind.GROUNDING.value, 'Grounding > Build on'),
            ('src/query/legacy.unit', CitedPathKind.GROUNDING.value, 'Grounding > Leave alone'),
            ('src/orders/cache.unit', CitedPathKind.GROUNDING.value, 'Grounding > Exemplars'),
            ('docs/contributing.md', CitedPathKind.GROUNDING.value, 'Grounding > Conventions'),
        ]
    )


def test_each_step_files_path_is_returned_with_its_verb_and_step() -> None:
    files = 'implementation.md > Step {} > Files'

    assert cited(extract_implementation_paths(BRIEF_IMPLEMENTATION)) == sorted(
        [
            ('<path to the repository query module>', CitedPathKind.CREATE.value, files.format(1)),
            ('<path to the query test file>', CitedPathKind.CREATE.value, files.format(1)),
            ('<path to the service wiring module>', CitedPathKind.MODIFY.value, files.format(1)),
            ('<path to the cache module>', CitedPathKind.CREATE.value, files.format(2)),
            ('<path to the cache test file>', CitedPathKind.CREATE.value, files.format(2)),
            ('<path to the result list component>', CitedPathKind.CREATE.value, files.format(3)),
            ('<path to the result list test file>', CitedPathKind.CREATE.value, files.format(3)),
        ]
    )
