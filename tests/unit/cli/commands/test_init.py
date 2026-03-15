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

    def test_config_excludes_stack_and_tooling(
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
        assert 'stack' not in config
        assert 'tooling' not in config
        assert config['project_name'] == tmp_path.name
        assert config['platform'] == 'linear'
        assert 'version' in config
        assert 'created_at' in config

    def test_legacy_config_without_config_dir_triggers_migration(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text('{}')

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'

        mocker.patch('src.cli.commands.init.PlatformOrchestrator')
        mocker.patch('src.cli.commands.init.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.init.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.init.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.init.generate_templates', return_value=([Path('file1.md')], 5, 12))
        mocker.patch('src.cli.commands.init.register_mcp_server', return_value=True)
        mocker.patch('src.cli.commands.init.DockerManager')
        mock_detect = mocker.patch(
            'src.cli.commands.init.detect_project_stack',
            return_value=ProjectStack(language='python'),
        )

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=True, force=False)
        result = init.run(args)

        assert result == 0
        mock_detect.assert_called_once()
        assert (respec_ai_dir / 'config.json').exists()

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

    def test_existing_config_with_yes_flag_preserves_config(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text(
            json.dumps(
                {
                    'project_name': 'test-project',
                    'platform': 'linear',
                }
            )
        )
        config_dir = respec_ai_dir / 'config'
        config_dir.mkdir()
        (config_dir / 'stack.md').write_text('# Project Stack\n\n## Languages\n- Python 3.13')
        (config_dir / 'python.md').write_text('# Python\n\n## Commands\n- **Test**: `pytest`')

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

        assert (config_dir / 'stack.md').read_text() == '# Project Stack\n\n## Languages\n- Python 3.13'
        assert (config_dir / 'python.md').read_text() == '# Python\n\n## Commands\n- **Test**: `pytest`'

    def test_existing_config_without_yes_flag_prompts_user_option_1(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text(
            json.dumps(
                {
                    'project_name': 'test-project',
                    'platform': 'linear',
                }
            )
        )
        config_dir = respec_ai_dir / 'config'
        config_dir.mkdir()
        (config_dir / 'stack.md').write_text('# Project Stack')
        (config_dir / 'python.md').write_text('# Python')

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
        mock_console.input.return_value = '1'

        mock_detect = mocker.patch('src.cli.commands.init.detect_project_stack')
        mock_prompt = mocker.patch('src.cli.commands.init.prompt_stack_profile')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=False, force=False)
        result = init.run(args)

        assert result == 0
        mock_detect.assert_not_called()
        mock_prompt.assert_not_called()
        mock_console.input.assert_called_once()

        assert (config_dir / 'stack.md').read_text() == '# Project Stack'
        assert (config_dir / 'python.md').read_text() == '# Python'

    def test_existing_config_without_yes_flag_prompts_user_option_2(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text(
            json.dumps(
                {
                    'project_name': 'test-project',
                    'platform': 'linear',
                }
            )
        )
        config_dir = respec_ai_dir / 'config'
        config_dir.mkdir()
        (config_dir / 'stack.md').write_text('# Old Stack')

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
        assert 'stack' not in config

    def test_existing_config_invalid_choice_returns_error(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        (respec_ai_dir / 'config.json').write_text(
            json.dumps(
                {
                    'project_name': 'test-project',
                    'platform': 'linear',
                }
            )
        )
        config_dir = respec_ai_dir / 'config'
        config_dir.mkdir()
        (config_dir / 'stack.md').write_text('# Project Stack')

        mock_console = mocker.patch('src.cli.commands.init.console')
        mock_console.input.return_value = '3'

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False, yes=False, force=False)
        result = init.run(args)

        assert result == 1
