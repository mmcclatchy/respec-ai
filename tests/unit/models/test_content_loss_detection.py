"""Phase 3 — validate_document's model-layer engine.

Findings F7-F9 (docs/phase-refactor/findings.md) mean the markdown parser silently
drops user edits in three ways. Phase 3 does not repair the parser (the workflow still
needs Step 9's fix-and-retry/drop/abort flow) - it reports the loss instead, so a human
hand-editing phase.md at the gate is told rather than silently overwritten.

Behaviors pinned: B1 (any silently-discarded edit is reported), B2 (bare '---' inside a
section, inverts Phase 0's B6), B3 (custom H3 under a mapped H2, inverts Phase 0's B7).
"""

from typing import Callable

import pytest

from src.models.phase import Phase
from src.models.plan import Plan
from src.models.roadmap import Roadmap
from src.models.task import Task
from src.platform.templates.commands.phase_command import technical_phase_template


@pytest.mark.parametrize('model_class', [Phase, Plan, Roadmap, Task])
def test_a_document_this_system_generates_never_reports_content_loss(
    model_class, markdown_builder: Callable
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
