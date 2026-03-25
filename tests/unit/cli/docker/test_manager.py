from unittest.mock import MagicMock, patch

from docker.errors import NotFound

from src.cli.docker.manager import DockerManager


class TestStartContainer:
    def test_start_container_passes_environment_and_network(self) -> None:
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.side_effect = NotFound('not found')
        mock_client.images.get.return_value = MagicMock()
        mock_client.containers.run.return_value = mock_container

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.start_container(version='1.0.0')

        call_kwargs = mock_client.containers.run.call_args.kwargs
        assert call_kwargs['environment'] == DockerManager.CONTAINER_ENV
        assert call_kwargs['network'] == DockerManager.DB_NETWORK_NAME

    def test_start_container_env_includes_database_url(self) -> None:
        assert 'DATABASE_URL' in DockerManager.CONTAINER_ENV
        assert 'respec-ai-db-prod' in DockerManager.CONTAINER_ENV['DATABASE_URL']

    def test_start_container_env_includes_state_manager(self) -> None:
        assert DockerManager.CONTAINER_ENV['MCP_STATE_MANAGER'] == 'database'
