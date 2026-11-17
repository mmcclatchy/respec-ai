"""Phase 3 — the validate_document MCP tool.

Behavior B1: a user edit that the parser would silently discard is reported instead of
being swallowed. This wraps Phase.find_content_loss (see
tests/unit/models/test_content_loss_detection.py) for every document type, dispatched
the same way store_document/get_document are.

Phase-cooperative phase 3 (docs/phase-cooperative/phase-3-structural-checks.md) adds the
structural checks: B10 keeps them apart from content loss, B11 reports unstorable content,
B13 makes agent writes report their own loss, and B14 adds the stored-document key mode.
"""

from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.document_tools import DocumentTools, register_document_tools
from src.mcp.tools.feedback_tools_unified import UnifiedFeedbackTools
from src.models.document_validation import (
    CONTENT_LOSS_WARNING,
    UNSTORABLE_DOCUMENT,
    CitedPathKind,
    StructuralFinding,
)
from src.models.enums import DocumentType
from src.models.phase import Phase
from src.platform.templates.agents.create_phase import sparse_phase_example
from src.utils.enums import LoopStatus, LoopType
from src.utils.loop_state import DocumentValidationResponse, LoopState
from src.utils.state_manager import InMemoryStateManager


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager(max_history_size=3)


@pytest.fixture
def document_tools(state_manager: InMemoryStateManager) -> DocumentTools:
    return DocumentTools(state_manager)


PHASE_WITH_TRUNCATED_SECTION = """# Phase: sample-phase

## Overview
### Objectives
Real objective content.

---

Lost content that must never silently disappear.
### Scope
Some scope.
### Dependencies
Some deps.
### Deliverables
Some deliverables.
"""

CLEAN_PHASE = """# Phase: sample-phase

## Overview
### Objectives
Some objective.
### Scope
Some scope.
### Dependencies
Some deps.
### Deliverables
Some deliverables.
"""


async def test_validate_document_reports_content_that_would_be_silently_dropped(
    document_tools: DocumentTools,
) -> None:
    result = await document_tools.validate_document(DocumentType.PHASE, PHASE_WITH_TRUNCATED_SECTION)

    assert 'Objectives' in result.message


async def test_validate_document_reports_nothing_for_a_clean_document(document_tools: DocumentTools) -> None:
    result = await document_tools.validate_document(DocumentType.PHASE, CLEAN_PHASE)

    assert 'Objectives' not in result.message


PHASE_KEY = 'sample-plan/sample-phase'
UNCOVERED_SEAM = 'src/billing/invoices.unit'
UNCOVERED_SEAM_KEY = f'seam-path-not-in-module-layout {UNCOVERED_SEAM}'
MISSING_POLICY_KEY = 'implementation-section-missing implementation.md [Policy]'
COVERING_MODULE_LAYOUT = '- `src/ledger/` — owns ledger entries\n- `src/billing/` — owns invoices'
PARTIAL_MODULE_LAYOUT = '- `src/ledger/` — owns ledger entries'
READ_PATH = '.best-practices/ledger-posting.md'
RESEARCH_LEDGER = f'- Read: `{READ_PATH}` — informs: the ledger seam — Source: in-kb'


def accept_as_is(*finding_keys: str) -> str:
    quoted = '; '.join(f'{key} — accepted at review' for key in finding_keys)
    return (
        f'- SD-001 | source=user | supersedes=unresolved-checks | decision=accept as-is: {quoted}'
        ' | rationale=the user keeps the design as written | binding=yes'
    )


def designed_phase(module_layout: str, settled: str = '', research: str = '') -> str:
    document = [
        CLEAN_PHASE.rstrip('\n'),
        '',
        '## Design Shape',
        '### Module Layout',
        module_layout,
        '### Skeleton Index',
        '- `src/ledger/entries.unit` :: Ledger.post(entry: Entry) -> Receipt',
        f'- `{UNCOVERED_SEAM}` :: Billing.issue(order: Order) -> Invoice',
        '### Test List',
        '- `tests/ledger_check.unit::posts an entry`',
        '- `tests/billing_check.unit::issues an invoice`',
    ]
    if settled:
        document.extend(['', '## Design Decisions', '### Settled Design Decisions', settled])
    if research:
        document.extend(['', '## Additional Details', '### Research Requirements', research])
    return '\n'.join(document) + '\n'


CLEAN_DESIGN = designed_phase(COVERING_MODULE_LAYOUT)
SEAM_OUTSIDE_LAYOUT = designed_phase(PARTIAL_MODULE_LAYOUT)

