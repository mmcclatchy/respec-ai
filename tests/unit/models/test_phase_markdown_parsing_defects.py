"""Known defects in Phase.parse_markdown, pinned so Phase 3's validate_document has a
concrete test to flip once it repairs them.

See docs/phase-refactor/findings.md F8, F9 and testing.md's guidance on inverted tests:
these assert today's defective behavior on purpose, not the desired behavior, because a
human will be hand-editing phase.md at the Phase 3 gate and silently losing content is
strictly worse than the current opacity.
"""

from src.models.phase import Phase


def test_bare_hr_truncates_section_KNOWN_DEFECT_inverted_in_phase_3() -> None:
    # Finding F8: base.py's H2/H3 content scan stops at a bare `---` line. Phase 3's
    # validate_document is expected to repair this (e.g. by requiring `---` to only
    # appear as YAML frontmatter delimiters, or by scanning structurally instead of by
    # line). When it does, invert this assertion to check the lost content survives.
    markdown = """# Phase: sample-phase

## Overview
### Objectives
Real objective content.

---

Lost content that must never appear after the separator.
"""

    phase = Phase.parse_markdown(markdown)

    assert phase.objectives == 'Real objective content.'
    assert 'Lost content' not in (phase.objectives or '')


def test_custom_h3_under_a_mapped_h2_is_dropped_KNOWN_DEFECT_inverted_in_phase_3() -> None:
    # Finding F9: only *unmapped* H2 sections are captured into additional_sections.
    # A custom H3 nested under an H2 the model already knows (e.g. "## Implementation")
    # has nowhere to land and vanishes on round trip. Phase 3's validate_document is
    # expected to capture these; when it does, invert this assertion to check the
    # custom H3 content is preserved somewhere.
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

    assert phase.testing_strategy == 'Strategy content.'
    assert 'This custom H3 content is silently dropped.' not in (phase.testing_strategy or '')
    assert not phase.additional_sections or 'My Custom Notes' not in phase.additional_sections
    for value in phase.model_dump().values():
        if isinstance(value, str):
            assert 'This custom H3 content is silently dropped.' not in value
