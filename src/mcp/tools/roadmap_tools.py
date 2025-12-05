from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from src.models.roadmap import Roadmap
from src.models.spec import TechnicalSpec
from src.shared import state_manager
from src.utils.state_manager import StateManager


class RoadmapTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    def create_roadmap(self, project_name: str, roadmap_data: str) -> str:
        if not project_name:
            raise ToolError('Project name cannot be empty')
        if not roadmap_data:
            raise ToolError('Roadmap data cannot be empty')

        try:
            spec_blocks = roadmap_data.split('# Technical Specification:')
            roadmap_metadata = spec_blocks[0]

            roadmap = Roadmap.parse_markdown(roadmap_metadata)
            self.state.store_roadmap(project_name, roadmap)

            # Parse and store each spec individually
            specs = []
            for i, spec_block in enumerate(spec_blocks[1:], 1):
                spec_markdown = f'# Technical Specification:{spec_block}'
                spec = TechnicalSpec.parse_markdown(spec_markdown)
                specs.append(spec)
                self.state.store_spec(project_name, spec)

            return f'Created roadmap "{roadmap.project_name}" with {len(specs)} specs for project {project_name}'
        except Exception as e:
            raise ToolError(f'Failed to create roadmap: {str(e)}')

    def get_roadmap(self, project_name: str) -> str:
        if not project_name:
            raise ToolError('Project name cannot be empty')

        try:
            roadmap = self.state.get_roadmap(project_name)
            specs = self.state.get_roadmap_specs(project_name)
            return roadmap.build_markdown(specs)
        except Exception as e:
            raise ResourceError(f'Roadmap not found for project {project_name}: {str(e)}')


def register_roadmap_tools(mcp: FastMCP) -> None:
    roadmap_tools = RoadmapTools(state_manager)

    @mcp.tool()
    async def create_roadmap(project_name: str, roadmap_data: str, ctx: Context) -> str:
        """Create a new roadmap for a project.

        Parameters:
        - project_name: Name for this project
        - roadmap_data: Complete roadmap markdown content including all TechnicalSpec sections

        Returns:
        - str: Confirmation message
        """
        await ctx.info(f'Creating roadmap for project: {project_name}')
        result = roadmap_tools.create_roadmap(project_name, roadmap_data)
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
        result = roadmap_tools.get_roadmap(project_name)
        await ctx.info(f'Got roadmap for project: {project_name}')
        return result


roadmap_tools = RoadmapTools(state_manager)
