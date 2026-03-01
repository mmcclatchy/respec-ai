import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import init
from src.cli.config.claude_config import ClaudeConfigError
from src.platform.models import ProjectStack


class TestInitCommand:
    def test_successful_initialization(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        result = init.run(args)

        assert result == 0
        assert (tmp_path / '.respec-ai' / 'config.json').exists()

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['platform'] == 'linear'
        assert config['version'] == '0.2.0'
        assert config['project_name'] == tmp_path.name

    def test_stack_prompts_called_when_yes_false(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')
        mocker.patch('src.cli.commands.init.console')

        mock_prompt = mocker.patch(
            'src.cli.commands.init.prompt_stack_profile',
            return_value=ProjectStack(language='python'),
        )

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=False, force=False)
        result = init.run(args)

        assert result == 0
        mock_prompt.assert_called_once()

    def test_stack_prompts_skipped_when_yes_true(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')

        mock_prompt = mocker.patch('src.cli.commands.init.prompt_stack_profile')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        result = init.run(args)

        assert result == 0
        mock_prompt.assert_not_called()

    def test_config_includes_all_stack_fields(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')
        mocker.patch(
            'src.cli.commands.init.detect_project_stack',
            return_value=ProjectStack(language='python'),
        )

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        init.run(args)

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        stack = config['stack']
        assert stack['language'] == 'python'
        assert stack['backend_framework'] is None
        assert stack['frontend_framework'] is None
        assert stack['database'] is None
        assert stack['async_runtime'] is None
        assert len(stack) == 12

    def test_already_initialized(self, mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text('{}')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        result = init.run(args)

        assert result == 1

    def test_skip_mcp_registration(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mock_register = mocker.patch('src.cli.commands.init.register_mcp_server')

        args = Namespace(platform='linear', project_name='MyProject', skip_mcp_registration=True, yes=True, force=False)
        result = init.run(args)

        assert result == 0
        mock_register.assert_not_called()

    def test_custom_plan_name(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')

        args = Namespace(
            platform='github', project_name='CustomName', skip_mcp_registration=False, yes=True, force=False
        )
        result = init.run(args)

        assert result == 0

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['project_name'] == 'CustomName'
        assert config['platform'] == 'github'

    def test_mcp_registration_failure_continues(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch(
            'src.cli.commands.init.register_mcp_server', side_effect=ClaudeConfigError('MCP registration failed')
        )
        mock_docker = mocker.patch('src.cli.commands.init.DockerManager')
        mock_docker.return_value.verify_image_exists.return_value = True

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        result = init.run(args)

        assert result == 0
        assert (tmp_path / '.respec-ai' / 'config.json').exists()

    def test_existing_stack_with_yes_flag_preserves_stack(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        existing_config = {
            'project_name': 'test-project',
            'platform': 'linear',
            'stack': {
                'language': 'python',
                'backend_framework': 'fastapi',
                'frontend_framework': None,
                'database': 'postgresql',
                'async_runtime': None,
                'package_manager': 'uv',
                'type_checker': 'ty',
                'runtime_version': '3.13',
                'api_style': 'rest',
                'css_framework': None,
                'ui_components': None,
                'architecture': 'monolith',
            },
        }
        (respec_ai_dir / 'config.json').write_text(json.dumps(existing_config))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')

        mock_detect = mocker.patch('src.cli.commands.init.detect_project_stack')
        mock_prompt = mocker.patch('src.cli.commands.init.prompt_stack_profile')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        result = init.run(args)

        assert result == 0
        mock_detect.assert_not_called()
        mock_prompt.assert_not_called()

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['stack']['language'] == 'python'
        assert config['stack']['backend_framework'] == 'fastapi'
        assert config['stack']['database'] == 'postgresql'
        assert config['stack']['type_checker'] == 'ty'
        assert config['stack']['architecture'] == 'monolith'

    def test_existing_stack_without_yes_flag_prompts_user_option_1(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        existing_config = {
            'project_name': 'test-project',
            'platform': 'linear',
            'stack': {
                'language': 'python',
                'backend_framework': 'fastapi',
                'frontend_framework': None,
                'database': 'postgresql',
                'async_runtime': None,
                'package_manager': 'uv',
                'type_checker': 'ty',
                'runtime_version': '3.13',
                'api_style': 'rest',
                'css_framework': None,
                'ui_components': None,
                'architecture': 'monolith',
            },
        }
        (respec_ai_dir / 'config.json').write_text(json.dumps(existing_config))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')

        mock_console = mocker.patch('src.cli.commands.init.console')
        mock_console.input.side_effect = ['1', 'y']

        mock_detect = mocker.patch('src.cli.commands.init.detect_project_stack')
        mock_prompt = mocker.patch('src.cli.commands.init.prompt_stack_profile')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=False, force=False)
        result = init.run(args)

        assert result == 0
        mock_detect.assert_not_called()
        mock_prompt.assert_not_called()
        assert mock_console.input.call_count == 2

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['stack']['language'] == 'python'
        assert config['stack']['backend_framework'] == 'fastapi'
        assert config['stack']['type_checker'] == 'ty'
        assert config['stack']['architecture'] == 'monolith'

    def test_existing_stack_without_yes_flag_prompts_user_option_2(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        existing_config = {
            'project_name': 'test-project',
            'platform': 'linear',
            'stack': {
                'language': 'python',
                'backend_framework': 'fastapi',
                'frontend_framework': None,
                'database': 'postgresql',
                'async_runtime': None,
                'package_manager': 'uv',
                'type_checker': 'ty',
                'runtime_version': '3.13',
                'api_style': 'rest',
                'css_framework': None,
                'ui_components': None,
                'architecture': 'monolith',
            },
        }
        (respec_ai_dir / 'config.json').write_text(json.dumps(existing_config))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')

        mock_console = mocker.patch('src.cli.commands.init.console')
        mock_console.input.side_effect = ['2', 'y']

        mock_detect = mocker.patch(
            'src.cli.commands.init.detect_project_stack',
            return_value=ProjectStack(language='typescript'),
        )
        mock_prompt = mocker.patch(
            'src.cli.commands.init.prompt_stack_profile',
            return_value=ProjectStack(language='typescript'),
        )

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=False, force=False)
        result = init.run(args)

        assert result == 0
        mock_detect.assert_called_once()
        mock_prompt.assert_called_once()

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['stack']['language'] == 'typescript'

    def test_existing_stack_invalid_choice_returns_error(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        existing_config = {
            'project_name': 'test-project',
            'platform': 'linear',
            'stack': {'language': 'python'},
        }
        (respec_ai_dir / 'config.json').write_text(json.dumps(existing_config))

        mock_console = mocker.patch('src.cli.commands.init.console')
        mock_console.input.return_value = '3'

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=False, force=False)
        result = init.run(args)

        assert result == 1
