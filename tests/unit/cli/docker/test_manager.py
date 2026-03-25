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


class TestEnsureDbRunning:
    def test_starts_db_container_when_not_found(self) -> None:
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound('not found')

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.ensure_db_running()

        call_kwargs = mock_client.containers.run.call_args.kwargs
        assert call_kwargs['image'] == DockerManager.DB_IMAGE
        assert call_kwargs['name'] == DockerManager.DB_CONTAINER_NAME
        assert call_kwargs['environment'] == DockerManager.DB_ENV
        assert call_kwargs['network'] == DockerManager.DB_NETWORK_NAME

    def test_connects_existing_stopped_db_to_network(self) -> None:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.status = 'exited'
        mock_db.id = 'db-container-id'
        mock_client.containers.get.return_value = mock_db
        mock_network = MagicMock()
        mock_network.containers = []
        mock_client.networks.get.return_value = mock_network

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.ensure_db_running()

        mock_db.start.assert_called_once()
        mock_network.connect.assert_called_once_with(mock_db)

    def test_connects_running_db_to_network_if_not_connected(self) -> None:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.status = 'running'
        mock_db.id = 'db-container-id'
        mock_client.containers.get.return_value = mock_db
        mock_network = MagicMock()
        mock_network.containers = []
        mock_client.networks.get.return_value = mock_network

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.ensure_db_running()

        mock_db.start.assert_not_called()
        mock_network.connect.assert_called_once_with(mock_db)

    def test_skips_network_connect_when_already_connected(self) -> None:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.status = 'running'
        mock_db.id = 'db-container-id'
        mock_client.containers.get.return_value = mock_db
        mock_already_connected = MagicMock()
        mock_already_connected.id = 'db-container-id'
        mock_network = MagicMock()
        mock_network.containers = [mock_already_connected]
        mock_client.networks.get.return_value = mock_network

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.ensure_db_running()

        mock_network.connect.assert_not_called()
