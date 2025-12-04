"""Tests for tool enums and validation system."""

import pytest

from services.platform.models import PlatformToolMapping, ToolReference
from services.platform.platform_selector import PlatformType
from services.platform.startup_validation import (
    validate_external_platform_tools,
    validate_tool_registry,
)
from services.platform.template_helpers import TemplateToolBuilder, create_spec_command_tools
from services.platform.tool_enums import (
    AbstractOperation,
    BuiltInTool,
    ExternalPlatformTool,
    SpecAITool,
)
from services.platform.tool_registry import ToolRegistry


class TestToolEnums:
    def test_external_platform_tool_values(self) -> None:
        assert ExternalPlatformTool.LINEAR_CREATE_ISSUE.value == 'mcp__linear-server__create_issue'
        assert ExternalPlatformTool.GITHUB_CREATE_ISSUE.value == 'mcp__github__create_issue'

    def test_builtin_tool_values(self) -> None:
        assert BuiltInTool.READ.value == 'Read'
        assert BuiltInTool.WRITE.value == 'Write'
        assert BuiltInTool.EDIT.value == 'Edit'
        assert BuiltInTool.TASK.value == 'Task'

    def test_spec_ai_tool_values(self) -> None:
        assert SpecAITool.INITIALIZE_REFINEMENT_LOOP.value == 'mcp__spec-ai__initialize_refinement_loop'
        assert SpecAITool.DECIDE_LOOP_NEXT_ACTION.value == 'mcp__spec-ai__decide_loop_next_action'

    def test_abstract_operation_values(self) -> None:
        assert AbstractOperation.CREATE_SPEC_TOOL.value == 'create_spec_tool'
        assert AbstractOperation.GET_SPEC_TOOL.value == 'get_spec_tool'


class TestToolReference:
    def test_tool_reference_render_without_parameters(self) -> None:
        tool_ref = ToolReference(tool=BuiltInTool.READ)
        assert tool_ref.render() == 'Read'

    def test_tool_reference_render_with_parameters(self) -> None:
        tool_ref = ToolReference(tool=BuiltInTool.READ, parameters='.spec-ai/projects/*/spec-ai-specs/*.md')
        assert tool_ref.render() == 'Read(.spec-ai/projects/*/spec-ai-specs/*.md)'

    def test_tool_reference_validation_file_operations(self) -> None:
        # Should work with valid path
        ToolReference(tool=BuiltInTool.READ, parameters='.spec-ai/projects/*/spec-ai-specs/*.md')

        # Should fail with directory traversal
        with pytest.raises(ValueError, match='directory traversal'):
            ToolReference(tool=BuiltInTool.READ, parameters='../../../etc/passwd')

    def test_tool_reference_validation_task_agent(self) -> None:
        # Should work with valid agent name
        ToolReference(tool=BuiltInTool.TASK, parameters='spec-architect')

        # Should fail with invalid agent name
        with pytest.raises(ValueError, match='Agent name can only contain'):
            ToolReference(tool=BuiltInTool.TASK, parameters='invalid@agent!')

    def test_tool_reference_external_tools(self) -> None:
        tool_ref = ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE)
        assert tool_ref.render() == 'mcp__linear-server__create_issue'

    def test_tool_reference_spec_ai_tools(self) -> None:
        tool_ref = ToolReference(tool=SpecAITool.INITIALIZE_REFINEMENT_LOOP)
        assert tool_ref.render() == 'mcp__spec-ai__initialize_refinement_loop'


