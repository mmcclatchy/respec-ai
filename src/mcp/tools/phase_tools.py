from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.mcp.tools.base import DocumentToolsInterface
from src.models.phase import Phase
from src.utils.enums import LoopStatus
from src.utils.errors import LoopNotFoundError, PhaseNotFoundError
from src.utils.loop_state import MCPResponse


class PhaseTools(DocumentToolsInterface):
    async def get_phase_by_path_or_loop(self, path: str | None = None, loop_id: str | None = None) -> MCPResponse:
        try:
            if loop_id:
                loop_state = await self.state.get_loop(loop_id)
                phase = await self.state.get_phase_by_loop(loop_id)
                content = phase.build_markdown()
                char_length = len(content)
                return MCPResponse(
                    id=loop_id,
                    status=loop_state.status,
                    message=content,
                    char_length=char_length,
                )

            if path:
                parts = path.split('/')
                if len(parts) != 2:
                    raise ToolError(f'Invalid phase path format: {path} (expected: plan-name/phase-name)')
                plan_name, phase_name = parts
                phase = await self.state.get_phase(plan_name, phase_name)
                content = phase.build_markdown()
                char_length = len(content)
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=content,
                    char_length=char_length,
                )

            raise ToolError('Either path OR loop_id must be provided')
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist or is not linked to a document')
        except PhaseNotFoundError as e:
            raise ResourceError(str(e))
        except ValueError as e:
            raise ResourceError(str(e))
        except (ResourceError, ToolError):
            raise
        except Exception as e:
            raise ToolError(f'Failed to retrieve phase: {str(e)}')

    async def list_phases(self, plan_name: str) -> MCPResponse:
        if not plan_name:
            raise ToolError('parent_path (plan_name) is required for listing phases')

        try:
            phase_names = await self.state.list_phases(plan_name)
            paths = [f'{plan_name}/{name}' for name in phase_names]

            if not paths:
                return MCPResponse(
                    id='phase',
                    status=LoopStatus.COMPLETED,
                    message=f'No phase documents found under {plan_name}',
                )

            paths_str = ', '.join(paths)
            return MCPResponse(
                id='phase',
                status=LoopStatus.COMPLETED,
                message=f'Found {len(paths)} phase document{"s" if len(paths) != 1 else ""} under {plan_name}: {paths_str}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list phases: {str(e)}')

    async def delete_phase(self, plan_name: str, phase_name: str) -> MCPResponse:
        if not plan_name or not phase_name:
            raise ToolError('Plan name and phase name cannot be empty')

        try:
            was_deleted = await self.state.delete_phase(plan_name, phase_name)
            path = f'{plan_name}/{phase_name}'

            if was_deleted:
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=f'Deleted phase document at {path}',
                )
            else:
                return MCPResponse(
                    id=path,
                    status=LoopStatus.COMPLETED,
                    message=f'phase document not found at {path}',
                )
        except Exception as e:
            raise ToolError(f'Failed to delete phase: {str(e)}')

    async def link_loop_to_phase(self, loop_id: str, plan_name: str, phase_name: str) -> MCPResponse:
        if not loop_id or not plan_name or not phase_name:
            raise ToolError('Loop ID, plan name, and phase name cannot be empty')

        try:
            await self.state.link_loop_to_phase(loop_id, plan_name, phase_name)
            loop_state = await self.state.get_loop(loop_id)
            path = f'{plan_name}/{phase_name}'
            return MCPResponse(
                id=loop_id,
                status=loop_state.status,
                message=f'Linked loop {loop_id} to phase document at {path}',
            )
        except LoopNotFoundError:
            raise ResourceError('Loop does not exist')
        except Exception as e:
            raise ToolError(f'Failed to link loop to phase: {str(e)}')

    # Standardized interface methods (new)

    def _parse_key(self, key: str) -> tuple[str, str]:
        parts = key.split('/')
        if len(parts) != 2:
            raise ToolError(f'Invalid phase key: {key} (expected: plan-name/phase-name)')
        return parts[0], parts[1]

    async def store(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            phase = Phase.parse_markdown(content)
            await self.state.store_phase(plan_name, phase)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=phase_name)
        except ValidationError as e:
            raise ToolError(f'Invalid phase markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to store phase: {str(e)}')

    async def get(self, key: str | None = None, loop_id: str | None = None) -> MCPResponse:
        return await self.get_phase_by_path_or_loop(path=key, loop_id=loop_id)

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        if not parent_key:
            raise ToolError('parent_key (plan_name) is required for listing phases')

        return await self.list_phases(parent_key)

    async def update(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            phase = Phase.parse_markdown(content)
            result = await self.state.update_phase(plan_name, phase_name, phase)

            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=result)
        except ValidationError as e:
            raise ToolError(f'Invalid phase markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to update phase: {str(e)}')

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            return await self.delete_phase(plan_name, phase_name)
        except Exception as e:
            raise ToolError(f'Failed to delete phase: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        if not loop_id or not key:
            raise ToolError('Loop ID and key cannot be empty')

        try:
            plan_name, phase_name = self._parse_key(key)
            return await self.link_loop_to_phase(loop_id, plan_name, phase_name)
        except Exception as e:
            raise ToolError(f'Failed to link loop to phase: {str(e)}')
