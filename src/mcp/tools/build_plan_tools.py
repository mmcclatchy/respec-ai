from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.models.build_plan import BuildPlan
from src.shared import state_manager
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class BuildPlanTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state
        self._build_plans: dict[str, BuildPlan] = {}  # loop_id -> BuildPlan

    async def store_build_plan(self, loop_id: str, plan: BuildPlan) -> MCPResponse:
        try:
            loop_state = await self.state.get_loop(loop_id)
            if plan is None:
                raise ValueError('BuildPlan cannot be None')

            self._build_plans[loop_id] = plan
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Stored build plan: {plan.project_name}',
            )
        except ValidationError:
            raise ToolError('Invalid build plan data provided')
        except ValueError as e:
            raise ToolError(f'Invalid build plan: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error storing build plan: {str(e)}')

    async def get_build_plan_data(self, loop_id: str) -> BuildPlan:
        try:
            await self.state.get_loop(loop_id)

            if loop_id not in self._build_plans:
                raise ResourceError('No build plan stored for this loop')

            return self._build_plans[loop_id]
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except (ResourceError, ToolError):
            raise
        except Exception as e:
            raise ToolError(f'Unexpected error retrieving build plan: {str(e)}')

    async def get_build_plan_markdown(self, loop_id: str) -> MCPResponse:
        try:
            loop_state = await self.state.get_loop(loop_id)
            build_plan = await self.get_build_plan_data(loop_id)

            markdown = build_plan.build_markdown()
            return MCPResponse(id=loop_id, status=loop_state.status, message=markdown)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error generating markdown: {str(e)}')

    async def list_build_plans(self, count: int = 10) -> MCPResponse:
        try:
            if not self._build_plans:
                return MCPResponse(id='list', status=LoopStatus.INITIALIZED, message='No build plans found')

            plan_items = list(self._build_plans.items())[-count:]
            plan_count = len(plan_items)

            plan_summaries = []
            for loop_id, plan in plan_items:
                summary = f'ID: {loop_id}, Project: {plan.project_name}'
                plan_summaries.append(summary)

            message = f'Found {plan_count} build plan{"s" if plan_count != 1 else ""}: ' + '; '.join(plan_summaries)
            return MCPResponse(id='list', status=LoopStatus.COMPLETED, message=message)
        except Exception as e:
            raise ToolError(f'Unexpected error listing build plans: {str(e)}')

    async def delete_build_plan(self, loop_id: str) -> MCPResponse:
        try:
            await self.state.get_loop(loop_id)

            if loop_id in self._build_plans:
                plan_name = self._build_plans[loop_id].project_name
                del self._build_plans[loop_id]
            else:
                plan_name = 'Unknown'
            return MCPResponse(id=loop_id, status=LoopStatus.COMPLETED, message=f'Deleted build plan: {plan_name}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error deleting build plan: {str(e)}')


def register_build_plan_tools(mcp: FastMCP) -> None:
    build_plan_tools = BuildPlanTools(state_manager)

    @mcp.tool()
    async def store_build_plan(loop_id: str, plan_markdown: str, ctx: Context) -> MCPResponse:
        """Store implementation plan from markdown.

        Parses markdown content into a BuildPlan model and stores it.

        Parameters:
        - loop_id: Loop ID to store the build plan for
        - plan_markdown: Complete implementation plan in markdown format

        Returns:
        - MCPResponse: Contains loop_id, status, and confirmation message
        """
        await ctx.info(f'Storing build plan for loop: {loop_id}')

        try:
            build_plan = BuildPlan.parse_markdown(plan_markdown)
            result = await build_plan_tools.store_build_plan(loop_id, build_plan)

            await ctx.info(f'Stored build plan: {result.id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to store build plan: {str(e)}')
            raise ToolError(f'Failed to store build plan: {str(e)}')

    @mcp.tool()
    async def get_build_plan_markdown(loop_id: str, ctx: Context) -> MCPResponse:
        """Generate markdown for implementation plan.

        Retrieves stored build plan and formats as markdown.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains loop_id, status, and formatted markdown content
        """
        await ctx.info(f'Generating markdown for build plan: {loop_id}')
        try:
            result = await build_plan_tools.get_build_plan_markdown(loop_id)
            await ctx.info(f'Generated markdown for build plan: {loop_id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to generate build plan markdown: {str(e)}')
            raise ResourceError(f'Build plan not found for loop {loop_id}: {str(e)}')

    @mcp.tool()
    async def list_build_plans(count: int, ctx: Context) -> MCPResponse:
        """List available implementation plans.

        Returns summary of stored build plans with basic metadata.

        Parameters:
        - count: Maximum number of plans to return

        Returns:
        - MCPResponse: Contains list status and build plan summaries
        """
        await ctx.info(f'Listing up to {count} build plans')
        try:
            result = await build_plan_tools.list_build_plans(count)
            await ctx.info('Retrieved build plan list')
            return result
        except Exception as e:
            await ctx.error(f'Failed to list build plans: {str(e)}')
            raise ToolError(f'Failed to list build plans: {str(e)}')

    @mcp.tool()
    async def delete_build_plan(loop_id: str, ctx: Context) -> MCPResponse:
        """Delete a stored implementation plan.

        Removes build plan data associated with the given loop ID.

        Parameters:
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains loop_id, status, and deletion confirmation
        """
        await ctx.info(f'Deleting build plan: {loop_id}')
        try:
            result = await build_plan_tools.delete_build_plan(loop_id)
            await ctx.info(f'Deleted build plan: {loop_id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to delete build plan: {str(e)}')
            raise ToolError(f'Failed to delete build plan: {str(e)}')
