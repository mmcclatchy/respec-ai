from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.mcp.tools.base import DocumentToolsInterface
from src.models.plan_completion_report import PlanCompletionReport
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError
from src.utils.loop_state import MCPResponse


class PlanCompletionReportTools(DocumentToolsInterface):
    # Standardized interface methods

    async def store(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            report = PlanCompletionReport.parse_markdown(content)
            loop_state = await self.state.get_loop(key)
            await self.state.store_completion_report(key, report)
            return MCPResponse(
                id=key,
                status=loop_state.status,
                message=f'Stored completion report for loop {key}',
            )
        except ValidationError as e:
            raise ToolError(f'Invalid completion report markdown: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

    async def get(self, key: str | None = None, loop_id: str | None = None) -> MCPResponse:
        report_id = loop_id if loop_id else key
        if not report_id:
            raise ToolError('Either key OR loop_id must be provided')

        try:
            loop_state = await self.state.get_loop(report_id)
            report = await self.state.get_completion_report(report_id)
            content = report.build_markdown()
            return MCPResponse(id=report_id, status=loop_state.status, message=content, char_length=len(content))
        except ValueError as e:
            if 'No completion report found' in str(e):
                raise ResourceError('No completion report stored for this loop')
            raise ToolError(f'Invalid input: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        try:
            reports = await self.state.list_completion_reports()

            if not reports:
                return MCPResponse(
                    id='completion_report',
                    status=LoopStatus.COMPLETED,
                    message='No completion reports found',
                )

            report_list = []
            for loop_id, report in reports:
                report_list.append(f'{loop_id}: {report.report_title}')

            ids_str = ', '.join(report_list)
            return MCPResponse(
                id='completion_report',
                status=LoopStatus.COMPLETED,
                message=f'Found {len(reports)} report{"s" if len(reports) != 1 else ""}: {ids_str}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list completion reports: {str(e)}')

    async def update(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            report = PlanCompletionReport.parse_markdown(content)
            loop_state = await self.state.get_loop(key)

            # Verify report exists before updating
            try:
                await self.state.get_completion_report(key)
            except ValueError:
                raise ResourceError('No completion report stored for this loop')

            await self.state.store_completion_report(key, report)
            return MCPResponse(
                id=key,
                status=loop_state.status,
                message=f'Updated completion report for loop {key}',
            )
        except ValidationError as e:
            raise ToolError(f'Invalid completion report markdown: {str(e)}')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            # Get the report before deleting to include title in response
            report = await self.state.get_completion_report(key)
            report_title = report.report_title

            was_deleted = await self.state.delete_completion_report(key)

            if was_deleted:
                return MCPResponse(
                    id=key,
                    status=LoopStatus.COMPLETED,
                    message=f'Deleted completion report: {report_title}',
                )

            raise ResourceError(f'No completion report found for loop {key}')
        except ValueError as e:
            if 'No completion report found' in str(e):
                raise ResourceError(f'No completion report found for loop {key}')
            raise ToolError(f'Invalid input: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        if loop_id != key:
            raise ToolError('For completion reports, loop_id must equal key')

        return MCPResponse(
            id=loop_id,
            status=LoopStatus.COMPLETED,
            message=f'Completion report already linked to loop {loop_id} (implicit)',
        )
