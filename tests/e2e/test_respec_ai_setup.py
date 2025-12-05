import json
import subprocess
from pathlib import Path


class TestRespecAISetupEndToEnd:
    def test_full_linear_project_setup_workflow(self, tmp_path: Path) -> None:
        project_path = tmp_path / 'test_project'
        project_path.mkdir()

        result = subprocess.run(
            [
                'uv',
                'run',
                'respec-ai',
                'init',
                '--platform',
                'linear',
                '--project-name',
                'test-project',
                '--skip-mcp-registration',
            ],
            cwd=str(project_path),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (project_path / '.claude' / 'commands' / 'respec-plan.md').exists()
        assert (project_path / '.claude' / 'commands' / 'respec-spec.md').exists()
        assert (project_path / '.claude' / 'commands' / 'respec-build.md').exists()
        assert (project_path / '.claude' / 'commands' / 'respec-roadmap.md').exists()
        assert (project_path / '.claude' / 'agents' / 'respec-create-spec.md').exists()
        assert (project_path / '.respec-ai' / 'config.json').exists()

        config_data = json.loads((project_path / '.respec-ai' / 'config.json').read_text())
        assert config_data['platform'] == 'linear'
        assert config_data['project_name'] == 'test-project'

    def test_full_github_project_setup_workflow(self, tmp_path: Path) -> None:
        project_path = tmp_path / 'test_project'
        project_path.mkdir()

        result = subprocess.run(
            [
                'uv',
                'run',
                'respec-ai',
                'init',
                '--platform',
                'github',
                '--project-name',
                'test-project',
                '--skip-mcp-registration',
            ],
            cwd=str(project_path),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (project_path / '.claude' / 'commands' / 'respec-plan.md').exists()
        assert (project_path / '.respec-ai' / 'config.json').exists()

        config_data = json.loads((project_path / '.respec-ai' / 'config.json').read_text())
        assert config_data['platform'] == 'github'
        assert config_data['project_name'] == 'test-project'

    def test_full_markdown_project_setup_workflow(self, tmp_path: Path) -> None:
        project_path = tmp_path / 'test_project'
        project_path.mkdir()

        result = subprocess.run(
            [
                'uv',
                'run',
                'respec-ai',
                'init',
                '--platform',
                'markdown',
                '--project-name',
                'test-project',
                '--skip-mcp-registration',
            ],
            cwd=str(project_path),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (project_path / '.claude' / 'commands' / 'respec-plan.md').exists()
        assert (project_path / '.respec-ai' / 'config.json').exists()

        config_data = json.loads((project_path / '.respec-ai' / 'config.json').read_text())
        assert config_data['platform'] == 'markdown'
        assert config_data['project_name'] == 'test-project'

    def test_command_templates_contain_platform_specific_tools(self, tmp_path: Path) -> None:
        for platform in ['linear', 'github', 'markdown']:
            platform_project = tmp_path / f'{platform}_project'
            platform_project.mkdir()

            result = subprocess.run(
                [
                    'uv',
                    'run',
                    'respec-ai',
                    'init',
                    '--platform',
                    platform,
                    '--project-name',
                    'test-project',
                    '--skip-mcp-registration',
                ],
                cwd=str(platform_project),
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            spec_command_path = platform_project / '.claude' / 'commands' / 'respec-spec.md'
            spec_command_content = spec_command_path.read_text()

            if platform == 'linear':
                assert 'mcp__linear-server__create_issue' in spec_command_content
            elif platform == 'github':
                assert 'mcp__github__create_issue' in spec_command_content
            elif platform == 'markdown':
                assert 'Write' in spec_command_content

    def test_agent_templates_contain_platform_specific_tools(self, tmp_path: Path) -> None:
        for platform in ['linear', 'github', 'markdown']:
            project_path = tmp_path / f'{platform}_test_project'
            project_path.mkdir()

            result = subprocess.run(
                [
                    'uv',
                    'run',
                    'respec-ai',
                    'init',
                    '--platform',
                    platform,
                    '--project-name',
                    'test-project',
                    '--skip-mcp-registration',
                ],
                cwd=str(project_path),
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0

            create_spec_agent_path = project_path / '.claude' / 'agents' / 'respec-create-spec.md'
            create_spec_agent_content = create_spec_agent_path.read_text()

            if platform == 'linear':
                assert 'mcp__linear-server__create_issue' in create_spec_agent_content
            elif platform == 'github':
                assert 'mcp__github__create_issue' in create_spec_agent_content
            elif platform == 'markdown':
                assert 'Write' in create_spec_agent_content

    def test_platform_config_contains_correct_metadata(self, tmp_path: Path) -> None:
        project_path = tmp_path / 'test_project'
        project_path.mkdir()

        result = subprocess.run(
            [
                'uv',
                'run',
                'respec-ai',
                'init',
                '--platform',
                'linear',
                '--project-name',
                'test-project',
                '--skip-mcp-registration',
            ],
            cwd=str(project_path),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        config_file_path = project_path / '.respec-ai' / 'config.json'
        config_data = json.loads(config_file_path.read_text())

        assert config_data['platform'] == 'linear'
        assert config_data['project_name'] == 'test-project'
        assert 'created_at' in config_data
        assert config_data['version'] == '0.3.0'
