import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from src.cli.commands import update
from src.cli.docker.manager import DockerManagerError


class TestUpdateDocker:
    def test_no_new_version_ensures_running_and_cleans_up(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.0.0')

        assert result is True
        mock_manager.get_container_status.assert_not_called()
        mock_manager.stop_container.assert_not_called()
        mock_manager.start_container.assert_not_called()
        mock_manager.ensure_running.assert_called_once_with(version='1.0.0')
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

    def test_new_version_stops_old_and_ensures_new_running(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = {'running': True}
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.1.0')

        assert result is True
        mock_manager.get_container_status.assert_called_once_with(version='1.0.0')
        mock_manager.stop_container.assert_called_once_with(version='1.0.0')
        mock_manager.pull_image.assert_called_once_with(version='1.1.0')
        mock_manager.ensure_running.assert_called_once_with(version='1.1.0')
        mock_manager.cleanup_old_versions.assert_called_once_with(version='1.1.0')
        mock_manager.start_container.assert_not_called()

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

    def test_new_version_start_failure_restores_previous_running_container(self, mocker: MockerFixture) -> None:
        mock_manager = MagicMock()
        mock_manager.get_container_status.return_value = {'running': True}
        mock_manager.ensure_running.side_effect = [DockerManagerError('start failed'), MagicMock()]
        mocker.patch('src.cli.commands.update.DockerManager', return_value=mock_manager)

        result = update._update_docker(old_version='1.0.0', new_version='1.1.0')

        assert result is False
        mock_manager.stop_container.assert_called_once_with(version='1.0.0')
        mock_manager.pull_image.assert_called_once_with(version='1.1.0')
        assert mock_manager.ensure_running.call_count == 2
        mock_manager.ensure_running.assert_any_call(version='1.1.0')
        mock_manager.ensure_running.assert_any_call(version='1.0.0')
        mock_manager.cleanup_old_versions.assert_not_called()


class TestUpdateCommandRun:
    def test_run_does_not_invoke_missing_standards_render(
        self, tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_root = tmp_path / '.respec-ai'
        (config_root / 'config').mkdir(parents=True)
        (config_root / 'config.json').write_text(
            json.dumps({'platform': 'markdown', 'version': '1.0.0'}),
            encoding='utf-8',
        )

        commands: list[list[str]] = []

        def fake_run(cmd: list[str], capture_output: bool, text: bool) -> MagicMock:
            commands.append(cmd)
            return MagicMock(returncode=0, stdout='', stderr='')

        mocker.patch('src.cli.commands.update.get_package_version', return_value='1.0.0')
        mocker.patch('src.cli.commands.update._get_installed_version', return_value='1.0.0')
        mocker.patch('src.cli.commands.update.subprocess.run', side_effect=fake_run)

        result = update.run(Namespace(skip_docker=True))

        assert result == 0
        assert ['respec-ai', 'standards', 'validate'] in commands
        assert ['respec-ai', 'standards', 'render'] not in commands
        assert ['respec-ai', 'regenerate'] in commands
