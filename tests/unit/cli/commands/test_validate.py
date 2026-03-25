import json
from argparse import Namespace
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import validate
from src.platform.template_generator import EXPECTED_AGENTS_COUNT, EXPECTED_COMMANDS_COUNT


class TestValidateCommand:
    def test_all_checks_pass(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0', 'plan_name': 'test'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir()
        agents_dir.mkdir()

        for i in range(EXPECTED_COMMANDS_COUNT):
            (commands_dir / f'cmd{i}.md').touch()
        for i in range(EXPECTED_AGENTS_COUNT):
            (agents_dir / f'agent{i}.md').touch()

        mocker.patch('src.cli.commands.validate.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.validate.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.validate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.validate.is_mcp_server_registered', return_value=True)

        args = Namespace()
        result = validate.run(args)

        assert result == 0

    def test_not_initialized(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        mocker.patch('src.cli.commands.validate.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.validate.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.validate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.validate.is_mcp_server_registered', return_value=False)

        args = Namespace()
        result = validate.run(args)

        assert result == 1

    def test_invalid_platform(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'invalid', 'version': '0.2.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir()
        agents_dir.mkdir()

        for i in range(EXPECTED_COMMANDS_COUNT):
            (commands_dir / f'cmd{i}.md').touch()
        for i in range(EXPECTED_AGENTS_COUNT):
            (agents_dir / f'agent{i}.md').touch()

        mocker.patch('src.cli.commands.validate.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.validate.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.validate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.validate.is_mcp_server_registered', return_value=True)

        args = Namespace()
        result = validate.run(args)

        assert result == 1

    def test_wrong_file_counts(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir()
        agents_dir.mkdir()

        for i in range(3):
            (commands_dir / f'cmd{i}.md').touch()
        for i in range(10):
            (agents_dir / f'agent{i}.md').touch()

        mocker.patch('src.cli.commands.validate.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.validate.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.validate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.validate.is_mcp_server_registered', return_value=True)

        args = Namespace()
        result = validate.run(args)

        assert result == 1

    def test_mcp_not_registered(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.2.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir()
        agents_dir.mkdir()

        for i in range(EXPECTED_COMMANDS_COUNT):
            (commands_dir / f'cmd{i}.md').touch()
        for i in range(EXPECTED_AGENTS_COUNT):
            (agents_dir / f'agent{i}.md').touch()

        mocker.patch('src.cli.commands.validate.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.validate.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.validate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.validate.is_mcp_server_registered', return_value=False)

        args = Namespace()
        result = validate.run(args)

        assert result == 1

    def test_version_mismatch(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        respec_ai_dir = tmp_path / '.respec-ai'
        respec_ai_dir.mkdir()
        config_data = {'platform': 'linear', 'version': '0.1.0'}
        (respec_ai_dir / 'config.json').write_text(json.dumps(config_data))

        commands_dir = tmp_path / 'commands'
        agents_dir = tmp_path / 'agents'
        commands_dir.mkdir()
        agents_dir.mkdir()

        for i in range(EXPECTED_COMMANDS_COUNT):
            (commands_dir / f'cmd{i}.md').touch()
        for i in range(EXPECTED_AGENTS_COUNT):
            (agents_dir / f'agent{i}.md').touch()

        mocker.patch('src.cli.commands.validate.get_commands_dir', return_value=commands_dir)
        mocker.patch('src.cli.commands.validate.get_agents_dir', return_value=agents_dir)
        mocker.patch('src.cli.commands.validate.get_package_version', return_value='0.2.0')
        mocker.patch('src.cli.commands.validate.is_mcp_server_registered', return_value=True)

        args = Namespace()
        result = validate.run(args)

        assert result == 1
