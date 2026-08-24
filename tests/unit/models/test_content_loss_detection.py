"""Phase 3 — validate_document's model-layer engine.

Findings F7-F9 (docs/phase-refactor/findings.md) mean the markdown parser silently
drops user edits in three ways. Phase 3 does not repair the parser (the workflow still
needs Step 9's fix-and-retry/drop/abort flow) - it reports the loss instead, so a human
hand-editing phase.md at the gate is told rather than silently overwritten.

Behaviors pinned: B1 (any silently-discarded edit is reported), B2 (bare '---' inside a
section, inverts Phase 0's B6), B3 (custom H3 under a mapped H2, inverts Phase 0's B7).
"""

from src.models.phase import Phase


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
