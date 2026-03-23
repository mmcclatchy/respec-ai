from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from src.mcp.tools.base import DocumentToolsInterface
from src.mcp.tools.phase_tools import PhaseTools
from src.mcp.tools.plan_tools import PlanTools
from src.mcp.tools.roadmap_tools import RoadmapTools
from src.mcp.tools.task_tools import TaskTools
from src.models.enums import DocumentType
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class DocumentTools:
    def __init__(self, state: StateManager) -> None:
        self.plan_tools = PlanTools(state)
        self.roadmap_tools = RoadmapTools(state)
        self.phase_tools = PhaseTools(state)
        self.task_tools = TaskTools(state)

        self._tool_map: dict[DocumentType, DocumentToolsInterface] = {
            DocumentType.PLAN: self.plan_tools,
            DocumentType.ROADMAP: self.roadmap_tools,
            DocumentType.PHASE: self.phase_tools,
            DocumentType.TASK_BREAKDOWN: self.task_tools,
            DocumentType.TASK: self.task_tools,
        }

    async def store_document(self, doc_type: DocumentType, key: str, content: str) -> str:
        if not key or not content:
            raise ToolError('key and content cannot be empty')

        tool = self._tool_map.get(doc_type)
        if not tool:
            raise ToolError(f'Unknown document type: {doc_type}')

        response = await tool.store(key, content)
        return response.message

    async def get_document(
        self, doc_type: DocumentType, key: str | None = None, loop_id: str | None = None
    ) -> MCPResponse:
        if not key and not loop_id:
            raise ToolError('Either key OR loop_id must be provided')

        tool = self._tool_map.get(doc_type)
        if not tool:
            raise ToolError(f'Unknown document type: {doc_type}')

        return await tool.get(key, loop_id)

    async def list_documents(self, doc_type: DocumentType, parent_key: str | None = None) -> MCPResponse:
        tool = self._tool_map.get(doc_type)
        if not tool:
            raise ToolError(f'Unknown document type: {doc_type}')

        return await tool.list(parent_key)

    async def update_document(self, doc_type: DocumentType, key: str, content: str) -> str:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        tool = self._tool_map.get(doc_type)
        if not tool:
            raise ToolError(f'Unknown document type: {doc_type}')

        response = await tool.update(key, content)
        return response.message

    async def delete_document(self, doc_type: DocumentType, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        tool = self._tool_map.get(doc_type)
        if not tool:
            raise ToolError(f'Unknown document type: {doc_type}')
        return await tool.delete(key)

    async def link_loop_to_document(self, loop_id: str, doc_type: DocumentType, key: str) -> MCPResponse:
        if not loop_id or not key:
            raise ToolError('Loop ID and key cannot be empty')

        tool = self._tool_map.get(doc_type)
        if not tool:
            raise ToolError(f'Unknown document type: {doc_type}')
        return await tool.link_loop(loop_id, key)


def register_document_tools(mcp: FastMCP) -> None:
    _tools: DocumentTools | None = None

    def _get_tools(ctx: Context) -> DocumentTools:
        nonlocal _tools
        if _tools is None:
            _tools = DocumentTools(ctx.lifespan_context['state_manager'])
        return _tools

    @mcp.tool()
    async def store_document(doc_type: DocumentType, key: str, content: str, ctx: Context) -> str:
        """Store document with hierarchical key.

        Generic document storage for Plan, Roadmap, Phase, and Task documents.
        Uses hierarchical keys for organization (e.g., plan-name/phase-name/task-name).

        Parameters:
        - doc_type: Type of document ("phase", "task", "roadmap")
        - key: Hierarchical key (e.g., "plan-name/phase-name" or "plan-name/phase-name/task-name")
        - content: Complete document in markdown format

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Storing {doc_type.value} document at {key}')
        try:
            result = await _get_tools(ctx).store_document(doc_type, key, content)
            await ctx.info(f'Stored {doc_type.value} document at {key}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to store document: {str(e)}')
            raise

    @mcp.tool()
    async def get_document(doc_type: DocumentType, key: str | None, loop_id: str | None, ctx: Context) -> MCPResponse:
        """Retrieve document as markdown.

        Two retrieval modes:
        1. By loop_id: Retrieves document linked to active refinement loop
        2. By key: Retrieves document directly from storage

        Parameters:
        - doc_type: Type of document ("phase", "task", "roadmap")
        - key: Hierarchical key (required if not using loop_id)
        - loop_id: Loop identifier (alternative to key)

        Returns:
        - MCPResponse: Contains document markdown in message field
        """
        await ctx.info(f'Retrieving {doc_type.value} document')
        try:
            result = await _get_tools(ctx).get_document(doc_type, key, loop_id)
            await ctx.info(f'Retrieved {doc_type.value} document')
            return result
        except Exception as e:
            await ctx.error(f'Failed to retrieve document: {str(e)}')
            raise

    @mcp.tool()
    async def list_documents(doc_type: DocumentType, parent_key: str | None, ctx: Context) -> MCPResponse:
        """List documents of a type, optionally filtered by parent key.

        Examples:
        - list_documents("phase", None) → All phases
        - list_documents("phase", "plan-name") → All phases for plan
        - list_documents("task", "plan-name/phase-name") → All tasks for phase

        Parameters:
        - doc_type: Type of document ("phase", "task", "roadmap")
        - parent_key: Optional parent key to filter results

        Returns:
        - MCPResponse: Contains list of document keys in message field
        """
        parent_msg = f' under {parent_key}' if parent_key else ''
        await ctx.info(f'Listing {doc_type.value} documents{parent_msg}')
        try:
            result = await _get_tools(ctx).list_documents(doc_type, parent_key)
            await ctx.info(f'Listed {doc_type.value} documents')
            return result
        except Exception as e:
            await ctx.error(f'Failed to list documents: {str(e)}')
            raise

    @mcp.tool()
    async def update_document(doc_type: DocumentType, key: str, content: str, ctx: Context) -> str:
        """Update existing document with new content.

        Used during refinement loops when agents improve content.

        Parameters:
        - doc_type: Type of document ("phase", "task", "roadmap")
        - key: Hierarchical key to document
        - content: Updated markdown content

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Updating {doc_type.value} document at {key}')
        try:
            result = await _get_tools(ctx).update_document(doc_type, key, content)
            await ctx.info(f'Updated {doc_type.value} document at {key}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to update document: {str(e)}')
            raise

    @mcp.tool()
    async def delete_document(doc_type: DocumentType, key: str, ctx: Context) -> MCPResponse:
        """Delete document from storage.

        Parameters:
        - doc_type: Type of document ("phase", "task", "roadmap")
        - key: Hierarchical key to document

        Returns:
        - MCPResponse: Contains deletion confirmation
        """
        await ctx.info(f'Deleting {doc_type.value} document at {key}')
        try:
            result = await _get_tools(ctx).delete_document(doc_type, key)
            await ctx.info(f'Deleted {doc_type.value} document at {key}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to delete document: {str(e)}')
            raise

    @mcp.tool()
    async def link_loop_to_document(loop_id: str, doc_type: DocumentType, key: str, ctx: Context) -> MCPResponse:
        """Link active refinement loop to document for idempotent iteration.

        Creates temporary mapping allowing agents to retrieve/update documents via loop_id
        during refinement sessions. Enables idempotent architect/critic pattern.

        Parameters:
        - loop_id: Active loop identifier
        - doc_type: Type of document ("phase", "task", "roadmap")
        - key: Hierarchical key to document

        Returns:
        - MCPResponse: Contains linking confirmation
        """
        await ctx.info(f'Linking loop {loop_id} to {doc_type.value} document at {key}')
        try:
            result = await _get_tools(ctx).link_loop_to_document(loop_id, doc_type, key)
            await ctx.info(f'Linked loop {loop_id} to document')
            return result
        except Exception as e:
            await ctx.error(f'Failed to link loop to document: {str(e)}')
            raise

    # Dedicated roadmap tools to prevent loop_id misuse
    @mcp.tool()
    async def get_roadmap(plan_name: str, ctx: Context) -> MCPResponse:
        """Retrieve roadmap as markdown.

        Parameters:
        - plan_name: Name of the project

        Returns:
        - MCPResponse: Contains roadmap markdown
        """
        await ctx.info(f'Retrieving roadmap for plan: {plan_name}')
        try:
            result = await _get_tools(ctx).get_document(DocumentType.ROADMAP, key=plan_name, loop_id=None)
            await ctx.info(f'Retrieved roadmap for plan: {plan_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to retrieve roadmap: {str(e)}')
            raise

    @mcp.tool()
    async def create_roadmap(plan_name: str, roadmap_data: str, ctx: Context) -> str:
        """Create a new roadmap for a project.

        Parameters:
        - plan_name: Name for this project
        - roadmap_data: Complete roadmap markdown content including all Phase sections

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Creating roadmap for plan: {plan_name}')
        try:
            result = await _get_tools(ctx).store_document(DocumentType.ROADMAP, key=plan_name, content=roadmap_data)
            await ctx.info(f'Created roadmap for plan: {plan_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to create roadmap: {str(e)}')
            raise
