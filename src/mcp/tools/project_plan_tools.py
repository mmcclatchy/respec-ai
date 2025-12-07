from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.models.project_plan import ProjectPlan
from src.shared import state_manager
from src.utils.enums import LoopStatus
from src.utils.errors import ProjectPlanNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class ProjectPlanTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state

    async def create_project_plan(self, project_name: str, project_plan: ProjectPlan) -> MCPResponse:
        try:
            if project_plan is None:
                raise ValueError('ProjectPlan cannot be None')

            if not project_name:
                raise ValueError('Project name cannot be empty')

            await self.state.store_project_plan(project_name, project_plan)
            return MCPResponse(
                id=project_name,
                status=LoopStatus.INITIALIZED,
                message=f'Created project plan: {project_name}',
            )
        except ValidationError:
            raise ToolError('Invalid project plan data provided')
        except ValueError as e:
            raise ToolError(f'Invalid project plan: {str(e)}')
        except Exception as e:
            raise ToolError(f'Unexpected error creating project plan: {str(e)}')

    async def store_project_plan(self, project_name: str, project_plan: ProjectPlan) -> MCPResponse:
        try:
            if project_plan is None:
                raise ValueError('ProjectPlan cannot be None')
            if not project_name:
                raise ValueError('Project name cannot be empty')

            await self.state.store_project_plan(project_name, project_plan)
            return MCPResponse(
                id=project_name,
                status=LoopStatus.IN_PROGRESS,
                message=f'Stored project plan: {project_plan.project_name}',
            )
        except ValidationError:
            raise ToolError('Invalid project plan data provided')
        except ValueError as e:
            raise ToolError(f'Invalid project plan: {str(e)}')
        except Exception as e:
            raise ToolError(f'Unexpected error storing project plan: {str(e)}')

    async def get_project_plan_data(self, project_name: str) -> ProjectPlan:
        try:
            if not project_name:
                raise ToolError('Project name cannot be empty')

            return await self.state.get_project_plan(project_name)
        except ProjectPlanNotFoundError as e:
            raise ResourceError(str(e))
        except (ResourceError, ToolError):
            raise
        except Exception as e:
            raise ToolError(f'Unexpected error retrieving project plan: {str(e)}')

    async def get_project_plan_markdown(self, project_name: str) -> MCPResponse:
        try:
            project_plan = await self.get_project_plan_data(project_name)
            markdown = project_plan.build_markdown()
            return MCPResponse(id=project_name, status=LoopStatus.COMPLETED, message=markdown)
        except Exception as e:
            raise ToolError(f'Unexpected error generating markdown: {str(e)}')

    async def list_project_plans(self, count: int = 10) -> MCPResponse:
        try:
            plan_names = await self.state.list_project_plans()
            if not plan_names:
                return MCPResponse(id='list', status=LoopStatus.INITIALIZED, message='No project plans found')

            recent_names = plan_names[-count:]
            plan_summaries = []
            for project_name in recent_names:
                try:
                    plan = await self.state.get_project_plan(project_name)
                    summary = f'Project: {project_name}, Status: {plan.project_status.value}'
                    plan_summaries.append(summary)
                except Exception:
                    pass

            plan_count = len(plan_summaries)
            message = f'Found {plan_count} project plan{"s" if plan_count != 1 else ""}: ' + '; '.join(plan_summaries)
            return MCPResponse(id='list', status=LoopStatus.COMPLETED, message=message)
        except Exception as e:
            raise ToolError(f'Unexpected error listing project plans: {str(e)}')

    async def delete_project_plan(self, project_name: str) -> MCPResponse:
        try:
            if not project_name:
                raise ToolError('Project name cannot be empty')

            await self.state.delete_project_plan(project_name)
            return MCPResponse(
                id=project_name, status=LoopStatus.COMPLETED, message=f'Deleted project plan: {project_name}'
            )
        except ProjectPlanNotFoundError as e:
            raise ResourceError(str(e))
        except (ResourceError, ToolError):
            raise
        except Exception as e:
            raise ToolError(f'Unexpected error deleting project plan: {str(e)}')


