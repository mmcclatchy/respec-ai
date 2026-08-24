"""Known defects in Phase.parse_markdown, now reported rather than silently eaten.

See docs/phase-refactor/findings.md F8, F9. Phase 3's validate_document
(Phase.find_content_loss, see test_content_loss_detection.py) does not repair
parse_markdown - the Step 9 gate flow (fix-and-retry / drop-those-edits / abort) only
makes sense if truncation still happens on the live parse path. Instead it reports the
loss, so a human hand-editing phase.md at the gate is told rather than overwritten.
"""

from src.models.phase import Phase


def test_bare_hr_truncates_section_but_validate_document_reports_it() -> None:
    # Finding F8: base.py's H2/H3 content scan stops at a bare `---` line.
    markdown = """# Phase: sample-phase

## Overview
### Objectives
Real objective content.

---

Lost content that must never appear after the separator.
"""

    phase = Phase.parse_markdown(markdown)
    issues = Phase.find_content_loss(markdown)

    assert phase.objectives == 'Real objective content.'
    assert 'Lost content' not in (phase.objectives or '')
    assert any('Objectives' in issue for issue in issues)


def test_custom_h3_under_a_mapped_h2_is_dropped_but_validate_document_reports_it() -> None:
    # Finding F9: only *unmapped* H2 sections are captured into additional_sections.
    # A custom H3 nested under an H2 the model already knows (e.g. "## Implementation")
    # has nowhere to land and vanishes on round trip.
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
This custom H3 content is silently dropped.
"""

    phase = Phase.parse_markdown(markdown)
    issues = Phase.find_content_loss(markdown)

    assert phase.testing_strategy == 'Strategy content.'
    assert 'This custom H3 content is silently dropped.' not in (phase.testing_strategy or '')
    assert not phase.additional_sections or 'My Custom Notes' not in phase.additional_sections
    for value in phase.model_dump().values():
        if isinstance(value, str):
            assert 'This custom H3 content is silently dropped.' not in value
    assert any('My Custom Notes' in issue for issue in issues)