CLEAN_IMPLEMENTATION = """# Implementation Plan: sample-phase

## Build Order
### Steps
#### Step 1: Ledger entries
**Objective**: Post entries before anything bills them.

#### Step 2: Invoices
**Objective**: Issue invoices once entries post.

## Policy
### Execution Intent Policy
- Mode: MVP

### Deferred Risk Register
- None

## Checklist
- [ ] Post entries (Step 1) (verify: run-checks ledger)
- [ ] Issue invoices (Step 2) (verify: run-checks invoices)
"""

IMPLEMENTATION_WITHOUT_POLICY = """# Implementation Plan: sample-phase

## Build Order
### Steps
#### Step 1: Ledger entries
**Objective**: Post entries before anything bills them.

## Checklist
- [ ] Post entries (Step 1) (verify: run-checks ledger)
"""


def finding_keys(findings: list[StructuralFinding]) -> list[str]:
    return sorted(
        f'{finding.check.value} {finding.subject}' + (f' [{finding.part}]' if finding.part else '')
        for finding in findings
    )


def skipped_with_prefix(result: DocumentValidationResponse, prefix: str) -> list[str]:
    return [entry for entry in result.skipped_checks if entry.startswith(prefix)]


async def store_phase(document_tools: DocumentTools, content: str) -> None:
    await document_tools.store_document(DocumentType.PHASE, PHASE_KEY, content)


async def validate_by_key(
    document_tools: DocumentTools, implementation_markdown: str | None = None
) -> DocumentValidationResponse:
    return await document_tools.validate_document(
        DocumentType.PHASE, key=PHASE_KEY, implementation_markdown=implementation_markdown
    )


# --- B10: structural findings never change status or message --------------------------------------


async def test_structural_findings_leave_the_content_loss_verdict_untouched(document_tools: DocumentTools) -> None:
    clean = await document_tools.validate_document(DocumentType.PHASE, CLEAN_DESIGN)
    defective = await document_tools.validate_document(DocumentType.PHASE, SEAM_OUTSIDE_LAYOUT)

    assert clean.structural_findings == []
    assert finding_keys(defective.structural_findings) == [UNCOVERED_SEAM_KEY]
    assert (defective.status, defective.message) == (clean.status, clean.message)
    assert defective.status == LoopStatus.COMPLETED


async def test_content_loss_still_asks_the_user_when_structural_findings_are_present(
    document_tools: DocumentTools,
) -> None:
    lossy = SEAM_OUTSIDE_LAYOUT.replace('### Skeleton Index', '### Skeleton Index\n---\nLost seam notes.')

    result = await document_tools.validate_document(DocumentType.PHASE, lossy)

    assert result.status == LoopStatus.USER_INPUT
    assert 'Design Shape > Skeleton Index' in result.message


async def test_a_phase_without_a_design_layer_reports_no_structural_findings(document_tools: DocumentTools) -> None:
    create_phase_output = sparse_phase_example.replace('[phase-name-in-kebab-case]', 'sample-phase')

    result = await document_tools.validate_document(DocumentType.PHASE, create_phase_output)

    assert result.status == LoopStatus.COMPLETED
    assert result.structural_findings == []
    assert result.implementation_findings == []


# --- B11: content store would reject is reported as content loss, never as clean ------------------


UNSTORABLE_PHASES = [
    pytest.param(CLEAN_DESIGN.replace('# Phase: sample-phase', '# Phase: Sample Phase'), id='title-not-kebab-case'),
    pytest.param(CLEAN_DESIGN.replace('# Phase: sample-phase', '## Phase notes'), id='no-title-heading'),
    pytest.param(CLEAN_DESIGN + '\n## Metadata\n### Iteration\nthree\n', id='metadata-not-a-number'),
    pytest.param(CLEAN_DESIGN + '\n## Metadata\n### Shape Gate\nhalf-shaped\n', id='unknown-shape-gate'),
]


@pytest.mark.parametrize('content', UNSTORABLE_PHASES)
async def test_content_store_would_reject_is_reported_as_content_loss(
    document_tools: DocumentTools, content: str
) -> None:
    result = await document_tools.validate_document(DocumentType.PHASE, content)

    unstorable_lines = [line for line in result.message.splitlines() if UNSTORABLE_DOCUMENT in line]
    assert result.status == LoopStatus.USER_INPUT
    assert len(unstorable_lines) == 1
    assert unstorable_lines[0].split(UNSTORABLE_DOCUMENT, 1)[1].strip(' :')
    assert result.structural_findings == []
    assert result.paths_to_verify == []
    assert skipped_with_prefix(result, 'structure:')


