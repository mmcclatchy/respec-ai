from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.mcp.tools.base import DocumentToolsInterface
from src.models.task import Task
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError
from src.utils.loop_state import MCPResponse


class TaskTools(DocumentToolsInterface):
    def _parse_task_key(self, key: str) -> tuple[str, str]:
        parts = key.split('/')
        if len(parts) < 3:
            raise ToolError(f'Invalid task key: {key} (expected: plan-name/phase-name/task-name)')
        phase_path = '/'.join(parts[:-1])
        task_name = parts[-1]
        return phase_path, task_name

    async def store(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            phase_path, task_name = self._parse_task_key(key)
            task = Task.parse_markdown(content)

            await self.state.store_task(phase_path, task)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=task_name)
        except ValidationError as e:
            raise ToolError(f'Invalid task markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to store task: {str(e)}')

    async def get(self, key: str | None = None, loop_id: str | None = None) -> MCPResponse:
        if not key and not loop_id:
            raise ToolError('Either key OR loop_id must be provided')

        try:
            if loop_id:
                return await self._get_by_loop(loop_id)
            if key:
                return await self._get_by_key(key)
            raise ToolError('Either key OR loop_id must be provided')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist or is not linked to a document')
        except ValueError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to get task: {str(e)}')

    async def _get_by_loop(self, loop_id: str) -> MCPResponse:
        loop_state = await self.state.get_loop(loop_id)

        try:
            task = await self.state.get_task_by_loop(loop_id)
            content = task.build_markdown()
        except (ValueError, LoopNotFoundError):
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message='No task linked to this loop yet',
            )

        return MCPResponse(id=loop_id, status=loop_state.status, message=content, char_length=len(content))

    async def _get_by_key(self, key: str) -> MCPResponse:
        phase_path, task_name = self._parse_task_key(key)
        task = await self.state.get_task(phase_path, task_name)
        content = task.build_markdown()

        return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=content, char_length=len(content))

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        if not parent_key:
            raise ToolError('parent_key (phase_path) is required for listing tasks')

        try:
            task_names = await self.state.list_tasks(parent_key)
            paths = [f'{parent_key}/{name}' for name in task_names]

            if not paths:
                return MCPResponse(
                    id='task',
                    status=LoopStatus.COMPLETED,
                    message=f'No task documents found under {parent_key}',
                )

            paths_str = ', '.join(paths)
            return MCPResponse(
                id='task',
                status=LoopStatus.COMPLETED,
                message=f'Found {len(paths)} task document{"s" if len(paths) != 1 else ""} under {parent_key}: {paths_str}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list tasks: {str(e)}')

    async def update(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            phase_path, task_name = self._parse_task_key(key)
            task = Task.parse_markdown(content)
            await self.state.store_task(phase_path, task)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=task_name)
        except ValidationError as e:
            raise ToolError(f'Invalid task markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to update task: {str(e)}')

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            phase_path, task_name = self._parse_task_key(key)
            was_deleted = await self.state.delete_task(phase_path, task_name)

            if was_deleted:
                return MCPResponse(
                    id=key,
                    status=LoopStatus.COMPLETED,
                    message=f'Deleted task document at {key}',
                )
            else:
                return MCPResponse(
                    id=key,
                    status=LoopStatus.COMPLETED,
                    message=f'task document not found at {key}',
                )
        except Exception as e:
            raise ToolError(f'Failed to delete task: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        if not loop_id or not key:
            raise ToolError('Loop ID and key cannot be empty')

        try:
            phase_path, task_name = self._parse_task_key(key)
            await self.state.link_loop_to_task(loop_id, phase_path, task_name)
            loop_state = await self.state.get_loop(loop_id)

            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Linked loop {loop_id} to task document at {key}',
            )
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Failed to link loop to task: {str(e)}')
