import pytest
from typing import Callable
from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.document_tools import DocumentTools
from src.models.enums import DocumentType
from src.utils.enums import LoopStatus
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import InMemoryStateManager

from src.utils.loop_state import LoopState, LoopType


@pytest.fixture
def state_manager() -> InMemoryStateManager:
    return InMemoryStateManager(max_history_size=3)


@pytest.fixture
def document_tools(state_manager: InMemoryStateManager) -> DocumentTools:
    return DocumentTools(state_manager)


@pytest.fixture
def sample_documents() -> dict[DocumentType, str]:
    return {
        DocumentType.PHASE: """# Phase: test-phase

## Overview

### Objectives
- Test objective 1
- Test objective 2

### Scope
Test scope description

### Dependencies
None

### Deliverables
- Test deliverable 1
- Test deliverable 2
""",
    }


@pytest.mark.parametrize(
    'doc_type',
    [
        DocumentType.PHASE,
    ],
)
class TestDocumentToolsCRUD:
    @pytest.mark.asyncio
    async def test_store_document_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test storing document works for all types"""
        key = 'test-plan/test-phase'

        content = sample_documents[doc_type]

        result = await document_tools.store_document(doc_type, key, content)

        assert isinstance(result, str)
        assert result == 'test-phase'

    @pytest.mark.asyncio
    async def test_get_document_by_key_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test retrieving document by key works for all types"""
        key = 'test-plan/test-phase'

        content = sample_documents[doc_type]

        await document_tools.store_document(doc_type, key, content)
        response = await document_tools.get_document(doc_type, key=key)

        assert isinstance(response, MCPResponse)
        assert response.id == key
        assert response.status == LoopStatus.COMPLETED
        assert 'test-phase' in response.message
        assert response.char_length is not None and response.char_length > 0

    @pytest.mark.asyncio
    async def test_get_document_by_loop_id_success(
        self,
        document_tools: DocumentTools,
        doc_type: DocumentType,
        sample_documents: dict[DocumentType, str],
        state_manager: InMemoryStateManager,
    ) -> None:
        """Test retrieving document by loop_id works for all types"""
        key = 'test-plan/test-phase'

        content = sample_documents[doc_type]
        loop_id = 'a1b2c3d4'  # UUID first section format

        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-plan')

        await document_tools.store_document(doc_type, key, content)
        await document_tools.link_loop_to_document(loop_id, doc_type, key)

        response = await document_tools.get_document(doc_type, loop_id=loop_id)

        assert isinstance(response, MCPResponse)
        assert response.id == loop_id
        assert 'test-phase' in response.message
        assert response.char_length is not None and response.char_length > 0

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, document_tools: DocumentTools, doc_type: DocumentType) -> None:
        parent_key = 'test-plan'
        response = await document_tools.list_documents(doc_type, parent_key=parent_key)

        assert isinstance(response, MCPResponse)
        assert response.id == doc_type.value
        assert response.status == LoopStatus.COMPLETED
        assert f'No {doc_type.value} documents found' in response.message

    @pytest.mark.asyncio
    async def test_list_documents_multiple(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test list_documents returns multiple items correctly"""
        parent_key = 'test-plan'
        items = []
        for i in range(1, 4):
            phase_name = f'test-phase-{i}'
            content = f"""# Phase: {phase_name}

## Overview

### Objectives
- Test objective {i}

### Scope
Test scope {i}

### Dependencies
None

### Deliverables
- Test deliverable {i}
"""
            items.append((f'test-plan/{phase_name}', content, phase_name))

        for key, content, name in items:
            await document_tools.store_document(doc_type, key, content)

        response = await document_tools.list_documents(doc_type, parent_key=parent_key)

        assert isinstance(response, MCPResponse)
        assert response.id == doc_type.value
        assert response.status == LoopStatus.COMPLETED
        assert f'Found 3 {doc_type.value} documents' in response.message
        for key, _, _ in items:
            assert key in response.message

    @pytest.mark.asyncio
    async def test_update_document_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test updating document works for all types"""
        key = 'test-plan/test-phase'

        original_content = sample_documents[doc_type]

        await document_tools.store_document(doc_type, key, original_content)

        updated_content = (
            original_content
            + """
## System Design

### Architecture
Updated architecture description
"""
        )

        result = await document_tools.update_document(doc_type, key, updated_content)

        assert isinstance(result, str)
        assert 'test-phase' in result
        assert 'Updated phase' in result

        response = await document_tools.get_document(doc_type, key=key)
        assert 'Updated architecture' in response.message

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test deleting document works for all types"""
        key = 'test-plan/test-phase'

        content = sample_documents[doc_type]

        await document_tools.store_document(doc_type, key, content)
        response = await document_tools.delete_document(doc_type, key)

        assert isinstance(response, MCPResponse)
        assert response.id == key
        assert response.status == LoopStatus.COMPLETED
        assert f'Deleted {doc_type.value} document at {key}' == response.message

    @pytest.mark.asyncio
    async def test_link_loop_to_document_success(
        self,
        document_tools: DocumentTools,
        doc_type: DocumentType,
        sample_documents: dict[DocumentType, str],
        state_manager: InMemoryStateManager,
    ) -> None:
        """Test linking loop to document works for all types"""
        key = 'test-plan/test-phase'

        content = sample_documents[doc_type]
        loop_id = 'b2c3d4e5'  # UUID first section format

        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-plan')

        await document_tools.store_document(doc_type, key, content)
        result = await document_tools.link_loop_to_document(loop_id, doc_type, key)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert f'Linked loop {loop_id} to {doc_type.value} document at {key}' == result.message


@pytest.mark.parametrize(
    'method,kwargs,error_pattern',
    [
        (
            'store_document',
            {'doc_type': DocumentType.PHASE, 'key': '', 'content': 'x'},
            'key and content cannot be empty',
        ),
        (
            'update_document',
            {'doc_type': DocumentType.PHASE, 'key': '', 'content': 'x'},
            'Key and content cannot be empty',
        ),
        ('delete_document', {'doc_type': DocumentType.PHASE, 'key': ''}, 'Key cannot be empty'),
        (
            'store_document',
            {'doc_type': DocumentType.PHASE, 'key': 'test', 'content': ''},
            'key and content cannot be empty',
        ),
        (
            'update_document',
            {'doc_type': DocumentType.PHASE, 'key': 'test', 'content': ''},
            'Key and content cannot be empty',
        ),
        (
            'link_loop_to_document',
            {'loop_id': '', 'doc_type': DocumentType.PHASE, 'key': 'test'},
            'Loop ID and key cannot be empty',
        ),
        (
            'get_document',
            {'doc_type': DocumentType.PHASE, 'key': None, 'loop_id': None},
            'Either key OR loop_id must be provided',
        ),
    ],
)
@pytest.mark.asyncio
async def test_validation_errors(document_tools: DocumentTools, method: str, kwargs: dict, error_pattern: str) -> None:
    with pytest.raises(ToolError, match=error_pattern):
        await getattr(document_tools, method)(**kwargs)


@pytest.mark.parametrize(
    'doc_type',
    [
        DocumentType.PHASE,
    ],
)
class TestDocumentToolsErrorHandling:
    @pytest.mark.asyncio
    async def test_get_document_not_found_raises_resource_error(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """ResourceError raised when document doesn't exist"""
        key = 'nonexistent/phase'

        with pytest.raises(ResourceError):
            await document_tools.get_document(doc_type, key=key)

    @pytest.mark.asyncio
    async def test_delete_document_not_found_returns_not_found_message(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """delete_document returns 'not found' message when document doesn't exist"""
        key = 'nonexistent/phase'

        response = await document_tools.delete_document(doc_type, key)

        assert isinstance(response, MCPResponse)
        assert response.id == key
        assert response.status == LoopStatus.COMPLETED
        assert f'{doc_type.value} document not found at {key}' == response.message

    @pytest.mark.asyncio
    async def test_update_document_not_found_raises_resource_error(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """ResourceError raised when updating non-existent document"""
        key = 'nonexistent/phase'

        with pytest.raises((ResourceError, ToolError)):
            await document_tools.update_document(doc_type, key, 'new content')

    @pytest.mark.asyncio
    async def test_get_document_by_loop_id_not_found_raises_resource_error(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """ResourceError raised when loop doesn't exist or isn't linked"""
        loop_id = 'deadbeef'  # UUID first section format

        with pytest.raises(ResourceError, match='Loop does not exist or is not linked to a document'):
            await document_tools.get_document(doc_type, loop_id=loop_id)


@pytest.mark.parametrize(
    'doc_type,parent_key,store_count,expected_count',
    [
        (DocumentType.PHASE, 'test-plan', 0, 0),
        (DocumentType.PHASE, 'test-plan', 5, 5),
    ],
)
@pytest.mark.asyncio
async def test_list_documents_count_filtering(
    document_tools: DocumentTools,
    doc_type: DocumentType,
    parent_key: str,
    store_count: int,
    expected_count: int,
) -> None:
    """Test list_documents count works for all document types"""

    for i in range(1, store_count + 1):
        phase_name = f'test-phase-{i}'
        content = f"""# Phase: {phase_name}

## Overview

### Objectives
- Test objective {i}

### Scope
Test scope description {i}

### Dependencies
None

### Deliverables
- Test deliverable {i}
"""
        key = f'{parent_key}/{phase_name}'

        await document_tools.store_document(doc_type, key, content)

    response = await document_tools.list_documents(doc_type, parent_key)

    assert isinstance(response, MCPResponse)
    if expected_count == 0:
        assert f'No {doc_type.value} documents found' in response.message
    else:
        assert f'Found {expected_count} {doc_type.value}' in response.message


@pytest.mark.parametrize(
    'doc_type,retrieval_mode',
    [
        (DocumentType.PHASE, 'key'),
        (DocumentType.PHASE, 'loop_id'),
    ],
)
@pytest.mark.asyncio
async def test_get_document_retrieval_modes(
    document_tools: DocumentTools,
    doc_type: DocumentType,
    retrieval_mode: str,
    sample_documents: dict[DocumentType, str],
    state_manager: InMemoryStateManager,
) -> None:
    """Test both key-based and loop_id-based retrieval"""

    key = 'test-plan/test-phase'

    content = sample_documents[doc_type]
    loop_id = 'c3d4e5f6'  # UUID first section format

    await document_tools.store_document(doc_type, key, content)

    if retrieval_mode == 'key':
        response = await document_tools.get_document(doc_type, key=key)
        assert response.id == key
        assert response.status == LoopStatus.COMPLETED
    else:  # loop_id mode
        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-plan')

        await document_tools.link_loop_to_document(loop_id, doc_type, key)
        response = await document_tools.get_document(doc_type, loop_id=loop_id)
        assert response.id == loop_id

    assert 'test-phase' in response.message
    assert 'Objectives' in response.message
    assert response.char_length is not None and response.char_length > 0


@pytest.mark.parametrize(
    'operation,status_check',
    [
        ('store_document', lambda r: isinstance(r, str)),
        ('get_document', lambda r: isinstance(r, MCPResponse) and r.status == LoopStatus.COMPLETED),
        ('update_document', lambda r: isinstance(r, str)),
        ('delete_document', lambda r: isinstance(r, MCPResponse) and r.status == LoopStatus.COMPLETED),
        ('list_documents', lambda r: isinstance(r, MCPResponse) and r.status == LoopStatus.COMPLETED),
        ('link_loop_to_document', lambda r: isinstance(r, MCPResponse)),
    ],
)
@pytest.mark.asyncio
async def test_mcp_response_structure(
    document_tools: DocumentTools,
    operation: str,
    status_check: Callable,
    sample_documents: dict[DocumentType, str],
    state_manager: InMemoryStateManager,
) -> None:
    """All operations return well-formed responses"""

    doc_type = DocumentType.PHASE
    key = 'test-plan/test-phase'
    content = sample_documents[doc_type]
    loop_id = 'd4e5f6a7'  # UUID first section format

    if operation in ('get_document', 'update_document', 'delete_document', 'link_loop_to_document'):
        await document_tools.store_document(doc_type, key, content)

    if operation == 'link_loop_to_document':
        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-plan')

    result: str | MCPResponse
    if operation == 'store_document':
        result = await document_tools.store_document(doc_type, key, content)
    elif operation == 'get_document':
        result = await document_tools.get_document(doc_type, key=key)
    elif operation == 'update_document':
        updated_content = (
            content
            + """
## System Design

### Architecture
Updated architecture description
"""
        )
        result = await document_tools.update_document(doc_type, key, updated_content)
    elif operation == 'delete_document':
        result = await document_tools.delete_document(doc_type, key)
    elif operation == 'list_documents':
        result = await document_tools.list_documents(doc_type, parent_key='test-plan')
    elif operation == 'link_loop_to_document':
        result = await document_tools.link_loop_to_document(loop_id, doc_type, key)
    else:
        raise ValueError(f'Unknown operation: {operation}')

    assert status_check(result)
