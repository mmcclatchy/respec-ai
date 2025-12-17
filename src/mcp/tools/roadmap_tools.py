from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.base import DocumentToolsInterface
from src.models.phase import Phase
from src.models.roadmap import Roadmap
from src.utils.enums import LoopStatus
from src.utils.loop_state import MCPResponse


class RoadmapTools(DocumentToolsInterface):
    async def store(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            phase_blocks = content.split('# Phase:')
            roadmap_metadata = phase_blocks[0]

            roadmap = Roadmap.parse_markdown(roadmap_metadata)
            await self.state.store_roadmap(key, roadmap)

            # Mark existing phases as inactive before storing new ones
            await self.state.mark_phases_inactive(key)

            # Parse and store each phase individually
            phases = []
            for phase_block in phase_blocks[1:]:
                phase_markdown = f'# Phase:{phase_block}'
                phase = Phase.parse_markdown(phase_markdown)
                phases.append(phase)
                await self.state.store_phase(key, phase)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=key)
        except Exception as e:
            raise ToolError(f'Failed to store roadmap: {str(e)}')

    async def get(self, key: str | None = None, loop_id: str | None = None) -> MCPResponse:
        if not key:
            raise ToolError('Key is required for roadmaps')

        if loop_id:
            raise ToolError('Roadmaps do not support loop-based retrieval')

        try:
            roadmap = await self.state.get_roadmap(key)
            phases = await self.state.get_roadmap_phases(key)
            markdown = roadmap.build_markdown(phases)
            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=markdown, char_length=len(markdown))
        except Exception as e:
            raise ResourceError(f'Roadmap not found for project {key}: {str(e)}')

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        try:
            # Note: StateManager doesn't have list_roadmaps method, so we'll return empty
            # This can be implemented if needed
            return MCPResponse(id='roadmap', status=LoopStatus.COMPLETED, message='Roadmap listing not yet implemented')
        except Exception as e:
            raise ToolError(f'Failed to list roadmaps: {str(e)}')

    async def update(self, key: str, content: str) -> MCPResponse:
        return await self.store(key, content)

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            # Note: StateManager doesn't have delete_roadmap method
            # For now, we'll return a placeholder response
            return MCPResponse(
                id=key, status=LoopStatus.COMPLETED, message=f'Roadmap deletion not yet implemented for {key}'
            )
        except Exception as e:
            raise ToolError(f'Failed to delete roadmap: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        raise ToolError('Roadmaps do not support loop linking')
