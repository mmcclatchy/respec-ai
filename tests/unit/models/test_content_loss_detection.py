"""Phase 3 — validate_document's model-layer engine.

Findings F7-F9 (docs/phase-refactor/findings.md) mean the markdown parser silently
drops user edits in three ways. Phase 3 does not repair the parser (the workflow still
needs Step 9's fix-and-retry/drop/abort flow) - it reports the loss instead, so a human
hand-editing phase.md at the gate is told rather than silently overwritten.

Behaviors pinned: B1 (any silently-discarded edit is reported), B2 (bare '---' inside a
section, inverts Phase 0's B6), B3 (custom H3 under a mapped H2, inverts Phase 0's B7).
"""

from typing import Callable

from src.models.base import MCPModel

import pytest

from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.platform.templates.agents.phase_architect import technical_phase_template


@pytest.mark.parametrize('model_class', [Phase, Plan, Roadmap])
def test_a_document_this_system_generates_never_reports_content_loss(
    model_class: type[MCPModel], markdown_builder: Callable
) -> None:
    seed_markdown = markdown_builder(model_class)
    instance = model_class.parse_markdown(seed_markdown)

    assert model_class.find_content_loss(instance.build_markdown()) == []


def test_the_shipped_phase_template_never_reports_content_loss() -> None:
    assert Phase.find_content_loss(technical_phase_template) == []


def test_a_trailing_separator_before_a_concatenated_document_is_not_reported_as_loss() -> None:
    # Real generated markdown legitimately uses a bare '---' to separate concatenated
    # documents (e.g. RoadmapTools.store splits multi-document markdown on '# Phase:').
    # See tests/unit/models/test_markdown_separator_handling.py - this is not the F8
    # defect, it is intentional structure, and must not be reported.
    markdown = """# Phase: sample-phase

## Overview
### Objectives
Real objective content.
### Scope
Some scope.
### Dependencies
Some deps.
### Deliverables
Some deliverables.

## Metadata

### Status
draft

---

# Phase: another-concatenated-phase
"""

    assert Phase.find_content_loss(markdown) == []


def test_bare_hr_inside_a_section_is_reported() -> None:
    markdown = """# Phase: sample-phase

## Overview
### Objectives
Real objective content.

---

Lost content that must never silently disappear.
"""

    issues = Phase.find_content_loss(markdown)

    assert any('Objectives' in issue for issue in issues)


def test_custom_h3_under_a_mapped_h2_is_reported() -> None:
    markdown = """# Phase: sample-phase

## Overview
### Objectives
Some objective.
### Scope
Some scope.
### Dependencies
Some deps.
### Deliverables
Some deliverables.

## Implementation
### Testing Strategy
Strategy content.

### My Custom Notes
This custom H3 content has nowhere to land.
"""

    issues = Phase.find_content_loss(markdown)

    assert any('My Custom Notes' in issue for issue in issues)


def test_clean_document_with_no_loss_reports_nothing() -> None:
    markdown = """# Phase: sample-phase

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

    issues = Phase.find_content_loss(markdown)

    assert issues == []


def test_content_loss_report_does_not_change_what_parse_markdown_extracts() -> None:
    # validate_document reports the defect; it does not fix parse_markdown. Step 9's
    # fix-and-retry/drop-those-edits/abort flow only makes sense if truncation still
    # happens on the live parse path.
    markdown = """# Phase: sample-phase

## Overview
### Objectives
Real objective content.

---

