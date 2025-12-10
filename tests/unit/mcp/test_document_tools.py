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
        DocumentType.PHASE: '# Phase: Test Phase\n\nPhase content here',
        DocumentType.TASK: '# Task: Test Task\n\nTask content here',
        DocumentType.COMPLETION_REPORT: '# Completion Report\n\nReport content here',
    }


@pytest.mark.parametrize(
    'doc_type',
    [
        DocumentType.PHASE,
        DocumentType.TASK,
        DocumentType.COMPLETION_REPORT,
    ],
)
class TestDocumentToolsCRUD:
    @pytest.mark.asyncio
    async def test_store_document_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test storing document works for all types"""
        path = f'test-project/{doc_type.value}-test'
        content = sample_documents[doc_type]

        result = await document_tools.store_document(doc_type, path, content)

        assert isinstance(result, str)
        assert f'Stored {doc_type.value} document at {path}' == result

    @pytest.mark.asyncio
    async def test_get_document_by_path_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test retrieving document by path works for all types"""
        path = f'test-project/{doc_type.value}-test'
        content = sample_documents[doc_type]

        await document_tools.store_document(doc_type, path, content)
        response = await document_tools.get_document(doc_type, path=path)

        assert isinstance(response, MCPResponse)
        assert response.id == path
        assert response.status == LoopStatus.COMPLETED
        assert response.message == content
        assert response.char_length == len(content)

    @pytest.mark.asyncio
    async def test_get_document_by_loop_id_success(
        self,
        document_tools: DocumentTools,
        doc_type: DocumentType,
        sample_documents: dict[DocumentType, str],
        state_manager: InMemoryStateManager,
    ) -> None:
        """Test retrieving document by loop_id works for all types"""

        path = f'test-project/{doc_type.value}-test'
        content = sample_documents[doc_type]
        loop_id = 'test-loop-123'

        # Create loop first
        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-project')

        await document_tools.store_document(doc_type, path, content)
        await document_tools.link_loop_to_document(loop_id, doc_type, path)

        response = await document_tools.get_document(doc_type, loop_id=loop_id)

        assert isinstance(response, MCPResponse)
        assert response.id == loop_id
        assert response.message == content
        assert response.char_length == len(content)

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, document_tools: DocumentTools, doc_type: DocumentType) -> None:
        response = await document_tools.list_documents(doc_type)

        assert isinstance(response, MCPResponse)
        assert response.id == doc_type.value
        assert response.status == LoopStatus.COMPLETED
        assert f'No {doc_type.value} documents found' in response.message

    @pytest.mark.asyncio
    async def test_list_documents_multiple(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test list_documents returns multiple items correctly"""
        content = sample_documents[doc_type]
        paths = [
            f'test-project/{doc_type.value}-1',
            f'test-project/{doc_type.value}-2',
            f'test-project/{doc_type.value}-3',
        ]

        for path in paths:
            await document_tools.store_document(doc_type, path, content)

        response = await document_tools.list_documents(doc_type)

        assert isinstance(response, MCPResponse)
        assert response.id == doc_type.value
        assert response.status == LoopStatus.COMPLETED
        assert f'Found 3 {doc_type.value} documents' in response.message
        for path in paths:
            assert path in response.message

    @pytest.mark.asyncio
    async def test_update_document_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test updating document works for all types"""
        path = f'test-project/{doc_type.value}-test'
        original_content = sample_documents[doc_type]
        updated_content = f'{original_content}\n\n## Updated Section'

        await document_tools.store_document(doc_type, path, original_content)
        result = await document_tools.update_document(doc_type, path, updated_content)

        assert isinstance(result, str)
        assert f'Updated {doc_type.value} document at {path}' == result

        response = await document_tools.get_document(doc_type, path=path)
        assert response.message == updated_content

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, document_tools: DocumentTools, doc_type: DocumentType, sample_documents: dict[DocumentType, str]
    ) -> None:
        """Test deleting document works for all types"""
        path = f'test-project/{doc_type.value}-test'
        content = sample_documents[doc_type]

        await document_tools.store_document(doc_type, path, content)
        response = await document_tools.delete_document(doc_type, path)

        assert isinstance(response, MCPResponse)
        assert response.id == path
        assert response.status == LoopStatus.COMPLETED
        assert f'Deleted {doc_type.value} document at {path}' == response.message

    @pytest.mark.asyncio
    async def test_link_loop_to_document_success(
        self,
        document_tools: DocumentTools,
        doc_type: DocumentType,
        sample_documents: dict[DocumentType, str],
        state_manager: InMemoryStateManager,
    ) -> None:
        """Test linking loop to document works for all types"""

        path = f'test-project/{doc_type.value}-test'
        content = sample_documents[doc_type]
        loop_id = 'test-loop-456'

        # Create loop first
        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-project')

        await document_tools.store_document(doc_type, path, content)
        result = await document_tools.link_loop_to_document(loop_id, doc_type, path)

        assert isinstance(result, MCPResponse)
        assert result.id == loop_id
        assert f'Linked loop {loop_id} to {doc_type.value} document at {path}' == result.message


