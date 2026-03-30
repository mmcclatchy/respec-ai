import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import register_mcp
from src.cli.config.claude_config import ClaudeConfigError
from src.cli.docker.manager import DockerManagerError
from src.platform.tui_adapters.opencode import OpenCodeAdapter


@pytest.fixture
def project_with_config(tmp_path: Path, mocker: MockerFixture) -> Path:
    config_dir = tmp_path / '.respec-ai'
    config_dir.mkdir()
    config_path = config_dir / 'config.json'
    config_path.write_text(json.dumps({'tui': 'claude-code', 'platform': 'linear'}))
    mocker.patch('src.cli.commands.register_mcp.Path.cwd', return_value=tmp_path)
    return tmp_path


@pytest.fixture
def mock_adapter(mocker: MockerFixture) -> MagicMock:
    adapter = MagicMock()
    adapter.is_mcp_registered.return_value = False
    adapter.register_mcp_server.return_value = True
    mocker.patch('src.cli.commands.register_mcp.get_tui_adapter', return_value=adapter)
    return adapter


@pytest.fixture
def mock_docker(mocker: MockerFixture) -> MagicMock:
    manager = MagicMock()
    manager.get_container_status.return_value = {'exists': True, 'running': True}
    mocker.patch('src.cli.commands.register_mcp.DockerManager', return_value=manager)
    return manager


class TestRegisterMcpCommand:
    def test_new_registration_success(
        self, project_with_config: Path, mock_adapter: MagicMock, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        result = register_mcp.run(Namespace(force=False))
        assert result == 0
        mock_adapter.register_mcp_server.assert_called_once_with(project_with_config)

    def test_already_registered_without_force(
        self, project_with_config: Path, mock_adapter: MagicMock, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        mock_adapter.is_mcp_registered.return_value = True
        result = register_mcp.run(Namespace(force=False))
        assert result == 0
        mock_adapter.register_mcp_server.assert_not_called()

    def test_force_reregister(
        self, project_with_config: Path, mock_adapter: MagicMock, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        mock_adapter.is_mcp_registered.return_value = True
        result = register_mcp.run(Namespace(force=True))
        assert result == 0
        mock_adapter.register_mcp_server.assert_called_once_with(project_with_config)

    def test_container_not_exists(
        self, project_with_config: Path, mock_adapter: MagicMock, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        mock_docker.get_container_status.return_value = {'exists': False, 'running': False}
        result = register_mcp.run(Namespace(force=False))
        assert result == 1

    def test_container_not_running_starts_successfully(
        self, project_with_config: Path, mock_adapter: MagicMock, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        mock_docker.get_container_status.return_value = {'exists': True, 'running': False}
        result = register_mcp.run(Namespace(force=False))
        assert result == 0
        mock_docker.ensure_running.assert_called_once()
        mock_adapter.register_mcp_server.assert_called_once()

    def test_docker_manager_error(
        self, project_with_config: Path, mock_adapter: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            side_effect=DockerManagerError('Docker daemon not running'),
        )
        result = register_mcp.run(Namespace(force=False))
        assert result == 1

    def test_claude_config_error(
        self, project_with_config: Path, mock_adapter: MagicMock, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')
        mock_adapter.register_mcp_server.side_effect = ClaudeConfigError('Config error')
        result = register_mcp.run(Namespace(force=False))
        assert result == 1

    def test_not_initialized(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch('src.cli.commands.register_mcp.Path.cwd', return_value=tmp_path)
        result = register_mcp.run(Namespace(force=False))
        assert result == 1

    def test_opencode_tui_uses_opencode_adapter(
        self, tmp_path: Path, mock_docker: MagicMock, mocker: MockerFixture
    ) -> None:
        config_dir = tmp_path / '.respec-ai'
        config_dir.mkdir()
        (config_dir / 'config.json').write_text(json.dumps({'tui': 'opencode', 'platform': 'linear'}))
        mocker.patch('src.cli.commands.register_mcp.Path.cwd', return_value=tmp_path)
        mocker.patch('src.cli.commands.register_mcp.get_package_version', return_value='0.3.0')

        mock_get_adapter = mocker.patch(
            'src.cli.commands.register_mcp.get_tui_adapter', return_value=MagicMock(spec=OpenCodeAdapter)
        )

        result = register_mcp.run(Namespace(force=False))
        assert result == 0
        mock_get_adapter.assert_called_once()
