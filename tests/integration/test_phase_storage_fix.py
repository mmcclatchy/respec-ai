"""
Integration test to verify phases are stored in typed storage, not generic documents.

This test verifies the fix for the bug where phases were being stored in the
generic `documents` dictionary instead of the typed `phases_by_project` dictionary.
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


@pytest.fixture
def valid_phase_markdown() -> str:
    return """# Phase: phase-1-foundation

## Overview

### Objectives
- Set up project infrastructure
- Configure development environment

### Scope
This phase covers initial setup and configuration.

### Dependencies
None

### Deliverables
- Working development environment
- Project structure
"""


@pytest.mark.asyncio
async def test_phase_stored_in_typed_storage_not_generic_documents(
    document_tools: DocumentTools,
    state_manager: InMemoryStateManager,
    valid_phase_markdown: str,
) -> None:
    """
    Verify that storing a phase via store_document delegates to typed storage.

    This is a regression test for the bug where phases were stored in:
      documents=['phase/rag-poc/phase-1-foundation-and-infrastructure']

    Instead of:
      phases_by_project={'rag-poc': {'phase-1-foundation-and-infrastructure': Phase(...)}}
    """
    plan_name = 'test-plan'
    phase_name = 'phase-1-foundation'
    path = f'{plan_name}/{phase_name}'

    # Store phase via MCP tool (mimics what Task command does)
    result = await document_tools.store_document(
        DocumentType.PHASE,
        path,
        valid_phase_markdown,
    )

    # Verify success - store_phase returns the phase name
    assert result == phase_name

    # CRITICAL: Verify phase is in typed storage (not generic documents)
    assert plan_name in state_manager._phases
    assert phase_name in state_manager._phases[plan_name]

    # Verify phase object has correct data
    phase = state_manager._phases[plan_name][phase_name]
    assert phase.phase_name == phase_name
    assert 'Set up project infrastructure' in phase.objectives
    assert 'This phase covers initial setup' in phase.scope

    # Verify retrieval works
    response = await document_tools.get_document(DocumentType.PHASE, key=path)
    assert phase_name in response.message
    assert 'Objectives' in response.message


@pytest.mark.asyncio
async def test_phase_update_uses_typed_storage(
    document_tools: DocumentTools,
    state_manager: InMemoryStateManager,
    valid_phase_markdown: str,
) -> None:
    """Verify that updating a phase via update_document uses typed storage."""
    plan_name = 'test-plan'
    phase_name = 'phase-1-foundation'
    path = f'{plan_name}/{phase_name}'

    # Store initial phase
    await document_tools.store_document(DocumentType.PHASE, path, valid_phase_markdown)

    # Update with new markdown - add a non-frozen field (architecture)
    updated_markdown = (
        valid_phase_markdown
        + """
## System Design

### Architecture
This is the updated architecture for the system.
"""
    )

    result = await document_tools.update_document(DocumentType.PHASE, path, updated_markdown)

    # Verify update success - update_phase returns iteration/version info
    assert phase_name in result
    assert 'Updated phase' in result

    # Verify phase is still in typed storage with updated data
    phase = state_manager._phases[plan_name][phase_name]

    # Verify non-frozen field was updated
    assert phase.architecture is not None
    assert 'updated architecture' in phase.architecture.lower()

    # Verify frozen fields were preserved (objectives should not change)
    assert 'Set up project infrastructure' in phase.objectives

    # Verify version and iteration incremented (initial is 0, after update is 1)
    assert phase.iteration == 1
    assert phase.version == 2
