from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError
from src.models.plan_completion_report import PlanCompletionReport
from src.shared import state_manager
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError
from src.utils.loop_state import MCPResponse
from src.utils.state_manager import StateManager


class PlanCompletionReportTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state
        self._completion_reports: dict[str, PlanCompletionReport] = {}

    def create_completion_report(
        self, project_path: str, completion_report: PlanCompletionReport, loop_id: str
    ) -> MCPResponse:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            if completion_report is None:
                raise ValueError('PlanCompletionReport cannot be None')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Verify loop exists
            loop_state = self.state.get_loop(loop_id)

            # Check if report already exists for this loop
            if loop_id in self._completion_reports:
                raise ValueError(f'Completion report already exists for loop {loop_id}')

            self._completion_reports[loop_id] = completion_report
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Created completion report for {completion_report.report_title}',
            )
        except ValidationError:
            raise ToolError('Invalid completion report data provided')
        except ValueError as e:
            raise ToolError(f'Invalid input: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error creating completion report: {str(e)}')

    def store_completion_report(
        self, project_path: str, completion_report: PlanCompletionReport, loop_id: str
    ) -> MCPResponse:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            if completion_report is None:
                raise ValueError('PlanCompletionReport cannot be None')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            loop_state = self.state.get_loop(loop_id)
            self._completion_reports[loop_id] = completion_report
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Stored completion report for {completion_report.report_title}',
            )
        except ValidationError:
            raise ToolError('Invalid completion report data provided')
        except ValueError as e:
            raise ToolError(f'Invalid input: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error storing completion report: {str(e)}')

    def get_completion_report_data(self, project_path: str, loop_id: str) -> PlanCompletionReport:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Check if loop exists
            self.state.get_loop(loop_id)

            if loop_id not in self._completion_reports:
                raise ResourceError('No completion report stored for this loop')

            return self._completion_reports[loop_id]
        except ValueError as e:
            raise ToolError(f'Invalid input: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except (ResourceError, ToolError):
            raise  # Re-raise FastMCP exceptions as-is
        except Exception as e:
            raise ToolError(f'Unexpected error retrieving completion report: {str(e)}')

    def get_completion_report_markdown(self, project_path: str, loop_id: str) -> MCPResponse:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            loop_state = self.state.get_loop(loop_id)
            completion_report = self.get_completion_report_data(project_path, loop_id)

            markdown = completion_report.build_markdown()
            return MCPResponse(id=loop_id, status=loop_state.status, message=markdown)
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error generating completion report markdown: {str(e)}')

    def update_completion_report(
        self, project_path: str, completion_report: PlanCompletionReport, loop_id: str
    ) -> MCPResponse:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            if completion_report is None:
                raise ValueError('PlanCompletionReport cannot be None')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Check if loop and report exist
            loop_state = self.state.get_loop(loop_id)
            if loop_id not in self._completion_reports:
                raise ResourceError('No completion report stored for this loop')

            self._completion_reports[loop_id] = completion_report
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Updated completion report for {completion_report.report_title}',
            )
        except ValidationError:
            raise ToolError('Invalid completion report data provided')
        except ValueError as e:
            raise ToolError(f'Invalid input: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except (ResourceError, ToolError):
            raise  # Re-raise FastMCP exceptions as-is
        except Exception as e:
            raise ToolError(f'Unexpected error updating completion report: {str(e)}')

    def list_completion_reports(self, project_path: str, count: int = 10) -> MCPResponse:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            if count <= 0:
                raise ValueError('Count must be a positive integer')

            if not self._completion_reports:
                return MCPResponse(id='list', status=LoopStatus.INITIALIZED, message='No completion reports found')

            # Get recent reports (limited by count)
            report_items = list(self._completion_reports.items())[-count:]
            report_count = len(report_items)

            report_summaries = []
            for loop_id, report in report_items:
                summary = f'ID: {loop_id}, Report: {report.report_title}, Score: {report.final_plan_score}%'
                report_summaries.append(summary)

            message = f'Found {report_count} completion report{"s" if report_count != 1 else ""}: ' + '; '.join(
                report_summaries
            )
            return MCPResponse(id='list', status=LoopStatus.COMPLETED, message=message)
        except ValueError as e:
            raise ToolError(f'Invalid input: {str(e)}')
        except Exception as e:
            raise ToolError(f'Unexpected error listing completion reports: {str(e)}')

    def delete_completion_report(self, project_path: str, loop_id: str) -> MCPResponse:
        try:
            if not project_path or not project_path.strip():
                raise ValueError('Project path cannot be empty')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Check if loop exists
            self.state.get_loop(loop_id)

            # Remove completion report
            if loop_id in self._completion_reports:
                report_title = self._completion_reports[loop_id].report_title
                del self._completion_reports[loop_id]
            else:
                report_title = 'Unknown'
            return MCPResponse(
                id=loop_id, status=LoopStatus.COMPLETED, message=f'Deleted completion report: {report_title}'
            )
        except ValueError as e:
            raise ToolError(f'Invalid input: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Unexpected error deleting completion report: {str(e)}')


def register_plan_completion_report_tools(mcp: FastMCP) -> None:
    completion_report_tools = PlanCompletionReportTools(state_manager)

    @mcp.tool()
    async def create_plan_completion_report(
        project_path: str, completion_report_markdown: str, loop_id: str, ctx: Context
    ) -> MCPResponse:
        """Create a new plan completion report for an existing loop.

        Parses markdown content into a PlanCompletionReport model and creates it for
        the specified loop.

        Parameters:
        - project_path: Absolute path to project directory
        - completion_report_markdown: Complete completion report in markdown format
        - loop_id: Existing loop ID to associate with the completion report

        Returns:
        - MCPResponse: Contains loop_id, status, and confirmation message
        """
        await ctx.info(f'Creating new completion report for loop {loop_id} at {project_path}')

        try:
            # Validate inputs
            if not completion_report_markdown or not completion_report_markdown.strip():
                raise ValueError('Completion report markdown cannot be empty')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Parse markdown into PlanCompletionReport model
            completion_report = PlanCompletionReport.parse_markdown(completion_report_markdown)
            result = completion_report_tools.create_completion_report(project_path, completion_report, loop_id)

            await ctx.info(f'Created completion report for loop ID: {result.id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to create completion report: {str(e)}')
            raise ToolError(f'Failed to create completion report: {str(e)}')

    @mcp.tool()
    async def store_plan_completion_report(
        project_path: str, loop_id: str, completion_report_markdown: str, ctx: Context
    ) -> MCPResponse:
        """Store structured completion report data from markdown.

        Parses markdown content into a PlanCompletionReport model and stores it with
        the specified loop.

        Parameters:
        - project_path: Absolute path to project directory
        - loop_id: Loop ID to store the completion report for
        - completion_report_markdown: Complete completion report in markdown format

        Returns:
        - MCPResponse: Contains loop_id, status, and confirmation message
        """

        await ctx.info(f'Parsing and storing completion report markdown with loop_id: {loop_id} at {project_path}')

        try:
            # Validate inputs
            if not completion_report_markdown or not completion_report_markdown.strip():
                raise ValueError('Completion report markdown cannot be empty')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Parse markdown into PlanCompletionReport model
            completion_report = PlanCompletionReport.parse_markdown(completion_report_markdown)
            result = completion_report_tools.store_completion_report(project_path, completion_report, loop_id)

            await ctx.info(f'Stored completion report with ID: {result.id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to store completion report: {str(e)}')
            raise ToolError(f'Failed to store completion report: {str(e)}')

    @mcp.tool()
    async def get_plan_completion_report_markdown(project_path: str, loop_id: str, ctx: Context) -> MCPResponse:
        """Generate markdown for plan completion report.

        Retrieves stored completion report and formats as markdown.

        Parameters:
        - project_path: Absolute path to project directory
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains loop_id, status, and formatted markdown content
        """
        await ctx.info(f'Generating markdown for completion report {loop_id} at {project_path}')
        try:
            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            result = completion_report_tools.get_completion_report_markdown(project_path, loop_id)
            await ctx.info(f'Generated markdown for completion report {loop_id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to generate completion report markdown: {str(e)}')
            raise ResourceError(f'Completion report not found for loop {loop_id}: {str(e)}')

    @mcp.tool()
    async def update_plan_completion_report(
        project_path: str, loop_id: str, completion_report_markdown: str, ctx: Context
    ) -> MCPResponse:
        """Update an existing plan completion report.

        Parses markdown content and updates the existing completion report for the specified loop.

        Parameters:
        - project_path: Absolute path to project directory
        - loop_id: Loop ID of the completion report to update
        - completion_report_markdown: Updated completion report in markdown format

        Returns:
        - MCPResponse: Contains loop_id, status, and confirmation message
        """
        await ctx.info(f'Updating completion report for loop {loop_id} at {project_path}')

        try:
            # Validate inputs
            if not completion_report_markdown or not completion_report_markdown.strip():
                raise ValueError('Completion report markdown cannot be empty')

            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            # Parse markdown into PlanCompletionReport model
            completion_report = PlanCompletionReport.parse_markdown(completion_report_markdown)
            result = completion_report_tools.update_completion_report(project_path, completion_report, loop_id)

            await ctx.info(f'Updated completion report for loop ID: {result.id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to update completion report: {str(e)}')
            raise ToolError(f'Failed to update completion report: {str(e)}')

    @mcp.tool()
    async def list_plan_completion_reports(project_path: str, count: int, ctx: Context) -> MCPResponse:
        """List available plan completion reports.

        Returns summary of stored completion reports with basic metadata.

        Parameters:
        - project_path: Absolute path to project directory
        - count: Maximum number of reports to return

        Returns:
        - MCPResponse: Contains list status and completion report summaries
        """
        await ctx.info(f'Listing up to {count} completion reports at {project_path}')
        try:
            if count <= 0:
                raise ValueError('Count must be a positive integer')

            result = completion_report_tools.list_completion_reports(project_path, count)
            await ctx.info('Retrieved completion report list')
            return result
        except Exception as e:
            await ctx.error(f'Failed to list completion reports: {str(e)}')
            raise ToolError(f'Failed to list completion reports: {str(e)}')

    @mcp.tool()
    async def delete_plan_completion_report(project_path: str, loop_id: str, ctx: Context) -> MCPResponse:
        """Delete a stored plan completion report.

        Removes completion report data associated with the given loop ID.

        Parameters:
        - project_path: Absolute path to project directory
        - loop_id: Unique identifier of the loop

        Returns:
        - MCPResponse: Contains loop_id, status, and deletion confirmation
        """
        await ctx.info(f'Deleting completion report {loop_id} at {project_path}')
        try:
            if not loop_id or not loop_id.strip():
                raise ValueError('Loop ID cannot be empty')

            result = completion_report_tools.delete_completion_report(project_path, loop_id)
            await ctx.info(f'Deleted completion report {loop_id}')
            return result
        except Exception as e:
            await ctx.error(f'Failed to delete completion report: {str(e)}')
            raise ToolError(f'Failed to delete completion report: {str(e)}')
