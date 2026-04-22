"""Tests for tool enums and validation system."""

import pytest

from src.platform.models import ToolReference
from src.platform.platform_selector import PlatformType
from src.platform.startup_validation import (
    validate_external_platform_tools,
    validate_platform_adapters,
)
from src.platform.template_helpers import (
    TemplateToolBuilder,
    create_code_command_tools,
    create_phase_command_tools,
    create_patch_command_tools,
    create_plan_command_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
    create_task_plan_critic_agent_tools,
)
from src.platform.tool_enums import (
    BuiltInTool,
    ExternalPlatformTool,
    RespecAIAgent,
    RespecAITool,
)


from src.platform.tui_adapters import ClaudeCodeAdapter


class TestToolEnums:
    def test_external_platform_tool_values(self) -> None:
        assert ExternalPlatformTool.LINEAR_CREATE_ISSUE.value == 'mcp__linear-server__create_issue'
        assert ExternalPlatformTool.GITHUB_CREATE_ISSUE.value == 'mcp__github__create_issue'

    def test_builtin_tool_values(self) -> None:
        assert BuiltInTool.READ.value == 'Read'
        assert BuiltInTool.WRITE.value == 'Write'
        assert BuiltInTool.EDIT.value == 'Edit'
        assert BuiltInTool.TASK.value == 'Task'

    def test_respec_ai_tool_values(self) -> None:
        assert RespecAITool.INITIALIZE_REFINEMENT_LOOP.value == 'mcp__respec-ai__initialize_refinement_loop'
        assert RespecAITool.DECIDE_LOOP_NEXT_ACTION.value == 'mcp__respec-ai__decide_loop_next_action'

    def test_review_section_tool_values(self) -> None:
        assert RespecAITool.STORE_REVIEW_SECTION.value == 'mcp__respec-ai__store_review_section'
        assert RespecAITool.GET_REVIEW_SECTION.value == 'mcp__respec-ai__get_review_section'
        assert RespecAITool.LIST_REVIEW_SECTIONS.value == 'mcp__respec-ai__list_review_sections'


class TestToolReference:
    def test_tool_reference_render_without_parameters(self) -> None:
        tool_ref = ToolReference(tool=BuiltInTool.READ)
        assert tool_ref.render() == 'Read'

    def test_tool_reference_render_with_parameters(self) -> None:
        tool_ref = ToolReference(tool=BuiltInTool.READ, parameters='.respec-ai/plans/*/phases/*.md')
        assert tool_ref.render() == 'Read(.respec-ai/plans/*/phases/*.md)'

    def test_tool_reference_validation_file_operations(self) -> None:
        # Should work with valid path
        ToolReference(tool=BuiltInTool.READ, parameters='.respec-ai/plans/*/phases/*.md')

        # Should fail with directory traversal
        with pytest.raises(ValueError, match='directory traversal'):
            ToolReference(tool=BuiltInTool.READ, parameters='../../../etc/passwd')

    def test_tool_reference_validation_task_agent(self) -> None:
        # Should work with valid agent name
        ToolReference(tool=BuiltInTool.TASK, parameters='phase-architect')

        # Should fail with invalid agent name
        with pytest.raises(ValueError, match='Agent name can only contain'):
            ToolReference(tool=BuiltInTool.TASK, parameters='invalid@agent!')

    def test_tool_reference_external_tools(self) -> None:
        tool_ref = ToolReference(tool=ExternalPlatformTool.LINEAR_CREATE_ISSUE)
        assert tool_ref.render() == 'mcp__linear-server__create_issue'

    def test_tool_reference_respec_ai_tools(self) -> None:
        tool_ref = ToolReference(tool=RespecAITool.INITIALIZE_REFINEMENT_LOOP)
        assert tool_ref.render() == 'mcp__respec-ai__initialize_refinement_loop'


