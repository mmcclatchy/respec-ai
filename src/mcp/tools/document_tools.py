from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from src.models.enums import DocumentType
from src.shared import state_manager
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class DocumentTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def store_document(self, doc_type: DocumentType, path: str, content: str) -> str:
        if not path:
            raise ToolError('Path cannot be empty')
        if not content:
            raise ToolError('Content cannot be empty')

        try:
            return await self.state.store_document(doc_type.value, path, content)
        except Exception as e:
            raise ToolError(f'Failed to store document: {str(e)}')

    async def get_document(
        self, doc_type: DocumentType, path: str | None = None, loop_id: str | None = None
    ) -> MCPResponse:
        try:
            if loop_id:
                loop_state = await self.state.get_loop(loop_id)
                retrieved_doc_type, content = await self.state.get_document_by_loop(loop_id)
                char_length = len(content)
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message=content,
                    char_length=char_length,
                )

            if path:
                content = await self.state.get_document(doc_type.value, path)
                char_length = len(content)
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=content,
                    char_length=char_length,
                )

            raise ToolError('Either path OR loop_id must be provided')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist or is not linked to a document')
        except ValueError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to retrieve document: {str(e)}')

    async def list_documents(self, doc_type: DocumentType, parent_path: str | None = None) -> MCPResponse:
        try:
            paths = await self.state.list_documents(doc_type.value, parent_path)
            if not paths:
                parent_msg = f' under {parent_path}' if parent_path else ''
                return MCPResponse(
                    id=f'{doc_type.value}',
                    status=LoopStatus.COMPLETED,
                    message=f'No {doc_type.value} documents found{parent_msg}',
                )

            paths_str = ', '.join(paths)
            parent_msg = f' under {parent_path}' if parent_path else ''
            return MCPResponse(
                id=f'{doc_type.value}',
                status=LoopStatus.COMPLETED,
                message=f'Found {len(paths)} {doc_type.value} document{"s" if len(paths) != 1 else ""}{parent_msg}: {paths_str}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list documents: {str(e)}')

    async def update_document(self, doc_type: DocumentType, path: str, content: str) -> str:
        if not path:
            raise ToolError('Path cannot be empty')
        if not content:
            raise ToolError('Content cannot be empty')

        try:
            return await self.state.update_document(doc_type.value, path, content)
        except ValueError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to update document: {str(e)}')

    async def delete_document(self, doc_type: DocumentType, path: str) -> MCPResponse:
        if not path:
            raise ToolError('Path cannot be empty')

        try:
            was_deleted = await self.state.delete_document(doc_type.value, path)
            if was_deleted:
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=f'Deleted {doc_type.value} document at {path}',
                )
            else:
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=f'{doc_type.value} document not found at {path}',
                )
        except Exception as e:
            raise ToolError(f'Failed to delete document: {str(e)}')

    async def link_loop_to_document(self, loop_id: str, doc_type: DocumentType, path: str) -> MCPResponse:
        if not loop_id:
            raise ToolError('Loop ID cannot be empty')
        if not path:
            raise ToolError('Path cannot be empty')

        try:
            await self.state.link_loop_to_document(loop_id, doc_type.value, path)
            loop_state = await self.state.get_loop(loop_id)
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Linked loop {loop_id} to {doc_type.value} document at {path}',
            )
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Failed to link loop to document: {str(e)}')


