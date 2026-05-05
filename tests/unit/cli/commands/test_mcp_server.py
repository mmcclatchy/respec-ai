from argparse import Namespace
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from src.cli.commands import mcp_server
from src.cli.docker.manager import DockerManagerError


class TestMcpServerCommand:
    def test_uses_current_running_container_when_available(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': True, 'name': 'respec-ai-0.13.5'}
        manager.MCP_DAEMON_HOST = '127.0.0.1'
        manager.MCP_DAEMON_PORT = 9876
        manager.MCP_DAEMON_PATH = '/mcp'
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        proxy = MagicMock()
        create_proxy = mocker.patch('src.cli.commands.mcp_server.create_proxy', return_value=proxy)

        result = mcp_server.run(Namespace())

        assert result == 0
        create_proxy.assert_called_once_with('http://127.0.0.1:9876/mcp', name='respec-ai')
        proxy.run.assert_called_once_with(transport='stdio', show_banner=False)
        manager.ensure_running.assert_not_called()

    def test_uses_any_running_version_when_current_not_running(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': False, 'name': 'respec-ai-0.13.5'}
        manager.CONTAINER_NAME_PREFIX = 'respec-ai'
        manager.DB_CONTAINER_NAME = 'respec-ai-db-prod'
        manager.IMAGE_NAME = 'respec-ai-server'
        manager.REGISTRIES = ['ghcr.io/mmcclatchy/respec-ai-server']
        manager.MCP_DAEMON_HOST = '127.0.0.1'
        manager.MCP_DAEMON_PORT = 9876
        manager.MCP_DAEMON_PATH = '/mcp'
        manager.list_all_containers.return_value = [
            {
                'name': 'respec-ai-0.13.4',
                'status': 'running',
                'image': 'ghcr.io/mmcclatchy/respec-ai-server:0.13.4',
            }
        ]
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        proxy = MagicMock()
        create_proxy = mocker.patch('src.cli.commands.mcp_server.create_proxy', return_value=proxy)

        result = mcp_server.run(Namespace())

        assert result == 0
        create_proxy.assert_called_once_with('http://127.0.0.1:9876/mcp', name='respec-ai')
        proxy.run.assert_called_once_with(transport='stdio', show_banner=False)
        manager.ensure_running.assert_not_called()

    def test_starts_container_when_none_running(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': False, 'name': 'respec-ai-0.13.5'}
        manager.CONTAINER_NAME_PREFIX = 'respec-ai'
        manager.DB_CONTAINER_NAME = 'respec-ai-db-prod'
        manager.IMAGE_NAME = 'respec-ai-server'
        manager.REGISTRIES = ['ghcr.io/mmcclatchy/respec-ai-server']
        manager.MCP_DAEMON_HOST = '127.0.0.1'
        manager.MCP_DAEMON_PORT = 9876
        manager.MCP_DAEMON_PATH = '/mcp'
        manager.list_all_containers.return_value = []
        container = MagicMock()
        container.name = 'respec-ai-0.13.5'
        manager.ensure_running.return_value = container
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        proxy = MagicMock()
        create_proxy = mocker.patch('src.cli.commands.mcp_server.create_proxy', return_value=proxy)

        result = mcp_server.run(Namespace())

        assert result == 0
        manager.ensure_running.assert_called_once()
        create_proxy.assert_called_once_with('http://127.0.0.1:9876/mcp', name='respec-ai')
        proxy.run.assert_called_once_with(transport='stdio', show_banner=False)

    def test_proxy_failure_returns_failure(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': True, 'name': 'respec-ai-0.13.5'}
        manager.MCP_DAEMON_HOST = '127.0.0.1'
        manager.MCP_DAEMON_PORT = 9876
        manager.MCP_DAEMON_PATH = '/mcp'
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)
        mocker.patch('src.cli.commands.mcp_server.create_proxy', side_effect=RuntimeError('proxy unavailable'))

        result = mcp_server.run(Namespace())

        assert result == 1

    def test_docker_manager_error_returns_failure(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.mcp_server.DockerManager',
            side_effect=DockerManagerError('docker unavailable'),
        )

        result = mcp_server.run(Namespace())

        assert result == 1
