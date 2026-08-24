"""Phase 3 — the validate_document MCP tool.

Behavior B1: a user edit that the parser would silently discard is reported instead of
being swallowed. This wraps Phase.find_content_loss (see
tests/unit/models/test_content_loss_detection.py) for every document type, dispatched
the same way store_document/get_document are.
"""

import pytest

from src.mcp.tools.document_tools import DocumentTools
from src.models.enums import DocumentType
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
