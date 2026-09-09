from fastmcp.exceptions import ResourceError, ToolError

from src.mcp.tools.base import DocumentToolsInterface
from src.models.phase import Phase
from src.models.roadmap import Roadmap
from src.utils.enums import LoopStatus
from src.utils.errors import RoadmapNotFoundError
from src.utils.loop_state import MCPResponse


class RoadmapTools(DocumentToolsInterface):
    document_model = Roadmap

    async def store(self, key: str, content: str, allow_frozen_field_edits: bool = False) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            # Parse everything before mutating anything. mark_phases_inactive deactivates
            # every phase, so a parse failure part-way through the loop used to leave the
            # project with fewer phases than it started with and no rollback (F1c).
            phase_blocks = content.split('# Phase:')
            roadmap = Roadmap.parse_markdown(phase_blocks[0])
            phases = [Phase.parse_markdown(f'# Phase:{phase_block}') for phase_block in phase_blocks[1:]]

            await self.state.store_roadmap(key, roadmap)

            # Every phase is deactivated first, so no phase written below is live and no
            # frozen field is preserved: the incoming roadmap is authoritative and there
            # is nothing to warn about here. Direct phase writes (PhaseTools) target live
            # phases and DO report discards.
            await self.state.mark_phases_inactive(key)

            for phase in phases:
                await self.state.store_phase(key, phase, allow_frozen_field_edits=allow_frozen_field_edits)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=key)
        except Exception as e:
            raise ToolError(f'Failed to store roadmap: {str(e)}')

    async def get(
        self, key: str | None = None, loop_id: str | None = None, include_phases: bool = True
    ) -> MCPResponse:
        if not key:
            raise ToolError('Key is required for roadmaps')

        if loop_id:
            raise ToolError('Roadmaps do not support loop-based retrieval')

        try:
            roadmap = await self.state.get_roadmap(key)
            phases = await self.state.get_roadmap_phases(key) if include_phases else None
            markdown = roadmap.build_markdown(phases)
            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=markdown, char_length=len(markdown))
        except Exception as e:
            raise ResourceError(f'Roadmap not found for project {key}: {str(e)}')

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        try:
            plan_names = await self.state.list_roadmaps()
            if not plan_names:
                return MCPResponse(id='roadmap', status=LoopStatus.COMPLETED, message='No roadmaps found')

            count = len(plan_names)
            return MCPResponse(
                id='roadmap',
                status=LoopStatus.COMPLETED,
                message=f'Found {count} roadmap{"s" if count != 1 else ""}: {", ".join(plan_names)}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list roadmaps: {str(e)}')

    async def update(self, key: str, content: str, allow_frozen_field_edits: bool = False) -> MCPResponse:
        return await self.store(key, content, allow_frozen_field_edits=allow_frozen_field_edits)

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            await self.state.delete_roadmap(key)
            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=f'Deleted roadmap and its phases for {key}')
        except RoadmapNotFoundError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to delete roadmap: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        raise ToolError('Roadmaps do not support loop linking')
