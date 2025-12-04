"""Tests for Platform Orchestrator functionality."""

import tempfile
from pathlib import Path

import pytest

from services.platform.models import (
    PlatformRequirements,
    ProjectPlatformChangeRequest,
    ProjectSetupRequest,
    ProjectSetupWithRecommendationRequest,
    TemplateGenerationRequest,
)
from services.platform.platform_orchestrator import PlatformOrchestrator
from services.platform.platform_selector import PlatformType
from services.platform.tool_enums import CommandTemplate


class TestPlatformOrchestrator:
    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = PlatformOrchestrator(config_dir=self.temp_dir)
        self.test_project_path = '/tmp/test_project'

    def test_setup_project_with_auto_selection(self) -> None:
        requirements = PlatformRequirements(supports_issues=True, real_time_collaboration=True, supports_comments=True)
        request = ProjectSetupWithRecommendationRequest(
            project_path=Path(self.test_project_path), requirements=requirements
        )

        config = self.orchestrator.setup_project_with_recommendation(request)

        assert str(config.project_path) == self.test_project_path
        assert config.platform == PlatformType.LINEAR  # Should select Linear for real-time collaboration

    def test_setup_project_with_explicit_platform(self) -> None:
        config = self.orchestrator.setup_project_with_defaults(self.test_project_path, PlatformType.GITHUB)

        assert str(config.project_path) == self.test_project_path
        assert config.platform == PlatformType.GITHUB

    def test_setup_project_validation_error(self) -> None:
        requirements = PlatformRequirements(
            supports_issues=True,
            supports_comments=True,
            real_time_collaboration=True,  # Markdown doesn't support this
        )
        request = ProjectSetupRequest(
            project_path=Path(self.test_project_path), platform=PlatformType.MARKDOWN, requirements=requirements
        )

        with pytest.raises(ValueError, match='does not meet requirements'):
            self.orchestrator.setup_project(request)

    def test_generate_command_template(self) -> None:
        # Set up project first
        self.orchestrator.setup_project_with_defaults(self.test_project_path, PlatformType.LINEAR)

        request = TemplateGenerationRequest(
            project_path=Path(self.test_project_path), command_name=CommandTemplate.SPEC
        )
        template = self.orchestrator.generate_command_template(request)

        # Verify template contains Linear-specific tools
        assert 'mcp__linear-server__create_issue' in template
        assert 'mcp__linear-server__get_issue' in template
        assert 'mcp__linear-server__update_issue' in template

    def test_generate_command_template_no_config(self) -> None:
        request = TemplateGenerationRequest(
            project_path=Path(self.test_project_path), command_name=CommandTemplate.SPEC
        )
        with pytest.raises(ValueError, match='No configuration found for project'):
            self.orchestrator.generate_command_template(request)

    def test_get_platform_tools(self) -> None:
        # Set up project
        self.orchestrator.setup_project_with_defaults(self.test_project_path, PlatformType.GITHUB)

        tools = self.orchestrator.get_platform_tools(self.test_project_path)

        assert 'create_spec_tool' in tools
        assert tools['create_spec_tool'] == 'mcp__github__create_issue'
        assert tools['get_spec_tool'] == 'mcp__github__get_issue'

    def test_change_project_platform(self) -> None:
        # Set up project with Linear
        self.orchestrator.setup_project_with_defaults(self.test_project_path, PlatformType.LINEAR)

        # Change to GitHub
        request = ProjectPlatformChangeRequest(
            project_path=Path(self.test_project_path), new_platform=PlatformType.GITHUB
        )
        self.orchestrator.change_project_platform(request)

        # Verify platform changed
        platform = self.orchestrator.get_project_platform(self.test_project_path)
        assert platform == PlatformType.GITHUB

    def test_get_project_info(self) -> None:
        # Set up project
        requirements = PlatformRequirements(supports_issues=True, supports_comments=True)
        request = ProjectSetupRequest(
            project_path=Path(self.test_project_path), platform=PlatformType.MARKDOWN, requirements=requirements
        )
        self.orchestrator.setup_project(request)

        info = self.orchestrator.get_project_info(self.test_project_path)

        assert info is not None
        assert str(info['project_path']) == self.test_project_path
        assert info['platform'] == 'markdown'
        assert 'platform_capabilities' in info
        assert 'platform_tools' in info
        assert 'available_commands' in info
        assert info['config_valid'] is True

    def test_validate_project_setup(self) -> None:
        # Test with no config
        assert not self.orchestrator.validate_project_setup(self.test_project_path)

        # Set up project
        self.orchestrator.setup_project_with_defaults(self.test_project_path, PlatformType.LINEAR)

        # Test with valid config
        assert self.orchestrator.validate_project_setup(self.test_project_path)

    def test_get_available_platforms(self) -> None:
        platforms = self.orchestrator.get_available_platforms()

        assert PlatformType.LINEAR in platforms
        assert PlatformType.GITHUB in platforms
        assert PlatformType.MARKDOWN in platforms

    def test_get_available_commands(self) -> None:
        commands = self.orchestrator.get_available_commands()

        assert 'spec-ai-plan' in commands
        assert 'spec-ai-spec' in commands
        assert 'spec-ai-build' in commands
        assert 'spec-ai-roadmap' in commands
        assert 'spec-ai-plan-conversation' in commands

    def test_recommend_platform_for_requirements(self) -> None:
        # Requirements favoring Linear
        requirements = {'supports_issues': True, 'real_time_collaboration': True}

        platform = self.orchestrator.recommend_platform_for_requirements(requirements)
        assert platform == PlatformType.LINEAR

        # Requirements with minimal needs (Markdown-friendly but other platforms score higher due to more features)
        requirements = {'supports_issues': True, 'real_time_collaboration': False}

        platform = self.orchestrator.recommend_platform_for_requirements(requirements)
        # LINEAR scores highest because it has the most capabilities, even when not all are required
        assert platform == PlatformType.LINEAR
