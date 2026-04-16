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
        assert call_kwargs['log_config']['Type'] == DockerManager.CONTAINER_LOG_DRIVER
        assert call_kwargs['log_config']['Config'] == DockerManager.CONTAINER_LOG_OPTIONS

    def test_start_container_env_includes_database_url(self) -> None:
        assert 'DATABASE_URL' in DockerManager.CONTAINER_ENV
        assert 'respec-ai-db-prod' in DockerManager.CONTAINER_ENV['DATABASE_URL']

    def test_start_container_env_includes_state_manager(self) -> None:
        assert DockerManager.CONTAINER_ENV['MCP_STATE_MANAGER'] == 'database'

    def test_start_container_uses_log_rotation_settings(self) -> None:
        assert DockerManager.CONTAINER_LOG_DRIVER == 'json-file'
        assert DockerManager.CONTAINER_LOG_OPTIONS == {'max-size': '10m', 'max-file': '5'}


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
        mock_network.attrs = {'Containers': {}}
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
        mock_network.attrs = {'Containers': {}}
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
        mock_network = MagicMock()
        mock_network.attrs = {'Containers': {'db-container-id': {'Name': 'respec-ai-db-prod'}}}
        mock_client.networks.get.return_value = mock_network

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.ensure_db_running()

        mock_network.connect.assert_not_called()


class TestCleanupOldVersions:
    def test_does_not_remove_database_container(self) -> None:
        mock_client = MagicMock()
        current_server = MagicMock()
        current_server.name = 'respec-ai-1.0.0'
        old_server = MagicMock()
        old_server.name = 'respec-ai-0.9.0'
        db_container = MagicMock()
        db_container.name = DockerManager.DB_CONTAINER_NAME

        mock_client.containers.list.return_value = [current_server, old_server, db_container]
        mock_client.images.list.return_value = []

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.cleanup_old_versions(version='1.0.0')

        old_server.remove.assert_called_once_with(force=True)
        current_server.remove.assert_not_called()
        db_container.remove.assert_not_called()

    def test_only_removes_versioned_server_containers(self) -> None:
        mock_client = MagicMock()
        versioned_old_server = MagicMock()
        versioned_old_server.name = 'respec-ai-0.8.0'
        non_versioned_server = MagicMock()
        non_versioned_server.name = 'respec-ai-dev'
        unrelated_container = MagicMock()
        unrelated_container.name = 'other-app'

        mock_client.containers.list.return_value = [versioned_old_server, non_versioned_server, unrelated_container]
        mock_client.images.list.return_value = []

        with patch('src.cli.docker.manager.docker.from_env', return_value=mock_client):
            manager = DockerManager()
            manager.cleanup_old_versions(version='1.0.0')

        versioned_old_server.remove.assert_called_once_with(force=True)
        non_versioned_server.remove.assert_not_called()
        unrelated_container.remove.assert_not_called()
