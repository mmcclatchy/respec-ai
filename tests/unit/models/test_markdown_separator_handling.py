"""Test markdown separator (---) handling in MCPModel parsing.

This test suite verifies that the markdown parser correctly handles
the markdown separator (---) as a section boundary, preventing it
from being included in field values.

Context:
- Roadmap agent was generating markdown with --- separators between sections
- Parser was including --- in the status field value ('draft\n\n---')
- Fix: Treat --- as a section boundary, similar to headers

Regression prevention: If these tests fail, the parser has regressed
and will fail to parse agent-generated markdown with --- separators.
"""

from src.models.phase import Phase
from src.models.roadmap import Roadmap


class TestMarkdownSeparatorHandling:
    def test_phase_status_field_stops_at_markdown_separator(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
Test objectives

### Scope
Test scope

### Dependencies
None

### Deliverables
Test deliverable

## Metadata

### Iteration
0

### Version
1

### Status
draft

---

# Next section after separator
"""
        phase = Phase.parse_markdown(markdown)

        assert phase.phase_status.value == 'draft'
        assert '---' not in str(phase.phase_status.value)

    def test_roadmap_status_field_stops_at_markdown_separator(self) -> None:
        markdown = """# Plan Roadmap: test-project

## Plan Details

### Plan Goal
Test goal

### Total Duration
1 week

### Team Size
1 developer

### Budget
None

## Risk Assessment

### Critical Path Analysis
None

### Key Risks
None

### Mitigation Plans
None

### Buffer Time
None

## Resource Planning

### Development Resources
None

### Infrastructure Requirements
None

### External Dependencies
None

### Quality Assurance Plan
None

## Success Metrics

### Technical Milestones
None

### Business Milestones
None

### Quality Gates
None

### Performance Targets
None

## Metadata

### Status
draft

---

# Phase: test-phase
"""
        roadmap = Roadmap.parse_markdown(markdown)

        assert roadmap.roadmap_status.value == 'draft'
        assert '---' not in str(roadmap.roadmap_status.value)

    def test_phase_without_separator_still_works(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
Test objectives

### Scope
Test scope

### Dependencies
None

### Deliverables
Test deliverable

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""
        phase = Phase.parse_markdown(markdown)

        assert phase.phase_status.value == 'draft'
        assert phase.phase_name == 'test-phase'

    def test_content_field_stops_at_markdown_separator(self) -> None:
        markdown = """# Phase: test-phase

## Overview

### Objectives
These are the objectives

---

### Scope
Test scope

### Dependencies
None

### Deliverables
Test deliverable

## Metadata

### Iteration
0

### Version
1

### Status
draft
"""
        phase = Phase.parse_markdown(markdown)

        objectives = phase.objectives.strip()
        assert objectives == 'These are the objectives'
        assert '---' not in objectives
