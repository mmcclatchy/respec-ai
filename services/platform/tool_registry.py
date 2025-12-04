from .models import PlatformToolMapping, ToolReference
from .platform_selector import PlatformType
from .tool_enums import (
    AbstractOperation,
    BuiltInTool,
    ExternalPlatformTool,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tool_mappings = self._create_validated_mappings()

    def _create_validated_mappings(self) -> list[PlatformToolMapping]:
        return [
            # Spec Management Tools
            PlatformToolMapping(
                operation=AbstractOperation.CREATE_SPEC_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_CREATE_ISSUE),
                markdown_tool=ToolReference(
                    tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'
                ),
            ),
            PlatformToolMapping(
                operation=AbstractOperation.GET_SPEC_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_GET_ISSUE),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_GET_ISSUE),
                markdown_tool=ToolReference(tool=BuiltInTool.READ, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
            ),
            PlatformToolMapping(
                operation=AbstractOperation.UPDATE_SPEC_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_UPDATE_ISSUE),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_UPDATE_ISSUE),
                markdown_tool=ToolReference(tool=BuiltInTool.EDIT, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
            ),
            PlatformToolMapping(
                operation=AbstractOperation.COMMENT_SPEC_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_COMMENT),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_CREATE_COMMENT),
                markdown_tool=ToolReference(tool=BuiltInTool.EDIT, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
            ),
            # Project Management Tools
            PlatformToolMapping(
                operation=AbstractOperation.CREATE_PROJECT_EXTERNAL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_PROJECT),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_CREATE_PROJECT),
                markdown_tool=ToolReference(tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/project_plan.md'),
            ),
            PlatformToolMapping(
                operation=AbstractOperation.CREATE_PROJECT_COMPLETION_EXTERNAL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_CREATE_ISSUE),
                markdown_tool=ToolReference(
                    tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/project_completion.md'
                ),
            ),
            # Plan Management Tools
            PlatformToolMapping(
                operation=AbstractOperation.GET_PROJECT_PLAN_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_GET_DOCUMENT),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_GET_FILE),
                markdown_tool=ToolReference(tool=BuiltInTool.READ, parameters='.spec-ai/projects/*/project_plan.md'),
            ),
            PlatformToolMapping(
                operation=AbstractOperation.UPDATE_PROJECT_PLAN_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_UPDATE_ISSUE),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_UPDATE_FILE),
                markdown_tool=ToolReference(tool=BuiltInTool.EDIT, parameters='.spec-ai/projects/*/project_plan.md'),
            ),
            # Spec Listing Tools
            PlatformToolMapping(
                operation=AbstractOperation.LIST_PROJECT_SPECS_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_LIST_ISSUES),
                github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_LIST_FILES),
                markdown_tool=ToolReference(tool=BuiltInTool.GLOB, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
            ),
        ]

    def get_tool_for_platform(self, abstract_tool: str, platform: PlatformType) -> str:
        # Convert string to enum if needed
        try:
            operation = AbstractOperation(abstract_tool)
        except ValueError:
            raise ValueError(f'Unknown abstract operation: {abstract_tool}')

        # Find the mapping for this operation
        mapping = self._find_mapping(operation)
        if not mapping:
            raise ValueError(f'No mapping found for operation: {abstract_tool}')

        # Get the tool for the platform
        tool_string = mapping.render_tool_for_platform(platform)
        if tool_string is None:
            raise ValueError(f'Platform {platform.value} not supported for operation {abstract_tool}')

        return tool_string

    def get_all_tools_for_platform(self, platform: PlatformType) -> dict[str, str]:
        platform_tools = {}

        for mapping in self._tool_mappings:
            tool_string = mapping.render_tool_for_platform(platform)
            if tool_string is not None:
                platform_tools[mapping.operation.value] = tool_string

        return platform_tools

    def get_supported_operations(self) -> list[str]:
        return [mapping.operation.value for mapping in self._tool_mappings]

    def add_tool_mapping(self, operation: AbstractOperation, platform: PlatformType, tool_ref: ToolReference) -> None:
        # Find existing mapping or create new one
        existing_mapping = self._find_mapping(operation)
        if existing_mapping:
            # Create new mapping with updated tool using Pydantic model_copy
            if platform == PlatformType.LINEAR:
                updated_mapping = existing_mapping.model_copy(update={'linear_tool': tool_ref})
            elif platform == PlatformType.GITHUB:
                updated_mapping = existing_mapping.model_copy(update={'github_tool': tool_ref})
            elif platform == PlatformType.MARKDOWN:
                updated_mapping = existing_mapping.model_copy(update={'markdown_tool': tool_ref})
            else:
                raise ValueError(f'Unsupported platform: {platform}')

            # Replace existing mapping
            self._tool_mappings.remove(existing_mapping)
            self._tool_mappings.append(updated_mapping)
        else:
            # Create new mapping
            if platform == PlatformType.LINEAR:
                new_mapping = PlatformToolMapping(operation=operation, linear_tool=tool_ref)
            elif platform == PlatformType.GITHUB:
                new_mapping = PlatformToolMapping(operation=operation, github_tool=tool_ref)
            elif platform == PlatformType.MARKDOWN:
                new_mapping = PlatformToolMapping(operation=operation, markdown_tool=tool_ref)
            else:
                raise ValueError(f'Unsupported platform: {platform}')

            self._tool_mappings.append(new_mapping)

    def validate_platform_support(self, platform: PlatformType, required_operations: list[str]) -> bool:
        for operation_str in required_operations:
            try:
                operation = AbstractOperation(operation_str)
            except ValueError:
                return False

            mapping = self._find_mapping(operation)
            if not mapping:
                return False

            if mapping.render_tool_for_platform(platform) is None:
                return False

        return True

    def _find_mapping(self, operation: AbstractOperation) -> PlatformToolMapping | None:
        for mapping in self._tool_mappings:
            if mapping.operation == operation:
                return mapping
        return None

    def get_all_mappings(self) -> list[PlatformToolMapping]:
        return self._tool_mappings.copy()
