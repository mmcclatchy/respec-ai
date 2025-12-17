from fastmcp.exceptions import ResourceError, ToolError
from pydantic import ValidationError

from src.mcp.tools.base import DocumentToolsInterface
from src.models.plan import Plan
from src.utils.enums import LoopStatus
from src.utils.errors import PlanNotFoundError
from src.utils.loop_state import MCPResponse


class PlanTools(DocumentToolsInterface):
    async def store(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            plan = Plan.parse_markdown(content)
            await self.state.store_plan(key, plan)
            return MCPResponse(
                id=key,
                status=LoopStatus.IN_PROGRESS,
                message=key,
            )
        except ValidationError as e:
            raise ToolError(f'Invalid plan markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to store plan: {str(e)}')

    async def get(self, key: str | None = None, loop_id: str | None = None) -> MCPResponse:
        if not key:
            raise ToolError('Key is required for plans')

        if loop_id:
            raise ToolError('Plans do not support loop-based retrieval')

        try:
            plan = await self.state.get_plan(key)
            markdown = plan.build_markdown()
            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=markdown, char_length=len(markdown))
        except PlanNotFoundError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to get plan: {str(e)}')

    async def list(self, parent_key: str | None = None) -> MCPResponse:
        try:
            plan_names = await self.state.list_plans()
            if not plan_names:
                return MCPResponse(id='plan', status=LoopStatus.COMPLETED, message='No project plans found')

            plan_summaries = []
            for plan_name in plan_names:
                try:
                    plan = await self.state.get_plan(plan_name)
                    summary = f'{plan_name} (Status: {plan.plan_status.value})'
                    plan_summaries.append(summary)
                except Exception:
                    pass

            plans_str = ', '.join(plan_summaries)
            count = len(plan_summaries)
            return MCPResponse(
                id='plan',
                status=LoopStatus.COMPLETED,
                message=f'Found {count} plan{"s" if count != 1 else ""}: {plans_str}',
            )
        except Exception as e:
            raise ToolError(f'Failed to list plans: {str(e)}')

    async def update(self, key: str, content: str) -> MCPResponse:
        if not key or not content:
            raise ToolError('Key and content cannot be empty')

        try:
            plan = Plan.parse_markdown(content)
            await self.state.store_plan(key, plan)
            return MCPResponse(id=key, status=LoopStatus.IN_PROGRESS, message=key)
        except ValidationError as e:
            raise ToolError(f'Invalid plan markdown: {str(e)}')
        except Exception as e:
            raise ToolError(f'Failed to update plan: {str(e)}')

    async def delete(self, key: str) -> MCPResponse:
        if not key:
            raise ToolError('Key cannot be empty')

        try:
            await self.state.delete_plan(key)
            return MCPResponse(id=key, status=LoopStatus.COMPLETED, message=f'Deleted project plan: {key}')
        except PlanNotFoundError as e:
            raise ResourceError(str(e))
        except Exception as e:
            raise ToolError(f'Failed to delete plan: {str(e)}')

    async def link_loop(self, loop_id: str, key: str) -> MCPResponse:
        raise ToolError('Plans do not support loop linking')