def register_document_tools(mcp: FastMCP) -> None:
    doc_tools = DocumentTools(state_manager)

    @mcp.tool()
    async def store_document(doc_type: DocumentType, path: str, content: str, ctx: Context) -> str:
        """Store document with hierarchical path.

        Generic document storage for Phase, Task, and CompletionReport documents.
        Uses hierarchical paths for organization (e.g., plan-name/phase-name/task-name).

        Parameters:
        - doc_type: Type of document ("phase", "task", "completion_report")
        - path: Hierarchical path (e.g., "plan-name/phase-name" or "plan-name/phase-name/task-name")
        - content: Complete document in markdown format

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Storing {doc_type.value} document at {path}')
        try:
            result = await doc_tools.store_document(doc_type, path, content)
            await ctx.info(f'Stored {doc_type.value} document at {path}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to store document: {str(e)}')
            raise

    @mcp.tool()
    async def get_document(doc_type: DocumentType, path: str | None, loop_id: str | None, ctx: Context) -> MCPResponse:
        """Retrieve document as markdown.

        Two retrieval modes:
        1. By loop_id: Retrieves document linked to active refinement loop
        2. By path: Retrieves document directly from storage

        Parameters:
        - doc_type: Type of document ("phase", "task", "completion_report")
        - path: Hierarchical path (required if not using loop_id)
        - loop_id: Loop identifier (alternative to path)

        Returns:
        - MCPResponse: Contains document markdown in message field
        """
        await ctx.info(f'Retrieving {doc_type.value} document')
        try:
            result = await doc_tools.get_document(doc_type, path, loop_id)
            await ctx.info(f'Retrieved {doc_type.value} document')
            return result
        except Exception as e:
            await ctx.error(f'Failed to retrieve document: {str(e)}')
            raise

    @mcp.tool()
    async def list_documents(doc_type: DocumentType, parent_path: str | None, ctx: Context) -> MCPResponse:
        """List documents of a type, optionally filtered by parent path.

        Examples:
        - list_documents("phase", None) → All phases
        - list_documents("phase", "plan-name") → All phases for plan
        - list_documents("task", "plan-name/phase-name") → All tasks for phase

        Parameters:
        - doc_type: Type of document ("phase", "task", "completion_report")
        - parent_path: Optional parent path to filter results

        Returns:
        - MCPResponse: Contains list of document paths in message field
        """
        parent_msg = f' under {parent_path}' if parent_path else ''
        await ctx.info(f'Listing {doc_type.value} documents{parent_msg}')
        try:
            result = await doc_tools.list_documents(doc_type, parent_path)
            await ctx.info(f'Listed {doc_type.value} documents')
            return result
        except Exception as e:
            await ctx.error(f'Failed to list documents: {str(e)}')
            raise

    @mcp.tool()
    async def update_document(doc_type: DocumentType, path: str, content: str, ctx: Context) -> str:
        """Update existing document with new content.

        Used during refinement loops when agents improve content.

        Parameters:
        - doc_type: Type of document ("phase", "task", "completion_report")
        - path: Hierarchical path to document
        - content: Updated markdown content

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Updating {doc_type.value} document at {path}')
        try:
            result = await doc_tools.update_document(doc_type, path, content)
            await ctx.info(f'Updated {doc_type.value} document at {path}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to update document: {str(e)}')
            raise

    @mcp.tool()
    async def delete_document(doc_type: DocumentType, path: str, ctx: Context) -> MCPResponse:
        """Delete document from storage.

        Parameters:
        - doc_type: Type of document ("phase", "task", "completion_report")
        - path: Hierarchical path to document

        Returns:
        - MCPResponse: Contains deletion confirmation
        """
        await ctx.info(f'Deleting {doc_type.value} document at {path}')
        try:
            result = await doc_tools.delete_document(doc_type, path)
            await ctx.info(f'Deleted {doc_type.value} document at {path}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to delete document: {str(e)}')
            raise

    @mcp.tool()
    async def link_loop_to_document(loop_id: str, doc_type: DocumentType, path: str, ctx: Context) -> MCPResponse:
        """Link active refinement loop to document for idempotent iteration.

        Creates temporary mapping allowing agents to retrieve/update documents via loop_id
        during refinement sessions. Enables idempotent architect/critic pattern.

        Parameters:
        - loop_id: Active loop identifier
        - doc_type: Type of document ("phase", "task", "completion_report")
        - path: Hierarchical path to document

        Returns:
        - MCPResponse: Contains linking confirmation
        """
        await ctx.info(f'Linking loop {loop_id} to {doc_type.value} document at {path}')
        try:
            result = await doc_tools.link_loop_to_document(loop_id, doc_type, path)
            await ctx.info(f'Linked loop {loop_id} to document')
            return result
        except Exception as e:
            await ctx.error(f'Failed to link loop to document: {str(e)}')
            raise
