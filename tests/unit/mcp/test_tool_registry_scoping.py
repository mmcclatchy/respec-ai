import pytest

from services.platform.platform_selector import PlatformType
from services.platform.tool_registry import ToolRegistry


class TestToolRegistryScoping:
    @pytest.fixture
    def tool_registry(self) -> ToolRegistry:
        return ToolRegistry()

    def test_markdown_tools_are_properly_scoped(self, tool_registry: ToolRegistry) -> None:
        # Get all tools for Markdown platform
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        # Verify all tools are scoped to .spec-ai directories
        for abstract_tool, concrete_tool in markdown_tools.items():
            assert '.spec-ai/projects/' in concrete_tool, f'Tool {abstract_tool} not scoped: {concrete_tool}'

    def test_markdown_tools_use_standard_mcp_tools(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        expected_tool_patterns = {
            'create_spec_tool': 'Write(.spec-ai/projects/*/spec-ai-specs/*.md)',
            'get_spec_tool': 'Read(.spec-ai/projects/*/spec-ai-specs/*.md)',
            'update_spec_tool': 'Edit(.spec-ai/projects/*/spec-ai-specs/*.md)',
            'comment_spec_tool': 'Edit(.spec-ai/projects/*/spec-ai-specs/*.md)',
            'create_project_external': 'Write(.spec-ai/projects/*/project_plan.md)',
            'create_project_completion_external': 'Write(.spec-ai/projects/*/project_completion.md)',
            'get_project_plan_tool': 'Read(.spec-ai/projects/*/project_plan.md)',
            'update_project_plan_tool': 'Edit(.spec-ai/projects/*/project_plan.md)',
            'list_project_specs_tool': 'Glob(.spec-ai/projects/*/spec-ai-specs/*.md)',
        }

        for abstract_tool, expected_pattern in expected_tool_patterns.items():
            assert abstract_tool in markdown_tools
            assert markdown_tools[abstract_tool] == expected_pattern

    def test_markdown_tools_prevent_arbitrary_access(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        for abstract_tool, concrete_tool in markdown_tools.items():
            # Should not allow absolute paths
            assert not concrete_tool.startswith('/'), f'Tool {abstract_tool} allows absolute paths: {concrete_tool}'

            # Should not allow directory traversal
            assert '..' not in concrete_tool, f'Tool {abstract_tool} allows directory traversal: {concrete_tool}'

            # Should be scoped to .spec-ai directory
            assert '.spec-ai' in concrete_tool, f'Tool {abstract_tool} not scoped to .spec-ai: {concrete_tool}'

    def test_markdown_tools_use_wildcard_patterns(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        # Tools that should use wildcards for project names
        wildcard_tools = [
            'create_spec_tool',
            'get_spec_tool',
            'update_spec_tool',
            'comment_spec_tool',
            'create_project_external',
            'create_project_completion_external',
            'get_project_plan_tool',
            'update_project_plan_tool',
            'list_project_specs_tool',
        ]

        for tool_name in wildcard_tools:
            tool_path = markdown_tools[tool_name]
            assert '/projects/*/' in tool_path, f'Tool {tool_name} should use wildcard pattern: {tool_path}'

    def test_spec_tools_are_scoped_to_specs_directory(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        spec_tools = ['create_spec_tool', 'get_spec_tool', 'update_spec_tool', 'comment_spec_tool']

        for tool_name in spec_tools:
            tool_path = markdown_tools[tool_name]
            assert '/spec-ai-specs/' in tool_path, f'Spec tool {tool_name} not scoped to specs directory: {tool_path}'
            assert '.md' in tool_path, f'Spec tool {tool_name} should target .md files: {tool_path}'

    def test_project_tools_are_scoped_to_project_files(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        project_file_tools = {
            'create_project_external': 'project_plan.md',
            'create_project_completion_external': 'project_completion.md',
            'get_project_plan_tool': 'project_plan.md',
            'update_project_plan_tool': 'project_plan.md',
        }

        for tool_name, expected_file in project_file_tools.items():
            tool_path = markdown_tools[tool_name]
            assert expected_file in tool_path, f'Project tool {tool_name} should target {expected_file}: {tool_path}'
            assert '/spec-ai-specs/' not in tool_path, (
                f'Project tool {tool_name} should not target specs directory: {tool_path}'
            )

    def test_list_tool_uses_glob_pattern(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        list_tool = markdown_tools['list_project_specs_tool']
        assert list_tool.startswith('Glob('), f'List tool should use Glob: {list_tool}'
        assert 'specs/*.md' in list_tool, f'List tool should target spec files: {list_tool}'

    def test_different_platforms_have_different_tools(self, tool_registry: ToolRegistry) -> None:
        linear_tools = tool_registry.get_all_tools_for_platform(PlatformType.LINEAR)
        github_tools = tool_registry.get_all_tools_for_platform(PlatformType.GITHUB)
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        # Same abstract operation should map to different concrete tools
        operation = 'create_spec_tool'

        assert linear_tools[operation] != markdown_tools[operation]
        assert github_tools[operation] != markdown_tools[operation]
        assert linear_tools[operation] != github_tools[operation]

        # Markdown should use scoped Write tool
        assert markdown_tools[operation].startswith('Write(')

        # Other platforms should use their specific tools
        assert 'mcp__linear-server__' in linear_tools[operation]
        assert 'mcp__github__' in github_tools[operation]


class TestSecurityScoping:
    @pytest.fixture
    def tool_registry(self) -> ToolRegistry:
        return ToolRegistry()

    def test_no_absolute_paths_allowed(self, tool_registry: ToolRegistry) -> None:
        all_platforms = [PlatformType.LINEAR, PlatformType.GITHUB, PlatformType.MARKDOWN]

        for platform in all_platforms:
            tools = tool_registry.get_all_tools_for_platform(platform)
            for tool_name, tool_path in tools.items():
                if platform == PlatformType.MARKDOWN:  # Only check Markdown tools for path scoping
                    assert not tool_path.startswith('/'), f'Tool {tool_name} on {platform.value} allows absolute paths'

    def test_no_directory_traversal_allowed(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        for tool_name, tool_path in markdown_tools.items():
            assert '..' not in tool_path, f'Tool {tool_name} allows directory traversal: {tool_path}'
            assert not tool_path.startswith('./'), f'Tool {tool_name} allows relative traversal: {tool_path}'

    def test_all_paths_within_spec_ai_scope(self, tool_registry: ToolRegistry) -> None:
        markdown_tools = tool_registry.get_all_tools_for_platform(PlatformType.MARKDOWN)

        for tool_name, tool_path in markdown_tools.items():
            assert '.spec-ai' in tool_path, f'Tool {tool_name} not scoped to .spec-ai: {tool_path}'
            assert tool_path.count('.spec-ai') == 1, f'Tool {tool_name} has multiple .spec-ai references: {tool_path}'