class TestTemplateHelpers:
    def test_template_tool_builder(self) -> None:
        builder = TemplateToolBuilder()
        tools = (
            builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
            .add_respec_ai_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
            .build()
        )

        assert 'Task(respec-phase-architect)' in tools
        assert 'mcp__respec-ai__initialize_refinement_loop' in tools

    def test_template_tool_builder_yaml_rendering(self) -> None:
        builder = TemplateToolBuilder()
        yaml_output = (
            builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
            .add_respec_ai_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
            .render_yaml_tools()
        )

        assert '- Task(respec-phase-architect)' in yaml_output
        assert '- mcp__respec-ai__initialize_refinement_loop' in yaml_output

    def test_create_phase_command_tools(self) -> None:
        # Simulate what TemplateCoordinator does for LINEAR platform
        platform_tools = [
            'mcp__linear-server__create_issue',
            'mcp__linear-server__get_issue',
            'mcp__linear-server__update_issue',
        ]

        tools = create_phase_command_tools(
            platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans', tui_adapter=ClaudeCodeAdapter()
        )

        assert 'Task(respec-phase-architect)' in tools.tools_yaml
        assert 'Task(bp)' in tools.tools_yaml
        assert 'mcp__respec-ai__initialize_refinement_loop' in tools.tools_yaml
        assert 'mcp__linear-server__create_issue' in tools.tools_yaml
        assert tools.invoke_phase_critic_post_synthesis
        assert 'post_synthesis' in tools.invoke_phase_critic_post_synthesis
        assert tools.platform == PlatformType.LINEAR

    def test_create_plan_command_tools_includes_reference_write_without_ask_user(self) -> None:
        platform_tools = [
            'mcp__linear-server__create_project',
            'mcp__linear-server__get_project',
        ]

        tools = create_plan_command_tools(
            platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans', tui_adapter=ClaudeCodeAdapter()
        )

        assert 'AskUserQuestion' not in tools.tools_yaml
        assert 'Read' in tools.tools_yaml
        assert 'Write(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_roadmap_agent_tools_includes_reference_read_permission(self) -> None:
        tools = create_roadmap_agent_tools(ClaudeCodeAdapter(), plans_dir='~/.claude/plans')
        assert 'Read(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_roadmap_critic_tools_include_reference_read_permission(self) -> None:
        tools = create_roadmap_critic_agent_tools(ClaudeCodeAdapter())
        assert 'Read(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_task_plan_critic_tools_include_reference_read_permission(self) -> None:
        tools = create_task_plan_critic_agent_tools(ClaudeCodeAdapter())
        assert 'Read(.respec-ai/plans/*/references/*.md)' in tools.tools_yaml

    def test_create_code_command_tools_include_unrestricted_bash(self) -> None:
        platform_tools = [
            'mcp__linear-server__get_issue',
            'mcp__linear-server__create_comment',
        ]
        tools = create_code_command_tools(platform_tools, PlatformType.LINEAR, tui_adapter=ClaudeCodeAdapter())
        assert 'Bash' in tools.tools_yaml

    def test_create_patch_command_tools_include_unrestricted_bash(self) -> None:
        platform_tools = [
            'mcp__linear-server__get_issue',
            'mcp__linear-server__create_comment',
        ]
        tools = create_patch_command_tools(
            platform_tools, PlatformType.LINEAR, plans_dir='~/.claude/plans', tui_adapter=ClaudeCodeAdapter()
        )
        assert 'Bash' in tools.tools_yaml


class TestStartupValidation:
    def test_validate_external_platform_tools(self) -> None:
        result = validate_external_platform_tools()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'issues' in result
        assert result['linear_tools_count'] > 0
        assert result['github_tools_count'] > 0

    def test_validate_platform_adapters(self) -> None:
        result = validate_platform_adapters()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'issues' in result
        assert result['adapters_count'] == 3
        assert 'adapters' in result
        assert result['properties_per_adapter'] == 20
