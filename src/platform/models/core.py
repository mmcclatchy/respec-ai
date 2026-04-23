from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..tool_enums import BuiltInTool, ToolEnums
from ..tui_adapters.base import TuiAdapter


class AgentToolsModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tui_adapter: TuiAdapter = Field(..., description='TUI adapter for model resolution')


class CommandToolsModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tui_adapter: TuiAdapter = Field(..., description='TUI adapter for platform-specific rendering')


class PlatformModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        extra='forbid',  # Fail if unexpected fields provided
    )


class ToolReference(PlatformModel):
    tool: ToolEnums = Field(description='The specific tool to reference')
    parameters: str = Field(default='', description='Tool parameters like path patterns or agent names')

    def render(self) -> str:
        if self.parameters:
            return f'{self.tool}({self.parameters})'
        return self.tool

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: str, info: Any) -> str:
        if not v:
            return v

        tool = info.data.get('tool')
        if not tool:
            return v

        # Validate path patterns for file operations
        if tool in [BuiltInTool.READ, BuiltInTool.WRITE, BuiltInTool.EDIT, BuiltInTool.GLOB]:
            if not v.strip():
                raise ValueError(f'File operation tool {tool} requires non-empty path parameter')
            # Basic path pattern validation
            if '..' in v:
                raise ValueError(f'Path parameter cannot contain directory traversal: {v}')

        # Validate agent names for Task tool
        elif tool == BuiltInTool.TASK:
            if not v.strip():
                raise ValueError('Task tool requires non-empty agent name parameter')
            # Skip validation for special platform tool markers
            if v.startswith('__PLATFORM_TOOL__'):
                return v
            # Basic agent name validation
            if not v.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f'Agent name can only contain letters, numbers, hyphens, and underscores: {v}')

        return v
