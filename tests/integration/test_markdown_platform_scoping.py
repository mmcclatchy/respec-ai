import tempfile
from pathlib import Path
from typing import Generator

import pytest

from services.platform.models import PlatformRequirements, ProjectSetupRequest, TemplateGenerationRequest
from services.platform.platform_orchestrator import PlatformOrchestrator
from services.platform.platform_selector import PlatformType
from services.platform.tool_enums import CommandTemplate


class TestMarkdownPlatformScoping:
    @pytest.fixture
    def orchestrator(self) -> Generator[PlatformOrchestrator, None, None]:
        with tempfile.TemporaryDirectory() as temp_dir:
            yield PlatformOrchestrator(temp_dir)

    @pytest.fixture
    def temp_workspace(self) -> Generator[Path, None, None]:
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_platform_orchestrator_uses_scoped_markdown_tools(self, orchestrator: PlatformOrchestrator) -> None:
        # Setup project with Markdown platform
        project_path = '/tmp/test-scoped-integration'
        config = orchestrator.setup_project_with_defaults(project_path, PlatformType.MARKDOWN)

        assert config.platform == PlatformType.MARKDOWN

        # Get platform tools
        tools = orchestrator.get_platform_tools(project_path)

        # Verify all expected scoped tools are present
        expected_tools = {
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

        for abstract_tool, expected_concrete in expected_tools.items():
            assert abstract_tool in tools
            assert tools[abstract_tool] == expected_concrete

    def test_markdown_platform_capabilities_reflect_scoping(self, orchestrator: PlatformOrchestrator) -> None:
        capabilities = orchestrator.get_platform_capabilities(PlatformType.MARKDOWN)

        # These should be True because our scoped tools support them
        assert capabilities['supports_issues'] is True  # Via structured spec files
        assert capabilities['supports_comments'] is True  # Via spec comment functionality
        assert capabilities['supports_projects'] is True  # Via project plan files

        # These should be False (not supported by Markdown)
        assert capabilities['supports_labels'] is False
        assert capabilities['real_time_collaboration'] is False
        assert capabilities['external_integration'] is False

    def test_template_generation_works_with_scoped_tools(self, orchestrator: PlatformOrchestrator) -> None:
        # Setup project
        project_path = '/tmp/test-template-scoping'
        orchestrator.setup_project_with_defaults(project_path, PlatformType.MARKDOWN)

        # Test each command template can be generated
        available_commands = orchestrator.get_available_commands()

        for command_str in available_commands:
            try:
                command_enum = CommandTemplate(command_str)
                request = TemplateGenerationRequest(project_path=Path(project_path), command_name=command_enum)
                template = orchestrator.generate_command_template(request)
                assert isinstance(template, str)
                assert len(template) > 0
                # Templates should reference the scoped tool names
                if command_str in ['spec-ai-spec', 'spec-ai-build']:
                    assert any(tool in template for tool in ['Write(', 'Read(', 'Edit(', 'Glob('])
            except ValueError as e:
                # Some commands may not be supported by Markdown platform
                if 'does not support command' not in str(e):
                    raise

    def test_end_to_end_scoped_workflow(self, temp_workspace: Path, orchestrator: PlatformOrchestrator) -> None:
        # Setup platform orchestrator project
        project_path = str(temp_workspace / 'test-project')
        orchestrator.setup_project_with_defaults(project_path, PlatformType.MARKDOWN)

        # Get the properly scoped tools from the orchestrator
        tools = orchestrator.get_platform_tools(project_path)

        # Verify we have the correct scoped tools available
        assert 'create_spec_tool' in tools
        assert 'create_project_external' in tools
        assert tools['create_spec_tool'] == 'Write(.spec-ai/projects/*/spec-ai-specs/*.md)'
        assert tools['create_project_external'] == 'Write(.spec-ai/projects/*/project_plan.md)'

        # Test that the scoped path patterns are properly defined
        # (The actual file operations would happen through the MCP client using these tools)
        assert '.spec-ai/projects/' in tools['create_spec_tool']
        assert '.spec-ai/projects/' in tools['get_spec_tool']
        assert 'specs/*.md' in tools['create_spec_tool']
        assert 'project_plan.md' in tools['create_project_external']

    def test_security_boundaries_in_integration(self, orchestrator: PlatformOrchestrator) -> None:
        # Setup project
        project_path = '/tmp/test-security-integration'
        orchestrator.setup_project_with_defaults(project_path, PlatformType.MARKDOWN)

        # Get scoped tools
        tools = orchestrator.get_platform_tools(project_path)

        # Verify that all tools are properly scoped to .spec-ai directories
        for tool_name, tool_path in tools.items():
            assert '.spec-ai/projects/' in tool_path, f'Tool {tool_name} not properly scoped: {tool_path}'

        # Verify no tools allow arbitrary path access
        for tool_name, tool_path in tools.items():
            assert not tool_path.startswith('/'), f'Tool {tool_name} allows absolute paths: {tool_path}'
            assert '..' not in tool_path, f'Tool {tool_name} allows directory traversal: {tool_path}'

    def test_platform_validation_with_scoped_capabilities(self, orchestrator: PlatformOrchestrator) -> None:
        # Markdown platform should now support the basic requirements
        requirements = PlatformRequirements(supports_issues=True, supports_comments=True, real_time_collaboration=False)
        request = ProjectSetupRequest(
            project_path=Path('/tmp/test-validation'), platform=PlatformType.MARKDOWN, requirements=requirements
        )

        # This should work now (previously would have failed)
        config = orchestrator.setup_project(request)

        assert config.platform == PlatformType.MARKDOWN

        # But requirements that Markdown doesn't support should still fail
        unsupported_requirements = PlatformRequirements(
            supports_issues=True,
            supports_comments=True,
            supports_labels=True,  # Markdown doesn't support labels
            real_time_collaboration=True,  # Markdown doesn't support real-time
        )
        unsupported_request = ProjectSetupRequest(
            project_path=Path('/tmp/test-unsupported'),
            platform=PlatformType.MARKDOWN,
            requirements=unsupported_requirements,
        )

        with pytest.raises(ValueError, match='does not meet requirements'):
            orchestrator.setup_project(unsupported_request)

    def test_project_info_reflects_scoped_capabilities(self, orchestrator: PlatformOrchestrator) -> None:
        # Setup project
        project_path = '/tmp/test-project-info'
        orchestrator.setup_project_with_defaults(project_path, PlatformType.MARKDOWN)

        # Get project info
        info = orchestrator.get_project_info(project_path)

        # Should include all scoped capabilities
        expected_capabilities = {
            'supports_issues': True,  # Updated for scoped tools
            'supports_comments': True,  # Updated for scoped tools
            'supports_projects': True,  # Updated for scoped tools
            'supports_labels': False,
            'real_time_collaboration': False,
            'external_integration': False,
        }

        assert info['platform_capabilities'] == expected_capabilities

        # Should include all scoped tools (9 total)
        assert len(info['platform_tools']) == 9
        assert 'create_spec_tool' in info['platform_tools']
        assert info['platform_tools']['create_spec_tool'] == 'Write(.spec-ai/projects/*/spec-ai-specs/*.md)'

        # Project should be valid
        assert info['config_valid'] is True