class TestPlatformToolMapping:
    def test_platform_tool_mapping_creation(self) -> None:
        mapping = PlatformToolMapping(
            operation=AbstractOperation.CREATE_SPEC_TOOL,
            linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
            github_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_CREATE_ISSUE),
            markdown_tool=ToolReference(tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
        )

        assert mapping.operation == AbstractOperation.CREATE_SPEC_TOOL
        assert mapping.linear_tool is not None
        assert mapping.github_tool is not None
        assert mapping.markdown_tool is not None

    def test_platform_tool_mapping_get_tool(self) -> None:
        mapping = PlatformToolMapping(
            operation=AbstractOperation.CREATE_SPEC_TOOL,
            linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
            markdown_tool=ToolReference(tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
        )

        linear_tool = mapping.get_tool_for_platform(PlatformType.LINEAR)
        assert linear_tool is not None
        assert linear_tool.tool == ExternalPlatformTool.LINEAR_CREATE_ISSUE

        github_tool = mapping.get_tool_for_platform(PlatformType.GITHUB)
        assert github_tool is None  # Not defined for GitHub

    def test_platform_tool_mapping_render_tool(self) -> None:
        mapping = PlatformToolMapping(
            operation=AbstractOperation.CREATE_SPEC_TOOL,
            linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
            markdown_tool=ToolReference(tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
        )

        linear_rendered = mapping.render_tool_for_platform(PlatformType.LINEAR)
        assert linear_rendered == 'mcp__linear-server__create_issue'

        markdown_rendered = mapping.render_tool_for_platform(PlatformType.MARKDOWN)
        assert markdown_rendered == 'Write(.spec-ai/projects/*/spec-ai-specs/*.md)'

        github_rendered = mapping.render_tool_for_platform(PlatformType.GITHUB)
        assert github_rendered is None

    def test_platform_tool_mapping_validation_linear(self) -> None:
        # Should work with Linear tools
        mapping = PlatformToolMapping(
            operation=AbstractOperation.CREATE_SPEC_TOOL,
            linear_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
        )
        assert mapping.linear_tool is not None

        # Should fail with non-Linear external tool for Linear platform
        with pytest.raises(ValueError, match='Linear platform tool must be a Linear server tool'):
            PlatformToolMapping(
                operation=AbstractOperation.CREATE_SPEC_TOOL,
                linear_tool=ToolReference(tool=ExternalPlatformTool.GITHUB_CREATE_ISSUE),
            )

    def test_platform_tool_mapping_validation_markdown(self) -> None:
        # Should work with built-in tools
        mapping = PlatformToolMapping(
            operation=AbstractOperation.CREATE_SPEC_TOOL,
            markdown_tool=ToolReference(tool=BuiltInTool.WRITE, parameters='.spec-ai/projects/*/spec-ai-specs/*.md'),
        )
        assert mapping.markdown_tool is not None

        # Should fail with external platform tool for Markdown
        with pytest.raises(ValueError, match='Markdown platform must use built-in tools'):
            PlatformToolMapping(
                operation=AbstractOperation.CREATE_SPEC_TOOL,
                markdown_tool=ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE),
            )


class TestToolRegistry:
    def test_tool_registry_initialization(self) -> None:
        registry = ToolRegistry()
        operations = registry.get_supported_operations()
        assert len(operations) > 0
        assert 'create_spec_tool' in operations

    def test_tool_registry_get_tool_for_platform(self) -> None:
        registry = ToolRegistry()

        # Test Linear platform
        linear_tool = registry.get_tool_for_platform('create_spec_tool', PlatformType.LINEAR)
        assert linear_tool == 'mcp__linear-server__create_issue'

        # Test Markdown platform
        markdown_tool = registry.get_tool_for_platform('create_spec_tool', PlatformType.MARKDOWN)
        assert markdown_tool == 'Write(.spec-ai/projects/*/spec-ai-specs/*.md)'

    def test_tool_registry_get_all_tools_for_platform(self) -> None:
        registry = ToolRegistry()

        linear_tools = registry.get_all_tools_for_platform(PlatformType.LINEAR)
        assert len(linear_tools) > 0
        assert 'create_spec_tool' in linear_tools
        assert linear_tools['create_spec_tool'] == 'mcp__linear-server__create_issue'

    def test_tool_registry_invalid_operation(self) -> None:
        registry = ToolRegistry()

        with pytest.raises(ValueError, match='Unknown abstract operation'):
            registry.get_tool_for_platform('invalid_operation', PlatformType.LINEAR)

    def test_tool_registry_unsupported_platform(self) -> None:
        registry = ToolRegistry()

        # This should work for all our defined operations, but let's test the error handling
        # by checking the validation method
        result = registry.validate_platform_support(PlatformType.LINEAR, ['invalid_operation'])
        assert result is False


class TestTemplateHelpers:
    def test_template_tool_builder(self) -> None:
        builder = TemplateToolBuilder()
        tools = builder.add_task_agent('spec-architect').add_spec_ai_tool(SpecAITool.INITIALIZE_REFINEMENT_LOOP).build()

        assert 'Task(spec-architect)' in tools
        assert 'mcp__spec-ai__initialize_refinement_loop' in tools

    def test_template_tool_builder_yaml_rendering(self) -> None:
        builder = TemplateToolBuilder()
        yaml_output = (
            builder.add_task_agent('spec-architect')
            .add_spec_ai_tool(SpecAITool.INITIALIZE_REFINEMENT_LOOP)
            .render_yaml_tools()
        )

        assert '- Task(spec-architect)' in yaml_output
        assert '- mcp__spec-ai__initialize_refinement_loop' in yaml_output

    def test_create_spec_command_tools(self) -> None:
        # Simulate what TemplateCoordinator does for LINEAR platform
        platform_tools = [
            'mcp__linear-server__create_issue',
            'mcp__linear-server__get_issue',
            'mcp__linear-server__update_issue',
        ]

        yaml_output = create_spec_command_tools(platform_tools)

        assert 'Task(spec-ai-spec-architect)' in yaml_output
        assert 'mcp__spec-ai__initialize_refinement_loop' in yaml_output
        assert 'mcp__linear-server__create_issue' in yaml_output


class TestStartupValidation:
    def test_validate_external_platform_tools(self) -> None:
        result = validate_external_platform_tools()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'issues' in result
        assert result['linear_tools_count'] > 0
        assert result['github_tools_count'] > 0

    def test_validate_tool_registry(self) -> None:
        result = validate_tool_registry()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'issues' in result
        assert result['mappings_count'] > 0
        assert 'operations' in result
