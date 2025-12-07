from argparse import Namespace

from pytest_mock import MockerFixture
from src.cli.commands import register_mcp
from src.cli.config.claude_config import ClaudeConfigError
from src.cli.docker.manager import DockerManagerError


class TestRegisterMcpCommand:
    def test_new_registration_success(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.load_claude_config',
            return_value={'mcpServers': {}},
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value=None,
        )
        mock_register = mocker.patch(
            'src.cli.commands.register_mcp.register_mcp_server',
            return_value=True,
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )

        mock_docker_manager = mocker.MagicMock()
        mock_docker_manager.get_container_status.return_value = {'exists': True, 'running': True}
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            return_value=mock_docker_manager,
        )

        args = Namespace(force=False)
        result = register_mcp.run(args)

        assert result == 0
        mock_register.assert_called_once_with(force=False)
        mock_docker_manager.ensure_running.assert_not_called()

    def test_already_registered_without_force(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.load_claude_config',
            return_value={'mcpServers': {'RespecAI': {'command': 'docker'}}},
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value={'command': 'docker'},
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )

        mock_docker_manager = mocker.MagicMock()
        mock_docker_manager.get_container_status.return_value = {'exists': True, 'running': True}
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            return_value=mock_docker_manager,
        )

        args = Namespace(force=False)
        result = register_mcp.run(args)

        assert result == 0

    def test_force_reregister(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value={'command': 'old'},
        )
        mock_register = mocker.patch(
            'src.cli.commands.register_mcp.register_mcp_server',
            return_value=True,
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )

        mock_docker_manager = mocker.MagicMock()
        mock_docker_manager.get_container_status.return_value = {'exists': True, 'running': True}
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            return_value=mock_docker_manager,
        )

        args = Namespace(force=True)
        result = register_mcp.run(args)

        assert result == 0
        mock_register.assert_called_once_with(force=True)

    def test_container_not_exists(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value=None,
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )

        mock_docker_manager = mocker.MagicMock()
        mock_docker_manager.get_container_status.return_value = {'exists': False, 'running': False}
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            return_value=mock_docker_manager,
        )

        args = Namespace(force=False)
        result = register_mcp.run(args)

        assert result == 1

    def test_container_not_running_starts_successfully(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.load_claude_config',
            return_value={'mcpServers': {}},
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value=None,
        )
        mock_register = mocker.patch(
            'src.cli.commands.register_mcp.register_mcp_server',
            return_value=True,
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )

        mock_docker_manager = mocker.MagicMock()
        mock_docker_manager.get_container_status.return_value = {'exists': True, 'running': False}
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            return_value=mock_docker_manager,
        )

        args = Namespace(force=False)
        result = register_mcp.run(args)

        assert result == 0
        mock_docker_manager.ensure_running.assert_called_once()
        mock_register.assert_called_once_with(force=False)

    def test_docker_manager_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value=None,
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            side_effect=DockerManagerError('Docker daemon not running'),
        )

        args = Namespace(force=False)
        result = register_mcp.run(args)

        assert result == 1

    def test_claude_config_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            'src.cli.commands.register_mcp.get_mcp_server_config',
            return_value=None,
        )
        mocker.patch(
            'src.cli.commands.register_mcp.register_mcp_server',
            side_effect=ClaudeConfigError('Config error'),
        )
        mocker.patch(
            'src.cli.commands.register_mcp.get_package_version',
            return_value='0.3.0',
        )

        mock_docker_manager = mocker.MagicMock()
        mock_docker_manager.get_container_status.return_value = {'exists': True, 'running': True}
        mocker.patch(
            'src.cli.commands.register_mcp.DockerManager',
            return_value=mock_docker_manager,
        )

        args = Namespace(force=False)
        result = register_mcp.run(args)

        assert result == 1