def register_project_plan_tools(mcp: FastMCP) -> None:
    project_plan_tools = ProjectPlanTools(state_manager)

    @mcp.tool()
    async def create_project_plan(project_name: str, project_plan_markdown: str, ctx: Context) -> MCPResponse:
        """Create a new project plan.

        Parses markdown content into a ProjectPlan model and stores it.

        Parameters:
        - project_name: Name for this project
        - project_plan_markdown: Complete project plan in markdown format

        Returns:
        - MCPResponse: Contains project_name, status, and confirmation message
        """
        await ctx.info(f'Creating new project plan: {project_name}')

        try:
            project_plan = ProjectPlan.parse_markdown(project_plan_markdown)
            result = await project_plan_tools.create_project_plan(project_name, project_plan)

            await ctx.info(f'Created project plan: {result.id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to create project plan: {str(e)}')
            raise ToolError(f'Failed to create project plan: {str(e)}')

    @mcp.tool()
    async def store_project_plan(project_name: str, project_plan_markdown: str, ctx: Context) -> MCPResponse:
        """Store structured project plan data from markdown.

        Parses markdown content into a ProjectPlan model and stores it.

        Parameters:
        - project_name: Name for this project
        - project_plan_markdown: Complete project plan in markdown format

        Returns:
        - MCPResponse: Contains project_name, status, and confirmation message
        """

        await ctx.info(f'Storing project plan: {project_name}')

        try:
            project_plan = ProjectPlan.parse_markdown(project_plan_markdown)
            result = await project_plan_tools.store_project_plan(project_name, project_plan)

            await ctx.info(f'Stored project plan: {result.id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to store project plan: {str(e)}')
            raise ToolError(f'Failed to store project plan: {str(e)}')

    @mcp.tool()
    async def get_project_plan_markdown(project_name: str, ctx: Context) -> MCPResponse:
        """Generate markdown for project plan.

        Retrieves stored project plan and formats as markdown.

        Parameters:
        - project_name: Name of the project

        Returns:
        - MCPResponse: Contains project_name, status, and formatted markdown content
        """
        await ctx.info(f'Generating markdown for project plan: {project_name}')
        try:
            result = await project_plan_tools.get_project_plan_markdown(project_name)
            await ctx.info(f'Generated markdown for project plan: {project_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to generate project plan markdown: {str(e)}')
            raise ResourceError(f'Project plan not found: {project_name}: {str(e)}')

    @mcp.tool()
    async def list_project_plans(count: int, ctx: Context) -> MCPResponse:
        """List available project plans.

        Returns summary of stored project plans with basic metadata.

        Parameters:
        - count: Maximum number of plans to return

        Returns:
        - MCPResponse: Contains list status and project plan summaries
        """
        await ctx.info(f'Listing up to {count} project plans')
        try:
            result = await project_plan_tools.list_project_plans(count)
            await ctx.info('Retrieved project plan list')
            return result
        except Exception as e:
            await ctx.error(f'Failed to list project plans: {str(e)}')
            raise ToolError(f'Failed to list project plans: {str(e)}')

    @mcp.tool()
    async def delete_project_plan(project_name: str, ctx: Context) -> MCPResponse:
        """Delete a stored project plan.

        Removes project plan data associated with the given project name.

        Parameters:
        - project_name: Name of the project

        Returns:
        - MCPResponse: Contains project_name, status, and deletion confirmation
        """
        await ctx.info(f'Deleting project plan: {project_name}')
        try:
            result = await project_plan_tools.delete_project_plan(project_name)
            await ctx.info(f'Deleted project plan: {project_name}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to delete project plan: {str(e)}')
            raise ToolError(f'Failed to delete project plan: {str(e)}')