@pytest.mark.parametrize('content', UNSTORABLE_PHASES)
async def test_content_store_would_reject_is_proven_unstorable(document_tools: DocumentTools, content: str) -> None:
    with pytest.raises(ToolError):
        await document_tools.store_document(DocumentType.PHASE, PHASE_KEY, content)


async def test_a_storable_document_never_reports_skipped_structure(document_tools: DocumentTools) -> None:
    result = await document_tools.validate_document(DocumentType.PHASE, CLEAN_DESIGN)

    assert UNSTORABLE_DOCUMENT not in result.message
    assert skipped_with_prefix(result, 'structure:') == []


async def test_an_unstorable_document_says_its_implementation_and_path_checks_did_not_run(
    document_tools: DocumentTools,
) -> None:
    unstorable = CLEAN_DESIGN.replace('# Phase: sample-phase', '# Phase: Sample Phase')

    result = await document_tools.validate_document(
        DocumentType.PHASE, unstorable, implementation_markdown=IMPLEMENTATION_WITHOUT_POLICY
    )

    assert result.implementation_findings == []
    assert len(skipped_with_prefix(result, 'implementation.md')) == 1
    assert len(skipped_with_prefix(result, 'cited-paths-exist')) == 1


# --- B7 and B8 through the tool: what the server cannot check is said, never implied clean --------


@pytest.mark.parametrize('mode', ['content', 'key'])
async def test_cited_paths_are_returned_and_their_existence_is_listed_as_skipped(
    document_tools: DocumentTools, mode: str
) -> None:
    content = designed_phase(COVERING_MODULE_LAYOUT, research=RESEARCH_LEDGER)
    await store_phase(document_tools, content)

    result = (
        await document_tools.validate_document(DocumentType.PHASE, content)
        if mode == 'content'
        else await validate_by_key(document_tools)
    )

    assert [(cited.path, cited.kind) for cited in result.paths_to_verify] == [(READ_PATH, CitedPathKind.READ)]
    assert len(skipped_with_prefix(result, 'cited-paths-exist')) == 1


async def test_an_implementation_body_that_was_not_passed_is_skipped_never_clean(
    document_tools: DocumentTools,
) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)

    result = await validate_by_key(document_tools)

    assert result.implementation_findings == []
    assert len(skipped_with_prefix(result, 'implementation.md')) == 1


@pytest.mark.parametrize(
    ('implementation_markdown', 'expected_keys'),
    [
        pytest.param(CLEAN_IMPLEMENTATION, [], id='clean'),
        pytest.param(IMPLEMENTATION_WITHOUT_POLICY, [MISSING_POLICY_KEY], id='missing-policy'),
        pytest.param(
            '',
            [
                'implementation-section-missing implementation.md [Build Order > Steps]',
                'implementation-section-missing implementation.md [Checklist]',
                MISSING_POLICY_KEY,
            ],
            id='empty-body',
        ),
    ],
)
async def test_a_passed_implementation_body_is_checked_against_the_phase(
    document_tools: DocumentTools, implementation_markdown: str, expected_keys: list[str]
) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)

    result = await validate_by_key(document_tools, implementation_markdown)

    assert finding_keys(result.implementation_findings) == expected_keys
    assert skipped_with_prefix(result, 'implementation.md') == []


async def test_content_mode_checks_a_passed_implementation_body_too(document_tools: DocumentTools) -> None:
    result = await document_tools.validate_document(
        DocumentType.PHASE, CLEAN_DESIGN, implementation_markdown=IMPLEMENTATION_WITHOUT_POLICY
    )

    assert finding_keys(result.implementation_findings) == [MISSING_POLICY_KEY]


# --- B17 through the tool: an accepted finding stays accepted in both finding lists ---------------


async def test_findings_the_user_accepted_are_dropped_from_both_lists_and_listed_as_skipped(
    document_tools: DocumentTools,
) -> None:
    accepted = designed_phase(PARTIAL_MODULE_LAYOUT, settled=accept_as_is(UNCOVERED_SEAM_KEY, MISSING_POLICY_KEY))
    await store_phase(document_tools, accepted)

    result = await validate_by_key(document_tools, IMPLEMENTATION_WITHOUT_POLICY)

    assert result.structural_findings == []
    assert result.implementation_findings == []
    assert sorted(skipped_with_prefix(result, 'accepted: ')) == sorted(
        [f'accepted: {UNCOVERED_SEAM_KEY}', f'accepted: {MISSING_POLICY_KEY}']
    )