Lost content that must never silently disappear.
"""

    phase = Phase.parse_markdown(markdown)

    assert phase.objectives == 'Real objective content.'
    assert 'Lost content' not in (phase.objectives or '')


# --- Phase-cooperative phase 3, B12: content loss in additional sections and fenced headings ------
# docs/phase-cooperative/phase-3-structural-checks.md, work item 4 (findings F27 traps 1-3).

OVERVIEW_MARKDOWN = (
    '# Phase: sample-phase\n\n## Overview\n### Objectives\nSome objective.\n### Scope\nSome scope.\n'
    '### Dependencies\nSome deps.\n### Deliverables\nSome deliverables.\n'
)
WIRING = 'Design Shape > Collaboration And Wiring'


def designed_phase(wiring_extra: str = '', extra_sections: str = '', before_system_design: str = '') -> str:
    return (
        OVERVIEW_MARKDOWN
        + before_system_design
        + '\n## System Design\n### Architecture\nA ledger service and a billing service.\n'
        + '\n## Design Shape\n### Module Layout\n- `src/ledger/` — owns ledger entries\n'
        + '### Collaboration And Wiring\nBilling calls the ledger.\n'
        + wiring_extra
        + '### Test List\n- `tests/ledger_check.unit::posts an entry`\n'
        + '\n## Design Decisions\n### Settled Design Decisions\n- None\n'
        + extra_sections
    )


def fenced(*body: str, fence: str = '```') -> str:
    return '\n'.join([f'{fence}text', *body, fence]) + '\n'


def extra_section(name: str, body: str) -> str:
    return f'\n## {name}\n{body}'


def reported_headings(issues: list[str]) -> list[str]:
    return sorted(issue.split(': ', 1)[0] for issue in issues)


FENCES = [pytest.param('```', id='backtick-fence'), pytest.param('~~~', id='tilde-fence')]


def test_the_designed_fixture_reports_no_loss() -> None:
    assert Phase.find_content_loss(designed_phase()) == []


def test_a_bare_separator_inside_an_extra_section_is_reported() -> None:
    markdown = designed_phase(extra_sections=extra_section('Guardrails', 'Rule one\n---\nRule two\n'))

    assert reported_headings(Phase.find_content_loss(markdown)) == ['Guardrails']


@pytest.mark.parametrize(
    'name',
    [
        pytest.param('Design', id='captured-by-system-design'),
        pytest.param('Decisions', id='captured-by-design-decisions'),
    ],
)
def test_an_extra_section_captured_by_an_earlier_heading_containing_its_name_is_reported(name: str) -> None:
    markdown = designed_phase(extra_sections=extra_section(name, 'Notes only this section holds.\n'))

    assert reported_headings(Phase.find_content_loss(markdown)) == [name]


def test_an_extra_section_placed_before_the_heading_containing_its_name_loses_nothing() -> None:
    markdown = designed_phase(before_system_design=extra_section('Design', 'Notes only this section holds.\n'))

    assert Phase.find_content_loss(markdown) == []


@pytest.mark.parametrize('fence', FENCES)
@pytest.mark.parametrize(
    ('wiring_extra', 'extra_sections', 'heading'),
    [
        pytest.param('{fence}', '', WIRING, id='under-a-mapped-subsection'),
        pytest.param(
            '', extra_section('Guardrails', 'Rule one.\n{fence}Rule two.\n'), 'Guardrails', id='under-an-extra-section'
        ),
        pytest.param(
            '',
            extra_section('Guardrails', '### Rules\n{fence}Rule two.\n'),
            'Guardrails',
            id='under-a-subheading-of-an-extra-section',
        ),
    ],
)
def test_a_fenced_h2_line_is_reported_wherever_it_sits(
    fence: str, wiring_extra: str, extra_sections: str, heading: str
) -> None:
    block = fenced('## Example heading', 'example body', fence=fence)
    markdown = designed_phase(
        wiring_extra=wiring_extra.replace('{fence}', block), extra_sections=extra_sections.replace('{fence}', block)
    )

    assert reported_headings(Phase.find_content_loss(markdown)) == [heading]


@pytest.mark.parametrize('fence', FENCES)
@pytest.mark.parametrize(
    ('fenced_heading', 'headings'),
    [
        pytest.param('### Test List', [WIRING], id='mapped-name'),
        pytest.param('### Example', [WIRING, 'Design Shape > Example'], id='unmapped-name-also-an-orphan'),
    ],
)
def test_a_fenced_h3_line_under_a_mapped_section_is_reported(
    fence: str, fenced_heading: str, headings: list[str]
) -> None:
    markdown = designed_phase(wiring_extra=fenced(fenced_heading, '- `tests/x.unit::example`', fence=fence))

    assert reported_headings(Phase.find_content_loss(markdown)) == headings


@pytest.mark.parametrize('fence', FENCES)
def test_an_indented_heading_line_in_a_list_item_fence_is_not_reported(fence: str) -> None:
    item_fence = f'- Wire the ledger:\n  {fence}text\n  ## Example heading\n  ### Example subheading\n  {fence}\n'
    markdown = designed_phase(wiring_extra=item_fence)

    assert Phase.find_content_loss(markdown) == []


@pytest.mark.parametrize('fence', FENCES)
def test_a_fenced_h3_line_under_an_extra_section_is_not_reported(fence: str) -> None:
    body = 'Rule one.\n' + fenced('### Example heading', 'example body', fence=fence) + 'Rule two.\n'
    markdown = designed_phase(extra_sections=extra_section('Guardrails', body))

    assert Phase.find_content_loss(markdown) == []


@pytest.mark.parametrize(
    ('wiring_extra', 'extra_sections', 'heading'),
    [
        pytest.param(
            'More wiring.\n---\nLost wiring.\n' + fenced('## Example heading'), '', WIRING, id='separator-and-fence'
        ),
        pytest.param(
            '',
            extra_section('Guardrails', 'Rule one\n---\nRule two\n' + fenced('## Example heading')),
            'Guardrails',
            id='extra-section-separator-and-fence',
        ),
        pytest.param(
            fenced('## First example') + 'Between.\n' + fenced('### Second example'), '', WIRING, id='two-fences'
        ),
        pytest.param('```text\nan example its author never closed\n', '', WIRING, id='unclosed-fence'),
    ],
)
def test_each_affected_heading_is_reported_once(wiring_extra: str, extra_sections: str, heading: str) -> None:
    markdown = designed_phase(wiring_extra=wiring_extra, extra_sections=extra_sections)

    assert reported_headings(Phase.find_content_loss(markdown)) == [heading]


def test_a_phase_with_extra_sections_round_trips_without_reporting_loss() -> None:
    phase = Phase.parse_markdown(designed_phase())
    phase.additional_sections = {
        'Guardrails': '### Rules\n' + fenced('### Example heading', 'example body') + '- Keep it small.',
        'Rollout Notes': 'Ship behind a flag.',
    }

    assert Phase.find_content_loss(phase.build_markdown()) == []


@pytest.mark.parametrize('model_class', [Plan, Roadmap])
def test_plan_and_roadmap_content_loss_ignores_extra_section_checks(
    model_class: type[MCPModel], markdown_builder: Callable
) -> None:
    markdown = (
        markdown_builder(model_class)
        + extra_section('Guardrails', 'Rule one\n---\nRule two\n')
        + extra_section('Examples', fenced('## Example heading'))
    )

    assert model_class.find_content_loss(markdown) == []
