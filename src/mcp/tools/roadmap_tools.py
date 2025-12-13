from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from src.models.phase import Phase
from src.models.roadmap import Roadmap
from src.shared import state_manager
from src.utils.state_manager import StateManager


class RoadmapTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def create_roadmap(self, project_name: str, roadmap_data: str) -> str:
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not roadmap_data:
            raise ToolError('Roadmap data cannot be empty')

        try:
            phase_blocks = roadmap_data.split('# Phase:')
            roadmap_metadata = phase_blocks[0]

            roadmap = Roadmap.parse_markdown(roadmap_metadata)
            await self.state.store_roadmap(project_name, roadmap)

            # Mark existing phases as inactive before storing new ones
            inactive_count = await self.state.mark_phases_inactive(project_name)
            if inactive_count > 0:
                print(f'Marked {inactive_count} existing phases as inactive')

            # Parse and store each phase individually
            phases = []
            for i, phase_block in enumerate(phase_blocks[1:], 1):
                phase_markdown = f'# Phase:{phase_block}'
                phase = Phase.parse_markdown(phase_markdown)
                phases.append(phase)
                await self.state.store_phase(project_name, phase)

            return f'Created roadmap "{roadmap.project_name}" with {len(phases)} phases for project {project_name}'
        except Exception as e:
            raise ToolError(f'Failed to create roadmap: {str(e)}')

    async def get_roadmap(self, project_name: str) -> str:
        if not project_name:
            raise ToolError('Project name cannot be empty')

        try:
            roadmap = await self.state.get_roadmap(project_name)
            phases = await self.state.get_roadmap_phases(project_name)
            return roadmap.build_markdown(phases)
        except Exception as e:
            raise ResourceError(f'Roadmap not found for project {project_name}: {str(e)}')


def register_roadmap_tools(mcp: FastMCP) -> None:
    roadmap_tools = RoadmapTools(state_manager)

    @mcp.tool()
    async def create_roadmap(project_name: str, roadmap_data: str, ctx: Context) -> str:
        """Create a new roadmap for a project.

        Parameters:
        - project_name: Name for this project
        - roadmap_data: Complete roadmap markdown content including all Phase sections

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Creating roadmap for project: {project_name}')
        result = await roadmap_tools.create_roadmap(project_name, roadmap_data)
        await ctx.info(f'Created roadmap for project: {project_name}')
        return result

    @mcp.tool()
    async def get_roadmap(project_name: str, ctx: Context) -> str:
        """Retrieve roadmap as markdown.

        Parameters:
        - project_name: Name of the project

        Returns:
        - str: Roadmap markdown
        """
        await ctx.info(f'Getting roadmap for project: {project_name}')
        result = await roadmap_tools.get_roadmap(project_name)
        await ctx.info(f'Got roadmap for project: {project_name}')
        return result


roadmap_tools = RoadmapTools(state_manager)