async def test_findings_without_an_accepting_entry_are_still_reported(document_tools: DocumentTools) -> None:
    await store_phase(document_tools, SEAM_OUTSIDE_LAYOUT)

    result = await validate_by_key(document_tools, IMPLEMENTATION_WITHOUT_POLICY)

    assert finding_keys(result.structural_findings) == [UNCOVERED_SEAM_KEY]
    assert finding_keys(result.implementation_findings) == [MISSING_POLICY_KEY]
    assert skipped_with_prefix(result, 'accepted: ') == []


POSTING_ITEM = '- [ ] Post entries (Step 1) (verify: run-checks ledger)'


def critic_relay(loop_id: str, blocker: str) -> str:
    return f"""# Critic Feedback: PHASE-CRITIC

## Assessment Summary
- **Loop ID**: {loop_id}
- **Iteration**: 1
- **Overall Score**: 0
- **Assessment Summary**: One relayed implementation finding remains.

## Analysis

The implementation plan has one structural finding.

## Issues and Recommendations

### Key Issues

- None identified

### Blockers

- {blocker}

### Recommendations

- None provided
"""


def stored_blockers(feedback_message: str) -> list[str]:
    section = feedback_message.split('### Blockers\n', 1)[1].split('\n\n', 1)[0]
    return [line.removeprefix('- ') for line in section.splitlines()]


@pytest.mark.parametrize(
    'item',
    [
        pytest.param('- [ ] Post entries (Step 1) (verify: `TODO`)', id='code-span-subject'),
        pytest.param('- [ ] Post __entries__ (Step 1) (verify: TODO)', id='emphasis-subject'),
    ],
)
async def test_a_relayed_implementation_finding_accepted_from_stored_feedback_stays_accepted(
    document_tools: DocumentTools, state_manager: InMemoryStateManager, item: str
) -> None:
    # The spent-budget branches build the accept-as-is quote from the critic's stored blockers,
    # so the quote is only as exact as the blocker text get_feedback returns.
    loop = LoopState(loop_type=LoopType.PHASE)
    await state_manager.add_loop(loop, 'sample-plan')
    feedback_tools = UnifiedFeedbackTools(state_manager)
    implementation = CLEAN_IMPLEMENTATION.replace(POSTING_ITEM, item)
    await store_phase(document_tools, CLEAN_DESIGN)
    [finding] = (await validate_by_key(document_tools, implementation)).implementation_findings
    [key] = finding_keys([finding])
    relay = f'[mechanical] [Implementation Plan Structure Invalid - BLOCKING]: {key} — {finding.detail}'

    await feedback_tools.store_critic_feedback(loop.id, critic_relay(loop.id, relay))
    unresolved_checks = stored_blockers((await feedback_tools.get_feedback(loop.id, count=1)).message)
    accept = (
        f'- SD-001 | source=user | supersedes=unresolved-checks | decision=accept as-is: {"; ".join(unresolved_checks)}'
        ' | rationale=accepted at design review | binding=yes'
    )
    await store_phase(document_tools, designed_phase(COVERING_MODULE_LAYOUT, settled=accept))
    result = await validate_by_key(document_tools, implementation)

    assert result.implementation_findings == []
    assert skipped_with_prefix(result, 'accepted: ') == [f'accepted: {key}']
    assert unresolved_checks == [relay]


# --- B14: key mode, the exactly-one rule, phase-only inputs, and the published schema -------------


async def test_key_mode_validates_the_stored_document(document_tools: DocumentTools) -> None:
    await store_phase(document_tools, SEAM_OUTSIDE_LAYOUT)
    defective = await validate_by_key(document_tools)
    await store_phase(document_tools, CLEAN_DESIGN)
    repaired = await validate_by_key(document_tools)

    assert finding_keys(defective.structural_findings) == [UNCOVERED_SEAM_KEY]
    assert repaired.structural_findings == []
    assert defective.status == repaired.status == LoopStatus.COMPLETED


async def test_key_mode_reads_the_document_as_stored_not_as_last_validated(document_tools: DocumentTools) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)
    await document_tools.validate_document(DocumentType.PHASE, SEAM_OUTSIDE_LAYOUT)

    result = await validate_by_key(document_tools)

    assert result.structural_findings == []


async def test_key_mode_on_a_phase_that_does_not_exist_is_a_resource_error(document_tools: DocumentTools) -> None:
    with pytest.raises(ResourceError):
        await validate_by_key(document_tools)


async def test_key_mode_with_a_malformed_key_is_a_tool_error(document_tools: DocumentTools) -> None:
    with pytest.raises(ToolError):
        await document_tools.validate_document(DocumentType.PHASE, key='sample-phase')


