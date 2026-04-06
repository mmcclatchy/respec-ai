from argparse import Namespace
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from src.cli.commands import mcp_server
from src.cli.docker.manager import DockerManagerError


class TestMcpServerCommand:
    def test_uses_current_running_container_when_available(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': True, 'name': 'respec-ai-0.13.5'}
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        primary = MagicMock(returncode=0)
        run_mock = mocker.patch('src.cli.commands.mcp_server.subprocess.run', return_value=primary)

        result = mcp_server.run(Namespace())

        assert result == 0
        run_mock.assert_called_once()
        cmd = run_mock.call_args.args[0]
        assert cmd[:4] == ['docker', 'exec', '-i', 'respec-ai-0.13.5']
        assert cmd[4:] == ['uv', 'run', 'respec-server']
        manager.ensure_running.assert_not_called()

    def test_uses_any_running_version_when_current_not_running(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': False, 'name': 'respec-ai-0.13.5'}
        manager.CONTAINER_NAME_PREFIX = 'respec-ai'
        manager.DB_CONTAINER_NAME = 'respec-ai-db-prod'
        manager.IMAGE_NAME = 'respec-ai-server'
        manager.REGISTRIES = ['ghcr.io/mmcclatchy/respec-ai-server']
        manager.list_all_containers.return_value = [
            {
                'name': 'respec-ai-0.13.4',
                'status': 'running',
                'image': 'ghcr.io/mmcclatchy/respec-ai-server:0.13.4',
            }
        ]
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        run_mock = mocker.patch('src.cli.commands.mcp_server.subprocess.run', return_value=MagicMock(returncode=0))

        result = mcp_server.run(Namespace())

        assert result == 0
        cmd = run_mock.call_args.args[0]
        assert cmd[:4] == ['docker', 'exec', '-i', 'respec-ai-0.13.4']
        manager.ensure_running.assert_not_called()

    def test_starts_container_when_none_running(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': False, 'name': 'respec-ai-0.13.5'}
        manager.CONTAINER_NAME_PREFIX = 'respec-ai'
        manager.DB_CONTAINER_NAME = 'respec-ai-db-prod'
        manager.IMAGE_NAME = 'respec-ai-server'
        manager.REGISTRIES = ['ghcr.io/mmcclatchy/respec-ai-server']
        manager.list_all_containers.return_value = []
        container = MagicMock()
        container.name = 'respec-ai-0.13.5'
        manager.ensure_running.return_value = container
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        run_mock = mocker.patch('src.cli.commands.mcp_server.subprocess.run', return_value=MagicMock(returncode=0))

        result = mcp_server.run(Namespace())

        assert result == 0
        manager.ensure_running.assert_called_once()
        cmd = run_mock.call_args.args[0]
        assert cmd[:4] == ['docker', 'exec', '-i', 'respec-ai-0.13.5']

    def test_falls_back_to_module_entrypoint_when_primary_exec_fails(self, mocker: MockerFixture) -> None:
        manager = MagicMock()
        manager.get_container_status.return_value = {'running': True, 'name': 'respec-ai-0.13.5'}
        mocker.patch('src.cli.commands.mcp_server.DockerManager', return_value=manager)

        run_mock = mocker.patch(
            'src.cli.commands.mcp_server.subprocess.run',
            side_effect=[MagicMock(returncode=1), MagicMock(returncode=0)],
        )

        result = mcp_server.run(Namespace())

        assert result == 0
        assert run_mock.call_count == 2
        primary_cmd = run_mock.call_args_list[0].args[0]
        fallback_cmd = run_mock.call_args_list[1].args[0]
        assert primary_cmd[4:] == ['uv', 'run', 'respec-server']
        assert fallback_cmd[4:] == ['uv', 'run', 'python', '-m', 'src.mcp']

    def test_docker_manager_error_returns_failure(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.mcp_server.DockerManager',
            side_effect=DockerManagerError('docker unavailable'),
        )

        result = mcp_server.run(Namespace())

        assert result == 1
