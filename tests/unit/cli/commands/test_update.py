from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from src.cli.commands import update
from src.cli.docker.manager import DockerManagerError


class TestUpdateDocker:
    def test_no_new_version_skips_stop_start_and_cleans_up(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.0.0')

        assert result is True
        mock_manager.get_container_status.assert_not_called()
        mock_manager.stop_container.assert_not_called()
        mock_manager.start_container.assert_not_called()
        mock_manager.ensure_running.assert_not_called()
        mock_manager.cleanup_old_versions.assert_called_once_with(version='1.0.0')

    def test_no_new_version_pull_failure_skips_cleanup(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mock_manager.pull_image.side_effect = DockerManagerError('pull failed')
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.0.0')

        assert result is False
        mock_manager.stop_container.assert_not_called()
        mock_manager.start_container.assert_not_called()
        mock_manager.ensure_running.assert_not_called()
        mock_manager.cleanup_old_versions.assert_not_called()

    def test_new_version_stops_old_and_starts_new(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = {'running': True}
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.1.0')

        assert result is True
        mock_manager.get_container_status.assert_called_once_with(version='1.0.0')
        mock_manager.stop_container.assert_called_once_with(version='1.0.0')
        mock_manager.pull_image.assert_called_once_with(version='1.1.0')
        mock_manager.cleanup_old_versions.assert_called_once_with(version='1.1.0')
        mock_manager.start_container.assert_called_once_with(version='1.1.0')

    def test_new_version_pull_failure_restores_previous_running_container(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = {'running': True}
        mock_manager.pull_image.side_effect = DockerManagerError('pull failed')
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.1.0')

        assert result is False
        mock_manager.stop_container.assert_called_once_with(version='1.0.0')
        mock_manager.ensure_running.assert_called_once_with(version='1.0.0')
        mock_manager.cleanup_old_versions.assert_not_called()
        mock_manager.start_container.assert_not_called()