@pytest.mark.parametrize(
    'inputs',
    [
        pytest.param({}, id='neither'),
        pytest.param({'content': '', 'key': ''}, id='both-empty'),
        pytest.param({'content': CLEAN_DESIGN, 'key': PHASE_KEY}, id='both'),
        pytest.param({'implementation_markdown': CLEAN_IMPLEMENTATION}, id='only-implementation'),
    ],
)
async def test_validation_requires_exactly_one_of_content_and_key(
    document_tools: DocumentTools, inputs: dict[str, str]
) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)

    with pytest.raises(ToolError):
        await document_tools.validate_document(DocumentType.PHASE, **inputs)


@pytest.mark.parametrize('doc_type', [DocumentType.PLAN, DocumentType.ROADMAP])
@pytest.mark.parametrize(
    'inputs',
    [
        pytest.param({'key': 'sample-plan'}, id='key'),
        pytest.param({'content': CLEAN_PHASE, 'implementation_markdown': CLEAN_IMPLEMENTATION}, id='implementation'),
    ],
)
async def test_phase_only_inputs_on_another_document_type_are_errors(
    document_tools: DocumentTools, doc_type: DocumentType, inputs: dict[str, str]
) -> None:
    with pytest.raises(ToolError):
        await document_tools.validate_document(doc_type, **inputs)


async def published_validate_document() -> dict[str, dict[str, Any]]:
    mcp = FastMCP('validate-document-schema-probe')
    register_document_tools(mcp)
    tool = next(tool for tool in await mcp.list_tools() if tool.name == 'validate_document')
    return {'parameters': tool.parameters, 'output_schema': tool.output_schema or {}}


async def test_the_published_schema_requires_only_the_document_type() -> None:
    published = await published_validate_document()

    assert published['parameters']['required'] == ['doc_type']
    assert {'content', 'key', 'implementation_markdown'} <= set(published['parameters']['properties'])


async def test_the_published_output_schema_exposes_every_result_field() -> None:
    published = await published_validate_document()

    assert {
        'status',
        'message',
        'structural_findings',
        'implementation_findings',
        'paths_to_verify',
        'skipped_checks',
    } <= set(published['output_schema'].get('properties', {}))


# --- B13: an agent write that loses content still stores, and says which headings lost it ---------


LOSSY_AGENT_WRITE = CLEAN_DESIGN.replace(
    '### Skeleton Index', '### Skeleton Index\n---\nSeam notes lost on write.'
).replace('### Test List', '### Test List\n---\nTest notes lost on write.')
LOST_HEADINGS = ['Design Shape > Skeleton Index', 'Design Shape > Test List']


def content_loss_warnings(message: str) -> list[str]:
    return [line for line in message.splitlines() if line.startswith(CONTENT_LOSS_WARNING)]


async def test_an_agent_write_that_loses_content_still_stores_what_the_parser_kept(
    document_tools: DocumentTools, state_manager: InMemoryStateManager
) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)

    await document_tools.update_document(DocumentType.PHASE, PHASE_KEY, LOSSY_AGENT_WRITE)

    stored = await state_manager.get_phase('sample-plan', 'sample-phase')
    parsed = Phase.parse_markdown(LOSSY_AGENT_WRITE)
    assert stored.skeleton_index == parsed.skeleton_index
    assert stored.test_list == parsed.test_list
    assert 'lost on write' not in stored.build_markdown()


async def test_an_agent_write_that_loses_content_names_each_heading_in_one_warning(
    document_tools: DocumentTools,
) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)

    message = await document_tools.update_document(DocumentType.PHASE, PHASE_KEY, LOSSY_AGENT_WRITE)

    warnings = content_loss_warnings(message)
    assert len(warnings) == 1
    assert all(heading in warnings[0] for heading in LOST_HEADINGS)


async def test_an_agent_write_that_loses_an_extra_section_names_it(document_tools: DocumentTools) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)
    lossy = CLEAN_DESIGN + '\n## Rollout Notes\nShip behind a flag.\n---\nThen remove the flag.\n'

    message = await document_tools.update_document(DocumentType.PHASE, PHASE_KEY, lossy)

    warnings = content_loss_warnings(message)
    assert len(warnings) == 1
    assert 'Rollout Notes' in warnings[0]


async def test_a_lossless_agent_write_carries_no_content_loss_warning(document_tools: DocumentTools) -> None:
    await store_phase(document_tools, CLEAN_DESIGN)

    message = await document_tools.update_document(DocumentType.PHASE, PHASE_KEY, SEAM_OUTSIDE_LAYOUT)

    assert content_loss_warnings(message) == []
