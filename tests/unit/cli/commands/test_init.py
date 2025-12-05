import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from src.cli.commands import init
from src.cli.config.claude_config import ClaudeConfigError


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

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False)
        result = init.run(args)

        assert result == 0
        assert (tmp_path / '.respec-ai' / 'config.json').exists()

        config = json.loads((tmp_path / '.respec-ai' / 'config.json').read_text())
        assert config['platform'] == 'linear'
        assert config['version'] == '0.2.0'
        assert config['project_name'] == tmp_path.name

    def test_already_initialized(self, mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        reRESPEC_AI_dir = tmp_path / '.respec-ai'
        reRESPEC_AI_dir.mkdir()
        (reRESPEC_AI_dir / 'config.json').write_text('{}')

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False)
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

        args = Namespace(platform='linear', project_name='MyProject', skip_mcp_registration=True)
        result = init.run(args)

        assert result == 0
        mock_register.assert_not_called()

    def test_custom_project_name(
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

        args = Namespace(platform='github', project_name='CustomName', skip_mcp_registration=False)
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

        args = Namespace(platform='linear', project_name=None, skip_mcp_registration=False)
        result = init.run(args)

        assert result == 0
        assert (tmp_path / '.respec-ai' / 'config.json').exists()