@pytest.mark.parametrize(
    'method,kwargs,error_pattern',
    [
        # Empty path validation (only test empty string '', not whitespace)
        ('store_document', {'doc_type': DocumentType.PHASE, 'path': '', 'content': 'x'}, 'Path cannot be empty'),
        ('update_document', {'doc_type': DocumentType.PHASE, 'path': '', 'content': 'x'}, 'Path cannot be empty'),
        ('delete_document', {'doc_type': DocumentType.PHASE, 'path': ''}, 'Path cannot be empty'),
        # Empty content validation (only test empty string '', not whitespace)
        ('store_document', {'doc_type': DocumentType.PHASE, 'path': 'test', 'content': ''}, 'Content cannot be empty'),
        ('update_document', {'doc_type': DocumentType.PHASE, 'path': 'test', 'content': ''}, 'Content cannot be empty'),
        # Empty loop_id validation (only test empty string '', not whitespace)
        (
            'link_loop_to_document',
            {'loop_id': '', 'doc_type': DocumentType.PHASE, 'path': 'test'},
            'Loop ID cannot be empty',
        ),
        # get_document requires path OR loop_id
        (
            'get_document',
            {'doc_type': DocumentType.PHASE, 'path': None, 'loop_id': None},
            'Either path OR loop_id must be provided',
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
        DocumentType.TASK,
        DocumentType.COMPLETION_REPORT,
    ],
)
class TestDocumentToolsErrorHandling:
    @pytest.mark.asyncio
    async def test_get_document_not_found_raises_resource_error(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """ResourceError raised when document doesn't exist"""
        path = f'nonexistent/{doc_type.value}'

        with pytest.raises(ResourceError):
            await document_tools.get_document(doc_type, path=path)

    @pytest.mark.asyncio
    async def test_delete_document_not_found_returns_not_found_message(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """delete_document returns 'not found' message when document doesn't exist (doesn't raise error)"""
        path = f'nonexistent/{doc_type.value}'

        response = await document_tools.delete_document(doc_type, path)

        assert isinstance(response, MCPResponse)
        assert response.id == path
        assert response.status == LoopStatus.COMPLETED
        assert f'{doc_type.value} document not found at {path}' == response.message

    @pytest.mark.asyncio
    async def test_update_document_not_found_raises_resource_error(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """ResourceError raised when updating non-existent document"""
        path = f'nonexistent/{doc_type.value}'

        with pytest.raises(ResourceError):
            await document_tools.update_document(doc_type, path, 'new content')

    @pytest.mark.asyncio
    async def test_get_document_by_loop_id_not_found_raises_resource_error(
        self, document_tools: DocumentTools, doc_type: DocumentType
    ) -> None:
        """ResourceError raised when loop doesn't exist or isn't linked"""
        loop_id = 'nonexistent-loop'

        with pytest.raises(ResourceError, match='Loop does not exist or is not linked to a document'):
            await document_tools.get_document(doc_type, loop_id=loop_id)


@pytest.mark.parametrize(
    'doc_type,parent_path,store_count,expected_count',
    [
        (DocumentType.PHASE, None, 0, 0),  # Empty list
        (DocumentType.PHASE, None, 5, 5),  # All items
        (DocumentType.TASK, 'project-a', 3, 3),  # With parent path
        (DocumentType.COMPLETION_REPORT, None, 2, 2),  # Few items
    ],
)
@pytest.mark.asyncio
async def test_list_documents_count_filtering(
    document_tools: DocumentTools,
    doc_type: DocumentType,
    parent_path: str | None,
    store_count: int,
    expected_count: int,
    sample_documents: dict[DocumentType, str],
) -> None:
    """Test list_documents count works for all document types"""
    content = sample_documents[doc_type]

    for i in range(store_count):
        if parent_path:
            path = f'{parent_path}/{doc_type.value}-{i}'
        else:
            path = f'{doc_type.value}-{i}'
        await document_tools.store_document(doc_type, path, content)

    response = await document_tools.list_documents(doc_type, parent_path)

    assert isinstance(response, MCPResponse)
    if expected_count == 0:
        assert f'No {doc_type.value} documents found' in response.message
    else:
        assert f'Found {expected_count} {doc_type.value}' in response.message


@pytest.mark.parametrize(
    'doc_type,retrieval_mode',
    [
        (DocumentType.PHASE, 'path'),
        (DocumentType.PHASE, 'loop_id'),
        (DocumentType.TASK, 'path'),
        (DocumentType.TASK, 'loop_id'),
        (DocumentType.COMPLETION_REPORT, 'path'),
        (DocumentType.COMPLETION_REPORT, 'loop_id'),
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
    """Test both path-based and loop_id-based retrieval"""

    path = f'test/{doc_type.value}'
    content = sample_documents[doc_type]
    loop_id = f'loop-{doc_type.value}'

    await document_tools.store_document(doc_type, path, content)

    if retrieval_mode == 'path':
        response = await document_tools.get_document(doc_type, path=path)
        assert response.id == path
        assert response.status == LoopStatus.COMPLETED
    else:  # loop_id mode
        # Create loop first
        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-project')

        await document_tools.link_loop_to_document(loop_id, doc_type, path)
        response = await document_tools.get_document(doc_type, loop_id=loop_id)
        assert response.id == loop_id

    assert response.message == content
    assert response.char_length == len(content)


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
    path = f'test/{doc_type.value}'
    content = sample_documents[doc_type]
    loop_id = 'test-loop'

    if operation in ('get_document', 'update_document', 'delete_document', 'link_loop_to_document'):
        await document_tools.store_document(doc_type, path, content)

    if operation == 'link_loop_to_document':
        # Create loop first
        loop_state = LoopState(id=loop_id, loop_type=LoopType.PHASE)
        await state_manager.add_loop(loop_state, 'test-project')

    result: str | MCPResponse
    if operation == 'store_document':
        result = await document_tools.store_document(doc_type, path, content)
    elif operation == 'get_document':
        result = await document_tools.get_document(doc_type, path=path)
    elif operation == 'update_document':
        result = await document_tools.update_document(doc_type, path, f'{content}\nUpdated')
    elif operation == 'delete_document':
        result = await document_tools.delete_document(doc_type, path)
    elif operation == 'list_documents':
        result = await document_tools.list_documents(doc_type)
    elif operation == 'link_loop_to_document':
        result = await document_tools.link_loop_to_document(loop_id, doc_type, path)
    else:
        raise ValueError(f'Unknown operation: {operation}')

    assert status_check(result)
